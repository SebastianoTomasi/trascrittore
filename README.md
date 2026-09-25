# Transcriber

Turns a recording, audio or video, into an Italian transcript that says who
spoke, when, and what they said. A person drags the recording onto
`Trascrivi.bat`; a Docker container transcribes it on the NVIDIA GPU (or the
CPU, with a clear warning), recognizes the voices in the `voci` library next to
the script, and writes `<name> - trascrizione.txt` and `.json` next to the
recording. An agent such as Claude Code or Codex runs the same commands through
the skill that `Installa.bat` installs. Naming a voice that was not recognized
adds its clips to the library. Everything runs on the PC and works offline.

It is a personal tool for people close to the maintainer, on Windows only. The
user guide, in Italian, is [docker/LEGGIMI.md](docker/LEGGIMI.md). Product
decisions live under [docs/](docs/), starting from
[the product promise](docs/product/transcriber-promise.md), and
[CONTEXT.md](CONTEXT.md) holds the vocabulary.

## How it works

`python -m src.transcriber transcribe <recording> [--speakers N] [--out-dir DIR]` runs
four steps on a 16 kHz copy of the recording:

1. transcription: WhisperX with faster-whisper large-v3, pyannote VAD, Italian;
2. word alignment: wav2vec2 for Italian;
3. speaker separation: pyannote community-1, with the exact speaker count when given;
4. speaker recognition: pyannote/embedding voiceprints of fixed windows, overlapped
   speech excluded, matched against the voice library with a threshold and a margin.

Unrecognized voices become "Persona 1..N". `device = auto` picks the GPU, or the
CPU with int8 and a reason that is repeated on screen and in both output files.
The JSON records, for each speaker, the windows used to recognize the voice.

No command asks a question: each prints lines for people on stderr and ends
with one JSON result summary on stdout, and exits with 0 on success, 2 for
invalid arguments, 130 when interrupted and 1 otherwise, including a wrong
line in `trascrittore.ini` (status `invalid_settings`). The other commands:

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
  (`[library]` in the settings; raise `SELECTION_VERSION` when the algorithm
  changes, to start a new trial).

`name`, `listen` and `check` compute voiceprints on the CPU, so they can run beside a
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
| `src/transcriber/` | commands, runner, text and JSON output, naming, library growth, recognition check |
| `src/asr/` | transcription, alignment, diarization, voiceprints and matching |
| `src/settings.py` | the default settings with the person's `trascrittore.ini` on top |
| `docker/defaults.ini` | the default settings, inside the image |
| `docker/LICENZE.md` | credits and license texts of the models the image carries |
| `docker/trascrittore.ps1` | host launcher for people and agents |
| `docker/Trascrivi.bat`, `docker/Verifica.bat`, `docker/Installa.bat`, `docker/LEGGIMI.md` | what users get |
| `docker/skill-trascrittore.md` | the agent skill, installed by `Installa.bat` |
| `docker/build.ps1` | builds the image and exports the files users download |

## Development

Requirements: Python 3.12, Poetry 2, ffmpeg on `PATH`, an NVIDIA GPU for fast runs.

```powershell
poetry install --no-root
copy .env.example .env               # set HF_TOKEN
# optional: a trascrittore.ini with the local folders, and TRANSCRIBER_SETTINGS=trascrittore.ini in .env
.venv\Scripts\python -m src.transcriber transcribe "C:\path\to\Registrazione.m4a" --speakers 3
.venv\Scripts\python -m pytest -q
```

The settings are `docker/defaults.ini` with the lines of the file named by
`TRANSCRIBER_SETTINGS` on top; that file may hold only settings the defaults
know, with values of the same kind. The tests always use the defaults alone and
fake the models.

## Image and distribution

```powershell
powershell -ExecutionPolicy Bypass -File docker\build.ps1
powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "C:\path\to\export\folder"
```

- The Hugging Face token goes from `.env` to BuildKit as a secret; it never lands
  in a layer or in the build history.
- Layers go dependencies → models → code, so a code change rebuilds in seconds.
  A lock change reinstalls the dependencies and downloads the models again (3.4 GB).
- The image works offline (`HF_HUB_OFFLINE=1`) and is about 20 GB in Docker, 7 GB as a `.tar`.
- `-Export` writes `trascrittore.tar`, the `.bat` files, `trascrittore.ps1`,
  the skill, `LEGGIMI.md`, `LICENZE.md` and the `voci` folder. It writes no
  settings file: `Installa.bat` creates `trascrittore.ini` once, for the
  person's own changes, and no update replaces it.
- Users download these files, run `Installa.bat` once and again after each
  update; it removes the previous version and installs the skill for Claude Code
  (`%USERPROFILE%\.claude\skills`) and Codex (`%USERPROFILE%\.agents\skills`),
  with the transcriber's folder written in.

## Sharing with a new person

1. Export into a folder of its own, not the folder you use the transcriber
   from, which holds your settings and your voice library:

   ```powershell
   powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "$env:USERPROFILE\Desktop\Trascrittore da condividere"
   ```

2. Drag these eight files, from the browser, into the `trascrittore` shared
   drive on Claror's Google Drive, and give the person access to it:
   `trascrittore.tar`, `Installa.bat`, `Trascrivi.bat`, `Verifica.bat`,
   `trascrittore.ps1`, `skill-trascrittore.md`, `LEGGIMI.md` and `LICENZE.md`.
   `LICENZE.md` is required: the models' licenses ask for their credits in every
   distribution. The `.tar` is about 7 GB, too big for an agent's Drive
   connector, which passes file contents through the conversation.
3. Leave out:
   - `trascrittore.ini`: `Installa.bat` creates one on their PC;
   - `voci`: each PC has its own library, and the launcher creates an empty one.
     Yours holds other people's voices, which are biometric data, and each
     `registrazioni/clip.json` holds paths of your recordings. As a starting
     point, send separately only the clips of people who agree, such as your
     own; they go into `voci\<Nome Cognome>` on the other PC.
4. The person follows [docker/LEGGIMI.md](docker/LEGGIMI.md): install Docker
   Desktop, download the files one by one (Drive splits a whole folder into
   several zips), and run `Installa.bat`. They need Windows 10 or 11, about
   30 GB free and, for speed, an NVIDIA GPU.

For an update, export again and replace on Drive the files that changed, usually
only `trascrittore.tar`, and tell the person which ones. They put them in the
same folder and run `Installa.bat` again; their `voci` and `trascrittore.ini`
stay as they are.

## Calibration

`[matching]` uses threshold 0.575 and margin 0.10, calibrated on 2026-09-24 by
leave-one-out on four recordings. A wrong name is worse than "Persona N", so
recheck both values with `Verifica.bat` (the `check` command) as the library
grows. It suggests a threshold only from at least 10 simulated missing voices.

## Origin

Extracted on 2026-09-24 from the ASR pipeline of YIAN, a personal project, without
its git history. The two code bases now evolve separately.
