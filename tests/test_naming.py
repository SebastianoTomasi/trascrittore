from __future__ import annotations

import json
import os
import time
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
    """
    Every window sounds the same, except those starting at the seconds listed in `outliers`.

    A clip in the library sounds like the speaker when its file holds b"near", and unlike them otherwise.
    """

    outliers: set[float] = set()

    def of_windows(self, _audio, windows):
        return [
            np.asarray([0.0, 1.0] if window["start"] in self.outliers else [1.0, 0.0], dtype=np.float32)
            for window in windows
        ]

    def of_clip(self, path):
        near = Path(path).read_bytes() == b"near"
        return np.asarray([1.0, 0.0] if near else [0.0, 1.0], dtype=np.float32)


def _pool(folder: Path, *, sound: bytes = b"far", added: bool = True, clips: int = 3) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    names = [f"altra-00-00-0{second}.wav" for second in range(1, clips + 1)]
    for name in names:
        (folder / name).write_bytes(sound)
    if added:
        record = {name: {"recording_file": "Altra.m4a", "consistency": 0.8} for name in names}
        (folder / "clip.json").write_text(json.dumps(record), encoding="utf-8")
    return folder


def _library_settings(monkeypatch, **changes):
    selection = naming.get_library_settings()
    settings = library.LibrarySettings(
        keep_clips=changes.get("keep_clips", selection.keep_clips),
        min_consistency=changes.get("min_consistency", selection.min_consistency),
        max_clips=changes.get("max_clips", selection.max_clips),
        max_pools=changes.get("max_pools", selection.max_pools),
    )
    monkeypatch.setattr(naming, "get_library_settings", lambda: settings)


def _write_transcript(folder: Path, name: str) -> Path:
    folder.mkdir()
    transcript = folder / f"{name}-trascrizione.json"
    transcript.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    transcript.with_suffix(".txt").write_text(render_payload_text(_payload()), encoding="utf-8")
    (folder / "Registrazione.m4a").write_bytes(b"not decoded: load_recording is faked")
    return transcript


@pytest.fixture
def transcript_and_library(tmp_path, monkeypatch):
    transcript = _write_transcript(tmp_path / "2026-10-29 Demo Acme", "registrazione")
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
        "registrazione-00-00-03.wav",
        "registrazione-00-00-13.wav",
        "registrazione-00-00-23.wav",
    ]
    record = json.loads((pool / "clip.json").read_text(encoding="utf-8"))
    assert record["registrazione-00-00-03.wav"]["transcript"] == str(transcript)
    assert record["registrazione-00-00-03.wav"]["label"] == "Persona 1"
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
    assert sorted(path.name for path in pool.glob("*.wav")) == ["registrazione-00-00-03.wav", "registrazione-00-00-23.wav"]
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
    summary = naming.name_speakers(str(tmp_path / "manca-trascrizione.json"), ["Persona 1=Luca Bianchi"])

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
    assert (library_dir / "Mario Rossi" / "registrazioni" / "registrazione-00-00-40.wav").is_file()
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


def test_passing_a_pools_cap_proposes_clips_to_remove(transcript_and_library, monkeypatch):
    transcript, library_dir = transcript_and_library
    _library_settings(monkeypatch, max_clips=4, max_pools=1)
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
            "pool": str(pool),
            "cap": 4,
            "remove": ["Altra 00.00.03.wav", "Altra 00.00.02.wav", "registrazione-00-00-03.wav"],
        }
    ]
    assert len(list(pool.glob("*.wav"))) == 8


def test_a_missed_recognition_starts_a_pool_named_after_the_transcripts_folder(transcript_and_library):
    transcript, library_dir = transcript_and_library
    _pool(library_dir / "Luca Bianchi", added=False)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    pool = library_dir / "Luca Bianchi" / "2026-10-29-demo-acme"
    assert sorted(path.name for path in pool.glob("*.wav")) == [
        "registrazione-00-00-03.wav",
        "registrazione-00-00-13.wav",
        "registrazione-00-00-23.wav",
    ]
    assert (pool / "clip.json").is_file()
    assert summary["named"][0]["folder"] == str(pool)
    assert "gruppo nuovo" in summary["named"][0]["note"]
    assert not (library_dir / "Luca Bianchi" / "registrazioni").exists()


def test_a_corrected_name_of_someone_in_the_library_is_a_miss_too(transcript_and_library):
    transcript, library_dir = transcript_and_library
    payload = _payload()
    payload["speakers"][0]["windows"] = [{"start": 40.0, "end": 50.0}, {"start": 50.0, "end": 60.0}, {"start": 60.0, "end": 70.0}]
    transcript.write_text(json.dumps(payload), encoding="utf-8")
    _pool(library_dir / "Luca Bianchi" / "registrazioni")

    summary = naming.name_speakers(str(transcript), ["Mario Rossi=Luca Bianchi"], correct=True)

    assert summary["named"][0]["folder"] == str(library_dir / "Luca Bianchi" / "2026-10-29-demo-acme")


