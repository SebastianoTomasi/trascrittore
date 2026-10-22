from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.transcriber import library, naming, voices
from src.transcriber.transcript import render_payload_text


DURATION_SEC = 95.0


def _payload(*, windows: bool = True) -> dict[str, object]:
    persona_1_windows = [
        {"start": 3.0, "end": 13.0},
        {"start": 13.0, "end": 23.0},
        {"start": 23.0, "end": 33.0},
        {"start": 33.0, "end": 36.0},
    ]
    speakers = [
        {
            "label": "Mario Rossi",
            "recognized": True,
            "speech_sec": 30.0,
            "score": 0.7,
            "windows": [{"start": 40.0, "end": 50.0}],
        },
        {"label": "Persona 1", "recognized": False, "speech_sec": 33.0, "windows": persona_1_windows},
        {"label": "Persona 2", "recognized": False, "speech_sec": 4.0, "windows": []},
    ]
    if not windows:
        for speaker in speakers:
            del speaker["windows"]
    return {
        "file": "Registrazione.m4a",
        "recording": "C:\\Registrazioni\\Registrazione.m4a",
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
def transcript_and_library(tmp_path, monkeypatch):
    folder = tmp_path / "Registrazioni"
    folder.mkdir()
    transcript = folder / "Registrazione - trascrizione.json"
    transcript.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    (folder / "Registrazione - trascrizione.txt").write_text(render_payload_text(_payload()), encoding="utf-8")
    (folder / "Registrazione.m4a").write_bytes(b"not decoded: load_recording is faked")
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


def test_naming_rewrites_both_files_and_adds_the_speakers_clips(transcript_and_library, capsys):
    transcript, library_dir = transcript_and_library

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
        "Registrazione 00.00.03.wav",
        "Registrazione 00.00.13.wav",
        "Registrazione 00.00.23.wav",
    ]
    record = json.loads((pool / "clip.json").read_text(encoding="utf-8"))
    assert record["Registrazione 00.00.03.wav"]["transcript"] == str(transcript)
    assert record["Registrazione 00.00.03.wav"]["label"] == "Persona 1"
    assert summary["named"] == [
        {
            "label": "Persona 1",
            "name": "Luca Bianchi",
            "action": "named",
            "clips_added": 3,
            "folder": str(pool),
            "note": None,
        }
    ]
    assert summary["over_cap"] == []
    assert "Luca Bianchi" in capsys.readouterr().err


def test_a_speaker_without_clips_is_named_with_an_explanation(transcript_and_library):
    transcript, library_dir = transcript_and_library

    summary = naming.name_speakers(str(transcript), ["Persona 2=Anna Neri"])

    assert summary["status"] == "ok"
    assert summary["named"][0]["clips_added"] == 0
    assert "troppo poco" in summary["named"][0]["note"]
    assert not (library_dir / "Anna Neri").exists()
    assert "Anna Neri" in _read(transcript)[1]


def test_a_missing_recording_still_applies_the_name(transcript_and_library):
    transcript, library_dir = transcript_and_library
    (transcript.parent / "Registrazione.m4a").unlink()

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["status"] == "ok"
    assert summary["named"][0]["clips_added"] == 0
    assert "Registrazione non trovata" in summary["named"][0]["note"]
    assert "Luca Bianchi" in _read(transcript)[1]
    assert not (library_dir / "Luca Bianchi").exists()


def test_the_recording_can_be_given_when_it_moved(transcript_and_library, tmp_path):
    transcript, library_dir = transcript_and_library
    moved = tmp_path / "Archivio" / "Registrazione.m4a"
    moved.parent.mkdir()
    (transcript.parent / "Registrazione.m4a").rename(moved)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"], recording=str(moved))

    assert summary["named"][0]["clips_added"] == 3


def test_a_recording_of_another_length_adds_no_clips(transcript_and_library, monkeypatch):
    transcript, library_dir = transcript_and_library
    monkeypatch.setattr(voices, "load_recording", lambda _path: np.zeros(16000 * 30, dtype=np.float32))

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["clips_added"] == 0
    assert "non corrisponde" in summary["named"][0]["note"]


def test_a_transcript_from_an_older_version_is_named_without_clips(transcript_and_library):
    transcript, library_dir = transcript_and_library
    transcript.write_text(json.dumps(_payload(windows=False)), encoding="utf-8")

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["clips_added"] == 0
    assert "versione precedente" in summary["named"][0]["note"]
    assert "trascrivi di nuovo la registrazione" in summary["named"][0]["note"]


