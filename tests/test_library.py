from __future__ import annotations

import json

import numpy as np
import pytest
import soundfile as sf

from src.meeting import library
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


def test_selection_keeps_the_most_consistent_full_windows_and_votes_on_the_rest():
    windows = _windows(0.0, 10.0, 20.0, 30.0) + [{"start": 40.0, "end": 44.0}]
    embeddings = [
        _unit(1.0, 0.2, 0.0),
        _unit(1.0, 0.0, 0.0),
        _unit(0.0, 0.0, 1.0),
        _unit(1.0, 0.6, 0.0),
        _unit(1.0, 0.05, 0.0),
    ]

    candidates = library.select_clips(windows, embeddings, window_sec=10.0, selection=SELECTION)

    # The short window at 40 s counts in the others' mean but never becomes a clip.
    assert [(candidate.start, candidate.vote) for candidate in candidates] == [
        (0.0, "keep"),
        (10.0, "keep"),
        (30.0, "discard"),
        (20.0, "discard"),
    ]
    assert candidates[0].consistency == pytest.approx(0.9458, abs=1e-4)


def test_selection_discards_inconsistent_windows_even_below_the_cap():
    windows = _windows(0.0, 10.0, 20.0)
    embeddings = [_unit(1.0, 0.0, 0.0), _unit(1.0, 0.05, 0.0), _unit(-0.2, 0.0, 1.0)]

    candidates = library.select_clips(
        windows, embeddings, window_sec=10.0, selection=LibrarySettings(keep_clips=8, min_consistency=0.6)
    )

    assert [candidate.vote for candidate in candidates] == ["keep", "keep", "discard"]


def test_selection_skips_windows_that_could_not_be_embedded():
    candidates = library.select_clips(_windows(0.0, 10.0), [None, _unit(1.0, 0.0)], window_sec=10.0, selection=SELECTION)

    assert [(candidate.start, candidate.consistency, candidate.vote) for candidate in candidates] == [
        (10.0, None, "keep")
    ]


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


def test_clip_names_carry_the_recording_and_the_time():
    assert library.clip_filename("Riunione budget.m4a", 754.6) == "Riunione budget 00.12.34.wav"


def _save(tmp_path, *, trial: bool, label: str = "Persona 2", recording: str = "Riunione.m4a") -> list[str]:
    audio = np.linspace(-0.5, 0.5, 16000 * 60, dtype=np.float32)
    candidates = [
        library.Candidate(start=10.0, end=20.0, consistency=0.9, vote="keep"),
        library.Candidate(start=30.0, end=40.0, consistency=0.4, vote="discard"),
    ]
    return library.save_clips(
        tmp_path,
        "Luca Bianchi",
        audio,
        candidates,
        trial=trial,
        selection=SELECTION,
        origin={
            "recording": f"C:\\Riunioni\\{recording}",
            "recording_file": recording,
            "recording_duration_sec": 60.0,
            "transcript": f"C:\\Riunioni\\{recording} - trascrizione.json",
            "label": label,
        },
    )


def test_during_the_trial_every_candidate_is_saved_with_its_vote(tmp_path):
    saved = _save(tmp_path, trial=True)

    folder = tmp_path / "Luca Bianchi" / "registrazioni"
    assert saved == ["Riunione 00.00.10.wav", "Riunione 00.00.30.wav"]
    info = sf.info(folder / "Riunione 00.00.10.wav")
    assert (info.samplerate, round(info.duration, 3)) == (16000, 10.0)
    record = json.loads((folder / "clip.json").read_text(encoding="utf-8"))
    assert record["Riunione 00.00.10.wav"]["vote"] == "keep"
    assert record["Riunione 00.00.30.wav"] | {"saved": None} == {
        "recording": "C:\\Riunioni\\Riunione.m4a",
        "recording_file": "Riunione.m4a",
        "recording_duration_sec": 60.0,
        "transcript": "C:\\Riunioni\\Riunione.m4a - trascrizione.json",
        "label": "Persona 2",
        "start": 30.0,
        "end": 40.0,
        "consistency": 0.4,
        "vote": "discard",
        "trial": True,
        "selection": {"keep_clips": 2, "min_consistency": 0.6, "version": library.SELECTION_VERSION},
        "saved": None,
    }


