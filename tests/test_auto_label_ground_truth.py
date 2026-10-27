import asyncio
import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.auto_label_ground_truth import main


def analysis_result():
    return SimpleNamespace(
        status_group=2,
        reason_code="KHACH_BAN",
        call_decision="CALL_BACK",
        appointment_date=None,
        summary="Ứng viên đang bận và hẹn gọi lại.",
        recommended_message="Em sẽ gọi lại sau.",
    )


class AutoLabelTests(unittest.TestCase):
    def test_resume_retries_failed_file_without_duplicate_or_losing_human_label(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_dir = root / "audio"
            audio_dir.mkdir()
            for name in ("1.wav", "2.wav", "3.wav"):
                (audio_dir / name).write_bytes(b"audio")
            output = root / "review.csv"

            def transcribe(path):
                return {"text": path.stem}

            async def fail_second(transcript, contact_name):
                if transcript == "2":
                    raise RuntimeError("Ollama unavailable")
                return analysis_result()

            first = asyncio.run(main(audio_dir, output, resume=True, expected_count=3,
                                     transcribe_fn=transcribe, analyze_fn=fail_second))
            self.assertEqual(first, 1)
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["File_Name"] for row in rows], ["1.wav", "3.wav"])
            self.assertTrue((root / "review_error_log.csv").exists())

            # A manual label entered during review must survive a resumed run.
            rows[0]["Human_Status_Group (Điền tay)"] = "2"
            with output.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            called = []

            async def succeed(transcript, contact_name):
                called.append(transcript)
                return analysis_result()

            second = asyncio.run(main(audio_dir, output, resume=True, expected_count=3,
                                      transcribe_fn=transcribe, analyze_fn=succeed))
            self.assertEqual(second, 0)
            self.assertEqual(called, ["2"])
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual(len({row["File_Name"] for row in rows}), 3)
            self.assertEqual(rows[0]["Human_Status_Group (Điền tay)"], "2")

    def test_expected_count_stops_before_loading_models_or_creating_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_dir = root / "audio"
            audio_dir.mkdir()
            (audio_dir / "1.wav").write_bytes(b"audio")
            output = root / "review.csv"
            result = asyncio.run(main(audio_dir, output, resume=True, expected_count=713))
            self.assertEqual(result, 2)
            self.assertFalse(output.exists())

    def test_stops_after_five_consecutive_model_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_dir = root / "audio"
            audio_dir.mkdir()
            for index in range(6):
                (audio_dir / f"{index}.wav").write_bytes(b"audio")
            output = root / "review.csv"
            calls = []

            async def failing_model(transcript, contact_name):
                calls.append(transcript)
                raise RuntimeError("Ollama unavailable")

            result = asyncio.run(main(audio_dir, output, resume=True, expected_count=6,
                                      transcribe_fn=lambda path: {"text": path.stem},
                                      analyze_fn=failing_model))
            self.assertEqual(result, 1)
            self.assertEqual(calls, ["0", "1", "2", "3", "4"])
            with output.open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 0)


if __name__ == "__main__":
    unittest.main()
