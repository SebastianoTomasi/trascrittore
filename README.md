# meeting-transcriber

Turns one meeting recording into an Italian transcript with the names of who
spoke. A colleague drags the audio onto `Trascrivi.bat` in a shared folder; a
Docker container transcribes it on the NVIDIA GPU (or the CPU, with a clear
warning), recognizes the voices enrolled in the shared `voci` library, and
writes `<name> - trascrizione.txt` and `.json` next to the audio. An agent such
as Claude Code or Codex runs the same commands through the skill that
`Installa.bat` installs. Naming a voice that was not recognized adds its clips
to the library. Nothing leaves the PC.

It is a pilot. The colleague-facing guide is [docker/LEGGIMI.md](docker/LEGGIMI.md).

## How it works

`python -m src.meeting transcribe <audio> [--speakers N] [--out-dir DIR]` runs
four steps on a 16 kHz copy of the audio:

1. transcription: WhisperX with faster-whisper large-v3, pyannote VAD, Italian;
2. word alignment: wav2vec2 for Italian;
3. speaker separation: pyannote community-1, with the exact speaker count when given;
4. speaker recognition: pyannote/embedding voiceprints of fixed windows, overlapped
   speech excluded, matched against the enrolled library with a threshold and a margin.

Unrecognized voices become "Persona 1..N". `device = auto` picks the GPU, or the
CPU with int8 and a reason that is repeated on screen and in both output files.
The JSON records, for each speaker, the windows used to recognize the voice.

No command asks a question: each prints lines for people on stderr and ends
with one JSON result summary on stdout, and exits with 0 on success, 2 for
invalid arguments, 130 when interrupted and 1 otherwise. The other commands:

- `name <transcript.json> "Persona 2=Nome Cognome" ...` rewrites both transcript
  files from the JSON, and cuts clips of each named speaker from the recording
  into `voci/<Nome>/registrazioni`, with their origin and the clip selection's
  vote in `clip.json`;
- `listen <transcript.json> "Persona 2" ...` joins a speaker's best one or two
  clips in one file, for the person to hear before naming;
- `check` scores the voices a person named (marked `named` in the JSON) against
  the library without the clips cut from the same recording, simulates missing
  voices by removing one person at a time, and suggests a threshold above every
  wrong name without writing it;
- `trial` compares the selection's votes with the clips the person deleted;
  after 10 named speakers without a disagreement, `trial --reviewed` (the person
  confirms they reviewed the clips) lets the selection discard clips by itself
  (`[library]` in `meeting.ini`; raise `SELECTION_VERSION` when the algorithm
  changes, to start a new trial).

`name`, `listen` and `check` embed on the CPU, so they can run beside a
transcription. `docker/trascrittore.ps1` is the host launcher that
`Trascrivi.bat`, `Verifica.bat` and agents all call: it mounts the folders,
falls back to the CPU when Docker has no GPU, refuses a second transcription
with status `busy` (exit 3), and asks the person's questions for
`Trascrivi.bat`. It stays ASCII, because Windows PowerShell 5.1 reads a script
without a byte order mark in the ANSI code page. The design is in
[docs/features/agent-cli](docs/features/agent-cli/) and
[docs/features/voice-library-growth](docs/features/voice-library-growth/).

| Path | Content |
|---|---|
| `src/meeting/` | commands, runner, text and JSON output, naming, library growth, recognition check |
| `src/asr/` | transcription, alignment, diarization, voiceprints and matching |
| `docker/meeting.ini` | settings used inside the container |
| `docker/trascrittore.ps1` | host launcher for people and agents |
| `docker/Trascrivi.bat`, `docker/Verifica.bat`, `docker/Installa.bat`, `docker/LEGGIMI.md` | what colleagues get |
| `docker/skill-trascrittore.md` | the agent skill, installed by `Installa.bat` |
| `docker/build.ps1` | builds the image and exports the shared folder |

## Development

Requirements: Python 3.12, Poetry 2, ffmpeg on `PATH`, an NVIDIA GPU for fast runs.

```powershell
poetry install --no-root
copy .env.example .env               # set HF_TOKEN
copy docker\meeting.ini meeting.ini  # point enrollment_dir, paths_output and cache_dir at local folders
.venv\Scripts\python -m src.meeting transcribe "C:\path\to\Riunione.m4a" --speakers 3
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
- `-Export` writes `meeting-transcriber.tar`, the `.bat` files, `trascrittore.ps1`,
  the skill, `LEGGIMI.md` and the `voci` folder, and copies `meeting.ini` only when
  the shared folder has none, because that copy holds the tuned settings.
- Colleagues run `Installa.bat` once and after each update; it removes the previous
  version and installs the skill for Claude Code (`%USERPROFILE%\.claude\skills`)
  and Codex (`%USERPROFILE%\.agents\skills`), with the transcriber's folder written in.

## Calibration

`[matching]` uses threshold 0.575 and margin 0.10, calibrated on 2026-09-24 by
leave-one-out on four recordings. A wrong name is worse than "Persona N", so
recheck both values with `Verifica.bat` (the `check` command) as the library
grows. It suggests a threshold only from at least 10 simulated missing voices.

## Origin

Extracted on 2026-09-24 from the ASR pipeline of YIAN, a personal project, without
its git history. The two code bases now evolve separately.
