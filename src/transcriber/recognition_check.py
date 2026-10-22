"""
The recognition check: how well this PC's voice library recognizes the people in its named transcripts.

It repeats the 2026-09-24 calibration as a command, with three precautions against fooling itself:

1. only the voices a person named count as known: a name the transcriber gave by itself may be wrong;
2. each recording is scored against the library without the clips cut from that recording, known by
   the recording's name at the start of their file names, so no speaker is matched against their own clips;
3. voices missing from the library are simulated by removing one named person at a time.

It suggests a threshold above every wrong name, with some slack, but never writes trascrittore.ini:
a person applies the suggestion.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.asr.utils.config import get_matching_settings
from src.asr.utils.diarization_utils import match_speakers_to_names_with_diagnostics
from src.transcriber import library, naming, voices
from src.transcriber.summary import INVALID_ARGUMENTS, OK, CommandError, guarded, host_path, say
from src.transcriber.transcript import UNATTRIBUTED_DISPLAY, is_anonymous


COMMAND = "check"
LIBRARY = "library"
MISSING = "missing"
# The 2026-09-24 calibration put the threshold 0.035 above the best-scoring missing voice.
SUGGESTION_SLACK = 0.03
# With fewer simulated missing voices a suggestion would rest on chance; that calibration had 7 voices missing
# from the library besides the simulated ones.
MIN_MISSING_FOR_SUGGESTION = 10
# Accept every candidate that passes the margin: outcomes at any threshold follow from these.
_NO_THRESHOLD = -1.0

RecordingKey = str


@dataclass(frozen=True)
class LibraryClip:
    person: str
    pool: str
    voiceprint: np.ndarray
    # The recording the clip was cut from, read from its file name; None for a clip placed by hand.
    recording: RecordingKey | None = None


@dataclass
class CheckedSpeaker:
    label: str
    voiceprints: list[np.ndarray]


@dataclass
class CheckedRecording:
    name: str
    key: RecordingKey
    speakers: list[CheckedSpeaker]


@dataclass
class Outcome:
    recording: str
    label: str
    scenario: str
    # The person the speaker is, when the library scored against still holds them.
    truth: str | None
    best_name: str | None
    best_score: float | None
    # The name recognition gives with no threshold at all; a threshold only removes lower scores.
    accepted: str | None
    true_score: float | None


def recording_key(recording_name: str) -> RecordingKey:
    # Windows file names ignore case. Two recordings with the same name lose each other's clips too,
    # which only makes the check stricter.
    return recording_name.casefold()


def library_pools(clips: list[LibraryClip], *, without_recording: RecordingKey | None = None) -> dict[str, list[np.ndarray]]:
    """
    Build each person's pool voiceprints as recognition does: the normalized mean of the pool's clips.
    """
    by_pool: dict[tuple[str, str], list[np.ndarray]] = {}
    for clip in clips:
        if without_recording is not None and clip.recording == without_recording:
            continue
        by_pool.setdefault((clip.person, clip.pool), []).append(clip.voiceprint)
    pools: dict[str, list[np.ndarray]] = {}
    for (person, _), voiceprints in by_pool.items():
        mean = np.mean(np.stack(voiceprints), axis=0)
        pools.setdefault(person, []).append(mean / (np.linalg.norm(mean) + 1e-9))
    return pools


def _outcome(recording: CheckedRecording, speaker: CheckedSpeaker, scenario: str, truth: str | None, diag: dict[str, Any]) -> Outcome:
    best_name = diag.get("best_name")
    return Outcome(
        recording=recording.name,
        label=speaker.label,
        scenario=scenario,
        truth=truth,
        best_name=best_name,
        best_score=float(diag["best_score"]) if best_name else None,
        accepted=diag["assigned_label"] if diag.get("rejection_reason") == "accepted" else None,
        true_score=float(diag["scores"][truth]) if truth in diag.get("scores", {}) else None,
    )


def evaluate(clips: list[LibraryClip], recordings: list[CheckedRecording], *, margin: float) -> list[Outcome]:
    """
    Score every named speaker of every recording, and again with their own person removed from the library.
    """
    outcomes: list[Outcome] = []
    for recording in recordings:
        pools = library_pools(clips, without_recording=recording.key)
        speakers = {
            str(index): speaker
            for index, speaker in enumerate(recording.speakers)
            if speaker.voiceprints and not is_anonymous(speaker.label) and speaker.label != UNATTRIBUTED_DISPLAY
        }
        if not speakers or not pools:
            continue
        voiceprints = {key: speaker.voiceprints for key, speaker in speakers.items()}
        matched = match_speakers_to_names_with_diagnostics(voiceprints, pools, threshold=_NO_THRESHOLD, margin=margin)
        for key, speaker in speakers.items():
            truth = speaker.label if speaker.label in pools else None
            outcomes.append(_outcome(recording, speaker, LIBRARY, truth, matched.diagnostics["speakers"][key]))
            others = {person: refs for person, refs in pools.items() if person != truth}
            if truth is None or not others:
                continue
            without = match_speakers_to_names_with_diagnostics(voiceprints, others, threshold=_NO_THRESHOLD, margin=margin)
            outcomes.append(_outcome(recording, speaker, MISSING, None, without.diagnostics["speakers"][key]))
    return outcomes


def counts_at(outcomes: list[Outcome], threshold: float) -> dict[str, int]:
    """
    Count right names, wrong names and missed people at a threshold.

    Candidates are assigned best score first, so raising the threshold only drops the lowest-scoring
    assignments and never hands a name to someone else: the outcomes found with no threshold are enough.
    """
    counts = {"right": 0, "wrong": 0, "missed": 0, "wrong_when_missing": 0}
    for outcome in outcomes:
        accepted = outcome.accepted if outcome.accepted and outcome.best_score >= threshold else None
        if outcome.scenario == MISSING:
            counts["wrong_when_missing"] += accepted is not None
        elif outcome.truth is None:
            counts["wrong"] += accepted is not None
        elif accepted == outcome.truth:
            counts["right"] += 1
        elif accepted:
            counts["wrong"] += 1
        else:
            counts["missed"] += 1
    return counts


def _range(scores: list[float]) -> dict[str, Any]:
    return {
        "count": len(scores),
        "min": round(min(scores), 3) if scores else None,
        "max": round(max(scores), 3) if scores else None,
    }


def report(
    outcomes: list[Outcome], *, threshold: float, margin: float, min_missing: int = MIN_MISSING_FOR_SUGGESTION
) -> dict[str, Any]:
    known = [o.true_score for o in outcomes if o.scenario == LIBRARY and o.truth and o.true_score is not None]
    missing = [o.best_score for o in outcomes if o.truth is None and o.best_score is not None]
    # A person of the library taken for another one is a wrong name too.
    confused = [o.best_score for o in outcomes if o.scenario == LIBRARY and o.truth and o.accepted not in (None, o.truth)]
    current = {"threshold": threshold, "margin": margin, **counts_at(outcomes, threshold)}
    suggested = None
    if missing and len(missing) >= min_missing:
        suggested_threshold = math.ceil((max(missing + confused) + SUGGESTION_SLACK) * 1000) / 1000
        suggested = {"threshold": suggested_threshold, **counts_at(outcomes, suggested_threshold)}
        suggested["lost"] = current["right"] - suggested["right"]
    return {"known_voices": _range(known), "missing_voices": _range(missing), "current": current, "suggested": suggested}


def _library_clips(library_dir: Path, voiceprints: voices.Voiceprints) -> list[LibraryClip]:
    from src.asr.voice_library import scan_voice_library

    voice_library = scan_voice_library(str(library_dir))
    total = sum(len(clips) for pools in voice_library.values() for clips in pools.values())
    say(f"Calcolo le impronte delle {total} clip della libreria...")
    clips = []
    for person, pools in voice_library.items():
        for pool, paths in pools.items():
            for path in paths:
                try:
                    voiceprint = voiceprints.of_clip(path)
                except (RuntimeError, ValueError):
                    say(f"  salto una clip illeggibile: {host_path(path)}")
                    continue
                recording = library.clip_recording(path)
                clips.append(LibraryClip(person, pool, voiceprint, recording_key(recording) if recording else None))
    return clips


def _discover_pairs(library_dir: Path) -> list[tuple[str, str]]:
    pairs: dict[str, str] = {}
    for origin in library.clip_records(library_dir):
        if origin.get("transcript") and origin.get("recording"):
            pairs.setdefault(origin["transcript"], origin["recording"])
    return list(pairs.items())


def _checked_recording(transcript: str, recording: str, voiceprints: voices.Voiceprints) -> CheckedRecording:
    transcript_path = Path(transcript)
    payload = naming.load_transcript(transcript_path)
    speakers = payload.get("speakers", [])
    if not any("windows" in speaker for speaker in speakers):
        raise CommandError(INVALID_ARGUMENTS, "trascrizione di una versione precedente, senza i tratti delle voci")
    named = [speaker for speaker in speakers if speaker.get("named") and speaker.get("windows")]
    if not named:
        raise CommandError(INVALID_ARGUMENTS, "nessuna voce a cui una persona ha dato il nome")
    audio, problem = naming.open_recording(payload, transcript_path, recording)
    if audio is None:
        raise CommandError(INVALID_ARGUMENTS, problem)
    checked = []
    for speaker in named:
        computed = [voiceprint for voiceprint in voiceprints.of_windows(audio, speaker["windows"]) if voiceprint is not None]
        checked.append(CheckedSpeaker(label=speaker["label"], voiceprints=computed))
    return CheckedRecording(
        name=payload["file"], key=recording_key(library.recording_name(payload["file"])), speakers=checked
    )


def _report_lines(result: dict[str, Any], checked: int, skipped: list[dict[str, str]]) -> list[str]:
    known, missing, current, suggested = (
        result["known_voices"],
        result["missing_voices"],
        result["current"],
        result["suggested"],
    )
    lines = ["Verifica del riconoscimento delle voci", f"Registrazioni verificate: {checked}."]
    lines += [f"  saltata {entry['transcript']}: {entry['reason']}" for entry in skipped]
    if not known["count"] and not missing["count"]:
        lines.append(
            "Niente da verificare: serve una trascrizione con nomi di persone che hanno nella libreria anche clip "
            "di altre registrazioni o messe a mano. Dai un nome alle voci di altre registrazioni e riprova."
        )
        return lines
    if not known["count"]:
        lines.append("Nessuna voce della libreria da verificare: le persone con nome hanno clip solo di questa registrazione.")
        return lines
    lines.append(f"Voci nella libreria: punteggi da {known['min']:.3f} a {known['max']:.3f} ({known['count']} voci).")
    if missing["count"]:
        lines.append(
            f"Voci assenti dalla libreria: punteggio più alto {missing['max']:.3f} ({missing['count']} casi simulati)."
        )
    lines.append(f"Con soglia {current['threshold']:.3f} e margine {current['margin']:.2f}:")
    lines.append(
        f"  nomi giusti {current['right']}, nomi sbagliati {current['wrong']}, "
        f"persone della libreria rimaste 'Persona N' {current['missed']};"
    )
    lines.append(f"  voci tolte dalla libreria a cui andrebbe un nome sbagliato: {current['wrong_when_missing']}.")
    if suggested:
        change = (
            f"perderebbe {suggested['lost']} riconoscimenti"
            if suggested["lost"] >= 0
            else f"recupererebbe {-suggested['lost']} riconoscimenti"
        )
        lines.append(
            f"Soglia suggerita: {suggested['threshold']:.3f} ({change}; nomi sbagliati "
            f"{suggested['wrong'] + suggested['wrong_when_missing']})."
        )
        lines.append(
            f"Per applicarla scrivi threshold = {suggested['threshold']:.3f} sotto la riga [matching] di trascrittore.ini: "
            "la verifica non la cambia da sola."
        )
    else:
        lines.append(
            f"Nessuna soglia suggerita: servono almeno {MIN_MISSING_FOR_SUGGESTION} voci assenti simulate, "
            f"ce ne sono {missing['count']}. Dai un nome alle voci di altre registrazioni."
        )
    return lines


def _run_check(pairs: list[tuple[str, str]] | None, missing: list[str]) -> dict[str, Any]:
    library_dir = library.library_dir()
    if library_dir is None or not library_dir.is_dir():
        raise CommandError(INVALID_ARGUMENTS, "La libreria delle voci non è configurata o non esiste.")
    pairs = _discover_pairs(library_dir) if pairs is None else pairs
    skipped = [{"transcript": path, "reason": "file non trovato"} for path in missing]
    voiceprints = voices.Voiceprints()
    clips = _library_clips(library_dir, voiceprints)
    recordings = []
    for index, (transcript, recording) in enumerate(pairs, start=1):
        say(f"Registrazione {index}/{len(pairs)}: {Path(transcript).name}")
        try:
            recordings.append(_checked_recording(transcript, recording, voiceprints))
        except CommandError as exc:
            skipped.append({"transcript": host_path(transcript), "reason": exc.message})
    matching = get_matching_settings()
    result = report(evaluate(clips, recordings, margin=matching.margin), threshold=matching.threshold, margin=matching.margin)

    lines = _report_lines(result, len(recordings), skipped)
    say("")
    for line in lines:
        say(line)
    return {
        "command": COMMAND,
        "status": OK,
        "message": " ".join(line.strip() for line in lines[1:]),
        "recordings_checked": len(recordings),
        "skipped": skipped,
        **result,
    }


def run_check(pairs: list[tuple[str, str]] | None = None, *, missing: list[str] | None = None) -> dict[str, Any]:
    """
    Check recognition on the named transcripts found on this PC, or on the given transcript and recording pairs.

    The launcher always passes pairs, since inside the container the library's records name paths of the PC.
    """
    return guarded(COMMAND, lambda: _run_check(pairs, missing or []), failed="La verifica non è riuscita")
