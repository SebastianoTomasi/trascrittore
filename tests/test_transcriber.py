from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import src.asr.diarization as diarization
import src.transcriber.runner as runner
from src.asr.utils.config import SpeakerSettings, WhisperSettings
from src.transcriber.transcript import (
    build_payload,
    display_labels,
    render_payload_text,
    render_text,
    rename_speakers,
    speaker_labels,
    speaker_summaries,
)


def _turn(speaker: str, start: float, end: float, text: str) -> dict[str, object]:
    segments = [{"start_sec": start, "end_sec": end, "text": text}]
    return {"speaker": speaker, "time": "", "start_sec": start, "end_sec": end, "text": text, "segments": segments}


TURNS = [
    _turn("Mario Rossi", 3.0, 65.0, "buongiorno a tutti partiamo dal budget"),
    _turn("ANONYMOUS_SPEAKER_03", 66.0, 80.0, "io direi di rimandare"),
    _turn("Mario Rossi", 81.0, 90.0, "va bene"),
    _turn("ANONYMOUS_SPEAKER_01", 91.0, 95.0, "sono d'accordo con la proposta di rimandare tutto"),
]

DIAGNOSTICS = {
    "speakers": {
        "SPEAKER_00": {
            "assigned_label": "Mario Rossi",
            "best_name": "Mario Rossi",
            "best_score": 0.8123,
            "second_best_name": "Luca Bianchi",
            "score_margin": 0.4011,
            "rejection_reason": "accepted",
        },
        "SPEAKER_03": {
            "assigned_label": "ANONYMOUS_SPEAKER_03",
            "best_name": "Luca Bianchi",
            "best_score": 0.52,
            "second_best_name": "Mario Rossi",
            "score_margin": 0.2,
            "rejection_reason": "below_threshold",
            "windows": [
                {"start": 66.0, "end": 76.0, "voiceprint_status": "computed"},
                {"start": 76.0, "end": 80.0, "voiceprint_status": "skipped"},
                {"start": 76.12345, "end": 79.5, "voiceprint_status": "not_computed"},
            ],
        },
        "SPEAKER_01": {
            "assigned_label": "ANONYMOUS_SPEAKER_01",
            "best_name": None,
            "best_score": -1.0,
            "second_best_name": None,
            "score_margin": 0.0,
            "rejection_reason": "no_voiceprint_windows",
        },
    }
}


def test_display_labels_number_anonymous_voices_by_first_appearance():
    turns = TURNS + [_turn("UNATTRIBUTED", 96.0, 97.0, "mh")]

    assert display_labels(turns, "ANONYMOUS_") == {
        "Mario Rossi": "Mario Rossi",
        "ANONYMOUS_SPEAKER_03": "Persona 1",
        "ANONYMOUS_SPEAKER_01": "Persona 2",
        "UNATTRIBUTED": "Voce non attribuita",
    }


def test_render_text_lists_speakers_and_timestamped_turns():
    labels = display_labels(TURNS, "ANONYMOUS_")

    text = render_text(
        source_name="Registrazione budget.m4a",
        duration_sec=3725.0,
        device="cuda",
        fallback_reason=None,
        turns=TURNS,
        labels=labels,
    )

    assert text.splitlines() == [
        "Trascrizione di: Registrazione budget.m4a",
        "Durata: 01:02:05 · Elaborata su GPU",
        "Chi parla: Mario Rossi (1 min), Persona 1 (<1 min), Persona 2 (<1 min)",
        "",
        "[00:00:03] Mario Rossi: buongiorno a tutti partiamo dal budget",
        "",
        "[00:01:06] Persona 1: io direi di rimandare",
        "",
        "[00:01:21] Mario Rossi: va bene",
        "",
        "[00:01:31] Persona 2: sono d'accordo con la proposta di rimandare tutto",
    ]
    assert text.endswith("tutto\n")


def test_render_text_leaves_unattributed_words_out_of_the_speakers():
    turns = TURNS[:1] + [_turn("UNATTRIBUTED", 66.0, 67.0, "ecco")]

    text = render_text(
        source_name="a.wav",
        duration_sec=70.0,
        device="cuda",
        fallback_reason=None,
        turns=turns,
        labels=display_labels(turns, "ANONYMOUS_"),
    )

    assert "Chi parla: Mario Rossi (1 min)" in text.splitlines()
    assert "[00:01:06] Voce non attribuita: ecco" in text.splitlines()


