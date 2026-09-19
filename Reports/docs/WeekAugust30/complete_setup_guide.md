# Hướng Dẫn Cài Đặt & Test FollowUpAgent (Từ A-Z Cho Máy Mới)

Tài liệu này dành cho một server Linux hoàn toàn mới. Hãy mở **3 Tab Terminal** và thực hiện tuần tự không bỏ sót bước nào.

---

## PHẦN 1: Chuẩn bị môi trường & Source Code (Tab 1)

**1. Tải source code:**
```bash
git clone https://github.com/thanhpham1108/FollowUpAgent.git
cd FollowUpAgent
```

**2. Cài đặt Conda & Các thư viện lõi:**
```bash
# Tạo môi trường Python 3.10
conda create -n datacore python=3.10 -y
conda activate datacore

# Cài đặt các thư viện Python
pip install -r requirements.txt

# Cài đặt thư viện xử lý âm thanh (Bắt buộc cho PhoWhisper)
conda install -c conda-forge ffmpeg -y
```

---

## PHẦN 2: Cài đặt Database PostgreSQL (Tab 1)

Không dùng Docker, chúng ta cài trực tiếp Postgres qua Conda:

```bash
# Cài đặt Postgres
conda install -c conda-forge postgresql -y

# Khởi tạo data directory (Chỉ chạy 1 lần)
initdb -D ~/pgdata

# Khởi động Database Server
pg_ctl -D ~/pgdata -l ~/pgdata/logfile start

# Tạo Database và User (Thay cổng 5432 hoặc 5433 tùy máy)
createdb -h localhost followup_agent -p 5433
psql -h localhost -p 5433 -d followup_agent -c "CREATE USER thanhpnc WITH PASSWORD 'password';"
```

---

## PHẦN 3: Cài đặt AI & Ollama (Tab 1)

Cài đặt bản Ollama Standalone (Không cần quyền Admin):

```bash
# Tải công cụ giải nén
conda install -c conda-forge zstd -y

# Tải và giải nén động cơ Ollama
curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -xf -

# Khởi động Ollama (chạy ngầm)
# OLLAMA_KEEP_ALIVE=-1 giữ model thường trực trên VRAM, tránh mất 90 giây nạp lại mỗi lần cold start
OLLAMA_KEEP_ALIVE=-1 ./bin/ollama serve &

# Tải model AI về máy (File nặng 4.7GB, chạy lần đầu sẽ mất chút thời gian)
./bin/ollama run qwen2.5:7b-instruct
```
*(Đợi model tải xong, gõ `/bye` để thoát giao diện chat của Ollama).*

---

## PHẦN 4: Cấu hình .env & Khởi động API Server (Tab 1)

**1. Cấu hình file biến môi trường:**
```bash
cp .env.example .env
nano .env
```
Đảm bảo 2 dòng quan trọng sau được cập nhật (Tạo URL Webhook miễn phí tại `webhook.site`):
```text
DATABASE_URL=postgresql+asyncpg://thanhpnc:password@localhost:5433/followup_agent
WEBHOOK_URL=https://webhook.site/xxxx-xxxx-xxxx-xxxx
```

**2. Bật API Server:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 18000
```
*(Nếu thành công, log sẽ báo: `Application startup complete`)*. Đứng nguyên tab 1 này để xem log AI.

---

## PHẦN 5: Giả lập CRM File Server (Tab 2)

Hệ thống bắt buộc phải tải file từ một đường link Web. Vì vậy ta phải bật một server giả lập.

**1. Đảm bảo có file audio:**
Tải 1 file `.wav` mẫu vào thư mục `FollowUpAgent` (Ví dụ file: `test_audio.wav`).

**2. Bật Server giả lập CRM:**
```bash
# Mở tab 2, kích hoạt môi trường và vào đúng thư mục code
conda activate datacore
cd ~/datacore/FollowUpAgent

# Bật web server
python -m http.server 8001
```
*(Lưu ý: Nếu bị báo lỗi 404 khi tải file, chắc chắn 100% là do bạn đang chạy lệnh này ở sai thư mục, hoặc file âm thanh chưa được copy vào thư mục đó).*

---

## PHẦN 6: Bắn Test E2E (Tab 3)

Mở **Tab Terminal thứ 3** và thực thi lệnh cURL để giả lập CRM gọi sang hệ thống của chúng ta:

```bash
curl -X POST http://localhost:18000/api/v1/candidates/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ssn": "999888777",
    "candidate_name": "Nguyen Van Test",
    "audio_url": "http://localhost:8001/test_audio.wav"
  }'
