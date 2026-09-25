"""
Tests for the voiceprints of the voice library, pool by pool.

Heavy ML dependencies are mocked. Tiny WAV files are real so duration checks and
fingerprints exercise the actual filesystem behavior.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

import src.asr.voice_library as voice_library_mod
import src.asr.voiceprint_cache as ec


VOICEPRINT_DIM = 256


def _make_wav(path: str | Path, duration_sec: float = 1.0, sr: int = 16000) -> None:
    n = int(duration_sec * sr)
    sf.write(str(path), np.zeros(n, dtype=np.float32), sr)


def _build_pool_dir(
    base: Path,
    layout: Dict[str, Dict[str, int]],
    clip_duration: float = 1.0,
) -> ec.LibraryPools:
    voice_library: ec.LibraryPools = {}
    for person, pools in layout.items():
        voice_library[person] = {}
        for pool, n_clips in pools.items():
            pool_dir = base / person / pool
            pool_dir.mkdir(parents=True, exist_ok=True)
            clips = []
            for i in range(1, n_clips + 1):
                p = pool_dir / f"clip_{i}.wav"
                _make_wav(p, duration_sec=clip_duration)
                clips.append(os.path.normpath(str(p)))
            voice_library[person][pool] = clips
    return voice_library


_voiceprint_counter = 0


def _fake_voiceprint(_model, _audio, device, **_kw) -> np.ndarray:
    global _voiceprint_counter
    _voiceprint_counter += 1
    rng = np.random.RandomState(_voiceprint_counter)
    return rng.rand(VOICEPRINT_DIM).astype(np.float32)


@pytest.fixture(autouse=True)
def _reset_voiceprint_counter():
    global _voiceprint_counter
    _voiceprint_counter = 0
    yield


@pytest.fixture()
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "_CACHE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def voice_library_dir(tmp_path):
    base = tmp_path / "voice_library"
    voice_library = _build_pool_dir(base, {"Alice": {"inside": 2, "car": 1}, "Bob": {"outside": 2}})
    return base, voice_library


@pytest.fixture()
def mock_ml(monkeypatch):
    fake_model = MagicMock(name="voiceprint_model")
    mock_load_model = MagicMock(return_value=fake_model)
    mock_voiceprint = MagicMock(side_effect=_fake_voiceprint)
    mock_load_audio = MagicMock(return_value=np.zeros(16000, dtype=np.float32))

    monkeypatch.setattr(ec, "load_voiceprint_model", mock_load_model)
    monkeypatch.setattr(ec, "compute_voiceprint", mock_voiceprint)
    monkeypatch.setattr(ec, "whisperx", MagicMock(load_audio=mock_load_audio))

    return {"load_model": mock_load_model, "voiceprint": mock_voiceprint, "load_audio": mock_load_audio}


class TestVoiceLibraryScan:
    def test_discovers_person_pool_layout(self, tmp_path):
        base = tmp_path / "voice_library"
        _build_pool_dir(base, {"Alice": {"inside": 1}})

        result = voice_library_mod.scan_voice_library(str(base))

        assert set(result) == {"Alice"}
        assert set(result["Alice"]) == {"inside"}
        assert len(result["Alice"]["inside"]) == 1

    def test_audio_directly_under_person_folder_forms_the_root_pool(self, tmp_path):
        base = tmp_path / "voice_library"
        person_dir = base / "Alice"
        person_dir.mkdir(parents=True)
        _make_wav(person_dir / "root_clip.wav")
        (person_dir / "desktop.ini").write_text("not audio", encoding="utf-8")

        result = voice_library_mod.scan_voice_library(str(base))

        assert result == {"Alice": {voice_library_mod.ROOT_POOL: [os.path.normpath(str(person_dir / "root_clip.wav"))]}}

    def test_root_clips_and_pool_subfolders_are_combined(self, tmp_path):
        base = tmp_path / "voice_library"
        _build_pool_dir(base, {"Alice": {"car": 2}})
        _make_wav(base / "Alice" / "root_clip.wav")

        result = voice_library_mod.scan_voice_library(str(base))

        assert set(result["Alice"]) == {voice_library_mod.ROOT_POOL, "car"}
        assert len(result["Alice"]["car"]) == 2

    def test_person_without_clips_is_skipped_with_a_warning(self, tmp_path):
        base = tmp_path / "voice_library"
        (base / "Alice").mkdir(parents=True)
        _build_pool_dir(base, {"Bob": {"inside": 1}})

        with patch.object(voice_library_mod, "log_warning") as mock_warn:
            result = voice_library_mod.scan_voice_library(str(base))

        assert set(result) == {"Bob"}
        assert any("Alice" in call.args for call in mock_warn.call_args_list)

    def test_library_without_clips_leaves_everyone_anonymous(self, tmp_path, monkeypatch):
        base = tmp_path / "voice_library"
        (base / "Alice" / "inside").mkdir(parents=True)
        monkeypatch.setattr(voice_library_mod, "get_paths_settings", lambda: MagicMock(voice_library_dir=str(base)))

        with patch("src.asr.voiceprint_cache.build_library_voiceprints") as mock_build:
            assert voice_library_mod.load_library_voiceprints("cpu") is None

        mock_build.assert_not_called()

    def test_includes_nested_audio_inside_pool(self, tmp_path):
        base = tmp_path / "voice_library"
        nested = base / "Alice" / "inside" / "phone"
        nested.mkdir(parents=True)
        _make_wav(nested / "clip.wav")

        result = voice_library_mod.scan_voice_library(str(base))

        assert len(result["Alice"]["inside"]) == 1

    def test_empty_pool_warns_and_is_skipped(self, tmp_path):
        base = tmp_path / "voice_library"
        (base / "Alice" / "empty").mkdir(parents=True)
        _build_pool_dir(base, {"Alice": {"inside": 1}})

        with patch.object(voice_library_mod, "log_warning") as mock_warn:
            result = voice_library_mod.scan_voice_library(str(base))

        assert set(result["Alice"]) == {"inside"}
        mock_warn.assert_called_once()


class TestVoiceprintRoundTrip:
    def test_encode_decode_preserves_values(self):
        original = np.random.rand(VOICEPRINT_DIM).astype(np.float32)
        encoded = ec._voiceprint_to_json(original)
        decoded = ec._voiceprint_from_json(encoded)
        np.testing.assert_array_equal(original, decoded)


class TestPoolNeedsUpdate:
    def test_none_cached_always_needs_update(self):
        assert ec._pool_needs_update(None, [("a.wav", 100, 1.0)]) is True

    def test_same_fingerprints_no_update(self):
        fps = [("a.wav", 100, 1.0), ("b.wav", 200, 2.0)]
        cached = {"clips": [{"path": "a.wav", "size": 100, "mtime": 1.0},
                             {"path": "b.wav", "size": 200, "mtime": 2.0}]}
        assert ec._pool_needs_update(cached, fps) is False

    def test_different_fingerprint_needs_update(self):
        cached = {"clips": [{"path": "a.wav", "size": 100, "mtime": 1.0}]}
        assert ec._pool_needs_update(cached, [("a.wav", 999, 1.0)]) is True


class TestBuildLibraryVoiceprints:
    def test_fresh_build_computes_pools(self, cache_dir, voice_library_dir, mock_ml):
        base, voice_library = voice_library_dir
        result = ec.build_library_voiceprints(voice_library, str(base), "cpu")

        assert set(result) == {"Alice", "Bob"}
        assert len(result["Alice"]) == 2
        assert len(result["Bob"]) == 1
        for voiceprints in result.values():
            for emb in voiceprints:
                assert emb.shape == (VOICEPRINT_DIM,)
                assert emb.dtype == np.float32
                assert np.linalg.norm(emb) == pytest.approx(1.0)

        assert mock_ml["voiceprint"].call_count == 5
        assert mock_ml["load_model"].call_count == 1

    def test_cache_file_created_with_current_schema(self, cache_dir, voice_library_dir, mock_ml):
        base, voice_library = voice_library_dir
        ec.build_library_voiceprints(voice_library, str(base), "cpu")

        data = json.loads((cache_dir / ec._CACHE_FILENAME).read_text(encoding="utf-8"))

        assert data["schema_version"] == ec._SCHEMA_VERSION
        assert set(data["people"]) == {"Alice", "Bob"}
        assert set(data["people"]["Alice"]["pools"]) == {"inside", "car"}

    def test_second_run_is_cache_hit(self, cache_dir, voice_library_dir, mock_ml):
        base, voice_library = voice_library_dir
        first = ec.build_library_voiceprints(voice_library, str(base), "cpu")

        mock_ml["voiceprint"].reset_mock()
        mock_ml["load_model"].reset_mock()

        second = ec.build_library_voiceprints(voice_library, str(base), "cpu")

        assert mock_ml["voiceprint"].call_count == 0
        assert mock_ml["load_model"].call_count == 0
        for name in first:
            for left, right in zip(first[name], second[name]):
                np.testing.assert_array_equal(left, right)

    def test_recompute_only_changed_pool(self, cache_dir, voice_library_dir, mock_ml):
        base, voice_library = voice_library_dir
        ec.build_library_voiceprints(voice_library, str(base), "cpu")

        mock_ml["voiceprint"].reset_mock()
        mock_ml["load_model"].reset_mock()

        clip = voice_library["Alice"]["inside"][0]
        time.sleep(0.05)
        _make_wav(clip, duration_sec=2.0)

        ec.build_library_voiceprints(voice_library, str(base), "cpu")

        assert mock_ml["voiceprint"].call_count == 2
        assert mock_ml["load_model"].call_count == 1

    def test_stale_person_and_pool_removed_from_cache(self, cache_dir, voice_library_dir, mock_ml):
        base, voice_library = voice_library_dir
        ec.build_library_voiceprints(voice_library, str(base), "cpu")

        del voice_library["Bob"]
        del voice_library["Alice"]["car"]
        ec.build_library_voiceprints(voice_library, str(base), "cpu")

        data = json.loads((cache_dir / ec._CACHE_FILENAME).read_text(encoding="utf-8"))
        assert set(data["people"]) == {"Alice"}
        assert set(data["people"]["Alice"]["pools"]) == {"inside"}

    def test_outdated_cache_recomputes_all(self, cache_dir, voice_library_dir, mock_ml):
        base, voice_library = voice_library_dir
        (cache_dir / ec._CACHE_FILENAME).write_text(
            json.dumps({"schema_version": ec._SCHEMA_VERSION - 1, "people": {"Alice": {"pools": {}}}}),
            encoding="utf-8",
        )

        ec.build_library_voiceprints(voice_library, str(base), "cpu")

        assert mock_ml["voiceprint"].call_count == 5

    def test_empty_voice_library_raises(self, cache_dir, mock_ml):
        with pytest.raises(RuntimeError, match="empty"):
            ec.build_library_voiceprints({}, "dummy", "cpu")

    def test_person_with_no_pools_raises(self, cache_dir, voice_library_dir, mock_ml):
        base, voice_library = voice_library_dir
        voice_library["Ghost"] = {}

        with pytest.raises(RuntimeError, match="Ghost"):
            ec.build_library_voiceprints(voice_library, str(base), "cpu")


class TestValidateVoiceClips:
    def test_warns_too_few_clips(self, tmp_path):
        base = tmp_path / "voice_library"
        voice_library = _build_pool_dir(base, {"Solo": {"inside": 1}}, clip_duration=10.0)

        with patch.object(ec, "log_warning") as mock_warn:
            ec._validate_voice_clips(voice_library)
            messages = " ".join(str(c) for c in mock_warn.call_args_list)
            assert "only %d voice clip" in messages

    def test_warns_short_clip(self, tmp_path):
        base = tmp_path / "voice_library"
        voice_library = _build_pool_dir(base, {"Shorty": {"inside": 3}}, clip_duration=2.0)

        with patch.object(ec, "log_warning") as mock_warn:
            ec._validate_voice_clips(voice_library)
            messages = " ".join(str(c) for c in mock_warn.call_args_list)
            assert "Short clips" in messages

    def test_warns_low_total_duration(self, tmp_path):
        base = tmp_path / "voice_library"
        voice_library = _build_pool_dir(base, {"Brief": {"inside": 3}}, clip_duration=6.0)

        with patch.object(ec, "log_warning") as mock_warn:
            ec._validate_voice_clips(voice_library)
            messages = " ".join(str(c) for c in mock_warn.call_args_list)
            assert "voice clips last" in messages

    def test_no_warnings_when_all_good(self, tmp_path):
        base = tmp_path / "voice_library"
        voice_library = _build_pool_dir(base, {"Good": {"inside": 3}}, clip_duration=15.0)

        with patch.object(ec, "log_warning") as mock_warn:
            ec._validate_voice_clips(voice_library)
            mock_warn.assert_not_called()
