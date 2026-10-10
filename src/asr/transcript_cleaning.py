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


def clean_transcript_text(text: str) -> str:
    """
    Strip known ASR boilerplate snippets from a single transcript turn.
    """
    cleaned = text.strip()
    for pattern in _BOILERPLATE_SNIPPET_RES:
        cleaned = pattern.sub(" ", cleaned)
    prompt_pattern = _prompt_pattern()
    if prompt_pattern is not None:
        cleaned = prompt_pattern.sub(" ", cleaned)
    return _WHITESPACE_RE.sub(" ", cleaned).strip(" ,;:-")


def is_obvious_transcript_noise(text: str) -> bool:
    """
    Return True for ASR boilerplate that is very unlikely to be useful speech.
    """
    stripped = clean_transcript_text(text)
    if not stripped:
        return True

    normalized = _normalize_text(stripped)
    if not normalized:
        return True

    # A short answer such as "No." changes what a transcript says; only sounds without meaning go.
    return all(token in _FILLERS for token in normalized.split())


def _clean_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove from each segment what is removed from its turn; a segment left without words goes.

    Fillers stay, as they stay in the turn's text. A phrase or prompt that spans two segments stays in both.
    """
    cleaned: list[dict[str, Any]] = []
    for segment in segments:
        text = clean_transcript_text(str(segment["text"]))
        if _normalize_text(text):
            cleaned.append({**segment, "text": text})
    return cleaned


def clean_transcript_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove clearly hallucinated boilerplate turns while preserving metadata.
    """
    cleaned: list[dict[str, Any]] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        text = clean_transcript_text(str(turn.get("text", "")))
        if is_obvious_transcript_noise(text):
            continue
        cleaned_turn = {**turn, "text": text}
        if "segments" in turn:
            cleaned_turn["segments"] = _clean_segments(turn["segments"])
        cleaned.append(cleaned_turn)
    return cleaned