```

**✅ Kịch bản thành công hoàn hảo:**
1. Tab 1 sẽ báo nhận request.
2. Tab 2 sẽ báo `GET /test_audio.wav 200 OK` (File đã được tải).
3. Tab 1 sẽ chạy PhoWhisper bóc băng (STT).
4. Tab 1 sẽ gọi Qwen2.5 để phân tích.
5. Tab 1 sẽ báo bắn Webhook thành công sang `webhook.site`.
6. Database lưu lại lịch sử với trạng thái `COMPLETED`.

---

## PHẦN 7: Kiểm tra Database (Tab 3)

Để biết chắc chắn hệ thống đã phân tích và lưu thành công hay chưa, hãy gõ lệnh sau để truy vấn Database:

```bash
psql -h localhost -p 5433 -d followup_agent -U thanhpnc -c "SELECT contact_name, status, intent, summary FROM call_records ORDER BY created_at DESC LIMIT 1;"
```
*(Nếu cổng DB của bạn là 5432 thì thay số 5433 thành 5432).*

**Kết quả thành công:** Cột `status` hiển thị chữ `COMPLETED` và các cột `intent`, `summary` có chứa nội dung AI tóm tắt.

---

## PHẦN 8: Xem Database qua Web UI — Adminer (Tùy chọn)

Nếu muốn xem toàn bộ database bằng giao diện web thay vì gõ lệnh psql:

```bash
# Tab 2 hoặc Tab 3 — Tải Adminer (file PHP đơn lẻ, ~500KB)
wget https://github.com/vrana/adminer/releases/download/v4.8.1/adminer-4.8.1.php

# Chạy Adminer trên cổng 8002 (dùng PHP built-in server)
php -S 0.0.0.0:8002 adminer-4.8.1.php
```

Sau đó mở trình duyệt và truy cập `http://<IP_SERVER>:8002/adminer-4.8.1.php` và đăng nhập:
- **System:** PostgreSQL
- **Server:** `localhost:5433`
- **Username:** `thanhpnc`
- **Password:** `password`
- **Database:** `followup_agent`

> **Lưu ý:** Nếu máy không có PHP, có thể cài nhanh bằng `sudo apt install php -y` hoặc `conda install -c conda-forge php -y`.

---

## PHẦN 9: Các Lỗi Hay Gặp & Cách Xử Lý

