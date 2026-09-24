from __future__ import annotations

import os
import shutil
from pathlib import Path

from src.asr.utils.config import (
    PathsSettings,
    ensure_data_directories,
    get_data_directories,
    get_enrollment_cache_path,
)


def _paths() -> PathsSettings:
    return PathsSettings(
        input_path="riunioni/input.m4a",
        enrollment_dir="data/voci",
        raw_asr_dir="data/work/raw/asr",
        aligned_transcripts_dir="data/work/raw/aligned",
        diarization_segments_dir="data/work/raw/diarization_segments",
        diarized_words_dir="data/work/raw/diarized_words",
        identified_words_dir="data/work/raw/identified_words",
        diarized_transcripts_dir="data/work/transcripts",
        speaker_identification_diagnostics_dir="data/work/raw/speaker_identification",
        speaker_identification_windows_dir="data/work/raw/speaker_identification_windows",
        cache_dir="cache",
    )


def test_data_directories_include_complete_runtime_structure():
    directories = {os.path.normpath(path) for path in get_data_directories(_paths())}

    assert directories == {
        os.path.normpath("data/voci"),
        os.path.normpath("data/work/raw/asr"),
        os.path.normpath("data/work/raw/aligned"),
        os.path.normpath("data/work/raw/diarization_segments"),
        os.path.normpath("data/work/raw/diarized_words"),
        os.path.normpath("data/work/raw/identified_words"),
        os.path.normpath("data/work/transcripts"),
        os.path.normpath("data/work/raw/speaker_identification"),
        os.path.normpath("data/work/raw/speaker_identification_windows"),
    }


def test_ensure_data_directories_creates_missing_structure(monkeypatch):
    original_cwd = Path.cwd()
    scratch_dir = Path("tests/.tmp_data_directories").resolve()
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)

    paths = _paths()

    try:
        scratch_dir.mkdir(parents=True)
        monkeypatch.chdir(scratch_dir)
        ensure_data_directories(paths)

        for directory in get_data_directories(paths):
            assert Path(directory).is_dir()
    finally:
        os.chdir(original_cwd)
        if scratch_dir.exists():
            shutil.rmtree(scratch_dir)


def test_enrollment_cache_path_is_derived_from_paths_settings():
    assert os.path.normpath(get_enrollment_cache_path(_paths())) == os.path.normpath(
        "cache/embeddings/enrollment_cache.json"
    )
