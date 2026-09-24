from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import src.asr.diarization as diarization
import src.meeting.runner as runner
from src.asr.utils.config import SpeakerSettings, WhisperSettings
from src.meeting.cli import parse_args
from src.meeting.transcript import (
    ask_names,
    build_payload,
    display_labels,
    rename_labels,
    render_text,
    speaker_summaries,
)


def _turn(speaker: str, start: float, end: float, text: str) -> dict[str, object]:
    return {"speaker": speaker, "time": "", "start_sec": start, "end_sec": end, "text": text}


TURNS = [
    _turn("Mario Rossi", 3.0, 65.0, "buongiorno a tutti partiamo dal budget"),
    _turn("UNKNOWN_SPEAKER_03", 66.0, 80.0, "io direi di rimandare"),
    _turn("Mario Rossi", 81.0, 90.0, "va bene"),
    _turn("UNKNOWN_SPEAKER_01", 91.0, 95.0, "sono d'accordo con la proposta di rimandare tutto"),
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
            "assigned_label": "UNKNOWN_SPEAKER_03",
            "best_name": "Luca Bianchi",
            "best_score": 0.52,
            "second_best_name": "Mario Rossi",
            "score_margin": 0.2,
            "rejection_reason": "below_threshold",
        },
        "SPEAKER_01": {
            "assigned_label": "UNKNOWN_SPEAKER_01",
            "best_name": None,
            "best_score": -1.0,
            "second_best_name": None,
            "score_margin": 0.0,
            "rejection_reason": "no_embedding_windows",
        },
    }
}


def test_display_labels_number_unknown_voices_by_first_appearance():
    turns = TURNS + [_turn("UNKNOWN", 96.0, 97.0, "mh")]

    assert display_labels(turns, "UNKNOWN_") == {
        "Mario Rossi": "Mario Rossi",
        "UNKNOWN_SPEAKER_03": "Persona 1",
        "UNKNOWN_SPEAKER_01": "Persona 2",
        "UNKNOWN": "Voce non attribuita",
    }


def test_render_text_lists_participants_and_timestamped_turns():
    labels = display_labels(TURNS, "UNKNOWN_")

    text = render_text(
        source_name="Riunione budget.m4a",
        duration_sec=3725.0,
        device="cuda",
        fallback_reason=None,
        turns=TURNS,
        labels=labels,
    )

    assert text.splitlines() == [
        "Trascrizione di: Riunione budget.m4a",
        "Durata: 01:02:05 · Elaborata su GPU",
        "Partecipanti: Mario Rossi (1 min), Persona 1 (<1 min), Persona 2 (<1 min)",
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


def test_render_text_leaves_unattributed_words_out_of_the_participants():
    turns = TURNS[:1] + [_turn("UNKNOWN", 66.0, 67.0, "ecco")]

    text = render_text(
        source_name="a.wav",
        duration_sec=70.0,
        device="cuda",
        fallback_reason=None,
        turns=turns,
        labels=display_labels(turns, "UNKNOWN_"),
    )

    assert "Partecipanti: Mario Rossi (1 min)" in text.splitlines()
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
    assert "(Nell'audio non è stato trovato parlato.)" in text.splitlines()


def test_speaker_summaries_expose_scores_for_calibration():
    labels = display_labels(TURNS, "UNKNOWN_")

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
            "reason": "no_embedding_windows",
        },
    ]


def test_build_payload_uses_display_labels_and_records_the_cpu_warning():
    labels = rename_labels(display_labels(TURNS, "UNKNOWN_"), {"Persona 1": "Luca Bianchi"})

    payload = build_payload(
        source_name="Riunione budget.m4a",
        duration_sec=95.04,
        device="cpu",
        compute_type="int8",
        fallback_reason="Nessuna GPU NVIDIA disponibile.",
        elapsed_sec=301.26,
        turns=TURNS,
        labels=labels,
        speakers=speaker_summaries(TURNS, labels, DIAGNOSTICS),
    )

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
    }


def test_ask_names_keeps_persona_on_enter_and_shows_examples():
    labels = display_labels(TURNS, "UNKNOWN_")
    answers = iter(["  Luca Bianchi ", ""])
    printed: list[str] = []

    names = ask_names(TURNS, labels, input_fn=lambda _prompt: next(answers), print_fn=printed.append)

    assert names == {"Persona 1": "Luca Bianchi"}
    assert '  [00:01:06] "io direi di rimandare"' in printed


def test_ask_names_stops_at_end_of_input():
    labels = display_labels(TURNS, "UNKNOWN_")

    def closed_input(_prompt: str) -> str:
        raise EOFError

    assert ask_names(TURNS, labels, input_fn=closed_input, print_fn=lambda _line: None) == {}


def test_ask_names_does_not_prompt_when_everyone_is_recognized():
    def unexpected_input(_prompt: str) -> str:
        raise AssertionError("no prompt expected")

    labels = {"Mario Rossi": "Mario Rossi"}
    assert ask_names(TURNS[:1], labels, input_fn=unexpected_input, print_fn=lambda _line: None) == {}


