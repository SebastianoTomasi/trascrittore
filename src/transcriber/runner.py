"""
Transcribe one recording into a folder of its own, "<name>/<name>-trascrizione.txt/.json", and move the
recording into it as "<name>/<name>.<ext>", where <name> is the recording's name written without spaces.

Nothing here asks a question: naming speakers is a separate command, which Trascrivi.bat
calls after asking the person, and an agent calls with names the person confirmed.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path, PureWindowsPath
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
    UNATTRIBUTED_DISPLAY,
    build_payload,
    display_labels,
    format_minutes,
    is_anonymous,
    render_payload_text,
    speaker_summaries,
)
from src.paths import safe_filename_part, slug
from src.utils.logging_setup import format_duration, get_logger


logger = get_logger("transcriber")

SAMPLE_RATE = 16000
TRANSCRIPT_SUFFIX = "-trascrizione"
COMMAND = "transcribe"
_RULE = "=" * 70
_ALERT = "!" * 70


def _holds_another_recording(folder: Path, name: str, recording: str) -> bool:
    """
    Whether the folder holds a recording called <name>, or the transcript of a recording other than this one.

    A transcript left without its recording, because the person deleted it, is kept; one whose recording
    stayed where it was, because the move failed, is written again.
    """
    if not folder.is_dir():
        return False
    if any(path.is_file() and path.stem == name for path in folder.iterdir()):
        return True
    transcript = folder / f"{name}{TRANSCRIPT_SUFFIX}.json"
    if not transcript.is_file():
        return False
    try:
        return json.loads(transcript.read_text(encoding="utf-8")).get("recording") != recording
    except (OSError, ValueError):
        return True


def transcript_place(recording_path: str | os.PathLike[str], out_dir: str | None) -> tuple[Path, str, Path | None]:
    """
    Return the transcript's folder, the name its files start with, and where the recording moves, if it does.

    A recording already in its transcript's folder, even one an agent renamed, is transcribed there again.
    A folder that already holds another recording of the same name gives way to "<name>-2", "<name>-3"...
    """
    source = Path(os.path.abspath(recording_path))
    name = slug(source.stem)
    if out_dir:
        return Path(out_dir) / name, name, None
    here = source.parent
    # In the container the folder is mounted under another name: its name on the PC is the one to compare.
    if PureWindowsPath(host_path(here)).name == name or (here / f"{name}{TRANSCRIPT_SUFFIX}.json").is_file():
        return here, name, None
    base, count = name, 1
    while _holds_another_recording(here / name, name, host_path(source)):
        count += 1
        name = f"{base}-{count}"
    return here / name, name, here / name / f"{name}{source.suffix.lower()}"


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


def _move_recording(source: Path, destination: Path) -> str | None:
    """
    Move the recording into its transcript's folder; return why it stayed where it was, or None.
    """
    if destination.exists():
        return f"nella cartella c'è già '{destination.name}'"
    try:
        # A rename, never a copy: the folder is next to the recording, and a copy could stay behind.
        os.rename(source, destination)
    except OSError as exc:
        logger.debug("Moving the recording failed", exc_info=exc)
        return "forse è aperta in un altro programma"
    return None


def _stayed(move_problem: str) -> str:
    return f"La registrazione è rimasta dov'era: non ho potuto spostarla nella cartella ({move_problem})."


def _who_spoke(payload: dict[str, Any]) -> list[tuple[str, str]]:
    speakers = [speaker for speaker in payload["speakers"] if speaker["label"] != UNATTRIBUTED_DISPLAY]
    speakers.sort(key=lambda speaker: -speaker["speech_sec"])
    return [(speaker["label"], format_minutes(speaker["speech_sec"])) for speaker in speakers]


def _summary(
    payload: dict[str, Any], txt_path: Path, json_path: Path, *, moved: bool, move_problem: str | None
) -> dict[str, Any]:
    anonymous = [speaker["label"] for speaker in payload["speakers"] if is_anonymous(speaker["label"])]
    who = ", ".join(f"{label} ({minutes})" for label, minutes in _who_spoke(payload)) or "nessuno"
    message = f"Trascrizione completata in {format_duration(payload['elapsed_sec'])}. Chi ha parlato: {who}."
    if anonymous:
        message += f" Senza nome: {', '.join(anonymous)}."
    if move_problem:
        message += f" {_stayed(move_problem)}"
    return {
        "command": COMMAND,
        "status": OK,
        "message": message,
        "folder": host_path(txt_path.parent),
        "recording": payload["recording"],
        "recording_moved": moved,
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
    folder, name, destination = transcript_place(source, out_dir)
    txt_path = folder / f"{name}{TRANSCRIPT_SUFFIX}.txt"
    json_path = folder / f"{name}{TRANSCRIPT_SUFFIX}.json"
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
    # The files exist before the recording moves, and name it where it really is afterwards.
    move_problem = _move_recording(source, destination) if destination else None
    moved = destination is not None and move_problem is None
    if moved:
        payload["file"], payload["recording"] = destination.name, host_path(destination)
        _write_outputs(txt_path, json_path, payload)

    _say("")
    _say(_RULE)
    _say(f"Fatto in {format_duration(elapsed_sec)}.")
    if not turns:
        _say("Nella registrazione non ho trovato parlato.")
    who = _who_spoke(payload)
    _say("Chi ha parlato:" if who else "Chi ha parlato: nessuno.")
    for label, minutes in who:
        _say(f"  - {label}: {minutes}")
    if any(speaker["recognized"] for speaker in payload["speakers"]):
        _say("Se un nome è sbagliato, trascina il file .json su Trascrivi.bat e correggilo.")
    _say(f"Nella cartella {host_path(folder)} trovi '{txt_path.name}' e '{json_path.name}'.")
    if moved:
        _say(f"Ho spostato lì anche la registrazione, come '{destination.name}'.")
    elif move_problem:
        _say(_stayed(move_problem))
    elif source.parent == folder:
        _say("La registrazione è già nella cartella.")
    else:
        _say("La registrazione è rimasta dov'era.")
    if settings.fallback_reason:
        for line in _cpu_alert(settings):
            _say(line)
    _say(_RULE)
    return _summary(payload, txt_path, json_path, moved=moved, move_problem=move_problem)


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
