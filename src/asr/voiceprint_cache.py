from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import soundfile as sf
import whisperx
import torch

from src.asr.utils.config import get_voiceprint_cache_path
from src.asr.voiceprints import compute_voiceprint, load_voiceprint_model, mean_voiceprint, normalize_voiceprint
from src.utils.logging_setup import get_logger, log_event, log_warning

_CACHE_FILENAME = "voiceprint_cache.json"
_CACHE_DIR: str | None = None
# v3: voiceprints computed with TF32 disabled (see load_voiceprint_model).
_SCHEMA_VERSION = 3
logger = get_logger("asr.voiceprint_cache")

# --- Quality thresholds (based on Azure SpeakerRecognition ≥20 s, project config
#     recommendation of 30–120 s total, and ECAPA-TDNN research showing degradation
#     below ~5 s per segment). ---
_MIN_CLIPS_PER_PERSON = 3
_MIN_CLIP_DURATION_SEC = 5.0
_MAX_CLIP_DURATION_SEC = 120.0
_MIN_TOTAL_DURATION_SEC = 30.0


# ---------------------------------------------------------------------------
# JSON cache helpers
# ---------------------------------------------------------------------------

_CacheData = Dict[str, Any]
LibraryPools = Dict[str, Dict[str, List[str]]]
Fingerprint = Tuple[str, int, float]


def _get_cache_path() -> str:
    if _CACHE_DIR is not None:
        return os.path.join(_CACHE_DIR, _CACHE_FILENAME)
    return get_voiceprint_cache_path()


def _load_cache() -> _CacheData:
    path = _get_cache_path()
    if not os.path.isfile(path):
        return {"schema_version": _SCHEMA_VERSION, "people": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"schema_version": _SCHEMA_VERSION, "people": {}}

    if not isinstance(data, dict) or data.get("schema_version") != _SCHEMA_VERSION:
        return {"schema_version": _SCHEMA_VERSION, "people": {}}
    if not isinstance(data.get("people"), dict):
        return {"schema_version": _SCHEMA_VERSION, "people": {}}
    return data


def _save_cache(data: _CacheData) -> None:
    path = _get_cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _voiceprint_to_json(arr: np.ndarray) -> Dict[str, Any]:
    raw = base64.b64encode(arr.astype(np.float32).tobytes()).decode("ascii")
    return {"data": raw, "shape": list(arr.shape)}


def _voiceprint_from_json(obj: Dict[str, Any]) -> np.ndarray:
    raw = base64.b64decode(obj["data"])
    shape = tuple(obj["shape"])
    return np.frombuffer(raw, dtype=np.float32).reshape(shape).copy()


def _clip_fingerprint(clip_path: str, voice_library_dir: str) -> Fingerprint:
    rel = os.path.relpath(clip_path, voice_library_dir)
    stat = os.stat(clip_path)
    return (rel, stat.st_size, stat.st_mtime)


def _fingerprints_to_json(fps: List[Fingerprint]) -> List[Dict[str, Any]]:
    return [{"path": p, "size": s, "mtime": m} for p, s, m in fps]


def _pool_needs_update(
    cached_pool: Dict[str, Any] | None,
    fingerprints: List[Fingerprint],
) -> bool:
    if cached_pool is None:
        return True

    cached_clips = cached_pool.get("clips", [])
    if len(cached_clips) != len(fingerprints):
        return True

    cached_set = {(c["path"], c["size"], c["mtime"]) for c in cached_clips}
    disk_set = set(fingerprints)
    return cached_set != disk_set


# ---------------------------------------------------------------------------
# Voice clip quality checks
# ---------------------------------------------------------------------------

