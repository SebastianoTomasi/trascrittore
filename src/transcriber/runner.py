"""
Transcribe one recording and write "<name> - trascrizione.txt/.json" next to it.

Nothing here asks a question: naming speakers is a separate command, which Trascrivi.bat
calls after asking the person, and an agent calls with names the person confirmed.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import soundfile as sf

from src.asr.utils.config import WhisperSettings, get_speaker_settings, get_whisper_settings
from src.asr.utils.output_format import format_offset
from src.transcriber.summary import (
    FILE_NOT_FOUND,
    GPU_OUT_OF_MEMORY,
    OK,
    UNREADABLE_RECORDING,
    CommandError,
    guarded,
    host_path,
    say as _say,
)
from src.transcriber.transcript import (
    build_payload,
    display_labels,
    is_anonymous,
    speaker_names,
    render_payload_text,
    speaker_summaries,
)
from src.paths import safe_filename_part
from src.utils.logging_setup import format_duration, get_logger


logger = get_logger("transcriber")

SAMPLE_RATE = 16000
OUTPUT_SUFFIX = " - trascrizione"
COMMAND = "transcribe"
_RULE = "=" * 70
_ALERT = "!" * 70


def output_paths(recording_path: str | os.PathLike[str], out_dir: str | None) -> tuple[Path, Path]:
    source = Path(recording_path)
    folder = Path(out_dir) if out_dir else source.resolve().parent
    return folder / f"{source.stem}{OUTPUT_SUFFIX}.txt", folder / f"{source.stem}{OUTPUT_SUFFIX}.json"


def _cpu_alert(settings: WhisperSettings) -> list[str]:
    return [
        _ALERT,
        f"ATTENZIONE: nessuna GPU disponibile, elaboro su CPU ({settings.compute_type}).",
        "Sarà molto più lento: anche più della durata della registrazione.",
        f"Motivo: {settings.fallback_reason}",
        _ALERT,
    ]


def _device_lines(settings: WhisperSettings) -> list[str]:
    if settings.device.startswith("cuda"):
        return [f"Dispositivo: GPU NVIDIA ({settings.compute_type})"]
    if settings.fallback_reason:
        return _cpu_alert(settings)
    return [f"Dispositivo: CPU ({settings.compute_type})"]


def _step(index: int, title: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    _say(f"[{index}/4] {title}...")
    started = time.perf_counter()
    result = fn(*args, **kwargs)
    _say(f"      fatto in {format_duration(time.perf_counter() - started)}")
    return result


def _is_out_of_memory(exc: BaseException) -> bool:
    import torch

    # CTranslate2 reports CUDA OOM as a plain RuntimeError.
    return isinstance(exc, torch.OutOfMemoryError) or "out of memory" in str(exc).lower()


def _write_outputs(txt_path: Path, json_path: Path, payload: dict[str, Any]) -> None:
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(render_payload_text(payload), encoding="utf-8")


def _summary(payload: dict[str, Any], txt_path: Path, json_path: Path) -> dict[str, Any]:
    anonymous = [speaker["label"] for speaker in payload["speakers"] if is_anonymous(speaker["label"])]
    message = f"Trascrizione completata in {format_duration(payload['elapsed_sec'])}."
    if anonymous:
        message += f" Senza nome: {', '.join(anonymous)}."
    return {
        "command": COMMAND,
        "status": OK,
        "message": message,
        "recording": payload["recording"],
        "transcript_txt": host_path(txt_path),
        "transcript_json": host_path(json_path),
        "duration_sec": payload["duration_sec"],
        "elapsed_sec": payload["elapsed_sec"],
        "device": payload["device"],
        "compute_type": payload["compute_type"],
        "warnings": payload["warnings"],
        "speakers": [
            {"label": speaker["label"], "recognized": speaker["recognized"], "speech_sec": speaker["speech_sec"]}
            for speaker in payload["speakers"]
        ],
    }


def _transcribe(source: Path, *, speakers: int | None, out_dir: str | None) -> dict[str, Any]:
    started = time.perf_counter()
    settings = get_whisper_settings()

    _say(_RULE)
    _say("Trascrizione")
    _say(f"File: {source.name}")
    for line in _device_lines(settings):
        _say(line)
    _say(f"Persone che parlano: {speakers if speakers else 'rilevamento automatico'}")
    _say(_RULE)

    # Heavy ML imports happen here, after the banner is on screen.
    from src.asr import diarization

    with tempfile.TemporaryDirectory(prefix="trascrittore-") as work_dir:
        # Decode once to 16 kHz mono WAV: every step rereads the audio, and WAV is cheap to reread.
        work_copy = os.path.join(work_dir, f"{safe_filename_part(source.stem)}.wav")
        try:
            audio = diarization.load_audio(str(source))
        except RuntimeError as exc:
            logger.debug("Decoding the recording failed", exc_info=exc)
            raise CommandError(
                UNREADABLE_RECORDING, f"Non riesco a leggere la registrazione '{source.name}'. È un file audio o video?"
            ) from exc
        duration_sec = len(audio) / SAMPLE_RATE
        sf.write(work_copy, audio, SAMPLE_RATE)
        del audio
        _say(f"Durata: {format_offset(duration_sec)}")

        _step(1, "Trascrizione del parlato", diarization.transcribe_recording, work_copy)
        _step(2, "Allineamento delle parole", diarization.align_transcript, work_copy)
        _step(3, "Separazione delle voci", diarization.diarize_transcript, work_copy, num_speakers=speakers)
        _, transcript_path, diagnostics_path = _step(
            4, "Riconoscimento delle voci", diarization.recognize_speakers, work_copy
        )
        with open(transcript_path, encoding="utf-8") as f:
            turns = json.load(f)["turns"]
        with open(diagnostics_path, encoding="utf-8") as f:
            diagnostics = json.load(f)

    elapsed_sec = time.perf_counter() - started
    labels = display_labels(turns, get_speaker_settings().anonymous_prefix)
    txt_path, json_path = output_paths(source, out_dir)
    payload = build_payload(
        source_name=source.name,
        recording=host_path(source),
        duration_sec=duration_sec,
        device=settings.device,
        compute_type=settings.compute_type,
        fallback_reason=settings.fallback_reason,
        elapsed_sec=elapsed_sec,
        turns=turns,
        labels=labels,
        speakers=speaker_summaries(turns, labels, diagnostics),
    )
    _write_outputs(txt_path, json_path, payload)

    _say("")
    _say(_RULE)
    _say(f"Fatto in {format_duration(elapsed_sec)}.")
    if not turns:
        _say("Nella registrazione non ho trovato parlato.")
    _say(f"Chi parla: {', '.join(speaker_names(labels)) or 'nessuno'}")
    _say(f"Accanto alla registrazione trovi '{txt_path.name}' e '{json_path.name}'.")
    if settings.fallback_reason:
        for line in _cpu_alert(settings):
            _say(line)
    _say(_RULE)
    return _summary(payload, txt_path, json_path)


def _transcribe_or_explain(source: Path, *, speakers: int | None, out_dir: str | None) -> dict[str, Any]:
    if not source.is_file():
        raise CommandError(FILE_NOT_FOUND, f"File non trovato: {host_path(source)}")
    try:
        return _transcribe(source, speakers=speakers, out_dir=out_dir)
    except Exception as exc:
        if not _is_out_of_memory(exc):
            raise
        logger.debug("GPU out of memory", exc_info=exc)
        raise CommandError(
            GPU_OUT_OF_MEMORY,
            "Memoria della GPU esaurita. In trascrittore.ini, accanto a Trascrivi.bat, scrivi "
            "batch_size = 4 sotto la riga [whisper] (poi 2, se non basta) e riprova.",
        ) from exc


def run(recording_path: str, *, speakers: int | None = None, out_dir: str | None = None) -> dict[str, Any]:
    """
    Transcribe one recording end to end; return the result summary.
    """
    return guarded(
        COMMAND,
        lambda: _transcribe_or_explain(Path(recording_path), speakers=speakers, out_dir=out_dir),
        failed="La trascrizione non è riuscita",
    )
