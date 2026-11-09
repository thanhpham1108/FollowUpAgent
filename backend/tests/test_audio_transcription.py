"""Keep stereo calls on the original one-pass PhoWhisper path."""

import wave

from app.audio import service as audio_service


def test_stereo_recording_is_transcribed_once_as_original_file(tmp_path, monkeypatch):
    source = tmp_path / "call.wav"
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x01\x00\xff\xff" * (8000 * 2))

    calls = []
    chunks = [{"text": "Mai anh ra", "timestamp": (1.0, 2.0)}]

    def fake_asr(path, generate_kwargs):
        calls.append(path)
        return {"text": "Mai anh ra", "chunks": chunks}

    monkeypatch.setattr(audio_service, "get_whisper_model", lambda: fake_asr)
    result = audio_service.transcribe_audio(source)

    assert calls == [str(source.resolve())]
    assert result["text"] == "Mai anh ra"
    assert result["segments"] == chunks
    assert result["duration_seconds"] == 2.0
