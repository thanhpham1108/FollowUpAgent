import sys
import asyncio
import csv
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.audio_service import transcribe_audio
from app.services.llm_service import llm_service

async def main():
    data_dir = Path("data")
    wav_files = sorted(list(data_dir.glob("*.wav")))
    if not wav_files:
        # Fallback tìm các file .wav ở thư mục gốc
        wav_files = sorted(list(Path(".").glob("*.wav")))
    
    if not wav_files:
        print("Không tìm thấy file .wav nào trong thư mục data/ hoặc thư mục dự án.")
        return

    data_dir.mkdir(exist_ok=True)
    output_csv = data_dir / "ground_truth_review.csv"
    if output_csv.exists():
        output_csv = data_dir / f"ground_truth_review_{datetime.now():%Y%m%d_%H%M%S}.csv"
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
    asyncio.run(main())
