"""
Pure formatting for transcripts: display labels, speaker summaries, text and JSON output, renaming.
"""

from __future__ import annotations

from typing import Any

from src.asr.utils.output_format import format_offset


# A transcript's files are "<name>-trascrizione.txt" and "<name>-trascrizione.json".
TRANSCRIPT_SUFFIX = "-trascrizione"
ANONYMOUS_DISPLAY_PREFIX = "Persona"
UNATTRIBUTED_LABEL = "UNATTRIBUTED"
UNATTRIBUTED_DISPLAY = "Voce non attribuita"
_CPU_WARNING_PREFIX = "Elaborata su CPU invece che su GPU. "
# Windows whose voiceprint was, or could have been, computed to recognize a speaker; "skipped" ones failed.
_USABLE_WINDOW_STATUSES = {"computed", "not_computed"}


def display_labels(turns: list[dict[str, Any]], anonymous_prefix: str) -> dict[str, str]:
    """
    Map raw speaker labels to what the reader sees.

    Recognized names stay as they are; unrecognized voices become "Persona 1..N"
    in order of first appearance.
    """
    labels: dict[str, str] = {}
    anonymous_count = 0
    for turn in turns:
        speaker = turn["speaker"]
        if speaker in labels:
            continue
        if speaker == UNATTRIBUTED_LABEL:
            labels[speaker] = UNATTRIBUTED_DISPLAY
        elif anonymous_prefix and speaker.startswith(anonymous_prefix):
            anonymous_count += 1
            labels[speaker] = f"{ANONYMOUS_DISPLAY_PREFIX} {anonymous_count}"
        else:
            labels[speaker] = speaker
    return labels


def is_anonymous(display_label: str) -> bool:
    return display_label.startswith(f"{ANONYMOUS_DISPLAY_PREFIX} ")


def speaker_names(labels: dict[str, str]) -> list[str]:
    """
    Return the speakers of the recording, in order of first appearance.

    Words the diarization gave to nobody are not a speaker.
    """
    return [name for name in dict.fromkeys(labels.values()) if name != UNATTRIBUTED_DISPLAY]


def _speech_sec(turns: list[dict[str, Any]]) -> float:
    return sum(float(turn["end_sec"]) - float(turn["start_sec"]) for turn in turns)


def _rounded(value: Any) -> float | None:
    return round(float(value), 3) if value is not None else None


def _windows(speaker_diag: dict[str, Any]) -> list[dict[str, float]]:
    return [
        {"start": round(float(window["start"]), 3), "end": round(float(window["end"]), 3)}
        for window in speaker_diag.get("windows", [])
        if window.get("voiceprint_status") in _USABLE_WINDOW_STATUSES
    ]


