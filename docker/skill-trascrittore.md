---
name: trascrittore
description: Transcribe audio or video recordings (meetings, calls, OBS recordings) in Italian on this PC, with the names of who spoke, keep frames of what a video showed, give names to the voices left as "Persona N", and, when the user asks, confirm or correct a voice the transcriber recognized. Use when the user asks to transcribe a recording ("trascrivi questa registrazione"), who spoke in it, for the frames or images of a video, to name the speakers of a transcript, or to add clips of a person or fix a wrong name ("vorrei aggiungere delle clip di Sebastiano").
---

# Trascrittore

The transcriber installed in `{{CARTELLA}}` turns a recording into an Italian transcript that says
who spoke, when, and what they said. It runs on this PC in Docker and sends nothing anywhere.

Run every command through its launcher. The same line works from PowerShell, cmd and Git Bash:

```
powershell -NoProfile -ExecutionPolicy Bypass -File "{{CARTELLA}}\trascrittore.ps1" <command> [arguments]
```

Below, `trascrittore` stands for that whole line. No command asks questions. Lines for people go to
standard error. Every command ends with one line of JSON on standard output, the result summary,
with a `status` and an Italian `message` you can relay. Exit status: 0 ok, 2 invalid arguments,
3 another transcription is running, 130 interrupted, 1 any other failure. `trascrittore help`
prints the full reference.

## Transcribe a recording

```
trascrittore transcribe "<recording>" [--speakers N] [--out-dir "<folder>"]
```

- A transcription takes minutes, and on a CPU longer than the recording itself. Start it in the
  background and wait until it ends; do not hold a foreground command open. If your environment
  cannot run commands in the background, give the command a timeout longer than the recording.
- Do not ask how many people speak. Pass `--speakers N` when the person states it: an exact number
  separates the voices a little better, a wrong one worse.
- The recording must be on the PC. A file that is only online in OneDrive or Google Drive must be
  downloaded first.
- The transcript goes in a folder of its own next to the recording, and the recording moves into
  it. The transcriber writes the names it creates without spaces: lowercase, without accents, each
  run of characters other than letters and digits replaced by one hyphen, and no hyphen at either
  end. So `2026-10-29 14-30-12.mkv` gives the folder
  `2026-10-29-14-30-12`, holding `2026-10-29-14-30-12-trascrizione.txt`, `...-trascrizione.json` and
  the recording as `2026-10-29-14-30-12.mkv`. With `--out-dir` the folder goes there and the
  recording stays where it is. Transcribing a recording that is already in its folder writes there
  again.

On success the summary gives `folder`, `recording` (where the recording is now), `recording_moved`,
`transcript_txt`, `transcript_json`, `duration_sec`, `elapsed_sec`, `device`, `warnings`, and
`speakers`: for each one its `label`, whether it was `recognized`, and its `speech_sec`. When
`recording_moved` is false without `--out-dir`, the `message` says why the recording stayed where
it was: relay it. If the number of speakers looks wrong, for example a speaker with only a few
seconds of speech or fewer speakers than the person expects, propose transcribing again with
`--speakers N`. When `warnings` is not empty, the transcription ran on the CPU: tell the person
why. Read `transcript_txt` for the content. Minutes, summaries and action items are your own work
on that text.

### Show who spoke, every time

After every transcription, show the person who spoke: one bullet per speaker, longest first, with
the name in bold and the minutes of speech from `speech_sec`, recognized names and "Persona N"
alike. Leave out "Voce non attribuita": it holds words no speaker could be given. Then ask whether
the names are right. For example:

> In questa registrazione hanno parlato:
> - **Luca Bianchi**: 15 min
> - **Persona 1**: 5 min
> - **Mario Rossi**: 3 min
>
> I nomi sono giusti?

