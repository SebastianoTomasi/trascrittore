from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from functools import lru_cache

from src.asr.utils.device import DOCKER_GPU_FALLBACK_ENV, DeviceChoice, probe_cuda, resolve_device
from src.paths import (
    DEFAULT_ALIGNED_TRANSCRIPTS_DIR,
    DEFAULT_CACHE_DIR,
    DEFAULT_DIARIZATION_SEGMENTS_DIR,
    DEFAULT_DIARIZED_TRANSCRIPTS_DIR,
    DEFAULT_DIARIZED_WORDS_DIR,
    DEFAULT_VOICE_LIBRARY_DIR,
    DEFAULT_RECOGNIZED_WORDS_DIR,
    DEFAULT_RAW_ASR_DIR,
    DEFAULT_SPEAKER_RECOGNITION_DIAGNOSTICS_DIR,
    DEFAULT_SPEAKER_RECOGNITION_WINDOWS_DIR,
    normalize_path,
    project_paths_from_settings,
)
from src.settings import load_settings


def _normalize_path(value: str) -> str:
    """
    Normalize path values coming from INI (supports quoted paths).
    """
    return normalize_path(value)


# Read once per process: the defaults inside the transcriber, with the person's trascrittore.ini on top.
config: configparser.ConfigParser = load_settings()


def _parse_bool(raw_value: str, *, field_name: str) -> bool:
    value = raw_value.strip().lower()
    if value in {"1", "yes", "true", "on"}:
        return True
    if value in {"0", "no", "false", "off"}:
        return False
    raise RuntimeError(f"{field_name} must be a boolean value.")


@dataclass(frozen=True)
class WhisperSettings:
    model_id: str
    device: str
    compute_type: str
    batch_size: int
    language: str | None
    initial_prompt: str | None
    vad_onset: float
    vad_offset: float
    vad_chunk_size: int
    fallback_reason: str | None = None


@dataclass(frozen=True)
class DiarizationSettings:
    min_speakers: int | None
    max_speakers: int | None


@dataclass(frozen=True)
class VoiceprintSettings:
    model_id: str
    sample_rate: int


@dataclass(frozen=True)
class VadSettings:
    min_duration_sec: float


@dataclass(frozen=True)
class PathsSettings:
    input_path: str
    voice_library_dir: str = DEFAULT_VOICE_LIBRARY_DIR
    raw_asr_dir: str = DEFAULT_RAW_ASR_DIR
    aligned_transcripts_dir: str = DEFAULT_ALIGNED_TRANSCRIPTS_DIR
    diarization_segments_dir: str = DEFAULT_DIARIZATION_SEGMENTS_DIR
    diarized_words_dir: str = DEFAULT_DIARIZED_WORDS_DIR
    recognized_words_dir: str = DEFAULT_RECOGNIZED_WORDS_DIR
    diarized_transcripts_dir: str = DEFAULT_DIARIZED_TRANSCRIPTS_DIR
    speaker_recognition_diagnostics_dir: str = DEFAULT_SPEAKER_RECOGNITION_DIAGNOSTICS_DIR
    speaker_recognition_windows_dir: str = DEFAULT_SPEAKER_RECOGNITION_WINDOWS_DIR
    cache_dir: str = DEFAULT_CACHE_DIR


@dataclass(frozen=True)
class MatchingSettings:
    threshold: float
    margin: float
    window_sec: float
    min_window_sec: float
    min_total_speech_sec: float
    max_windows_per_spk: int
    save_window_clips: bool


@dataclass(frozen=True)
class SpeakerSettings:
    anonymous_prefix: str


@dataclass(frozen=True)
class LibrarySettings:
    """How clips of a named speaker are selected for the voice library."""

    keep_clips: int
    min_consistency: float
    # The cap on a person's added clips; not part of the selection, so changing it starts no new trial.
    max_clips: int = 64


@lru_cache(maxsize=1)
def _device_choice() -> DeviceChoice:
    """
    Decide the compute device once per process, warning when `auto` falls back to CPU.
    """
    requested = config["whisper"]["device"].strip()
    cuda_available, cuda_error = probe_cuda() if requested.lower() != "cpu" else (False, None)
    choice = resolve_device(
        requested,
        config["whisper"]["compute_type"].strip(),
        cuda_available=cuda_available,
        cuda_error=cuda_error,
        docker_gpu_missing=os.getenv(DOCKER_GPU_FALLBACK_ENV, "").strip().lower() == "docker",
    )
    if choice.fallback_reason:
        from src.utils.logging_setup import log_warning

        log_warning(
            "Running on CPU instead of GPU (compute_type=%s): %s",
            choice.compute_type,
            choice.fallback_reason,
        )
    return choice


def get_whisper_settings() -> WhisperSettings:
    """
    Return Whisper/ASR-related configuration with the resolved device and compute type.
    """
    choice = _device_choice()

    return WhisperSettings(
        model_id=config["whisper"]["model_id"],
        device=choice.device,
        compute_type=choice.compute_type,
        batch_size=int(config["whisper"]["batch_size"]),
        language=config["whisper"].get("language", "").strip() or None,
        initial_prompt=config["whisper"].get("initial_prompt", "").strip() or None,
        vad_onset=float(config["vad"]["onset"]),
        vad_offset=float(config["vad"]["offset"]),
        vad_chunk_size=int(config["vad"]["chunk_size"]),
        fallback_reason=choice.fallback_reason,
    )


