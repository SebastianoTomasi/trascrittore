# meeting-transcriber

Turns one meeting recording into an Italian transcript with the names of who
spoke. A colleague drags the audio onto `Trascrivi.bat` in a shared folder; a
Docker container transcribes it on the NVIDIA GPU (or the CPU, with a clear
warning), recognizes the voices enrolled in the shared `voci` library, and
writes `<name> - trascrizione.txt` and `.json` next to the audio. Nothing
leaves the PC.

It is a pilot. The colleague-facing guide is [docker/LEGGIMI.md](docker/LEGGIMI.md).

## How it works

`python -m src.meeting <audio> [--speakers N] [--ask-names]` runs four steps on
a 16 kHz copy of the audio:

1. transcription: WhisperX with faster-whisper large-v3, pyannote VAD, Italian;
2. word alignment: wav2vec2 for Italian;
3. speaker separation: pyannote community-1, with the exact speaker count when given;
4. speaker recognition: pyannote/embedding voiceprints of fixed windows, overlapped
   speech excluded, matched against the enrolled library with a threshold and a margin.

Unrecognized voices become "Persona 1..N"; with `--ask-names` the user can name
them for that transcript only. `device = auto` picks the GPU, or the CPU with
int8 and a reason that is repeated on screen and in both output files.

| Path | Content |
|---|---|
| `src/meeting/` | command line, runner, text and JSON output |
| `src/asr/` | transcription, alignment, diarization, voiceprints and matching |
| `docker/meeting.ini` | settings used inside the container |
| `docker/Trascrivi.bat`, `docker/Installa.bat`, `docker/LEGGIMI.md` | what colleagues get |
| `docker/build.ps1` | builds the image and exports the shared folder |

## Development

Requirements: Python 3.12, Poetry 2, ffmpeg on `PATH`, an NVIDIA GPU for fast runs.

```powershell
poetry install --no-root
copy .env.example .env               # set HF_TOKEN
copy docker\meeting.ini meeting.ini  # point enrollment_dir, paths_output and cache_dir at local folders
.venv\Scripts\python -m src.meeting "C:\path\to\Riunione.m4a" --speakers 3 --ask-names
.venv\Scripts\python -m pytest -q
```

`MEETING_CONFIG` selects another config file. The tests always use
`docker/meeting.ini` and fake the models.

## Image and distribution

```powershell
powershell -ExecutionPolicy Bypass -File docker\build.ps1
powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "C:\path\to\shared\folder"
```

- The Hugging Face token goes from `.env` to BuildKit as a secret; it never lands
  in a layer or in the build history.
- Layers go dependencies → models → code, so a code change rebuilds in seconds.
  A lock change reinstalls the dependencies and downloads the models again (3.4 GB).
- The image works offline (`HF_HUB_OFFLINE=1`) and is about 20 GB in Docker, 7 GB as a `.tar`.
- `-Export` writes `meeting-transcriber.tar`, the `.bat` files, `LEGGIMI.md` and
  the `voci` folder, and copies `meeting.ini` only when the shared folder has none,
  because that copy holds the tuned settings.
- Colleagues run `Installa.bat` once and after each update; it removes the previous version.

## Calibration

`[matching]` uses threshold 0.575 and margin 0.10, calibrated on 2026-09-24 by
leave-one-out on four recordings. A wrong name is worse than "Persona N", so
recheck both values against the `speakers` block of the JSON after real meetings.

## Origin

Extracted on 2026-09-24 from the ASR pipeline of YIAN, a personal project, without
its git history. The two code bases now evolve separately.