def test_render_text_warns_when_processed_on_cpu():
    text = render_text(
        source_name="a.wav",
        duration_sec=10.0,
        device="cpu",
        fallback_reason="Nessuna GPU NVIDIA disponibile.",
        turns=[],
        labels={},
    )

    assert "Elaborata su CPU" in text
    assert "ATTENZIONE: elaborata su CPU invece che su GPU. Nessuna GPU NVIDIA disponibile." in text.splitlines()
    assert "(Nella registrazione non è stato trovato parlato.)" in text.splitlines()


def test_speaker_summaries_expose_scores_for_calibration():
    labels = display_labels(TURNS, "ANONYMOUS_")

    summaries = speaker_summaries(TURNS, labels, DIAGNOSTICS)

    assert summaries == [
        {
            "label": "Mario Rossi",
            "recognized": True,
            "turn_count": 2,
            "speech_sec": 71.0,
            "best_match": "Mario Rossi",
            "score": 0.812,
            "second_match": "Luca Bianchi",
            "margin": 0.401,
            "reason": "accepted",
            "windows": [],
        },
        {
            "label": "Persona 1",
            "recognized": False,
            "turn_count": 1,
            "speech_sec": 14.0,
            "best_match": "Luca Bianchi",
            "score": 0.52,
            "second_match": "Mario Rossi",
            "margin": 0.2,
            "reason": "below_threshold",
            "windows": [{"start": 66.0, "end": 76.0}, {"start": 76.123, "end": 79.5}],
        },
        {
            "label": "Persona 2",
            "recognized": False,
            "turn_count": 1,
            "speech_sec": 4.0,
            "best_match": None,
            "score": None,
            "second_match": None,
            "margin": None,
            "reason": "no_voiceprint_windows",
            "windows": [],
        },
    ]


def _payload(labels: dict[str, str] | None = None) -> dict[str, object]:
    labels = labels or display_labels(TURNS, "ANONYMOUS_")
    return build_payload(
        source_name="Registrazione budget.m4a",
        recording="C:\\Registrazioni\\Registrazione budget.m4a",
        duration_sec=95.96,
        device="cpu",
        compute_type="int8",
        fallback_reason="Nessuna GPU NVIDIA disponibile.",
        elapsed_sec=301.26,
        turns=TURNS,
        labels=labels,
        speakers=speaker_summaries(TURNS, labels, DIAGNOSTICS),
    )


def test_build_payload_uses_display_labels_and_records_the_cpu_warning():
    labels = {**display_labels(TURNS, "ANONYMOUS_"), "ANONYMOUS_SPEAKER_03": "Luca Bianchi"}

    payload = build_payload(
        source_name="Registrazione budget.m4a",
        recording="C:\\Registrazioni\\Registrazione budget.m4a",
        duration_sec=95.04,
        device="cpu",
        compute_type="int8",
        fallback_reason="Nessuna GPU NVIDIA disponibile.",
        elapsed_sec=301.26,
        turns=TURNS,
        labels=labels,
        speakers=speaker_summaries(TURNS, labels, DIAGNOSTICS),
    )

    assert payload["recording"] == "C:\\Registrazioni\\Registrazione budget.m4a"
    assert payload["device"] == "cpu"
    assert payload["compute_type"] == "int8"
    assert payload["warnings"] == ["Elaborata su CPU invece che su GPU. Nessuna GPU NVIDIA disponibile."]
    assert (payload["duration_sec"], payload["elapsed_sec"]) == (95.0, 301.3)
    assert [speaker["label"] for speaker in payload["speakers"]] == ["Mario Rossi", "Luca Bianchi", "Persona 2"]
    assert payload["turns"][1] == {
        "speaker": "Luca Bianchi",
        "start": "00:01:06",
        "start_sec": 66.0,
        "end_sec": 80.0,
        "text": "io direi di rimandare",
        "segments": [{"start_sec": 66.0, "end_sec": 80.0, "text": "io direi di rimandare"}],
    }


