from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENROLLMENT_DIR = "data/voci"
DEFAULT_RAW_ASR_DIR = "data/work/raw/asr"
DEFAULT_ALIGNED_TRANSCRIPTS_DIR = "data/work/raw/aligned"
DEFAULT_DIARIZATION_SEGMENTS_DIR = "data/work/raw/diarization_segments"
DEFAULT_DIARIZED_WORDS_DIR = "data/work/raw/diarized_words"
DEFAULT_IDENTIFIED_WORDS_DIR = "data/work/raw/identified_words"
DEFAULT_DIARIZED_TRANSCRIPTS_DIR = "data/work/transcripts"
DEFAULT_SPEAKER_IDENTIFICATION_DIAGNOSTICS_DIR = "data/work/raw/speaker_identification"
DEFAULT_SPEAKER_IDENTIFICATION_WINDOWS_DIR = "data/work/raw/speaker_identification_windows"
DEFAULT_CACHE_DIR = "cache"


def normalize_path(value: str | os.PathLike[str]) -> str:
    raw = str(value).strip().strip('"').strip("'")
    return os.path.normpath(os.path.expanduser(raw)) if raw else ""


def clean_path(value: str | os.PathLike[str]) -> str:
    raw = str(value).strip().strip('"').strip("'")
    return os.path.expanduser(raw) if raw else ""


def file_stem(path_value: str | os.PathLike[str]) -> str:
    return os.path.splitext(os.path.basename(str(path_value)))[0]


def join_path(base: str | os.PathLike[str], *parts: str) -> str:
    return os.path.join(str(base), *parts)


def safe_filename_part(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "_.-" else "_" for char in value.strip())
    return cleaned.strip("._") or "value"


@dataclass(frozen=True)
class ProjectPaths:
    input_path: str
    enrollment_dir: str = DEFAULT_ENROLLMENT_DIR
    raw_asr_dir: str = DEFAULT_RAW_ASR_DIR
    aligned_transcripts_dir: str = DEFAULT_ALIGNED_TRANSCRIPTS_DIR
    diarization_segments_dir: str = DEFAULT_DIARIZATION_SEGMENTS_DIR
    diarized_words_dir: str = DEFAULT_DIARIZED_WORDS_DIR
    identified_words_dir: str = DEFAULT_IDENTIFIED_WORDS_DIR
    diarized_transcripts_dir: str = DEFAULT_DIARIZED_TRANSCRIPTS_DIR
    speaker_identification_diagnostics_dir: str = DEFAULT_SPEAKER_IDENTIFICATION_DIAGNOSTICS_DIR
    speaker_identification_windows_dir: str = DEFAULT_SPEAKER_IDENTIFICATION_WINDOWS_DIR
    cache_dir: str = DEFAULT_CACHE_DIR

    @property
    def embeddings_cache_dir(self) -> str:
        return join_path(self.cache_dir, "embeddings")

    @property
    def enrollment_cache_path(self) -> str:
        return join_path(self.embeddings_cache_dir, "enrollment_cache.json")

    def raw_asr_path(self, input_audio_path: str) -> str:
        return join_path(self.raw_asr_dir, f"{file_stem(input_audio_path)}.json")

    def aligned_transcript_path(self, input_audio_path: str) -> str:
        return join_path(self.aligned_transcripts_dir, f"{file_stem(input_audio_path)}.json")

    def diarization_segments_path(self, input_audio_path: str) -> str:
        return join_path(self.diarization_segments_dir, f"{file_stem(input_audio_path)}.json")

    def diarized_words_path(self, input_audio_path: str) -> str:
        return join_path(self.diarized_words_dir, f"{file_stem(input_audio_path)}.json")

    def identified_words_path(self, input_audio_path: str) -> str:
        return join_path(self.identified_words_dir, f"{file_stem(input_audio_path)}.json")

    def diarized_transcript_path(self, input_audio_path: str) -> str:
        return join_path(self.diarized_transcripts_dir, f"{file_stem(input_audio_path)}.json")

    def speaker_identification_diagnostics_path(self, input_audio_path: str) -> str:
        return join_path(self.speaker_identification_diagnostics_dir, f"{file_stem(input_audio_path)}.json")

    def speaker_identification_window_clip_path(
        self,
        input_audio_path: str,
        clip_index: int,
        speaker: str,
        duration_sec: float,
    ) -> str:
        stem = safe_filename_part(file_stem(input_audio_path))
        safe_speaker = safe_filename_part(speaker)
        filename = f"{stem}_clip_{clip_index:03d}_{safe_speaker}_duration_{duration_sec:.3f}s.wav"
        return join_path(self.speaker_identification_windows_dir, filename)

    def runtime_dirs(self) -> tuple[str, ...]:
        return (
            self.enrollment_dir,
            self.raw_asr_dir,
            self.aligned_transcripts_dir,
            self.diarization_segments_dir,
            self.diarized_words_dir,
            self.identified_words_dir,
            self.diarized_transcripts_dir,
            self.speaker_identification_diagnostics_dir,
            self.speaker_identification_windows_dir,
        )

    def ensure_runtime_dirs(self) -> None:
        for directory in self.runtime_dirs():
            if directory:
                os.makedirs(directory, exist_ok=True)


def project_paths_from_settings(settings: Any) -> ProjectPaths:
    return ProjectPaths(
        input_path=clean_path(getattr(settings, "input_path", "")),
        enrollment_dir=clean_path(getattr(settings, "enrollment_dir", DEFAULT_ENROLLMENT_DIR)),
        raw_asr_dir=clean_path(getattr(settings, "raw_asr_dir", DEFAULT_RAW_ASR_DIR)),
        aligned_transcripts_dir=clean_path(
            getattr(settings, "aligned_transcripts_dir", DEFAULT_ALIGNED_TRANSCRIPTS_DIR)
        ),
        diarization_segments_dir=clean_path(
            getattr(settings, "diarization_segments_dir", DEFAULT_DIARIZATION_SEGMENTS_DIR)
        ),
        diarized_words_dir=clean_path(getattr(settings, "diarized_words_dir", DEFAULT_DIARIZED_WORDS_DIR)),
        identified_words_dir=clean_path(getattr(settings, "identified_words_dir", DEFAULT_IDENTIFIED_WORDS_DIR)),
        diarized_transcripts_dir=clean_path(
            getattr(settings, "diarized_transcripts_dir", DEFAULT_DIARIZED_TRANSCRIPTS_DIR)
        ),
        speaker_identification_diagnostics_dir=clean_path(
            getattr(
                settings,
                "speaker_identification_diagnostics_dir",
                DEFAULT_SPEAKER_IDENTIFICATION_DIAGNOSTICS_DIR,
            )
        ),
        speaker_identification_windows_dir=clean_path(
            getattr(settings, "speaker_identification_windows_dir", DEFAULT_SPEAKER_IDENTIFICATION_WINDOWS_DIR)
        ),
        cache_dir=clean_path(getattr(settings, "cache_dir", DEFAULT_CACHE_DIR)),
    )