def test_a_miss_with_few_clips_joins_the_closest_added_pool(transcript_and_library):
    transcript, library_dir = transcript_and_library
    FakeVoiceprints.outliers = {13.0}
    person = library_dir / "Luca Bianchi"
    _pool(person / "registrazioni", sound=b"far")
    _pool(person / "2026-01-01-call", sound=b"near")
    _pool(person / "macchina", sound=b"near", added=False)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["folder"] == str(person / "2026-01-01-call")
    assert len(list((person / "2026-01-01-call").glob("registrazione-*.wav"))) == 2
    assert sorted(path.name for path in person.iterdir()) == ["2026-01-01-call", "macchina", "registrazioni"]


def test_a_miss_past_the_limit_of_pools_joins_the_closest_added_pool(transcript_and_library, monkeypatch):
    transcript, library_dir = transcript_and_library
    _library_settings(monkeypatch, max_pools=2)
    person = library_dir / "Luca Bianchi"
    _pool(person / "registrazioni", sound=b"near")
    _pool(person / "2026-01-01-call", sound=b"far")

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["folder"] == str(person / "registrazioni")
    assert sorted(path.name for path in person.iterdir()) == ["2026-01-01-call", "registrazioni"]


def test_a_miss_without_added_pools_and_few_clips_starts_registrazioni(transcript_and_library):
    transcript, library_dir = transcript_and_library
    FakeVoiceprints.outliers = {13.0}
    _pool(library_dir / "Luca Bianchi" / "macchina", sound=b"near", added=False)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["folder"] == str(library_dir / "Luca Bianchi" / "registrazioni")


def test_a_folder_made_by_hand_keeps_its_name_from_a_new_pool(transcript_and_library):
    transcript, library_dir = transcript_and_library
    _pool(library_dir / "Luca Bianchi" / "2026-10-29-demo-acme", added=False)

    summary = naming.name_speakers(str(transcript), ["Persona 1=Luca Bianchi"])

    assert summary["named"][0]["folder"] == str(library_dir / "Luca Bianchi" / "2026-10-29-demo-acme-2")


def test_a_confirmation_joins_the_added_pool_closest_to_the_speaker(transcript_and_library):
    transcript, library_dir = transcript_and_library
    person = library_dir / "Mario Rossi"
    _pool(person / "registrazioni", sound=b"far")
    _pool(person / "2026-01-01-call", sound=b"near")

    summary = naming.name_speakers(str(transcript), [], confirm=["Mario Rossi"])

    assert summary["named"][0]["folder"] == str(person / "2026-01-01-call")


def test_a_confirmation_closest_to_a_folder_made_by_hand_joins_registrazioni(transcript_and_library):
    transcript, library_dir = transcript_and_library
    person = library_dir / "Mario Rossi"
    _pool(person / "2026-01-01-call", sound=b"far")
    _pool(person, sound=b"near", added=False)

    summary = naming.name_speakers(str(transcript), [], confirm=["Mario Rossi"])

    assert summary["named"][0]["folder"] == str(person / "registrazioni")


def test_listening_plays_one_clip_at_a_time_best_first(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    FakeVoiceprints.outliers = {3.0}
    out_dir = tmp_path / "ascolto"
    out_dir.mkdir()
    (out_dir / "ascolta registrazione - Persona 3 - 1.wav").write_bytes(b"old")
    (out_dir / "altro.wav").write_bytes(b"not ours")

    summary = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir))

    assert summary["status"] == "ok"
    assert {key: summary[key] for key in ("label", "file", "clip", "clips", "seconds", "note")} == {
        "label": "Persona 1",
        "file": str(out_dir / "ascolta registrazione - Persona 1 - 1.wav"),
        "clip": 1,
        "clips": 3,
        "seconds": 10.0,
        "note": None,
    }
    assert "Persona 1" in summary["message"]
    assert round(sf.info(out_dir / "ascolta registrazione - Persona 1 - 1.wav").duration, 2) == 10.0
    assert sorted(path.name for path in out_dir.iterdir()) == ["altro.wav", "ascolta registrazione - Persona 1 - 1.wav"]

    recognized = naming.prepare_listening(str(transcript), "Mario Rossi", out_dir=str(out_dir))
    third = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir), clip=3)
    fourth = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir), clip=4)

    assert recognized["file"] == str(out_dir / "ascolta registrazione - Mario Rossi - 1.wav")
    assert third["file"] == str(out_dir / "ascolta registrazione - Persona 1 - 3.wav")
    assert fourth["file"] is None
    assert "solo 3 clip" in fourth["note"]


