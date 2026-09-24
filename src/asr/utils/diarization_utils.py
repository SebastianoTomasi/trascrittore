from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd
import soundfile as sf
import whisperx
from pyannote.core import Segment

from src.asr.utils.config import get_matching_settings, get_speaker_settings
from src.asr.embeddings import embed_audio_waveform, normalize_embed


_matching_settings = get_matching_settings()
_speaker_settings = get_speaker_settings()

MATCHING_THRESHOLD_DEFAULT = _matching_settings.threshold
MATCHING_MARGIN_DEFAULT = _matching_settings.margin
WINDOW_SEC_DEFAULT = _matching_settings.window_sec
MIN_WINDOW_SEC_DEFAULT = _matching_settings.min_window_sec
MIN_TOTAL_SPEECH_SEC_DEFAULT = _matching_settings.min_total_speech_sec
MAX_WINDOWS_PER_SPK_DEFAULT = _matching_settings.max_windows_per_spk
UNKNOWN_PREFIX_DEFAULT = _speaker_settings.unknown_prefix


@dataclass(frozen=True)
class SpeakerEmbeddingDiagnosticsResult:
    embeddings: Dict[str, List[np.ndarray]]
    diagnostics: Dict[str, Any]


@dataclass(frozen=True)
class SpeakerMatchDiagnosticsResult:
    mapping: Dict[str, str]
    diagnostics: Dict[str, Any]


def diarization_to_dataframe(diarization_output: Any) -> pd.DataFrame:
    """
    Normalize WhisperX/pyannote diarization outputs into a DataFrame with columns:
      start, end, speaker
    """
    # Audio without speech yields no segments, saved as an empty list.
    if diarization_output is None or (isinstance(diarization_output, (list, tuple)) and not diarization_output):
        return pd.DataFrame(columns=["start", "end", "speaker"])

    if isinstance(diarization_output, pd.DataFrame):
        df = diarization_output.copy()
    elif hasattr(diarization_output, "itertracks"):
        rows = []
        for seg, _, label in diarization_output.itertracks(yield_label=True):
            rows.append({"start": float(seg.start), "end": float(seg.end), "speaker": str(label)})
        df = pd.DataFrame(rows, columns=["start", "end", "speaker"])
    elif isinstance(diarization_output, (list, tuple)):
        df = pd.DataFrame(list(diarization_output))
    else:
        raise TypeError(f"Unsupported diarization output type: {type(diarization_output)}")

    colmap = {c.lower(): c for c in df.columns}
    if "speaker" not in df.columns and "label" in colmap:
        df = df.rename(columns={colmap["label"]: "speaker"})

    for req in ["start", "end", "speaker"]:
        if req not in df.columns:
            raise ValueError(f"Diarization DataFrame missing required column '{req}'. Columns={list(df.columns)}")

    df["start"] = df["start"].astype(float)
    df["end"] = df["end"].astype(float)
    df["speaker"] = df["speaker"].astype(str)
    return df[df["end"] > df["start"]].reset_index(drop=True)


