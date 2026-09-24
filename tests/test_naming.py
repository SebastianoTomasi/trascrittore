from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.meeting import library, naming, voices
from src.meeting.transcript import render_payload_text


DURATION_SEC = 95.0


def _payload(*, windows: bool = True) -> dict[str, object]:
    persona_1_windows = [
        {"start": 3.0, "end": 13.0},
        {"start": 13.0, "end": 23.0},
        {"start": 23.0, "end": 33.0},
        {"start": 33.0, "end": 36.0},
    ]
    speakers = [
        {"label": "Mario Rossi", "recognized": True, "speech_sec": 30.0, "windows": [{"start": 40.0, "end": 50.0}]},
        {"label": "Persona 1", "recognized": False, "speech_sec": 33.0, "windows": persona_1_windows},
        {"label": "Persona 2", "recognized": False, "speech_sec": 4.0, "windows": []},
    ]
    if not windows:
        for speaker in speakers:
            del speaker["windows"]
    return {
        "file": "Riunione.m4a",
        "recording": "C:\\Riunioni\\Riunione.m4a",
        "duration_sec": DURATION_SEC,
        "device": "cuda",
        "compute_type": "float16",
        "warnings": [],
        "elapsed_sec": 60.0,
        "speakers": speakers,
        "turns": [
            {"speaker": "Persona 1", "start": "00:00:03", "start_sec": 3.0, "end_sec": 36.0, "text": "partiamo dal budget"},
            {"speaker": "Mario Rossi", "start": "00:00:40", "start_sec": 40.0, "end_sec": 70.0, "text": "va bene"},
            {"speaker": "Persona 2", "start": "00:01:11", "start_sec": 71.0, "end_sec": 75.0, "text": "d'accordo"},
        ],
    }


class FakeVoiceprints:
    """Every window sounds the same, except those starting at the seconds listed in `outliers`."""

    outliers: set[float] = set()

    def of_windows(self, _audio, windows):
        return [
            np.asarray([0.0, 1.0] if window["start"] in self.outliers else [1.0, 0.0], dtype=np.float32)
            for window in windows
        ]


@pytest.fixture
def meeting(tmp_path, monkeypatch):
    folder = tmp_path / "Riunioni"
    folder.mkdir()
    transcript = folder / "Riunione - trascrizione.json"
    transcript.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    (folder / "Riunione - trascrizione.txt").write_text(render_payload_text(_payload()), encoding="utf-8")
    (folder / "Riunione.m4a").write_bytes(b"not decoded: load_recording is faked")
    library_dir = tmp_path / "voci"
    library_dir.mkdir()

    monkeypatch.setattr(library, "library_dir", lambda: library_dir)
    monkeypatch.setattr(voices, "load_recording", lambda _path: np.zeros(int(DURATION_SEC * 16000), dtype=np.float32))
    FakeVoiceprints.outliers = set()
    monkeypatch.setattr(voices, "Voiceprints", FakeVoiceprints)
    return transcript, library_dir


def _read(transcript: Path) -> tuple[dict[str, object], str]:
    return (
        json.loads(transcript.read_text(encoding="utf-8")),
        transcript.with_suffix(".txt").read_text(encoding="utf-8"),
    )


def test_naming_rewrites_both_files_and_adds_the_speakers_clips(meeting, capsys):
    transcript, library_dir = meeting

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["status"] == "ok"
    payload, text = _read(transcript)
    assert [speaker["label"] for speaker in payload["speakers"]] == ["Mario Rossi", "Luca Bianchi", "Persona 2"]
    assert [speaker.get("named", False) for speaker in payload["speakers"]] == [False, True, False]
    assert payload == _payload() | {"speakers": payload["speakers"], "turns": payload["turns"]}
    assert "[00:00:03] Luca Bianchi: partiamo dal budget" in text.splitlines()
    assert text == render_payload_text(payload)

    pool = library_dir / "Luca Bianchi" / "registrazioni"
    assert sorted(path.name for path in pool.glob("*.wav")) == [
        "Riunione 00.00.03.wav",
        "Riunione 00.00.13.wav",
        "Riunione 00.00.23.wav",
    ]
    record = json.loads((pool / "clip.json").read_text(encoding="utf-8"))
    assert record["Riunione 00.00.03.wav"]["transcript"] == str(transcript)
    assert record["Riunione 00.00.03.wav"]["label"] == "Persona 1"
    assert summary["named"] == [
        {"label": "Persona 1", "name": "Luca Bianchi", "clips_added": 3, "folder": str(pool), "note": None}
    ]
    assert summary["trial"] == {"passed": False, "named_speakers": 1, "needed": 10}
    assert "Luca Bianchi" in capsys.readouterr().err


def test_a_speaker_without_clips_is_named_with_an_explanation(meeting):
    transcript, library_dir = meeting

    summary = naming.name_speakers(str(transcript), ["Persona 2=Anna Neri"])

    assert summary["status"] == "ok"
    assert summary["named"][0]["clips_added"] == 0
    assert "troppo poco" in summary["named"][0]["note"]
    assert not (library_dir / "Anna Neri").exists()
    assert "Anna Neri" in _read(transcript)[1]


