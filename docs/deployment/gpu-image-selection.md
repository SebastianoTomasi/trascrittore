# Selecting a GPU image at installation

**Status:** accepted

## Scope

This artifact governs how a Windows PC receives the CUDA image suited to its
NVIDIA GPU, and how an update avoids replacing a working installation with an
image whose GPU kernels do not run. Model and batch choices inside the image
belong to Implementation; the person's installation steps belong to Frontend.

## Dependencies

- [Work with or without a GPU](../product/transcriber-promise.md#capabilities)
  — a supported NVIDIA GPU must run all transcription phases on the GPU.
- [Install and update from files](../product/transcriber-promise.md#capabilities)
  — installation uses local release files and loads only the selected image.
- [What an update must not break](../product/transcriber-promise.md#what-an-update-must-not-break)
  — updating never changes the person's settings, voice library or existing
  transcripts.

## Release files

The maintainer builds two images of the same transcriber version, with the same
application and models. They use one shared agent skill. The images differ in
their PyTorch CUDA build:

- `trascrittore-cu126.tar` supports older NVIDIA GPUs, including the MX230;
- `trascrittore-cu128.tar` supports newer NVIDIA GPUs, including the RTX 2070
  and RTX 5070.

This split follows [PyTorch's published CUDA build policy](https://dev-discuss.pytorch.org/t/cuda-toolkit-version-and-architecture-support-update-maxwell-and-pascal-architecture-support-removed-in-cuda-12-8-and-12-9-builds/3128):
its CUDA 12.8 binaries omit Pascal kernels, while its CUDA 12.6 binaries retain
them.

One `Installa.bat` is shared by both. An offline universal folder can contain
both archives; when the GPU of the destination PC is known, the maintainer can
send only the matching archive. The installer does not download dependencies or
load the other image.

## Installation and update

The installer reads the GPU's compute capability from the NVIDIA driver using
[`nvidia-smi`](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html), then
chooses the archive by that capability rather than by a list of GPU names. SM
6.1 selects CUDA 12.6; supported newer capabilities select CUDA 12.8. If the
capability is unsupported or the matching archive is absent, installation
explains the problem and names the needed file when applicable. If no NVIDIA
GPU is present, an available image may be installed for CPU processing under
the Product promise.

After loading the selected image under a candidate tag, installation runs
PyTorch and CTranslate2 GPU operations that exercise real kernels. Only a
successful check makes the candidate the active transcriber image. A failed
check explains the problem and preserves the previous active image. The
installer leaves `trascrittore.ini`, `voci` and existing transcripts alone.

## Release verification

Before claiming GPU support for a variant, the maintainer transcribes a short
recording on that GPU and confirms that every phase used the GPU. The MX230's
4 GB of video memory and current driver require this real-PC check; selecting
the CUDA 12.6 archive alone is not proof that the full recording fits. The
RTX 5070 check also confirms that its existing CUDA 12.8 path and settings
continue to work. If the RTX 2070 is available, it is checked as a third
representative GPU.
