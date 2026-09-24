"""
Transcribe one meeting recording and write "<name> - trascrizione.txt/.json" next to it.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from functools import partial
from pathlib import Path
from typing import Any, Callable

import soundfile as sf

from src.asr.utils.config import WhisperSettings, get_speaker_settings, get_whisper_settings
from src.asr.utils.output_format import format_offset
from src.meeting.transcript import (
    ask_names as ask_names_for,
    build_payload,
    display_labels,
    participant_names,
    rename_labels,
    render_text,
    speaker_summaries,
)
from src.paths import safe_filename_part
from src.utils.logging_setup import format_duration, get_logger


logger = get_logger("meeting")

SAMPLE_RATE = 16000
OUTPUT_SUFFIX = " - trascrizione"
_RULE = "=" * 70
_ALERT = "!" * 70


class MeetingError(Exception):
    """A problem the user can fix, reported in Italian without a traceback."""


def _say(message: str = "") -> None:
    print(message, flush=True)


def output_paths(audio_path: str | os.PathLike[str], out_dir: str | None) -> tuple[Path, Path]:
    source = Path(audio_path)
    folder = Path(out_dir) if out_dir else source.resolve().parent
    return folder / f"{source.stem}{OUTPUT_SUFFIX}.txt", folder / f"{source.stem}{OUTPUT_SUFFIX}.json"


def _cpu_alert(settings: WhisperSettings) -> list[str]:
    return [
        _ALERT,
        f"ATTENZIONE: nessuna GPU disponibile, elaboro su CPU ({settings.compute_type}).",
        "Sarà molto più lento: anche più della durata dell'audio.",
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


def _write_outputs(
    *,
    txt_path: Path,
    json_path: Path,
    source_name: str,
    duration_sec: float,
    settings: WhisperSettings,
    elapsed_sec: float,
    turns: list[dict[str, Any]],
    labels: dict[str, str],
    diagnostics: dict[str, Any],
) -> None:
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(
        render_text(
            source_name=source_name,
            duration_sec=duration_sec,
            device=settings.device,
            fallback_reason=settings.fallback_reason,
            turns=turns,
            labels=labels,
        ),
        encoding="utf-8",
    )
    payload = build_payload(
        source_name=source_name,
        duration_sec=duration_sec,
        device=settings.device,
        compute_type=settings.compute_type,
        fallback_reason=settings.fallback_reason,
        elapsed_sec=elapsed_sec,
        turns=turns,
        labels=labels,
        speakers=speaker_summaries(turns, labels, diagnostics),
    )
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _transcribe(source: Path, *, speakers: int | None, ask_names: bool, out_dir: str | None) -> int:
    started = time.perf_counter()
    settings = get_whisper_settings()

    _say(_RULE)
    _say("Trascrizione riunione")
    _say(f"File: {source.name}")
    for line in _device_lines(settings):
        _say(line)
    _say(f"Persone che parlano: {speakers if speakers else 'rilevamento automatico'}")
    _say(_RULE)

    # Heavy ML imports happen here, after the banner is on screen.
    from src.asr import diarization

    with tempfile.TemporaryDirectory(prefix="meeting-") as work_dir:
        # Decode once to 16 kHz mono WAV: every step rereads the audio, and WAV is cheap to reread.
        work_audio = os.path.join(work_dir, f"{safe_filename_part(source.stem)}.wav")
        try:
            audio = diarization.load_audio(str(source))
        except RuntimeError as exc:
            logger.debug("Audio decoding failed", exc_info=exc)
            raise MeetingError(f"non riesco a leggere l'audio di '{source.name}'. È un file audio o video?") from exc
        duration_sec = len(audio) / SAMPLE_RATE
        sf.write(work_audio, audio, SAMPLE_RATE)
        del audio
        _say(f"Durata audio: {format_offset(duration_sec)}")

        _step(1, "Trascrizione del parlato", diarization.transcribe_audio, work_audio)
        _step(2, "Allineamento delle parole", diarization.align_transcript, work_audio)
        _step(3, "Separazione delle voci", diarization.diarize_transcript, work_audio, num_speakers=speakers)
        _, transcript_path, diagnostics_path = _step(
            4, "Riconoscimento delle voci", diarization.identify_speakers, work_audio
        )
        with open(transcript_path, encoding="utf-8") as f:
            turns = json.load(f)["turns"]
        with open(diagnostics_path, encoding="utf-8") as f:
            diagnostics = json.load(f)

    elapsed_sec = time.perf_counter() - started
    labels = display_labels(turns, get_speaker_settings().unknown_prefix)
    txt_path, json_path = output_paths(source, out_dir)
    write = partial(
        _write_outputs,
        txt_path=txt_path,
        json_path=json_path,
        source_name=source.name,
        duration_sec=duration_sec,
        settings=settings,
        elapsed_sec=elapsed_sec,
        turns=turns,
        diagnostics=diagnostics,
    )
    # Write before asking names, so closing the window mid-prompt loses nothing.
    write(labels=labels)
    if ask_names:
        names = ask_names_for(turns, labels, print_fn=_say)
        if names:
            labels = rename_labels(labels, names)
            write(labels=labels)

    _say("")
    _say(_RULE)
    _say(f"Fatto in {format_duration(elapsed_sec)}.")
    if not turns:
        _say("Nell'audio non ho trovato parlato.")
    _say(f"Partecipanti: {', '.join(participant_names(labels)) or 'nessuno'}")
    _say(f"Accanto all'audio trovi '{txt_path.name}' e '{json_path.name}'.")
    if settings.fallback_reason:
        for line in _cpu_alert(settings):
            _say(line)
    _say(_RULE)
    return 0


def run(audio_path: str, *, speakers: int | None = None, ask_names: bool = False, out_dir: str | None = None) -> int:
    """
    Transcribe one recording end to end; return a process exit code.
    """
    source = Path(audio_path)
    if not source.is_file():
        _say(f"Errore: file non trovato: {audio_path}")
        return 1
    try:
        return _transcribe(source, speakers=speakers, ask_names=ask_names, out_dir=out_dir)
    except KeyboardInterrupt:
        _say("\nInterrotto.")
        return 130
    except MeetingError as exc:
        _say(f"\nErrore: {exc}")
        return 1
    except Exception as exc:
        logger.exception("Meeting transcription failed")
        _say("")
        if _is_out_of_memory(exc):
            _say(
                "Errore: memoria della GPU esaurita. Nella sezione [whisper] di meeting.ini "
                "abbassa batch_size (per esempio a 4, poi 2) e riprova."
            )
        else:
            _say(f"Errore: la trascrizione non è riuscita ({type(exc).__name__}: {exc}).")
        return 1
