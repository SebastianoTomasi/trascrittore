import os


# src.asr.utils.config reads the settings at import time; the tests use the defaults alone,
# whatever trascrittore.ini a developer points at for local runs.
os.environ.pop("TRANSCRIBER_DEFAULTS", None)
os.environ.pop("TRANSCRIBER_SETTINGS", None)
