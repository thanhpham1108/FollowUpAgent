import sys
import asyncio
import csv
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.audio_service import transcribe_audio
from app.services.llm_service import llm_service

async def main(
    audio_dir: Path = Path("data"),
    output_csv: Path = Path("data/ground_truth_review.csv"),
    limit: int = 0,
):
    wav_files = sorted(audio_dir.glob("*.wav"))
    if not wav_files and audio_dir == Path("data"):
        # Fallback tìm các file .wav ở thư mục gốc
        wav_files = sorted(Path(".").glob("*.wav"))
    
    if not wav_files:
        print(f"Không tìm thấy file .wav nào trong {audio_dir}.")
        return

    if limit > 0:
        wav_files = wav_files[:limit]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if output_csv.exists():
        output_csv = output_csv.with_name(
            f"{output_csv.stem}_{datetime.now():%Y%m%d_%H%M%S}{output_csv.suffix}"
        )
    print(f"[*] Bắt đầu quy trình Auto-Labeling cho {len(wav_files)} files...")
    
    with open(output_csv, mode='x', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "File_Name", 
            "Transcript_Cleaned", 
            "AI_Status_Group", 
            "AI_Reason_Code", 
            "AI_Call_Decision",
            "AI_Appointment_Date", 
            "AI_Summary",
            "AI_Recommended_Message",
            "Human_Status_Group (Điền tay)",
            "Human_Reason_Code (Điền tay)"
        ])
        
        for i, wav_file in enumerate(wav_files, 1):
            print(f"\n[{i}/{len(wav_files)}] Đang phân tích: {wav_file.name}")
            try:
                # 1. Chạy STT (đã tự động tích hợp Text Normalizer chuẩn hóa tên công ty/KCN)
                stt_result = transcribe_audio(wav_file)
                transcript = stt_result["text"].strip()
                
                # 2. Chạy LLM (Prompt mới với 115 công ty, 5 nhóm chuẩn, summary 3-5 câu)
                analysis = await llm_service.analyze_audio(transcript, contact_name="Ứng viên")
                
                # 3. Ghi kết quả
                writer.writerow([
                    wav_file.name,
                    transcript,
                    analysis.status_group,
                    analysis.reason_code,
                    analysis.call_decision,
                    analysis.appointment_date,
                    analysis.summary,
                    analysis.recommended_message,
                    "", # Cột trống cho người điền
                    ""  # Cột trống cho người điền
                ])
                f.flush()
                print(f"   -> Nhóm {analysis.status_group} ({analysis.reason_code}) | Quyết định: {analysis.call_decision}")
                print(f"   -> Summary: {analysis.summary[:100]}...")
                
            except Exception as e:
                print(f"   -> LỖI: {e}")
                writer.writerow([wav_file.name, f"Lỗi: {e}", "", "", "", "", "", "", "", ""])
                f.flush()

    print(f"\n[+] HOÀN TẤT! File review được lưu tại: {output_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy STT và LLM để tạo CSV cho người gán nhãn kiểm tra")
    parser.add_argument("--audio-dir", type=Path, default=Path("data"), help="Thư mục chứa các file .wav")
    parser.add_argument("--output", type=Path, default=Path("data/ground_truth_review.csv"), help="CSV kết quả")
    parser.add_argument("--limit", type=int, default=0, help="Số file đầu tiên cần xử lý; 0 là tất cả")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit phải lớn hơn hoặc bằng 0")
    asyncio.run(main(args.audio_dir, args.output, args.limit))
