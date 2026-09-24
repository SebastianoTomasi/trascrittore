from __future__ import annotations

import json

import numpy as np
import pytest

from src.meeting import library, naming, recognition_check as check, voices
from src.meeting.recognition_check import CheckedRecording, CheckedSpeaker, LibraryClip


def _voice(angle_deg: float) -> np.ndarray:
    """A unit voiceprint on a circle: the cosine of two voices is the cosine of their angle."""
    angle = np.radians(angle_deg)
    return np.asarray([np.cos(angle), np.sin(angle)], dtype=np.float32)


LUCA, ANNA = 0.0, 60.0
MEETING = ("riunione.m4a", 600.0)


def _clip(person: str, angle: float, recording: tuple[str, float] | None = None) -> LibraryClip:
    pool = "registrazioni" if recording else "."
    return LibraryClip(person=person, pool=pool, voiceprint=_voice(angle), recording=recording)


def _meeting(*speakers: tuple[str, float]) -> CheckedRecording:
    return CheckedRecording(
        name="Riunione.m4a",
        key=MEETING,
        speakers=[CheckedSpeaker(label=label, voiceprints=[_voice(angle)]) for label, angle in speakers],
    )


def test_each_named_speaker_is_scored_against_the_rest_of_the_library():
    clips = [_clip("Luca", 20.0), _clip("Anna", 80.0), _clip("Marco", 170.0)]

    outcomes = check.evaluate(clips, [_meeting(("Luca", 0.0), ("Anna", 90.0))], margin=0.10)
    report = check.report(outcomes, threshold=0.575, margin=0.10)

    assert report["current"] | {"threshold": None} == {
        "threshold": None,
        "margin": 0.10,
        "right": 2,
        "wrong": 0,
        "missed": 0,
        "wrong_when_missing": 0,
    }
    assert report["known_voices"]["min"] == pytest.approx(np.cos(np.radians(20)), abs=1e-3)
    # Without Anna in the library, her voice at 90 degrees is closest to Luca's clip at 20.
    assert report["missing_voices"]["max"] == pytest.approx(np.cos(np.radians(70)), abs=1e-3)


def test_clips_cut_from_the_recording_being_checked_are_left_out():
    own_clip = _clip("Luca", LUCA, recording=MEETING)
    other_clip = _clip("Luca", LUCA + 30, recording=("altra.m4a", 60.0))

    outcomes = check.evaluate([own_clip, other_clip, _clip("Anna", ANNA)], [_meeting(("Luca", LUCA))], margin=0.10)

    library_outcome = next(outcome for outcome in outcomes if outcome.scenario == "library")
    assert library_outcome.true_score == pytest.approx(np.cos(np.radians(30)), abs=1e-3)


def test_a_person_whose_only_clips_come_from_the_recording_counts_as_missing_from_the_library():
    clips = [_clip("Luca", LUCA, recording=MEETING), _clip("Anna", ANNA)]

    outcomes = check.evaluate(clips, [_meeting(("Luca", LUCA))], margin=0.10)

    assert [(outcome.scenario, outcome.truth, outcome.best_name) for outcome in outcomes] == [
        ("library", None, "Anna")
    ]


def test_speakers_nobody_named_are_not_checked():
    outcomes = check.evaluate([_clip("Luca", LUCA)], [_meeting(("Persona 1", LUCA))], margin=0.10)

    assert outcomes == []


def test_the_suggested_threshold_keeps_missing_voices_out_and_counts_what_it_loses():
    # Luca and Marco are close: removing one, the other would get his name.
    clips = [_clip("Luca", 25.0), _clip("Marco", 45.0), _clip("Anna", 120.0)]
    recordings = [_meeting(("Luca", 0.0), ("Anna", 120.0))]

    report = check.report(check.evaluate(clips, recordings, margin=0.0), threshold=0.575, margin=0.0, min_missing=2)

    # Without Luca, Marco scores cos(45) = 0.707 for Luca's voice and takes his name.
    assert report["current"]["wrong_when_missing"] == 1
    assert report["suggested"]["threshold"] == pytest.approx(0.738, abs=1e-3)
    assert report["suggested"]["wrong_when_missing"] == 0
    assert report["suggested"]["right"] == 2
    assert report["suggested"]["lost"] == 0


def test_the_suggested_threshold_stays_above_people_of_the_library_taken_for_each_other():
    # Luca's voice at 0 degrees scores 0.906 against Marco's clips and 0.819 against his own.
    clips = [_clip("Luca", 35.0), _clip("Marco", 25.0), _clip("Anna", 150.0)]
    recordings = [_meeting(("Luca", 0.0), ("Anna", 150.0))]

    report = check.report(check.evaluate(clips, recordings, margin=0.0), threshold=0.575, margin=0.0, min_missing=1)

    assert report["current"]["wrong"] == 1
    assert report["suggested"]["threshold"] == pytest.approx(0.937, abs=1e-3)
    assert report["suggested"]["wrong"] == 0


def test_no_suggestion_without_enough_voices_to_simulate_as_missing():
    clips = [_clip("Luca", 25.0), _clip("Marco", 45.0), _clip("Anna", 120.0)]
    outcomes = check.evaluate(clips, [_meeting(("Luca", 0.0), ("Anna", 120.0))], margin=0.0)

    assert check.report(outcomes, threshold=0.575, margin=0.0)["suggested"] is None
    assert check.report([], threshold=0.575, margin=0.10)["known_voices"]["count"] == 0


def test_the_check_command_reads_named_transcripts_and_their_recordings(tmp_path, monkeypatch):
    library_dir = tmp_path / "voci"
    for person, pool, clip in [("Luca Bianchi", ".", "nota.wav"), ("Anna Neri", ".", "nota.wav")]:
        (library_dir / person).mkdir(parents=True)
        (library_dir / person / clip).write_bytes(b"x")
    folder = tmp_path / "Riunioni"
    folder.mkdir()
    transcript = folder / "Riunione - trascrizione.json"
    transcript.write_text(
        json.dumps(
            {
                "file": "Riunione.m4a",
                "duration_sec": 60.0,
                "speakers": [
                    {"label": "Luca Bianchi", "named": True, "windows": [{"start": 0.0, "end": 10.0}]},
                    {"label": "Anna Neri", "named": True, "windows": [{"start": 10.0, "end": 20.0}]},
                    # Recognized by the transcriber, never confirmed by a person: not trusted.
                    {"label": "Marco Verdi", "windows": [{"start": 20.0, "end": 30.0}]},
                ],
                "turns": [],
            }
        ),
        encoding="utf-8",
    )
    (folder / "Riunione.m4a").write_bytes(b"x")

    class FakeVoiceprints:
        def of_clip(self, path):
            return _voice(LUCA if "Luca" in str(path) else ANNA)

        def of_windows(self, _audio, windows):
            return [_voice(LUCA if window["start"] == 0.0 else ANNA) for window in windows]

    monkeypatch.setattr(library, "library_dir", lambda: library_dir)
    monkeypatch.setattr(voices, "Voiceprints", FakeVoiceprints)
    monkeypatch.setattr(voices, "load_recording", lambda _path: np.zeros(16000 * 60, dtype=np.float32))

    summary = check.run_check([(str(transcript), str(folder / "Riunione.m4a"))], missing=["C:\\Vecchia - trascrizione.json"])

    assert summary["status"] == "ok"
    assert summary["recordings_checked"] == 1
    assert summary["skipped"] == [{"transcript": "C:\\Vecchia - trascrizione.json", "reason": "file non trovato"}]
    assert summary["current"]["right"] == 2
    assert summary["current"]["wrong"] == 0
