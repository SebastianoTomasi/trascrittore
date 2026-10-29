from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import src.asr.diarization as diarization

LOOP = "E lui " + "pa" * 220
RECOVERED = "E lui pa pa pa pa pa itera itera itera allunga allunga allunga allunga fino a che non arriva alla fine."
SPEECH = "Quindi adesso la chat sembra che abbia memoria, e ce l'ha, diciamo, in un certo modo."


class FakeWhisper:
    """
    The loaded faster-whisper model: its sequential decoding returns the texts it is given, in order.
    """

    def __init__(self, *texts: str):
        self.texts = list(texts)
        self.windows: list[tuple[float, dict[str, object]]] = []

    def transcribe(self, audio, **options):
        self.windows.append((len(audio) / 16000, options))
        return iter([SimpleNamespace(text=f" {self.texts.pop(0)}")]), None


def _pipeline(*texts: str) -> SimpleNamespace:
    options = SimpleNamespace(
        beam_size=5,
        temperatures=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
        initial_prompt="Registrazione in italiano.",
        suppress_tokens=[-1],
    )
    return SimpleNamespace(options=options, model=FakeWhisper(*texts))


def _segments() -> list[dict[str, object]]:
    return [
        {"text": SPEECH, "start": 0.0, "end": 20.0},
        {"text": LOOP, "start": 381.2, "end": 418.0},
    ]


AUDIO = np.zeros(16000 * 420, dtype=np.float32)


def test_a_looping_window_is_decoded_again_on_its_own_and_its_text_replaced():
    pipeline = _pipeline(RECOVERED)
    segments = _segments()

    unrecovered = diarization.recover_repetition_loops(pipeline, AUDIO, segments)

    assert unrecovered == []
    assert [segment["text"] for segment in segments] == [SPEECH, f" {RECOVERED}"]
    [(seconds, options)] = pipeline.model.windows
    assert seconds == pytest.approx(36.8)
    assert options["temperature"] == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    assert options["compression_ratio_threshold"] == 2.4
    assert options["initial_prompt"] == "Registrazione in italiano."


def test_a_loop_that_decoding_again_cannot_undo_is_reported_with_its_window():
    pipeline = _pipeline("pa" * 100)
    segments = _segments()

    unrecovered = diarization.recover_repetition_loops(pipeline, AUDIO, segments)

    assert unrecovered == [{"start_sec": 381.2, "end_sec": 418.0}]
    assert segments[1]["text"] == " " + "pa" * 100


def test_decoding_again_that_finds_no_speech_keeps_the_text_heard_first():
    pipeline = _pipeline("")
    segments = _segments()

    unrecovered = diarization.recover_repetition_loops(pipeline, AUDIO, segments)

    assert unrecovered == [{"start_sec": 381.2, "end_sec": 418.0}]
    assert segments[1]["text"] == LOOP


def test_windows_under_the_threshold_are_not_decoded_again():
    pipeline = _pipeline()
    segments = [
        {"text": SPEECH, "start": 0.0, "end": 20.0},
        {"text": "E lui pa pa pa pa pa itera itera itera allunga allunga allunga allunga.", "start": 20.0, "end": 30.0},
    ]

    unrecovered = diarization.recover_repetition_loops(pipeline, AUDIO, [dict(segment) for segment in segments])

    assert unrecovered == []
    assert pipeline.model.windows == []


def test_transcribe_returns_the_loops_it_could_not_recover(monkeypatch):
    class FakePipeline:
        def __init__(self):
            fake = _pipeline("pa" * 100)
            self.options, self.model = fake.options, fake.model

        def transcribe(self, audio, batch_size):
            return {"segments": _segments(), "language": "it"}

    monkeypatch.setattr(diarization.whisperx, "load_model", lambda *args, **kwargs: FakePipeline())

    result = diarization.transcribe(AUDIO)

    assert result["repetition_loops"] == [{"start_sec": 381.2, "end_sec": 418.0}]
    assert result["segments"][0]["text"] == SPEECH