def test_rename_speakers_changes_only_the_named_labels():
    payload = _payload()

    renamed = rename_speakers(payload, {"Persona 1": "Luca Bianchi"})

    assert speaker_labels(renamed) == ["Mario Rossi", "Luca Bianchi", "Persona 2"]
    assert [turn["speaker"] for turn in renamed["turns"]] == ["Mario Rossi", "Luca Bianchi", "Mario Rossi", "Persona 2"]
    assert renamed["speakers"][1]["windows"] == payload["speakers"][1]["windows"]
    assert {key: value for key, value in renamed.items() if key not in ("speakers", "turns")} == {
        key: value for key, value in payload.items() if key not in ("speakers", "turns")
    }
    assert speaker_labels(payload) == ["Mario Rossi", "Persona 1", "Persona 2"]


def test_text_rendered_from_the_payload_matches_after_renaming():
    payload = _payload()
    renamed_by_labels = _payload({**display_labels(TURNS, "ANONYMOUS_"), "ANONYMOUS_SPEAKER_03": "Luca Bianchi"})

    text = render_payload_text(rename_speakers(payload, {"Persona 1": "Luca Bianchi"}))

    assert text == render_payload_text(renamed_by_labels)
    assert text.splitlines()[1] == "Durata: 00:01:36 · Elaborata su CPU"
    assert "ATTENZIONE: elaborata su CPU invece che su GPU. Nessuna GPU NVIDIA disponibile." in text.splitlines()
    assert "[00:01:06] Luca Bianchi: io direi di rimandare" in text.splitlines()


def test_output_paths_sit_next_to_the_audio(tmp_path):
    txt_path, json_path = runner.output_paths(tmp_path / "Registrazione budget.m4a", None)

    assert txt_path == tmp_path / "Registrazione budget - trascrizione.txt"
    assert json_path == tmp_path / "Registrazione budget - trascrizione.json"


def _cpu_settings() -> WhisperSettings:
    return WhisperSettings(
        model_id="large-v3",
        device="cpu",
        compute_type="int8",
        batch_size=8,
        language="it",
        initial_prompt=None,
        vad_onset=0.5,
        vad_offset=0.363,
        vad_chunk_size=30,
        fallback_reason="Nessuna GPU NVIDIA disponibile.",
    )


@pytest.fixture
def fake_pipeline(tmp_path, monkeypatch):
    """
    Replace the ML steps with fakes that record their calls and produce saved artifacts.
    """
    calls: list[object] = []
    monkeypatch.setattr(diarization, "load_audio", lambda _path: np.zeros(16000 * 95, dtype=np.float32))
    monkeypatch.setattr(diarization, "transcribe_recording", lambda path: calls.append(("transcribe", Path(path).suffix)))
    monkeypatch.setattr(diarization, "align_transcript", lambda _path: calls.append("align"))
    monkeypatch.setattr(
        diarization,
        "diarize_transcript",
        lambda _path, num_speakers=None: calls.append(("diarize", num_speakers)),
    )

    def fake_recognize(_path: str) -> tuple[str, str, str]:
        calls.append("recognize")
        transcript_path = tmp_path / "artifacts" / "transcript.json"
        diagnostics_path = tmp_path / "artifacts" / "diagnostics.json"
        transcript_path.parent.mkdir(exist_ok=True)
        transcript_path.write_text(json.dumps({"date": None, "turns": TURNS}), encoding="utf-8")
        diagnostics_path.write_text(json.dumps(DIAGNOSTICS), encoding="utf-8")
        return "recognized.json", str(transcript_path), str(diagnostics_path)

    monkeypatch.setattr(diarization, "recognize_speakers", fake_recognize)
    monkeypatch.setattr(runner, "get_whisper_settings", _cpu_settings)
    monkeypatch.setattr(runner, "get_speaker_settings", lambda: SpeakerSettings(anonymous_prefix="ANONYMOUS_"))
    return calls