def test_a_missing_recording_still_applies_the_name(meeting):
    transcript, library_dir = meeting
    (transcript.parent / "Riunione.m4a").unlink()

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["status"] == "ok"
    assert summary["named"][0]["clips_added"] == 0
    assert "Registrazione non trovata" in summary["named"][0]["note"]
    assert "Luca Bianchi" in _read(transcript)[1]
    assert not (library_dir / "Luca Bianchi").exists()


def test_the_recording_can_be_given_when_it_moved(meeting, tmp_path):
    transcript, library_dir = meeting
    moved = tmp_path / "Archivio" / "Riunione.m4a"
    moved.parent.mkdir()
    (transcript.parent / "Riunione.m4a").rename(moved)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"], recording=str(moved))

    assert summary["named"][0]["clips_added"] == 3


def test_a_recording_of_another_length_adds_no_clips(meeting, monkeypatch):
    transcript, library_dir = meeting
    monkeypatch.setattr(voices, "load_recording", lambda _path: np.zeros(16000 * 30, dtype=np.float32))

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["clips_added"] == 0
    assert "non corrisponde" in summary["named"][0]["note"]


def test_a_transcript_from_an_older_version_is_named_without_clips(meeting):
    transcript, library_dir = meeting
    transcript.write_text(json.dumps(_payload(windows=False)), encoding="utf-8")

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["clips_added"] == 0
    assert "versione precedente" in summary["named"][0]["note"]


def test_after_the_trial_only_the_selected_clips_are_saved(meeting):
    transcript, library_dir = meeting
    FakeVoiceprints.outliers = {13.0}
    selection = naming.get_library_settings()
    (library_dir / library.TRIAL_RECORD).write_text(
        json.dumps(
            {
                "passed": [
                    {
                        "keep_clips": selection.keep_clips,
                        "min_consistency": selection.min_consistency,
                        "version": library.SELECTION_VERSION,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    pool = library_dir / "Luca Bianchi" / "registrazioni"
    assert sorted(path.name for path in pool.glob("*.wav")) == ["Riunione 00.00.03.wav", "Riunione 00.00.23.wav"]
    assert summary["trial"]["passed"] is True


def test_a_name_already_in_the_library_uses_its_folder(meeting):
    transcript, library_dir = meeting
    (library_dir / "Luca Bianchi").mkdir()

    summary = naming.name_speakers(str(transcript), ["Persona 1=luca  bianchi"])

    assert summary["named"][0]["name"] == "Luca Bianchi"
    assert "c'è già 'Luca Bianchi'" in summary["named"][0]["note"]
    assert "[00:00:03] Luca Bianchi: partiamo dal budget" in _read(transcript)[1].splitlines()


@pytest.mark.parametrize(
    ("pair", "expected"),
    [
        ("Persona 9=Luca Bianchi", "non è una voce di questa trascrizione"),
        ("Mario Rossi=Mario Rossini", "ha già un nome"),
        ("Persona 1=Luca/Bianchi", "caratteri"),
        ("Persona 1", "Persona 2=Nome Cognome"),
    ],
)
def test_a_refused_name_leaves_the_files_as_they_were(meeting, pair, expected):
    transcript, library_dir = meeting
    before = _read(transcript)

    summary = naming.name_speakers(str(transcript), [pair])

    assert summary["status"] == "invalid_arguments"
    assert expected in summary["message"]
    assert _read(transcript) == before
    assert list(library_dir.iterdir()) == []


def test_naming_a_missing_transcript_is_refused(tmp_path):
    summary = naming.name_speakers(str(tmp_path / "manca - trascrizione.json"), ["Persona 1=Luca Bianchi"])

    assert summary["status"] == "file_not_found"


def test_listening_joins_the_best_two_clips_of_each_speaker_in_one_file(meeting, tmp_path):
    transcript, _ = meeting
    FakeVoiceprints.outliers = {3.0}
    out_dir = tmp_path / "ascolto"
    out_dir.mkdir()
    (out_dir / "ascolta Persona 3.wav").write_bytes(b"old")
    (out_dir / "altro.wav").write_bytes(b"not ours")

    summary = naming.prepare_listening(str(transcript), ["Persona 1", "Persona 2"], out_dir=str(out_dir))

    assert summary["status"] == "ok"
    assert summary["speakers"][0] == {
        "label": "Persona 1",
        "file": str(out_dir / "ascolta Persona 1.wav"),
        "clips": 2,
        "note": None,
    }
    assert round(sf.info(out_dir / "ascolta Persona 1.wav").duration, 2) == 20.7
    assert summary["speakers"][1]["file"] is None
    assert "troppo poco" in summary["speakers"][1]["note"]
    assert sorted(path.name for path in out_dir.iterdir()) == ["altro.wav", "ascolta Persona 1.wav"]
