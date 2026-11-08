import wave

import numpy as np

from app.services.speaker_transcript import (
    merge_channel_transcripts,
    split_conversation_channels,
)


def test_independent_stereo_channels_form_ordered_dialogue(tmp_path, monkeypatch):
    rate = 8000
    seconds = 4
    time_axis = np.arange(rate * seconds) / rate
    audio = np.zeros((len(time_axis), 2), dtype=np.int16)
    audio[: rate * 2, 0] = (2000 * np.sin(2 * np.pi * 220 * time_axis[: rate * 2])).astype(np.int16)
    audio[rate * 2 :, 1] = (2000 * np.sin(2 * np.pi * 330 * time_axis[rate * 2 :])).astype(np.int16)
    source = tmp_path / "call.wav"
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(audio.tobytes())

    channels = split_conversation_channels(source, tmp_path / "channels")
    assert channels is not None
    dialogue, mode = merge_channel_transcripts((
        {"text": "Em bên Việc Ba Miền gọi cho anh.", "chunks": [
            {"text": "Em bên Việc Ba Miền gọi cho anh.", "timestamp": (0, 1)}
        ]},
        {"text": "Mai anh ra, em gửi Zalo anh chấp nhận.", "chunks": [
            {"text": "Mai anh ra, em gửi Zalo anh chấp nhận.", "timestamp": (2, 3)}
        ]},
    ))
    assert mode == "dual_role_labeled"
    assert dialogue.index("HR:") < dialogue.index("Ứng viên:")
    assert "Mai anh ra" in dialogue

    from app.services import audio_service

    def fake_asr(path, generate_kwargs):
        if path.endswith("channel_1.wav"):
            text, timestamp = "Em bên Việc Ba Miền gọi cho anh.", (0, 1)
        else:
            text, timestamp = "Mai anh ra, em gửi Zalo anh chấp nhận.", (2, 3)
        return {"text": text, "chunks": [{"text": text, "timestamp": timestamp}]}

    monkeypatch.setattr(audio_service, "get_whisper_model", lambda: fake_asr)
    result = audio_service.transcribe_audio(source)
    assert result["duration_seconds"] == 4
    assert result["speaker_mode"] == "dual_role_labeled"
    assert "HR:" in result["text"] and "Ứng viên:" in result["text"]


def test_identical_stereo_keeps_mixed_fallback(tmp_path):
    source = tmp_path / "mixed.wav"
    samples = np.full((8000 * 3, 2), 1000, dtype=np.int16)
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(samples.tobytes())
    assert split_conversation_channels(source, tmp_path / "channels") is None
