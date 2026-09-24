from __future__ import annotations

import pytest

from src.asr.utils.device import resolve_device


def test_auto_uses_cuda_when_available():
    choice = resolve_device("auto", "float16", cuda_available=True)

    assert (choice.device, choice.compute_type, choice.fallback_reason) == ("cuda", "float16", None)


def test_auto_falls_back_to_cpu_int8_and_explains_the_driver_error():
    choice = resolve_device(
        "auto",
        "float16",
        cuda_available=False,
        cuda_error="Found no NVIDIA driver on your system.",
    )

    assert (choice.device, choice.compute_type) == ("cpu", "int8")
    assert "Found no NVIDIA driver on your system." in choice.fallback_reason


def test_auto_fallback_blames_docker_when_the_gpu_retry_happened():
    choice = resolve_device(
        "auto",
        "float16",
        cuda_available=False,
        cuda_error="Found no NVIDIA driver on your system.",
        docker_gpu_missing=True,
    )

    assert choice.device == "cpu"
    assert "Docker" in choice.fallback_reason
    assert "--gpus" in choice.fallback_reason


def test_auto_fallback_has_a_reason_even_without_error_details():
    choice = resolve_device("auto", "float16", cuda_available=False)

    assert choice.fallback_reason == "Nessuna GPU NVIDIA disponibile."


def test_explicit_cpu_switches_half_precision_without_a_warning():
    choice = resolve_device("cpu", "int8_float16", cuda_available=False)

    assert (choice.device, choice.compute_type, choice.fallback_reason) == ("cpu", "int8", None)


@pytest.mark.parametrize("compute_type", ["int8", "float32"])
def test_cpu_keeps_compute_types_it_supports(compute_type):
    assert resolve_device("auto", compute_type, cuda_available=False).compute_type == compute_type


def test_explicit_cuda_index_is_kept():
    assert resolve_device("cuda:1", "float16", cuda_available=True).device == "cuda:1"


def test_explicit_cuda_without_gpu_fails():
    with pytest.raises(RuntimeError, match="CUDA is not available"):
        resolve_device("cuda", "float16", cuda_available=False)


def test_unknown_device_is_rejected():
    with pytest.raises(RuntimeError, match="auto, cpu or cuda"):
        resolve_device("gpu", "float16", cuda_available=True)
