"""
Voiceprints of stretches of a recording, or of whole voice clips, for naming and for the recognition check.

They run on the CPU: a transcription may be using the GPU at the same time, and a few dozen
10-second stretches take seconds there.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from src.asr.utils.config import get_matching_settings


DEVICE = "cpu"
SAMPLE_RATE = 16000


def load_recording(path: str | os.PathLike[str]) -> np.ndarray:
    """
    Decode a recording or a clip to 16 kHz mono, as the transcription does.
    """
    import whisperx

    try:
        return whisperx.load_audio(str(path))
    except Exception as exc:  # pragma: no cover - depends on ffmpeg errors
        raise RuntimeError(f"Failed to load audio '{path}'.") from exc


class Voiceprints:
    """
    Embed windows and clips with the model recognition uses, loading it on first use.
    """

    def __init__(self) -> None:
        self._model: Any = None

    def _loaded_model(self) -> Any:
        if self._model is None:
            from src.asr.embeddings import load_embedding_model

            self._model = load_embedding_model(DEVICE)
        return self._model

    def of_windows(self, audio: np.ndarray, windows: list[dict[str, float]]) -> list[np.ndarray | None]:
        """
        Return one normalized voiceprint per window, or None where the window cannot be embedded.
        """
        from pyannote.core import Segment

        from src.asr.embeddings import embed_audio_waveform, normalize_embed

        model = self._loaded_model()
        min_window_sec = get_matching_settings().min_window_sec
        voiceprints: list[np.ndarray | None] = []
        for window in windows:
            try:
                voiceprints.append(
                    normalize_embed(
                        embed_audio_waveform(
                            model,
                            audio,
                            device=DEVICE,
                            crop=Segment(float(window["start"]), float(window["end"])),
                            min_duration_sec=min_window_sec,
                        )
                    )
                )
            except (RuntimeError, ValueError):
                voiceprints.append(None)
        return voiceprints

    def of_clip(self, path: str | os.PathLike[str]) -> np.ndarray:
        from src.asr.embeddings import embed_audio_waveform, normalize_embed

        return normalize_embed(embed_audio_waveform(self._loaded_model(), load_recording(path), device=DEVICE))


def cut(audio: np.ndarray, start: float, end: float) -> np.ndarray:
    """
    Return the samples between two times, in seconds from the start of the recording.
    """
    start_i = max(0, int(round(start * SAMPLE_RATE)))
    end_i = min(len(audio), int(round(end * SAMPLE_RATE)))
    return audio[start_i:end_i]
