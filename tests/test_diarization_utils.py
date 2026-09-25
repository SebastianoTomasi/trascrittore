from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from pyannote.core import Segment

import src.asr.utils.diarization_utils as du


def _unit(values):
    arr = np.asarray(values, dtype=np.float32)
    return arr / (np.linalg.norm(arr) + 1e-9)


def test_diarization_to_dataframe_accepts_saved_segments_of_silent_audio():
    df = du.diarization_to_dataframe([])

    assert df.empty
    assert list(df.columns) == ["start", "end", "speaker"]


def test_split_segment_into_windows_keeps_long_enough_remainder():
    windows = du._split_segment_into_windows(Segment(0.0, 25.0), window_sec=10.0, min_window_sec=2.0)

    assert [(w.start, w.end) for w in windows] == [(0.0, 10.0), (10.0, 20.0), (20.0, 25.0)]


def test_split_segment_into_windows_drops_short_remainder():
    windows = du._split_segment_into_windows(Segment(0.0, 21.0), window_sec=10.0, min_window_sec=2.0)

    assert [(w.start, w.end) for w in windows] == [(0.0, 10.0), (10.0, 20.0)]


def test_sample_longest_per_bucket_takes_bucket_centers_when_durations_tie():
    windows = [Segment(float(i), float(i + 1)) for i in range(10)]

    sampled = du._sample_longest_per_bucket(windows, max_windows=4)

    assert [(w.start, w.end) for w in sampled] == [
        (0.0, 1.0),
        (3.0, 4.0),
        (5.0, 6.0),
        (8.0, 9.0),
    ]


def test_sample_longest_per_bucket_prefers_longest_window_in_each_bucket():
    windows = [
        Segment(0.0, 2.0),
        Segment(10.0, 12.0),
        Segment(20.0, 29.0),
        Segment(30.0, 40.0),
        Segment(50.0, 53.0),
        Segment(60.0, 63.0),
    ]

    sampled = du._sample_longest_per_bucket(windows, max_windows=2)

    assert [(w.start, w.end) for w in sampled] == [(20.0, 29.0), (30.0, 40.0)]


def test_sample_longest_per_bucket_single_window_is_longest_not_first():
    windows = [Segment(0.0, 2.0), Segment(10.0, 20.0), Segment(30.0, 33.0)]

    sampled = du._sample_longest_per_bucket(windows, max_windows=1)

    assert [(w.start, w.end) for w in sampled] == [(10.0, 20.0)]


def test_sample_longest_per_bucket_ignores_float_noise_in_durations():
    # Splitting from 17.3 s yields one window of 9.999999999999996 s among 10.0 s ones.
    windows = du._split_segment_into_windows(Segment(17.3, 57.3), window_sec=10.0, min_window_sec=2.0)

    sampled = du._sample_longest_per_bucket(windows, max_windows=1)

    assert sampled == [windows[1]]


def test_speaker_voiceprints_windowing_min_total_and_normalization(monkeypatch):
    diarize_df = pd.DataFrame(
        [
            {"start": 0.0, "end": 12.0, "speaker": "SPEAKER_00"},
            {"start": 20.0, "end": 21.0, "speaker": "SPEAKER_01"},
        ]
    )
    monkeypatch.setattr(du.whisperx, "load_audio", MagicMock(return_value=np.zeros(30 * 16000, dtype=np.float32)))

    raw_voiceprints = iter([
        np.asarray([2.0, 0.0], dtype=np.float32),
        np.asarray([0.0, 3.0], dtype=np.float32),
    ])

    def fake_voiceprint(_model, _audio, device, crop, min_duration_sec):
        return next(raw_voiceprints)

    monkeypatch.setattr(du, "compute_voiceprint", fake_voiceprint)

    result = du.speaker_voiceprints_from_diarization(
        object(),
        "dummy.wav",
        diarize_df,
        device="cpu",
        window_sec=10.0,
        min_window_sec=2.0,
        min_total_speech_sec=4.0,
        max_windows_per_spk=12,
    )

    assert set(result) == {"SPEAKER_00"}
    assert len(result["SPEAKER_00"]) == 2
    assert np.linalg.norm(result["SPEAKER_00"][0]) == pytest.approx(1.0)