def test_run_writes_the_transcript_and_ends_with_a_summary(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "Registrazione di prova è.m4a"
    audio.write_bytes(b"not decoded: load_audio is faked")
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("transcribing asks nothing"))

    summary = runner.run(str(audio), speakers=3)

    assert fake_pipeline == [("transcribe", ".wav"), "align", ("diarize", 3), "recognize"]
    txt_path = tmp_path / "Registrazione di prova è - trascrizione.txt"
    json_path = tmp_path / "Registrazione di prova è - trascrizione.json"
    text = txt_path.read_text(encoding="utf-8")
    assert "[00:01:06] Persona 1: io direi di rimandare" in text
    assert "ATTENZIONE: elaborata su CPU" in text
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["recording"] == str(audio)
    assert payload["warnings"] and payload["device"] == "cpu"
    assert payload["speakers"][1]["windows"] == [{"start": 66.0, "end": 76.0}, {"start": 76.123, "end": 79.5}]
    assert text == render_payload_text(payload)

    assert summary["status"] == "ok"
    assert summary["message"].endswith("Senza nome: Persona 1, Persona 2.")
    assert (summary["transcript_txt"], summary["transcript_json"]) == (str(txt_path), str(json_path))
    assert summary["warnings"] == payload["warnings"]
    assert summary["speakers"] == [
        {"label": "Mario Rossi", "recognized": True, "speech_sec": 71.0},
        {"label": "Persona 1", "recognized": False, "speech_sec": 14.0},
        {"label": "Persona 2", "recognized": False, "speech_sec": 4.0},
    ]
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.count("ATTENZIONE: nessuna GPU disponibile, elaboro su CPU") == 2


def test_run_reports_paths_as_the_person_sees_them(tmp_path, monkeypatch, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    monkeypatch.setenv("TRANSCRIBER_HOST_PATHS", f"{tmp_path.as_posix()}=C:\\Registrazioni|")

    summary = runner.run(str(audio))

    assert summary["transcript_json"] == "C:\\Registrazioni\\call - trascrizione.json"
    assert summary["recording"] == "C:\\Registrazioni\\call.mp4"


def test_run_names_the_output_folder_when_one_is_given(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    out_dir = tmp_path / "uscita"
    out_dir.mkdir()
    monkeypatch.setenv("TRANSCRIBER_HOST_PATHS", f"{out_dir.as_posix()}=C:\\Trascrizioni|")

    runner.run(str(audio), out_dir=str(out_dir))

    err = capsys.readouterr().err
    assert "Nella cartella C:\\Trascrizioni trovi 'call - trascrizione.txt' e 'call - trascrizione.json'." in err
    assert "Accanto alla registrazione" not in err


def test_run_explains_gpu_out_of_memory(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "call.wav"
    audio.write_bytes(b"x")

    def out_of_memory(_path: str) -> None:
        raise RuntimeError("CUDA failed with error out of memory")

    monkeypatch.setattr(diarization, "transcribe_recording", out_of_memory)

    summary = runner.run(str(audio))

    assert summary["status"] == "gpu_out_of_memory"
    assert "batch_size" in summary["message"]
    assert "Memoria della GPU esaurita" in capsys.readouterr().err
    assert not (tmp_path / "call - trascrizione.txt").exists()


def test_run_explains_a_file_without_readable_audio(tmp_path, monkeypatch, capsys, fake_pipeline):
    document = tmp_path / "Verbale.docx"
    document.write_bytes(b"x")

    def undecodable(path: str) -> None:
        raise RuntimeError(f"Failed to load input audio '{path}'.")

    monkeypatch.setattr(diarization, "load_audio", undecodable)

    summary = runner.run(str(document))

    assert summary["status"] == "unreadable_recording"
    assert "Non riesco a leggere la registrazione 'Verbale.docx'" in summary["message"]
    output = capsys.readouterr()
    assert "Non riesco a leggere la registrazione 'Verbale.docx'" in output.err
    assert "Traceback" not in output.out + output.err
    assert fake_pipeline == []


def test_run_reports_a_missing_file(tmp_path, capsys):
    summary = runner.run(str(tmp_path / "manca.m4a"))

    assert summary["status"] == "file_not_found"
    assert "File non trovato" in capsys.readouterr().err
