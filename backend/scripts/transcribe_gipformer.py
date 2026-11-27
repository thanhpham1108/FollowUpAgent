#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#     "huggingface-hub>=0.20",
#     "openpyxl>=3.1,<4",
#     "sherpa-onnx>=1.13,<2",
#     "sherpa-onnx-core>=1.13,<2",
#     "soundfile>=0.12,<1",
# ]
# ///
"""Transcribe the workbook's 345-call batch offline with Gipformer ONNX."""

import argparse
import json
import re
import sys
from pathlib import Path

import sherpa_onnx
import soundfile as sf
from huggingface_hub import hf_hub_download
from openpyxl import load_workbook

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MODEL_ID = "g-group-ai-lab/gipformer-68M-rnnt"
MODEL_REVISION = "318322b009200f8e77a3751fa64638e5cc85a7dc"
FIRST_FILE = "18678002.wav"
LAST_FILE = "22052466.wav"
EXPECTED_COUNT = 345
WINDOW_SECONDS = 20
CELL_CHARS = 30_000
LONG_NUMBER = re.compile(r"(?<!\d)(?:\d[ .-]?){8,}\d(?!\d)")


def workbook_batch(workbook):
    names = [name for (name,) in workbook["Labeling"].iter_rows(
        min_row=5, max_col=1, values_only=True
    ) if name]
    names = names[names.index(FIRST_FILE):names.index(LAST_FILE) + 1]
    if len(names) != EXPECTED_COUNT or len(set(names)) != EXPECTED_COUNT:
        raise ValueError(f"Cần đúng {EXPECTED_COUNT} tên WAV duy nhất trong phạm vi.")
    if any(Path(name).name != name or not name.endswith(".wav") for name in names):
        raise ValueError("Cột File_Name chỉ được chứa tên file WAV.")

    sheet = workbook["Transcript_Short"]
    headers = {cell.value: cell.column for cell in sheet[1]}
    rows = {}
    for (cell,) in sheet.iter_rows(min_row=2, max_col=1):
        if cell.value:
            if cell.value in rows:
                raise ValueError(f"Tên file trùng trong Transcript_Short: {cell.value}")
            rows[cell.value] = cell.row
    return names, sheet, rows, headers["Evidence"]


def create_recognizer(threads):
    files = {
        "encoder": "encoder.onnx",
        "decoder": "decoder.onnx",
        "joiner": "joiner.onnx",
        "tokens": "tokens.txt",
    }
    paths = {key: hf_hub_download(MODEL_ID, filename, revision=MODEL_REVISION)
             for key, filename in files.items()}
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        **paths, sample_rate=16000, feature_dim=80, num_threads=threads,
        decoding_method="modified_beam_search",
    )


def transcribe(recognizer, path):
    segments = []
    with sf.SoundFile(path) as audio:
        rate = audio.samplerate
        duration = audio.frames / rate
        if not duration:
            raise ValueError(f"WAV không có mẫu âm thanh: {path.name}")
        start = 0
        for samples in audio.blocks(
            blocksize=WINDOW_SECONDS * rate, dtype="float32", always_2d=True
        ):
            end = start + len(samples)
            streams = []
            for channel in range(audio.channels):
                stream = recognizer.create_stream()
                stream.accept_waveform(rate, samples[:, channel].copy())
                streams.append(stream)
            recognizer.decode_streams(streams)
            for channel, stream in enumerate(streams, 1):
                transcript = stream.result.text.strip()
                if transcript:
                    segments.append({
                        "start": round(start / rate, 3),
                        "end": round(end / rate, 3),
                        "channel": channel,
                        "text": LONG_NUMBER.sub("[ẩn chuỗi số]", transcript),
                    })
            start = end
    return {
        "File_Name": path.name,
        "model": MODEL_ID,
        "duration_seconds": round(duration, 3),
        "segments": segments,
    }


def read_checkpoint(path, names):
    completed = {}
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                name = record["File_Name"]
                if name not in names or name in completed or record["model"] != MODEL_ID:
                    raise ValueError(f"Checkpoint không khớp lô WAV: {path}")
                completed[name] = record
    return completed


def write_evidence(sheet, row, column, record):
    lines = [f"[{MODEL_ID}]", *(
        f"[{s['start']:.1f}–{s['end']:.1f}s] Kênh {s['channel']}: {s['text']}"
        for s in record["segments"]
    )]
    if not record["segments"]:
        lines.append("[Gipformer không nhận dạng được lời thoại.]")
    transcript = "\n".join(lines)
    sheet.cell(row, column).value = transcript[:CELL_CHARS]
    for part, offset in enumerate(range(CELL_CHARS, len(transcript), CELL_CHARS), 2):
        heading = f"Evidence (phần {part})"
        extra = next((cell.column for cell in sheet[1] if cell.value == heading), None)
        if extra is None:
            extra = sheet.max_column + 1
            sheet.cell(1, extra).value = heading
        sheet.cell(row, extra).value = transcript[offset:offset + CELL_CHARS]


def main(args):
    if args.output.exists():
        raise ValueError(f"Workbook đầu ra đã tồn tại: {args.output}")
    workbook = load_workbook(args.workbook)
    names, sheet, rows, evidence_column = workbook_batch(workbook)
    if args.limit:
        names = names[:args.limit]
    missing = [name for name in names if name not in rows or not (args.audio_dir / name).is_file()]
    if missing:
        raise ValueError("Thiếu WAV hoặc thiếu dòng Transcript_Short: " + ", ".join(missing[:10]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output.with_suffix(".jsonl")
    completed = read_checkpoint(checkpoint, set(names))
    if len(completed) != len(names):
        recognizer = create_recognizer(args.threads)
        with checkpoint.open("a", encoding="utf-8") as handle:
            for index, name in enumerate(names, 1):
                if name not in completed:
                    record = transcribe(recognizer, args.audio_dir / name)
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
                    completed[name] = record
                    print(f"{index}/{len(names)} {name}", flush=True)

    for name in names:
        write_evidence(sheet, rows[name], evidence_column, completed[name])
    pending = args.output.with_suffix(".tmp.xlsx")
    workbook.save(pending)
    pending.replace(args.output)
    print(f"Đã ghi {len(names)} transcript: {args.output}\nJSONL: {checkpoint}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-dir", type=Path, default=DATA_DIR / "recordings_import/audio")
    parser.add_argument("--workbook", type=Path, default=DATA_DIR / "ground_truth_713_labeling.xlsx")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "ground_truth_713_gipformer.xlsx")
    parser.add_argument("--limit", type=int, default=0, help="Số file chạy thử; 0 là cả 345 file.")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if not 0 <= args.limit <= EXPECTED_COUNT or args.threads < 1:
        parser.error("--limit phải từ 0 đến 345 và --threads phải lớn hơn 0.")
    if args.output.suffix.lower() != ".xlsx":
        parser.error("--output phải có đuôi .xlsx.")
    try:
        main(args)
    except (KeyError, OSError, ValueError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(1) from error
