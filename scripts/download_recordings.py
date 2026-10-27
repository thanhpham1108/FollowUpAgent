#!/usr/bin/env python3
"""Inventory and download recordings from the recordings API, not /deals.

Examples:
  python scripts/download_recordings.py --out-dir data/recordings_import
  python scripts/download_recordings.py --out-dir data/recordings_import \
      --ids-file data/new_recording_ids.txt --download
  python scripts/download_recordings.py --out-dir data/recordings_import \
      --select highest-id --count 100 --download

The highest numeric IDs are not necessarily the newest recordings. Use that
selection only if the API owner confirms how IDs are assigned.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_SERVER = "http://192.168.25.175:8000"
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")


class RecordingError(Exception):
    """An API response or download cannot be used safely."""


def get_json(url: str, timeout: int) -> object:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" not in content_type:
            raise RecordingError(f"Expected JSON at {url}; got {content_type or 'unknown type'}")
        return json.load(response)


def fetch_inventory(server: str, page_size: int, timeout: int) -> list[str]:
    """Fetch all pages and reject inconsistent or incomplete pagination."""
    offset = 0
    expected_count: int | None = None
    ids: list[str] = []

    while expected_count is None or offset < expected_count:
        url = f"{server}/recordings?{urlencode({'limit': page_size, 'offset': offset})}"
        page = get_json(url, timeout)
        if not isinstance(page, dict):
            raise RecordingError(f"Expected an object at offset {offset}")

        count = page.get("count")
        actual_offset = page.get("offset")
        actual_limit = page.get("limit")
        recordings = page.get("recordings")
        if (type(count) is not int or count < 0 or
                type(actual_offset) is not int or actual_offset != offset or
                type(actual_limit) is not int or actual_limit <= 0 or
                not isinstance(recordings, list)):
            raise RecordingError(f"Invalid pagination response at offset {offset}: {page!r}")
        if expected_count is None:
            expected_count = count
        elif count != expected_count:
            raise RecordingError(f"Count changed while paging: {expected_count} -> {count}")
        if len(recordings) > actual_limit or offset + len(recordings) > count:
            raise RecordingError(f"Invalid page size at offset {offset}")
        if count > offset and not recordings:
            raise RecordingError(f"Empty page before count={count} at offset {offset}")
        for call_id in recordings:
            if not isinstance(call_id, str) or not ID_PATTERN.fullmatch(call_id):
                raise RecordingError(f"Invalid recording ID at offset {offset}: {call_id!r}")

        ids.extend(recordings)
        print(f"List: {len(ids)}/{count} IDs (offset {offset})", flush=True)
        offset += len(recordings)

    if len(ids) != len(set(ids)):
        raise RecordingError("The API returned duplicate IDs across pages; list may have changed")
    return ids


def select_ids(
    inventory: list[str], selection: str | None, count: int | None, ids_file: Path | None
) -> list[str]:
    if ids_file is not None:
        requested = [line.strip() for line in ids_file.read_text(encoding="utf-8").splitlines()]
        requested = list(dict.fromkeys(call_id for call_id in requested if call_id))
        if not requested:
            raise RecordingError(f"No IDs in {ids_file}")
        available = set(inventory)
        missing = [call_id for call_id in requested if call_id not in available]
        if missing:
            raise RecordingError(f"{len(missing)} selected IDs absent from API; first: {missing[0]}")
        return requested

    if selection is None:
        return []
    if selection == "all":
        return inventory.copy()
    if count is None or count <= 0:
        raise RecordingError("--count must be positive for first, last or highest-id")
    if count > len(inventory):
        raise RecordingError(f"Requested {count} IDs, but API has {len(inventory)}")
    if selection == "first":
        return inventory[:count]
    if selection == "last":
        return inventory[-count:]
    if selection == "highest-id":
        if any(not call_id.isascii() or not call_id.isdecimal() for call_id in inventory):
            raise RecordingError("highest-id requires numeric ASCII IDs")
        return sorted(inventory, key=lambda call_id: (int(call_id), call_id), reverse=True)[:count]
    raise RecordingError(f"Unknown selection: {selection}")


def write_lines(path: Path, values: list[str]) -> None:
    path.write_text("".join(f"{value}\n" for value in values), encoding="utf-8")


def valid_wav(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 44:
        return False
    with path.open("rb") as handle:
        header = handle.read(12)
    return header[:4] in (b"RIFF", b"RIFX", b"RF64") and header[8:12] == b"WAVE"


def download_one(server: str, call_id: str, audio_dir: Path, timeout: int) -> str:
    target = audio_dir / f"{call_id}.wav"
    if valid_wav(target):
        return "existing"

    partial = audio_dir / f"{call_id}.wav.part"
    url = f"{server}/media/play/{call_id}.wav"
    for attempt in range(1, 4):
        try:
            request = Request(url, headers={"Accept": "audio/wav, application/octet-stream"})
            with urlopen(request, timeout=timeout) as response, partial.open("wb") as output:
                content_type = response.headers.get("Content-Type", "").lower()
                if "html" in content_type or "json" in content_type:
                    raise RecordingError(f"Audio endpoint returned {content_type} for {call_id}")
                content_length = response.headers.get("Content-Length")
                received = 0
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    received += len(chunk)
                if content_length is not None and received != int(content_length):
                    raise RecordingError(f"Incomplete WAV for {call_id}: {received}/{content_length} bytes")
            if not valid_wav(partial):
                raise RecordingError(f"Downloaded data is not WAV for {call_id}")
            partial.replace(target)
            return "downloaded"
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RecordingError) as exc:
            partial.unlink(missing_ok=True)
            if attempt == 3:
                raise RecordingError(f"{call_id}: {exc}") from exc
            time.sleep(attempt)
    raise AssertionError("Unreachable")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inventory and download the recordings API (not /deals).",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Base URL without /docs")
    parser.add_argument("--out-dir", type=Path, default=Path("data/recordings_import"))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=60)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--ids-file", type=Path, help="File with exact call IDs to download")
    choice.add_argument("--select", choices=["first", "last", "highest-id", "all"])
    parser.add_argument("--count", type=int, help="Number of IDs for first, last or highest-id")
    parser.add_argument("--download", action="store_true", help="Download selected IDs")
    args = parser.parse_args(argv)

    if args.page_size <= 0 or args.timeout <= 0:
        parser.error("--page-size and --timeout must be positive")
    if args.server.rstrip("/").endswith("/docs"):
        parser.error("--server must be the base URL, without /docs")
    if args.download and not (args.select or args.ids_file):
        parser.error("Choose --select or --ids-file before --download")
    if args.count is not None and args.select not in ("first", "last", "highest-id"):
        parser.error("--count only applies to first, last or highest-id")

    server = args.server.rstrip("/")
    try:
        inventory = fetch_inventory(server, args.page_size, args.timeout)
        selected = select_ids(inventory, args.select, args.count, args.ids_file)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        write_lines(args.out_dir / "all_call_ids.txt", inventory)
        manifest = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "server": server,
            "total": len(inventory),
            "selection": "ids-file" if args.ids_file else args.select,
            "selected_count": len(selected),
            "note": "ID or API list order does not establish recording date",
        }
        (args.out_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if selected:
            write_lines(args.out_dir / "selected_call_ids.txt", selected)
        print(f"Inventory: {len(inventory)} IDs -> {args.out_dir / 'all_call_ids.txt'}")
        if not selected:
            print("Inventory only. Select exact IDs or a confirmed ordering before download.")
            return 0
        print(f"Selected: {len(selected)} IDs -> {args.out_dir / 'selected_call_ids.txt'}")
        if not args.download:
            return 0

        audio_dir = args.out_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        failed: list[str] = []
        for index, call_id in enumerate(selected, 1):
            try:
                result = download_one(server, call_id, audio_dir, args.timeout)
                print(f"[{index}/{len(selected)}] {result}: {call_id}", flush=True)
            except RecordingError as exc:
                failed.append(call_id)
                print(f"[{index}/{len(selected)}] ERROR: {exc}", file=sys.stderr, flush=True)
        write_lines(args.out_dir / "failed_call_ids.txt", failed)
        print(f"Done: {len(selected) - len(failed)}/{len(selected)} WAV files available")
        return 1 if failed else 0
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, RecordingError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
