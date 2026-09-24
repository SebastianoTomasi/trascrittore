---
name: trascrittore
description: Transcribe audio or video recordings (meetings, calls, OBS recordings) in Italian on this PC, with the names of who spoke, and give names to the voices left as "Persona N". Use when the user asks to transcribe a recording ("trascrivi questa registrazione"), who spoke in it, or to name the speakers of a transcript.
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
- Pass `--speakers N` only when the person knows the exact number of people who speak.
- The recording must be on the PC. A file that is only online in OneDrive or Google Drive must be
  downloaded first.
- The transcript's `.txt` and `.json` files appear next to the recording, or in `--out-dir`.

On success the summary gives `transcript_txt`, `transcript_json`, `duration_sec`, `elapsed_sec`,
`device`, `warnings`, and `speakers`: for each one its `label`, whether it was `recognized`, and
its `speech_sec`. When `warnings` is not empty, the transcription ran on the CPU: tell the person
why. Read `transcript_txt` for the content. Minutes, summaries and action items are your own work
on that text.

When `status` is not `ok`, relay `message`. The statuses:

| status | what to do |
|---|---|
| `busy` | Another transcription is running on this PC. Wait for it to end, then retry. Never start two. |
| `file_not_found`, `unreadable_audio` | Check the path, and that the file is audio or video and on the PC. |
| `docker_not_running` | Ask the person to open Docker Desktop and wait until it is ready. |
| `not_installed` | The person runs `Installa.bat` in `{{CARTELLA}}`. |
| `gpu_out_of_memory` | The message says how to lower `batch_size` in `{{CARTELLA}}\meeting.ini`. |

## Name the voices left as "Persona N"

Only the person gives a name. You may propose one from what a speaker said, for example when others
address them by name, but use it only after the person confirms it or writes another. Naming a voice
also adds it to this PC's voice library, so later recordings recognize that person: a wrong name
would teach the transcriber the wrong voice.

1. Propose names to the person, quoting the lines that suggest them.
2. For each name the person confirms, let them hear the voice first:

   ```
   trascrittore listen "<transcript.json>" "Persona 2" [...] --open
   ```

   It opens, in the person's default player, a short file with that speaker's best one or two
   clips. You cannot judge a voice by ear: ask the person whether it is really that person.
3. Only for the voices the person confirmed:

   ```
   trascrittore name "<transcript.json>" "Persona 2=Nome Cognome" ["Persona 3=Nome Cognome" ...]
   ```

   It rewrites both transcript files with the names, without transcribing again, and adds the
   speaker's clips to `{{CARTELLA}}\voci\<Nome Cognome>\registrazioni`.

- If the person says the voice is not that person, do not name it.
- If `listen` found no clip for a speaker, its `note` says why. The name can still be given; it
  only adds no clips.
- When the person is already in the library, use exactly the name of their folder in
  `{{CARTELLA}}\voci`, so one person never ends up in two folders. A name that differs from a
  folder only in case or spaces is changed to the folder's; the `note` of that speaker says so.
- Only "Persona N" voices can be named.
- If the recording has moved since the transcription, add `--recording "<new path>"` to `listen`
  and `name`.

During the trial period of the automatic clip selection, the summary of `name` asks the person to
listen to the added clips and delete the bad ones, those with other voices, laughter or noise.
Pass that request on.

## Check recognition and the trial

```
trascrittore check
trascrittore trial
```

Run them in this order, as `Verifica.bat` does, and suggest it after a few new names.

- `check` measures how well the voice library recognizes the voices a person named in this PC's
  transcripts, and suggests a threshold. It never changes `meeting.ini`: relay the suggestion, and
  let the person decide whether to change `threshold` in `{{CARTELLA}}\meeting.ini`.
- `trial` reports the trial of the automatic clip selection. When its summary has `"ready": true`,
  ask the person whether they listened to every clip added to the library and deleted the bad ones.
  Only if they say yes, run `trascrittore trial --reviewed`: from then on the selection discards
  the worst clips by itself. If it lists `disagreements`, the selection kept clips the person
  deleted; tell them to report it to whoever gave them the transcriber.
