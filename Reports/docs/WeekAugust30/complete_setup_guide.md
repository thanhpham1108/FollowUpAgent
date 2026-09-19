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
| **11434** | Ollama | LLM inference (Qwen2.5 7B) |
| **5433** | PostgreSQL | Database lưu kết quả |
| **8001** | File Server (test) | Giả lập CRM phục vụ file audio |
| **8002** | Adminer (tùy chọn) | Web UI để xem database |
