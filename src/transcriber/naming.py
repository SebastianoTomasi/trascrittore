"""
Naming speakers after the transcript exists, and preparing the clip a person listens to first.

Only a person gives a name: an agent calls these commands with names the person confirmed or wrote.
Naming never transcribes again. It rewrites both transcript files from the JSON file, and cuts clips
of each named speaker from the recording into the PC's voice library.

A speaker the transcriber recognized changes only when the person asks: `confirm` keeps the name and
adds clips, `correct` allows a pair that replaces the name. Neither is ever offered by the transcriber.
"""

from __future__ import annotations

import json
import re
import tempfile
import time
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable

import numpy as np
import soundfile as sf

from src.asr.utils.config import get_library_settings, get_matching_settings
from src.asr.utils.output_format import format_offset
from src.transcriber import library, voices
from src.transcriber.summary import (
    FILE_NOT_FOUND,
    INVALID_ARGUMENTS,
    OK,
    OVER_CAP,
    SIMILAR_NAME,
    CommandError,
    guarded,
    host_path,
    say,
)
from src.transcriber.transcript import (
    TRANSCRIPT_SUFFIX,
    UNATTRIBUTED_DISPLAY,
    is_anonymous,
    rename_speakers,
    render_payload_text,
    speaker_labels,
)


NAME_COMMAND = "name"
LISTEN_COMMAND = "listen"
LISTEN_PREFIX = "ascolta "
NAMED, CONFIRMED, CORRECTED = "named", "confirmed", "corrected"
# The transcript stores the duration rounded to a tenth of a second.
_DURATION_TOLERANCE_SEC = 1.0
# A confirmed speaker scoring less than this above the threshold gains much from new clips.
_CLOSE_TO_THRESHOLD = 0.05
# Listening clips that a session left behind, for example because it stopped before naming, go after a day.
_FORGOTTEN_CLIP_AGE_SEC = 24 * 3600
# HH:MM:SS, MM:SS or seconds; a minus sign only so that a time before the recording is refused as such.
_TIME_RE = re.compile(r"(-)?(?:(?:(\d+):)?(\d+):)?(\d+(?:[.,]\d+)?)")
# A passage is heard with a second of what comes before and after it.
_PASSAGE_MARGIN_SEC = 1.0


def _clean(text: str) -> str:
    return " ".join(text.split())


def parse_pairs(pairs: list[str]) -> dict[str, str]:
    """
    Read "Persona 2=Luca Bianchi" pairs into {label: name}.
    """
    names: dict[str, str] = {}
    for pair in pairs:
        label, separator, name = pair.partition("=")
        label, name = _clean(label), _clean(name)
        if not separator or not label or not name:
            raise CommandError(INVALID_ARGUMENTS, f"'{pair}' non è nella forma \"Persona 2=Nome Cognome\".")
        if label in names:
            raise CommandError(INVALID_ARGUMENTS, f"'{label}' compare due volte.")
        names[label] = name
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


def _check_known(payload: dict[str, Any], labels: Iterable[str]) -> None:
    known = [label for label in speaker_labels(payload) if label != UNATTRIBUTED_DISPLAY]
    for label in labels:
        if label not in known:
            raise CommandError(
                INVALID_ARGUMENTS,
                f"'{label}' non è una voce di questa trascrizione. Voci: {', '.join(known) or 'nessuna'}.",
            )


def _check_naming(payload: dict[str, Any], written: dict[str, str], confirm: list[str], correct: bool) -> None:
    _check_known(payload, [*written, *confirm])
    for label in written:
        if label in confirm:
            raise CommandError(INVALID_ARGUMENTS, f"'{label}' compare due volte.")
        if not is_anonymous(label) and not correct:
            raise CommandError(
                INVALID_ARGUMENTS,
                f"'{label}' ha già un nome, dato dal riconoscimento. Si corregge solo se la persona lo chiede: "
                "in quel caso aggiungi --correct.",
            )
    for label in confirm:
        if is_anonymous(label):
            raise CommandError(
                INVALID_ARGUMENTS, f"'{label}' non ha un nome da confermare: dagli un nome con \"{label}=Nome Cognome\"."
            )


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


def _speaker(payload: dict[str, Any], label: str) -> dict[str, Any]:
    return next((speaker for speaker in payload.get("speakers", []) if speaker["label"] == label), {})


