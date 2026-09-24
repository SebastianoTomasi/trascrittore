from __future__ import annotations

import os
from typing import Any, List

import numpy as np
import torch
from pyannote.core import Segment

from src.asr.utils.config import get_embedding_settings, get_vad_settings


_embedding_settings = get_embedding_settings()
_vad_settings = get_vad_settings()

EMBEDDING_MODEL_ID = _embedding_settings.model_id
SAMPLE_RATE_DEFAULT = _embedding_settings.sample_rate
MIN_DURATION_SEC_DEFAULT = _vad_settings.min_duration_sec


def normalize_embed(emb: np.ndarray) -> np.ndarray:
    """
    Return a float32 L2-normalized copy of an embedding vector.
    """
    emb = emb.astype(np.float32, copy=False)
    return emb / (np.linalg.norm(emb) + 1e-9)


def mean_embed(embeds: List[np.ndarray]) -> np.ndarray:
    """
    Return the centroid (element-wise mean) of a non-empty embedding list.
    """
    if not embeds:
        raise ValueError("Cannot compute mean embedding from an empty list.")
    return np.mean(np.stack(embeds, axis=0), axis=0)


def load_embedding_model(device: str) -> Any:
    """
    Load and prepare the speaker embedding model on the requested device.
    """
    # Import lazily so logging/warning setup can run before pyannote loads.
    from pyannote.audio import Model

    # PyTorch lets cuDNN use TF32 by default, and pyannote turns it off only while its diarization
    # pipeline runs. Force full FP32 so voiceprints and scores do not depend on what ran earlier.
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False

    token = os.getenv("HF_TOKEN")
    model = Model.from_pretrained(EMBEDDING_MODEL_ID, token=token)
    model.to(torch.device(device))
    model.eval()
    return model


def embed_audio_waveform(
    model,
    audio: np.ndarray,
    device: str,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
    crop: Segment | None = None,
    min_duration_sec: float = MIN_DURATION_SEC_DEFAULT,
) -> np.ndarray:
    """
    Extract a speaker embedding from a full waveform or an optional cropped segment.
    """
    if crop is not None:
        start_i = max(0, int(round(crop.start * sample_rate)))
        end_i = min(len(audio), int(round(crop.end * sample_rate)))
        if end_i <= start_i:
            # Recover from tiny/degenerate segments by taking a short fallback window.
            end_i = min(len(audio), start_i + sample_rate // 10)
        audio = audio[start_i:end_i]

    min_len = int(round(min_duration_sec * sample_rate))
    if len(audio) == 0:
        raise ValueError("Empty audio passed to embedding.")
    if len(audio) < min_len:
        audio = np.pad(
            audio.astype(np.float32, copy=False),
            (0, min_len - len(audio)),
            mode="constant",
        )

    x = torch.from_numpy(audio.astype(np.float32, copy=False)).unsqueeze(0).unsqueeze(0)  # (1, 1, T)
    with torch.inference_mode():
        x = x.to(torch.device(device))
        emb = model(x).squeeze().detach().cpu().numpy()
    return emb

