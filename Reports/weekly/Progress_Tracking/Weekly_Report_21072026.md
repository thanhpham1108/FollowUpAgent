# Báo cáo Tiến độ (Progress Report)
**Ngày lập báo cáo**: 21/07/2026
**Người thực hiện**: Trần Nguyễn Quỳnh Như
**Giai đoạn**: Hoàn tất cơ sở hạ tầng hệ thống (Infrastructure Layer)

---

## 1. Tóm tắt kết quả đạt được

Trong chu kỳ này (19/07 – 20/07/2026), team đã tập trung xây dựng và hoàn thiện **tầng cơ sở hạ tầng (Infrastructure Layer)** của dự án FollowUpAgent. Các công việc bao gồm: khởi tạo cơ sở dữ liệu SQLAlchemy, chuẩn hóa hệ thống ghi log, quản lý file tạm, xử lý lỗi API thống nhất, và đưa vào hệ thống các template Prompt tiếng Việt chuyên biệt cho module AI.

Tổng cộng: **6 commits**, **15 files thay đổi**, **~412 dòng code mới**.

---

## 2. Chi tiết các hạng mục đã triển khai

### 2.1. Cơ sở dữ liệu – SQLAlchemy ORM (`app/core/database.py`)

- Khởi tạo kết nối cơ sở dữ liệu SQLite qua SQLAlchemy với các thành phần:
  - `engine`: quản lý kết nối ở mức thấp, bật `check_same_thread=False` tương thích với FastAPI async.
  - `SessionLocal`: factory tạo session giao dịch (`autocommit=False`, `autoflush=False`).
  - `Base`: class nền cho toàn bộ model ORM trong dự án.
  - `get_db()`: hàm generator chuẩn FastAPI Dependency Injection để inject DB session vào từng API route.
- Thêm thư viện `sqlalchemy>=2.0.0` vào `requirements.txt`.
- Đưa vào file CSDL test `test.db` (28KB) để kiểm thử cục bộ.

---

### 2.2. Hệ thống ghi log (`app/utils/logger.py`)

- Xây dựng module `logger.py` cấu hình logging theo chuẩn production:
  - Ghi log ra **2 kênh song song**: Console (stdout) và File (`logs/followup_agent.log`).
  - Dùng `RotatingFileHandler` giới hạn dung lượng tối đa **10MB/file**, giữ lại **5 bản backup** tự động.
  - Định dạng log: `[YYYY-MM-DD HH:MM:SS] [LEVEL] [module_name] message`.
  - Hàm `get_logger(name)` cho phép mọi module trong dự án khởi tạo logger nhất quán chỉ bằng 1 dòng lệnh.
  - Cấu hình log level đọc trực tiếp từ biến môi trường `LOG_LEVEL` (trong file `.env`).

---

### 2.3. Quản lý file âm thanh tạm (`app/utils/file_manager.py`)

- Bổ sung 4 hàm tiện ích hỗ trợ vòng đời file trong thư mục tạm:
  - `ensure_data_dir()`: tạo thư mục lưu file tải về nếu chưa tồn tại, an toàn với đa luồng.
  - `cleanup_audio(file_path)`: xóa một file âm thanh tạm cụ thể sau khi xử lý xong, không raise exception.
  - `cleanup_orphaned_files(max_age_hours)`: quét toàn bộ thư mục tạm, xóa các file cũ hơn ngưỡng giờ cấu hình — dùng cho cron job định kỳ khi process bị crash khiến khối `finally` không chạy được.
  - `cleanup_dir(dir_path, remove_root)`: dọn dẹp toàn bộ nội dung một thư mục, có tuỳ chọn xóa cả thư mục gốc.

---

### 2.4. Xử lý lỗi thống nhất (`app/core/exceptions.py`)

- Xây dựng bộ Custom Exception Handler để chuẩn hóa cấu trúc JSON trả về khi có lỗi:
  - Handler cho `HTTPException` (lỗi 4xx, 5xx từ logic nghiệp vụ).
  - Handler cho `RequestValidationError` (lỗi validate Pydantic request body/query params).
  - Toàn bộ lỗi đều trả về cấu trúc `{"detail": "...", "status_code": ...}` nhất quán, tránh trả về HTML mặc định của FastAPI.
- Đăng ký các handler này vào `app.main` để hoạt động trên toàn bộ ứng dụng.

