# Chạy lại nhãn AI cho 713 recording trên server

Thực hiện từ `~/datacore/FollowUpAgent` trên `ood-master`, trong Conda env `datacore`. Script chỉ đọc WAV và ghi CSV review; nó **không** cập nhật database, tạo lịch follow-up hay gửi webhook CRM. Hai cột Human vẫn để trống để bạn nghe và điền nhãn thật.

## 1. Lấy phiên bản logic mới

Nếu server chưa có nhánh `refactor/repo-layout`:

```bash
cd ~/datacore/FollowUpAgent
git status --short
git fetch origin refactor/repo-layout
git switch --track origin/refactor/repo-layout
```

Nếu đã có nhánh này trên server, dùng `git switch refactor/repo-layout` và `git pull --ff-only`. Nếu `git switch` báo file local cản trở, dừng và xem `git status`; không dùng `reset --hard` hoặc xóa CSV/audio để ép chuyển nhánh.

## 2. Kiểm tra audio và Ollama

```bash
conda activate datacore
find data/recordings_import/audio -maxdepth 1 -type f -name '*.wav' | wc -l
ollama list
```

Số WAV phải là **713**. Ở một terminal khác, giữ `ollama serve` đang chạy nếu chưa có tiến trình Ollama. Cấu hình model và STT đọc từ `.env` ở repo root; mặc định STT là PhoWhisper. Nếu muốn dùng Whisper v3 Turbo, phải xác nhận cấu hình server trước khi bắt đầu vì tên CSV thử nghiệm trên Mac không thay đổi model của server.

## 3. Chạy 10 file đầu

Dùng tên output mới để không resume nhầm CSV của taxonomy cũ. Script kiểm tra đủ 713 WAV trước khi xử lý 10 file đầu:

```bash
python backend/scripts/auto_label_ground_truth.py \
  --audio-dir data/recordings_import/audio \
  --output data/recordings_import/ground_truth_review_713_merged.csv \
  --expected-count 713 \
  --limit 10 --resume
```

Trong bộ ID đã gửi, `18522754.wav` và `18571597.wav` nằm trong 10 tên đầu khi sắp xếp. Kiểm tra hai dòng này, nghe audio và đọc summary; kết quả mong đợi lần lượt là `DI_LAM` và `HEN_PHONG_VAN` với ngày hẹn phỏng vấn trống. Đây là mốc so sánh, không đảm bảo model sẽ tự ra đúng; nếu lệch, xem trace trước khi chạy tiếp.

Đọc nhanh các cột quan trọng mà không phải mở toàn bộ transcript dài:

```bash
python - <<'PY'
import csv
from pathlib import Path

path = Path('data/recordings_import/ground_truth_review_713_merged.csv')
with path.open(encoding='utf-8-sig', newline='') as handle:
    rows = list(csv.DictReader(handle))
print('Số dòng thành công:', len(rows))
for row in rows:
    if row['File_Name'] in {'18522754.wav', '18571597.wav'}:
        print('\n', row['File_Name'], row['AI_Reason_Code'], row['AI_Status_Group'])
        print('Ngày phỏng vấn:', row['AI_Appointment_Date'] or 'null')
        print('Summary:', row['AI_Summary'])
PY
```

## 4. Chạy toàn bộ và tiếp tục khi bị ngắt

Sau khi 10 file đầu ổn, chạy lại cùng output **không có `--limit`**. `--resume` bỏ qua các dòng đã thành công và thử lại file chưa có trong CSV:

```bash
python backend/scripts/auto_label_ground_truth.py \
  --audio-dir data/recordings_import/audio \
  --output data/recordings_import/ground_truth_review_713_merged.csv \
  --expected-count 713 --resume
```

Nếu Ollama/STT ngắt hoặc script dừng sau 5 lỗi liên tiếp, khôi phục dịch vụ rồi **chạy lại đúng lệnh trên**. Không đổi tên output giữa các lần chạy, không mở rồi lưu CSV bằng Excel khi script đang ghi. Script chạy tuần tự; nó không có tùy chọn bỏ qua STT để chỉ phân loại lại transcript cũ.

Ba file kết quả cạnh nhau:

- `ground_truth_review_713_merged.csv`: dòng AI thành công, giữ nguyên hai cột Human để bạn điền tay.
- `ground_truth_review_713_merged_decision_trace.jsonl`: output LLM từng lượt, câu bằng chứng, kết quả kiểm tra và quyết định cuối.
- `ground_truth_review_713_merged_error_log.csv`: lỗi hoặc ca cần nghe lại. File có thể chưa tồn tại nếu chưa có lỗi.

Error log là lịch sử các lần lỗi; một file đã lỗi có thể thành công ở lần resume sau. Đếm dòng thành công trong CSV thay vì `wc -l`, vì transcript có thể chứa xuống dòng. Chỉ khi nghe audio và điền cột Human thì CSV mới trở thành ground truth để đánh giá model.

**Lưu ý ngày:** Prompt lấy ngày hiện tại trên server. Với recording được ghi vào ngày khác, “mai”, “thứ Hai tới”, “ngày 13/14” cần được người nghe đối chiếu lại với thời điểm cuộc gọi trước khi điền Human appointment date.