def speaker_summaries(
    turns: list[dict[str, Any]],
    labels: dict[str, str],
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Summarize each voice for the output file: who, how much they spoke, and how sure recognition was.

    Scores and margins let the maintainer calibrate matching.threshold and matching.margin on real
    recordings. The windows are the stretches used to recognize the voice, from which naming a
    speaker later cuts voice clips.
    """
    diag_by_label = {
        speaker_diag.get("assigned_label"): speaker_diag
        for speaker_diag in diagnostics.get("speakers", {}).values()
    }
    summaries = []
    for raw_label, display in labels.items():
        speaker_turns = [turn for turn in turns if turn["speaker"] == raw_label]
        speaker_diag = diag_by_label.get(raw_label, {})
        best_name = speaker_diag.get("best_name")
        summaries.append(
            {
                "label": display,
                "recognized": speaker_diag.get("rejection_reason") == "accepted",
                "turn_count": len(speaker_turns),
                "speech_sec": round(_speech_sec(speaker_turns), 1),
                "best_match": best_name,
                "score": _rounded(speaker_diag.get("best_score")) if best_name else None,
                "second_match": speaker_diag.get("second_best_name"),
                "margin": _rounded(speaker_diag.get("score_margin")) if speaker_diag.get("second_best_name") else None,
                "reason": speaker_diag.get("rejection_reason"),
                "windows": _windows(speaker_diag),
            }
        )
    return summaries


def format_minutes(seconds: float) -> str:
    minutes = round(seconds / 60)
    return f"{minutes} min" if minutes >= 1 else "<1 min"


def render_text(
    *,
    source_name: str,
    duration_sec: float,
    device: str,
    warnings: list[str],
    turns: list[dict[str, Any]],
    labels: dict[str, str],
) -> str:
    """
    Render the human-readable transcript: a short header with any warnings, then "[HH:MM:SS] Name: text" lines.
    """
    speech_by_display: dict[str, float] = {}
    for turn in turns:
        display = labels[turn["speaker"]]
        speech_by_display[display] = speech_by_display.get(display, 0.0) + _speech_sec([turn])
    speakers = ", ".join(
        f"{name} ({format_minutes(speech_by_display[name])})" for name in speaker_names(labels)
    )

    lines = [
        f"Trascrizione di: {source_name}",
        f"Durata: {format_offset(duration_sec)} · Elaborata su {'GPU' if device.startswith('cuda') else 'CPU'}",
        f"Chi parla: {speakers or 'nessuno'}",
    ]
    for warning in warnings:
        # Each warning is a sentence of its own in the JSON file; here it goes on after "ATTENZIONE:".
        lines.append(f"ATTENZIONE: {warning[:1].lower()}{warning[1:]}")
    lines.append("")
    if not turns:
        lines.append("(Nella registrazione non è stato trovato parlato.)")
    for turn in turns:
        lines.append(f"[{format_offset(turn['start_sec'])}] {labels[turn['speaker']]}: {turn['text']}")
        lines.append("")
    return "\n".join(lines)


def _unaligned_warning(unaligned: list[dict[str, float]]) -> str:
    stretches = ", ".join(
        f"{format_offset(stretch['start_sec'])}–{format_offset(stretch['end_sec'])}" for stretch in unaligned
    )
    return (
        "In alcuni tratti il parlato non si è potuto allineare parola per parola, "
        f"e orari e chi parla sono approssimativi: {stretches}."
    )


def _warnings(fallback_reason: str | None, unaligned: list[dict[str, float]]) -> list[str]:
    warnings = [f"{_CPU_WARNING_PREFIX}{fallback_reason}"] if fallback_reason else []
    if unaligned:
        warnings.append(_unaligned_warning(unaligned))
    return warnings


def build_payload(
    *,
    source_name: str,
    recording: str,
    duration_sec: float,
    device: str,
    compute_type: str,
    fallback_reason: str | None,
    unaligned: list[dict[str, float]],
    elapsed_sec: float,
    turns: list[dict[str, Any]],
    labels: dict[str, str],
    speakers: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build the machine-readable transcript saved next to the text file.

    `unaligned` holds the stretches whose speech whisperX could not align word by word.
    """
    return {
        "file": source_name,
        "recording": recording,
        "duration_sec": round(duration_sec, 1),
        "device": device,
        "compute_type": compute_type,
        "warnings": _warnings(fallback_reason, unaligned),
        "elapsed_sec": round(elapsed_sec, 1),
        "speakers": speakers,
        "turns": [
            {
                "speaker": labels[turn["speaker"]],
                "start": format_offset(turn["start_sec"]),
                "start_sec": turn["start_sec"],
                "end_sec": turn["end_sec"],
                "text": turn["text"],
                "segments": turn["segments"],
            }
            for turn in turns
        ],
    }


def render_payload_text(payload: dict[str, Any]) -> str:
    """
    Render the text transcript from its JSON payload, so both files always agree.
    """
    turns = payload["turns"]
    return render_text(
        source_name=payload["file"],
        duration_sec=float(payload["duration_sec"]),
        device=payload["device"],
        warnings=payload["warnings"],
        turns=turns,
        labels={turn["speaker"]: turn["speaker"] for turn in turns},
    )


def speaker_labels(payload: dict[str, Any]) -> list[str]:
    """
    Return the displayed speaker labels of a transcript, in order of first appearance.
    """
    labels = [speaker["label"] for speaker in payload.get("speakers", [])]
    labels += [turn["speaker"] for turn in payload.get("turns", [])]
    return list(dict.fromkeys(labels))


def rename_speakers(payload: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    """
    Return a copy of the transcript payload with displayed labels replaced ("Persona 2" -> "Luca Bianchi").

    Renamed speakers are marked "named": a person gave that name, unlike a recognized one.
    Everything else stays as it was.
    """
    renamed = dict(payload)
    renamed["speakers"] = [
        {**speaker, "label": names[speaker["label"]], "named": True} if speaker["label"] in names else speaker
        for speaker in payload.get("speakers", [])
    ]
    renamed["turns"] = [
        {**turn, "speaker": names.get(turn["speaker"], turn["speaker"])} for turn in payload.get("turns", [])
    ]
    return renamed