def test_only_the_selected_clips_are_saved_from_the_first_naming(transcript_and_library):
    transcript, library_dir = transcript_and_library
    FakeVoiceprints.outliers = {13.0}

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    pool = library_dir / "Luca Bianchi" / "registrazioni"
    assert sorted(path.name for path in pool.glob("*.wav")) == ["Registrazione 00.00.03.wav", "Registrazione 00.00.23.wav"]
    assert summary["named"][0]["clips_added"] == 2
    assert "prova" not in summary["message"]


def test_a_name_already_in_the_library_uses_its_folder(transcript_and_library):
    transcript, library_dir = transcript_and_library
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
def test_a_refused_name_leaves_the_files_as_they_were(transcript_and_library, pair, expected):
    transcript, library_dir = transcript_and_library
    before = _read(transcript)

    summary = naming.name_speakers(str(transcript), [pair])

    assert summary["status"] == "invalid_arguments"
    assert expected in summary["message"]
    assert _read(transcript) == before
    assert list(library_dir.iterdir()) == []


def test_naming_a_missing_transcript_is_refused(tmp_path):
    summary = naming.name_speakers(str(tmp_path / "manca - trascrizione.json"), ["Persona 1=Luca Bianchi"])

    assert summary["status"] == "file_not_found"


def test_a_recognized_speaker_the_person_confirms_gets_more_clips(transcript_and_library):
    transcript, library_dir = transcript_and_library
    (library_dir / "Mario Rossi").mkdir()

    summary = naming.name_speakers(str(transcript), [], confirm=["Mario Rossi"])

    assert summary["status"] == "ok"
    result = summary["named"][0]
    assert (result["action"], result["name"], result["clips_added"]) == ("confirmed", "Mario Rossi", 1)
    assert (result["score"], result["threshold"]) == (0.7, naming.get_matching_settings().threshold)
    assert "0.700" in result["note"] and "aiuteranno poco" in result["note"]
    assert (library_dir / "Mario Rossi" / "registrazioni" / "Registrazione 00.00.40.wav").is_file()
    payload, _ = _read(transcript)
    assert payload["speakers"][0]["label"] == "Mario Rossi" and payload["speakers"][0]["named"] is True


def test_a_pair_that_repeats_a_recognized_name_is_a_confirmation(transcript_and_library):
    transcript, _ = transcript_and_library

    summary = naming.name_speakers(str(transcript), ["Mario Rossi=mario rossi"])

    assert summary["named"][0]["action"] == "confirmed"


def test_a_recognized_name_is_corrected_only_with_correct(transcript_and_library):
    transcript, library_dir = transcript_and_library
    (library_dir / "Mario Rossi").mkdir()

    summary = naming.name_speakers(str(transcript), ["Mario Rossi=Luca Bianchi"], correct=True)

    assert summary["status"] == "ok"
    result = summary["named"][0]
    assert (result["action"], result["name"], result["clips_added"]) == ("corrected", "Luca Bianchi", 1)
    assert "al posto di 'Luca Bianchi'" in result["note"]
    assert str(library_dir / "Mario Rossi") in result["note"]
    assert "[00:00:40] Luca Bianchi: va bene" in _read(transcript)[1].splitlines()
    assert list((library_dir / "Mario Rossi").iterdir()) == []


def test_an_anonymous_speaker_cannot_be_confirmed(transcript_and_library):
    transcript, _ = transcript_and_library

    summary = naming.name_speakers(str(transcript), [], confirm=["Persona 1"])

    assert summary["status"] == "invalid_arguments"
    assert "non ha un nome da confermare" in summary["message"]


def test_a_similar_name_stops_the_naming_until_the_person_decides(transcript_and_library):
    transcript, library_dir = transcript_and_library
    (library_dir / "Luca Bianchi").mkdir()
    before = _read(transcript)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianco"])

    assert summary["status"] == "similar_name"
    assert summary["similar"] == [{"label": "Persona 1", "name": "Luca Bianco", "people": ["Luca Bianchi"]}]
    assert _read(transcript) == before
    assert not (library_dir / "Luca Bianco").exists()

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianco"], new_people=["luca bianco"])

    assert summary["status"] == "ok"
    assert (library_dir / "Luca Bianco" / "registrazioni").is_dir()