def _merge_intervals(intervals: List[tuple[float, float]]) -> List[tuple[float, float]]:
    merged: List[tuple[float, float]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _subtract_intervals(
    start: float,
    end: float,
    blockers: List[tuple[float, float]],
) -> List[tuple[float, float]]:
    """
    Return the parts of [start, end) not covered by sorted, non-overlapping `blockers`.
    """
    parts: List[tuple[float, float]] = []
    cursor = start
    for block_start, block_end in blockers:
        if block_end <= cursor:
            continue
        if block_start >= end:
            break
        if block_start > cursor:
            parts.append((cursor, block_start))
        cursor = max(cursor, block_end)
    if cursor < end:
        parts.append((cursor, end))
    return parts


def _exclusive_speaker_segments(diarize_df: pd.DataFrame) -> Dict[str, List[Segment]]:
    """
    Return each speaker's segments without the stretches where another speaker also talks.

    Overlapped speech mixes two voices, so embedding it would pull a speaker's voiceprint
    toward whoever talks over them. Every speaker keeps a key, even with no speech left.
    """
    intervals_by_spk: Dict[str, List[tuple[float, float]]] = {}
    for _, row in diarize_df.iterrows():
        intervals_by_spk.setdefault(str(row["speaker"]), []).append((float(row["start"]), float(row["end"])))

    exclusive: Dict[str, List[Segment]] = {}
    for spk, intervals in intervals_by_spk.items():
        others = _merge_intervals(
            [interval for other, other_intervals in intervals_by_spk.items() if other != spk for interval in other_intervals]
        )
        exclusive[spk] = [
            Segment(part_start, part_end)
            for start, end in intervals
            for part_start, part_end in _subtract_intervals(start, end, others)
        ]
    return exclusive


def _split_segment_into_windows(seg: Segment, window_sec: float, min_window_sec: float) -> List[Segment]:
    duration = seg.end - seg.start
    if duration < min_window_sec:
        return []
    if duration <= window_sec:
        return [seg]

    windows: List[Segment] = []
    cursor = seg.start
    while cursor < seg.end:
        end = min(cursor + window_sec, seg.end)
        if (end - cursor) >= min_window_sec:
            windows.append(Segment(cursor, end))
        cursor = end
    return windows


def _sample_longest_per_bucket(windows: List[Segment], max_windows: int) -> List[Segment]:
    """
    Select a deterministic subset that spans the whole recording and favors long windows.

    Time-ordered candidates are split into `max_windows` buckets of consecutive windows
    with near-equal counts, and the longest window of each bucket is kept, since longer
    windows give more stable embeddings. Ties go to the window nearest the bucket center.
    """
    if max_windows <= 0:
        return []
    if len(windows) <= max_windows:
        return list(windows)

    selected: List[Segment] = []
    for bucket in range(max_windows):
        lo = bucket * len(windows) // max_windows
        hi = (bucket + 1) * len(windows) // max_windows
        center = (lo + hi - 1) / 2
        # Round durations so float noise from window splitting does not break ties.
        best = max(range(lo, hi), key=lambda i: (round(windows[i].duration, 3), -abs(i - center)))
        selected.append(windows[best])
    return selected


def _segment_record(start: float, end: float, speaker: str | None = None) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "start": float(start),
        "end": float(end),
        "duration_sec": float(end - start),
    }
    if speaker is not None:
        record["speaker"] = speaker
    return record


