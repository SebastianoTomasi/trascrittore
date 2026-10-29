# Trascrittore

Turns a recording, audio or video, into an Italian transcript that says who
spoke, when, and what they said. A person drags the recording onto
`Trascrivi.bat`; a Docker container transcribes it on the NVIDIA GPU (or the
CPU, with a clear warning), recognizes the voices in the `voci` library next to
the script, and writes `<name>-trascrizione.txt` and `.json` into a folder
`<name>` next to the recording, then moves the recording into it; `<name>` is
the recording's name without spaces. Everything runs on the PC and works
offline.

It is a personal tool for people close to the maintainer, on Windows only. The
user guide, in Italian, is [docker/LEGGIMI.md](docker/LEGGIMI.md). Product
decisions live under [docs/](docs/), starting from
[the product promise](docs/product/transcriber-promise.md), and
[GLOSSARY.md](GLOSSARY.md) holds the vocabulary.

## Features

- **Transcription.** Any audio or video file that ffmpeg reads, in Italian.
  The `.txt` opens with the recording's name, its duration, the device used and
  who speaks, then one `[HH:MM:SS] Name: text` line per turn. The `.json` holds
  the same turns for programs, each split into segments, one per sentence and
  again at pauses of a second or more, with their start and end.
- **Speaker separation.** The voices are told apart automatically; the person
  can give the exact number of speakers to help.
- **Speaker recognition.** Speakers with voice clips in the `voci` library
  appear under their name. When recognition is not sure enough the speaker
  stays "Persona N", because a wrong name is worse than none; words that no
  speaker can be given appear as "Voce non attribuita".
- **Naming.** Right after a transcription, or later by dropping its `.json` on
  `Trascrivi.bat`, the person names each "Persona N" after seeing two of their
  sentences and hearing a 10-second clip of the voice. Naming rewrites both
  transcript files without transcribing again and adds the speaker's best clips
  to the library, so later recordings recognize them. A name similar to someone
  already in the library is asked about before anything is saved. Added clips
  form pools in the person's folder: a known voice that recognition missed
  starts a new pool, up to `max_pools` (8) per person, and past `max_clips`
  (16) clips in a pool, the transcriber proposes which to remove. Only when the
  person asks, a recognized voice can be confirmed, which adds more of its
  clips, or corrected.
- **Who spoke.** Every transcription ends with who spoke and for how many
  minutes, longest first, so the person sees a wrong name at once.
- **Agents.** `Installa.bat` installs two skills for Claude Code and Codex:
  `trascrittore`, which runs every command above without questions and, for a
  video, titles the transcript's folder and keeps the frames that matter in
  `fotogrammi`, and
  `fix-transcript`, which corrects misheard words, such as names and technical
  terms, in a transcript's `.txt` or in subtitles made from it.
- **GPU or CPU.** On a supported NVIDIA GPU every phase runs on the GPU. A PC
  without one transcribes on the CPU, much more slowly, with a warning on
  screen and in the transcript. The installer tests the GPU before activating a
  new version, and keeps the previous one when the test fails.
- **Settings without a new version.** `trascrittore.ini`, next to the scripts,
  holds only what the person changed; everything else comes from
  `docker/defaults.ini` inside the image.
- **Plain messages.** Every problem a person can fix, such as Docker Desktop
  not running, an unreadable recording or GPU memory running out, ends with a
  message in Italian saying what to do.

## Requirements

To use the transcriber:

- Windows 10 or 11, 64-bit. Linux and macOS are not supported, and an agent
  that uses the transcriber must run on Windows, not inside WSL.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with its
  default WSL 2 backend. Installing it needs administrator rights, and it needs
  hardware virtualization enabled in the firmware. Docker Desktop is free for
  personal use and small businesses; larger companies need a paid subscription.
- About 30 GB of free disk space: the image takes about 20 GB in Docker, and
  `trascrittore-cu128.tar` about 7 GB until it is deleted after installation.
