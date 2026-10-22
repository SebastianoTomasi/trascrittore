from __future__ import annotations

import json

import pytest

from src.transcriber import cli, library, naming, recognition_check, runner


def _last_json(stdout: str) -> dict[str, object]:
    lines = stdout.strip().splitlines()
    assert len(lines) == 1, "standard output carries only the result summary"
    return json.loads(lines[0])


def test_transcribe_passes_its_arguments_and_prints_the_summary(monkeypatch, capsys):
    calls = []

    def fake_run(audio, *, speakers, out_dir):
        calls.append((audio, speakers, out_dir))
        return {"command": "transcribe", "status": "ok", "message": "Trascrizione completata in 1m 2s."}

    monkeypatch.setattr(runner, "run", fake_run)

    assert cli.main(["transcribe", "Registrazione.m4a", "--speakers", "3", "--out-dir", "/out"]) == 0
    assert calls == [("Registrazione.m4a", 3, "/out")]
    assert _last_json(capsys.readouterr().out)["status"] == "ok"


@pytest.mark.parametrize(
    "argv",
    [
        ["transcribe", "Registrazione.m4a", "--speakers", "0"],
        ["transcribe", "Registrazione.m4a", "--ask-names"],
        ["transcribe"],
        ["listen", "Registrazione - trascrizione.json"],
        ["listen", "Registrazione - trascrizione.json", "Persona 1", "--clip", "0"],
        ["listen", "Registrazione - trascrizione.json", "Persona 1", "Persona 2"],
        ["remove-clips", "Luca Bianchi"],
        ["rinomina"],
        [],
    ],
)
def test_invalid_arguments_still_end_with_a_summary(argv, capsys):
    assert cli.main(argv) == 2

    output = capsys.readouterr()
    summary = _last_json(output.out)
    assert summary["status"] == "invalid_arguments"
    assert "usage:" in output.err


def test_name_passes_pairs_and_the_recording(monkeypatch, capsys):
    calls = []

    def fake_name(transcript, pairs, *, recording, confirm, correct, new_people):
        calls.append((transcript, pairs, recording, confirm, correct, new_people))
        return {"command": "name", "status": "invalid_arguments", "message": "x"}

    monkeypatch.setattr(naming, "name_speakers", fake_name)

    assert cli.main(["name", "t.json", "Persona 1=Luca Bianchi", "Persona 2=Anna Neri", "--recording", "r.m4a"]) == 2
    assert cli.main(
        ["name", "t.json", "Mario Rossi=Luca Bianchi", "--correct", "--confirm", "Anna Neri", "--new-person", "Luca Bianchi"]
    ) == 2
    assert calls == [
        ("t.json", ["Persona 1=Luca Bianchi", "Persona 2=Anna Neri"], "r.m4a", [], False, []),
        ("t.json", ["Mario Rossi=Luca Bianchi"], None, ["Anna Neri"], True, ["Luca Bianchi"]),
    ]


def test_listen_check_and_trial_reach_their_commands(monkeypatch, capsys):
    calls = []
    ok = {"status": "ok", "message": ""}
    monkeypatch.setattr(
        naming,
        "prepare_listening",
        lambda transcript, label, *, recording, out_dir, clip: calls.append(("listen", transcript, label, out_dir, clip))
        or ok,
    )
    monkeypatch.setattr(
        library, "remove_clips_report", lambda person, clips, selection: calls.append(("remove", person, clips)) or ok
    )
    monkeypatch.setattr(
        recognition_check, "run_check", lambda pairs, *, missing: calls.append(("check", pairs, missing)) or ok
    )
    monkeypatch.setattr(library, "trial_report", lambda selection, *, reviewed: calls.append(("trial", reviewed)) or ok)

    assert cli.main(["listen", "t.json", "Persona 1", "--out-dir", "/ascolto"]) == 0
    assert cli.main(["listen", "t.json", "Mario Rossi", "--clip", "2"]) == 0
    assert cli.main(["remove-clips", "Luca Bianchi", "a.wav", "b.wav"]) == 0
    assert cli.main(["check", "--pair", "a.json", "a.m4a", "--missing", r"C:\b.json"]) == 0
    assert cli.main(["check", "--missing", r"C:\b.json"]) == 0
    assert cli.main(["check"]) == 0
    assert cli.main(["trial"]) == 0
    assert cli.main(["trial", "--reviewed"]) == 0
    assert calls == [
        ("listen", "t.json", "Persona 1", "/ascolto", 1),
        ("listen", "t.json", "Mario Rossi", None, 2),
        ("remove", "Luca Bianchi", ["a.wav", "b.wav"]),
        ("check", [("a.json", "a.m4a")], [r"C:\b.json"]),
        # Only a check given nothing looks for transcripts itself.
        ("check", [], [r"C:\b.json"]),
        ("check", None, []),
        ("trial", False),
        ("trial", True),
    ]


def test_a_command_that_breaks_still_ends_with_a_summary(monkeypatch, capsys):
    import src.asr.utils.config as config

    def broken_settings():
        raise RuntimeError("library.keep_clips must be greater than zero.")

    monkeypatch.setattr(config, "get_library_settings", broken_settings)

    assert cli.main(["trial"]) == 1
    summary = _last_json(capsys.readouterr().out)
    assert summary["status"] == "error"
    assert "keep_clips" in summary["message"]
