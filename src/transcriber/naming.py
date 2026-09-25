"""
Naming speakers after the transcript exists, and preparing the clips a person listens to first.

Only a person gives a name: an agent calls these commands with names the person confirmed or
wrote. Naming never transcribes again. It rewrites both transcript files from the JSON file,
and cuts clips of each named speaker from the recording into the PC's voice library.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from src.asr.utils.config import get_library_settings, get_matching_settings
from src.transcriber import library, voices
from src.transcriber.summary import FILE_NOT_FOUND, INVALID_ARGUMENTS, OK, CommandError, guarded, host_path, say
from src.transcriber.transcript import is_anonymous, rename_speakers, render_payload_text, speaker_labels


NAME_COMMAND = "name"
LISTEN_COMMAND = "listen"
LISTEN_PREFIX = "ascolta "
# Silence between the clips joined in one listening file.
_LISTEN_GAP_SEC = 0.7
# The transcript stores the duration rounded to a tenth of a second.
_DURATION_TOLERANCE_SEC = 1.0


def parse_pairs(pairs: list[str]) -> dict[str, str]:
    """
    Read "Persona 2=Luca Bianchi" pairs into {label: name}.
    """
    names: dict[str, str] = {}
    for pair in pairs:
        label, separator, name = pair.partition("=")
        label, name = " ".join(label.split()), " ".join(name.split())
        if not separator or not label or not name:
            raise CommandError(INVALID_ARGUMENTS, f"'{pair}' non è nella forma \"Persona 2=Nome Cognome\".")
        if label in names:
            raise CommandError(INVALID_ARGUMENTS, f"'{label}' compare due volte.")
        names[label] = name
    if not names:
        raise CommandError(INVALID_ARGUMENTS, "Indica almeno una voce da nominare, per esempio \"Persona 2=Nome Cognome\".")
    return names


def load_transcript(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CommandError(FILE_NOT_FOUND, f"Trascrizione non trovata: {host_path(path)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None
    if not isinstance(payload, dict) or "turns" not in payload or "file" not in payload:
        raise CommandError(INVALID_ARGUMENTS, f"'{path.name}' non è il file .json di una trascrizione.")
    return payload


def _check_labels(payload: dict[str, Any], labels: list[str]) -> None:
    known = speaker_labels(payload)
    anonymous = [label for label in known if is_anonymous(label)]
    for label in labels:
        if label not in known:
            raise CommandError(
                INVALID_ARGUMENTS,
                f"'{label}' non è una voce di questa trascrizione. Voci senza nome: {', '.join(anonymous) or 'nessuna'}.",
            )
        if not is_anonymous(label):
            raise CommandError(INVALID_ARGUMENTS, f"'{label}' ha già un nome: si possono nominare solo le voci 'Persona N'.")


def _resolve_recording(payload: dict[str, Any], transcript: Path, recording: str | None) -> Path | None:
    """
    Find the recording: the one given, the one the transcript names, or the file beside the transcript.
    """
    if recording:
        candidates = [Path(recording)]
    else:
        candidates = [Path(payload["recording"])] if payload.get("recording") else []
        candidates.append(transcript.parent / payload["file"])
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def open_recording(
    payload: dict[str, Any], transcript: Path, recording: str | None
) -> tuple[np.ndarray | None, str | None]:
    """
    Return the recording's audio, or why no clips can be cut from it.
    """
    path = _resolve_recording(payload, transcript, recording)
    if path is None:
        where = host_path(recording) if recording else payload.get("recording") or payload["file"]
        return None, f"Registrazione non trovata ({where}): indica dove si trova adesso."
    try:
        audio = voices.load_recording(path)
    except RuntimeError:
        return None, f"Non riesco a leggere la registrazione {host_path(path)}."
    if abs(len(audio) / voices.SAMPLE_RATE - float(payload["duration_sec"])) > _DURATION_TOLERANCE_SEC:
        return None, f"La registrazione {host_path(path)} non corrisponde alla trascrizione: ha un'altra durata."
    return audio, None


def _speaker_windows(payload: dict[str, Any], label: str) -> list[dict[str, float]] | None:
    for speaker in payload.get("speakers", []):
        if speaker["label"] == label:
            return speaker.get("windows")
    return None


def _candidates(
    payload: dict[str, Any], label: str, audio: np.ndarray, voiceprints: voices.Voiceprints
) -> tuple[list[library.Candidate], str | None]:
    """
    Rank the speaker's windows as clips, best first, or say why there are none.
    """
    windows = _speaker_windows(payload, label)
    if windows is None:
        return [], (
            "La trascrizione è di una versione precedente, che non salvava i tratti di ogni voce: "
            "per aggiungere la voce alla libreria, trascrivi di nuovo la registrazione e dalle il nome lì."
        )
    if not windows:
        return [], "Questa voce parla troppo poco da sola per ricavarne clip."
    window_sec = get_matching_settings().window_sec
    candidates = library.select_clips(
        windows,
        voiceprints.of_windows(audio, windows),
        window_sec=window_sec,
        selection=get_library_settings(),
    )
    if not candidates:
        return [], f"Questa voce non ha tratti di {window_sec:g} secondi pieni da cui ricavare clip."
    return candidates, None


def _grow_library(
    payload: dict[str, Any],
    transcript: Path,
    names: dict[str, str],
    recording: str | None,
    library_dir: Path | None,
) -> list[dict[str, Any]]:
    results = [
        {"label": label, "name": name, "clips_added": 0, "folder": None, "note": None} for label, name in names.items()
    ]
    if library_dir is None:
        for result in results:
            result["note"] = "La libreria delle voci non è configurata."
        return results

    audio, problem = open_recording(payload, transcript, recording)
    if audio is None:
        for result in results:
            result["note"] = problem
        return results

    selection = get_library_settings()
    trial = not library.trial_passed(library_dir, selection)
    voiceprints = voices.Voiceprints()
    for result in results:
        candidates, result["note"] = _candidates(payload, result["label"], audio, voiceprints)
        if not candidates:
            continue
        saved = library.save_clips(
            library_dir,
            result["name"],
            audio,
            candidates,
            trial=trial,
            selection=selection,
            origin={
                "recording": payload.get("recording"),
                "recording_file": payload["file"],
                "recording_duration_sec": payload["duration_sec"],
                "transcript": host_path(transcript),
                "label": result["label"],
            },
        )
        result["clips_added"] = len(saved)
        result["folder"] = host_path(library.clips_folder(library_dir, result["name"]))
    return results


def _write_transcript(transcript: Path, payload: dict[str, Any]) -> Path:
    text_path = transcript.with_suffix(".txt")
    transcript.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(render_payload_text(payload), encoding="utf-8")
    return text_path


def _naming_lines(results: list[dict[str, Any]], trial: dict[str, Any] | None) -> list[str]:
    lines = []
    for result in results:
        line = f"{result['label']} → {result['name']}: "
        if result["clips_added"]:
            line += f"{result['clips_added']} clip aggiunte alla libreria delle voci, in {result['folder']}."
            if result["note"]:
                line += f" {result['note']}"
        else:
            line += f"nessuna clip aggiunta. {result['note']}"
        lines.append(line)
    if trial and not trial["passed"] and any(result["clips_added"] for result in results):
        lines.append(
            "Periodo di prova della selezione delle clip: ascolta le clip aggiunte e cancella quelle con altre "
            f"voci, risate o rumori. Voci nominate finora: {trial['named_speakers']} su {trial['needed']}."
        )
    return lines


def _name_speakers(transcript: str, pairs: list[str], recording: str | None) -> dict[str, Any]:
    written = parse_pairs(pairs)
    transcript_path = Path(transcript)
    payload = load_transcript(transcript_path)
    _check_labels(payload, list(written))
    for name in written.values():
        problem = library.name_problem(name)
        if problem:
            raise CommandError(INVALID_ARGUMENTS, problem)
    library_dir = library.library_dir()
    names = dict(written)
    if library_dir is not None:
        names = {label: library.canonical_name(library_dir, name) for label, name in written.items()}

    # Clips first: if rewriting the transcript then fails, the labels are still there and naming can be
    # repeated, and the clips it saves again replace the same files.
    results = _grow_library(payload, transcript_path, names, recording, library_dir)
    for result in results:
        if result["name"] != written[result["label"]]:
            already = f"Nella libreria c'è già '{result['name']}': uso quel nome."
            result["note"] = f"{already} {result['note']}" if result["note"] else already
    text_path = _write_transcript(transcript_path, rename_speakers(payload, names))
    trial = None
    if library_dir is not None:
        status = library.trial_status(library_dir, get_library_settings())
        trial = {"passed": status.passed, "named_speakers": status.named_speakers, "needed": library.TRIAL_NAMED_SPEAKERS}

    lines = _naming_lines(results, trial)
    for line in lines:
        say(line)
    return {
        "command": NAME_COMMAND,
        "status": OK,
        "message": " ".join(["Nomi applicati alla trascrizione.", *lines]),
        "transcript_txt": host_path(text_path),
        "transcript_json": host_path(transcript_path),
        "named": results,
        "trial": trial,
    }


def name_speakers(transcript: str, pairs: list[str], *, recording: str | None = None) -> dict[str, Any]:
    """
    Apply names confirmed by a person to a transcript, and add the named speakers' clips to the voice library.
    """
    return guarded(
        NAME_COMMAND,
        lambda: _name_speakers(transcript, pairs, recording),
        failed="Non sono riuscito a dare i nomi",
    )


def _clear_listening_clips(out_dir: Path) -> None:
    for path in out_dir.glob(f"{LISTEN_PREFIX}*.wav"):
        try:
            path.unlink()
        except OSError:
            # Still open in the player: the new file of that speaker replaces it.
            pass


def _prepare_listening(transcript: str, labels: list[str], recording: str | None, out_dir: str | None) -> dict[str, Any]:
    labels = [" ".join(label.split()) for label in labels]
    if not labels:
        raise CommandError(INVALID_ARGUMENTS, "Indica almeno una voce da ascoltare, per esempio \"Persona 2\".")
    transcript_path = Path(transcript)
    payload = load_transcript(transcript_path)
    _check_labels(payload, labels)
    folder = Path(out_dir) if out_dir else Path(tempfile.gettempdir()) / "trascrittore-ascolto"
    folder.mkdir(parents=True, exist_ok=True)
    _clear_listening_clips(folder)

    speakers = [{"label": label, "file": None, "clips": 0, "note": None} for label in labels]
    audio, problem = open_recording(payload, transcript_path, recording)
    voiceprints = voices.Voiceprints()
    gap = np.zeros(int(_LISTEN_GAP_SEC * voices.SAMPLE_RATE), dtype=np.float32)
    for speaker in speakers:
        if audio is None:
            speaker["note"] = problem
            continue
        candidates, speaker["note"] = _candidates(payload, speaker["label"], audio, voiceprints)
        best = candidates[: library.LISTENING_CLIPS]
        if not best:
            continue
        pieces = []
        for candidate in best:
            pieces += [voices.cut(audio, candidate.start, candidate.end), gap]
        path = folder / f"{LISTEN_PREFIX}{speaker['label']}.wav"
        sf.write(path, np.concatenate(pieces[:-1]), voices.SAMPLE_RATE, subtype="PCM_16")
        speaker["file"], speaker["clips"] = host_path(path), len(best)

    for speaker in speakers:
        if speaker["file"]:
            say(f"{speaker['label']}: da ascoltare in {speaker['file']}")
        else:
            say(f"{speaker['label']}: nessuna clip da ascoltare. {speaker['note']}")
    return {
        "command": LISTEN_COMMAND,
        "status": OK,
        "message": "Clip pronte: la persona le ascolta e conferma di chi è la voce prima di darle il nome.",
        "speakers": speakers,
    }


def prepare_listening(
    transcript: str, labels: list[str], *, recording: str | None = None, out_dir: str | None = None
) -> dict[str, Any]:
    """
    Join the best one or two clips of each speaker in one file, so the person hears whose voice it is before naming.

    One file per speaker, because the default player on Windows handles one file at a time better.
    """
    return guarded(
        LISTEN_COMMAND,
        lambda: _prepare_listening(transcript, labels, recording, out_dir),
        failed="Non sono riuscito a preparare le clip da ascoltare",
    )