- For speed, an NVIDIA GPU with compute capability 7.0–12.x (Volta and newer,
  for example GeForce GTX 16 and RTX 20, 30, 40 and 50 series) and an
  up-to-date NVIDIA driver. The installer refuses older NVIDIA GPUs, such as
  the GTX 10 series and the MX230, instead of falling back to the CPU: on the
  MX230 transcription was too slow to be useful. Without an NVIDIA GPU,
  including PCs with only AMD or Intel graphics, everything runs on the CPU and
  can take longer than the recording itself.
- Recordings in Italian, and a person who reads Italian: messages and guide are
  in Italian.
- Internet only to download Docker Desktop and the release files. Transcribing
  needs no connection.

To build the image, also:

- a [Hugging Face](https://huggingface.co) read token whose account has
  accepted the conditions of
  [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)
  and [pyannote/embedding](https://huggingface.co/pyannote/embedding);
- room for the build cache beside the image, and 7 GB more for each export.

To develop: Python 3.12, [uv](https://docs.astral.sh/uv/) and ffmpeg on `PATH`;
see [Development](#development).

## How it works

`python -m src.transcriber transcribe <recording> [--speakers N] [--out-dir DIR]` runs
four steps on a 16 kHz copy of the recording:

1. transcription: WhisperX with faster-whisper large-v3, pyannote VAD, Italian;
2. word alignment: wav2vec2 for Italian;
3. speaker separation: pyannote community-1, with the exact speaker count when given;
4. speaker recognition: pyannote/embedding voiceprints of fixed windows, overlapped
   speech excluded, matched against the voice library with a threshold and a margin.

Unrecognized voices become "Persona 1..N". The transcript goes into a folder
next to the recording named after its slug: no accents, lowercase, each run of
other characters one hyphen. Once both files are written, the recording moves
into it as `<slug>.<ext>`, and the JSON is rewritten with its new place; a
recording already in its transcript's folder is transcribed there again. With
`--out-dir` the folder goes there and the recording stays where it is. The
installer reads each NVIDIA
GPU's compute capability with `nvidia-smi`, accepts 7.0–12.x, and tests the
CUDA 12.8 image's PyTorch and CTranslate2 kernels before activation.
`device = auto` uses the GPU for every transcription phase on a GPU
installation. `compute_type = auto` uses float16 where CTranslate2 supports it,
another supported precision otherwise, and int8 on a PC without NVIDIA. The
Whisper batch size drops to 4 on GPUs with up to 6 GB of memory and to 1 with
4 GB or less. A GPU failure stops the run with an error.
The JSON records, for each speaker, the windows used to recognize the voice
and how sure recognition was, and, in each turn, its segments: one per
sentence, split again at pauses of a second or more, each with its start, end
and text.

No command asks a question: each prints lines for people on stderr and ends
with one JSON result summary on stdout, and exits with 0 on success, 2 for
invalid arguments, 130 when interrupted and 1 otherwise, including a wrong
line in `trascrittore.ini` (status `invalid_settings`). The other commands:

- `name <transcript.json> "Persona 2=Nome Cognome" ... [--recording <file>]`
  rewrites both transcript files from the JSON, and cuts clips of each named
  speaker from the recording into a pool, a subfolder of `voci/<Nome>`, only
  those the clip selection keeps (`[library]` in the settings), with their
  origin in the pool's `clip.json`. A person new to the library gets
  `registrazioni`; a known person the library missed gets a new pool named
  after the transcript's folder, with at least 3 kept clips and fewer than
  `[library] max_pools` added pools, and the closest added pool otherwise.
  Only on the person's request, `--confirm "<Nome>"` adds clips of a
  recognized speaker to the closest pool and `--correct` lets a pair replace a
  recognized name. A name similar to a person in the library saves nothing and
  ends with status `similar_name` until it is repeated with the folder's name
  or with `--new-person`. A pool past `[library] max_clips` clips gives status
  `over_cap` (exit 0) with a proposal of clips to remove from it;
- `remove-clips "<Nome>" <clip.wav> ...` removes the proposed clips once the
  person confirms, and only clips recorded in a `clip.json` of that person's
  pools;
- `listen <transcript.json> "Persona 2" [--clip N] [--recording <file>]` cuts
  one clip of one speaker, the best or the N-th, for the person to hear before
  naming; clips opened together cannot be told apart, so it takes one speaker
  at a time; a speaker without a full window is heard from their longest one.

`--recording` gives the recording when it has moved since the transcription.
`name` and `listen` compute voiceprints on the CPU, so they can run beside a
transcription. `docker/trascrittore.ps1` is the host launcher that
`Trascrivi.bat` and agents call: it mounts the folders, uses the installer's
GPU/CPU mode, refuses a second transcription with status `busy` (exit 3),
opens the clip `listen --open` prepares, and asks the person's questions for
`Trascrivi.bat`.
`trascrittore.ps1 help` prints its reference. The launcher stays ASCII, because Windows PowerShell 5.1 reads a script
without a byte order mark in the ANSI code page. The design is in
[docs/features/agent-cli](docs/features/agent-cli/) and
[docs/features/voice-library-growth](docs/features/voice-library-growth/).

| Path | Content |
|---|---|
| `src/transcriber/` | commands, runner, text and JSON output, naming, library growth |
| `src/asr/` | transcription, alignment, diarization, voiceprints and matching |
| `src/settings.py` | the default settings with the person's `trascrittore.ini` on top |
| `docker/defaults.ini` | the default settings, inside the image |
| `docker/LICENZE.md` | credits and license texts of the models the image carries |
| `docker/trascrittore.ps1` | host launcher for people and agents |
| `docker/Trascrivi.bat`, `docker/Installa.bat`, `docker/LEGGIMI.md` | what users get |
| `docker/skill-trascrittore.md`, `docker/skill-fix-transcript.md` | the agent skills `trascrittore` and `fix-transcript`, installed by `Installa.bat` |
| `docker/build.ps1` | builds the image and exports the files users download |

## Where the data lives

| What | Where |
|---|---|
| Transcripts | A folder of their own next to the recording, which moves into it, or in `--out-dir`; the frames an agent keeps go in its `fotogrammi` subfolder. |
| Voice library | `voci\` next to the scripts, one folder per person; clips added by naming in pools, subfolders of `voci\<Nome>` such as `registrazioni`, each with `clip.json`. |
| The person's settings | `trascrittore.ini` next to the scripts. |
| Voiceprint cache, GPU/CPU mode, clips to listen to | `%LOCALAPPDATA%\Trascrittore\` (`cache\`, `gpu-mode.txt`, `ascolto\`). |
| Working files | Inside the container of each run, deleted when it ends. |
| Image | Docker: `trascrittore:latest` is the active image, `trascrittore:cu128` the last one loaded. |
| Skills | `%USERPROFILE%\.claude\skills\<name>` and `%USERPROFILE%\.agents\skills\<name>`. |

Voice clips, clip records and voiceprints are biometric personal data; the
classes, and how long each stays, are in
[Personal data and external obligations](docs/product/personal-data-and-obligations.md).
To uninstall, remove the two images, the transcriber's folder,
`%LOCALAPPDATA%\Trascrittore` and the two skill folders; the guide gives the
steps.

## Development

```powershell
uv sync
copy .env.example .env               # set HF_TOKEN
# optional: a trascrittore.ini with the local folders, and TRANSCRIBER_SETTINGS=trascrittore.ini in .env
.venv\Scripts\python -m src.transcriber transcribe "C:\path\to\Registrazione.m4a" --speakers 3
.venv\Scripts\python -m pytest -q
```

Outside Docker the models download from Hugging Face on first use, so
`HF_TOKEN` must be set, and a run without an NVIDIA GPU uses the CPU.
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
- Dependencies and models go into an image of their own,
  `trascrittore-base:<key>`, and the code goes on top of it. The key changes
  only with `Dockerfile`, `pyproject.toml`, `uv.lock` or
  `docker/prefetch_models.py`, so a code change reuses that image even after
  Docker has cleaned up its build cache. Docker still needs time to export the
  large image.
- Python's image is pinned by digest, so a Docker Hub refresh of its tag
  changes nothing until the digest in the `Dockerfile` is moved on.
- A change to one of those files builds a new base image and reinstalls
  dependencies. `-ModelImage trascrittore:latest` can reuse models from an
  existing image when their IDs are unchanged; that build needs no Hugging Face
  token or model download. Base images of older keys can be removed with
  `docker image rm`.
- The image works offline (`HF_HUB_OFFLINE=1`). It is about 20 GB in Docker,
  7 GB as a `.tar`.
- `-Export` writes `trascrittore-cu128.tar`, the `.bat` files, `trascrittore.ps1`,
  the skills, `LEGGIMI.md`, `LICENZE.md` and the `voci` folder. It writes no
  settings file: `Installa.bat` creates `trascrittore.ini` once, for the
  person's own changes, and no update replaces it.
- Users download these files, run `Installa.bat` once and again after each
  update; it checks the GPU and image, then installs the skills for Claude Code
  (`%USERPROFILE%\.claude\skills`) and Codex (`%USERPROFILE%\.agents\skills`),
  with the transcriber's folder written in. A new skill `<name>` is a
  `docker/skill-<name>.md` file, added to `$SkillNames` in `trascrittore.ps1`
  and to the files `build.ps1` exports.
- To install from source on your own PC, export into a folder of its own and
  follow [docker/LEGGIMI.md](docker/LEGGIMI.md) from that folder, starting at
  `Installa.bat`.

Before distributing an update, run the test suite, build the image, and check
that the TAR is complete and named correctly. On each target GPU, run
`Installa.bat` and transcribe a short recording, checking the CUDA device in
the result. An installer kernel check is not a substitute for a full recording
test. Keep the user's `voci` folder and `trascrittore.ini` out of the exported
release folder.

## Sharing with a new person

1. Export into a folder of its own, not the folder you use the transcriber
   from, which holds your settings and your voice library:

   ```powershell
   powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "$env:USERPROFILE\Desktop\Trascrittore da condividere"
   ```

2. Drag the release files, from the browser, into the `trascrittore` shared
   drive on Claror's Google Drive, and give the person access to it:
   `trascrittore-cu128.tar`, `Installa.bat`,
   `Trascrivi.bat`, `trascrittore.ps1`,
   `skill-trascrittore.md`, `skill-fix-transcript.md`, `LEGGIMI.md` and
   `LICENZE.md`. If the destination PC has an older NVIDIA GPU, the installer
   will explain that it is unsupported.
   `LICENZE.md` is required: the models' licenses ask for their credits in every
   distribution. The `.tar` is about 7 GB, too big for an agent's Drive
   connector, which passes file contents through the conversation.
3. Leave out:
   - `trascrittore.ini`: `Installa.bat` creates one on their PC;
   - `voci`: each PC has its own library, and the launcher creates an empty one.
     Yours holds other people's voices, which are biometric data, and each
     `clip.json` holds paths of your recordings. As a starting
     point, send separately only the clips of people who agree, such as your
     own; they go into `voci\<Nome Cognome>` on the other PC.
4. The person follows [docker/LEGGIMI.md](docker/LEGGIMI.md): install Docker
   Desktop, download the files one by one (Drive splits a whole folder into
   several zips), and run `Installa.bat`. Their PC must meet the
   [requirements](#requirements).

For an update, export again and replace on Drive the files that changed, including
`trascrittore-cu128.tar`, and tell the person which ones. They put them in the
same folder and run `Installa.bat` again; their `voci` and `trascrittore.ini`
stay as they are.

## Calibration

`[matching]` uses threshold 0.575 and margin 0.10, calibrated on 2026-09-24 by
leave-one-out on four recordings. A wrong name is worse than "Persona N".
Nothing on a PC suggests new values: the maintainer tunes them by hand when
people report wrong names, which the list of who spoke after each
transcription brings to light.

## Origin

Extracted on 2026-09-24 from the ASR pipeline of YIAN, a personal project, without
its git history. The two code bases now evolve separately.
