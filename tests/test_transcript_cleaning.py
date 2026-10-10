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


def test_an_echoed_prompt_split_across_segments_leaves_them_all(monkeypatch):
    monkeypatch.setattr(transcript_cleaning, "_configured_initial_prompt", lambda: LONG_PROMPT)
    first, second = LONG_PROMPT.split(". ")
    turn = {
        "speaker": "A",
        "text": f"Va bene. Ehm. {LONG_PROMPT}",
        "segments": [
            {"start_sec": 0.0, "end_sec": 0.6, "text": "Va bene."},
            {"start_sec": 1.0, "end_sec": 1.3, "text": "Ehm."},
            {"start_sec": 2.0, "end_sec": 4.0, "text": f"{first}."},
            {"start_sec": 4.1, "end_sec": 9.0, "text": second},
        ],
    }

    [cleaned] = clean_transcript_turns([turn])

    assert cleaned["text"] == "Va bene. Ehm."
    assert [segment["text"] for segment in cleaned["segments"]] == ["Va bene.", "Ehm."]


def _segmented(*texts: str) -> dict[str, object]:
    """
    Build a turn whose segments, one second apart, have these texts.
    """
    segments = [{"start_sec": float(i), "end_sec": i + 0.5, "text": text} for i, text in enumerate(texts)]
    return {"speaker": "A", "text": " ".join(texts), "segments": segments}


def test_a_phrase_across_two_segments_goes_and_the_words_beside_it_stay():
    [cleaned] = clean_transcript_turns([_segmented("Va bene grazie per", "la visione di ieri.")])

    assert cleaned["text"] == "Va bene di ieri."
    assert [(segment["start_sec"], segment["text"]) for segment in cleaned["segments"]] == [
        (0.0, "Va bene"),
        (1.0, "di ieri."),
    ]


def test_a_removed_part_of_the_prompt_stays_removed_where_its_words_are_said_again(monkeypatch):
    monkeypatch.setattr(transcript_cleaning, "_configured_initial_prompt", lambda: "Registrazione in italiano.")

    [cleaned] = clean_transcript_turns([_segmented("Registrazione in", "italiano.", "Parlo italiano.")])

    assert [segment["text"] for segment in cleaned["segments"]] == ["Parlo italiano."]


def test_the_segments_of_a_turn_joined_are_its_text():
    [cleaned] = clean_transcript_turns([_segmented("- Allora,", "ciao a tutti,", "Grazie per la visione!")])

    assert cleaned["text"] == "Allora, ciao a tutti"
    assert [segment["text"] for segment in cleaned["segments"]] == ["Allora,", "ciao a tutti"]


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
