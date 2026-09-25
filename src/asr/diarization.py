import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import torch
import whisperx

from src.asr.transcript_cleaning import clean_transcript_turns
from src.asr.utils.config import (
    ensure_data_directories,
    get_diarization_settings,
    get_whisper_settings,
    get_paths_settings,
    get_matching_settings,
    get_voiceprint_settings,
)
from src.asr.voiceprints import load_voiceprint_model
from src.asr.utils.diarization_utils import (
    diarization_to_dataframe,
    speaker_voiceprints_from_diarization_with_diagnostics,
    match_speakers_to_names_with_diagnostics,
    relabel_whisperx_segments,
)
from src.paths import file_stem, project_paths_from_settings, safe_filename_part
from src.utils.logging_setup import get_logger, log_event


logger = get_logger("asr.diarization")
_whisper_settings = get_whisper_settings()
_diarization_settings = get_diarization_settings()
_paths_settings = get_paths_settings()
_matching_settings = get_matching_settings()
_voiceprint_settings = get_voiceprint_settings()

device = _whisper_settings.device
compute_type = _whisper_settings.compute_type
batch_size = _whisper_settings.batch_size
whisper_model_id = _whisper_settings.model_id
whisper_language = _whisper_settings.language
whisper_initial_prompt = _whisper_settings.initial_prompt
vad_onset = _whisper_settings.vad_onset
vad_offset = _whisper_settings.vad_offset
vad_chunk_size = _whisper_settings.vad_chunk_size
min_speakers = _diarization_settings.min_speakers
max_speakers = _diarization_settings.max_speakers

sample_rate_default = _voiceprint_settings.sample_rate

DIARIZED_TRANSCRIPTS_DIR = _paths_settings.diarized_transcripts_dir
matching_threshold_default = _matching_settings.threshold


def _get_configured_input_path(input_path: str | None = None) -> str:
    if input_path is not None:
        cleaned = input_path.strip()
        if not cleaned:
            raise RuntimeError("input_path must not be empty.")
        return cleaned

    configured_input_path = _paths_settings.input_path.strip()
    if not configured_input_path:
        raise RuntimeError("paths.input_path must be set in the config.")
    return configured_input_path


def _validate_recording(input_path: str) -> None:
    if not os.path.isfile(input_path):
        raise RuntimeError(f"Input audio file not found: {input_path}")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def save_json_artifact(payload: Any, out_path: str) -> str:
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_json_default)
    return out_path