### ❌ Cổng 8080 bị Apache chiếm
**Triệu chứng:** cURL nhận về HTML "301 Moved Permanently" thay vì JSON.
**Fix:** Đổi sang cổng `18000`:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 18000
```

### ❌ File audio 404 Not Found
**Triệu chứng:** Log báo `CRM phản hồi mã lỗi: 404` khi đang tải file.
**Fix:** Đảm bảo `python -m http.server 8001` được chạy **đúng trong thư mục chứa file `.wav`**:
```bash
cd /home/thanhpnc/datacore/FollowUpAgent   # ← PHẢI CD vào đây trước!
python -m http.server 8001
```

### ❌ Ollama timeout ở lần đầu tiên
**Triệu chứng:** Log báo `Lỗi kết nối tới Ollama` sau 2 phút. Log Ollama báo `llama-server started in ~90 seconds`.
**Nguyên nhân:** Lần đầu tiên Ollama cần ~90 giây để nạp model 4.7GB lên VRAM.
**Fix:** Bắn lại cURL ngay sau khi Ollama khởi động xong. Code đã được sửa `timeout=300s` để phòng hờ.

### ❌ Xung đột cổng (Address already in use)
**Triệu chứng:** Uvicorn báo `ERROR: [Errno 98] address already in use`.
**Fix:** Giết tiến trình đang chiếm cổng:
```bash
fuser -k 18000/tcp   # Giết tiến trình đang dùng cổng 18000
# Hoặc:
pkill -u $USER -f uvicorn
```

### ❌ git pull bị lỗi xác thực VSCode
**Triệu chứng:** `Error: connect ENOENT /run/user/xxx/vscode-git-xxx.sock`
**Fix:** Dùng lệnh này thay thế (bypass credential helper của VSCode):
```bash
env -u GIT_ASKPASS git pull origin main
```

---

## Danh sách cổng sử dụng (Tổng kết)

| Cổng | Dịch vụ | Ghi chú |
|------|---------|---------| 
| **18000** | FastAPI (Uvicorn) | API chính của hệ thống |
| **11434** | Ollama | LLM inference (Qwen2.5 7B + Llama3.1 Judge) |
| **5433** | PostgreSQL | Database lưu kết quả |
| **8001** | File Server (test) | Giả lập CRM phục vụ file audio |
| **8002** | Adminer (tùy chọn) | Web UI để xem database |
| **8089** | Locust Web UI | Load testing dashboard |

---

## PHẦN 10: Evaluation Pipeline — Đánh giá chất lượng LLM (Tab 1)

Pipeline này dùng **Llama3.1 làm Giám khảo** để chấm điểm kết quả phân tích của **Qwen2.5 (Worker)**. Hai model khác nhau để tránh self-enhancement bias.

### Bước 1: Cài Llama3.1 (Giám khảo)

```bash
# Đảm bảo Ollama đang chạy (PHẦN 3), rồi tải model Judge về
./bin/ollama pull llama3.1
```
*(File ~4.9GB, chờ tải xong. Chỉ cần làm 1 lần.)*

Kiểm tra 2 model đã sẵn sàng:
```bash
./bin/ollama list
# Kết quả phải có đủ 2 dòng:
# qwen2.5:7b-instruct   ...
# llama3.1              ...
```

### Bước 2: Cấu hình biến môi trường cho Eval

Mở file `.env` và đảm bảo 2 dòng sau tồn tại:
```text
# Judge Model — BẮT BUỘC khác với OLLAMA_MODEL_NAME
JUDGE_OLLAMA_BASE_URL=http://localhost:11434/v1
JUDGE_MODEL_NAME=llama3.1
```

> **Lưu ý máy RAM thấp (< 16GB):** Nếu không đủ RAM chạy 2 model cùng lúc, dùng model nhỏ hơn làm Judge:
> ```text
> JUDGE_MODEL_NAME=llama3.2
> ```
> Rồi tải: `./bin/ollama pull llama3.2`

### Bước 3: Chạy Evaluation

```bash
conda activate datacore
cd ~/datacore/FollowUpAgent

python -m tests.eval.run_eval
```

**Output mẫu kỳ vọng:**
```
[Pre-check] Kiểm tra Judge Model (llama3.1)... OK ✅
[Info] Bắt đầu eval 8 samples...

================================================================================
  FollowUpAgent — LLM-as-a-Judge Evaluation Report
  Worker : qwen2.5:7b-instruct  |  Judge : llama3.1
  Run at : 2026-09-19 14:30:00
================================================================================

  Đang xử lý [01/08] case_01_hung_up... done
  [01] case_01_hung_up          Group: ✅ (2→2)  Code: ✅ (KNM_1→KNM_1)  Hallucination: 5/5  Logic: 5/5

  ...

================================================================================
  TỔNG KẾT
================================================================================
  📊 Deterministic (Exact Match)
     Status Group Accuracy : 7/8 (87.5%)
     Reason Code Accuracy  : 6/8 (75.0%)

  🤖 Judge Score (Llama3.1 chấm Qwen2.5)
     Avg Hallucination Score : 4.75/5.00  🟢
     Avg Logic Score         : 4.25/5.00  🟢
================================================================================

  📄 Full report saved: tests/eval/reports/eval_report_20260919_143000.json
```

### Bước 4: Đọc kết quả và Bootstrap Ground Truth

Sau khi chạy lần đầu, report JSON được lưu tại `tests/eval/reports/`. Mở file đó ra:
- Xem `critique` của từng sample (Judge giải thích lý do chấm điểm).
- Những case Worker bị sai (`group_match: false`) → sửa lại Prompt trong `app/prompts/` để cải thiện.
- Muốn thêm sample mới → append vào `tests/eval/dataset/samples.json`.

---

## PHẦN 11: Load Testing — Đánh giá chịu tải (Tab 2 & 3)

Kiểm tra hệ thống có chịu được nhiều CRM request bắn vào cùng lúc không.

### Bước 1: Cài thư viện Dev/Test (Chỉ làm 1 lần)

```bash
conda activate datacore
pip install -r requirements-dev.txt
```
*(File này cài `locust`, `pytest`, `pytest-asyncio` — không nhét vào `requirements.txt` production)*

### Bước 2: Đảm bảo API Server đang chạy

Tab 1 phải đang chạy:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 18000
```