def _validate_voice_clips(voice_library: LibraryPools) -> None:
    for name, pools in voice_library.items():
        all_clips = [clip for clips in pools.values() for clip in clips]
        n_clips = len(all_clips)
        if n_clips < _MIN_CLIPS_PER_PERSON:
            log_warning(
                "Person '%s': only %d voice clip(s) (recommended >= %d). "
                "Using clips from different sessions/microphones improves robustness.",
                name, n_clips, _MIN_CLIPS_PER_PERSON,
            )

        total_dur = 0.0
        for clip_path in all_clips:
            try:
                info = sf.info(clip_path)
                dur = info.duration
            except Exception:
                # soundfile cannot read formats such as m4a; computing the voiceprint decodes them through ffmpeg anyway.
                log_event(
                    logger,
                    "voice clip duration unreadable; quality check skipped",
                    level=logging.DEBUG,
                    person=name,
                    clip=os.path.basename(clip_path),
                )
                continue

            total_dur += dur

            if dur < _MIN_CLIP_DURATION_SEC:
                log_warning(
                    "Person '%s': clip '%s' is only %.1f s (recommended >= %.0f s). "
                    "Short clips produce less stable voiceprints.",
                    name, os.path.basename(clip_path), dur, _MIN_CLIP_DURATION_SEC,
                )

            if dur > _MAX_CLIP_DURATION_SEC:
                log_warning(
                    "Person '%s': clip '%s' is %.0f s (recommended <= %.0f s). "
                    "Very long clips may contain non-speech or overlapping speakers, diluting the voiceprint.",
                    name, os.path.basename(clip_path), dur, _MAX_CLIP_DURATION_SEC,
                )

        if total_dur < _MIN_TOTAL_DURATION_SEC:
            log_warning(
                "Person '%s': the voice clips last %.1f s in total (recommended >= %.0f s). "
                "More speech helps build a reliable voiceprint.",
                name, total_dur, _MIN_TOTAL_DURATION_SEC,
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_library_voiceprints(
    voice_library: LibraryPools,
    voice_library_dir: str,
    device: str,
) -> Dict[str, List[np.ndarray]]:
    """
    Return each person's pool voiceprints, computing only the pools whose clips changed
    since the last run. The voiceprints are kept in a JSON file inside ``cache/voiceprints/``.
    """
    if not voice_library:
        raise RuntimeError("The voice library is empty: there are no voiceprints to compute.")

    log_event(logger, "library voiceprints build started", level=logging.DEBUG, person_count=len(voice_library))
    _validate_voice_clips(voice_library)

    cache = _load_cache()
    people_cache = cache.setdefault("people", {})
    log_event(logger, "voiceprint cache loaded", level=logging.DEBUG, cached_person_count=len(people_cache))
    current_names = set(voice_library.keys())

    # Remove persons no longer on disk.
    for stale in set(people_cache.keys()) - current_names:
        log_event(logger, "voiceprint cache removing a person no longer in the library", level=logging.DEBUG, person=stale)
        del people_cache[stale]

    voiceprint_model_loaded = False
    voiceprint_model = None
    result: Dict[str, List[np.ndarray]] = {}

    try:
        for name, pools in voice_library.items():
            if not pools:
                raise RuntimeError(f"Person '{name}' has no pools.")

            person_cache = people_cache.setdefault(name, {"pools": {}})
            pool_cache = person_cache.setdefault("pools", {})
            current_pools = set(pools.keys())
            for stale_pool in set(pool_cache.keys()) - current_pools:
                log_event(
                    logger,
                    "voiceprint cache removing stale pool",
                    level=logging.DEBUG,
                    person=name,
                    pool=stale_pool,
                )
                del pool_cache[stale_pool]

            person_voiceprints: List[np.ndarray] = []
            for pool_name, clips in pools.items():
                if not clips:
                    raise RuntimeError(f"Person '{name}': pool '{pool_name}' has no clips.")

                fingerprints = [_clip_fingerprint(p, voice_library_dir) for p in clips]

                if not _pool_needs_update(pool_cache.get(pool_name), fingerprints):
                    log_event(
                        logger,
                        "pool voiceprint loaded from cache",
                        level=logging.DEBUG,
                        person=name,
                        pool=pool_name,
                        clip_count=len(clips),
                    )
                    person_voiceprints.append(_voiceprint_from_json(pool_cache[pool_name]["voiceprint"]))
                    continue

                if not voiceprint_model_loaded:
                    log_event(logger, "loading the voiceprint model", level=logging.DEBUG)
                    voiceprint_model = load_voiceprint_model(device)
                    voiceprint_model_loaded = True

                clip_voiceprints = []
                for p in clips:
                    log_event(
                        logger,
                        "computing a voice clip voiceprint",
                        level=logging.DEBUG,
                        person=name,
                        pool=pool_name,
                    )
                    clip_audio = whisperx.load_audio(p)
                    clip_voiceprints.append(normalize_voiceprint(compute_voiceprint(voiceprint_model, clip_audio, device=device)))

                voiceprint = normalize_voiceprint(mean_voiceprint(clip_voiceprints))
                pool_cache[pool_name] = {
                    "clips": _fingerprints_to_json(fingerprints),
                    "voiceprint": _voiceprint_to_json(voiceprint),
                }
                person_voiceprints.append(voiceprint)

            result[name] = person_voiceprints
    finally:
        if voiceprint_model is not None:
            del voiceprint_model
        if str(device).startswith("cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()

    _save_cache(cache)
    log_event(logger, "library voiceprints build completed", level=logging.DEBUG, person_count=len(result))
    return result
