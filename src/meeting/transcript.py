"""
Pure formatting for meeting transcripts: display labels, speaker summaries, text and JSON output.
"""

from __future__ import annotations

from typing import Any, Callable

from src.asr.utils.output_format import format_offset


UNKNOWN_DISPLAY_PREFIX = "Persona"
UNATTRIBUTED_LABEL = "UNKNOWN"
UNATTRIBUTED_DISPLAY = "Voce non attribuita"
_SAMPLE_TURNS = 2
_SAMPLE_MAX_CHARS = 160


def display_labels(turns: list[dict[str, Any]], unknown_prefix: str) -> dict[str, str]:
    """
    Map raw speaker labels to what the reader sees.

    Recognized names stay as they are; unrecognized voices become "Persona 1..N"
    in order of first appearance.
    """
    labels: dict[str, str] = {}
    unknown_count = 0
    for turn in turns:
        speaker = turn["speaker"]
        if speaker in labels:
            continue
        if speaker == UNATTRIBUTED_LABEL:
            labels[speaker] = UNATTRIBUTED_DISPLAY
        elif unknown_prefix and speaker.startswith(unknown_prefix):
            unknown_count += 1
            labels[speaker] = f"{UNKNOWN_DISPLAY_PREFIX} {unknown_count}"
        else:
            labels[speaker] = speaker
    return labels


def is_anonymous(display_label: str) -> bool:
    return display_label.startswith(f"{UNKNOWN_DISPLAY_PREFIX} ")


def participant_names(labels: dict[str, str]) -> list[str]:
    """
    Return the people in the meeting, in order of first appearance.

    Words the diarization gave to nobody are not a participant.
    """
    return [name for name in dict.fromkeys(labels.values()) if name != UNATTRIBUTED_DISPLAY]


def _speech_sec(turns: list[dict[str, Any]]) -> float:
    return sum(float(turn["end_sec"]) - float(turn["start_sec"]) for turn in turns)


def _rounded(value: Any) -> float | None:
    return round(float(value), 3) if value is not None else None


def speaker_summaries(
    turns: list[dict[str, Any]],
    labels: dict[str, str],
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Summarize each voice for the output file: who, how much they spoke, and how sure recognition was.

    Scores and margins let the team calibrate matching.threshold and matching.margin on real meetings.
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
            }
        )
    return summaries


def rename_labels(labels: dict[str, str], names: dict[str, str]) -> dict[str, str]:
    """
    Apply names typed by the user ("Persona 1" -> "Luca Bianchi") to the raw->display mapping.
    """
    return {raw_label: names.get(display, display) for raw_label, display in labels.items()}


def _format_minutes(seconds: float) -> str:
    minutes = round(seconds / 60)
    return f"{minutes} min" if minutes >= 1 else "<1 min"


def render_text(
    *,
    source_name: str,
    duration_sec: float,
    device: str,
    fallback_reason: str | None,
    turns: list[dict[str, Any]],
    labels: dict[str, str],
) -> str:
    """
    Render the human-readable transcript: a short header, then "[HH:MM:SS] Name: text" lines.
    """
    speech_by_display: dict[str, float] = {}
    for turn in turns:
        display = labels[turn["speaker"]]
        speech_by_display[display] = speech_by_display.get(display, 0.0) + _speech_sec([turn])
    participants = ", ".join(
        f"{name} ({_format_minutes(speech_by_display[name])})" for name in participant_names(labels)
    )

    lines = [
        f"Trascrizione di: {source_name}",
        f"Durata: {format_offset(duration_sec)} · Elaborata su {'GPU' if device.startswith('cuda') else 'CPU'}",
        f"Partecipanti: {participants or 'nessuno'}",
    ]
    if fallback_reason:
        lines.append(f"ATTENZIONE: elaborata su CPU invece che su GPU. {fallback_reason}")
    lines.append("")
    if not turns:
        lines.append("(Nell'audio non è stato trovato parlato.)")
    for turn in turns:
        lines.append(f"[{format_offset(turn['start_sec'])}] {labels[turn['speaker']]}: {turn['text']}")
        lines.append("")
    return "\n".join(lines)


def build_payload(
    *,
    source_name: str,
    duration_sec: float,
    device: str,
    compute_type: str,
    fallback_reason: str | None,
    elapsed_sec: float,
    turns: list[dict[str, Any]],
    labels: dict[str, str],
    speakers: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build the machine-readable transcript saved next to the text file.
    """
    return {
        "file": source_name,
        "duration_sec": round(duration_sec, 1),
        "device": device,
        "compute_type": compute_type,
        "warnings": [f"Elaborata su CPU invece che su GPU. {fallback_reason}"] if fallback_reason else [],
        "elapsed_sec": round(elapsed_sec, 1),
        "speakers": speakers,
        "turns": [
            {
                "speaker": labels[turn["speaker"]],
                "start": format_offset(turn["start_sec"]),
                "start_sec": turn["start_sec"],
                "end_sec": turn["end_sec"],
                "text": turn["text"],
            }
            for turn in turns
        ],
    }


def _sample_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    longest = sorted(turns, key=lambda turn: len(turn["text"].split()), reverse=True)[:_SAMPLE_TURNS]
    return sorted(longest, key=lambda turn: float(turn["start_sec"]))


def _clip(text: str) -> str:
    return text if len(text) <= _SAMPLE_MAX_CHARS else text[: _SAMPLE_MAX_CHARS - 1].rstrip() + "…"


def ask_names(
    turns: list[dict[str, Any]],
    labels: dict[str, str],
    *,
    input_fn: Callable[[str], str] | None = None,
    print_fn: Callable[[str], None] = print,
) -> dict[str, str]:
    """
    Ask a name for every anonymous voice, showing two of its longest turns as a reminder.

    Enter keeps "Persona N"; end of input stops asking. Names are used only for this transcript.
    """
    anonymous = [(raw, display) for raw, display in labels.items() if is_anonymous(display)]
    if not anonymous:
        return {}
    input_fn = input_fn or input

    print_fn("")
    print_fn("Alcune voci non sono state riconosciute.")
    print_fn("Scrivi il nome e premi Invio, oppure premi solo Invio per lasciare 'Persona N'.")
    names: dict[str, str] = {}
    for raw_label, display in anonymous:
        speaker_turns = [turn for turn in turns if turn["speaker"] == raw_label]
        print_fn("")
        print_fn(f"{display}: {len(speaker_turns)} interventi, {_format_minutes(_speech_sec(speaker_turns))} di parlato")
        for turn in _sample_turns(speaker_turns):
            print_fn(f"  [{format_offset(turn['start_sec'])}] \"{_clip(turn['text'])}\"")
        try:
            answer = input_fn(f"Nome per {display}: ").strip()
        except EOFError:
            break
        if answer:
            names[display] = answer
    return names
