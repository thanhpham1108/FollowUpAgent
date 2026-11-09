import asyncio
import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.auto_label_ground_truth import (
    DEFAULT_AUDIO_DIR,
    DEFAULT_OUTPUT_CSV,
    main,
    parse_args,
)


def analysis_result():
    return SimpleNamespace(
        status_group=2,
        reason_code="KHACH_BAN",
        call_decision="CALL_BACK",
        appointment_date=None,
        follow_up_days=None,
        summary="Ứng viên đang bận và hẹn gọi lại.",
    )


class AutoLabelTests(unittest.TestCase):
    def test_cli_defaults_target_new_batch_and_guard_713_files(self):
        args = parse_args([])
        self.assertEqual(args.audio_dir, DEFAULT_AUDIO_DIR)
        self.assertEqual(args.output, DEFAULT_OUTPUT_CSV)
        self.assertEqual(args.expected_count, 713)
        self.assertTrue(args.resume)

        custom = parse_args(["--audio-dir", "data/sample", "--no-resume"])
        self.assertIsNone(custom.expected_count)
        self.assertFalse(custom.resume)

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

            async def fail_second(transcript, contact_name, **kwargs):
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

            async def succeed(transcript, contact_name, **kwargs):
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

    def test_trace_sidecar_keeps_decision_evidence_out_of_review_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_dir = root / "audio"
            audio_dir.mkdir()
            (audio_dir / "1.wav").write_bytes(b"audio")
            output = root / "review.csv"

            async def analyze(transcript, contact_name, **kwargs):
                kwargs["trace_callback"]({
                    "event": "model_response", "attempt": 1,
                    "model": "test-model", "raw_response": '{"reason_code":"TRAO_DOI_THEM"}',
                    "parsed": {"reason_code": "TRAO_DOI_THEM", "candidate_evidence": "Gửi Zalo anh xem"},
                })
                kwargs["trace_callback"]({"event": "final", "outcome": "accepted", "reason_code": "TRAO_DOI_THEM"})
                return analysis_result()

            assert asyncio.run(main(
                audio_dir, output, expected_count=1,
                transcribe_fn=lambda path: {"text": "Gửi Zalo anh xem"},
                analyze_fn=analyze,
            )) == 0
            with output.open(encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertNotIn("candidate_evidence", row)
            trace_path = root / "review_decision_trace.jsonl"
            events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["event"] for event in events], ["model_response", "final"])
            self.assertEqual(events[0]["file_name"], "1.wav")
            self.assertNotIn("transcript", events[0])

    def test_fallback_is_saved_for_follow_up_and_logged_for_human_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_dir = root / "audio"
            audio_dir.mkdir()
            (audio_dir / "1.wav").write_bytes(b"audio")
            output = root / "review.csv"

            async def analyze(transcript, contact_name, **kwargs):
                kwargs["trace_callback"]({
                    "event": "fallback", "reason_code": "TRAO_DOI_THEM",
                    "requires_review": True,
                })
                return SimpleNamespace(
                    status_group=3, reason_code="TRAO_DOI_THEM",
                    call_decision="FOLLOW_UP", appointment_date=None,
                    follow_up_days=None, summary="Cần nghe lại audio.",
                )

            assert asyncio.run(main(
                audio_dir, output, expected_count=1,
                transcribe_fn=lambda path: {"text": "Anh đang đi làm rồi"},
                analyze_fn=analyze,
            )) == 0
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["AI_Reason_Code"], "TRAO_DOI_THEM")
            self.assertEqual(rows[0]["AI_Call_Decision"], "FOLLOW_UP")
            with (root / "review_error_log.csv").open(encoding="utf-8-sig", newline="") as handle:
                review_rows = list(csv.DictReader(handle))
            self.assertEqual(review_rows[0]["File_Name"], "1.wav")
            self.assertIn("Nhãn tạm", review_rows[0]["Error"])

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

            async def failing_model(transcript, contact_name, **kwargs):
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
