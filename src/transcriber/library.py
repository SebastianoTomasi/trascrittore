"""
Growing the voice library from named speakers: which clips to keep, where they go, and the trial.

A person's clips taken from recordings form one pool, `voci/<Nome>/registrazioni/`. One pool per
person, rather than one per recording, keeps the calibrated threshold meaningful: recognition keeps
the best score over a person's pools, so every extra pool would be one more chance to reach it.

Until the clip selection passes its trial, every candidate clip is saved together with the
selection's vote, and the person deletes the bad ones. The trial passes after 10 named speakers
if the selection never voted to keep a clip the person deleted, and the person confirms they reviewed
the clips added so far.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from src.asr.utils.config import LibrarySettings, get_paths_settings
from src.asr.utils.output_format import format_offset
from src.transcriber import voices
from src.transcriber.summary import INVALID_ARGUMENTS, OK, CommandError, guarded, say
from src.transcriber.transcript import UNATTRIBUTED_DISPLAY, is_anonymous


TRIAL_COMMAND = "trial"
REMOVE_COMMAND = "remove-clips"
CLIPS_FOLDER = "registrazioni"
CLIPS_RECORD = "clip.json"
TRIAL_RECORD = "prova-selezione.json"
TRIAL_NAMED_SPEAKERS = 10
# Raise it when the selection algorithm changes: the votes of the old one say nothing about the new one.
SELECTION_VERSION = 1
KEEP = "keep"
DISCARD = "discard"

# A window this much shorter than matching.window_sec still counts as full length (float noise).
_FULL_LENGTH_TOLERANCE_SEC = 0.01
_MAX_NAME_LENGTH = 80
_FOLDER_FORBIDDEN_CHARS = set('<>:"/\\|?*')
_WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"{device}{n}" for device in ("COM", "LPT") for n in range(1, 10)}
# The recording's name and the window's time that start a clip's file name, as clip_filename writes them.
_CLIP_NAME_RE = re.compile(r"(?P<recording>.+) \d{2,}\.\d{2}\.\d{2}(?!\d)")


@dataclass
class Candidate:
    start: float
    end: float
    consistency: float | None
    vote: str = KEEP


def _unit(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32)
    return vector / (np.linalg.norm(vector) + 1e-9)


def consistency_scores(voiceprints: list[np.ndarray]) -> list[float | None]:
    """
    Score each window by how much it resembles the mean of the same speaker's other windows.

    A window that does not resemble the rest usually holds another voice, laughter or noise.
    With a single window there is nothing to compare, so its score is unknown.
    """
    if len(voiceprints) < 2:
        return [None] * len(voiceprints)
    units = [_unit(voiceprint) for voiceprint in voiceprints]
    total = np.sum(units, axis=0)
    return [float(np.dot(unit, _unit(total - unit))) for unit in units]


def select_clips(
    windows: list[dict[str, float]],
    voiceprints: list[np.ndarray | None],
    *,
    window_sec: float,
    selection: LibrarySettings,
) -> list[Candidate]:
    """
    Rank a speaker's full-length windows, best first, and vote to keep or discard each.

    Every window with a voiceprint counts in the consistency score, but only full-length ones become clips.
    The selection keeps at most `keep_clips` windows, and none below `min_consistency`.
    """
    measured = [(window, voiceprint) for window, voiceprint in zip(windows, voiceprints) if voiceprint is not None]
    scores = consistency_scores([voiceprint for _, voiceprint in measured])
    candidates = [
        Candidate(start=float(window["start"]), end=float(window["end"]), consistency=score)
        for (window, _), score in zip(measured, scores)
        if float(window["end"]) - float(window["start"]) >= window_sec - _FULL_LENGTH_TOLERANCE_SEC
    ]
    candidates.sort(key=lambda candidate: (-(candidate.consistency or 0.0), candidate.start))
    kept = 0
    for candidate in candidates:
        consistent = candidate.consistency is None or candidate.consistency >= selection.min_consistency
        if consistent and kept < selection.keep_clips:
            candidate.vote = KEEP
            kept += 1
        else:
            candidate.vote = DISCARD
    return candidates


def name_problem(name: str) -> str | None:
    """
    Return why a name cannot become a voice library folder, or None when it can.
    """
    if not name.strip():
        return "Il nome è vuoto."
    if any(char in _FOLDER_FORBIDDEN_CHARS or ord(char) < 32 for char in name):
        return f"'{name}' contiene caratteri che non possono stare nel nome di una cartella: < > : \" / \\ | ? *"
    if name.endswith((".", " ")):
        return f"'{name}' non può finire con un punto o uno spazio."
    if name.split(".")[0].strip().upper() in _WINDOWS_RESERVED_NAMES:
        return f"'{name}' è un nome riservato da Windows."
    if is_anonymous(name) or name == UNATTRIBUTED_DISPLAY:
        return f"'{name}' non è il nome di una persona."
    if len(name) > _MAX_NAME_LENGTH:
        return f"Il nome è troppo lungo (al massimo {_MAX_NAME_LENGTH} caratteri)."
    return None


def canonical_name(library_dir: str | os.PathLike[str], name: str) -> str:
    """
    Return the person's folder name when the library already has them under another case or spacing.

    Windows folder names ignore case, so "luca bianchi" and "Luca Bianchi" are one folder anyway.
    """
    wanted = " ".join(name.split())
    folder = Path(library_dir)
    if folder.is_dir():
        for entry in folder.iterdir():
            if entry.is_dir() and entry.name.casefold() == wanted.casefold():
                return entry.name
    return wanted


def _edit_distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


def _is_initial(word: str) -> bool:
    return len(word.rstrip(".")) == 1


def names_are_similar(given: str, existing: str) -> bool:
    """
    Tell whether a new name may mean a person already in the library under another name.

    Similar: one or two letters apart, the same surname with an initial for the first name,
    or a first name alone that starts the existing name. Names equal but for case and spacing
    are the same person, not similar ones.
    """
    a, b = " ".join(given.split()).casefold(), " ".join(existing.split()).casefold()
    if a == b:
        return False
    if _edit_distance(a, b) <= 2:
        return True
    words_a, words_b = a.split(), b.split()
    if len(words_a) >= 2 and len(words_b) >= 2 and words_a[1:] == words_b[1:]:
        first_a, first_b = words_a[0], words_b[0]
        if (_is_initial(first_a) and first_b.startswith(first_a[0])) or (_is_initial(first_b) and first_a.startswith(first_b[0])):
            return True
    return len(words_a) == 1 and len(words_b) >= 2 and words_a[0] == words_b[0]


def similar_people(library_dir: str | os.PathLike[str], name: str) -> list[str]:
    """
    Return the people in the library whose names are similar to `name`, unless one is that very name.
    """
    folder = Path(library_dir)
    if not folder.is_dir():
        return []
    people = sorted(entry.name for entry in folder.iterdir() if entry.is_dir())
    wanted = " ".join(name.split()).casefold()
    if any(person.casefold() == wanted for person in people):
        return []
    return [person for person in people if names_are_similar(name, person)]


def library_dir() -> Path | None:
    """
    Return this PC's voice library, or None when the settings configure none.
    """
    configured = get_paths_settings().voice_library_dir
    return Path(configured).resolve() if configured else None


def recording_name(recording_file: str) -> str:
    """
    Return the name that starts the file names of the clips cut from a recording.
    """
    return Path(recording_file).stem


def clip_filename(recording_file: str, start: float) -> str:
    # A speaker's windows never overlap and last at least matching.min_window_sec, so seconds are enough.
    return f"{recording_name(recording_file)} {format_offset(start).replace(':', '.')}.wav"


def clip_recording(clip_file: str | os.PathLike[str]) -> str | None:
    """
    Return the name of the recording a clip was cut from: the part of its file name before the window's time.

    The name stays when the clip is moved, loses its record, or is copied with a suffix such as " - Copia".
    A clip placed by hand has none.
    """
    match = _CLIP_NAME_RE.match(Path(clip_file).stem)
    return match["recording"] if match else None


def clips_folder(library_dir: str | os.PathLike[str], person: str) -> Path:
    return Path(library_dir) / person / CLIPS_FOLDER


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _selection_record(selection: LibrarySettings) -> dict[str, Any]:
    return {"keep_clips": selection.keep_clips, "min_consistency": selection.min_consistency, "version": SELECTION_VERSION}


def save_clips(
    library_dir: str | os.PathLike[str],
    person: str,
    audio: np.ndarray,
    candidates: list[Candidate],
    *,
    trial: bool,
    selection: LibrarySettings,
    origin: dict[str, Any],
) -> list[str]:
    """
    Cut the candidates from the recording into the person's pool and record where each came from.

    During the trial every candidate is saved with its vote; afterwards only the kept ones.
    `origin` describes the recording, the transcript and the label the clips came from.
    """
    candidates = [candidate for candidate in candidates if trial or candidate.vote == KEEP]
    if not candidates:
        return []
    folder = clips_folder(library_dir, person)
    folder.mkdir(parents=True, exist_ok=True)
    record_path = folder / CLIPS_RECORD
    record = _read_json(record_path, {})
    saved: list[str] = []
    for candidate in candidates:
        clip = voices.cut(audio, candidate.start, candidate.end)
        if not len(clip):
            continue
        filename = clip_filename(origin["recording_file"], candidate.start)
        sf.write(folder / filename, clip, voices.SAMPLE_RATE, subtype="PCM_16")
        record[filename] = {
            **origin,
            "start": round(candidate.start, 3),
            "end": round(candidate.end, 3),
            "consistency": round(candidate.consistency, 4) if candidate.consistency is not None else None,
            "vote": candidate.vote,
            "trial": trial,
            "selection": _selection_record(selection),
            "saved": datetime.now().isoformat(timespec="seconds"),
        }
        saved.append(filename)
    _write_json(record_path, record)
    return saved


def _files_by_name(folder: Path) -> dict[str, Path]:
    # Windows file names ignore case.
    return {name.casefold(): Path(root) / name for root, _, names in os.walk(folder) for name in names}


def clip_records(library_dir: str | os.PathLike[str]) -> list[tuple[str, Path, dict[str, Any]]]:
    """
    Return (person, clip path, origin) for every clip ever saved from a recording, deleted or not.

    A clip is found by its file name anywhere in its person's folder, since the person may move it into a
    condition folder. The path of a clip the person deleted, or moved to another person, does not exist.
    """
    folder = Path(library_dir)
    if not folder.is_dir():
        return []
    records = []
    for person_dir in sorted(entry for entry in folder.iterdir() if entry.is_dir()):
        pool = person_dir / CLIPS_FOLDER
        origins = _read_json(pool / CLIPS_RECORD, {})
        found = _files_by_name(person_dir) if origins else {}
        for filename, origin in origins.items():
            records.append((person_dir.name, found.get(filename.casefold(), pool / filename), origin))
    return records


def _added_clips(library_dir: str | os.PathLike[str], person: str) -> tuple[Path, dict[str, Any], dict[str, str]]:
    """
    Return the person's pool folder, its clip record, and {record key: file name} for the recorded clips still in it.
    """
    folder = clips_folder(library_dir, person)
    record = _read_json(folder / CLIPS_RECORD, {})
    present = {path.name.casefold(): path.name for path in folder.glob("*") if path.is_file()} if folder.is_dir() else {}
    return folder, record, {key: present[key.casefold()] for key in record if key.casefold() in present}


def cap_proposal(library_dir: str | os.PathLike[str], person: str, cap: int) -> list[str]:
    """
    Propose which of the person's added clips to remove to get back to `cap`.

    Clips go from the recording that has the most of them, least consistent first, so rooms and microphones stay
    varied. Only clips the transcriber added and still in `registrazioni` count; clips placed by hand never do.
    """
    _, record, present = _added_clips(library_dir, person)
    excess = len(present) - cap
    if excess <= 0:
        return []
    by_recording: dict[str, list[str]] = {}
    for key in present:
        recording = clip_recording(key) or str(record[key].get("recording_file"))
        by_recording.setdefault(recording, []).append(key)
    for keys in by_recording.values():
        # A clip without a consistency score was the only window of its speaker: keep it for last.
        keys.sort(key=lambda key: (record[key].get("consistency") is None, record[key].get("consistency") or 0.0, key), reverse=True)
    proposal = []
    for _ in range(excess):
        recording = max(sorted(by_recording), key=lambda name: len(by_recording[name]))
        proposal.append(present[by_recording[recording].pop()])
    return proposal


def remove_clips(library_dir: str | os.PathLike[str], person: str, filenames: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    """
    Delete the given added clips of a person, as the person confirmed, and mark them removed in the clip record.

    A file that is not a recorded clip in the person's `registrazioni` folder is refused, never deleted.
    """
    folder, record, present = _added_clips(library_dir, person)
    keys = {key.casefold(): key for key in present}
    removed, refused = [], []
    for filename in filenames:
        key = keys.get(Path(filename).name.casefold())
        if key is None:
            refused.append({"clip": filename, "reason": "non è una clip aggiunta dal trascrittore in questa cartella"})
            continue
        (folder / present[key]).unlink()
        record[key]["removed"] = datetime.now().isoformat(timespec="seconds")
        removed.append(present[key])
    if removed:
        _write_json(folder / CLIPS_RECORD, record)
    return removed, refused


def remove_clips_report(person: str, filenames: list[str], selection: LibrarySettings) -> dict[str, Any]:
    """
    The remove-clips command: delete added clips the person confirmed, after a naming passed the cap.
    """

    def report() -> dict[str, Any]:
        folder = library_dir()
        if folder is None or not folder.is_dir():
            raise CommandError(INVALID_ARGUMENTS, "La libreria delle voci non è configurata o non esiste.")
        if not trial_passed(folder, selection):
            raise CommandError(
                INVALID_ARGUMENTS, "Durante il periodo di prova il trascrittore non toglie clip: cancellale tu, se sono brutte."
            )
        if not (folder / person).is_dir():
            raise CommandError(INVALID_ARGUMENTS, f"Nella libreria non c'è '{person}'.")
        removed, refused = remove_clips(folder, person, filenames)
        lines = [f"{person}: {len(removed)} clip tolte dalla libreria."]
        lines += [f"  non tolta {entry['clip']}: {entry['reason']}" for entry in refused]
        for line in lines:
            say(line)
        return {
            "command": REMOVE_COMMAND,
            "status": OK,
            "message": " ".join(line.strip() for line in lines),
            "person": person,
            "removed": removed,
            "refused": refused,
        }

    return guarded(REMOVE_COMMAND, report, failed="Non sono riuscito a togliere le clip")


@dataclass
class TrialStatus:
    named_speakers: int
    passed: bool
    disagreements: list[dict[str, Any]] = field(default_factory=list)
    votes: dict[str, int] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        """The criterion is met; the trial passes once the person confirms they reviewed the clips."""
        return not self.passed and self.named_speakers >= TRIAL_NAMED_SPEAKERS and not self.disagreements


def _passed_selections(library_dir: str | os.PathLike[str]) -> list[dict[str, Any]]:
    return _read_json(Path(library_dir) / TRIAL_RECORD, {}).get("passed", [])


def trial_passed(library_dir: str | os.PathLike[str], selection: LibrarySettings) -> bool:
    wanted = _selection_record(selection)
    return any({key: entry.get(key) for key in wanted} == wanted for entry in _passed_selections(library_dir))


def trial_status(library_dir: str | os.PathLike[str], selection: LibrarySettings) -> TrialStatus:
    """
    Compare the selection's votes with the person's deletions, for clips saved under this selection.

    A changed selection starts a new trial, since the old votes say nothing about it.
    """
    wanted = _selection_record(selection)
    named: set[tuple[Any, ...]] = set()
    disagreements = []
    votes = {"keep": 0, "discard": 0, "discarded_but_kept_by_person": 0}
    for person, clip_path, origin in clip_records(library_dir):
        if not origin.get("trial") or origin.get("selection") != wanted:
            continue
        named.add((person, origin.get("recording_file"), origin.get("recording_duration_sec"), origin.get("label")))
        if origin.get("vote") == KEEP:
            votes["keep"] += 1
            if not clip_path.exists():
                disagreements.append({"person": person, "clip": clip_path.name, "consistency": origin.get("consistency")})
        else:
            votes["discard"] += 1
            votes["discarded_but_kept_by_person"] += clip_path.exists()
    return TrialStatus(
        named_speakers=len(named),
        passed=trial_passed(library_dir, selection),
        disagreements=disagreements,
        votes=votes,
    )


def evaluate_trial(library_dir: str | os.PathLike[str], selection: LibrarySettings, *, reviewed: bool) -> TrialStatus:
    """
    Report the trial; when its criterion is met and the person reviewed the clips, the selection
    discards clips by itself from then on.
    """
    status = trial_status(library_dir, selection)
    if status.ready and reviewed:
        record_path = Path(library_dir) / TRIAL_RECORD
        record = _read_json(record_path, {})
        record.setdefault("passed", []).append(
            {**_selection_record(selection), "date": datetime.now().date().isoformat()}
        )
        _write_json(record_path, record)
        status.passed = True
    return status


def _trial_lines(status: TrialStatus, selection: LibrarySettings, *, already_passed: bool) -> list[str]:
    if already_passed:
        return ["La selezione delle clip ha già superato il periodo di prova: scarta da sola le clip peggiori."]
    if status.passed:
        return [
            f"Periodo di prova superato: {status.named_speakers} voci nominate e nessuna clip tenuta dalla selezione "
            "è stata cancellata.",
            f"Da ora la selezione tiene al massimo {selection.keep_clips} clip per voce e registrazione, "
            "e scarta le altre da sola.",
        ]
    if status.disagreements:
        return [
            f"La selezione aveva tenuto {len(status.disagreements)} clip che hai cancellato: va corretta prima di "
            "fidarsi. Segnalalo a chi ti ha dato il trascrittore; il periodo di prova continua.",
            *[f"  {entry['person']}: {entry['clip']}" for entry in status.disagreements],
        ]
    if status.ready:
        return [
            f"Criterio del periodo di prova raggiunto: {status.named_speakers} voci nominate e nessuna clip tenuta "
            "dalla selezione è stata cancellata. Se hai ascoltato tutte le clip aggiunte e cancellato quelle brutte, "
            "conferma: da lì in poi la selezione scarta da sola le peggiori."
        ]
    return [
        f"Periodo di prova della selezione delle clip: voci nominate {status.named_speakers} su "
        f"{TRIAL_NAMED_SPEAKERS}. Continua ad ascoltare le clip aggiunte e a cancellare quelle brutte."
    ]


def trial_report(selection: LibrarySettings, *, reviewed: bool = False) -> dict[str, Any]:
    """
    The trial command: where the selection's votes and the person's deletions disagree, and whether it passed.

    `reviewed` says the person listened to every clip added so far and deleted the bad ones.
    """

    def report() -> dict[str, Any]:
        folder = library_dir()
        if folder is None or not folder.is_dir():
            raise CommandError(INVALID_ARGUMENTS, "La libreria delle voci non è configurata o non esiste.")
        already_passed = trial_passed(folder, selection)
        status = evaluate_trial(folder, selection, reviewed=reviewed)
        lines = _trial_lines(status, selection, already_passed=already_passed)
        for line in lines:
            say(line)
        return {
            "command": TRIAL_COMMAND,
            "status": OK,
            "message": " ".join(line.strip() for line in lines),
            "passed": status.passed,
            "ready": status.ready,
            "named_speakers": status.named_speakers,
            "needed": TRIAL_NAMED_SPEAKERS,
            "votes": status.votes,
            "disagreements": status.disagreements,
        }

    return guarded(TRIAL_COMMAND, report, failed="Il resoconto del periodo di prova non è riuscito")
