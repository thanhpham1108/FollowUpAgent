"""Separate dual-channel call recordings and rebuild an ordered dialogue."""

from pathlib import Path
import unicodedata
import wave

import numpy as np


def split_conversation_channels(path: Path, output_dir: Path) -> tuple[Path, Path] | None:
    """Return two mono WAVs only when both channels contain distinct speech."""
    try:
        with wave.open(str(path), "rb") as source:
            if source.getnchannels() != 2 or source.getsampwidth() != 2:
                return None
            rate = source.getframerate()
            frames = source.readframes(source.getnframes())
    except (OSError, wave.Error):
        return None

    samples = np.frombuffer(frames, dtype="<i2")
    if len(samples) < rate * 2 or len(samples) % 2:
        return None
    stereo = samples.reshape(-1, 2)
    excerpt = stereo[:: max(1, rate // 400)].astype(np.float64)
    rms = np.sqrt(np.mean(excerpt * excerpt, axis=0))
    if np.min(rms) < 30 or np.min(np.std(excerpt, axis=0)) == 0:
        return None
    correlation = float(np.corrcoef(excerpt[:, 0], excerpt[:, 1])[0, 1])
    if not np.isfinite(correlation) or abs(correlation) > 0.8:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = (output_dir / "channel_1.wav", output_dir / "channel_2.wav")
    for index, output_path in enumerate(output_paths):
        with wave.open(str(output_path), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(rate)
            target.writeframes(stereo[:, index].tobytes())
    return output_paths


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold()).replace("đ", "d")
    return "".join(char for char in value if not unicodedata.combining(char))


def infer_channel_roles(text_1: str, text_2: str) -> tuple[str, str, bool]:
    """Assign HR only when one channel has a clearer recruiter introduction."""
    markers = ("em ben", "ben em", "em goi", "em lien he", "viec ba mien", "tuyen dung")
    scores = [sum(marker in _plain(text[:700]) for marker in markers)
              for text in (text_1, text_2)]
    if scores[0] > scores[1] and scores[0] >= 2:
        return "HR", "Ứng viên", True
    if scores[1] > scores[0] and scores[1] >= 2:
        return "Ứng viên", "HR", True
    return "Kênh 1", "Kênh 2", False


def merge_channel_transcripts(results: tuple[dict, dict]) -> tuple[str, str]:
    """Merge timestamped ASR chunks; retain channel names when roles are unclear."""
    texts = tuple((result.get("text") or "").strip() for result in results)
    roles = infer_channel_roles(*texts)
    segments = []
    timestamps_available = True
    for index, result in enumerate(results):
        chunks = result.get("chunks") or []
        if not chunks:
            chunks = [{"text": texts[index], "timestamp": (0, None)}]
            timestamps_available = False
        for chunk in chunks:
            content = (chunk.get("text") or "").strip()
            if not content:
                continue
            timestamp = chunk.get("timestamp") or (None, None)
            if timestamp[0] is None:
                timestamps_available = False
            start = float(timestamp[0] or 0)
            segments.append((start, index, content))
    segments.sort(key=lambda item: (item[0], item[1]))
    lines = [f"[{int(start // 60):02d}:{int(start % 60):02d}] {roles[index]}: {content}"
             for start, index, content in segments]
    if not lines:
        return "", "dual_empty"
    if not timestamps_available:
        lines.insert(0, "[Thứ tự câu nói chưa xác định vì STT thiếu timestamp]")
    mode = "dual_role_labeled" if roles[2] and timestamps_available else "dual_channel_labeled"
    return "\n".join(lines), mode
