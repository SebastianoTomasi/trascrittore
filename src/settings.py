"""
The transcriber's settings: the defaults that ship inside it, with the person's trascrittore.ini on top.

The person's file holds only what they changed, so every update brings new defaults for everything
else. A line the defaults do not know, or a value of the wrong kind, stops the run with a message that
names the line to correct.
"""

from __future__ import annotations

import configparser
import os
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# The container sets both; outside it the repository's defaults apply, and a person's file only when given.
DEFAULTS_ENV = "TRANSCRIBER_DEFAULTS"
SETTINGS_ENV = "TRANSCRIBER_SETTINGS"
DEFAULTS_PATH = PROJECT_ROOT / "docker" / "defaults.ini"

_BOOLEANS = {"true", "false", "yes", "no", "on", "off"}
_SECTION_RE = re.compile(r"\[(?P<name>.+)\]")
_DELIMITER_RE = re.compile(r"[=:]")


class SettingsError(RuntimeError):
    """The person's settings file has a line the transcriber cannot use; the message says which, in Italian."""


def _parser() -> configparser.ConfigParser:
    return configparser.ConfigParser(interpolation=None)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Notepad can save in the Windows code page, for example a prompt with accented names.
        return raw.decode("cp1252")


def _line_numbers(text: str) -> dict[tuple[str, str | None], int]:
    """
    Return the line of each section header, keyed (section, None), and of each setting, keyed (section, name).
    """
    lines: dict[tuple[str, str | None], int] = {}
    section = None
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        header = _SECTION_RE.fullmatch(stripped)
        if header:
            section = header.group("name")
            lines.setdefault((section, None), number)
        elif section is not None and _DELIMITER_RE.search(stripped):
            name = _DELIMITER_RE.split(stripped, maxsplit=1)[0].strip().lower()
            lines.setdefault((section, name), number)
    return lines


def _kind(default: str) -> str | None:
    value = default.strip()
    if not value:
        return None
    if value.lower() in _BOOLEANS:
        return "bool"
    for kind, convert in (("int", int), ("float", float)):
        try:
            convert(value)
            return kind
        except ValueError:
            pass
    return None


def _value_problem(value: str, default: str) -> str | None:
    kind = _kind(default)
    value = value.strip()
    if kind == "bool" and value.lower() not in _BOOLEANS | {"1", "0"}:
        return "deve essere true oppure false."
    if kind == "int":
        try:
            int(value)
        except ValueError:
            return f"deve essere un numero intero, per esempio {default.strip()}."
    if kind == "float":
        try:
            float(value)
        except ValueError:
            return f"deve essere un numero con il punto, non con la virgola, per esempio {default.strip()}."
    return None


def _read_person_settings(path: Path) -> tuple[configparser.ConfigParser, dict[tuple[str, str | None], int]]:
    name = path.name
    try:
        text = _read_text(path)
    except OSError as exc:
        raise SettingsError(f"Non riesco a leggere {name}: {exc.strerror or exc}.") from exc
    parser = _parser()
    try:
        parser.read_string(text, source=name)
    except configparser.MissingSectionHeaderError as exc:
        raise SettingsError(
            f"{name}, riga {exc.lineno}: prima di questa riga manca la sezione, per esempio [whisper]."
        ) from exc
    except configparser.DuplicateSectionError as exc:
        raise SettingsError(f"{name}, riga {exc.lineno}: la sezione [{exc.section}] compare due volte.") from exc
    except configparser.DuplicateOptionError as exc:
        raise SettingsError(
            f"{name}, riga {exc.lineno}: {exc.option} compare due volte nella sezione [{exc.section}]."
        ) from exc
    except configparser.ParsingError as exc:
        line_number = exc.errors[0][0] if exc.errors else "?"
        raise SettingsError(f"{name}, riga {line_number}: scrivi l'impostazione nella forma nome = valore.") from exc
    return parser, _line_numbers(text)


def _check_person_settings(
    person: configparser.ConfigParser,
    lines: dict[tuple[str, str | None], int],
    defaults: configparser.ConfigParser,
    name: str,
) -> None:
    if person.defaults():
        raise SettingsError(f"{name}, riga {lines.get(('DEFAULT', None), '?')}: la sezione [DEFAULT] non esiste.")
    for section in person.sections():
        if not defaults.has_section(section):
            raise SettingsError(
                f"{name}, riga {lines.get((section, None), '?')}: la sezione [{section}] non esiste. "
                "Correggila o cancellala."
            )
        for key, value in person.items(section):
            line = lines.get((section, key), "?")
            if not defaults.has_option(section, key):
                raise SettingsError(
                    f"{name}, riga {line}: {key} non è un'impostazione della sezione [{section}]. "
                    "Correggila o cancellala."
                )
            problem = _value_problem(value, defaults.get(section, key))
            if problem:
                raise SettingsError(f"{name}, riga {line}: {key} {problem}")


def load_settings(
    defaults_path: str | os.PathLike[str] | None = None,
    settings_path: str | os.PathLike[str] | None = None,
) -> configparser.ConfigParser:
    """
    Return the defaults with the person's settings on top.

    Without arguments the paths come from TRANSCRIBER_DEFAULTS and TRANSCRIBER_SETTINGS; without
    TRANSCRIBER_SETTINGS only the defaults apply.
    """
    defaults_file = Path(defaults_path or os.getenv(DEFAULTS_ENV) or DEFAULTS_PATH)
    settings_value = settings_path if settings_path is not None else os.getenv(SETTINGS_ENV, "").strip()

    settings = _parser()
    if not settings.read(defaults_file, encoding="utf-8"):
        raise RuntimeError(f"Default settings not found: {defaults_file}")
    if not settings_value:
        return settings

    settings_file = Path(settings_value)
    if not settings_file.is_file():
        raise SettingsError(f"Non trovo il file delle impostazioni {settings_file}.")
    person, lines = _read_person_settings(settings_file)
    _check_person_settings(person, lines, settings, settings_file.name)
    for section in person.sections():
        for key, value in person.items(section):
            settings.set(section, key, value)
    return settings