def get_diarization_settings() -> DiarizationSettings:
    """
    Return optional speaker-count constraints for diarization.
    """
    section = config["diarization"] if "diarization" in config else {}
    min_speakers = section.get("min_speakers", "").strip()
    max_speakers = section.get("max_speakers", "").strip()
    return DiarizationSettings(
        min_speakers=int(min_speakers) if min_speakers else None,
        max_speakers=int(max_speakers) if max_speakers else None,
    )


def get_voiceprint_settings() -> VoiceprintSettings:
    """
    Return voiceprint-model configuration used for speaker recognition.
    """
    return VoiceprintSettings(
        model_id=config["voiceprint"]["model_id"],
        sample_rate=int(config["voiceprint"]["sample_rate"]),
    )


def get_vad_settings() -> VadSettings:
    """
    Return the minimum audio duration worth voiceprint.
    """
    return VadSettings(min_duration_sec=float(config["vad"]["min_duration_sec"]))


def get_paths_settings() -> PathsSettings:
    """
    Return input/output paths configured for the pipeline.
    """
    output = config["paths_output"]
    return PathsSettings(
        input_path=_normalize_path(config["paths"].get("input_path", "")),
        voice_library_dir=_normalize_path(config["paths"].get("voice_library_dir", DEFAULT_VOICE_LIBRARY_DIR)),
        raw_asr_dir=_normalize_path(output.get("raw_asr_dir", DEFAULT_RAW_ASR_DIR)),
        aligned_transcripts_dir=_normalize_path(output.get("aligned_transcripts_dir", DEFAULT_ALIGNED_TRANSCRIPTS_DIR)),
        diarization_segments_dir=_normalize_path(
            output.get("diarization_segments_dir", DEFAULT_DIARIZATION_SEGMENTS_DIR)
        ),
        diarized_words_dir=_normalize_path(output.get("diarized_words_dir", DEFAULT_DIARIZED_WORDS_DIR)),
        recognized_words_dir=_normalize_path(output.get("recognized_words_dir", DEFAULT_RECOGNIZED_WORDS_DIR)),
        diarized_transcripts_dir=_normalize_path(
            output.get("diarized_transcripts_dir", DEFAULT_DIARIZED_TRANSCRIPTS_DIR)
        ),
        speaker_recognition_diagnostics_dir=_normalize_path(
            output.get("speaker_recognition_diagnostics_dir", DEFAULT_SPEAKER_RECOGNITION_DIAGNOSTICS_DIR)
        ),
        speaker_recognition_windows_dir=_normalize_path(
            output.get("speaker_recognition_windows_dir", DEFAULT_SPEAKER_RECOGNITION_WINDOWS_DIR)
        ),
        cache_dir=_normalize_path(output.get("cache_dir", DEFAULT_CACHE_DIR)),
    )


def get_voiceprint_cache_path(paths: PathsSettings | None = None) -> str:
    return project_paths_from_settings(paths or get_paths_settings()).voiceprint_cache_path


def get_data_directories(paths: PathsSettings | None = None) -> tuple[str, ...]:
    """
    Return every application-owned data directory that should exist at runtime.
    """
    return project_paths_from_settings(paths or get_paths_settings()).runtime_dirs()


def ensure_data_directories(paths: PathsSettings | None = None) -> None:
    """
    Create the configured data directory structure if it is missing.
    """
    project_paths_from_settings(paths or get_paths_settings()).ensure_runtime_dirs()


def get_matching_settings() -> MatchingSettings:
    """
    Return speaker-matching parameters used to assign names.
    """
    section = config["matching"]
    settings = MatchingSettings(
        threshold=float(section["threshold"]),
        margin=float(section["margin"]),
        window_sec=float(section["window_sec"]),
        min_window_sec=float(section["min_window_sec"]),
        min_total_speech_sec=float(section["min_total_speech_sec"]),
        max_windows_per_spk=int(section["max_windows_per_spk"]),
        save_window_clips=_parse_bool(section["save_window_clips"], field_name="matching.save_window_clips"),
    )
    if settings.window_sec <= 0:
        raise RuntimeError("matching.window_sec must be greater than zero.")
    if settings.min_window_sec <= 0:
        raise RuntimeError("matching.min_window_sec must be greater than zero.")
    if settings.min_window_sec > settings.window_sec:
        raise RuntimeError("matching.min_window_sec must be <= matching.window_sec.")
    if settings.min_total_speech_sec < 0:
        raise RuntimeError("matching.min_total_speech_sec must be >= 0.")
    if settings.max_windows_per_spk <= 0:
        raise RuntimeError("matching.max_windows_per_spk must be greater than zero.")
    return settings


def get_speaker_settings() -> SpeakerSettings:
    """
    Return speaker-label formatting settings for anonymous speakers.
    """
    # anonymous_prefix may legitimately be empty; default to empty string if missing.
    section = config["speaker"] if "speaker" in config else {}
    anonymous_prefix = section.get("anonymous_prefix", "").strip()
    return SpeakerSettings(anonymous_prefix=anonymous_prefix)


def get_library_settings() -> LibrarySettings:
    """
    Return the clip selection used when naming a speaker adds clips to the voice library.
    """
    section = config["library"]
    settings = LibrarySettings(
        keep_clips=int(section["keep_clips"]),
        min_consistency=float(section["min_consistency"]),
        max_clips=int(section["max_clips"]),
    )
    if settings.keep_clips <= 0:
        raise RuntimeError("library.keep_clips must be greater than zero.")
    if settings.max_clips < settings.keep_clips:
        raise RuntimeError("library.max_clips must be at least library.keep_clips.")
    return settings
