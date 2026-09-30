import sys
import asyncio
import csv
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.audio_service import transcribe_audio
from app.services.llm_service import llm_service

async def main():
    data_dir = Path("data")
    wav_files = sorted(list(data_dir.glob("*.wav")))
    
    if not wav_files:
        print("Không tìm thấy file .wav nào trong thư mục data/")
        return
        
    output_csv = data_dir / "ground_truth_review.csv"
    print(f"[*] Bắt đầu quy trình Auto-Labeling cho {len(wav_files)} files...")
    
    with open(output_csv, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "File_Name", 
            "Transcript_Raw", 
            "AI_Status_Group", 
            "AI_Reason_Code", 
            "AI_Appointment_Date", 
            "AI_Summary",
            "Human_Status_Group (Điền tay)",
            "Human_Reason_Code (Điền tay)"
        ])
        
        for i, wav_file in enumerate(wav_files, 1):
            print(f"\n[{i}/{len(wav_files)}] Đang phân tích: {wav_file.name}")
            try:
                # 1. Chạy STT
                stt_result = transcribe_audio(wav_file)
                transcript = stt_result["text"].strip()
                
                # 2. Chạy LLM
                analysis = await llm_service.analyze_audio(transcript, contact_name="Ứng viên")
                
                # 3. Ghi kết quả
                writer.writerow([
                    wav_file.name,
                    transcript,
                    analysis.status_group,
                    analysis.reason_code,
                    analysis.appointment_date,
                    analysis.summary,
                    "", # Cột trống cho người điền
                    ""  # Cột trống cho người điền
                ])
                f.flush()
                print(f"   -> Đã gán nhãn: Nhóm {analysis.status_group} ({analysis.reason_code})")
                
            except Exception as e:
                print(f"   -> LỖI: {e}")
                writer.writerow([wav_file.name, f"Lỗi: {e}", "", "", "", "", "", ""])
                f.flush()

    print(f"\n[+] HOÀN TẤT! File review được lưu tại: {output_csv}")

if __name__ == "__main__":
    asyncio.run(main())
