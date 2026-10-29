from __future__ import annotations

import logging
import os
from typing import Dict, List

import numpy as np

from src.asr.utils.config import get_paths_settings
from src.utils.logging_setup import get_logger, log_event, log_warning


AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".opus"}
logger = get_logger("asr.voice_library")


def _resolve_voice_library_dir() -> str | None:
    """
    Read the voice library folder from the settings, resolve it to an absolute path,
    and check that it exists. Returns ``None`` when no voice library is configured.
    """
    raw = get_paths_settings().voice_library_dir.strip()
    if not raw:
        return None

    resolved = os.path.abspath(os.path.expanduser(raw))
    if not os.path.isdir(resolved):
        raise RuntimeError(f"Voice library not found: {resolved}")

    return resolved


LibraryPools = Dict[str, Dict[str, List[str]]]

# Pool name for clips placed directly in a person's folder.
ROOT_POOL = "."


def _is_audio_file(path: str) -> bool:
    return os.path.isfile(path) and os.path.splitext(path)[1].lower() in AUDIO_EXTS


def scan_voice_library(voice_library_dir: str) -> LibraryPools:
    """
    Build a person->pool->clips mapping by scanning a voice library folder.

    Expected layout::

        voci/
            PersonA/
                clip0.m4a              <- clips directly in the person folder form pool "."
                inside/  clip1.mp3  clip2.wav  ...
                car/     ...
            PersonB/
                outside/ ...

    People without any usable clip are skipped with a warning, so one empty folder in the
    library does not block everyone else. Returns an empty mapping when nobody has clips.
    """
    voice_library_dir = os.path.abspath(os.path.expanduser(voice_library_dir))
    if not os.path.isdir(voice_library_dir):
        raise RuntimeError(f"Voice library not found: {voice_library_dir}")

    voice_library: LibraryPools = {}

    for person_entry in sorted(os.scandir(voice_library_dir), key=lambda e: e.name.lower()):
        if not person_entry.is_dir():
            continue

        pools: Dict[str, List[str]] = {}
        root_clips = [
            os.path.normpath(os.path.join(person_entry.path, fn))
            for fn in sorted(os.listdir(person_entry.path), key=str.lower)
            if _is_audio_file(os.path.join(person_entry.path, fn))
        ]
        if root_clips:
            pools[ROOT_POOL] = root_clips

        pool_dirs = [entry for entry in sorted(os.scandir(person_entry.path), key=lambda e: e.name.lower()) if entry.is_dir()]
        for pool_entry in pool_dirs:
            clips: List[str] = []
            for root, _, files in os.walk(pool_entry.path):
                for fn in sorted(files, key=str.lower):
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in AUDIO_EXTS:
                        clips.append(os.path.normpath(os.path.join(root, fn)))

            if clips:
                pools[pool_entry.name] = clips
            else:
                log_warning(
                    "Person '%s': pool '%s' contains no supported voice clips; skipping it.",
                    person_entry.name,
                    pool_entry.name,
                )

        if not pools:
            log_warning(
                "Person '%s' has no supported voice clips in '%s'; skipping this person.",
                person_entry.name,
                person_entry.path,
            )
            continue

        for pool_name, clips in pools.items():
            log_event(
                logger,
                "voice library pool clips discovered",
                level=logging.DEBUG,
                person=person_entry.name,
                pool=pool_name,
                clip_count=len(clips),
            )
        voice_library[person_entry.name] = pools

    return voice_library


def load_library_voiceprints(device: str) -> Dict[str, List[np.ndarray]] | None:
    """
    Read the settings, scan the voice library, and return each person's voiceprints,
    from the cache or freshly computed.

    Returns ``None`` when no voice library is configured or it holds no clips.
    """
    voice_library_dir = _resolve_voice_library_dir()
    if voice_library_dir is None:
        log_warning("No voice library is configured; every speaker stays anonymous.")
        return None

    # Import lazily to avoid heavy transitive imports at module load time.
    from src.asr.voiceprint_cache import build_library_voiceprints

    voice_library = scan_voice_library(voice_library_dir)
    if not voice_library:
        log_warning(
            "No voice clips found under %s (supported formats: %s); every speaker stays anonymous.",
            voice_library_dir,
            ", ".join(sorted(AUDIO_EXTS)),
        )
        return None
    log_event(logger, "voice library loaded", level=logging.DEBUG, person_count=len(voice_library))
    return build_library_voiceprints(voice_library, voice_library_dir, device)
