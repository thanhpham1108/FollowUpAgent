import os
import csv
import torch
from transformers import pipeline
from pathlib import Path

def determine_device():
    if torch.cuda.is_available():
        try:
            torch.zeros(1, device="cuda:0")
            return "cuda:0"
        except Exception:
            return "cpu"
    return "cpu"

def main():
    data_dir = Path("data")
    if not data_dir.exists():
        print(f"Lỗi: Không tìm thấy thư mục {data_dir}")
        return

    wav_files = sorted(list(data_dir.glob("*.wav")))
    if not wav_files:
        print(f"Không tìm thấy file .wav nào trong {data_dir}")
        return

    print(f"[*] Tìm thấy {len(wav_files)} file âm thanh. Đang nạp mô hình AI...")
    device = determine_device()
    model_name = "vinai/PhoWhisper-large"
    
    print(f"[*] Đang tải và nạp {model_name} lên {device}...")
    transcriber = pipeline(
        "automatic-speech-recognition",
        model=model_name,
        device=device
    )

    output_csv = data_dir / "transcripts.csv"
    print(f"[*] Bắt đầu bóc băng. Kết quả sẽ được lưu tại {output_csv}")

    # Dùng utf-8-sig để Excel trên Windows hiển thị đúng tiếng Việt
    with open(output_csv, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["File_Name", "Transcript"])

        for i, wav_file in enumerate(wav_files, 1):
            print(f"[{i}/{len(wav_files)}] đang xử lý: {wav_file.name}...")
            try:
                result = transcriber(str(wav_file))
                transcript = result["text"].strip()
                writer.writerow([wav_file.name, transcript])
                f.flush()  # Lưu ngay lập tức để phòng crash server
            except Exception as e:
                print(f"  -> Lỗi khi xử lý {wav_file.name}: {e}")
                writer.writerow([wav_file.name, f"Lỗi: {e}"])
                f.flush()

    print(f"\n[+] HOÀN THÀNH! Dữ liệu đã được xuất ra: {output_csv}")

if __name__ == "__main__":
    main()