---

### 2.5. Dependency Injection (`app/api/dependencies.py`)

- Tạo module tập trung chứa các FastAPI dependency dùng chung:
  - Dependency xác thực header / API Key cho các route cần bảo vệ.
  - Dependency kiểm tra rate-limit và các tham số chung.
- Cấu trúc giúp các endpoint không bị lặp code xác thực, dễ mở rộng thêm middleware.

---

### 2.6. Endpoint kiểm tra sức khỏe hệ thống (`app/api/v1/endpoints/health.py`)

- Mở rộng endpoint `/health` trả về thông tin trạng thái chi tiết hơn:
  - Trạng thái kết nối Database (SQLite / PostgreSQL).
  - Phiên bản ứng dụng và môi trường (`APP_ENV`).
  - Thời gian uptime server.
- Hữu ích cho môi trường Docker để cấu hình `HEALTHCHECK` tự động.

---

### 2.7. Chuẩn hóa Prompt cho AI (`app/prompts/`)

#### `app/prompts/system_prompts.py`
- Định nghĩa biến `SYSTEM_PROMPT` bằng tiếng Việt, định hình vai trò AI là **chuyên viên phân tích cuộc gọi**.
- Các ràng buộc bắt buộc được đưa vào prompt:
  1. Luôn trả lời bằng tiếng Việt.
  2. Trả về đúng định dạng JSON thuần, **không bọc trong markdown code block** (tránh lỗi parse).
  3. Giữ thái độ trung lập, không suy diễn cảm tính.
  4. Nếu thiếu thông tin, ghi rõ sự không chắc chắn trong `summary`, không được bịa.

#### `app/prompts/analysis_prompts.py`
- Định nghĩa `ANALYSIS_PROMPT` chi tiết cho luồng phân tích ứng viên (HR flow):
  - Mô tả rõ 5 nhóm nghiệp vụ (`status_group` 1–5) và các mã lý do tương ứng.
  - Template prompt dùng f-string với placeholder `{contact_name}` và `{context_data}` để inject dữ liệu động.
  - Gò output AI theo schema JSON chuẩn: `{"summary", "status_group", "reason_code", "appointment_date", "recommended_message"}`.

---

### 2.8. Dữ liệu kiểm thử

- Đưa vào file âm thanh mẫu `22685287.pcm.wav` (~2.4MB) phục vụ test luồng Speech-to-Text cục bộ.

---

## 3. Khó khăn / Điểm nghẽn (Blockers)

| # | Vấn đề | Mức độ | Ghi chú |
|---|--------|--------|---------|
| 1 | **Webhook chưa ổn định** | ⚠️ Trung bình | Module `webhook_service.py` hiện gặp lỗi khi serialize payload Pydantic chứa kiểu `datetime`/`Enum` sang JSON. Cần sửa `model_dump()` → `model_dump(mode="json")`. Thêm nữa, các biến `WEBHOOK_URL`, `CRM_WEBHOOK_URL` chưa được cấu hình trong `.env` nên hệ thống tự ngắt khi gọi. |
| 2 | **Thiếu môi trường GPU** | 🔴 Cao | Chưa thể test end-to-end với model PhoWhisper và LLM GGUF thực tế do thiếu server GPU. |
| 3 | **CRM API Contract** | 🟡 Thấp | Đang chờ tài liệu API chính thức từ phía CRM đối tác để căn chỉnh format dữ liệu đầu ra. |

---

## 4. Kế hoạch tiếp theo (Next Steps)

- [ ] **Sửa lỗi Webhook**: cập nhật `model_dump(mode="json")` và cấu hình đủ các biến `.env` liên quan.
- [ ] **Test E2E nội bộ**: dùng file `22685287.pcm.wav` vừa thêm vào để test toàn bộ luồng Audio → STT → LLM → Rule Engine → DB (với SQLite local).
- [ ] **Containerize**: cập nhật `Dockerfile` và `docker-compose.yml` tích hợp service Database (PostgreSQL) và đảm bảo `HEALTHCHECK` endpoint hoạt động đúng.
- [ ] **Kết nối CRM thực tế**: khi có API Contract từ đối tác, tiến hành ánh xạ schema webhook và test giao tiếp hai chiều.

---

*Báo cáo được tổng hợp tự động từ Git commit history ngày 19/07/2026 – 20/07/2026.*
