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
