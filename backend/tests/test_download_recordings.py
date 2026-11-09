import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.download_recordings import (
    RecordingError,
    download_one,
    fetch_inventory,
    select_ids,
)


class FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, content_type: str):
        super().__init__(body)
        self.headers = {"Content-Type": content_type}


class RecordingDownloadTests(unittest.TestCase):
    def test_fetches_every_page_and_selects_highest_numeric_ids(self):
        pages = [
            {"count": 3, "limit": 2, "offset": 0, "recordings": ["100", "300"]},
            {"count": 3, "limit": 2, "offset": 2, "recordings": ["200"]},
        ]
        with patch("scripts.download_recordings.get_json", side_effect=pages) as get_json:
            ids = fetch_inventory("http://example.test", 2, 5)
        self.assertEqual(ids, ["100", "300", "200"])
        self.assertIn("offset=2", get_json.call_args_list[1].args[0])
        self.assertEqual(select_ids(ids, "highest-id", 2, None), ["300", "200"])
        self.assertEqual(select_ids(ids, "all", None, None), ids)

    def test_rejects_page_that_ignores_offset(self):
        pages = [
            {"count": 3, "limit": 2, "offset": 0, "recordings": ["100", "200"]},
            {"count": 3, "limit": 2, "offset": 0, "recordings": ["100", "200"]},
        ]
        with patch("scripts.download_recordings.get_json", side_effect=pages):
            with self.assertRaises(RecordingError):
                fetch_inventory("http://example.test", 2, 5)

    def test_downloads_wav_then_skips_existing_file(self):
        wav = b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + bytes(32)
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = Path(temp_dir)
            with patch(
                "scripts.download_recordings.urlopen",
                return_value=FakeResponse(wav, "audio/wav"),
            ) as urlopen:
                self.assertEqual(download_one("http://example.test", "123", audio_dir, 5), "downloaded")
                self.assertEqual(download_one("http://example.test", "123", audio_dir, 5), "existing")
                self.assertEqual(urlopen.call_count, 1)
            self.assertEqual((audio_dir / "123.wav").read_bytes(), wav)

    def test_rejects_incomplete_audio(self):
        wav = b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + bytes(32)
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = Path(temp_dir)

            def response(*_args, **_kwargs):
                item = FakeResponse(wav, "audio/wav")
                item.headers["Content-Length"] = "100"
                return item

            with patch("scripts.download_recordings.urlopen", side_effect=response), patch(
                "scripts.download_recordings.time.sleep"
            ):
                with self.assertRaisesRegex(RecordingError, "Incomplete WAV"):
                    download_one("http://example.test", "123", audio_dir, 5)
            self.assertFalse((audio_dir / "123.wav").exists())


if __name__ == "__main__":
    unittest.main()