def _save_window_clip(
    full_audio: np.ndarray,
    window: Segment,
    clip_path: str | None,
    sample_rate: int,
) -> str | None:
    if not clip_path:
        return None

    n = len(full_audio)
    start_i = max(0, min(n, int(round(window.start * sample_rate))))
    end_i = max(0, min(n, int(round(window.end * sample_rate))))
    if end_i <= start_i:
        return None

    out_dir = os.path.dirname(clip_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    sf.write(clip_path, full_audio[start_i:end_i].astype(np.float32, copy=False), sample_rate)
    return clip_path


def speaker_embeddings_from_diarization_with_diagnostics(
    emb_model,
    audio_path: str,
    diarize_segments: Any,
    device: str,
    window_sec: float = WINDOW_SEC_DEFAULT,
    min_window_sec: float = MIN_WINDOW_SEC_DEFAULT,
    min_total_speech_sec: float = MIN_TOTAL_SPEECH_SEC_DEFAULT,
    max_windows_per_spk: int = MAX_WINDOWS_PER_SPK_DEFAULT,
    diagnostics_clip_path_factory: Callable[[int, str, float], str] | None = None,
    sample_rate: int = 16000,
) -> SpeakerEmbeddingDiagnosticsResult:
    """
    Build normalized fixed-window embeddings and diagnostics for each diarized speaker.

    Windows cover only speech where no other speaker overlaps. When a speaker has more
    candidate windows than `max_windows_per_spk`, only the longest window of each bucket
    of consecutive windows is embedded. Without `emb_model`, as when the voice library is
    empty, the windows are still recorded, because naming a speaker later cuts clips from them.
    """
    diarize_df = diarization_to_dataframe(diarize_segments)
    diagnostics: Dict[str, Any] = {"speakers": {}}
    if diarize_df.empty:
        return SpeakerEmbeddingDiagnosticsResult({}, diagnostics)
    full_audio = whisperx.load_audio(audio_path) if emb_model is not None else None

    speech_sec_by_spk: Dict[str, float] = {}
    for _, row in diarize_df.iterrows():
        spk = str(row["speaker"])
        speech_sec_by_spk[spk] = speech_sec_by_spk.get(spk, 0.0) + float(row["end"] - row["start"])

    exclusive_by_spk = _exclusive_speaker_segments(diarize_df)
    by_spk: Dict[str, List[Segment]] = {
        spk: [
            window
            for seg in segments
            for window in _split_segment_into_windows(seg, window_sec, min_window_sec)
        ]
        for spk, segments in exclusive_by_spk.items()
    }

    spk_embeddings: Dict[str, List[np.ndarray]] = {}
    clip_index = 1
    for spk, windows in by_spk.items():
        embeds = []
        accepted_duration = 0.0
        attempted_windows = _sample_longest_per_bucket(windows, max_windows_per_spk)
        exclusive_sec = sum(seg.duration for seg in exclusive_by_spk[spk])
        speaker_diag: Dict[str, Any] = {
            "overlap_excluded_sec": round(speech_sec_by_spk[spk] - exclusive_sec, 3),
            "candidate_window_count": len(windows),
            "sampled_window_count": len(attempted_windows),
            "sampling_strategy": "all" if len(windows) <= max_windows_per_spk else "longest_per_bucket",
            "windows": [],
            "accepted_duration_sec": 0.0,
            "embedding_count": 0,
            "eligible_for_matching": False,
            "embedding_rejection_reason": None,
        }
        for window_index, window in enumerate(attempted_windows, start=1):
            duration_sec = float(window.end - window.start)
            window_diag = _segment_record(window.start, window.end)
            window_diag["index"] = clip_index
            window_diag["clip_path"] = None
            window_diag["clip_error"] = None
            window_diag["embedding_status"] = "pending"

            if emb_model is None:
                window_diag["embedding_status"] = "not_embedded"
                speaker_diag["windows"].append(window_diag)
                clip_index += 1
                continue

            try:
                clip_path = (
                    diagnostics_clip_path_factory(clip_index, spk, duration_sec)
                    if diagnostics_clip_path_factory
                    else None
                )
                window_diag["clip_path"] = _save_window_clip(
                    full_audio,
                    window,
                    clip_path,
                    sample_rate,
                )
            except Exception as exc:  # pragma: no cover - filesystem/codec dependent
                window_diag["clip_error"] = f"{type(exc).__name__}: {exc}"

            try:
                embeds.append(
                    normalize_embed(
                        embed_audio_waveform(
                            emb_model,
                            full_audio,
                            device=device,
                            crop=window,
                            min_duration_sec=min_window_sec,
                        )
                    )
                )
                accepted_duration += window.end - window.start
                window_diag["embedding_status"] = "embedded"
            except (RuntimeError, ValueError) as exc:
                # Skip invalid or numerically unstable crops and continue with other windows.
                window_diag["embedding_status"] = "skipped"
                window_diag["embedding_error"] = f"{type(exc).__name__}: {exc}"

            speaker_diag["windows"].append(window_diag)
            clip_index += 1

        speaker_diag["accepted_duration_sec"] = float(accepted_duration)
        speaker_diag["embedding_count"] = len(embeds)
        if embeds and accepted_duration >= min_total_speech_sec:
            spk_embeddings[spk] = embeds
            speaker_diag["eligible_for_matching"] = True
        elif emb_model is None and attempted_windows:
            speaker_diag["embedding_rejection_reason"] = "enrollment_not_configured"
        elif not embeds:
            speaker_diag["embedding_rejection_reason"] = "no_embedding_windows"
        else:
            speaker_diag["embedding_rejection_reason"] = "min_total_speech_not_met"

        diagnostics["speakers"][spk] = speaker_diag

    return SpeakerEmbeddingDiagnosticsResult(spk_embeddings, diagnostics)


def speaker_embeddings_from_diarization(
    emb_model,
    audio_path: str,
    diarize_segments: Any,
    device: str,
    window_sec: float = WINDOW_SEC_DEFAULT,
    min_window_sec: float = MIN_WINDOW_SEC_DEFAULT,
    min_total_speech_sec: float = MIN_TOTAL_SPEECH_SEC_DEFAULT,
    max_windows_per_spk: int = MAX_WINDOWS_PER_SPK_DEFAULT,
) -> Dict[str, List[np.ndarray]]:
    """
    Build normalized fixed-window embeddings for each diarized speaker.
    """
    return speaker_embeddings_from_diarization_with_diagnostics(
        emb_model,
        audio_path,
        diarize_segments,
        device=device,
        window_sec=window_sec,
        min_window_sec=min_window_sec,
        min_total_speech_sec=min_total_speech_sec,
        max_windows_per_spk=max_windows_per_spk,
    ).embeddings


def _person_match_score(spk_embeds: List[np.ndarray], enroll_embeds: List[np.ndarray]) -> float:
    scores = [
        float(np.dot(spk_emb, enroll_emb))
        for spk_emb in spk_embeds
        for enroll_emb in enroll_embeds
    ]
    return max(scores, default=-1.0)


def match_speakers_to_names(
    spk_embeddings: Dict[str, List[np.ndarray]],
    enroll_db: Dict[str, List[np.ndarray]],
    threshold: float = MATCHING_THRESHOLD_DEFAULT,
    margin: float = MATCHING_MARGIN_DEFAULT,
) -> Dict[str, str]:
    """
    Map each diarized speaker id to the best known enrollment name or unknown label.
    """
    return match_speakers_to_names_with_diagnostics(
        spk_embeddings,
        enroll_db,
        threshold=threshold,
        margin=margin,
    ).mapping


def match_speakers_to_names_with_diagnostics(
    spk_embeddings: Dict[str, List[np.ndarray]],
    enroll_db: Dict[str, List[np.ndarray]],
    threshold: float = MATCHING_THRESHOLD_DEFAULT,
    margin: float = MATCHING_MARGIN_DEFAULT,
    diarized_speakers: List[str] | None = None,
    embedding_rejection_reasons: Dict[str, str] | None = None,
) -> SpeakerMatchDiagnosticsResult:
    """
    Map diarized speaker ids to enrolled names and return score/rejection diagnostics.
    """
    mapping: Dict[str, str] = {}
    embedding_rejection_reasons = embedding_rejection_reasons or {}
    speaker_order = list(diarized_speakers or spk_embeddings.keys())
    for spk in spk_embeddings:
        if spk not in speaker_order:
            speaker_order.append(spk)
    diagnostics: Dict[str, Any] = {"speakers": {}}
    assignment_candidates: List[Dict[str, Any]] = []

    for speaker_index, spk in enumerate(speaker_order):
        embeds = spk_embeddings.get(spk, [])
        best_name = None
        best_score = -1.0
        second_name = None
        second_score = -1.0
        scores_by_speaker: Dict[str, float] = {}
        mapping[spk] = f"{UNKNOWN_PREFIX_DEFAULT}{spk}"

        if not embeds:
            rejection_reason = embedding_rejection_reasons.get(spk, "no_embedding_windows")
        else:
            for name, refs in enroll_db.items():
                if not refs:
                    continue
                score = _person_match_score(embeds, refs)
                scores_by_speaker[name] = score
                if score > best_score:
                    second_score = best_score
                    second_name = best_name
                    best_score = score
                    best_name = name
                elif score > second_score:
                    second_score = score
                    second_name = name

            score_margin = best_score - second_score
            if best_name is None:
                rejection_reason = "no_enrollment_refs"
            elif best_score < threshold:
                rejection_reason = "below_threshold"
            elif score_margin < margin:
                rejection_reason = "below_margin"
            else:
                rejection_reason = "pending_unique_assignment"
                assignment_candidates.append(
                    {
                        "speaker": spk,
                        "speaker_index": speaker_index,
                        "name": best_name,
                        "score": best_score,
                    }
                )

        diagnostics["speakers"][spk] = {
            "scores": scores_by_speaker,
            "best_name": best_name,
            "best_score": best_score,
            "second_best_name": second_name,
            "second_best_score": second_score,
            "score_margin": best_score - second_score,
            "assigned_label": mapping[spk],
            "rejection_reason": rejection_reason,
        }

    assigned_names = set()
    assignment_candidates.sort(
        key=lambda candidate: (
            -candidate["score"],
            candidate["speaker_index"],
            candidate["speaker"],
            candidate["name"],
        )
    )
    for candidate in assignment_candidates:
        spk = candidate["speaker"]
        name = candidate["name"]
        speaker_diag = diagnostics["speakers"][spk]
        if name in assigned_names:
            speaker_diag["rejection_reason"] = "known_person_already_assigned_to_better_match"
            continue

        mapping[spk] = name
        assigned_names.add(name)
        speaker_diag["assigned_label"] = name
        speaker_diag["rejection_reason"] = "accepted"

    return SpeakerMatchDiagnosticsResult(mapping, diagnostics)


def relabel_whisperx_segments(result: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Rewrite WhisperX speaker ids with final human-readable speaker labels.
    """
    for seg in result.get("segments", []):
        spk = seg.get("speaker")
        if spk in mapping:
            seg["speaker"] = mapping[spk]
        for word in seg.get("words", []):
            word_spk = word.get("speaker")
            if word_spk in mapping:
                word["speaker"] = mapping[word_spk]
    return result

