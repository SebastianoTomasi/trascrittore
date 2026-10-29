from __future__ import annotations

import json

import numpy as np
import pytest
import soundfile as sf

from src.transcriber import library
from src.asr.utils.config import LibrarySettings


SELECTION = LibrarySettings(keep_clips=2, min_consistency=0.6)


def _unit(*values: float) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    return array / np.linalg.norm(array)


def _windows(*starts: float, length: float = 10.0) -> list[dict[str, float]]:
    return [{"start": start, "end": start + length} for start in starts]


def test_consistency_compares_each_window_with_the_rest_of_the_speaker():
    same = _unit(1.0, 0.0)
    other = _unit(0.0, 1.0)

    scores = library.consistency_scores([same, same, same, other])

    assert scores[0] == pytest.approx(scores[1]) == pytest.approx(scores[2]) == pytest.approx(2 / np.sqrt(5))
    assert scores[3] == pytest.approx(0.0, abs=1e-6)


def test_consistency_is_unknown_with_a_single_window():
    assert library.consistency_scores([_unit(1.0, 0.0)]) == [None]


def test_selection_keeps_the_most_consistent_full_windows():
    windows = _windows(0.0, 10.0, 20.0, 30.0) + [{"start": 40.0, "end": 44.0}]
    voiceprints = [
        _unit(1.0, 0.2, 0.0),
        _unit(1.0, 0.0, 0.0),
        _unit(0.0, 0.0, 1.0),
        _unit(1.0, 0.6, 0.0),
        _unit(1.0, 0.05, 0.0),
    ]

    candidates = library.select_clips(windows, voiceprints, window_sec=10.0, selection=SELECTION)

    # The short window at 40 s counts in the others' mean but never becomes a clip.
    assert [(candidate.start, candidate.keep) for candidate in candidates] == [
        (0.0, True),
        (10.0, True),
        (30.0, False),
        (20.0, False),
    ]
    assert candidates[0].consistency == pytest.approx(0.9458, abs=1e-4)


def test_selection_discards_inconsistent_windows_even_below_the_cap():
    windows = _windows(0.0, 10.0, 20.0)
    voiceprints = [_unit(1.0, 0.0, 0.0), _unit(1.0, 0.05, 0.0), _unit(-0.2, 0.0, 1.0)]

    candidates = library.select_clips(
        windows, voiceprints, window_sec=10.0, selection=LibrarySettings(keep_clips=8, min_consistency=0.6)
    )

    assert [candidate.keep for candidate in candidates] == [True, True, False]


def test_selection_skips_windows_without_a_voiceprint():
    candidates = library.select_clips(_windows(0.0, 10.0), [None, _unit(1.0, 0.0)], window_sec=10.0, selection=SELECTION)

    assert [(candidate.start, candidate.consistency, candidate.keep) for candidate in candidates] == [(10.0, None, True)]


@pytest.mark.parametrize(
    "name",
    ["", "   ", "Luca/Bianchi", 'Luca "Lu"', "Luca?", "Luca.", "CON", "Persona 3", "Voce non attribuita", "x" * 81],
)
def test_names_that_cannot_be_a_library_folder_are_refused(name):
    assert library.name_problem(name)


def test_ordinary_names_are_accepted():
    assert library.name_problem("Niccolò D'Amico-Rossi") is None


def test_a_name_matching_a_library_folder_in_another_case_uses_the_folder(tmp_path):
    (tmp_path / "Luca Bianchi").mkdir()

    assert library.canonical_name(tmp_path, "luca  bianchi") == "Luca Bianchi"
    assert library.canonical_name(tmp_path, "Marco Verdi") == "Marco Verdi"
    assert library.canonical_name(tmp_path / "missing", "Marco Verdi") == "Marco Verdi"


def test_clip_names_carry_the_recording_and_the_time_without_spaces():
    assert library.clip_filename("Registrazione budget.m4a", 754.6) == "registrazione-budget-00-12-34.wav"
    assert library.clip_filename("2026-10-29 14-30-12.mkv", 5.0) == "2026-10-29-14-30-12-00-00-05.wav"


def test_only_the_kept_clips_are_saved_with_their_origin(tmp_path):
    audio = np.linspace(-0.5, 0.5, 16000 * 60, dtype=np.float32)
    candidates = [
        library.Candidate(start=10.0, end=20.0, consistency=0.9),
        library.Candidate(start=30.0, end=40.0, consistency=0.4, keep=False),
    ]

    folder = tmp_path / "Luca Bianchi" / "registrazioni"
    origin = {
        "recording": "C:\\Registrazioni\\registrazione.m4a",
        "recording_file": "registrazione.m4a",
        "recording_duration_sec": 60.0,
        "transcript": "C:\\Registrazioni\\registrazione-trascrizione.json",
        "label": "Persona 2",
    }

    saved = library.save_clips(folder, audio, candidates, origin=origin)

    assert saved == ["registrazione-00-00-10.wav"]
    assert sorted(path.name for path in folder.glob("*.wav")) == ["registrazione-00-00-10.wav"]
    info = sf.info(folder / "registrazione-00-00-10.wav")
    assert (info.samplerate, round(info.duration, 3)) == (16000, 10.0)
    record = json.loads((folder / "clip.json").read_text(encoding="utf-8"))
    assert record["registrazione-00-00-10.wav"] | {"saved": None} == origin | {
        "start": 10.0,
        "end": 20.0,
        "consistency": 0.9,
        "saved": None,
    }


