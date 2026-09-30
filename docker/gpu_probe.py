"""Exercise PyTorch/cuDNN and CTranslate2 CUDA kernels before an image is activated."""

from __future__ import annotations

import sys

import numpy as np
import torch
from faster_whisper import WhisperModel

from src.asr.utils.device import probe_cuda, resolve_device


def main() -> None:
    ok, reason = probe_cuda()
    if not ok:
        raise RuntimeError(f"PyTorch/cuDNN: {reason}")

    import ctranslate2

    types = ctranslate2.get_supported_compute_types("cuda")
    choice = resolve_device("cuda", "auto", cuda_available=True, supported_compute_types=types)
    model = WhisperModel("large-v3", device="cuda", compute_type=choice.compute_type)
    # Loading alone does not prove that this GPU can execute the model's kernels.
    segments, _ = model.transcribe(
        np.zeros(16000, dtype=np.float32),
        language="it",
        beam_size=1,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    list(segments)
    torch.cuda.synchronize()
    print(f"GPU pronta: {torch.cuda.get_device_name(0)}; Whisper {choice.compute_type}; PyTorch e CTranslate2.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Controllo GPU fallito: {exc}", file=sys.stderr)
        raise SystemExit(1)
