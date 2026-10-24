# GPU installation and verification

**Status:** accepted

## Scope

This artifact governs installation of the CUDA image on Windows and how an
update avoids replacing a working installation with an image whose GPU kernels
do not run. Model and batch choices inside the image belong to Implementation;
the person's installation steps belong to Frontend.

## Dependencies

- [Work with or without a GPU](../product/transcriber-promise.md#capabilities)
  — a supported NVIDIA GPU must run all transcription phases on the GPU.
- [Install and update from files](../product/transcriber-promise.md#capabilities)
  — installation uses a local release file.
- [What an update must not break](../product/transcriber-promise.md#what-an-update-must-not-break)
  — updating never changes the person's settings, voice library or existing
  transcripts.

## Release image

The maintainer distributes one image, `trascrittore-cu128.tar`, with the CUDA
12.8 PyTorch build. It supports the RTX 2070 and RTX 5070 and other NVIDIA GPUs
with compute capability 7.0–12.x when the GPU check succeeds. Older NVIDIA
GPUs, including the MX230, are unsupported: real use on the MX230 was too slow
to be useful. The installer does not download another image or fall back to CPU
when it finds an unsupported NVIDIA GPU.

## Installation and update

The installer reads each NVIDIA GPU's compute capability with
[`nvidia-smi`](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html).
It rejects capabilities outside 7.0–12.x with a clear error. If no NVIDIA GPU
is present, the image may be installed for CPU processing under the Product
promise. The release folder needs only `trascrittore-cu128.tar` and the shared
scripts, guide, licenses and skills.

After loading the image under a candidate tag, installation runs PyTorch and
CTranslate2 GPU operations that exercise real kernels. Only a successful check
makes the candidate the active image. A failed check explains the problem and
preserves the previous active image. The installer leaves `trascrittore.ini`,
`voci` and existing transcripts alone.

## Release verification

Before distributing an update, the maintainer transcribes a short recording on
the RTX 5070 and checks that CUDA was used. This guards its existing path and
settings. The RTX 2070 can be checked when available. The installer kernel
check guards other supported capabilities, but a short recording on a target
GPU is the final confirmation of speed and available memory.
