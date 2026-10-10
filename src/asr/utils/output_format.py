from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, NamedTuple, Tuple

from src.asr.transcript_cleaning import clean_transcript_turns
from src.asr.utils.config import config


def _parse_recording_start(input_path: str) -> datetime | None:
    """
    Parse the recording start datetime from the input filename using config format.

    Returns None for free-form names, which most recordings have.
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


class Word(NamedTuple):
    text: str
    start: float
    end: float


class SpeakerTurn(NamedTuple):
    speaker: str
    start: float
    end: float
    words: list[Word]


def _turn(speaker: str, words: list[Word]) -> SpeakerTurn:
    return SpeakerTurn(speaker, words[0].start, max(word.end for word in words), words)


def _iter_words_with_speakers(result: Dict[str, Any]) -> Iterable[Tuple[str, str, float, float]]:
    """
    Yield normalized (word, speaker_label, word_start_sec, word_end_sec) tuples from WhisperX output.
    """
    previous_end = 0.0
    for seg in result.get("segments", []):
        segment_speaker = seg.get("speaker") or "UNATTRIBUTED"
        segment_start = float(seg.get("start", 0.0))
        for w in seg.get("words", []):
            word = (w.get("word") or "").strip()
            if not word:
                continue
            speaker = w.get("speaker") or segment_speaker
            # whisperX leaves the words it cannot align, such as numbers, without times: they follow the previous word.
            start = float(w.get("start", max(segment_start, previous_end)))
            end = float(w.get("end", start))
            previous_end = end
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


_SENTENCE_ENDS = (".", "?", "!", "…")
_CLOSING_MARKS = "\"'»”)]"
# A diarization boundary a few hundred milliseconds off moves one to three words across it.
_MAX_EDGE_WORDS = 3


def _ends_sentence(word: Word) -> bool:
    return word.text.rstrip(_CLOSING_MARKS).endswith(_SENTENCE_ENDS)


def _first_letter(word: Word) -> str:
    return next((char for char in word.text if char.isalpha()), "")


def _starts_lowercase(word: Word) -> bool:
    return _first_letter(word).islower()


def _sentence_end_at_start(earlier: SpeakerTurn, later: SpeakerTurn) -> int:
    """
    Count the words that open `later` and close the sentence `earlier` left unfinished, or 0.
    """
    if _ends_sentence(earlier.words[-1]) or not _starts_lowercase(later.words[0]):
        return 0
    for count, word in enumerate(later.words[:_MAX_EDGE_WORDS], start=1):
        if _ends_sentence(word):
            return count
    return 0


def _sentence_start_at_end(earlier: SpeakerTurn, later: SpeakerTurn) -> int:
    """
    Count the words that close `earlier` and open the sentence `later` goes on with, or 0.
    """
    if not _starts_lowercase(later.words[0]):
        return 0
    last_end = max((i for i, word in enumerate(earlier.words) if _ends_sentence(word)), default=-1)
    count = len(earlier.words) - last_end - 1
    if not 0 < count <= _MAX_EDGE_WORDS or not _first_letter(earlier.words[-count]).isupper():
        return 0
    return count


def _move_sentence_edges(turns: list[SpeakerTurn]) -> list[SpeakerTurn]:
    """
    Move to the neighbouring turn the edge of a sentence that the diarization put on the wrong side.

    Punctuation on both sides of a change of speaker must agree; see
    docs/implementation/speaker-turn-boundaries.md.
    """
    moved: list[SpeakerTurn] = []
    for turn in turns:
        if moved:
            earlier = moved[-1]
            back = _sentence_end_at_start(earlier, turn)
            forward = _sentence_start_at_end(earlier, turn)
            # When both apply, either speaker could have said the sentence: leave it where it is.
            if back and not forward:
                moved[-1] = _turn(earlier.speaker, earlier.words + turn.words[:back])
                if back == len(turn.words):
                    continue
                turn = _turn(turn.speaker, turn.words[back:])
            elif forward and not back:
                turn = _turn(turn.speaker, earlier.words[-forward:] + turn.words)
                if forward == len(earlier.words):
                    moved.pop()
                else:
                    moved[-1] = _turn(earlier.speaker, earlier.words[:-forward])
        moved.append(turn)
    return _merge_adjacent_turns(moved)


def _speaker_turns(mapping: Dict[str, str], result: Dict[str, Any]) -> list[SpeakerTurn]:
    turns: list[SpeakerTurn] = []
    current: SpeakerTurn | None = None

    for word, raw_speaker, start, end in _iter_words_with_speakers(result):
        speaker = mapping.get(raw_speaker, raw_speaker)

        if current is None or speaker != current.speaker:
            if current is not None:
                turns.append(current)
            current = SpeakerTurn(speaker, start, end, [Word(word, start, end)])
        else:
            current.words.append(Word(word, start, end))
            current = current._replace(end=max(current.end, end))

    if current is not None:
        turns.append(current)

    return _move_sentence_edges(_smooth_short_turns(turns))


# A pause this long inside a sentence ends a segment, so that the gaps between segments show every pause.
_SEGMENT_PAUSE_SEC = 1.0


def _segment_words(words: list[Word]) -> list[list[Word]]:
    """
    Split a turn's words into sentences, and a sentence where the speaker pauses.
    """
    segments: list[list[Word]] = []
    current: list[Word] = []
    for word in words:
        if current and word.start - current[-1].end >= _SEGMENT_PAUSE_SEC:
            segments.append(current)
            current = []
        current.append(word)
        if _ends_sentence(word):
            segments.append(current)
            current = []
    if current:
        segments.append(current)
    return segments


def _segments(turn: SpeakerTurn) -> list[dict[str, Any]]:
    return [
        {
            "start_sec": round(words[0].start, 3),
            "end_sec": round(max(word.end for word in words), 3),
            "text": " ".join(word.text for word in words),
        }
        for words in _segment_words(turn.words)
    ]


def build_transcript_turns(
    result: Dict[str, Any],
    input_path: str,
    mapping: Dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Build cleaned speaker turns with time, start/end seconds and timed segments from a word-level result.

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
            "text": " ".join(word.text for word in turn.words).strip(),
            "segments": _segments(turn),
        }
        for turn in _speaker_turns(mapping or {}, result)
    ]
    return clean_transcript_turns(turns)