Ask in your message, without answer buttons. A "yes", or no answer, changes nothing and adds no
clips. A name the person says is wrong is their request to correct it: follow
[Confirm or correct a recognized voice](#confirm-or-correct-a-recognized-voice-only-when-asked).
For "Persona N", propose names as below.

### Then

For a video, title its folder and keep its frames first, as
[A video: its folder and its frames](#a-video-its-folder-and-its-frames) says, then propose the
names. Then propose correcting the transcript's misheard words with the `fix-transcript` skill.
When speakers are left as "Persona N", propose it once naming is over instead: `name` rewrites the
`.txt` and would undo the corrections.

Never delete the recording, and never propose deleting it. A person who wants to keep only the
transcript and its frames gives the names first: naming reads the recording to cut voice clips, and
without it a name adds no clips.

For times inside a turn, for example to cut a video, read `transcript_json`. Each of its `turns` has
`segments`: one per sentence, split again where the speaker pauses for a second or more, each with
`start_sec`, `end_sec` and `text`. A gap between two segments is a pause. Use them instead of
running Whisper yourself. A transcript made by an older version has no `segments`, and no folder of
its own: transcribe the recording again with `trascrittore transcribe`.

When `status` is not `ok`, relay `message`. The statuses:

| status | what to do |
|---|---|
| `busy` | Another transcription is running on this PC. Wait for it to end, then retry. Never start two. |
| `file_not_found`, `unreadable_recording` | Check the path, and that the file is audio or video and on the PC. |
| `invalid_settings` | A line of `{{CARTELLA}}\trascrittore.ini` is wrong, and the message names it. Help the person correct or delete that line. |
| `docker_not_running` | Ask the person to open Docker Desktop and wait until it is ready. |
| `not_installed` | The person runs `Installa.bat` in `{{CARTELLA}}`. |
| `gpu_out_of_memory` | The message says how to lower `batch_size` in `{{CARTELLA}}\trascrittore.ini`. |

`{{CARTELLA}}\trascrittore.ini` holds only the settings the person changed, each under its section,
for example `batch_size = 4` under `[whisper]`. Everything else comes from the transcriber.

## A video: its folder and its frames

When the recording is a video, work in this order, without asking:

1. **Title the folder.** Rename the transcript's folder, `folder` in the summary, to the date of the
   recording followed by a short Italian title drawn from what was said, written the way the
   transcriber writes names: `2026-10-29-demo-prodotto-acme`. The date is when the video was
   recorded, from its file name or, failing that, its file's date. Rename only the folder, never the
   files inside it, and use the new paths from then on.
2. **Keep the frames.** A frame is kept for what it shows, not for when: something a speaker shows,
   such as a product, a service or a slide, or something on screen the transcript lacks, such as
   names, figures or a document, even if it stays there only a few seconds. Never keep two frames
   that show nearly the same image, and never keep one only because of its time. Find the
   candidates with everything you have:
   - the transcript, where speech refers to the screen ("come vedete qui", "in questa slide", a
     name being introduced);
   - the moments where the picture changes;
   - one frame every 20 seconds, or as often as the person asked for this recording, so that you
     see the screen where nothing is said about it and nothing changes.

   Look at the candidates small, in a temporary folder of your own: looking at a candidate does not
   keep it. Save each frame you keep at the video's full resolution in a `fotogrammi` folder inside
   the transcript's folder, named after its time from the start of the recording, such as
   `00-12-34.jpg`. Then delete the temporary folder. When nothing on screen is worth keeping, make
   no `fotogrammi` folder and say so.
3. **Propose names** for the speakers, using the names shown on screen too.

The transcript's files do not list the frames: do not add them there.

Use ffmpeg if the PC has it. Otherwise use the one in the transcriber's image, writing every folder
as a Windows path, such as `C:\Users\...` or `C:/Users/...`. From PowerShell:

```
# The moments where the picture changes: read the pts_time values it prints.
docker run --rm -v "<transcript folder>:/video:ro" --entrypoint ffmpeg trascrittore:latest -hide_banner -i "/video/<video file>" -vf "select='gt(scene,0.2)',showinfo" -an -f null -

# One small frame every 20 seconds: frame N is at second 20 x (N - 1).
docker run --rm -v "<transcript folder>:/video:ro" -v "<temporary folder>:/frames" --entrypoint ffmpeg trascrittore:latest -hide_banner -i "/video/<video file>" -vf "fps=1/20,scale=640:-2" /frames/sonda-%04d.jpg

# One small candidate at a given second.
docker run --rm -v "<transcript folder>:/video:ro" -v "<temporary folder>:/frames" --entrypoint ffmpeg trascrittore:latest -hide_banner -ss <second> -i "/video/<video file>" -frames:v 1 -vf "scale=640:-2" /frames/<second>.jpg

# A frame to keep, at full resolution: create the fotogrammi folder first.
docker run --rm -v "<transcript folder>:/video" --entrypoint ffmpeg trascrittore:latest -hide_banner -ss <second> -i "/video/<video file>" -frames:v 1 -q:v 2 /video/fotogrammi/00-12-34.jpg
```

On a screen recording, where slides change little, lower the scene threshold to `0.1` if it finds
few changes. From Git Bash, put `MSYS_NO_PATHCONV=1` in front of each line. Without it, Git Bash
rewrites `/video` and `/frames` into folders of its own, and ffmpeg finds no file. With it, a folder
written as `/c/Users/...` does not reach Docker as a Windows path either, so write the folders as
above. If ffmpeg cannot run, for example because Docker Desktop is not running, tell the person you
could not see the screen; the transcript and its folder stay as they are, apart from the title.

A video transcribed by an older version has no folder of its own: when the person asks for its
frames, propose transcribing it again. The names given earlier are not lost, since those voices are
in the voice library.

## Name the voices left as "Persona N"

Only the person gives a name. You may propose one from what a speaker said, for example when others
address them by name, or from a name on screen, but use it only after the person confirms it or
writes another. Naming a voice also adds it to this PC's voice library, so later recordings
recognize that person: a wrong name would teach the transcriber the wrong voice.

1. Propose names to the person, quoting the lines that suggest them. Naming is the answer you
   recommend: when you ask with answer buttons, the one that names the voices comes first and
   leaving them unnamed second. Naming still goes through the steps below.
2. For each name the person confirms, let them hear the voice first, one speaker at a time:

   ```
   trascrittore listen "<transcript.json>" "Persona 2" --open
   ```

   It opens, in the person's default player, one 10-second clip of that speaker: the best one.
   Clips opened together cannot be told apart, so `listen` takes one speaker only. Tell the person
   whose voice is playing and the name it would get, for example "this is Persona 2: is it Luca
   Bianchi?", and wait for the answer before playing the next speaker. Also give the name of the
   file that opened, the last part of the summary's `file`, such as
   `ascolta registrazione - Persona 2 - 1.wav`. Another session may open its own clip at the same
   time, and the player then plays only the last one, so the person checks that the player shows
   that file. You cannot judge a voice by ear. If the person is unsure, play the same speaker's
   next clip with `--clip 2`, then `--clip 3`; the summary's `clips` says how many there are. A
   speaker without any full clip is played from their longest stretch (`seconds`), which serves
   only to recognize the voice.
3. Only for the voices the person confirmed:

   ```
   trascrittore name "<transcript.json>" "Persona 2=Nome Cognome" ["Persona 3=Nome Cognome" ...]
   ```

   It rewrites both transcript files with the names, without transcribing again, and adds the
   speaker's clips to a pool, a folder of clips in `{{CARTELLA}}\voci\<Nome Cognome>`. It opens no
   window; the speaker's `folder` gives the path.

Which pool the clips go to (the Italian messages call a pool "gruppo"):

- A person new to the library starts with the pool `registrazioni`.
- A "Persona N" named after someone already in the library is a voice the transcriber missed,
  most likely because this recording sounds different: another microphone, room or call. Its clips
  start a new pool, a folder named after the transcript's folder, and the speaker's `note` says
  so: relay it. With only one or two clips, or once the person has 8 pools added by naming, they
  join the closest pool instead.
- The person may rename a pool, for example to `macchina`.

Also:

- If the person says the voice is not that person, do not name it.
- If `listen` found nothing to play, its `note` says why. The name can still be
  given; it only adds no clips.
- When the person is already in the library, use exactly the name of their folder in
  `{{CARTELLA}}\voci`. A name that differs from a folder only in case or spaces is changed to the
  folder's; the `note` of that speaker says so.
- If the recording has moved since the transcription, add `--recording "<new path>"` to `listen`
  and `name`.

`name` can end with two statuses that need the person's decision. Ask, then act:

| status | what happened | what to do |
|---|---|---|
| `similar_name` | A name looks like a person already in the library (listed in `similar`). Nothing was saved. | Ask whether they meant that person. Run `name` again with the folder's exact name, or, if it really is a new person, add `--new-person "Nome Cognome"`. |
| `over_cap` | The names are applied and the clips saved, but a pool now holds more than the cap. `over_cap` lists, for each `person` and `pool`, the clips proposed for removal. | Tell the person and ask. Only if they agree: `trascrittore remove-clips "Nome Cognome" "<clip.wav>" [...]` with the listed files. |

## Confirm or correct a recognized voice, only when asked

A voice the transcriber recognized keeps its name. Never propose to confirm or correct it: do it
only when the person asks, for example "vorrei aggiungere delle clip di Sebastiano", "quella non
era Luca, era Sebastiano", or by saying a name is wrong in the list of who spoke.

1. Let the person hear it, as above: `trascrittore listen "<transcript.json>" "Sebastiano Tomasi" --open`.
2. Only after they confirm the voice:
   - **the name is right, add clips**: `trascrittore name "<transcript.json>" --confirm "Sebastiano Tomasi"`.
     The clips join the person's pool that matches the voice best. The speaker's `note` says
     whether new clips help much (recognition was close to the threshold) or little; relay it.
   - **the name is wrong**: `trascrittore name "<transcript.json>" "Luca Bianchi=Sebastiano Tomasi" --correct`.
     The transcript takes the right name and the clips go to the right person, in a new pool when
     that person was already in the library. The `note` tells the person to listen to the wrong
     person's clips and delete those that are not theirs; relay it.
