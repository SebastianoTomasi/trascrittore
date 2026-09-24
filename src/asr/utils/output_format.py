from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, NamedTuple, Tuple

from src.asr.transcript_cleaning import clean_transcript_turns
from src.asr.utils.config import config


def _parse_recording_start(input_path: str) -> datetime | None:
    """
    Parse the recording start datetime from the input filename using config format.

    Returns None for free-form names such as meeting recordings.
    """
    fname = os.path.splitext(os.path.basename(input_path))[0]
    try:
        return datetime.strptime(fname, config["time"]["filename_format"])
    except ValueError:
        return None


def _format_turn_timestamp(recording_start: datetime, seconds_from_start: float) -> str:
    """
    Format a compact speaker-turn timestamp (HH:MM) from relative seconds.
    """
    dt = recording_start + timedelta(seconds=float(seconds_from_start))
    return dt.strftime("%H:%M")


def format_offset(seconds_from_start: float) -> str:
    """
    Format seconds from the start of the recording as HH:MM:SS.
    """
    hours, rest = divmod(max(0, int(seconds_from_start)), 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _turn_time(recording_start: datetime | None, seconds_from_start: float) -> str:
    if recording_start is None:
        return format_offset(seconds_from_start)
    return _format_turn_timestamp(recording_start, seconds_from_start)


class SpeakerTurn(NamedTuple):
    speaker: str
    start: float
    end: float
    words: list[str]


def _iter_words_with_speakers(result: Dict[str, Any]) -> Iterable[Tuple[str, str, float, float]]:
    """
    Yield normalized (word, speaker_label, word_start_sec, word_end_sec) tuples from WhisperX output.
    """
    for seg in result.get("segments", []):
        segment_speaker = seg.get("speaker") or "UNKNOWN"
        segment_start = float(seg.get("start", 0.0))
        for w in seg.get("words", []):
            word = (w.get("word") or "").strip()
            if not word:
                continue
            speaker = w.get("speaker") or segment_speaker
            start = float(w.get("start", segment_start))
            end = float(w.get("end", start))
            yield word, speaker, start, end


def _merge_adjacent_turns(turns: list[SpeakerTurn]) -> list[SpeakerTurn]:
    merged: list[SpeakerTurn] = []
    for turn in turns:
        if merged and merged[-1].speaker == turn.speaker:
            prev = merged[-1]
            merged[-1] = prev._replace(end=max(prev.end, turn.end), words=prev.words + turn.words)
        else:
            merged.append(turn)
    return merged


def _smooth_short_turns(
    turns: list[SpeakerTurn],
    max_words: int = 3,
) -> list[SpeakerTurn]:
    """
    Absorb isolated short speaker flips when the surrounding turns agree.
    """
    if len(turns) < 3:
        return turns

    smoothed = turns[:]
    changed = True
    while changed:
        changed = False
        next_turns: list[SpeakerTurn] = []
        i = 0
        while i < len(smoothed):
            if (
                0 < i < len(smoothed) - 1
                and len(smoothed[i].words) <= max_words
                and smoothed[i - 1].speaker == smoothed[i + 1].speaker
                and smoothed[i].speaker != smoothed[i - 1].speaker
            ):
                prev = next_turns.pop()
                following = smoothed[i + 1]
                next_turns.append(
                    prev._replace(
                        end=max(prev.end, following.end),
                        words=prev.words + smoothed[i].words + following.words,
                    )
                )
                i += 2
                changed = True
                continue

            next_turns.append(smoothed[i])
            i += 1
        smoothed = _merge_adjacent_turns(next_turns)

    return smoothed


def _speaker_turns(mapping: Dict[str, str], result: Dict[str, Any]) -> list[SpeakerTurn]:
    turns: list[SpeakerTurn] = []
    current: SpeakerTurn | None = None

    for word, raw_speaker, start, end in _iter_words_with_speakers(result):
        speaker = mapping.get(raw_speaker, raw_speaker)

        if current is None or speaker != current.speaker:
            if current is not None:
                turns.append(current)
            current = SpeakerTurn(speaker, start, end, [word])
        else:
            current.words.append(word)
            current = current._replace(end=max(current.end, end))

    if current is not None:
        turns.append(current)

    return _smooth_short_turns(turns)


def build_transcript_turns(
    result: Dict[str, Any],
    input_path: str,
    mapping: Dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Build cleaned speaker turns with time and start/end seconds from a word-level result.

    `time` is wall-clock HH:MM when the filename encodes the recording start, and
    HH:MM:SS from the start of the recording otherwise.
    """
    recording_start = _parse_recording_start(input_path)
    turns = [
        {
            "speaker": turn.speaker,
            "time": _turn_time(recording_start, turn.start),
            "start_sec": round(turn.start, 3),
            "end_sec": round(turn.end, 3),
            "text": " ".join(turn.words).strip(),
        }
        for turn in _speaker_turns(mapping or {}, result)
    ]
    return clean_transcript_turns(turns)
