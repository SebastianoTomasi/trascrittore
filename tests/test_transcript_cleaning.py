from __future__ import annotations

import src.asr.transcript_cleaning as transcript_cleaning
from src.asr.transcript_cleaning import clean_transcript_turns, is_obvious_transcript_noise

LONG_PROMPT = (
    "Trascrizione di audio quotidiano in italiano. "
    "Contiene parlato informale, rumore domestico, TV, radio, film, "
    "musica e voci di altre persone."
)


def _texts(turns: list[dict[str, str]]) -> list[str]:
    return [turn["text"] for turn in clean_transcript_turns(turns)]


def test_transcript_cleaning_removes_subtitle_boilerplate():
    turns = [
        {"speaker": "A", "time": "10:00", "text": "Grazie per la visione!"},
        {"speaker": "A", "time": "10:01", "text": "Autore dei sottotitoli e revisione a cura di QTSS Grazie"},
        {"speaker": "A", "time": "10:03", "text": "Però comunque i Jupyter Notebook sono buggati."},
    ]

    assert clean_transcript_turns(turns) == [
        {"speaker": "A", "time": "10:03", "text": "Però comunque i Jupyter Notebook sono buggati."}
    ]


def test_the_echoed_prompt_is_removed_only_where_it_appears_whole(monkeypatch):
    monkeypatch.setattr(transcript_cleaning, "_configured_initial_prompt", lambda: LONG_PROMPT)
    turns = [
        {"speaker": "A", "text": LONG_PROMPT.upper().replace(".", "")},
        {"speaker": "A", "text": f"Va bene. {LONG_PROMPT}"},
        {"speaker": "B", "text": "Contiene parlato informale, rumore domestico, TV, radio"},
        {"speaker": "B", "text": "Italiano."},
    ]

    assert _texts(turns) == [
        "Va bene.",
        "Contiene parlato informale, rumore domestico, TV, radio",
        "Italiano.",
    ]


def test_only_turns_made_of_fillers_are_dropped_as_noise():
    turns = [
        {"speaker": "A", "text": "Eh."},
        {"speaker": "A", "text": "Ehm, mmh, ehm."},
        {"speaker": "B", "text": "No."},
        {"speaker": "B", "text": "Sì."},
        {"speaker": "B", "text": "Ok."},
        {"speaker": "B", "text": "Sì, sì, sì."},
        {"speaker": "B", "text": "Eh, sì."},
    ]

    assert _texts(turns) == ["No.", "Sì.", "Ok.", "Sì, sì, sì.", "Eh, sì."]


def test_transcript_cleaning_keeps_normal_short_speech():
    assert not is_obvious_transcript_noise("Grazie.")
    assert not is_obvious_transcript_noise("Perché oggi mi sento stanco.")
