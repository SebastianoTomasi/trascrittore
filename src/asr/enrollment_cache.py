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

from src.asr.utils.config import get_enrollment_cache_path
from src.asr.embeddings import embed_audio_waveform, load_embedding_model, mean_embed, normalize_embed
from src.utils.logging_setup import get_logger, log_event, log_warning

_CACHE_FILENAME = "enrollment_cache.json"
_CACHE_DIR: str | None = None
# v3: embeddings computed with TF32 disabled (see load_embedding_model).
_SCHEMA_VERSION = 3
logger = get_logger("asr.enrollment_cache")

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
EnrollmentPools = Dict[str, Dict[str, List[str]]]
Fingerprint = Tuple[str, int, float]


def _get_cache_path() -> str:
    if _CACHE_DIR is not None:
        return os.path.join(_CACHE_DIR, _CACHE_FILENAME)
    return get_enrollment_cache_path()


def _load_cache() -> _CacheData:
    path = _get_cache_path()
    if not os.path.isfile(path):
        return {"schema_version": _SCHEMA_VERSION, "speakers": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"schema_version": _SCHEMA_VERSION, "speakers": {}}

    if not isinstance(data, dict) or data.get("schema_version") != _SCHEMA_VERSION:
        return {"schema_version": _SCHEMA_VERSION, "speakers": {}}
    if not isinstance(data.get("speakers"), dict):
        return {"schema_version": _SCHEMA_VERSION, "speakers": {}}
    return data


def _save_cache(data: _CacheData) -> None:
    path = _get_cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _embedding_to_json(arr: np.ndarray) -> Dict[str, Any]:
    raw = base64.b64encode(arr.astype(np.float32).tobytes()).decode("ascii")
    return {"data": raw, "shape": list(arr.shape)}


def _embedding_from_json(obj: Dict[str, Any]) -> np.ndarray:
    raw = base64.b64decode(obj["data"])
    shape = tuple(obj["shape"])
    return np.frombuffer(raw, dtype=np.float32).reshape(shape).copy()


def _clip_fingerprint(clip_path: str, enrollment_dir: str) -> Fingerprint:
    rel = os.path.relpath(clip_path, enrollment_dir)
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
# Enrollment quality validation
# ---------------------------------------------------------------------------

