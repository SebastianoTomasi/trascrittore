"""
Download every model the transcriber needs into the image at build time.

Runs on CPU with the same library calls the pipeline uses at runtime, so the
caches under HF_HOME, TORCH_HOME and NLTK_DATA match what it looks up later
with HF_HUB_OFFLINE=1. Model ids must match docker/defaults.ini.
"""

from __future__ import annotations

import os

import nltk
import whisperx
from pyannote.audio import Model
from whisperx.diarize import DiarizationPipeline


WHISPER_MODEL_ID = "large-v3"
ALIGN_LANGUAGE = "it"
VOICEPRINT_MODEL_ID = "pyannote/embedding"


def main() -> None:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("HF_TOKEN is empty: pass it with --secret id=hf_token.")

    print(f"Downloading Whisper {WHISPER_MODEL_ID}", flush=True)
    whisperx.load_model(WHISPER_MODEL_ID, "cpu", compute_type="int8", language=ALIGN_LANGUAGE, vad_method="pyannote")

    print(f"Downloading alignment model for '{ALIGN_LANGUAGE}'", flush=True)
    whisperx.load_align_model(ALIGN_LANGUAGE, device="cpu")

    print("Downloading diarization pipeline", flush=True)
    DiarizationPipeline(token=token, device="cpu")

    print(f"Downloading speaker voiceprint model {VOICEPRINT_MODEL_ID}", flush=True)
    Model.from_pretrained(VOICEPRINT_MODEL_ID, token=token)

    print("Downloading NLTK punkt_tab", flush=True)
    if not nltk.download("punkt_tab", download_dir=os.environ["NLTK_DATA"], quiet=True):
        raise SystemExit("NLTK punkt_tab download failed.")


if __name__ == "__main__":
    main()