def test_speaker_voiceprints_sample_per_bucket_when_capped(monkeypatch):
    diarize_df = pd.DataFrame(
        [
            {"start": float(i), "end": float(i + 1), "speaker": "SPEAKER_00"}
            for i in range(10)
        ]
    )
    monkeypatch.setattr(du.whisperx, "load_audio", MagicMock(return_value=np.zeros(10 * 16000, dtype=np.float32)))

    measured_starts = []

    def fake_voiceprint(_model, _audio, device, crop, min_duration_sec):
        measured_starts.append(crop.start)
        return np.asarray([1.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(du, "compute_voiceprint", fake_voiceprint)

    result = du.speaker_voiceprints_from_diarization_with_diagnostics(
        object(),
        "dummy.wav",
        diarize_df,
        device="cpu",
        window_sec=1.0,
        min_window_sec=0.5,
        min_total_speech_sec=0.0,
        max_windows_per_spk=4,
    )

    speaker_diag = result.diagnostics["speakers"]["SPEAKER_00"]
    assert measured_starts == [0.0, 3.0, 5.0, 8.0]
    assert speaker_diag["candidate_window_count"] == 10
    assert speaker_diag["sampled_window_count"] == 4
    assert speaker_diag["sampling_strategy"] == "longest_per_bucket"


def test_speaker_voiceprints_diagnostics_record_windows_and_clips(monkeypatch):
    scratch_dir = Path("tests/.tmp_speaker_diagnostics").resolve()
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)
    scratch_dir.mkdir(parents=True)

    diarize_df = pd.DataFrame(
        [
            {"start": 0.0, "end": 12.0, "speaker": "SPEAKER_00"},
            {"start": 20.0, "end": 21.0, "speaker": "SPEAKER_01"},
        ]
    )
    monkeypatch.setattr(du.whisperx, "load_audio", MagicMock(return_value=np.zeros(30 * 16000, dtype=np.float32)))

    raw_voiceprints = iter([
        np.asarray([2.0, 0.0], dtype=np.float32),
        np.asarray([0.0, 3.0], dtype=np.float32),
    ])

    def fake_voiceprint(_model, _audio, device, crop, min_duration_sec):
        return next(raw_voiceprints)

    monkeypatch.setattr(du, "compute_voiceprint", fake_voiceprint)

    try:
        result = du.speaker_voiceprints_from_diarization_with_diagnostics(
            object(),
            "dummy.wav",
            diarize_df,
            device="cpu",
            window_sec=10.0,
            min_window_sec=2.0,
            min_total_speech_sec=4.0,
            max_windows_per_spk=12,
            diagnostics_clip_path_factory=lambda index, speaker, duration_sec: str(
                scratch_dir / f"dummy_clip_{index:03d}_{speaker}_duration_{duration_sec:.3f}s.wav"
            ),
            sample_rate=16000,
        )

        assert set(result.voiceprints) == {"SPEAKER_00"}
        assert "raw_diarization" not in result.diagnostics
        speaker_diag = result.diagnostics["speakers"]["SPEAKER_00"]
        assert speaker_diag["sampled_window_count"] == 2
        assert speaker_diag["voiceprint_count"] == 2
        assert speaker_diag["eligible_for_matching"] is True
        assert all(window["voiceprint_status"] == "computed" for window in speaker_diag["windows"])
        assert all(window["clip_path"] for window in speaker_diag["windows"])
        assert all(os.path.isfile(window["clip_path"]) for window in speaker_diag["windows"])
        assert os.path.basename(speaker_diag["windows"][0]["clip_path"]) == (
            "dummy_clip_001_SPEAKER_00_duration_10.000s.wav"
        )

        short_diag = result.diagnostics["speakers"]["SPEAKER_01"]
        assert short_diag["sampled_window_count"] == 0
        assert short_diag["voiceprint_rejection_reason"] == "no_voiceprint_windows"
    finally:
        if scratch_dir.exists():
            shutil.rmtree(scratch_dir)


def test_speaker_windows_are_recorded_without_a_voiceprint_model(monkeypatch):
    diarize_df = pd.DataFrame(
        [
            {"start": 0.0, "end": 12.0, "speaker": "SPEAKER_00"},
            {"start": 20.0, "end": 21.0, "speaker": "SPEAKER_01"},
        ]
    )

    def no_audio(_path):
        raise AssertionError("windows alone need no audio")

    monkeypatch.setattr(du.whisperx, "load_audio", no_audio)

    result = du.speaker_voiceprints_from_diarization_with_diagnostics(
        None,
        "dummy.wav",
        diarize_df,
        device="cpu",
        window_sec=10.0,
        min_window_sec=2.0,
        min_total_speech_sec=4.0,
        max_windows_per_spk=12,
    )

    assert result.voiceprints == {}
    speaker_diag = result.diagnostics["speakers"]["SPEAKER_00"]
    assert [(window["start"], window["end"]) for window in speaker_diag["windows"]] == [(0.0, 10.0), (10.0, 12.0)]
    assert all(window["voiceprint_status"] == "not_computed" for window in speaker_diag["windows"])
    assert speaker_diag["voiceprint_rejection_reason"] == "voice_library_empty"
    assert result.diagnostics["speakers"]["SPEAKER_01"]["voiceprint_rejection_reason"] == "no_voiceprint_windows"


def test_match_uses_best_pairwise_pool_score():
    speaker_voiceprints = {
        "SPEAKER_00": [_unit([1.0, 0.0]), _unit([0.0, 1.0])],
    }
    library_voiceprints = {
        "Alice": [_unit([1.0, 0.0])],
        "Bob": [_unit([0.8, 0.6])],
    }

    mapping = du.match_speakers_to_names(
        speaker_voiceprints,
        library_voiceprints,
        threshold=0.6,
        margin=0.1,
    )

    assert mapping == {"SPEAKER_00": "Alice"}


def test_match_diagnostics_include_scores_and_acceptance_reason():
    speaker_voiceprints = {
        "SPEAKER_00": [_unit([1.0, 0.0]), _unit([0.9, 0.1])],
    }
    library_voiceprints = {
        "Alice": [_unit([1.0, 0.0]), _unit([0.8, 0.2])],
        "Bob": [_unit([0.0, 1.0])],
    }

    result = du.match_speakers_to_names_with_diagnostics(
        speaker_voiceprints,
        library_voiceprints,
        threshold=0.6,
        margin=0.1,
    )

    speaker_diag = result.diagnostics["speakers"]["SPEAKER_00"]
    assert result.mapping == {"SPEAKER_00": "Alice"}
    assert speaker_diag["assigned_label"] == "Alice"
    assert speaker_diag["rejection_reason"] == "accepted"
    assert speaker_diag["best_name"] == "Alice"
    assert speaker_diag["second_best_name"] == "Bob"
    assert set(speaker_diag["scores"]) == {"Alice", "Bob"}


def test_match_rejects_ambiguous_margin():
    speaker_voiceprints = {"SPEAKER_00": [_unit([1.0, 0.0])]}
    library_voiceprints = {
        "Alice": [_unit([1.0, 0.0])],
        "Bob": [_unit([0.99, 0.01])],
    }

    mapping = du.match_speakers_to_names(
        speaker_voiceprints,
        library_voiceprints,
        threshold=0.6,
        margin=0.05,
    )

    assert mapping == {"SPEAKER_00": "ANONYMOUS_SPEAKER_00"}


def test_match_diagnostics_include_speakers_without_voiceprints():
    result = du.match_speakers_to_names_with_diagnostics(
        {},
        {"Alice": [_unit([1.0, 0.0])]},
        threshold=0.6,
        margin=0.05,
        diarized_speakers=["SPEAKER_00"],
        voiceprint_rejection_reasons={"SPEAKER_00": "min_total_speech_not_met"},
    )

    speaker_diag = result.diagnostics["speakers"]["SPEAKER_00"]
    assert result.mapping == {"SPEAKER_00": "ANONYMOUS_SPEAKER_00"}
    assert speaker_diag["scores"] == {}
    assert speaker_diag["assigned_label"] == "ANONYMOUS_SPEAKER_00"
    assert speaker_diag["rejection_reason"] == "min_total_speech_not_met"


def test_match_rejects_below_threshold():
    speaker_voiceprints = {"SPEAKER_00": [_unit([1.0, 0.0])]}
    library_voiceprints = {"Alice": [_unit([0.0, 1.0])]}

    mapping = du.match_speakers_to_names(
        speaker_voiceprints,
        library_voiceprints,
        threshold=0.6,
        margin=0.05,
    )

    assert mapping == {"SPEAKER_00": "ANONYMOUS_SPEAKER_00"}


def test_match_assigns_duplicate_known_person_to_best_scoring_speaker():
    speaker_voiceprints = {
        "SPEAKER_00": [_unit([0.8, 0.6])],
        "SPEAKER_01": [_unit([1.0, 0.0])],
    }
    library_voiceprints = {"Alice": [_unit([1.0, 0.0])]}

    result = du.match_speakers_to_names_with_diagnostics(
        speaker_voiceprints,
        library_voiceprints,
        threshold=0.6,
        margin=0.05,
    )

    assert result.mapping == {
        "SPEAKER_00": "ANONYMOUS_SPEAKER_00",
        "SPEAKER_01": "Alice",
    }
    assert result.diagnostics["speakers"]["SPEAKER_00"]["rejection_reason"] == (
        "known_person_already_assigned_to_better_match"
    )
    assert result.diagnostics["speakers"]["SPEAKER_01"]["rejection_reason"] == "accepted"


def test_match_does_not_fallback_to_second_best_when_best_person_is_taken():
    speaker_voiceprints = {
        "SPEAKER_00": [_unit([0.8, 0.6])],
        "SPEAKER_01": [_unit([1.0, 0.0])],
    }
    library_voiceprints = {
        "Alice": [_unit([1.0, 0.0])],
        "Bob": [_unit([0.0, 1.0])],
    }

    result = du.match_speakers_to_names_with_diagnostics(
        speaker_voiceprints,
        library_voiceprints,
        threshold=0.5,
        margin=0.1,
    )

    speaker_diag = result.diagnostics["speakers"]["SPEAKER_00"]
    assert result.mapping == {
        "SPEAKER_00": "ANONYMOUS_SPEAKER_00",
        "SPEAKER_01": "Alice",
    }
    assert speaker_diag["best_name"] == "Alice"
    assert speaker_diag["second_best_name"] == "Bob"
    assert speaker_diag["rejection_reason"] == "known_person_already_assigned_to_better_match"


def test_exclusive_speaker_segments_removes_overlapped_speech():
    diarize_df = pd.DataFrame(
        [
            {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
            {"start": 8.0, "end": 15.0, "speaker": "SPEAKER_01"},
            {"start": 20.0, "end": 30.0, "speaker": "SPEAKER_00"},
            {"start": 24.0, "end": 25.0, "speaker": "SPEAKER_02"},
        ]
    )

    exclusive = du._exclusive_speaker_segments(diarize_df)

    assert {spk: [(seg.start, seg.end) for seg in segs] for spk, segs in exclusive.items()} == {
        "SPEAKER_00": [(0.0, 8.0), (20.0, 24.0), (25.0, 30.0)],
        "SPEAKER_01": [(10.0, 15.0)],
        "SPEAKER_02": [],
    }


def test_speaker_voiceprints_skip_overlapped_speech(monkeypatch):
    diarize_df = pd.DataFrame(
        [
            {"start": 0.0, "end": 12.0, "speaker": "SPEAKER_00"},
            {"start": 3.0, "end": 9.0, "speaker": "SPEAKER_01"},
        ]
    )
    monkeypatch.setattr(du.whisperx, "load_audio", MagicMock(return_value=np.zeros(12 * 16000, dtype=np.float32)))
    measured_crops = []

    def fake_voiceprint(_model, _audio, device, crop, min_duration_sec):
        measured_crops.append((crop.start, crop.end))
        return np.asarray([1.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(du, "compute_voiceprint", fake_voiceprint)

    result = du.speaker_voiceprints_from_diarization_with_diagnostics(
        object(),
        "dummy.wav",
        diarize_df,
        device="cpu",
        window_sec=10.0,
        min_window_sec=2.0,
        min_total_speech_sec=0.0,
        max_windows_per_spk=12,
    )

    assert measured_crops == [(0.0, 3.0), (9.0, 12.0)]
    assert result.diagnostics["speakers"]["SPEAKER_00"]["overlap_excluded_sec"] == pytest.approx(6.0)
    fully_overlapped = result.diagnostics["speakers"]["SPEAKER_01"]
    assert fully_overlapped["candidate_window_count"] == 0
    assert fully_overlapped["voiceprint_rejection_reason"] == "no_voiceprint_windows"
