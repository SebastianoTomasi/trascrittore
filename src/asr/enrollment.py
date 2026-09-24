from __future__ import annotations

import logging
import os
from typing import Dict, List

import numpy as np

from src.asr.utils.config import get_paths_settings
from src.utils.logging_setup import get_logger, log_event, log_warning


_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".opus"}
logger = get_logger("asr.enrollment")


def _resolve_enrollment_dir() -> str | None:
    """
    Read the enrollment directory from config, resolve it to an absolute path,
    and validate that it exists.  Returns ``None`` when enrollment is not
    configured.
    """
    raw = get_paths_settings().enrollment_dir.strip()
    if not raw:
        return None

    resolved = os.path.abspath(os.path.expanduser(raw))
    if not os.path.isdir(resolved):
        raise RuntimeError(f"Enrollment directory not found: {resolved}")

    return resolved


EnrollmentPools = Dict[str, Dict[str, List[str]]]

# Pool name for clips placed directly in a person's folder.
ROOT_POOL = "."


def _is_audio_file(path: str) -> bool:
    return os.path.isfile(path) and os.path.splitext(path)[1].lower() in _AUDIO_EXTS


def _build_enrollment_from_dir(enrollment_dir: str) -> EnrollmentPools:
    """
    Build a person->pool->clips mapping by scanning an enrollment directory tree.

    Expected layout::

        enrollment_clips/
            PersonA/
                clip0.m4a              <- clips directly in the person folder form pool "."
                inside/  clip1.mp3  clip2.wav  ...
                car/     ...
            PersonB/
                outside/ ...

    People without any usable clip are skipped with a warning, so one empty folder in a
    shared library does not block everyone else. Returns an empty mapping when nobody has clips.
    """
    enrollment_dir = os.path.abspath(os.path.expanduser(enrollment_dir))
    if not os.path.isdir(enrollment_dir):
        raise RuntimeError(f"Enrollment dir not found: {enrollment_dir}")

    enrollment: EnrollmentPools = {}

    for person_entry in sorted(os.scandir(enrollment_dir), key=lambda e: e.name.lower()):
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
                    if ext in _AUDIO_EXTS:
                        clips.append(os.path.normpath(os.path.join(root, fn)))

            if clips:
                pools[pool_entry.name] = clips
            else:
                log_warning(
                    "Speaker '%s': enrollment pool '%s' contains no supported audio clips; skipping it.",
                    person_entry.name,
                    pool_entry.name,
                )

        if not pools:
            log_warning(
                "Speaker '%s' has no supported audio clips in '%s'; skipping this person.",
                person_entry.name,
                person_entry.path,
            )
            continue

        for pool_name, clips in pools.items():
            log_event(
                logger,
                "enrollment speaker pool clips discovered",
                level=logging.DEBUG,
                speaker=person_entry.name,
                pool=pool_name,
                clip_count=len(clips),
            )
        enrollment[person_entry.name] = pools

    return enrollment


def load_enrollment_embeddings(device: str) -> Dict[str, List[np.ndarray]] | None:
    """
    End-to-end enrollment: read config, scan the enrollment directory, and
    return cached (or freshly computed) speaker embeddings.

    Returns ``None`` when no enrollment directory is configured or it holds no clips.
    """
    enrollment_dir = _resolve_enrollment_dir()
    if enrollment_dir is None:
        log_warning("Enrollment is empty; speaker identity recognition cannot be performed.")
        return None

    # Import lazily to avoid heavy transitive imports at module load time.
    from src.asr.enrollment_cache import build_enrollment_db

    enrollment = _build_enrollment_from_dir(enrollment_dir)
    if not enrollment:
        log_warning(
            "No enrollment clips found under %s (supported formats: %s); every speaker stays anonymous.",
            enrollment_dir,
            ", ".join(sorted(_AUDIO_EXTS)),
        )
        return None
    log_event(logger, "enrollment directory loaded", level=logging.DEBUG, speaker_count=len(enrollment))
    return build_enrollment_db(enrollment, enrollment_dir, device)

