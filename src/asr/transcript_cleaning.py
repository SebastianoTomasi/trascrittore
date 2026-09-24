from __future__ import annotations

import re
from typing import Any


_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")
_PROMPT_PATTERN_CACHE: dict[str, list[re.Pattern[str]]] = {}

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

_PROMPT_STOPWORDS = {
    "a",
    "ad",
    "al",
    "alla",
    "con",
    "dei",
    "del",
    "della",
    "di",
    "e",
    "gli",
    "i",
    "il",
    "in",
    "la",
    "le",
    "lo",
    "per",
    "un",
    "una",
    "uno",
}


def _normalize_text(text: str) -> str:
    lowered = text.casefold()
    without_punctuation = _PUNCTUATION_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", without_punctuation).strip()


def _configured_initial_prompt() -> str:
    from src.asr.utils.config import config

    section = config["whisper"] if "whisper" in config else {}
    return section.get("initial_prompt", "").strip()


def _prompt_tokens() -> list[str]:
    return _normalize_text(_configured_initial_prompt()).split()


def _prompt_phrase_patterns() -> list[re.Pattern[str]]:
    normalized_prompt = _normalize_text(_configured_initial_prompt())
    if normalized_prompt in _PROMPT_PATTERN_CACHE:
        return _PROMPT_PATTERN_CACHE[normalized_prompt]

    tokens = normalized_prompt.split()
    patterns: list[re.Pattern[str]] = []
    for start in range(len(tokens)):
        for end in range(len(tokens), start + 1, -1):
            phrase_tokens = tokens[start:end]
            if not any(token not in _PROMPT_STOPWORDS for token in phrase_tokens):
                continue
            if len(phrase_tokens) == 2 and any(token in _PROMPT_STOPWORDS for token in phrase_tokens):
                continue
            phrase = r"[\s,.;:!?]+".join(re.escape(token) for token in phrase_tokens)
            patterns.append(re.compile(rf"\b{phrase}\b[.!?]?", re.IGNORECASE))
    _PROMPT_PATTERN_CACHE[normalized_prompt] = patterns
    return patterns


def _is_prompt_fragment(normalized_text: str) -> bool:
    if not normalized_text:
        return False

    tokens = normalized_text.split()
    prompt_tokens = set(_prompt_tokens())
    if not prompt_tokens:
        return False

    if len(tokens) == 1:
        return (
            tokens[0] in prompt_tokens
            and tokens[0] not in _PROMPT_STOPWORDS
            and len(tokens[0]) > 2
        )

    if all(token in prompt_tokens for token in tokens):
        return True

    prompt_text = " ".join(_prompt_tokens())
    return len(tokens) >= 3 and normalized_text in prompt_text


def clean_transcript_text(text: str) -> str:
    """
    Strip known ASR boilerplate snippets from a single transcript turn.
    """
    cleaned = text.strip()
    for pattern in _BOILERPLATE_SNIPPET_RES:
        cleaned = pattern.sub(" ", cleaned)
    for pattern in _prompt_phrase_patterns():
        cleaned = pattern.sub(" ", cleaned)
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

    tokens = normalized.split()
    if not tokens:
        return True

    unique = set(tokens)
    if len(unique) == 1 and len(tokens) >= 3:
        return True

    if len(tokens) == 1 and len(tokens[0]) <= 2:
        return True

    return _is_prompt_fragment(normalized)


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
        cleaned.append({**turn, "text": text})
    return cleaned