def test_cli_parses_speakers_and_flags():
    args = parse_args(["Riunione.m4a", "--speakers", "3", "--ask-names"])

    assert (args.audio, args.speakers, args.ask_names, args.out_dir) == ("Riunione.m4a", 3, True, None)
    assert parse_args(["Riunione.m4a"]).speakers is None


@pytest.mark.parametrize("value", ["0", "-2", "tre"])
def test_cli_rejects_invalid_speaker_counts(value):
    with pytest.raises(SystemExit):
        parse_args(["Riunione.m4a", "--speakers", value])


def test_output_paths_sit_next_to_the_audio(tmp_path):
    txt_path, json_path = runner.output_paths(tmp_path / "Riunione budget.m4a", None)

    assert txt_path == tmp_path / "Riunione budget - trascrizione.txt"
    assert json_path == tmp_path / "Riunione budget - trascrizione.json"


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
    monkeypatch.setattr(diarization, "transcribe_audio", lambda path: calls.append(("transcribe", Path(path).suffix)))
    monkeypatch.setattr(diarization, "align_transcript", lambda _path: calls.append("align"))
    monkeypatch.setattr(
        diarization,
        "diarize_transcript",
        lambda _path, num_speakers=None: calls.append(("diarize", num_speakers)),
    )

    def fake_identify(_path: str) -> tuple[str, str, str]:
        calls.append("identify")
        transcript_path = tmp_path / "artifacts" / "transcript.json"
        diagnostics_path = tmp_path / "artifacts" / "diagnostics.json"
        transcript_path.parent.mkdir(exist_ok=True)
        transcript_path.write_text(json.dumps({"date": None, "turns": TURNS}), encoding="utf-8")
        diagnostics_path.write_text(json.dumps(DIAGNOSTICS), encoding="utf-8")
        return "identified.json", str(transcript_path), str(diagnostics_path)

    monkeypatch.setattr(diarization, "identify_speakers", fake_identify)
    monkeypatch.setattr(runner, "get_whisper_settings", _cpu_settings)
    monkeypatch.setattr(runner, "get_speaker_settings", lambda: SpeakerSettings(unknown_prefix="UNKNOWN_"))
    return calls


def test_run_writes_transcript_next_to_audio_and_applies_typed_names(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "Riunione di prova è.m4a"
    audio.write_bytes(b"not decoded: load_audio is faked")
    answers = iter(["Luca Bianchi", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    exit_code = runner.run(str(audio), speakers=3, ask_names=True)

    assert exit_code == 0
    assert fake_pipeline == [("transcribe", ".wav"), "align", ("diarize", 3), "identify"]
    text = (tmp_path / "Riunione di prova è - trascrizione.txt").read_text(encoding="utf-8")
    assert "[00:01:06] Luca Bianchi: io direi di rimandare" in text
    assert "Persona 1" not in text
    assert "ATTENZIONE: elaborata su CPU" in text
    payload = json.loads((tmp_path / "Riunione di prova è - trascrizione.json").read_text(encoding="utf-8"))
    assert payload["warnings"] and payload["device"] == "cpu"
    assert [speaker["label"] for speaker in payload["speakers"]] == ["Mario Rossi", "Luca Bianchi", "Persona 2"]
    output = capsys.readouterr().out
    assert output.count("ATTENZIONE: nessuna GPU disponibile, elaboro su CPU") == 2


def test_run_without_prompt_keeps_anonymous_voices(tmp_path, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")

    assert runner.run(str(audio)) == 0

    text = (tmp_path / "call - trascrizione.txt").read_text(encoding="utf-8")
    assert "[00:01:06] Persona 1: io direi di rimandare" in text


def test_run_explains_gpu_out_of_memory(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "call.wav"
    audio.write_bytes(b"x")

    def out_of_memory(_path: str) -> None:
        raise RuntimeError("CUDA failed with error out of memory")

    monkeypatch.setattr(diarization, "transcribe_audio", out_of_memory)

    assert runner.run(str(audio)) == 1
    assert "memoria della GPU esaurita" in capsys.readouterr().out
    assert not (tmp_path / "call - trascrizione.txt").exists()


def test_run_explains_a_file_without_readable_audio(tmp_path, monkeypatch, capsys, fake_pipeline):
    document = tmp_path / "Verbale.docx"
    document.write_bytes(b"x")

    def undecodable(path: str) -> None:
        raise RuntimeError(f"Failed to load input audio '{path}'.")

    monkeypatch.setattr(diarization, "load_audio", undecodable)

    assert runner.run(str(document)) == 1
    output = capsys.readouterr()
    assert "non riesco a leggere l'audio di 'Verbale.docx'" in output.out
    assert "Traceback" not in output.out + output.err
    assert fake_pipeline == []


def test_run_reports_a_missing_file(tmp_path, capsys):
    assert runner.run(str(tmp_path / "manca.m4a")) == 1
    assert "file non trovato" in capsys.readouterr().out