def test_two_transcripts_with_the_same_speaker_keep_their_own_listening_clips(
    transcript_and_library, tmp_path, monkeypatch
):
    transcript, _ = transcript_and_library
    other = _write_transcript(tmp_path / "altra", "altra")
    out_dir = tmp_path / "ascolto"
    # The other recording sounds different, so a clip overwritten by the other transcript's would show.
    def load_recording(path):
        loudness = 0.5 if Path(path).parent == other.parent else 0.0
        return np.full(int(DURATION_SEC * 16000), loudness, dtype=np.float32)

    monkeypatch.setattr(voices, "load_recording", load_recording)

    first = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir))
    heard = (out_dir / "ascolta registrazione - Persona 1 - 1.wav").read_bytes()
    second = naming.prepare_listening(str(other), "Persona 1", out_dir=str(out_dir))

    assert first["file"] == str(out_dir / "ascolta registrazione - Persona 1 - 1.wav")
    assert second["file"] == str(out_dir / "ascolta altra - Persona 1 - 1.wav")
    assert (out_dir / "ascolta registrazione - Persona 1 - 1.wav").read_bytes() == heard


def test_listening_clips_older_than_a_day_go_whatever_their_transcript(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    out_dir = tmp_path / "ascolto"
    out_dir.mkdir()
    forgotten = out_dir / "ascolta vecchia - Persona 1 - 1.wav"
    forgotten.write_bytes(b"two days old")
    two_days_ago = time.time() - 2 * 24 * 3600
    os.utime(forgotten, (two_days_ago, two_days_ago))
    (out_dir / "ascolta altra - Persona 1 - 1.wav").write_bytes(b"another session's")

    naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir))

    assert sorted(path.name for path in out_dir.iterdir()) == [
        "ascolta altra - Persona 1 - 1.wav",
        "ascolta registrazione - Persona 1 - 1.wav",
    ]


@pytest.mark.skipif(os.name != "nt", reason="only Windows refuses to delete a file that is still open")
def test_a_listening_clip_still_open_in_the_player_is_left_for_later(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    out_dir = tmp_path / "ascolto"
    out_dir.mkdir()
    playing = out_dir / "ascolta registrazione - Persona 1 - 2.wav"
    playing.write_bytes(b"still playing")

    with playing.open("rb"):
        summary = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir))

    assert summary["status"] == "ok"
    assert sorted(path.name for path in out_dir.iterdir()) == [
        "ascolta registrazione - Persona 1 - 1.wav",
        "ascolta registrazione - Persona 1 - 2.wav",
    ]


