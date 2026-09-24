from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

import src.asr.diarization as diarization
from src.asr.utils.diarization_utils import relabel_whisperx_segments


def test_relabel_whisperx_segments_updates_segment_and_word_speakers():
    result = {
        "segments": [
            {
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "ciao", "speaker": "SPEAKER_00"},
                    {"word": "ok", "speaker": "SPEAKER_01"},
                    {"word": "missing"},
                ],
            }
        ]
    }

    relabeled = relabel_whisperx_segments(
        result,
        {
            "SPEAKER_00": "Alice",
            "SPEAKER_01": "Bob",
        },
    )

    assert relabeled["segments"][0]["speaker"] == "Alice"
    assert relabeled["segments"][0]["words"] == [
        {"word": "ciao", "speaker": "Alice"},
        {"word": "ok", "speaker": "Bob"},
        {"word": "missing"},
    ]


def test_speaker_identification_stage_reads_saved_artifacts(monkeypatch):
    scratch_dir = Path("tests/.tmp_diarization_artifacts").resolve()
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)

    paths_settings = SimpleNamespace(
        input_path=str(scratch_dir / "260614_0841.mp3"),
        raw_asr_dir=str(scratch_dir / "raw" / "asr"),
        aligned_transcripts_dir=str(scratch_dir / "raw" / "aligned_transcripts"),
        diarization_segments_dir=str(scratch_dir / "raw" / "diarization_segments"),
        diarized_words_dir=str(scratch_dir / "raw" / "diarized_words"),
        identified_words_dir=str(scratch_dir / "raw" / "identified_words"),
        diarized_transcripts_dir=str(scratch_dir / "diarized"),
        speaker_identification_diagnostics_dir=str(scratch_dir / "raw" / "speaker_identification_diagnostics"),
        speaker_identification_windows_dir=str(scratch_dir / "raw" / "speaker_identification_windows"),
    )
    input_path = paths_settings.input_path

    try:
        Path(input_path).parent.mkdir(parents=True, exist_ok=True)
        Path(input_path).write_text("audio", encoding="utf-8")
        monkeypatch.setattr(diarization, "_paths_settings", paths_settings)

        diarization.save_diarization_segments(
            pd.DataFrame([{"start": 0.0, "end": 3.5, "speaker": "SPEAKER_00"}]),
            input_path,
        )
        diarization.save_diarized_words(
            {
                "segments": [
                    {
                        "start": 0.0,
                        "end": 3.5,
                        "speaker": "SPEAKER_00",
                        "words": [{"word": "ciao", "start": 0.0, "speaker": "SPEAKER_00"}],
                    }
                ]
            },
            input_path,
        )

        def fake_identify_speakers(
            audio_path: str,
            diarize_df: Any,
            result: dict[str, Any],
            threshold: float,
        ) -> tuple[dict[str, str], dict[str, Any], str]:
            assert audio_path == input_path
            assert list(diarize_df["speaker"]) == ["SPEAKER_00"]
            result["segments"][0]["speaker"] = "Alice"
            result["segments"][0]["words"][0]["speaker"] = "Alice"
            diagnostics = {
                "enrolled_speakers": ["Alice"],
                "settings": {"threshold": threshold},
                "speakers": {"SPEAKER_00": {"assigned_label": "Alice", "rejection_reason": "accepted"}},
            }
            diagnostics_path = diarization.save_speaker_identification_diagnostics(diagnostics, input_path)
            return {"SPEAKER_00": "Alice"}, result, diagnostics_path

        monkeypatch.setattr(diarization, "_identify_speakers_in_diarized_result", fake_identify_speakers)

        identified_words_path, transcript_path, diagnostics_path = diarization.identify_speakers(
            input_path=input_path,
            threshold=0.7,
        )

        segments = json.loads((scratch_dir / "raw" / "diarization_segments" / "260614_0841.json").read_text())
        identified_result = json.loads(Path(identified_words_path).read_text())
        assert segments == [{"speaker": "SPEAKER_00", "start": 0.0, "end": 3.5, "duration_sec": 3.5}]
        assert Path(identified_words_path).name == "260614_0841.json"
        assert identified_result["segments"][0]["speaker"] == "Alice"
        assert identified_result["segments"][0]["words"][0]["speaker"] == "Alice"
        assert json.loads(Path(transcript_path).read_text())["turns"] == [
            {"speaker": "Alice", "time": "08:41", "start_sec": 0.0, "end_sec": 0.0, "text": "ciao"}
        ]
        assert json.loads(Path(diagnostics_path).read_text()) == {
            "enrolled_speakers": ["Alice"],
            "settings": {"threshold": 0.7},
            "speakers": {"SPEAKER_00": {"assigned_label": "Alice", "rejection_reason": "accepted"}},
        }
    finally:
        if scratch_dir.exists():
            shutil.rmtree(scratch_dir)


def test_diarized_transcript_accepts_free_form_filenames(tmp_path):
    result = {
        "segments": [
            {
                "start": 62.0,
                "speaker": "Alice",
                "words": [
                    {"word": "buongiorno", "start": 62.0, "end": 62.6, "speaker": "Alice"},
                    {"word": "a", "start": 62.7, "end": 62.8, "speaker": "Alice"},
                    {"word": "tutti", "start": 62.9, "end": 63.4, "speaker": "Alice"},
                ],
            }
        ]
    }

    transcript_path = diarization.save_diarized_transcript({}, result, "Riunione di prova è.m4a", out_dir=str(tmp_path))

    transcript = json.loads(Path(transcript_path).read_text(encoding="utf-8"))
    assert Path(transcript_path).name == "Riunione di prova è.json"
    assert transcript["date"] is None
    assert transcript["turns"] == [
        {"speaker": "Alice", "time": "00:01:02", "start_sec": 62.0, "end_sec": 63.4, "text": "buongiorno a tutti"}
    ]