def _candidates(
    payload: dict[str, Any], label: str, audio: np.ndarray, voiceprints: voices.Voiceprints
) -> tuple[list[library.Candidate], str | None]:
    """
    Rank the speaker's windows as clips, best first, or say why there are none.
    """
    windows = _speaker(payload, label).get("windows")
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
    results: list[dict[str, Any]],
    recording: str | None,
    library_dir: Path | None,
) -> list[tuple[str, Path]]:
    """
    Add each named speaker's clips to the pool the library rules choose; return (person, pool) for each pool filled.
    """
    filled: list[tuple[str, Path]] = []
    if library_dir is None:
        for result in results:
            result["note"] = "La libreria delle voci non è configurata."
        return filled

    audio, problem = open_recording(payload, transcript, recording)
    if audio is None:
        for result in results:
            result["note"] = problem
        return filled

    voiceprints = voices.Voiceprints()
    # Whether each person was already in the library tells a miss from a person new to it.
    known = {result["name"]: (library_dir / result["name"]).is_dir() for result in results}
    # The transcript is mounted under another name in the container: its folder's name is the one on the PC.
    transcript_folder = PureWindowsPath(host_path(transcript.parent)).name
    max_pools = get_library_settings().max_pools
    for result in results:
        candidates, result["note"] = _candidates(payload, result["label"], audio, voiceprints)
        if not candidates:
            continue
        kept = [candidate for candidate in candidates if candidate.keep]
        person_dir = library_dir / result["name"]
        if result["action"] == CONFIRMED:
            kind = library.CONFIRM
        else:
            kind = library.MISS if known[result["name"]] else library.NEW
        folder = library.choose_pool(
            person_dir,
            kind=kind,
            kept=len(kept),
            transcript_folder=transcript_folder,
            max_pools=max_pools,
            similarity=library.similarity_to(kept, person_dir, voiceprints.of_clip),
        ) if kept else person_dir / library.CLIPS_FOLDER
        new_pool = kind == library.MISS and not folder.exists()
        saved = library.save_clips(
            folder,
            audio,
            candidates,
            origin={
                "recording": payload.get("recording"),
                "recording_file": payload["file"],
                "recording_duration_sec": payload["duration_sec"],
                "transcript": host_path(transcript),
                "label": result["label"],
            },
        )
        result["clips_added"] = len(saved)
        if not saved:
            result["note"] = (
                "Nessun tratto di questa voce somiglia abbastanza agli altri: probabilmente contengono altre voci "
                "o rumori, quindi non ho aggiunto clip."
            )
            continue
        result["folder"] = host_path(folder)
        filled.append((result["name"], folder))
        if new_pool:
            _add_note(
                result,
                f"Non l'avevo riconosciuta: le sue clip formano un gruppo nuovo, '{folder.name}', "
                "per le registrazioni come questa.",
            )
    return filled


def _add_note(result: dict[str, Any], note: str, *, first: bool = False) -> None:
    if not result["note"]:
        result["note"] = note
    else:
        result["note"] = f"{note} {result['note']}" if first else f"{result['note']} {note}"


def _recognition_notes(payload: dict[str, Any], results: list[dict[str, Any]], library_dir: Path | None) -> None:
    threshold = get_matching_settings().threshold
    for result in results:
        if result["action"] == CONFIRMED:
            score = _speaker(payload, result["label"]).get("score")
            if score is None:
                continue
            result["score"], result["threshold"] = score, threshold
            if not result["clips_added"]:
                continue
            gain = "molto" if score - threshold < _CLOSE_TO_THRESHOLD else "poco"
            _add_note(
                result,
                f"Era stata riconosciuta con punteggio {score:.3f} (soglia {threshold:.3f}): le nuove clip aiuteranno {gain}.",
                first=True,
            )
        elif result["action"] == CORRECTED:
            where = ""
            if library_dir is not None and (library_dir / result["label"]).is_dir():
                where = f" in {host_path(library_dir / result['label'])}"
            _add_note(
                result,
                f"'{result['label']}' era stata riconosciuta al posto di '{result['name']}': ascolta le clip di "
                f"'{result['label']}'{where} e cancella quelle che non sono sue.",
            )


def _write_transcript(transcript: Path, payload: dict[str, Any]) -> Path:
    text_path = transcript.with_suffix(".txt")
    transcript.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(render_payload_text(payload), encoding="utf-8")
    return text_path


