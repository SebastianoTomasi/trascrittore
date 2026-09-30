from __future__ import annotations

import pytest

from src.asr.utils.device import limit_batch_size, resolve_device


def test_auto_uses_cuda_when_available():
    choice = resolve_device("auto", "auto", cuda_available=True, supported_compute_types={"float16", "int8_float32"})

    assert (choice.device, choice.compute_type, choice.fallback_reason) == ("cuda", "float16", None)


def test_auto_uses_int8_float32_on_pascal_gpu():
    choice = resolve_device("auto", "auto", cuda_available=True, supported_compute_types={"int8_float32", "float32"})
    assert (choice.device, choice.compute_type) == ("cuda", "int8_float32")


def test_auto_never_uses_half_gpu_when_pytorch_fails():
    choice = resolve_device(
        "auto", "auto", cuda_available=False,
        cuda_error="no kernel image is available for execution on the device",
        supported_compute_types={"int8_float32"},
    )
    assert (choice.device, choice.compute_type) == ("cpu", "int8")
    assert "no kernel image" in choice.fallback_reason


@pytest.mark.parametrize(("memory_gib", "expected"), [(4, 1), (6, 4), (8, 8)])
def test_batch_size_respects_gpu_memory(memory_gib, expected):
    assert limit_batch_size(8, "cuda", memory_gib * 1024**3) == expected


def test_cuda_probe_runs_a_real_kernel(monkeypatch):
    import sys
    from types import SimpleNamespace
    from src.asr.utils.device import probe_cuda

    class BrokenRnn:
        def __init__(self, *args, **kwargs):
            pass

        def to(self, device):
            raise RuntimeError("no kernel image")

    fake_cuda = SimpleNamespace(is_available=lambda: True, synchronize=lambda: None)
    fake_torch = SimpleNamespace(cuda=fake_cuda, ones=lambda *a, **k: object(), nn=SimpleNamespace(GRU=BrokenRnn))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    available, reason = probe_cuda()
    assert not available
    assert "no kernel image" in reason


def test_auto_falls_back_to_cpu_int8_and_explains_the_driver_error():
    choice = resolve_device(
        "auto",
        "float16",
        cuda_available=False,
        cuda_error="Found no NVIDIA driver on your system.",
    )

    assert (choice.device, choice.compute_type) == ("cpu", "int8")
    assert "Found no NVIDIA driver on your system." in choice.fallback_reason


def test_auto_fallback_has_a_reason_even_without_error_details():
    choice = resolve_device("auto", "float16", cuda_available=False)

    assert choice.fallback_reason == "Nessuna GPU NVIDIA disponibile."


def test_explicit_cpu_switches_half_precision_without_a_warning():
    choice = resolve_device("cpu", "int8_float16", cuda_available=False)

    assert (choice.device, choice.compute_type, choice.fallback_reason) == ("cpu", "int8", None)


def test_gpu_installation_rejects_explicit_cpu_setting(monkeypatch):
    from src.asr.utils import config as config_module

    config_module._device_choice.cache_clear()
    monkeypatch.setenv("TRANSCRIBER_REQUIRE_GPU", "1")
    monkeypatch.setitem(config_module.config["whisper"], "device", "cpu")
    try:
        with pytest.raises(RuntimeError, match="togli device = cpu"):
            config_module._device_choice()
    finally:
        config_module._device_choice.cache_clear()


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
