from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import src.asr.diarization as diarization
import src.transcriber.runner as runner
from src.asr.utils.config import SpeakerSettings, WhisperSettings
from src.paths import slug
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
# Stretches of speech whisperX could not align word by word.
UNALIGNED: list[dict[str, float]] = []

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
        warnings=[],
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
        warnings=[],
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
        warnings=["Elaborata su CPU invece che su GPU. Nessuna GPU NVIDIA disponibile."],
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
        unaligned=[],
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
        unaligned=[],
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


def test_build_payload_warns_about_speech_that_could_not_be_aligned():
    labels = display_labels(TURNS, "ANONYMOUS_")

    payload = build_payload(
        source_name="a.wav",
        recording="C:\\Registrazioni\\a.wav",
        duration_sec=95.0,
        device="cuda",
        compute_type="float16",
        fallback_reason=None,
        unaligned=[{"start_sec": 66.0, "end_sec": 80.5}, {"start_sec": 3725.0, "end_sec": 3731.0}],
        elapsed_sec=30.0,
        turns=TURNS,
        labels=labels,
        speakers=speaker_summaries(TURNS, labels, DIAGNOSTICS),
    )

    warning = (
        "In alcuni tratti il parlato non si è potuto allineare parola per parola, "
        "e orari e chi parla sono approssimativi: 00:01:06–00:01:20, 01:02:05–01:02:11."
    )
    assert payload["warnings"] == [warning]
    assert f"ATTENZIONE: i{warning[1:]}" in render_payload_text(payload).splitlines()


def test_rename_speakers_changes_only_the_named_labels():
    payload = _payload()

    renamed = rename_speakers(payload, {"Persona 1": "Luca Bianchi"})

    assert speaker_labels(renamed) == ["Mario Rossi", "Luca Bianchi", "Persona 2"]
    assert [turn["speaker"] for turn in renamed["turns"]] == ["Mario Rossi", "Luca Bianchi", "Mario Rossi", "Persona 2"]
    assert renamed["speakers"][1]["windows"] == payload["speakers"][1]["windows"]
    assert [turn["segments"] for turn in renamed["turns"]] == [turn["segments"] for turn in payload["turns"]]
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


@pytest.mark.parametrize(
    ("name", "written"),
    [
        ("2026-10-29 14-30-12", "2026-10-29-14-30-12"),
        ("Riunione Più Lunga è", "riunione-piu-lunga-e"),
        ("  Call   (Acme) – finale!! ", "call-acme-finale"),
        ("2026-10-29-demo-prodotto-acme", "2026-10-29-demo-prodotto-acme"),
        ("???", "registrazione"),
    ],
)
def test_names_the_transcriber_creates_have_no_spaces(name, written):
    assert slug(name) == written


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
        transcript_path.write_text(json.dumps({"date": None, "turns": TURNS, "unaligned": UNALIGNED}), encoding="utf-8")
        diagnostics_path.write_text(json.dumps(DIAGNOSTICS), encoding="utf-8")
        return "recognized.json", str(transcript_path), str(diagnostics_path)

    monkeypatch.setattr(diarization, "recognize_speakers", fake_recognize)
    monkeypatch.setattr(runner, "get_whisper_settings", _cpu_settings)
    monkeypatch.setattr(runner, "get_speaker_settings", lambda: SpeakerSettings(anonymous_prefix="ANONYMOUS_"))
    return calls


def test_run_writes_the_transcript_in_its_folder_and_moves_the_recording(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "Registrazione di prova è.M4A"
    audio.write_bytes(b"not decoded: load_audio is faked")
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("transcribing asks nothing"))

    summary = runner.run(str(audio), speakers=3)

    assert fake_pipeline == [("transcribe", ".wav"), "align", ("diarize", 3), "recognize"]
    folder = tmp_path / "registrazione-di-prova-e"
    moved = folder / "registrazione-di-prova-e.m4a"
    txt_path = folder / "registrazione-di-prova-e-trascrizione.txt"
    json_path = folder / "registrazione-di-prova-e-trascrizione.json"
    assert not audio.exists() and moved.read_bytes() == b"not decoded: load_audio is faked"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["artifacts", "registrazione-di-prova-e"]
    text = txt_path.read_text(encoding="utf-8")
    assert "[00:01:06] Persona 1: io direi di rimandare" in text
    assert "ATTENZIONE: elaborata su CPU" in text
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert (payload["recording"], payload["file"]) == (str(moved), "registrazione-di-prova-e.m4a")
    assert payload["warnings"] and payload["device"] == "cpu"
    assert payload["speakers"][1]["windows"] == [{"start": 66.0, "end": 76.0}, {"start": 76.123, "end": 79.5}]
    assert text == render_payload_text(payload)
    assert payload["turns"][1]["segments"] == [{"start_sec": 66.0, "end_sec": 80.0, "text": "io direi di rimandare"}]

    assert summary["status"] == "ok"
    assert summary["message"].endswith("Senza nome: Persona 1, Persona 2.")
    assert (summary["transcript_txt"], summary["transcript_json"]) == (str(txt_path), str(json_path))
    assert (summary["folder"], summary["recording"], summary["recording_moved"]) == (str(folder), str(moved), True)
    assert summary["warnings"] == payload["warnings"]
    assert summary["speakers"] == [
        {"label": "Mario Rossi", "recognized": True, "speech_sec": 71.0},
        {"label": "Persona 1", "recognized": False, "speech_sec": 14.0},
        {"label": "Persona 2", "recognized": False, "speech_sec": 4.0},
    ]
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.count("ATTENZIONE: nessuna GPU disponibile, elaboro su CPU") == 2


