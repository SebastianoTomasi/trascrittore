from __future__ import annotations

import src.asr.transcript_cleaning as transcript_cleaning
from src.asr.transcript_cleaning import clean_transcript_turns, is_obvious_transcript_noise


def test_transcript_cleaning_removes_subtitle_and_prompt_boilerplate(monkeypatch):
    monkeypatch.setattr(
        transcript_cleaning,
        "_configured_initial_prompt",
        lambda: (
            "Trascrizione di audio quotidiano in italiano. "
            "Contiene parlato informale, rumore domestico, TV, radio, film, "
            "musica e voci di altre persone."
        ),
    )
    turns = [
        {"speaker": "A", "time": "10:00", "text": "Grazie per la visione!"},
        {"speaker": "A", "time": "10:01", "text": "Autore dei sottotitoli e revisione a cura di QTSS Grazie"},
        {"speaker": "A", "time": "10:02", "text": "Contiene parlato informale, rumore domestico, TV, radio"},
        {"speaker": "A", "time": "10:03", "text": "Però comunque i Jupyter Notebook sono buggati."},
    ]

    assert clean_transcript_turns(turns) == [
        {"speaker": "A", "time": "10:03", "text": "Però comunque i Jupyter Notebook sono buggati."}
    ]


def test_transcript_cleaning_keeps_normal_short_speech():
    assert not is_obvious_transcript_noise("Grazie.")
    assert not is_obvious_transcript_noise("Perché oggi mi sento stanco.")
