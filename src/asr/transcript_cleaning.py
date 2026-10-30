from __future__ import annotations

import re
from typing import Any


_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")
_PROMPT_PATTERN_CACHE: dict[str, re.Pattern[str] | None] = {}
_FILLERS = {"eh", "ehm", "mh", "mmh", "uh", "ah"}

_BOILERPLATE_SNIPPET_RES = (
    re.compile(r"\bgrazie\s+per\s+la\s+visione\b", re.IGNORECASE),
    re.compile(r"\bgrazie\s+per\s+aver\s+guardato\s+il\s+video\b", re.IGNORECASE),
    re.compile(r"\bgrazie\s+a\s+tutti\s+per\s+aver\s+guardato\s+il\s+video\b", re.IGNORECASE),
    re.compile(r"\bgrazie\s+(?:a\s+tutti\s+)?per\s+aver(?:mi|ci)\s+seguit[oaie]\b[.!?…]?", re.IGNORECASE),
    re.compile(
        r"\b(?:autore\s+dei\s+)?sottotitoli?\s+e\s+revisione\s+a\s+cura\s+di\s+qtss(?:\s+grazie)?\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bqtss\b", re.IGNORECASE),
)


def _normalize_text(text: str) -> str:
    lowered = text.casefold()
    without_punctuation = _PUNCTUATION_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", without_punctuation).strip()


def _configured_initial_prompt() -> str:
    from src.asr.utils.config import config

    section = config["whisper"] if "whisper" in config else {}
    return section.get("initial_prompt", "").strip()


def _prompt_pattern() -> re.Pattern[str] | None:
    """
    Match the whole configured prompt, whatever its case and punctuation.
    """
    normalized_prompt = _normalize_text(_configured_initial_prompt())
    if normalized_prompt not in _PROMPT_PATTERN_CACHE:
        tokens = normalized_prompt.split()
        phrase = r"[\W_]+".join(re.escape(token) for token in tokens)
        _PROMPT_PATTERN_CACHE[normalized_prompt] = (
            re.compile(rf"\b{phrase}\b[.!?…]?", re.IGNORECASE) if tokens else None
        )
    return _PROMPT_PATTERN_CACHE[normalized_prompt]


# Separators left at the edges of a cleaned text, as after "Grazie per la visione, ciao".
_EDGE_SEPARATORS = ",;:-"


def _view(text: str, kept: list[bool]) -> tuple[str, list[int | None]]:
    """
    Return the text as cleaning sees it, each removed stretch shown as one space, and where each of
    its characters comes from in `text` (None for those spaces).
    """
    chars: list[str] = []
    origin: list[int | None] = []
    for position, char in enumerate(text):
        if kept[position]:
            chars.append(char)
            origin.append(position)
        elif not origin or origin[-1] is not None:
            chars.append(" ")
            origin.append(None)
    return "".join(chars), origin


def _kept_characters(text: str) -> list[bool]:
    """
    Mark the characters of a text that cleaning keeps.

    Known phrases go wherever they appear and the prompt only where it appears whole; then the
    spaces and separators left at the two ends go too.
    """
    kept = [True] * len(text)
    patterns = list(_BOILERPLATE_SNIPPET_RES)
    prompt_pattern = _prompt_pattern()
    if prompt_pattern is not None:
        patterns.append(prompt_pattern)
    for pattern in patterns:
        view, origin = _view(text, kept)
        for match in pattern.finditer(view):
            for position in origin[match.start():match.end()]:
                if position is not None:
                    kept[position] = False
    for positions in (range(len(text)), reversed(range(len(text)))):
        for position in positions:
            if not kept[position]:
                continue
            if not (text[position].isspace() or text[position] in _EDGE_SEPARATORS):
                break
            kept[position] = False
    return kept


def _render(text: str, kept: list[bool]) -> str:
    return _WHITESPACE_RE.sub(" ", _view(text, kept)[0]).strip()


def clean_transcript_text(text: str) -> str:
    """
    Strip known ASR boilerplate snippets from a single transcript turn.
    """
    return _render(text, _kept_characters(text))


def _is_noise(cleaned: str) -> bool:
    normalized = _normalize_text(cleaned)
    # A short answer such as "No." changes what a transcript says; only sounds without meaning go.
    return not normalized or all(token in _FILLERS for token in normalized.split())


def is_obvious_transcript_noise(text: str) -> bool:
    """
    Return True for ASR boilerplate that is very unlikely to be useful speech.
    """
    return _is_noise(clean_transcript_text(text))


def _clean_segments(text: str, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove from each segment the characters that cleaning removes from its turn's text.

    A phrase or prompt split across segments goes from each of them, and the words beside it stay.
    A segment left without words goes, with the punctuation it kept. Fillers stay, as in the turn.
    """
    if " ".join(str(segment["text"]) for segment in segments) != text:
        raise ValueError("A turn's text must be its segments' texts joined by spaces.")
    kept = _kept_characters(text)
    cleaned: list[dict[str, Any]] = []
    start = 0
    for segment in segments:
        end = start + len(str(segment["text"]))
        segment_text = _render(text[start:end], kept[start:end])
        if _normalize_text(segment_text):
            cleaned.append({**segment, "text": segment_text})
        start = end + 1
    # Dropping a segment can leave a separator at an end of the turn, as in "ciao a tutti, !".
    if cleaned:
        cleaned[0]["text"] = cleaned[0]["text"].lstrip(" " + _EDGE_SEPARATORS)
        cleaned[-1]["text"] = cleaned[-1]["text"].rstrip(" " + _EDGE_SEPARATORS)
    return cleaned


def clean_transcript_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove clearly hallucinated boilerplate turns while preserving metadata.

    A turn with segments takes its text from its cleaned segments, so the two always agree.
    """
    cleaned: list[dict[str, Any]] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        text = str(turn.get("text", ""))
        cleaned_turn = dict(turn)
        if "segments" in turn:
            cleaned_turn["segments"] = _clean_segments(text, turn["segments"])
            cleaned_turn["text"] = " ".join(segment["text"] for segment in cleaned_turn["segments"])
        else:
            cleaned_turn["text"] = clean_transcript_text(text)
        if _is_noise(cleaned_turn["text"]):
            continue
        cleaned.append(cleaned_turn)
    return cleaned
