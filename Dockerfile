# syntax=docker/dockerfile:1.7
# Transcriber: one recording in, a transcript with the speakers' names out.
# Build with docker/build.ps1, which passes the Hugging Face token as a secret.
ARG MODEL_STAGE=downloaded
ARG MODEL_IMAGE=trascrittore:latest
FROM python:3.12-slim-bookworm AS dependencies

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    HF_HOME=/models/hf \
    TORCH_HOME=/models/torch \
    NLTK_DATA=/models/nltk \
    PYANNOTE_METRICS_ENABLED=false

WORKDIR /app

# Layers go from slowest-changing to fastest: dependencies, models, then code.
# The cache mount keeps downloaded wheels (torch alone is ~3 GB) out of the image
# but available to the next build after a lock change.
# uv installs into the image's own Python (UV_PROJECT_ENVIRONMENT); --inexact keeps pip.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install uv==0.11.8 \
    && uv sync --locked --no-dev --inexact \
    && pip uninstall -y uv

# CTranslate2 (faster-whisper) loads cuBLAS and cuDNN from the pip wheels torch already installs.
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.12/site-packages/nvidia/cudnn/lib

FROM dependencies AS downloaded
COPY docker/prefetch_models.py docker/
# A Xet transfer of Whisper stalled for 45 minutes on a slow link; plain HTTP downloads time out and resume.
RUN --mount=type=secret,id=hf_token,required=true \
    HF_TOKEN="$(cat /run/secrets/hf_token)" HF_HUB_DISABLE_XET=1 python docker/prefetch_models.py

FROM ${MODEL_IMAGE} AS model_source
FROM dependencies AS copied
COPY --from=model_source /models /models

FROM ${MODEL_STAGE} AS runtime
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TRANSCRIBER_DEFAULTS=/app/docker/defaults.ini

# The model licenses travel with the image, as with every exported copy.
COPY docker/defaults.ini docker/LICENZE.md docker/
COPY docker/gpu_probe.py docker/
COPY src ./src

ENTRYPOINT ["python", "-m", "src.transcriber"]
