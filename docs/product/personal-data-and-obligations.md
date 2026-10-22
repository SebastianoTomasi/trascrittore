# Personal data and external obligations

**Status:** accepted

## Scope

This artifact lists the classes of data the transcriber handles, which of them
are personal, where each one lives and how long it stays, and the external
obligations that bind the transcriber. The parties, the promise that processing
stays on the PC and the absence of any use policy are in
[the promise](transcriber-promise.md). How the data is stored belongs to
Architecture, and how it is protected to Security.

## Dependencies

- [Processing stays on the PC](transcriber-promise.md#processing-stays-on-the-pc)
  — every class below is read and written on the PC, and the transcriber sends
  none of them anywhere.
- [No use policy](transcriber-promise.md#no-use-policy) — no class carries a
  consent or retention rule, and where the person's files end up is the
  person's choice.
- [One voice library per PC](transcriber-promise.md#one-voice-library-per-pc)
  — voice clips and voiceprints exist on each PC separately, never in a shared
  place.

## Data classes

Every class except the settings is personal: it holds the
voice or the words of identifiable people, or says in which recordings they
spoke.

| Class | What it holds | Where it lives | How long it stays |
| --- | --- | --- | --- |
| Recording | The voices and words of its speakers. | Wherever the person keeps it. | The transcriber only reads it: it never moves, changes or deletes it. |
| Transcript | What each speaker said and when, under a recognized or given name, or as "Persona N". The JSON file also holds, for each speaker, how sure recognition was, including the closest person in the voice library even when that person was not recognized. | Next to the recording, or in the folder the person chooses. | As long as the person keeps it. |
| Voice clip | The voice of one identifiable person, from which the transcriber learns to recognize them. | In the voice library, inside the transcriber's folder. | Until someone removes it. A clip added by naming may also be removed by the transcriber when the person confirms its proposal to keep that person under the cap on added clips. |
| Clip record | For each clip added by naming a speaker: the recording and the transcript it came from, with their paths on the PC, the speaker's label in that transcript, the times of the clip and how much it resembles the rest of the speaker's voice. | In the voice library, in the named person's folder. | Until someone removes it, at the latest with that person's folder. The entry of a clip the person deleted stays, because the recognition check finds the named transcripts through the entries. |
| Voiceprint | What the transcriber derives from a person's voice clips to recognize their voice: biometric data. | In a cache on the PC, outside the voice library. | Recomputed when that person's clips change; no longer used once the person leaves the library. |
| Listening file | One speaker's voice: one of their best clips from a recording, or their longest stretch of speech when they have no full clip, which the person hears before naming them. | In the transcriber's data folder on the PC, outside the voice library. | Until the naming ends or the next listening starts. A file still open in the player is deleted the time after. |
| Working files | A 16 kHz copy of the recording and the intermediate steps of one run. | Inside the container of that run. | Deleted when the run ends. |
| Settings | Recognition thresholds and processing options. Not personal. | The person's changes in `trascrittore.ini`, next to the transcriber's scripts; everything else inside the transcriber. | The person's changes stay until they change them; the rest can change with any update. |

## Where the files end up

The person's files — recordings, transcripts and the voice library — stay
wherever the person puts them. If that place is synchronized with a cloud
service, for example a `Documenti` folder backed up by OneDrive, they follow it:
that is the person's choice, as [No use policy](transcriber-promise.md#no-use-policy)
says. The clip records sit in the voice library, so they follow it too. The transcriber itself places only its internal data:
voiceprints, listening files and working files.

Removing a person's folder from the voice library is enough for the transcriber
to stop recognizing them from the next run, and it removes their clip records
with it.

## External obligations

### Toward the people recorded or recognized

The transcriber takes on none. It is a personal, non-commercial tool with no
use policy, so whoever uses it answers for the obligations of that use, for
example data protection rules when it is used for work, as
[ADR 0002](../adr/0002-personal-tool-without-use-policy.md) records. The same
holds for Docker Desktop: it is free for personal use, and a subscription that
a larger company requires is a matter for whoever uses it there.

### Licenses of the models it carries

The maintainer redistributes these models inside the image. Their licenses
require crediting the authors and including the license text; the Punkt
models come with no stated license:

| Model | Role | License |
| --- | --- | --- |
| Whisper large-v3, faster-whisper conversion (`Systran/faster-whisper-large-v3`) | Transcription | MIT |
| `jonatasgrosman/wav2vec2-large-xlsr-53-italian` | Word alignment | Apache-2.0 |
| `pyannote/speaker-diarization-community-1` | Telling voices apart | CC-BY-4.0 |
| `pyannote/embedding` | Voiceprints | MIT |
| `pyannote/segmentation`, inside WhisperX | Finding where people speak | MIT |
| NLTK Punkt tokenizer models (`punkt_tab`) | Splitting the text into sentences | None stated |

Every distribution therefore includes a file with the credits and license texts
of the models it carries, and a model that is added or replaced joins that file
in the same release. The licenses above were checked on the models' Hugging
Face pages on 2026-09-24, and on 2026-09-25 for `pyannote/segmentation` and,
in the NLTK data index, for the Punkt models.