def test_the_record_drops_the_clips_the_person_deleted(tmp_path):
    audio = np.linspace(-0.5, 0.5, 16000 * 60, dtype=np.float32)
    folder = tmp_path / "Luca Bianchi" / "registrazioni"
    origin = {"recording_file": "registrazione.m4a", "label": "Persona 2"}
    library.save_clips(folder, audio, [library.Candidate(start=10.0, end=20.0, consistency=0.9)], origin=origin)
    (folder / "registrazione-00-00-10.wav").unlink()

    library.save_clips(folder, audio, [library.Candidate(start=30.0, end=40.0, consistency=0.8)], origin=origin)

    record = json.loads((folder / "clip.json").read_text(encoding="utf-8"))
    assert list(record) == ["registrazione-00-00-30.wav"]


@pytest.mark.parametrize(
    ("given", "existing", "similar"),
    [
        ("Marco Rosi", "Marco Rossi", True),
        ("Marko Rosi", "Marco Rossi", True),
        ("M. Rossi", "Marco Rossi", True),
        ("M Rossi", "Marco Rossi", True),
        ("Marco", "Marco Rossi", True),
        ("marco  rossi", "Marco Rossi", False),
        ("Marco Bianchi", "Marco Rossi", False),
        ("Rossi", "Marco Rossi", False),
        ("L. Rossi", "Marco Rossi", False),
    ],
)
def test_similar_names(given, existing, similar):
    assert library.names_are_similar(given, existing) is similar


def test_a_name_already_in_the_library_has_no_similar_people(tmp_path):
    for person in ("Marco Rossi", "Marco Rosi"):
        (tmp_path / person).mkdir()

    assert library.similar_people(tmp_path, "marco rossi") == []
    assert library.similar_people(tmp_path, "Marco Ross") == ["Marco Rosi", "Marco Rossi"]


def _added_pool(tmp_path):
    pool = tmp_path / "Luca Bianchi" / library.CLIPS_FOLDER
    pool.mkdir(parents=True)
    for name in ("Altra 00.00.01.wav", "Altra 00.00.02.wav"):
        (pool / name).write_bytes(b"clip")
    (pool / "a mano.wav").write_bytes(b"placed by hand")
    record = {name: {"recording_file": "Altra.m4a", "consistency": 0.8} for name in ("Altra 00.00.01.wav", "Altra 00.00.02.wav")}
    (pool / library.CLIPS_RECORD).write_text(json.dumps(record), encoding="utf-8")
    return pool


def test_only_recorded_clips_are_removed(tmp_path):
    pool = _added_pool(tmp_path)

    removed, refused = library.remove_clips(tmp_path, "Luca Bianchi", ["altra 00.00.01.wav", "a mano.wav"])

    assert removed == ["Altra 00.00.01.wav"]
    assert [entry["clip"] for entry in refused] == ["a mano.wav"]
    assert sorted(path.name for path in pool.glob("*.wav")) == ["Altra 00.00.02.wav", "a mano.wav"]
    record = json.loads((pool / library.CLIPS_RECORD).read_text(encoding="utf-8"))
    assert list(record) == ["Altra 00.00.02.wav"]
    assert library.cap_proposal(pool, 1) == []


def test_clips_are_removed_from_every_added_pool_of_the_person(tmp_path):
    pool = _added_pool(tmp_path)
    other = tmp_path / "Luca Bianchi" / "2026-10-29-demo-acme"
    other.mkdir()
    (other / "demo-00-00-05.wav").write_bytes(b"clip")
    (other / library.CLIPS_RECORD).write_text(json.dumps({"demo-00-00-05.wav": {"recording_file": "demo.mp4"}}), encoding="utf-8")

    removed, refused = library.remove_clips(tmp_path, "Luca Bianchi", ["Altra 00.00.02.wav", "demo-00-00-05.wav"])

    assert (removed, refused) == (["Altra 00.00.02.wav", "demo-00-00-05.wav"], [])
    assert json.loads((other / library.CLIPS_RECORD).read_text(encoding="utf-8")) == {}
    assert sorted(path.name for path in pool.glob("*.wav")) == ["Altra 00.00.01.wav", "a mano.wav"]


def test_the_remove_command_removes_the_confirmed_clips(tmp_path, monkeypatch, capsys):
    pool = _added_pool(tmp_path)
    monkeypatch.setattr(library, "library_dir", lambda: tmp_path)

    summary = library.remove_clips_report("Luca Bianchi", ["Altra 00.00.01.wav"])

    assert (summary["status"], summary["removed"], summary["refused"]) == ("ok", ["Altra 00.00.01.wav"], [])
    assert not (pool / "Altra 00.00.01.wav").exists()
    assert "1 clip tolte" in capsys.readouterr().err