def test_run_ends_with_who_spoke_longest_first(tmp_path, capsys, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")

    summary = runner.run(str(audio))

    assert "Chi ha parlato: Mario Rossi (1 min), Persona 1 (<1 min), Persona 2 (<1 min)." in summary["message"]
    lines = capsys.readouterr().err.splitlines()
    first = lines.index("Chi ha parlato:")
    assert lines[first + 1 : first + 4] == ["  - Mario Rossi: 1 min", "  - Persona 1: <1 min", "  - Persona 2: <1 min"]
    assert "Se un nome è sbagliato, trascina il file .json su Trascrivi.bat e correggilo." in lines


def test_run_warns_about_speech_that_could_not_be_aligned(tmp_path, monkeypatch, fake_pipeline):
    monkeypatch.setitem(globals(), "UNALIGNED", [{"start_sec": 66.0, "end_sec": 80.0}])
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")

    summary = runner.run(str(audio))

    payload = json.loads(Path(summary["transcript_json"]).read_text(encoding="utf-8"))
    assert payload["warnings"][1].endswith("orari e chi parla sono approssimativi: 00:01:06–00:01:20.")
    assert summary["warnings"] == payload["warnings"]
    assert Path(summary["transcript_txt"]).read_text(encoding="utf-8") == render_payload_text(payload)


def test_words_no_speaker_could_be_given_are_not_in_who_spoke(tmp_path, monkeypatch, capsys, fake_pipeline):
    monkeypatch.setitem(globals(), "TURNS", TURNS + [_turn("UNATTRIBUTED", 90.0, 94.0, "mh")])
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")

    summary = runner.run(str(audio))

    assert "Voce non attribuita" not in summary["message"]
    lines = capsys.readouterr().err.splitlines()
    first = lines.index("Chi ha parlato:")
    assert lines[first + 4] != "  - Voce non attribuita: <1 min"
    assert not any("Voce non attribuita" in line for line in lines)


def test_run_again_inside_the_transcripts_folder_writes_there(tmp_path, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    first = runner.run(str(audio))

    again = runner.run(first["recording"])

    folder = tmp_path / "call"
    assert (again["folder"], again["recording"], again["recording_moved"]) == (str(folder), str(folder / "call.mp4"), False)
    assert sorted(path.name for path in folder.iterdir()) == ["call-trascrizione.json", "call-trascrizione.txt", "call.mp4"]


@pytest.mark.parametrize(
    ("folder_on_the_pc", "recording", "written_in"),
    [
        # A recording called like the container's mount still gets a folder of its own.
        ("Registrazioni", "Recording.mp4", "recording"),
        # A recording in a folder of its name, without a transcript, is transcribed there.
        ("call", "call.mp4", "."),
    ],
)
def test_run_judges_the_folder_by_its_name_on_the_pc(tmp_path, monkeypatch, fake_pipeline, folder_on_the_pc, recording, written_in):
    mount = tmp_path / "recording"
    mount.mkdir()
    (mount / recording).write_bytes(b"x")
    monkeypatch.setenv("TRANSCRIBER_HOST_PATHS", f"{mount.as_posix()}=C:\\Utenti\\{folder_on_the_pc}|")

    runner.run(str(mount / recording))

    assert (mount / written_in / f"{Path(recording).stem.lower()}-trascrizione.json").is_file()


def test_run_keeps_the_transcript_of_a_recording_deleted_from_its_folder(tmp_path, fake_pipeline):
    (tmp_path / "call.mp4").write_bytes(b"first")
    runner.run(str(tmp_path / "call.mp4"))
    (tmp_path / "call" / "call.mp4").unlink()
    (tmp_path / "call.mp4").write_bytes(b"second")

    summary = runner.run(str(tmp_path / "call.mp4"))

    assert summary["recording"] == str(tmp_path / "call-2" / "call-2.mp4")
    assert sorted(path.name for path in (tmp_path / "call").iterdir()) == ["call-trascrizione.json", "call-trascrizione.txt"]


def test_run_again_after_a_failed_move_writes_in_the_same_folder(tmp_path, monkeypatch, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    with monkeypatch.context() as busy:
        busy.setattr(runner.os, "rename", _busy)
        runner.run(str(audio))

    summary = runner.run(str(audio))

    assert summary["recording"] == str(tmp_path / "call" / "call.mp4") and summary["recording_moved"] is True
    assert sorted(path.name for path in tmp_path.iterdir()) == ["artifacts", "call"]


def test_run_again_says_the_recording_is_already_in_its_folder(tmp_path, capsys, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    first = runner.run(str(audio))
    capsys.readouterr()

    runner.run(first["recording"])

    assert "La registrazione è già nella cartella." in capsys.readouterr().err


def test_run_again_in_a_folder_the_agent_renamed_writes_there(tmp_path, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    runner.run(str(audio))
    renamed = tmp_path / "2026-10-29-demo-prodotto-acme"
    (tmp_path / "call").rename(renamed)

    again = runner.run(str(renamed / "call.mp4"))

    assert again["transcript_json"] == str(renamed / "call-trascrizione.json")
    assert sorted(path.name for path in tmp_path.iterdir()) == ["2026-10-29-demo-prodotto-acme", "artifacts"]


def test_run_keeps_apart_two_recordings_with_the_same_name(tmp_path, fake_pipeline):
    (tmp_path / "Call.mp4").write_bytes(b"first")
    runner.run(str(tmp_path / "Call.mp4"))
    (tmp_path / "call.mkv").write_bytes(b"second")

    summary = runner.run(str(tmp_path / "call.mkv"))

    assert summary["recording"] == str(tmp_path / "call-2" / "call-2.mkv")
    assert (tmp_path / "call" / "call.mp4").read_bytes() == b"first"


def _busy(_source, _destination):
    raise PermissionError(13, "Permission denied")


def test_run_says_when_the_recording_could_not_move(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    monkeypatch.setattr(runner.os, "rename", _busy)

    summary = runner.run(str(audio))

    assert summary["status"] == "ok" and summary["recording_moved"] is False
    assert audio.exists() and summary["recording"] == str(audio)
    # No copy is left behind: the recording is either moved or where it was.
    assert sorted(path.name for path in (tmp_path / "call").iterdir()) == ["call-trascrizione.json", "call-trascrizione.txt"]
    payload = json.loads((tmp_path / "call" / "call-trascrizione.json").read_text(encoding="utf-8"))
    assert payload["recording"] == str(audio)
    stayed = "La registrazione è rimasta dov'era: non ho potuto spostarla nella cartella (forse è aperta in un altro programma)."
    assert summary["message"].endswith(stayed)
    assert stayed in capsys.readouterr().err


def test_run_reports_paths_as_the_person_sees_them(tmp_path, monkeypatch, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    monkeypatch.setenv("TRANSCRIBER_HOST_PATHS", f"{tmp_path.as_posix()}=C:\\Registrazioni|")

    summary = runner.run(str(audio))

    assert summary["transcript_json"] == "C:\\Registrazioni\\call\\call-trascrizione.json"
    assert summary["recording"] == "C:\\Registrazioni\\call\\call.mp4"


def test_run_writes_the_folder_in_the_output_folder_and_leaves_the_recording(tmp_path, monkeypatch, capsys, fake_pipeline):
    audio = tmp_path / "call.mp4"
    audio.write_bytes(b"x")
    out_dir = tmp_path / "uscita"
    out_dir.mkdir()
    monkeypatch.setenv("TRANSCRIBER_HOST_PATHS", f"{out_dir.as_posix()}=C:\\Trascrizioni|")

    summary = runner.run(str(audio), out_dir=str(out_dir))

    assert audio.exists() and summary["recording_moved"] is False
    assert (out_dir / "call" / "call-trascrizione.json").is_file()
    err = capsys.readouterr().err
    assert "Nella cartella C:\\Trascrizioni\\call trovi 'call-trascrizione.txt' e 'call-trascrizione.json'." in err
    assert "La registrazione è rimasta dov'era." in err


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
    assert sorted(path.name for path in tmp_path.iterdir()) == ["call.wav"]


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