def test_passing_the_cap_proposes_clips_to_remove(transcript_and_library, monkeypatch):
    transcript, library_dir = transcript_and_library
    selection = naming.get_library_settings()
    monkeypatch.setattr(
        naming,
        "get_library_settings",
        lambda: library.LibrarySettings(
            keep_clips=selection.keep_clips, min_consistency=selection.min_consistency, max_clips=4
        ),
    )
    pool = library_dir / "Luca Bianchi" / "registrazioni"
    pool.mkdir(parents=True)
    record = {}
    for second, consistency in ((1, 0.9), (2, 0.8), (3, 0.7), (4, 0.95)):
        name = f"Altra 00.00.0{second}.wav"
        (pool / name).write_bytes(b"clip")
        record[name] = {"recording_file": "Altra.m4a", "consistency": consistency}
    (pool / "clip.json").write_text(json.dumps(record), encoding="utf-8")
    (pool / "a mano.wav").write_bytes(b"placed by hand")

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["status"] == "over_cap"
    assert summary["over_cap"] == [
        {
            "person": "Luca Bianchi",
            "cap": 4,
            "remove": ["Altra 00.00.03.wav", "Altra 00.00.02.wav", "Registrazione 00.00.03.wav"],
        }
    ]
    assert len(list(pool.glob("*.wav"))) == 8


def test_listening_plays_one_clip_at_a_time_best_first(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    FakeVoiceprints.outliers = {3.0}
    out_dir = tmp_path / "ascolto"
    out_dir.mkdir()
    (out_dir / "ascolta Persona 3 - 1.wav").write_bytes(b"old")
    (out_dir / "altro.wav").write_bytes(b"not ours")

    summary = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir))

    assert summary["status"] == "ok"
    assert {key: summary[key] for key in ("label", "file", "clip", "clips", "seconds", "note")} == {
        "label": "Persona 1",
        "file": str(out_dir / "ascolta Persona 1 - 1.wav"),
        "clip": 1,
        "clips": 3,
        "seconds": 10.0,
        "note": None,
    }
    assert "Persona 1" in summary["message"]
    assert round(sf.info(out_dir / "ascolta Persona 1 - 1.wav").duration, 2) == 10.0
    assert sorted(path.name for path in out_dir.iterdir()) == ["altro.wav", "ascolta Persona 1 - 1.wav"]

    recognized = naming.prepare_listening(str(transcript), "Mario Rossi", out_dir=str(out_dir))
    third = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir), clip=3)
    fourth = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir), clip=4)

    assert recognized["file"] == str(out_dir / "ascolta Mario Rossi - 1.wav")
    assert third["file"] == str(out_dir / "ascolta Persona 1 - 3.wav")
    assert fourth["file"] is None
    assert "solo 3 clip" in fourth["note"]


def test_a_speaker_without_a_full_clip_is_heard_from_the_longest_stretch(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    payload = _payload()
    payload["speakers"][2]["windows"] = [{"start": 71.0, "end": 73.0}, {"start": 76.0, "end": 80.0}]
    transcript.write_text(json.dumps(payload), encoding="utf-8")

    summary = naming.prepare_listening(str(transcript), "Persona 2", out_dir=str(tmp_path))

    assert (summary["clips"], summary["seconds"]) == (0, 4.0)
    assert "tratto più lungo" in summary["note"]
    assert naming.name_speakers(str(transcript), ["Persona 2=Anna Neri"])["named"][0]["clips_added"] == 0


def test_the_unattributed_voice_cannot_be_heard(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library

    summary = naming.prepare_listening(str(transcript), "Voce non attribuita", out_dir=str(tmp_path))

    assert summary["status"] == "invalid_arguments"


def test_a_speaker_whose_clips_are_all_discarded_is_told_why(transcript_and_library, monkeypatch):
    transcript, library_dir = transcript_and_library
    FakeVoiceprints.outliers = {13.0}
    strict = library.LibrarySettings(keep_clips=8, min_consistency=0.99)
    monkeypatch.setattr(naming, "get_library_settings", lambda: strict)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    result = summary["named"][0]
    assert (result["clips_added"], result["folder"]) == (0, None)
    assert "altre voci o rumori" in result["note"]
    assert "None" not in summary["message"]
    assert not (library_dir / "Luca Bianchi").exists()