def test_a_speaker_without_a_full_clip_is_heard_from_the_longest_stretch(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    payload = _payload()
    payload["speakers"][2]["windows"] = [{"start": 71.0, "end": 73.0}, {"start": 76.0, "end": 80.0}]
    transcript.write_text(json.dumps(payload), encoding="utf-8")

    summary = naming.prepare_listening(str(transcript), "Persona 2", out_dir=str(tmp_path))

    assert (summary["clips"], summary["seconds"]) == (0, 4.0)
    assert "tratto più lungo" in summary["note"]
    assert naming.name_speakers(str(transcript), ["Persona 2=Anna Neri"])["named"][0]["clips_added"] == 0


def _with_segments(transcript: Path) -> None:
    """
    Give the transcript's turns their segments, as transcripts have since 2026-10-10.
    """
    payload = _payload()
    segments = [
        [(0.4, 2.0, "Allora."), (3.0, 10.0, "Partiamo dal budget."), (12.0, 20.0, "Poi i tempi.")],
        [(40.0, 70.0, "Va bene.")],
        [(71.0, 94.6, "D'accordo.")],
    ]
    for turn, timed in zip(payload["turns"], segments):
        turn["segments"] = [{"start_sec": start, "end_sec": end, "text": text} for start, end, text in timed]
    transcript.write_text(json.dumps(payload), encoding="utf-8")


def _passage(summary: dict[str, object]) -> tuple[object, ...]:
    return tuple(summary[key] for key in ("status", "start", "end", "text"))


def test_listening_at_a_time_plays_its_segment_with_a_second_on_each_side(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    _with_segments(transcript)
    out_dir = tmp_path / "ascolto"

    summary = naming.prepare_listening_at(str(transcript), "00:00:13.5", out_dir=str(out_dir))

    assert _passage(summary) == ("ok", 11.0, 21.0, "Poi i tempi.")
    assert (summary["command"], summary["note"]) == ("listen", None)
    assert summary["file"] == str(out_dir / "ascolta registrazione - 00-00-12.wav")
    assert round(sf.info(out_dir / "ascolta registrazione - 00-00-12.wav").duration, 2) == 10.0


@pytest.mark.parametrize(("time", "text"), [("11.5", "Poi i tempi."), ("10.5", "Partiamo dal budget.")])
def test_a_time_in_a_pause_plays_the_nearest_segment(transcript_and_library, tmp_path, time, text):
    transcript, _ = transcript_and_library
    _with_segments(transcript)

    assert naming.prepare_listening_at(str(transcript), time, out_dir=str(tmp_path))["text"] == text


@pytest.mark.parametrize("time", ["00:00:13.50", "0:13,5", "13.5", "13"])
def test_a_time_written_in_any_of_its_forms_plays_the_same_segment(transcript_and_library, tmp_path, time):
    transcript, _ = transcript_and_library
    _with_segments(transcript)

    assert _passage(naming.prepare_listening_at(str(transcript), time, out_dir=str(tmp_path))) == (
        "ok", 11.0, 21.0, "Poi i tempi."
    )


@pytest.mark.parametrize(("time", "start", "end"), [("1", 0.0, 3.0), ("01:30", 70.0, 95.0)])
def test_the_margin_stays_within_the_recording(transcript_and_library, tmp_path, time, start, end):
    transcript, _ = transcript_and_library
    _with_segments(transcript)

    summary = naming.prepare_listening_at(str(transcript), time, out_dir=str(tmp_path))

    assert (summary["start"], summary["end"]) == (start, end)


@pytest.mark.parametrize("time", ["-1", "00:01:36", "1:00:00"])
def test_a_time_outside_the_recording_is_refused_with_its_duration(transcript_and_library, tmp_path, time):
    transcript, _ = transcript_and_library
    _with_segments(transcript)

    summary = naming.prepare_listening_at(str(transcript), time, out_dir=str(tmp_path))

    assert summary["status"] == "invalid_arguments"
    assert "00:01:35" in summary["message"]


@pytest.mark.parametrize("time", ["", "dopo", "4m09s", "00:04:09:01"])
def test_a_time_that_cannot_be_read_is_refused(transcript_and_library, tmp_path, time):
    transcript, _ = transcript_and_library

    summary = naming.prepare_listening_at(str(transcript), time, out_dir=str(tmp_path))

    assert summary["status"] == "invalid_arguments"
    assert "HH:MM:SS" in summary["message"]


def test_a_transcript_without_segments_has_no_passage_to_play(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library

    summary = naming.prepare_listening_at(str(transcript), "00:00:13", out_dir=str(tmp_path))

    assert (summary["status"], summary["file"]) == ("ok", None)
    assert "versione precedente" in summary["note"]


def test_listening_at_a_time_without_the_recording_says_where_it_was_looked_for(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    _with_segments(transcript)
    (transcript.parent / "Registrazione.m4a").unlink()

    summary = naming.prepare_listening_at(str(transcript), "13", out_dir=str(tmp_path))

    assert (summary["status"], summary["file"], summary["text"]) == ("ok", None, "Poi i tempi.")
    assert "Registrazione non trovata" in summary["note"]


def test_listening_at_a_time_keeps_the_other_transcripts_listening_clips(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    _with_segments(transcript)
    out_dir = tmp_path / "ascolto"
    other = naming.prepare_listening(str(transcript), "Persona 1", out_dir=str(out_dir))
    mine = _write_transcript(tmp_path / "altra", "altra")
    _with_segments(mine)

    first = naming.prepare_listening_at(str(mine), "13", out_dir=str(out_dir))
    second = naming.prepare_listening_at(str(mine), "45", out_dir=str(out_dir))

    assert sorted(path.name for path in out_dir.iterdir()) == [
        "ascolta altra - 00-00-40.wav",
        "ascolta registrazione - Persona 1 - 1.wav",
    ]
    assert other["file"] == str(out_dir / "ascolta registrazione - Persona 1 - 1.wav")
    assert (first["file"], second["file"]) == (
        str(out_dir / "ascolta altra - 00-00-12.wav"),
        str(out_dir / "ascolta altra - 00-00-40.wav"),
    )


@pytest.mark.skipif(os.name != "nt", reason="only Windows refuses to delete a file that is still open")
def test_a_passage_still_open_in_the_player_is_played_again_from_its_file(transcript_and_library, tmp_path):
    transcript, _ = transcript_and_library
    _with_segments(transcript)
    out_dir = tmp_path / "ascolto"
    naming.prepare_listening_at(str(transcript), "13", out_dir=str(out_dir))
    playing = out_dir / "ascolta registrazione - 00-00-12.wav"

    with playing.open("rb"):
        summary = naming.prepare_listening_at(str(transcript), "14", out_dir=str(out_dir))

    assert (summary["status"], summary["file"]) == ("ok", str(playing))


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
