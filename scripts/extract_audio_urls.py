#!/usr/bin/env python3
# -------------------------------------------------------
# scripts/extract_audio_urls.py
# Quét danh sách deals từ CRM server (192.168.25.175:8000)
# và trích xuất tất cả các link audio (linkCall) ra urls.txt
# -------------------------------------------------------
# Cách dùng:
#   python scripts/extract_audio_urls.py
#   python scripts/extract_audio_urls.py --server http://192.168.25.175:8000 --output urls.txt
#   python scripts/extract_audio_urls.py --download --out-dir ./data/deal_audios
# -------------------------------------------------------
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Trích xuất audio URLs từ CRM Deals")
    parser.add_argument(
        "--server",
        default="http://192.168.25.175:8000",
        help="Base URL của deals server (default: http://192.168.25.175:8000)",
    )
    parser.add_argument(
        "--output",
        default="urls.txt",
        help="Đường dẫn file text đầu ra chứa danh sách audio URLs (default: urls.txt)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Tải luôn các file audio về máy cục bộ",
    )
    parser.add_argument(
        "--out-dir",
        default="./data/deal_audios",
        help="Thư mục lưu các file audio tải về (default: ./data/deal_audios)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Giới hạn số lượng audio URLs lấy ra (0 = không giới hạn)",
    )

    args = parser.parse_args()

    server_url = args.server.rstrip("/")
    deals_endpoint = f"{server_url}/deals"

    print("=" * 70)
    print(f"  🔍 BẮT ĐẦU QUÉT AUDIO TỪ DEALS SERVER")
    print(f"  Endpoint: {deals_endpoint}")
    print("=" * 70)

    try:
        req = urllib.request.Request(deals_endpoint, headers={"accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Không thể kết nối tới {deals_endpoint}: {e}")
        sys.exit(1)

    deal_ids = data.get("deal_ids", [])
    if not deal_ids:
        print("⚠️ Không tìm thấy deal_id nào trong kết quả trả về.")
        sys.exit(0)

    print(f"✅ Tìm thấy {len(deal_ids)} deals. Bắt đầu duyệt từng deal để bóc tách linkCall...")

    audio_urls = []
    request_items = []
    seen = set()

    for idx, did in enumerate(deal_ids, start=1):
        deal_url = f"{server_url}/deals/{did}"
        try:
            req = urllib.request.Request(deal_url, headers={"accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                deal_detail = json.loads(resp.read().decode("utf-8"))
                deal_data = deal_detail.get("data", {})
                company_name = deal_data.get("company_name", "").strip() or f"Deal {did}"
                activities = deal_data.get("activities", [])
                
                count_in_deal = 0
                for act in activities:
                    link = act.get("linkCall")
                    if link and link.startswith("http") and link not in seen:
                        seen.add(link)
                        audio_urls.append(link)

                        # Trích xuất call_id từ URL (ví dụ 23904923 từ /play/23904923.wav)
                        call_filename = link.split("?")[0].split("/")[-1]
                        call_id = call_filename.split(".")[0] if "." in call_filename else call_filename

                        # Tạo item chuẩn để bắn vào API FollowUpAgent
                        request_items.append({
                            "deal_id": did,
                            "call_id": call_id,
                            "ssn": f"{did}_{call_id}",
                            "candidate_name": f"{company_name} [{did}]",
                            "audio_url": link,
                        })
                        count_in_deal += 1

                print(f"  [{idx:02d}/{len(deal_ids)}] Deal {did}: tìm thấy {count_in_deal} link audio")

                if args.limit > 0 and len(request_items) >= args.limit:
                    audio_urls = audio_urls[:args.limit]
                    request_items = request_items[:args.limit]
                    print(f"⚡ Đã đạt giới hạn --limit={args.limit}")
                    break

        except Exception as e:
            print(f"  ⚠️ Lỗi khi lấy chi tiết deal {did}: {e}")

    print()
    print(f"📊 Tổng cộng thu thập được: {len(request_items)} cuộc gọi có audio.")

    # 1. Lưu danh sách URLs thuần
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for url in audio_urls:
            f.write(url + "\n")
    print(f"💾 Đã lưu danh sách link audio vào: {out_path.resolve()}")

    # 2. Lưu file requests.json chứa đầy đủ định danh (deal_id, ssn, candidate_name)
    requests_path = out_path.parent / (out_path.stem + "_requests.json" if out_path.stem != "urls" else "requests.json")
    with open(requests_path, "w", encoding="utf-8") as f:
        json.dump(request_items, f, ensure_ascii=False, indent=2)
    print(f"💾 Đã lưu file requests với đầy đủ Deal ID vào: {requests_path.resolve()}")

    # Nếu người dùng yêu cầu tải trực tiếp file về
    if args.download and audio_urls:
        download_dir = Path(args.out_dir)
        download_dir.mkdir(parents=True, exist_ok=True)
        print()
        print(f"📥 Đang tải {len(audio_urls)} file audio về: {download_dir.resolve()}...")

        success_count = 0
        for i, url in enumerate(audio_urls, start=1):
            # Lấy tên file từ URL (bỏ query params)
            base_filename = url.split("?")[0].split("/")[-1]
            if not base_filename.endswith((".wav", ".mp3", ".ogg", ".m4a")):
                base_filename = f"audio_{i:03d}.wav"
            else:
                base_filename = f"{i:03d}_{base_filename}"

            dest = download_dir / base_filename
            try:
                urllib.request.urlretrieve(url, str(dest))
                print(f"  ✅ [{i:02d}/{len(audio_urls)}] Tải thành công: {dest.name}")
                success_count += 1
            except Exception as e:
                print(f"  ❌ [{i:02d}/{len(audio_urls)}] Tải thất bại từ {url[:60]}... ({e})")

        print(f"🎉 Hoàn tất tải file: {success_count}/{len(audio_urls)} thành công.")


if __name__ == "__main__":
    main()