def _over_cap(filled: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    cap = get_library_settings().max_clips
    over = []
    for person, folder in dict.fromkeys(filled):
        proposal = library.cap_proposal(folder, cap)
        if proposal:
            over.append({"person": person, "pool": host_path(folder), "cap": cap, "remove": proposal})
    return over


def _naming_lines(results: list[dict[str, Any]], over_cap: list[dict[str, Any]]) -> list[str]:
    lines = []
    for result in results:
        arrow = "confermata" if result["action"] == CONFIRMED else f"→ {result['name']}"
        line = f"{result['label']} {arrow}: "
        if result["clips_added"]:
            line += f"{result['clips_added']} clip aggiunte alla libreria delle voci, in {result['folder']}."
            if result["note"]:
                line += f" {result['note']}"
        else:
            line += f"nessuna clip aggiunta. {result['note']}"
        lines.append(line)
    for entry in over_cap:
        lines.append(
            f"{entry['person']} ha più di {entry['cap']} clip aggiunte in {entry['pool']}: propongo di togliere le "
            f"{len(entry['remove'])} delle registrazioni con più clip, le meno somiglianti. Le tolgo solo dopo una conferma."
        )
    return lines


def _similar_names(
    written: dict[str, str], library_dir: Path | None, new_people: list[str]
) -> list[dict[str, Any]]:
    if library_dir is None:
        return []
    confirmed_new = {_clean(name).casefold() for name in new_people}
    similar = []
    for label, name in written.items():
        if name.casefold() in confirmed_new:
            continue
        people = library.similar_people(library_dir, name)
        if people:
            similar.append({"label": label, "name": name, "people": people})
    return similar


def _similar_summary(similar: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [
        f"'{entry['name']}' (per {entry['label']}) somiglia a chi è già nella libreria: {', '.join(entry['people'])}."
        for entry in similar
    ]
    lines.append("Non ho salvato niente: serve sapere se è una di queste persone o una persona nuova.")
    for line in lines:
        say(line)
    return {"command": NAME_COMMAND, "status": SIMILAR_NAME, "message": " ".join(lines), "similar": similar}


def _name_speakers(
    transcript: str,
    pairs: list[str],
    recording: str | None,
    confirm: list[str],
    correct: bool,
    new_people: list[str],
) -> dict[str, Any]:
    written = parse_pairs(pairs)
    confirm = list(dict.fromkeys(_clean(label) for label in confirm))
    # A pair that gives a recognized speaker the name it already has is a confirmation.
    for label, name in list(written.items()):
        if not is_anonymous(label) and name.casefold() == label.casefold():
            del written[label]
            confirm.append(label)
    if not written and not confirm:
        raise CommandError(INVALID_ARGUMENTS, "Indica almeno una voce da nominare, per esempio \"Persona 2=Nome Cognome\".")
    transcript_path = Path(transcript)
    payload = load_transcript(transcript_path)
    _check_naming(payload, written, confirm, correct)
    for name in written.values():
        problem = library.name_problem(name)
        if problem:
            raise CommandError(INVALID_ARGUMENTS, problem)
    library_dir = library.library_dir()
    names = dict(written)
    if library_dir is not None:
        names = {label: library.canonical_name(library_dir, name) for label, name in written.items()}
    similar = _similar_names(names, library_dir, new_people)
    if similar:
        return _similar_summary(similar)

    results = [
        {
            "label": label,
            "name": name,
            "action": CORRECTED if not is_anonymous(label) else NAMED,
            "clips_added": 0,
            "folder": None,
            "note": None,
        }
        for label, name in names.items()
    ]
    results += [
        {"label": label, "name": label, "action": CONFIRMED, "clips_added": 0, "folder": None, "note": None}
        for label in confirm
    ]
    # Clips first: if rewriting the transcript then fails, the labels are still there and naming can be
    # repeated, and the clips it saves again replace the same files.
    filled = _grow_library(payload, transcript_path, results, recording, library_dir)
    for result in results:
        if result["action"] != CONFIRMED and result["name"] != written[result["label"]]:
            _add_note(result, f"Nella libreria c'è già '{result['name']}': uso quel nome.", first=True)
    _recognition_notes(payload, results, library_dir)
    text_path = _write_transcript(
        transcript_path, rename_speakers(payload, {result["label"]: result["name"] for result in results})
    )
    over_cap = _over_cap(filled)

    lines = _naming_lines(results, over_cap)
    for line in lines:
        say(line)
    return {
        "command": NAME_COMMAND,
        "status": OVER_CAP if over_cap else OK,
        "message": " ".join(["Nomi applicati alla trascrizione.", *lines]),
        "transcript_txt": host_path(text_path),
        "transcript_json": host_path(transcript_path),
        "named": results,
        "over_cap": over_cap,
    }


def name_speakers(
    transcript: str,
    pairs: list[str],
    *,
    recording: str | None = None,
    confirm: list[str] | None = None,
    correct: bool = False,
    new_people: list[str] | None = None,
) -> dict[str, Any]:
    """
    Apply names confirmed by a person to a transcript, and add the named speakers' clips to the voice library.

    `confirm` lists recognized speakers the person confirmed; `correct` lets pairs replace a recognized name;
    `new_people` lists names the person confirmed as new people despite a similar name in the library.
    """
    return guarded(
        NAME_COMMAND,
        lambda: _name_speakers(transcript, pairs, recording, confirm or [], correct, new_people or []),
        failed="Non sono riuscito a dare i nomi",
    )


def _listening_prefix(transcript: Path) -> str:
    """
    Return how the names of a transcript's listening clips start, such as "ascolta registrazione - ".

    The name says which recording the person hears, and keeps apart the clips of parallel sessions.
    The launcher clears a transcript's listening clips after naming by this same rule.
    """
    return f"{LISTEN_PREFIX}{transcript.stem.removesuffix(TRANSCRIPT_SUFFIX)} - "


def _clear_listening_clips(out_dir: Path, prefix: str) -> None:
    """
    Delete the transcript's own listening clips, and those any transcript left for more than a day.

    The prefix ignores case, as Windows does: an agent may write the transcript's path in another case.
    """
    cutoff = time.time() - _FORGOTTEN_CLIP_AGE_SEC
    for path in out_dir.glob(f"{LISTEN_PREFIX}*.wav"):
        try:
            if path.name.casefold().startswith(prefix.casefold()) or path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            # Still open in the player, or just deleted by another session: the next listening tries again.
            pass


def _longest_window(payload: dict[str, Any], label: str) -> dict[str, float] | None:
    windows = _speaker(payload, label).get("windows") or []
    return max(windows, key=lambda window: float(window["end"]) - float(window["start"]), default=None)


def _listening_piece(
    payload: dict[str, Any], label: str, audio: np.ndarray, voiceprints: voices.Voiceprints, clip: int
) -> tuple[tuple[float, float] | None, int, str | None]:
    """
    Return the stretch to play for a speaker, how many full clips they have, and a note.
    """
    candidates, note = _candidates(payload, label, audio, voiceprints)
    if candidates:
        if clip > len(candidates):
            return None, len(candidates), f"Questa voce ha solo {len(candidates)} clip da ascoltare."
        best = candidates[clip - 1]
        return (best.start, best.end), len(candidates), None
    longest = _longest_window(payload, label)
    if longest is None or clip > 1:
        return None, 0, note
    start, end = float(longest["start"]), float(longest["end"])
    return (start, end), 0, (
        f"{note} Ascolti il tratto più lungo, di {end - start:.0f} secondi: serve solo a riconoscere la voce."
    )


def _listening_folder(out_dir: str | None) -> Path:
    folder = Path(out_dir) if out_dir else Path(tempfile.gettempdir()) / "trascrittore-ascolto"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _prepare_listening(
    transcript: str, label: str, recording: str | None, out_dir: str | None, clip: int
) -> dict[str, Any]:
    label = _clean(label)
    if not label:
        raise CommandError(INVALID_ARGUMENTS, "Indica la voce da ascoltare, per esempio \"Persona 2\".")
    if clip < 1:
        raise CommandError(INVALID_ARGUMENTS, "Il numero della clip parte da 1.")
    transcript_path = Path(transcript)
    payload = load_transcript(transcript_path)
    _check_known(payload, [label])
    folder = _listening_folder(out_dir)
    prefix = _listening_prefix(transcript_path)
    _clear_listening_clips(folder, prefix)

    heard: dict[str, Any] = {"label": label, "file": None, "clip": clip, "clips": 0, "seconds": None, "note": None}
    audio, problem = open_recording(payload, transcript_path, recording)
    if audio is None:
        heard["note"] = problem
    else:
        piece, heard["clips"], heard["note"] = _listening_piece(payload, label, audio, voices.Voiceprints(), clip)
        if piece is not None:
            # One file per clip: the one heard before may still be open in the player.
            path = folder / f"{prefix}{label} - {clip}.wav"
            sf.write(path, voices.cut(audio, *piece), voices.SAMPLE_RATE, subtype="PCM_16")
            heard["file"], heard["seconds"] = host_path(path), round(piece[1] - piece[0], 1)

    if heard["file"]:
        count = f"clip {clip} di {heard['clips']}" if heard["clips"] else "nessuna clip intera"
        say(f"{label} ({count}): da ascoltare in {heard['file']}")
        if heard["note"]:
            say(f"  {heard['note']}")
        message = f"Clip di {label} pronta: la persona la ascolta e conferma di chi è la voce prima di darle il nome."
    else:
        message = f"{label}: niente da ascoltare. {heard['note']}"
        say(message)
    return {"command": LISTEN_COMMAND, "status": OK, "message": message, **heard}


def prepare_listening(
    transcript: str,
    label: str,
    *,
    recording: str | None = None,
    out_dir: str | None = None,
    clip: int = 1,
) -> dict[str, Any]:
    """
    Cut one clip of a speaker, the `clip`-th best, so the person hears whose voice it is before naming.

    One speaker at a time: the person answers before hearing the next. A speaker without a full-length
    window is heard from their longest window, which never becomes a clip.
    """
    return guarded(
        LISTEN_COMMAND,
        lambda: _prepare_listening(transcript, label, recording, out_dir, clip),
        failed="Non sono riuscito a preparare la clip da ascoltare",
    )


def _seconds(at: str) -> float:
    """
    Read a time written as HH:MM:SS, MM:SS or seconds, with decimals after a point or, as in an .srt, a comma.
    """
    match = _TIME_RE.fullmatch(at.strip())
    if match is None:
        raise CommandError(
            INVALID_ARGUMENTS,
            f"Tempo non valido: '{at}'. Scrivilo come HH:MM:SS, MM:SS o in secondi, per esempio 00:04:09.62.",
        )
    sign, hours, minutes, seconds = match.groups()
    total = int(hours or 0) * 3600 + int(minutes or 0) * 60 + float(seconds.replace(",", "."))
    return -total if sign else total


def _passage(payload: dict[str, Any], seconds: float) -> dict[str, Any] | None:
    """
    Return the segment that holds the time or, when the time falls in a pause, the nearest one.
    """
    segments = [segment for turn in payload["turns"] for segment in turn.get("segments", [])]
    return min(
        segments,
        key=lambda segment: max(float(segment["start_sec"]) - seconds, seconds - float(segment["end_sec"]), 0.0),
        default=None,
    )


def _prepare_listening_at(transcript: str, at: str, recording: str | None, out_dir: str | None) -> dict[str, Any]:
    seconds = _seconds(at)
    transcript_path = Path(transcript)
    payload = load_transcript(transcript_path)
    duration = float(payload["duration_sec"])
    if not 0 <= seconds <= duration:
        raise CommandError(
            INVALID_ARGUMENTS, f"Il tempo {at} è fuori dalla registrazione, che dura {format_offset(duration)}."
        )
    folder = _listening_folder(out_dir)
    prefix = _listening_prefix(transcript_path)
    _clear_listening_clips(folder, prefix)

    heard: dict[str, Any] = {"file": None, "start": None, "end": None, "text": None, "note": None}
    segment = _passage(payload, seconds)
    if segment is None:
        heard["note"] = (
            "La trascrizione è di una versione precedente, senza i tempi delle frasi: "
            "per sentire il passaggio, apri la registrazione a quel punto."
            if payload["turns"]
            else "Nella trascrizione non c'è parlato da ascoltare."
        )
    else:
        heard["text"] = segment["text"]
        audio, heard["note"] = open_recording(payload, transcript_path, recording)
        if audio is not None:
            start = max(0.0, float(segment["start_sec"]) - _PASSAGE_MARGIN_SEC)
            end = min(len(audio) / voices.SAMPLE_RATE, float(segment["end_sec"]) + _PASSAGE_MARGIN_SEC)
            path = folder / f"{prefix}{format_offset(float(segment['start_sec'])).replace(':', '-')}.wav"
            # Still there after clearing: the same passage is open in the player, and its file holds it already.
            if not path.exists():
                sf.write(path, voices.cut(audio, start, end), voices.SAMPLE_RATE, subtype="PCM_16")
            heard.update(file=host_path(path), start=round(start, 1), end=round(end, 1))

    if heard["file"]:
        say(f"Passaggio {format_offset(heard['start'])}–{format_offset(heard['end'])}: da ascoltare in {heard['file']}")
        say(f"  \"{heard['text']}\"")
        message = "Passaggio pronto: la persona lo ascolta prima di scegliere la correzione."
    else:
        message = f"Niente da ascoltare. {heard['note']}"
        say(message)
    return {"command": LISTEN_COMMAND, "status": OK, "message": message, **heard}


def prepare_listening_at(
    transcript: str,
    at: str,
    *,
    recording: str | None = None,
    out_dir: str | None = None,
) -> dict[str, Any]:
    """
    Cut the segment of the transcript at a time, with a second on each side, so the person hears a passage.

    A time in a pause between segments plays the nearest segment. The summary gives the segment's text,
    so the agent can check that it holds the words in doubt.
    """
    return guarded(
        LISTEN_COMMAND,
        lambda: _prepare_listening_at(transcript, at, recording, out_dir),
        failed="Non sono riuscito a preparare il passaggio da ascoltare",
    )