### Bước 3A: Chạy Load Test có UI (Local / Có trình duyệt)

```bash
# Tab 2
conda activate datacore
cd ~/datacore/FollowUpAgent

locust -f tests/load_test/locustfile.py --host http://localhost:18000
```

Mở trình duyệt → `http://<IP_SERVER>:8089`
- **Number of users:** `20` (giả lập 20 CRM đồng thời)
- **Spawn rate:** `2` (tăng dần 2 user/giây)
- Bấm **Start swarming** và theo dõi biểu đồ.

### Bước 3B: Chạy Load Test không UI — Headless (Server không có trình duyệt)

```bash
# Chạy 20 users, spawn 2/giây, kéo dài 60 giây, tự tắt
locust -f tests/load_test/locustfile.py \
  --host http://localhost:18000 \
  --headless \
  -u 20 -r 2 -t 60s
```

**Nếu server không ra được internet** (audio URL public không tải được):
```bash
# Copy 1 file wav vào thư mục data/ và bật file server (Tab 3)
python -m http.server 8001 --directory ./data

# Set biến môi trường để Locust dùng URL nội bộ
export LOCUST_AUDIO_URL=http://localhost:8001/test_audio.wav

# Rồi chạy lại Locust
locust -f tests/load_test/locustfile.py --host http://localhost:18000 --headless -u 20 -r 2 -t 60s
```

### Bước 4: Đọc kết quả Load Test

Chú ý 3 chỉ số quan trọng:

| Chỉ số | Ngưỡng ổn | Ngưỡng cảnh báo |
|--------|-----------|-----------------|
| **Response Time (P95)** | < 500ms (cho 202 Accepted) | > 2000ms |
| **Failure Rate** | < 1% | > 5% |
| **Requests/sec** | Tùy server, baseline lần đầu | So sánh qua các lần chạy |

> **Lưu ý quan trọng:** Load test chỉ đo tốc độ API trả về **202 Accepted** (nhận request).
> Background task (STT + LLM) chạy ngầm — không đo được qua Locust.
> Để theo dõi background queue: xem log Tab 1 hoặc query DB: `SELECT status, COUNT(*) FROM call_records GROUP BY status;`

---

## PHẦN 12: Các Lỗi Hay Gặp (Eval & Load Test)

### ❌ `Judge Model chưa sẵn sàng` khi chạy run_eval.py
**Nguyên nhân:** Chưa pull `llama3.1` về Ollama.
```bash
./bin/ollama pull llama3.1
```

### ❌ Eval báo lỗi `ModuleNotFoundError: No module named 'app'`
**Nguyên nhân:** Chạy sai thư mục.
```bash
# PHẢI chạy từ thư mục gốc của project
cd ~/datacore/FollowUpAgent
python -m tests.eval.run_eval   # ← Dùng -m, không dùng python tests/eval/run_eval.py
```

### ❌ Locust báo `Connection refused` ngay khi start
**Nguyên nhân:** API server chưa chạy hoặc chạy sai cổng.
```bash
# Kiểm tra server đang lắng nghe cổng nào
ss -tlnp | grep python
# Nếu server đang chạy cổng 18000 nhưng Locust chỉ định 8000:
locust -f tests/load_test/locustfile.py --host http://localhost:18000
```

### ❌ Judge cho điểm toàn 5/5 — nghi ngờ không đáng tin
**Nguyên nhân:** Model nhỏ quá (không đủ năng lực phán xét) hoặc Prompt quá dễ tính.
**Fix:** Kiểm tra phần `critique` trong JSON report. Nếu critique chỉ là 1 câu chung chung → Model judge không đủ mạnh, thử dùng `llama3.1:70b` (cần server RAM lớn) hoặc đổi sang API cloud.
```text
# .env
JUDGE_MODEL_NAME=llama3.1:70b
```
