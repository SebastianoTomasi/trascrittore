"""
Growing the voice library from named speakers: which clips to keep, which pool they go to, and the caps.

A person's clips taken from recordings go to added pools, subfolders of `voci/<Nome>/` that hold a clip
record: `registrazioni` first, then one pool for each recognition the person says was missed, named after
the transcript's folder. Recognition keeps the best score over a person's pools, so every extra pool is one
more chance to reach the threshold: pools start only from misses, and a person has at most `max_pools`.

Only the clips the selection keeps are saved: the most consistent full-length windows of the speaker.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import soundfile as sf

from src.asr.utils.config import LibrarySettings, get_paths_settings
from src.asr.utils.output_format import format_offset
from src.asr.voice_library import AUDIO_EXTS
from src.paths import slug
from src.transcriber import voices
from src.transcriber.summary import INVALID_ARGUMENTS, OK, CommandError, guarded, say
from src.transcriber.transcript import UNATTRIBUTED_DISPLAY, is_anonymous


REMOVE_COMMAND = "remove-clips"
CLIPS_FOLDER = "registrazioni"
CLIPS_RECORD = "clip.json"
# What a naming is to the library: a person new to it, a confirmation, or a recognition that was missed.
NEW, CONFIRM, MISS = "new", "confirm", "miss"
# A pool of one or two clips proved noisy, so a miss with fewer kept clips starts no pool.
MIN_NEW_POOL_CLIPS = 3

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
    keep: bool = True
    voiceprint: np.ndarray | None = None


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
    Rank a speaker's full-length windows, best first, and mark the ones the selection keeps.

    Every window with a voiceprint counts in the consistency score, but only full-length ones become clips.
    The selection keeps at most `keep_clips` windows, and none below `min_consistency`.
    """
    measured = [(window, voiceprint) for window, voiceprint in zip(windows, voiceprints) if voiceprint is not None]
    scores = consistency_scores([voiceprint for _, voiceprint in measured])
    candidates = [
        Candidate(start=float(window["start"]), end=float(window["end"]), consistency=score, voiceprint=voiceprint)
        for (window, voiceprint), score in zip(measured, scores)
        if float(window["end"]) - float(window["start"]) >= window_sec - _FULL_LENGTH_TOLERANCE_SEC
    ]
    candidates.sort(key=lambda candidate: (-(candidate.consistency or 0.0), candidate.start))
    kept = 0
    for candidate in candidates:
        consistent = candidate.consistency is None or candidate.consistency >= selection.min_consistency
        candidate.keep = consistent and kept < selection.keep_clips
        kept += candidate.keep
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


def clip_filename(recording_file: str, start: float) -> str:
    """
    Name a clip after its recording and the window's start, without spaces: "riunione-00-12-34.wav".
    """
    # A speaker's windows never overlap and last at least matching.min_window_sec, so seconds are enough.
    return f"{slug(Path(recording_file).stem)}-{format_offset(start).replace(':', '-')}.wav"


def is_added_pool(folder: Path) -> bool:
    """
    Tell a pool of clips added by naming, known by its clip record, from a folder made by hand.
    """
    return folder.is_dir() and (folder.name == CLIPS_FOLDER or (folder / CLIPS_RECORD).is_file())


def added_pools(person_dir: Path) -> list[Path]:
    if not person_dir.is_dir():
        return []
    return sorted(entry for entry in person_dir.iterdir() if is_added_pool(entry))


def _audio_files(folder: Path, *, recursive: bool) -> list[Path]:
    files = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(path for path in files if path.is_file() and path.suffix.lower() in AUDIO_EXTS)


def pool_clips(person_dir: Path) -> dict[Path, list[Path]]:
    """
    Return the person's pools as recognition reads them: the clips directly in the folder, and each subfolder.
    """
    if not person_dir.is_dir():
        return {}
    pools = {person_dir: _audio_files(person_dir, recursive=False)}
    pools |= {entry: _audio_files(entry, recursive=True) for entry in sorted(person_dir.iterdir()) if entry.is_dir()}
    return {pool: clips for pool, clips in pools.items() if clips}


