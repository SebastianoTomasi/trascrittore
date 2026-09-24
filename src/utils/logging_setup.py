from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import logging
import os
import time
import warnings


APP_LOGGER_NAME = "meeting"
_orig_showwarning = warnings.showwarning


def _showwarning(message, category, filename, lineno, file=None, line=None):
    """
    Filter known third-party warning noise while preserving all actionable warnings.
    """
    msg = str(message)

    if category is UserWarning and "torchcodec is not installed correctly" in msg:
        return
    if category.__name__ == "ReproducibilityWarning" and "TensorFloat-32 (TF32) has been disabled" in msg:
        return
    if category is UserWarning and "std(): degrees of freedom is <= 0" in msg:
        return
    if category is UserWarning and "task-dependent loss function" in msg and "strict" in msg:
        return

    return _orig_showwarning(message, category, filename, lineno, file, line)


def configure_warnings() -> None:
    """
    Install warning filters and custom warning handler for noisy ML dependencies.
    """
    warnings.simplefilter("ignore")
    warnings.filterwarnings("ignore", message=".*torchcodec.*", category=UserWarning)
    warnings.filterwarnings("ignore", module="pyannote.audio.core.io", category=UserWarning)
    warnings.showwarning = _showwarning  # type: ignore[assignment]


def format_duration(seconds: float) -> str:
    """
    Format a duration for human-readable pipeline and API logs.
    """
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if h or m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def _format_fields(fields: dict[str, object]) -> str:
    clean_fields = {
        key: value
        for key, value in fields.items()
        if value is not None and value != ""
    }
    if not clean_fields:
        return ""
    return " " + " ".join(f"{key}={value}" for key, value in clean_fields.items())


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure application and third-party loggers for concise console output.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)

    logging.getLogger(APP_LOGGER_NAME).setLevel(level)

    # WhisperX installs its own INFO stdout handler on first use unless the logger already has one.
    whisperx_logger = logging.getLogger("whisperx")
    if not whisperx_logger.handlers:
        whisperx_logger.addHandler(logging.NullHandler())
    whisperx_logger.setLevel(logging.WARNING)
    logging.getLogger("whisperx.asr").setLevel(logging.WARNING)
    logging.getLogger("whisperx.diarize").setLevel(logging.WARNING)

    logging.getLogger("lightning").setLevel(logging.ERROR)
    logging.getLogger("lightning.pytorch").setLevel(logging.ERROR)
    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    logging.getLogger("lightning.pytorch.utilities.migration").setLevel(logging.ERROR)
    logging.getLogger("pyannote").setLevel(logging.ERROR)
    logging.getLogger("pyannote.audio").setLevel(logging.ERROR)
    logging.getLogger("speechbrain").setLevel(logging.ERROR)
    logging.getLogger("transformers").setLevel(logging.ERROR)
    logging.getLogger("torch").setLevel(logging.ERROR)
    logging.getLogger("torchaudio").setLevel(logging.ERROR)

    os.environ.setdefault("LIGHTNING_LOG_LEVEL", "error")
    os.environ.setdefault("PYTHONWARNINGS", "ignore")


def init_logging(level: int = logging.INFO) -> None:
    """
    Initialize warning and logger configuration at application startup.
    """
    configure_warnings()
    configure_logging(level=level)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return the named logger, defaulting to the application logger namespace.
    """
    if not name:
        return logging.getLogger(APP_LOGGER_NAME)
    if name == APP_LOGGER_NAME or name.startswith(f"{APP_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")


def log_event(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: object) -> None:
    """
    Log a structured, single-line event with key=value metadata.
    """
    logger.log(level, "%s%s", event, _format_fields(fields))


@contextmanager
def log_phase(
    logger: logging.Logger,
    phase: str,
    *,
    level: int = logging.INFO,
    start_level: int = logging.DEBUG,
    **fields: object,
) -> Iterator[None]:
    """
    Log start, success, failure, and elapsed time for a pipeline/API phase.
    """
    started_at = time.perf_counter()
    log_event(logger, f"{phase} started", level=start_level, **fields)
    try:
        yield
    except Exception:
        duration = format_duration(time.perf_counter() - started_at)
        logger.exception("%s failed%s", phase, _format_fields({**fields, "duration": duration}))
        raise
    duration = format_duration(time.perf_counter() - started_at)
    log_event(logger, f"{phase} completed", level=level, **fields, duration=duration)


def log_info(msg: str, *args, **kwargs) -> None:
    """
    Log an info message through the application logger.
    """
    get_logger().info(msg, *args, **kwargs)


def log_warning(msg: str, *args, **kwargs) -> None:
    """
    Log a warning message through the application logger.
    """
    get_logger().warning(msg, *args, **kwargs)


def log_error(msg: str, *args, **kwargs) -> None:
    """
    Log an error message through the application logger.
    """
    get_logger().error(msg, *args, **kwargs)
