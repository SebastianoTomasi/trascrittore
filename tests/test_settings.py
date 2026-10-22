import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.settings import DEFAULTS_PATH, SettingsError, load_settings


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path, text: str, encoding: str = "utf-8"):
    path = tmp_path / "trascrittore.ini"
    path.write_bytes(text.encode(encoding))
    return load_settings(DEFAULTS_PATH, path)


def test_without_a_settings_file_only_the_defaults_apply():
    settings = load_settings(DEFAULTS_PATH, "")

    assert settings["whisper"]["batch_size"] == "8"
    assert settings["whisper"]["initial_prompt"] == "Registrazione in italiano."


def test_the_persons_lines_replace_only_those_defaults(tmp_path):
    settings = _settings(tmp_path, "; Solo quello che cambio.\n[whisper]\nbatch_size = 4\n")

    assert settings["whisper"]["batch_size"] == "4"
    assert settings["whisper"]["model_id"] == "large-v3"
    assert settings["matching"]["threshold"] == "0.575"


def test_a_file_saved_by_notepad_in_the_windows_code_page_is_read(tmp_path):
    settings = _settings(tmp_path, "[whisper]\ninitial_prompt = Registrazione con Niccolò.\n", encoding="cp1252")

    assert settings["whisper"]["initial_prompt"] == "Registrazione con Niccolò."


def test_a_byte_order_mark_is_ignored(tmp_path):
    settings = _settings(tmp_path, "﻿[whisper]\nbatch_size = 2\n")

    assert settings["whisper"]["batch_size"] == "2"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[whisperx]\nbatch_size = 4\n", "trascrittore.ini, riga 1: la sezione [whisperx] non esiste."),
        (
            "[whisper]\n\nbatchsize = 4\n",
            "trascrittore.ini, riga 3: batchsize non è un'impostazione della sezione [whisper].",
        ),
        ("[matching]\nthreshold = 0,6\n", "trascrittore.ini, riga 2: threshold deve essere un numero con il punto"),
        ("[whisper]\nbatch_size = quattro\n", "trascrittore.ini, riga 2: batch_size deve essere un numero intero, per esempio 8."),
        ("[matching]\nsave_window_clips = forse\n", "trascrittore.ini, riga 2: save_window_clips deve essere true oppure false."),
        ("batch_size = 4\n", "trascrittore.ini, riga 1: prima di questa riga manca la sezione"),
        ("[whisper]\nbatch_size\n", "trascrittore.ini, riga 2: scrivi l'impostazione nella forma nome = valore."),
        ("[whisper]\nbatch_size = 4\nbatch_size = 2\n", "trascrittore.ini, riga 3: batch_size compare due volte"),
    ],
)
def test_a_line_the_transcriber_does_not_understand_is_named(tmp_path, text, expected):
    with pytest.raises(SettingsError) as raised:
        _settings(tmp_path, text)

    assert str(raised.value).startswith(expected)


def test_a_command_stops_with_the_line_to_correct(tmp_path):
    settings = tmp_path / "trascrittore.ini"
    settings.write_text("[whisper]\nbatchsize = 4\n", encoding="utf-8")
    env = {**os.environ, "TRANSCRIBER_SETTINGS": str(settings), "PYTHONIOENCODING": "utf-8"}
    env.pop("TRANSCRIBER_DEFAULTS", None)

    completed = subprocess.run(
        [sys.executable, "-m", "src.transcriber", "remove-clips", "Luca Bianchi", "a.wav"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

    summary = json.loads(completed.stdout.strip().splitlines()[-1])
    assert completed.returncode == 1
    assert summary["status"] == "invalid_settings"
    assert summary["message"].startswith("trascrittore.ini, riga 2: batchsize")