def _validate_enrollment_clips(enrollment: EnrollmentPools) -> None:
    for name, pools in enrollment.items():
        all_clips = [clip for clips in pools.values() for clip in clips]
        n_clips = len(all_clips)
        if n_clips < _MIN_CLIPS_PER_PERSON:
            log_warning(
                "Speaker '%s': only %d enrollment clip(s) (recommended >= %d). "
                "Using clips from different sessions/microphones improves robustness.",
                name, n_clips, _MIN_CLIPS_PER_PERSON,
            )

        total_dur = 0.0
        for clip_path in all_clips:
            try:
                info = sf.info(clip_path)
                dur = info.duration
            except Exception:
                # soundfile cannot read formats such as m4a; embedding decodes them through ffmpeg anyway.
                log_event(
                    logger,
                    "enrollment clip duration unreadable; quality check skipped",
                    level=logging.DEBUG,
                    speaker=name,
                    clip=os.path.basename(clip_path),
                )
                continue

            total_dur += dur

            if dur < _MIN_CLIP_DURATION_SEC:
                log_warning(
                    "Speaker '%s': clip '%s' is only %.1f s (recommended >= %.0f s). "
                    "Short clips produce less stable embeddings.",
                    name, os.path.basename(clip_path), dur, _MIN_CLIP_DURATION_SEC,
                )

            if dur > _MAX_CLIP_DURATION_SEC:
                log_warning(
                    "Speaker '%s': clip '%s' is %.0f s (recommended <= %.0f s). "
                    "Very long clips may contain non-speech or overlapping speakers, diluting the voiceprint.",
                    name, os.path.basename(clip_path), dur, _MAX_CLIP_DURATION_SEC,
                )

        if total_dur < _MIN_TOTAL_DURATION_SEC:
            log_warning(
                "Speaker '%s': total enrollment audio is %.1f s (recommended >= %.0f s). "
                "More speech helps build a reliable voiceprint.",
                name, total_dur, _MIN_TOTAL_DURATION_SEC,
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_enrollment_db(
    enrollment: EnrollmentPools,
    enrollment_dir: str,
    device: str,
) -> Dict[str, List[np.ndarray]]:
    """
    Build (or load from cache) a speaker embedding database.

    Embeddings are persisted in a JSON file inside ``cache/embeddings/``.  Only
    persons whose clip set has changed since the last run are recomputed.
    """
    if not enrollment:
        raise RuntimeError("Enrollment mapping is empty; cannot build enrollment database.")

    log_event(logger, "enrollment database build started", level=logging.DEBUG, speaker_count=len(enrollment))
    _validate_enrollment_clips(enrollment)

    cache = _load_cache()
    speakers_cache = cache.setdefault("speakers", {})
    log_event(logger, "enrollment cache loaded", level=logging.DEBUG, cached_speaker_count=len(speakers_cache))
    current_names = set(enrollment.keys())

    # Remove persons no longer on disk.
    for stale in set(speakers_cache.keys()) - current_names:
        log_event(logger, "enrollment cache removing stale speaker", level=logging.DEBUG, speaker=stale)
        del speakers_cache[stale]

    emb_model_loaded = False
    emb_model = None
    result: Dict[str, List[np.ndarray]] = {}

    try:
        for name, pools in enrollment.items():
            if not pools:
                raise RuntimeError(f"Enrollment user '{name}' has no pools.")

            person_cache = speakers_cache.setdefault(name, {"pools": {}})
            pool_cache = person_cache.setdefault("pools", {})
            current_pools = set(pools.keys())
            for stale_pool in set(pool_cache.keys()) - current_pools:
                log_event(
                    logger,
                    "enrollment cache removing stale pool",
                    level=logging.DEBUG,
                    speaker=name,
                    pool=stale_pool,
                )
                del pool_cache[stale_pool]

            person_embeddings: List[np.ndarray] = []
            for pool_name, clips in pools.items():
                if not clips:
                    raise RuntimeError(f"Enrollment user '{name}' pool '{pool_name}' has no clips.")

                fingerprints = [_clip_fingerprint(p, enrollment_dir) for p in clips]

                if not _pool_needs_update(pool_cache.get(pool_name), fingerprints):
                    log_event(
                        logger,
                        "enrollment speaker pool loaded from cache",
                        level=logging.DEBUG,
                        speaker=name,
                        pool=pool_name,
                        clip_count=len(clips),
                    )
                    person_embeddings.append(_embedding_from_json(pool_cache[pool_name]["embedding"]))
                    continue

                if not emb_model_loaded:
                    log_event(logger, "loading enrollment embedding model", level=logging.DEBUG)
                    emb_model = load_embedding_model(device)
                    emb_model_loaded = True

                clip_embeds = []
                for p in clips:
                    log_event(
                        logger,
                        "embedding enrollment clip",
                        level=logging.DEBUG,
                        speaker=name,
                        pool=pool_name,
                    )
                    clip_audio = whisperx.load_audio(p)
                    clip_embeds.append(normalize_embed(embed_audio_waveform(emb_model, clip_audio, device=device)))

                embedding = normalize_embed(mean_embed(clip_embeds))
                pool_cache[pool_name] = {
                    "clips": _fingerprints_to_json(fingerprints),
                    "embedding": _embedding_to_json(embedding),
                }
                person_embeddings.append(embedding)

            result[name] = person_embeddings
    finally:
        if emb_model is not None:
            del emb_model
        if str(device).startswith("cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()

    _save_cache(cache)
    log_event(logger, "enrollment database build completed", level=logging.DEBUG, speaker_count=len(result))
    return result
