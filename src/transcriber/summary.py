"""
What every command prints: lines for people on standard error, and one JSON result summary on standard output.

An agent reads the summary; a person reads the lines. Paths in the summary are the ones the person
sees on their PC, even when the command runs in the container.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable

from src.utils.logging_setup import get_logger


logger = get_logger("transcriber.summary")

# Set by the launcher: "/recording=C:\\Users\\...|/voci=C:\\...|", one container folder per mount.
HOST_PATHS_ENV = "TRANSCRIBER_HOST_PATHS"

OK = "ok"
INVALID_ARGUMENTS = "invalid_arguments"
INVALID_SETTINGS = "invalid_settings"
FILE_NOT_FOUND = "file_not_found"
UNREADABLE_RECORDING = "unreadable_recording"
GPU_OUT_OF_MEMORY = "gpu_out_of_memory"
INTERRUPTED = "interrupted"
FAILED = "error"

# Every other status, such as the launcher's docker_not_running, exits with 1.
_EXIT_CODES = {OK: 0, INVALID_ARGUMENTS: 2, "busy": 3, INTERRUPTED: 130}


class CommandError(Exception):
    """A problem the person can act on, reported with a status and an Italian message."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def say(message: str = "") -> None:
    print(message, file=sys.stderr, flush=True)


def exit_code(status: str) -> int:
    return _EXIT_CODES.get(status, 1)


def emit(summary: dict[str, Any]) -> int:
    """
    Print the result summary as one line of ASCII JSON and return the process exit code.
    """
    print(json.dumps(summary, ensure_ascii=True), flush=True)
    return exit_code(summary["status"])


def failure(command: str, status: str, message: str) -> dict[str, Any]:
    return {"command": command, "status": status, "message": message}


def guarded(command: str, body: Callable[[], dict[str, Any]], *, failed: str) -> dict[str, Any]:
    """
    Run a command and return its summary; a failure still ends with a summary that states its kind.

    `failed` opens the message of an unexpected error, for example "La trascrizione non è riuscita".
    """
    try:
        return body()
    except CommandError as exc:
        say(f"\nErrore: {exc.message}")
        return failure(command, exc.status, exc.message)
    except KeyboardInterrupt:
        say("\nInterrotto.")
        return failure(command, INTERRUPTED, "Interrotto.")
    except Exception as exc:
        logger.exception("Command %s failed", command)
        message = f"{failed} ({type(exc).__name__}: {exc})."
        say(f"\nErrore: {message}")
        return failure(command, FAILED, message)


def _mounts() -> list[tuple[str, str]]:
    mounts = []
    for entry in os.getenv(HOST_PATHS_ENV, "").split("|"):
        container, separator, host = entry.partition("=")
        if separator and container and host:
            mounts.append((container.rstrip("/"), host.rstrip("\\")))
    # The longest container folder wins, so /voci/x is not read as /voci.
    return sorted(mounts, key=lambda mount: len(mount[0]), reverse=True)


def host_path(path: str | os.PathLike[str]) -> str:
    """
    Return the path the person sees on their PC for a path inside the container.

    Outside the container, or outside every mount, the path only becomes absolute.
    """
    value = str(path).replace("\\", "/")
    for container, host in _mounts():
        if value == container or value.startswith(container + "/"):
            rest = value[len(container):].strip("/")
            return host + ("\\" + rest.replace("/", "\\") if rest else "")
    return os.path.abspath(str(path))

