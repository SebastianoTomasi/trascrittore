from __future__ import annotations

from dataclasses import dataclass


# Set by Trascrivi.bat when `docker run --gpus all` failed and it retried without a GPU.
DOCKER_GPU_FALLBACK_ENV = "TRANSCRIBER_GPU_FALLBACK"

# CTranslate2 has no half-precision kernels on CPU.
_CPU_UNSUPPORTED_COMPUTE_TYPES = {"float16", "int8_float16"}


@dataclass(frozen=True)
class DeviceChoice:
    device: str
    compute_type: str
    fallback_reason: str | None = None


def probe_cuda() -> tuple[bool, str | None]:
    """
    Return whether CUDA is usable and, when it is not, the driver error explaining why.
    """
    import torch

    if torch.cuda.is_available():
        return True, None
    try:
        torch.cuda.init()
    except Exception as exc:
        return False, str(exc).strip() or type(exc).__name__
    return False, None


def _fallback_reason(cuda_error: str | None, docker_gpu_missing: bool) -> str:
    if docker_gpu_missing:
        return (
            "Docker non ha dato accesso alla GPU NVIDIA (l'avvio con --gpus è fallito). "
            "Aggiorna il driver NVIDIA e controlla che Docker Desktop usi WSL2."
        )
    if cuda_error:
        return f"PyTorch non riesce a usare la GPU NVIDIA: {cuda_error}"
    return "Nessuna GPU NVIDIA disponibile."


def resolve_device(
    requested: str,
    compute_type: str,
    *,
    cuda_available: bool,
    cuda_error: str | None = None,
    docker_gpu_missing: bool = False,
) -> DeviceChoice:
    """
    Pick the device and compute type used by every pipeline step.

    `auto` prefers CUDA and falls back to CPU with a reason; an explicit `cuda`
    without a usable GPU is an error.
    """
    requested = requested.strip().lower()
    if requested.startswith("cuda"):
        if not cuda_available:
            raise RuntimeError(f"Config requested device '{requested}' but CUDA is not available on this system.")
        return DeviceChoice(requested, compute_type)
    if requested not in {"auto", "cpu"}:
        raise RuntimeError(f"whisper.device must be auto, cpu or cuda, got '{requested}'.")
    if requested == "auto" and cuda_available:
        return DeviceChoice("cuda", compute_type)

    cpu_compute_type = "int8" if compute_type in _CPU_UNSUPPORTED_COMPUTE_TYPES else compute_type
    reason = _fallback_reason(cuda_error, docker_gpu_missing) if requested == "auto" else None
    return DeviceChoice("cpu", cpu_compute_type, reason)
