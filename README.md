# FollowUpAgent

FastAPI nhận cuộc gọi tuyển dụng từ CRM, tải audio, chuyển lời nói thành transcript, phân loại bằng Ollama, tạo lịch follow-up và gửi kết quả về webhook. Code chạy trong `backend/`; dữ liệu và tài liệu nằm riêng.

## Cấu trúc repo

```text
backend/
  app/
    api/              FastAPI endpoints
    audio/            tải audio, STT, chuẩn hóa transcript
    classification/   reason code, prompt, Ollama
    followup/         lịch chăm sóc
    integrations/     webhook CRM
    core/             cấu hình, database, models
    schemas/          request/response
  scripts/            tải recording, gán nhãn, load test
  tests/             kiểm tra hành vi hiện hành
  eval/              bộ đánh giá LLM và dữ liệu mẫu
  perf/              Locust
  deploy/            systemd
Reports/                 báo cáo, slide và tài liệu lịch sử (có trong Git)
thanh-workspace/         hướng dẫn đang dùng, ghi chú và API contract (có trong Git)
data/                   audio và CSV chạy thực tế (không đưa vào Git)
.env.example            mẫu cấu hình; `.env` thật ở repo root
```

## Chạy trên server

Các lệnh dưới đây chạy từ **repo root** (`~/datacore/FollowUpAgent`); `.env` và `data/` vẫn ở root. Cần Python 3.10+, PostgreSQL và Ollama đang chạy. Cài dependency theo môi trường CUDA của server rồi cài `backend/requirements.txt`.

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn --app-dir backend app.main:app --host 0.0.0.0 --port 18000
```

Nếu dùng systemd, file unit ở `backend/deploy/followup-agent.service`; cài lại unit sau khi chuyển cấu trúc:

```bash
bash backend/deploy/setup_service.sh
```

## Script và tài liệu

```bash
python backend/scripts/download_recordings.py --out-dir data/recordings_import --select all --download
python backend/scripts/auto_label_ground_truth.py --limit 10
PYTHONPATH=backend python -m eval.run_eval
```

Script gán nhãn mặc định đọc `data/recordings_import/audio` và ghi CSV/trace vào `data/recordings_import`; nó không tự xác nhận ground truth. Xem [hướng dẫn tải audio](thanh-workspace/guides/audio-from-crm-api.md), [quy tắc gán nhãn hiện tại](thanh-workspace/guides/labeling-guideline.md), [ghi chú workspace](thanh-workspace/README.md) và [mục lục báo cáo](Reports/README.md).

### Chép WAV bằng Gipformer

Đặt WAV trong `data/recordings_import/audio/` và chạy từ thư mục gốc với [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uv run backend/scripts/transcribe_gipformer.py
```

Script chọn WAV theo thứ tự tên file, từ `18483292.wav` đến `22052024.wav` tính cả hai đầu (352 file trên bộ đầy đủ). Gipformer chạy trên CPU và chép riêng từng kênh theo khoảng 20 giây. Có thể dùng `--audio-dir` để đổi thư mục, hoặc `--limit 3` để chép thử ba file đầu.

Đầu ra là `data/recordings_import/gipformer_18483292_22052024.jsonl`, một dòng cho mỗi WAV. Chạy lại cùng lệnh để tiếp tục từ dòng đã lưu cuối cùng. File JSONL này dùng riêng cho phạm vi mới. `PHOWHISPER_MODEL` vẫn là cấu hình của dịch vụ FastAPI. Kiểm tra thông tin cá nhân trong transcript trước khi chia sẻ.

Không đưa `.env`, audio, CSV nhãn hoặc model weights vào Git.
