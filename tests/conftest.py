import os
from pathlib import Path


# src.asr.utils.config reads its INI at import time; the tests use the container defaults.
os.environ["MEETING_CONFIG"] = str(Path(__file__).resolve().parents[1] / "docker" / "meeting.ini")
