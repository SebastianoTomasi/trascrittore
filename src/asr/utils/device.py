from __future__ import annotations

from dataclasses import dataclass


_CPU_UNSUPPORTED_COMPUTE_TYPES = {"float16", "int8_float16"}


@dataclass(frozen=True)
class DeviceChoice:
    device: str
    compute_type: str
    fallback_reason: str | None = None


def limit_batch_size(batch_size: int, device: str, gpu_memory_bytes: int | None = None) -> int:
    if not device.startswith("cuda") or gpu_memory_bytes is None:
        return batch_size
    if gpu_memory_bytes <= 4 * 1024**3:
        return min(batch_size, 1)
    if gpu_memory_bytes <= 6 * 1024**3:
        return min(batch_size, 4)
    return batch_size


def probe_cuda() -> tuple[bool, str | None]:
    """Run a PyTorch tensor operation and a cuDNN kernel on the selected GPU."""
    import torch

    try:
        if not torch.cuda.is_available():
            torch.cuda.init()
            return False, "CUDA non e disponibile."
        x = torch.ones((1, 1, 1), device="cuda")
        torch.nn.GRU(1, 1, batch_first=True).to("cuda")(x)
        torch.cuda.synchronize()
    except Exception as exc:
        return False, str(exc).strip() or type(exc).__name__
    return True, None


def resolve_device(
    requested: str,
    compute_type: str,
    *,
    cuda_available: bool,
    cuda_error: str | None = None,
    supported_compute_types: set[str] | None = None,
) -> DeviceChoice:
    """Choose one device for every transcription phase and a valid Whisper precision."""
    requested = requested.strip().lower()
    if requested not in {"auto", "cpu"} and not requested.startswith("cuda"):
        raise RuntimeError(f"whisper.device must be auto, cpu or cuda, got '{requested}'.")
    if requested.startswith("cuda") and not cuda_available:
        raise RuntimeError(f"Config requested device '{requested}' but CUDA is not available on this system.")

    use_cuda = requested.startswith("cuda") or (requested == "auto" and cuda_available)
    device = requested if requested.startswith("cuda") else "cuda" if use_cuda else "cpu"
    if compute_type == "auto":
        if use_cuda:
            supported = supported_compute_types or set()
            compute_type = next(
                (kind for kind in ("float16", "int8_float32", "int8", "float32") if kind in supported),
                "float16" if supported_compute_types is None else "",
            )
            if not compute_type:
                raise RuntimeError("CTranslate2 non supporta questa GPU NVIDIA.")
        else:
            compute_type = "int8"
    elif use_cuda and supported_compute_types is not None and compute_type not in supported_compute_types:
        raise RuntimeError(f"CTranslate2 non supporta compute_type={compute_type} su questa GPU NVIDIA.")

    if use_cuda:
        return DeviceChoice(device, compute_type)
    cpu_compute_type = "int8" if compute_type in _CPU_UNSUPPORTED_COMPUTE_TYPES else compute_type
    reason = (
        f"PyTorch non riesce a usare la GPU NVIDIA: {cuda_error}"
        if cuda_error
        else "Nessuna GPU NVIDIA disponibile."
    ) if requested == "auto" else None
    return DeviceChoice("cpu", cpu_compute_type, reason)