def choose_pool(
    person_dir: Path,
    *,
    kind: str,
    kept: int,
    transcript_folder: str,
    max_pools: int,
    similarity: Callable[[Path], float],
) -> Path:
    """
    Return the pool a naming puts its clips in.

    A person new to the library starts `registrazioni`. A confirmation joins the pool closest to the speaker,
    or `registrazioni` when that pool was made by hand. A miss starts a pool named after the transcript's
    folder, unless it kept fewer than MIN_NEW_POOL_CLIPS clips or the person has max_pools added pools: then
    it joins the closest added pool. `similarity` scores a pool against the speaker's kept clips.
    """
    first = person_dir / CLIPS_FOLDER
    if kind == NEW:
        return first
    if kind == CONFIRM:
        pools = list(pool_clips(person_dir))
        closest = max(pools, key=similarity) if pools else first
        return closest if closest != person_dir and is_added_pool(closest) else first
    added = added_pools(person_dir)
    name = slug(transcript_folder)
    folder, count = person_dir / name, 1
    while folder.exists() and not is_added_pool(folder):
        count += 1
        folder = person_dir / f"{name}-{count}"
    if folder in added or (kept >= MIN_NEW_POOL_CLIPS and len(added) < max_pools):
        return folder
    return max(added, key=similarity) if added else first


def similarity_to(
    kept: list[Candidate], person_dir: Path, voiceprint_of: Callable[[Path], np.ndarray]
) -> Callable[[Path], float]:
    """
    Score a pool of the person against the speaker's kept clips: the cosine of the two normalized means.

    Each pool's voiceprints are computed only when it is scored, and once.
    """
    speaker = _unit(np.mean([candidate.voiceprint for candidate in kept if candidate.voiceprint is not None], axis=0))
    clips = pool_clips(person_dir)
    scores: dict[Path, float] = {}

    def similarity(pool: Path) -> float:
        if pool not in scores:
            files = clips.get(pool)
            pool_voiceprint = _unit(np.mean([voiceprint_of(path) for path in files], axis=0)) if files else None
            scores[pool] = float(np.dot(speaker, pool_voiceprint)) if pool_voiceprint is not None else -1.0
        return scores[pool]

    return similarity


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _present_record(folder: Path) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Return the pool's clip record without the entries of deleted clips, and {record key: file name} of its clips.
    """
    record = _read_json(folder / CLIPS_RECORD, {})
    present = {path.name.casefold(): path.name for path in folder.glob("*") if path.is_file()} if folder.is_dir() else {}
    record = {key: origin for key, origin in record.items() if key.casefold() in present}
    return record, {key: present[key.casefold()] for key in record}


def save_clips(folder: Path, audio: np.ndarray, candidates: list[Candidate], *, origin: dict[str, Any]) -> list[str]:
    """
    Cut the kept candidates from the recording into a pool and record where each came from.

    `origin` describes the recording, the transcript and the label the clips came from. Writing the record
    drops the entries of clips the person deleted.
    """
    candidates = [candidate for candidate in candidates if candidate.keep]
    if not candidates:
        return []
    folder.mkdir(parents=True, exist_ok=True)
    record_path = folder / CLIPS_RECORD
    record, _ = _present_record(folder)
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
            "saved": datetime.now().isoformat(timespec="seconds"),
        }
        saved.append(filename)
    _write_json(record_path, record)
    return saved


def cap_proposal(folder: Path, cap: int) -> list[str]:
    """
    Propose which clips of an added pool to remove to get it back to `cap`.

    Clips go from the recording that has the most of them in the pool, least consistent first, so different
    recordings stay. Only clips the transcriber added count; clips placed by hand never do.
    """
    record, present = _present_record(folder)
    excess = len(present) - cap
    if excess <= 0:
        return []
    by_recording: dict[str, list[str]] = {}
    for key in present:
        by_recording.setdefault(str(record[key].get("recording_file")), []).append(key)
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
    Delete the given added clips of a person, as the person confirmed, and drop them from their clip records.

    A file that is not a recorded clip in one of the person's added pools is refused, never deleted.
    """
    pools = {folder: _present_record(folder) for folder in added_pools(Path(library_dir) / person)}
    removed, refused, changed = [], [], set()
    for filename in filenames:
        wanted = Path(filename).name.casefold()
        found = next(
            ((folder, key) for folder, (_, present) in pools.items() for key in present if key.casefold() == wanted), None
        )
        if found is None:
            refused.append({"clip": filename, "reason": "non è una clip aggiunta dal trascrittore per questa persona"})
            continue
        folder, key = found
        record, present = pools[folder]
        clip = present.pop(key)
        (folder / clip).unlink()
        del record[key]
        removed.append(clip)
        changed.add(folder)
    for folder in changed:
        _write_json(folder / CLIPS_RECORD, pools[folder][0])
    return removed, refused


def remove_clips_report(person: str, filenames: list[str]) -> dict[str, Any]:
    """
    The remove-clips command: delete added clips the person confirmed, after a naming passed the cap.
    """

    def report() -> dict[str, Any]:
        folder = library_dir()
        if folder is None or not folder.is_dir():
            raise CommandError(INVALID_ARGUMENTS, "La libreria delle voci non è configurata o non esiste.")
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
