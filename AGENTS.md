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

- Name things in code, messages and documentation with the terms of `GLOSSARY.md`, and avoid the words it lists as avoided.

## Documentation

- `README.md` is for developers; `docker/LEGGIMI.md` is the guide for the people who use the tool, in Italian.


## Agent skills

### Issue tracker

Issues live in GitHub Issues on this repository and are handled with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repository root. See `docs/agents/domain.md`.


@advisor-agents.md

Before doing any work, read and follow [advisor-agents.md](advisor-agents.md).
