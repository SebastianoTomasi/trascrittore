from __future__ import annotations

from src.asr.utils.output_format import build_transcript_turns, format_offset


def _word(word: str, start: float, end: float, speaker: str) -> dict[str, object]:
    return {"word": word, "start": start, "end": end, "speaker": speaker}


def test_build_transcript_turns_keeps_start_and_end_seconds():
    result = {
        "segments": [
            {
                "start": 0.0,
                "words": [
                    _word("ciao", 0.0, 0.5, "Alice"),
                    _word("come", 0.6, 1.0, "Alice"),
                    _word("stai", 1.1, 1.4, "Alice"),
                    _word("bene", 1.5, 2.0, "Bob"),
                    _word("grazie", 2.1, 2.6, "Bob"),
                    _word("davvero", 2.7, 3.0, "Bob"),
                    _word("tanto", 3.1, 3.5, "Bob"),
                    _word("ottimo", 70.0, 70.8, "Alice"),
                    _word("allora", 70.9, 71.2, "Alice"),
                ],
            }
        ]
    }

    assert build_transcript_turns(result, "260614_0841.mp3") == [
        {"speaker": "Alice", "time": "08:41", "start_sec": 0.0, "end_sec": 1.4, "text": "ciao come stai"},
        {"speaker": "Bob", "time": "08:41", "start_sec": 1.5, "end_sec": 3.5, "text": "bene grazie davvero tanto"},
        {"speaker": "Alice", "time": "08:42", "start_sec": 70.0, "end_sec": 71.2, "text": "ottimo allora"},
    ]


def test_build_transcript_turns_extends_end_when_smoothing_short_flips():
    result = {
        "segments": [
            {
                "start": 0.0,
                "words": [
                    _word("oggi", 0.0, 0.4, "Alice"),
                    _word("andiamo", 0.5, 1.0, "Alice"),
                    _word("sì", 1.1, 1.3, "Bob"),
                    _word("al", 1.4, 1.5, "Alice"),
                    _word("mare", 1.6, 2.4, "Alice"),
                ],
            }
        ]
    }

    assert build_transcript_turns(result, "260614_0841.mp3", {"Alice": "AliceRenamed"}) == [
        {
            "speaker": "AliceRenamed",
            "time": "08:41",
            "start_sec": 0.0,
            "end_sec": 2.4,
            "text": "oggi andiamo sì al mare",
        }
    ]


def _turns(*words: tuple[str, str]) -> list[dict[str, object]]:
    """
    Build turns from (word, speaker) pairs, one second per word.
    """
    result = {
        "segments": [
            {"start": 0.0, "words": [_word(word, i, i + 0.8, speaker) for i, (word, speaker) in enumerate(words)]}
        ]
    }
    return build_transcript_turns(result, "call.m4a")


def test_the_end_of_a_sentence_moves_back_to_the_speaker_who_began_it():
    turns = _turns(
        ("allora", "Alice"),
        ("ci", "Alice"),
        ("vediamo", "Alice"),
        ("la", "Alice"),
        ("prossima", "Alice"),
        ("settimana.", "Bob"),
        ("Intanto", "Bob"),
        ("partiamo", "Bob"),
        ("dal", "Bob"),
        ("budget.", "Bob"),
    )

    assert [(turn["speaker"], turn["text"], turn["start_sec"], turn["end_sec"]) for turn in turns] == [
        ("Alice", "allora ci vediamo la prossima settimana.", 0.0, 5.8),
        ("Bob", "Intanto partiamo dal budget.", 6.0, 9.8),
    ]


def test_the_start_of_a_sentence_moves_forward_to_the_speaker_who_says_it():
    turns = _turns(
        ("Ci", "Alice"),
        ("vediamo", "Alice"),
        ("domani.", "Alice"),
        ("Intanto", "Alice"),
        ("partiamo", "Alice"),
        ("dal", "Bob"),
        ("budget", "Bob"),
        ("di", "Bob"),
        ("marzo.", "Bob"),
    )

    assert [(turn["speaker"], turn["text"], turn["start_sec"], turn["end_sec"]) for turn in turns] == [
        ("Alice", "Ci vediamo domani.", 0.0, 2.8),
        ("Bob", "Intanto partiamo dal budget di marzo.", 3.0, 8.8),
    ]


def test_a_sentence_split_so_either_speaker_could_have_said_it_stays_where_it_is():
    turns = _turns(
        ("Ci", "Alice"),
        ("vediamo", "Alice"),
        ("domani.", "Alice"),
        ("Intanto", "Alice"),
        ("partiamo", "Alice"),
        ("dal", "Bob"),
        ("budget.", "Bob"),
    )

    assert [(turn["speaker"], turn["text"]) for turn in turns] == [
        ("Alice", "Ci vediamo domani. Intanto partiamo"),
        ("Bob", "dal budget."),
    ]


def test_words_stay_when_punctuation_on_both_sides_does_not_agree():
    turns = _turns(
        ("Vieni", "Alice"),
        ("anche", "Alice"),
        ("tu", "Alice"),
        ("Sì.", "Bob"),
        ("Arrivo", "Bob"),
        ("subito.", "Bob"),
        ("va", "Carla"),
        ("bene.", "Carla"),
    )

    assert [(turn["speaker"], turn["text"]) for turn in turns] == [
        ("Alice", "Vieni anche tu"),
        ("Bob", "Sì. Arrivo subito."),
        ("Carla", "va bene."),
    ]


def test_build_transcript_turns_drops_asr_boilerplate():
    result = {
        "segments": [
            {
                "start": 0.0,
                "words": [
                    _word("Grazie", 0.0, 0.3, "Alice"),
                    _word("per", 0.4, 0.5, "Alice"),
                    _word("la", 0.6, 0.7, "Alice"),
                    _word("visione!", 0.8, 1.2, "Alice"),
                    _word("buongiorno", 5.0, 5.6, "Bob"),
                    _word("Alice", 5.7, 6.1, "Bob"),
                ],
            }
        ]
    }

    assert [turn["speaker"] for turn in build_transcript_turns(result, "260614_0841.mp3")] == ["Bob"]


def test_build_transcript_turns_uses_offsets_for_free_form_filenames():
    result = {
        "segments": [
            {
                "start": 0.0,
                "words": [
                    _word("buongiorno", 5.2, 5.9, "Alice"),
                    _word("a", 6.0, 6.1, "Alice"),
                    _word("tutti", 6.2, 6.6, "Alice"),
                    _word("allora", 3725.4, 3725.9, "Bob"),
                    _word("partiamo", 3726.0, 3726.6, "Bob"),
                    _word("subito", 3726.7, 3727.2, "Bob"),
                    _word("oggi", 3727.3, 3727.6, "Bob"),
                ],
            }
        ]
    }

    turns = build_transcript_turns(result, "Registrazione budget è.m4a")

    assert [(turn["speaker"], turn["time"], turn["start_sec"]) for turn in turns] == [
        ("Alice", "00:00:05", 5.2),
        ("Bob", "01:02:05", 3725.4),
    ]


def test_format_offset_pads_and_clamps():
    assert format_offset(0) == "00:00:00"
    assert format_offset(3725.9) == "01:02:05"
    assert format_offset(-1.0) == "00:00:00"
