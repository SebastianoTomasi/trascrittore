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
    DEFAULT_ENROLLMENT_DIR,
    DEFAULT_IDENTIFIED_WORDS_DIR,
    DEFAULT_RAW_ASR_DIR,
    DEFAULT_SPEAKER_IDENTIFICATION_DIAGNOSTICS_DIR,
    DEFAULT_SPEAKER_IDENTIFICATION_WINDOWS_DIR,
    normalize_path,
    project_paths_from_settings,
)


CONFIG_PATH = os.getenv("MEETING_CONFIG", "meeting.ini")


def _normalize_path(value: str) -> str:
    """
    Normalize path values coming from INI (supports quoted paths).
    """
    return normalize_path(value)


def _load_config() -> configparser.ConfigParser:
    """
    Load the INI configuration once and return a shared ConfigParser.
    """
    parser = configparser.ConfigParser(interpolation=None)
    read_files = parser.read(CONFIG_PATH, encoding="utf-8")
    if not read_files:
        raise RuntimeError(
            f"Config file not found: {CONFIG_PATH}. Copy docker/meeting.ini to meeting.ini and adapt its paths, "
            "or point MEETING_CONFIG at another file."
        )
    return parser


config: configparser.ConfigParser = _load_config()


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
class EmbeddingSettings:
    model_id: str
    sample_rate: int


@dataclass(frozen=True)
class VadSettings:
    min_duration_sec: float


@dataclass(frozen=True)
class PathsSettings:
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
    unknown_prefix: str


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


def get_embedding_settings() -> EmbeddingSettings:
    """
    Return embedding-model configuration used for speaker identification.
    """
    return EmbeddingSettings(
        model_id=config["embedding"]["model_id"],
        sample_rate=int(config["embedding"]["sample_rate"]),
    )


def get_vad_settings() -> VadSettings:
    """
    Return the minimum audio duration worth embedding.
    """
    return VadSettings(min_duration_sec=float(config["vad"]["min_duration_sec"]))


def get_paths_settings() -> PathsSettings:
    """
    Return input/output paths configured for the pipeline.
    """
    output = config["paths_output"]
    return PathsSettings(
        input_path=_normalize_path(config["paths"].get("input_path", "")),
        enrollment_dir=_normalize_path(config["paths"].get("enrollment_dir", DEFAULT_ENROLLMENT_DIR)),
        raw_asr_dir=_normalize_path(output.get("raw_asr_dir", DEFAULT_RAW_ASR_DIR)),
        aligned_transcripts_dir=_normalize_path(output.get("aligned_transcripts_dir", DEFAULT_ALIGNED_TRANSCRIPTS_DIR)),
        diarization_segments_dir=_normalize_path(
            output.get("diarization_segments_dir", DEFAULT_DIARIZATION_SEGMENTS_DIR)
        ),
        diarized_words_dir=_normalize_path(output.get("diarized_words_dir", DEFAULT_DIARIZED_WORDS_DIR)),
        identified_words_dir=_normalize_path(output.get("identified_words_dir", DEFAULT_IDENTIFIED_WORDS_DIR)),
        diarized_transcripts_dir=_normalize_path(
            output.get("diarized_transcripts_dir", DEFAULT_DIARIZED_TRANSCRIPTS_DIR)
        ),
        speaker_identification_diagnostics_dir=_normalize_path(
            output.get("speaker_identification_diagnostics_dir", DEFAULT_SPEAKER_IDENTIFICATION_DIAGNOSTICS_DIR)
        ),
        speaker_identification_windows_dir=_normalize_path(
            output.get("speaker_identification_windows_dir", DEFAULT_SPEAKER_IDENTIFICATION_WINDOWS_DIR)
        ),
        cache_dir=_normalize_path(output.get("cache_dir", DEFAULT_CACHE_DIR)),
    )


def get_enrollment_cache_path(paths: PathsSettings | None = None) -> str:
    return project_paths_from_settings(paths or get_paths_settings()).enrollment_cache_path


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
        threshold=float(section.get("threshold", "0.68")),
        margin=float(section.get("margin", "0.05")),
        window_sec=float(section.get("window_sec", "10.0")),
        min_window_sec=float(section.get("min_window_sec", "2.0")),
        min_total_speech_sec=float(section.get("min_total_speech_sec", "4.0")),
        max_windows_per_spk=int(section.get("max_windows_per_spk", "12")),
        save_window_clips=_parse_bool(section.get("save_window_clips", "false"), field_name="matching.save_window_clips"),
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
    Return speaker-label formatting settings for unknown speakers.
    """
    # unknown_prefix may legitimately be empty; default to empty string if missing.
    section = config["speaker"] if "speaker" in config else {}
    unknown_prefix = section.get("unknown_prefix", "").strip()
    return SpeakerSettings(unknown_prefix=unknown_prefix)
