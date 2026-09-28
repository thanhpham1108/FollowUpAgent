#!/usr/bin/env python3
# -------------------------------------------------------
# scripts/load_test.py
# Kịch bản Load Test — Bắn nhiều request đồng thời vào API
# -------------------------------------------------------
# Sử dụng:
#   python scripts/load_test.py --url http://localhost:18000 --audio-url http://localhost:8001/test.wav --count 5
#
# Hoặc dùng nhiều file audio khác nhau:
#   python scripts/load_test.py --url http://localhost:18000 --audio-urls urls.txt --count 10
#
# File urls.txt chứa mỗi dòng 1 URL audio.
# -------------------------------------------------------
import asyncio
import argparse
import time
import httpx


async def send_request(
    client: httpx.AsyncClient,
    api_url: str,
    payload: dict,
    index: int,
) -> dict:
    """Gửi 1 request phân tích audio và trả về kết quả."""
    start = time.perf_counter()
    ssn = payload.get("ssn", f"LOADTEST-{index:03d}")
    try:
        response = await client.post(
            f"{api_url}/api/v1/candidates/analyze",
            json=payload,
        )
        elapsed = time.perf_counter() - start
        data = response.json()

        status_icon = "✅" if response.status_code == 202 else "❌"
        task_id = data.get("task_id", "N/A")
        print(f"  {status_icon} #{index:03d} [{ssn}] | HTTP {response.status_code} | {elapsed:.2f}s | task_id={task_id}")

        return {
            "index": index,
            "ssn": ssn,
            "status_code": response.status_code,
            "task_id": data.get("task_id"),
            "elapsed": elapsed,
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"  ❌ #{index:03d} [{ssn}] | ERROR | {elapsed:.2f}s | {e}")
        return {"index": index, "ssn": ssn, "status_code": 0, "task_id": None, "elapsed": elapsed, "error": str(e)}


async def poll_task_status(
    client: httpx.AsyncClient,
    api_url: str,
    task_id: str,
    timeout: float = 600.0,
    interval: float = 5.0,
) -> str:
    """Polling trạng thái task cho đến khi hoàn thành hoặc timeout."""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        try:
            resp = await client.get(f"{api_url}/api/v1/tasks/{task_id}")
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "unknown")
                if status in ("completed", "failed", "webhook_failed"):
                    return status
        except Exception:
            pass
        await asyncio.sleep(interval)
    return "timeout"


async def main():
    parser = argparse.ArgumentParser(description="FollowUpAgent Load Tester")
    parser.add_argument("--url", default="http://localhost:18000", help="Base URL của API server")
    parser.add_argument("--audio-url", default=None, help="URL file audio dùng chung cho mọi request")
    parser.add_argument("--audio-urls", default=None, help="Đường dẫn tới file text chứa danh sách URL audio (mỗi dòng 1 URL)")
    parser.add_argument("--requests-file", default=None, help="Đường dẫn tới file JSON chứa danh sách request đầy đủ (deal_id, ssn, candidate_name, audio_url)")
    parser.add_argument("--count", type=int, default=5, help="Số request gửi đồng thời (mặc định: 5)")
    parser.add_argument("--poll", action="store_true", help="Bật chế độ polling: chờ đến khi tất cả task hoàn thành")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Khoảng cách giữa các lần polling (giây)")
    args = parser.parse_args()

    # Xây dựng danh sách payload
    payloads = []
    if args.requests_file:
        import json
        with open(args.requests_file, "r", encoding="utf-8") as f:
            req_data = json.load(f)
            for item in req_data:
                payloads.append({
                    "ssn": item.get("ssn"),
                    "candidate_name": item.get("candidate_name"),
                    "audio_url": item.get("audio_url"),
                })
    elif args.audio_urls:
        with open(args.audio_urls, "r", encoding="utf-8") as f:
            audio_urls = [line.strip() for line in f if line.strip()]
        for i, url in enumerate(audio_urls, 1):
            payloads.append({
                "ssn": f"LOADTEST-{i:03d}",
                "candidate_name": f"LoadTest User {i}",
                "audio_url": url,
            })
    elif args.audio_url:
        payloads.append({
            "ssn": "LOADTEST-001",
            "candidate_name": "LoadTest User 1",
            "audio_url": args.audio_url,
        })
    else:
        print("❌ Bạn phải cung cấp --requests-file, --audio-urls hoặc --audio-url")
        return

    count = min(args.count, len(payloads)) if args.requests_file else args.count

    print("=" * 70)
    print(f"  🚀 FOLLOWUPAGENT LOAD TEST")
    print(f"  Server:      {args.url}")
    print(f"  Nguồn data:  {args.requests_file or args.audio_urls or args.audio_url}")
    print(f"  Dataset:     {len(payloads)} request mẫu có sẵn")
    print(f"  Concurrency: {count} request(s) đồng thời")
    print(f"  Polling:     {'Bật' if args.poll else 'Tắt'}")
    print("=" * 70)
    print()

    # Giai đoạn 1: Bắn request đồng loạt
    print("📡 Giai đoạn 1: Gửi request đồng loạt...")
    overall_start = time.perf_counter()

    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        for i in range(count):
            p = payloads[i % len(payloads)]
            tasks.append(send_request(client, args.url, p, i + 1))

        results = await asyncio.gather(*tasks)

    submit_elapsed = time.perf_counter() - overall_start

    # Tổng kết giai đoạn 1
    success_count = sum(1 for r in results if r["status_code"] == 202)
    fail_count = count - success_count
    print()
    print(f"📊 Kết quả gửi request:")
    print(f"   Thành công: {success_count}/{count}")
    print(f"   Thất bại:   {fail_count}/{count}")
    print(f"   Tổng thời gian gửi: {submit_elapsed:.2f}s")
    print()

    # Giai đoạn 2: Polling (nếu bật)
    if args.poll and success_count > 0:
        print("⏳ Giai đoạn 2: Chờ tất cả task hoàn thành (polling)...")
        task_ids = [r["task_id"] for r in results if r.get("task_id")]

        async with httpx.AsyncClient(timeout=10.0) as client:
            poll_tasks = [
                poll_task_status(client, args.url, tid, interval=args.poll_interval)
                for tid in task_ids
            ]
            statuses = await asyncio.gather(*poll_tasks)

        total_elapsed = time.perf_counter() - overall_start
        print()
        print(f"📊 Kết quả xử lý:")
        for tid, st in zip(task_ids, statuses):
            icon = "✅" if st == "completed" else "⚠️" if st == "webhook_failed" else "❌"
            print(f"   {icon} {tid}: {st}")

        completed = sum(1 for s in statuses if s == "completed")
        webhook_failed = sum(1 for s in statuses if s == "webhook_failed")
        failed = sum(1 for s in statuses if s == "failed")
        timed_out = sum(1 for s in statuses if s == "timeout")
        print()
        print(f"   ✅ Completed:      {completed}")
        print(f"   ⚠️  Webhook Failed: {webhook_failed}")
        print(f"   ❌ Failed:         {failed}")
        print(f"   ⏰ Timeout:        {timed_out}")
        print(f"   Tổng thời gian:    {total_elapsed:.1f}s")
    else:
        print("💡 Thêm flag --poll để chờ kết quả xử lý của tất cả task.")

    print()
    print("=" * 70)
    print("  Hoàn thành Load Test!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