def load_json_artifact(path: str, *, description: str) -> Any:
    if not os.path.isfile(path):
        raise RuntimeError(f"Missing {description}: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _raw_diarization_records(diarize_df: Any) -> list[dict[str, Any]]:
    df = diarization_to_dataframe(diarize_df)
    return [
        {
            "speaker": str(row["speaker"]),
            "start": float(row["start"]),
            "end": float(row["end"]),
            "duration_sec": float(row["end"] - row["start"]),
        }
        for _, row in df.iterrows()
    ]


def _merge_recognition_diagnostics(
    *,
    threshold: float,
    library_voiceprints: dict[str, list[np.ndarray]] | None,
    voiceprint_diagnostics: dict[str, Any],
    match_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    speakers: dict[str, Any] = {}
    voiceprint_speakers = voiceprint_diagnostics.get("speakers", {})
    match_speakers = match_diagnostics.get("speakers", {})
    for speaker in sorted(set(voiceprint_speakers) | set(match_speakers)):
        speakers[speaker] = {
            **voiceprint_speakers.get(speaker, {}),
            **match_speakers.get(speaker, {}),
        }

    return {
        "library_people": sorted(library_voiceprints.keys()) if library_voiceprints else [],
        "settings": {
            "threshold": float(threshold),
            "margin": _matching_settings.margin,
            "window_sec": _matching_settings.window_sec,
            "min_window_sec": _matching_settings.min_window_sec,
            "min_total_speech_sec": _matching_settings.min_total_speech_sec,
            "max_windows_per_spk": _matching_settings.max_windows_per_spk,
            "score_reducer": "max_pairwise",
            "save_window_clips": _matching_settings.save_window_clips,
        },
        "speakers": speakers,
    }


def save_speaker_recognition_diagnostics(
    diagnostics: dict[str, Any],
    input_path: str,
) -> str:
    project_paths = project_paths_from_settings(_paths_settings)
    out_path = project_paths.speaker_recognition_diagnostics_path(input_path)
    return save_json_artifact(diagnostics, out_path)


def _clear_speaker_recognition_window_clips(input_path: str) -> None:
    project_paths = project_paths_from_settings(_paths_settings)
    windows_dir = Path(project_paths.speaker_recognition_windows_dir)
    if not windows_dir.exists():
        return
    stem = safe_filename_part(file_stem(input_path))
    for clip_path in windows_dir.glob(f"{stem}_clip_*.wav"):
        if clip_path.is_file():
            clip_path.unlink()


def _clear_cuda_cache_if_needed() -> None:
    """
    Release CUDA cached memory only when a CUDA device is active.
    """
    if str(device).startswith("cuda") and torch.cuda.is_available():
        torch.cuda.empty_cache()


def filter_obvious_noise(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Remove turns that are clearly ASR noise / filler while preserving all
    plausibly meaningful speech.  Intentionally lenient — strict filtering
    for specific downstream tasks (e.g. health extraction) happens later.
    """
    return clean_transcript_turns(turns)

def save_diarized_transcript(
    mapping: dict[str, str],
    result: dict[str, Any],
    input_path: str,
    out_dir: str = DIARIZED_TRANSCRIPTS_DIR,
) -> str:
    """
    Persist the diarized transcript as a JSON file with one entry per speaker turn.
    """
    from src.asr.utils.output_format import _parse_recording_start, build_transcript_turns

    recording_start = _parse_recording_start(input_path)
    transcript = {
        "date": recording_start.strftime("%Y-%m-%d") if recording_start else None,
        "turns": build_transcript_turns(result, input_path, mapping),
    }

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(input_path))[0]
    out_path = os.path.join(out_dir, f"{stem}.json")
    return save_json_artifact(transcript, out_path)


def save_raw_asr_result(asr_result: dict[str, Any], input_path: str) -> str:
    project_paths = project_paths_from_settings(_paths_settings)
    return save_json_artifact(asr_result, project_paths.raw_asr_path(input_path))


def load_raw_asr_result(input_path: str) -> dict[str, Any]:
    project_paths = project_paths_from_settings(_paths_settings)
    return load_json_artifact(project_paths.raw_asr_path(input_path), description="raw ASR artifact")


def save_aligned_transcript(aligned_result: dict[str, Any], input_path: str) -> str:
    project_paths = project_paths_from_settings(_paths_settings)
    return save_json_artifact(aligned_result, project_paths.aligned_transcript_path(input_path))


def load_aligned_transcript(input_path: str) -> dict[str, Any]:
    project_paths = project_paths_from_settings(_paths_settings)
    return load_json_artifact(project_paths.aligned_transcript_path(input_path), description="aligned transcript artifact")


def save_diarization_segments(diarize_df: Any, input_path: str) -> str:
    project_paths = project_paths_from_settings(_paths_settings)
    return save_json_artifact(_raw_diarization_records(diarize_df), project_paths.diarization_segments_path(input_path))


def load_diarization_segments(input_path: str) -> list[dict[str, Any]]:
    project_paths = project_paths_from_settings(_paths_settings)
    segments = load_json_artifact(
        project_paths.diarization_segments_path(input_path),
        description="raw diarization segments artifact",
    )
    if not isinstance(segments, list):
        raise RuntimeError(
            f"Invalid raw diarization segments artifact: {project_paths.diarization_segments_path(input_path)}"
        )
    return segments


def save_diarized_words(diarized_result: dict[str, Any], input_path: str) -> str:
    project_paths = project_paths_from_settings(_paths_settings)
    return save_json_artifact(diarized_result, project_paths.diarized_words_path(input_path))


def load_diarized_words(input_path: str) -> dict[str, Any]:
    project_paths = project_paths_from_settings(_paths_settings)
    return load_json_artifact(project_paths.diarized_words_path(input_path), description="diarized words artifact")


def save_recognized_words(recognized_result: dict[str, Any], input_path: str) -> str:
    project_paths = project_paths_from_settings(_paths_settings)
    return save_json_artifact(recognized_result, project_paths.recognized_words_path(input_path))


def load_recognized_words(input_path: str) -> dict[str, Any]:
    project_paths = project_paths_from_settings(_paths_settings)
    return load_json_artifact(project_paths.recognized_words_path(input_path), description="recognized words artifact")


def load_audio(recording_path: str) -> np.ndarray:
    """Load an audio file into a NumPy array via WhisperX."""
    try:
        return whisperx.load_audio(recording_path)
    except Exception as exc:  # pragma: no cover - depends on backend decoder errors
        raise RuntimeError(f"Failed to load input audio '{recording_path}'.") from exc


def transcribe(audio: np.ndarray) -> dict:
    """Run Whisper ASR on pre-loaded audio and return the raw result dict."""
    model = None
    try:
        log_event(
            logger,
            "Whisper transcription started",
            level=logging.DEBUG,
        )
        asr_options = {"initial_prompt": whisper_initial_prompt} if whisper_initial_prompt else None
        # CTranslate2 defaults to 4 CPU threads; use every core when there is no GPU.
        cpu_threads = (os.cpu_count() or 4) if device == "cpu" else 4
        model = whisperx.load_model(
            whisper_model_id,
            device,
            compute_type=compute_type,
            threads=cpu_threads,
            language=whisper_language,
            asr_options=asr_options,
            vad_method="pyannote",
            vad_options={"vad_onset": vad_onset, "vad_offset": vad_offset, "chunk_size": vad_chunk_size},
        )
        with torch.inference_mode():
            result = model.transcribe(audio, batch_size=batch_size)
        log_event(
            logger,
            "Whisper transcription completed",
            level=logging.DEBUG,
            language=result.get("language"),
            segment_count=len(result.get("segments", [])),
        )
    finally:
        if model is not None:
            del model
        _clear_cuda_cache_if_needed()
    return result


def align(audio: np.ndarray, asr_result: dict) -> dict:
    """Align ASR segments to word-level timestamps."""
    language = asr_result.get("language")
    if not language:
        raise RuntimeError("Whisper transcription did not return a language; cannot run alignment.")

    align_model = None
    try:
        log_event(logger, "WhisperX alignment started", level=logging.DEBUG, language=language)
        align_model, metadata = whisperx.load_align_model(language, device=device)
        with torch.inference_mode():
            result = whisperx.align(asr_result.get("segments", []), align_model, metadata, audio, device)
        log_event(logger, "WhisperX alignment completed", level=logging.DEBUG, language=language)
    finally:
        if align_model is not None:
            del align_model
        _clear_cuda_cache_if_needed()
    return result


def run_diarization(
    audio: np.ndarray,
    aligned_result: dict,
    num_speakers: int | None = None,
) -> tuple[dict, Any]:
    """
    Assign speaker labels to aligned segments. Returns (result, diarize_df).

    An exact `num_speakers` overrides the configured min/max bounds.
    """
    from whisperx.diarize import DiarizationPipeline

    hf_token = os.getenv("HF_TOKEN")
    diarize_model = None
    try:
        log_event(
            logger,
            "speaker diarization started",
            level=logging.DEBUG,
        )
        diarize_model = DiarizationPipeline(token=hf_token, device=device)
        if num_speakers is not None:
            diarize_output = diarize_model(audio, num_speakers=num_speakers)
        else:
            diarize_output = diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)
        diarize_df = diarization_to_dataframe(diarize_output)
        result = whisperx.assign_word_speakers(diarize_df, aligned_result)
        log_event(logger, "speaker diarization completed", level=logging.DEBUG, turn_count=len(diarize_df))
    finally:
        if diarize_model is not None:
            del diarize_model
        _clear_cuda_cache_if_needed()
    return result, diarize_df


def transcribe_recording(input_path: str | None = None) -> str:
    input_path = _get_configured_input_path(input_path)
    ensure_data_directories(_paths_settings)
    _validate_recording(input_path)
    audio = load_audio(input_path)
    asr_result = transcribe(audio)
    return save_raw_asr_result(asr_result, input_path)


def align_transcript(input_path: str | None = None) -> str:
    input_path = _get_configured_input_path(input_path)
    ensure_data_directories(_paths_settings)
    _validate_recording(input_path)
    audio = load_audio(input_path)
    asr_result = load_raw_asr_result(input_path)
    aligned_result = align(audio, asr_result)
    return save_aligned_transcript(aligned_result, input_path)


def diarize_transcript(input_path: str | None = None, num_speakers: int | None = None) -> tuple[str, str]:
    input_path = _get_configured_input_path(input_path)
    ensure_data_directories(_paths_settings)
    _validate_recording(input_path)
    audio = load_audio(input_path)
    aligned_result = load_aligned_transcript(input_path)
    diarized_result, diarize_df = run_diarization(audio, aligned_result, num_speakers=num_speakers)
    segments_path = save_diarization_segments(diarize_df, input_path)
    diarized_words_path = save_diarized_words(diarized_result, input_path)
    return segments_path, diarized_words_path


def recognize_speakers(
    input_path: str | None = None,
    threshold: float | None = None,
) -> tuple[str, str, str]:
    input_path = _get_configured_input_path(input_path)
    ensure_data_directories(_paths_settings)
    _validate_recording(input_path)
    threshold = matching_threshold_default if threshold is None else threshold
    diarization_segments = load_diarization_segments(input_path)
    diarize_df = diarization_to_dataframe(diarization_segments)
    diarized_result = load_diarized_words(input_path)
    mapping, recognized_result, diagnostics_path = _recognize_speakers_in_diarized_result(
        input_path,
        diarize_df,
        diarized_result,
        threshold=threshold,
    )
    recognized_words_path = save_recognized_words(recognized_result, input_path)
    transcript_path = save_diarized_transcript({}, recognized_result, input_path)
    log_event(
        logger,
        "speaker recognition artifacts saved",
        level=logging.DEBUG,
        speaker_count=len(mapping),
        recognized_words_path=recognized_words_path,
        transcript_path=transcript_path,
        diagnostics_path=diagnostics_path,
    )
    return recognized_words_path, transcript_path, diagnostics_path


def _recognize_speakers_in_diarized_result(
    recording_path: str,
    diarize_df: Any,
    result: dict,
    threshold: float = matching_threshold_default,
) -> tuple[dict[str, str], dict, str]:
    """Match diarized speakers against the people in the voice library and relabel segments."""
    from src.asr.voice_library import load_library_voiceprints

    mapping: dict[str, str] = {}
    project_paths = project_paths_from_settings(_paths_settings)
    diagnostics_path = project_paths.speaker_recognition_diagnostics_path(recording_path)
    _clear_speaker_recognition_window_clips(recording_path)
    library_voiceprints = load_library_voiceprints(device)
    if library_voiceprints is None:
        raw_diarization = _raw_diarization_records(diarize_df)
        diarized_speakers = list(dict.fromkeys(record["speaker"] for record in raw_diarization))
        # Nobody to recognize, but the windows are still recorded: naming a speaker later cuts clips from them.
        window_result = speaker_voiceprints_from_diarization_with_diagnostics(
            None,
            recording_path,
            diarize_df,
            device=device,
            window_sec=_matching_settings.window_sec,
            min_window_sec=_matching_settings.min_window_sec,
            min_total_speech_sec=_matching_settings.min_total_speech_sec,
            max_windows_per_spk=_matching_settings.max_windows_per_spk,
        )
        match_result = match_speakers_to_names_with_diagnostics(
            {},
            {},
            threshold=threshold,
            margin=_matching_settings.margin,
            diarized_speakers=diarized_speakers,
            voiceprint_rejection_reasons={speaker: "voice_library_empty" for speaker in diarized_speakers},
        )
        mapping = match_result.mapping
        result = relabel_whisperx_segments(result, mapping)
        diagnostics = _merge_recognition_diagnostics(
            threshold=threshold,
            library_voiceprints=None,
            voiceprint_diagnostics=window_result.diagnostics,
            match_diagnostics=match_result.diagnostics,
        )
        diagnostics_path = save_speaker_recognition_diagnostics(diagnostics, recording_path)
    else:
        voiceprint_model = None
        try:
            log_event(
                logger,
                "speaker recognition started",
                level=logging.DEBUG,
                library_person_count=len(library_voiceprints),
            )
            voiceprint_model = load_voiceprint_model(device)

            voiceprint_result = speaker_voiceprints_from_diarization_with_diagnostics(
                voiceprint_model,
                recording_path,
                diarize_df,
                device=device,
                window_sec=_matching_settings.window_sec,
                min_window_sec=_matching_settings.min_window_sec,
                min_total_speech_sec=_matching_settings.min_total_speech_sec,
                max_windows_per_spk=_matching_settings.max_windows_per_spk,
                diagnostics_clip_path_factory=(
                    lambda clip_index, speaker, duration_sec: project_paths.speaker_recognition_window_clip_path(
                        recording_path,
                        clip_index,
                        speaker,
                        duration_sec,
                    )
                    if _matching_settings.save_window_clips
                    else None
                ),
                sample_rate=sample_rate_default,
            )
            speaker_voiceprints = voiceprint_result.voiceprints
            voiceprint_rejection_reasons = {
                speaker: str(speaker_diag["voiceprint_rejection_reason"])
                for speaker, speaker_diag in voiceprint_result.diagnostics.get("speakers", {}).items()
                if speaker_diag.get("voiceprint_rejection_reason")
            }

            match_result = match_speakers_to_names_with_diagnostics(
                speaker_voiceprints,
                library_voiceprints,
                threshold=threshold,
                margin=_matching_settings.margin,
                diarized_speakers=list(voiceprint_result.diagnostics.get("speakers", {}).keys()),
                voiceprint_rejection_reasons=voiceprint_rejection_reasons,
            )
            mapping = match_result.mapping
            result = relabel_whisperx_segments(result, mapping)
            diagnostics = _merge_recognition_diagnostics(
                threshold=threshold,
                library_voiceprints=library_voiceprints,
                voiceprint_diagnostics=voiceprint_result.diagnostics,
                match_diagnostics=match_result.diagnostics,
            )
            diagnostics_path = save_speaker_recognition_diagnostics(diagnostics, recording_path)
            log_event(
                logger,
                "speaker recognition completed",
                level=logging.DEBUG,
                diarized_speaker_count=len(speaker_voiceprints),
                matched_speaker_count=len(mapping),
                diagnostics_path=diagnostics_path,
            )
        finally:
            if voiceprint_model is not None:
                del voiceprint_model
            _clear_cuda_cache_if_needed()

    return mapping, result, diagnostics_path
