#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#     "huggingface-hub>=0.20",
#     "sherpa-onnx>=1.13,<2",
#     "sherpa-onnx-core>=1.13,<2",
#     "soundfile>=0.12,<1",
# ]
# ///
"""Transcribe WAV files in filename order with Gipformer ONNX."""

import argparse
import fcntl
import json
import os
import re
import sys
from pathlib import Path

import sherpa_onnx
import soundfile as sf
from huggingface_hub import hf_hub_download

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
IMPORT_DIR = DATA_DIR / "recordings_import"
MODEL_ID = "g-group-ai-lab/gipformer-68M-rnnt"
MODEL_REVISION = "318322b009200f8e77a3751fa64638e5cc85a7dc"
FIRST_FILE = "18483292.wav"
LAST_FILE = "22052024.wav"
WINDOW_SECONDS = 20
LONG_NUMBER = re.compile(r"(?<!\d)(?:\d[ .-]?){8,}\d(?!\d)")


def audio_batch(audio_dir):
    for name in (FIRST_FILE, LAST_FILE):
        if not (audio_dir / name).is_file():
            raise ValueError(f"Thiếu file mốc: {audio_dir / name}")
    return sorted(
        path for path in audio_dir.glob("*.wav")
        if FIRST_FILE <= path.name <= LAST_FILE and path.is_file()
    )


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
        "model_revision": MODEL_REVISION,
        "duration_seconds": round(duration, 3),
        "segments": segments,
    }


def read_checkpoint(handle, paths):
    handle.seek(0)
    completed = 0
    valid_end = 0
    while line := handle.readline():
        if not line.endswith(b"\n"):
            # A stopped write can leave an incomplete record at the end.
            handle.truncate(valid_end)
            print("Sẽ chạy lại file có dòng JSONL ghi dở.", file=sys.stderr)
            break
        record = json.loads(line)
        if (
            completed >= len(paths)
            or not isinstance(record, dict)
            or record.get("File_Name") != paths[completed].name
            or record.get("model_revision") != MODEL_REVISION
            or not isinstance(record.get("segments"), list)
        ):
            raise ValueError(f"JSONL không khớp lô WAV tại dòng {completed + 1}: {handle.name}")
        completed += 1
        valid_end = handle.tell()
    return completed


def main(args):
    paths = audio_batch(args.audio_dir)
    total = min(args.limit, len(paths)) if args.limit else len(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(f"Đã có job ghi vào {args.output}") from exc
        completed = read_checkpoint(handle, paths)
        print(f"Đã lưu {completed}/{len(paths)} WAV; mục tiêu lượt này: {total}.", flush=True)
        if completed < total:
            recognizer = create_recognizer(args.threads)
            for index, path in enumerate(paths[completed:total], completed + 1):
                record = transcribe(recognizer, path)
                handle.write((json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
                print(f"{index}/{total} {path.name}", flush=True)

    print(f"JSONL: {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-dir", type=Path, default=IMPORT_DIR / "audio")
    parser.add_argument("--output", type=Path,
                        default=IMPORT_DIR / "gipformer_18483292_22052024.jsonl")
    parser.add_argument("--limit", type=int, default=0, help="Số file chạy thử; 0 là cả lô.")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.limit < 0 or args.threads < 1:
        parser.error("--limit phải >= 0 và --threads phải lớn hơn 0.")
    if args.output.suffix.lower() != ".jsonl":
        parser.error("--output phải có đuôi .jsonl.")
    try:
        main(args)
    except (OSError, ValueError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(1) from error
