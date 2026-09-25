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
from dataclasses import asdict, dataclass, field
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
CLIPS_FOLDER = "registrazioni"
CLIPS_RECORD = "clip.json"
TRIAL_RECORD = "prova-selezione.json"
TRIAL_NAMED_SPEAKERS = 10
LISTENING_CLIPS = 2
# Raise it when the selection algorithm changes: the votes of the old one say nothing about the new one.
SELECTION_VERSION = 1
KEEP = "keep"
DISCARD = "discard"

# A window this much shorter than matching.window_sec still counts as full length (float noise).
_FULL_LENGTH_TOLERANCE_SEC = 0.01
_MAX_NAME_LENGTH = 80
_FOLDER_FORBIDDEN_CHARS = set('<>:"/\\|?*')
_WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"{device}{n}" for device in ("COM", "LPT") for n in range(1, 10)}


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


def library_dir() -> Path | None:
    """
    Return this PC's voice library, or None when the settings configure none.
    """
    configured = get_paths_settings().voice_library_dir
    return Path(configured).resolve() if configured else None


def clip_filename(recording_file: str, start: float) -> str:
    # A speaker's windows never overlap and last at least matching.min_window_sec, so seconds are enough.
    return f"{Path(recording_file).stem} {format_offset(start).replace(':', '.')}.wav"


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
    return {**asdict(selection), "version": SELECTION_VERSION}


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
    folder = clips_folder(library_dir, person)
    folder.mkdir(parents=True, exist_ok=True)
    record_path = folder / CLIPS_RECORD
    record = _read_json(record_path, {})
    saved: list[str] = []
    for candidate in candidates:
        if not trial and candidate.vote != KEEP:
            continue
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


def clip_records(library_dir: str | os.PathLike[str]) -> list[tuple[str, Path, dict[str, Any]]]:
    """
    Return (person, clip path, origin) for every clip ever saved from a recording, deleted or not.
    """
    folder = Path(library_dir)
    if not folder.is_dir():
        return []
    records = []
    for person_dir in sorted(entry for entry in folder.iterdir() if entry.is_dir()):
        pool = person_dir / CLIPS_FOLDER
        for filename, origin in _read_json(pool / CLIPS_RECORD, {}).items():
            records.append((person_dir.name, pool / filename, origin))
    return records


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