def test_after_the_trial_only_the_kept_clips_are_saved(tmp_path):
    assert _save(tmp_path, trial=False) == ["Riunione 00.00.10.wav"]


def _name_speakers(tmp_path, count: int) -> None:
    for index in range(count):
        _save(tmp_path, trial=True, recording=f"Riunione {index}.m4a")


def test_trial_counts_named_speakers_and_passes_after_ten_once_the_person_reviewed(tmp_path):
    _name_speakers(tmp_path, 9)
    status = library.trial_status(tmp_path, SELECTION)
    assert (status.named_speakers, status.passed, status.ready, status.disagreements) == (9, False, False, [])

    _name_speakers(tmp_path, 10)
    not_reviewed = library.evaluate_trial(tmp_path, SELECTION, reviewed=False)
    assert not_reviewed.ready and not not_reviewed.passed
    assert not_reviewed.votes == {"keep": 10, "discard": 10, "discarded_but_kept_by_person": 10}

    status = library.evaluate_trial(tmp_path, SELECTION, reviewed=True)

    assert status.passed and status.named_speakers == 10 and not status.ready
    assert library.trial_status(tmp_path, SELECTION).passed
    assert not library.trial_status(tmp_path, LibrarySettings(keep_clips=6, min_consistency=0.6)).passed


def test_a_kept_clip_the_person_deleted_stops_the_trial(tmp_path):
    _name_speakers(tmp_path, 10)
    (tmp_path / "Luca Bianchi" / "registrazioni" / "Riunione 3 00.00.10.wav").unlink()
    (tmp_path / "Luca Bianchi" / "registrazioni" / "Riunione 3 00.00.30.wav").unlink()

    status = library.evaluate_trial(tmp_path, SELECTION, reviewed=True)

    assert not status.passed
    assert status.disagreements == [{"person": "Luca Bianchi", "clip": "Riunione 3 00.00.10.wav", "consistency": 0.9}]
    assert not library.trial_status(tmp_path, SELECTION).passed


def test_speakers_named_under_another_selection_start_a_new_trial(tmp_path):
    _name_speakers(tmp_path, 10)

    assert library.trial_status(tmp_path, LibrarySettings(keep_clips=8, min_consistency=0.5)).named_speakers == 0


def test_the_trial_report_says_what_to_do_next(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(library, "library_dir", lambda: tmp_path)
    _name_speakers(tmp_path, 3)

    summary = library.trial_report(SELECTION)

    assert (summary["status"], summary["passed"], summary["named_speakers"]) == ("ok", False, 3)
    assert "voci nominate 3 su 10" in capsys.readouterr().err

    _name_speakers(tmp_path, 10)
    ready = library.trial_report(SELECTION)
    assert ready["ready"] and not ready["passed"]
    assert "Se hai ascoltato tutte le clip" in ready["message"]
    assert library.trial_report(SELECTION, reviewed=True)["message"].startswith("Periodo di prova superato")
    assert "già superato" in library.trial_report(SELECTION)["message"]


def test_a_new_version_of_the_selection_starts_a_new_trial(tmp_path, monkeypatch):
    _name_speakers(tmp_path, 10)
    library.evaluate_trial(tmp_path, SELECTION, reviewed=True)

    monkeypatch.setattr(library, "SELECTION_VERSION", library.SELECTION_VERSION + 1)

    status = library.trial_status(tmp_path, SELECTION)
    assert (status.passed, status.named_speakers) == (False, 0)


def test_the_trial_report_lists_the_kept_clips_the_person_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(library, "library_dir", lambda: tmp_path)
    _name_speakers(tmp_path, 10)
    (tmp_path / "Luca Bianchi" / "registrazioni" / "Riunione 3 00.00.10.wav").unlink()

    summary = library.trial_report(SELECTION, reviewed=True)

    assert not summary["passed"]
    assert "va corretta" in summary["message"]
    assert summary["disagreements"][0]["clip"] == "Riunione 3 00.00.10.wav"
