# Repository Instructions

## Development Phase

- This repository is in active development. Changes do not need to preserve backward compatibility unless explicitly requested.
- Prefer simple, direct changes over compatibility layers, migration shims, or legacy fallback behavior.

## Checks

- Run `.venv/Scripts/python -m pytest -q` after every code change.
- After changing `Dockerfile`, `docker/`, `pyproject.toml` or `uv.lock`, rebuild the image with `docker/build.ps1` and transcribe a short recording with it.

## Personal data

- Recordings, voice clips, transcripts, voiceprints and `.env` never enter the repository or the image. `.gitignore` and the `.dockerignore` whitelist enforce this; keep them that way.
- Never print the Hugging Face token. `docker/build.ps1` passes it to the build as a BuildKit secret.

## Vocabulary

- Name things in code, messages and documentation with the terms of `CONTEXT.md`, and avoid the words it lists as avoided.

## Documentation

- `README.md` is for developers; `docker/LEGGIMI.md` is the guide for the people who use the tool, in Italian.


@advisor-agents.md

Before doing any work, read and follow [advisor-agents.md](advisor-agents.md).
