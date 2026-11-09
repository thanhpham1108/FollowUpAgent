# Báo cáo Tiến độ Tuần — FollowUpAgent
**Ngày báo cáo:** 23/06/2026
**Người thực hiện:** Trần Nguyễn Quỳnh Như
**Giai đoạn:** Phase 1 ✅ Hoàn thành → Phase 2 ✅ Hoàn thành (phần lớn)
**Người theo dõi:** thanhpham1108

---

## 1. Tóm tắt điều hành (Executive Summary)

Trong tuần vừa qua (từ 09/06 – 22/06/2026), dự án **FollowUpAgent** đã đạt được bước tiến vượt kỳ vọng so với kế hoạch ban đầu. Toàn bộ **Phase 2 – AI Pipeline Core** đã được xây dựng hoàn chỉnh với **3 commits lớn** được push lên repository vào ngày **19/06/2026**, bao gồm hơn **600 dòng code** mới trải rộng trên 8 file.

> Hệ thống hiện đã có đủ khung xương (skeleton) để **nhận ghi âm → phân tích bằng AI → gửi kết quả về CRM** — tất cả trong một pipeline kết nối end-to-end.

---

## 2. Công việc đã hoàn thành (Giai đoạn: 09/06 – 22/06/2026)

### 🏗️ 2.1 Tầng Cấu hình & Cơ sở dữ liệu (`app/core/`)

#### `config.py` (+64 dòng) — *Commit: "Add config, database, models" – 19/06*
- Chuyển đổi toàn bộ cấu hình sang **Pydantic BaseSettings v2** — tự động đọc từ file `.env`, không cần hardcode giá trị.
- Tập trung hoàn toàn tất cả các biến môi trường vào một chỗ duy nhất:
  - `WHISPER_MODEL`, `WHISPER_DEVICE` — cấu hình mô hình STT
  - `LLM_MODEL_PATH`, `OLLAMA_BASE_URL` — cấu hình AI cục bộ
  - `WEBHOOK_URL`, `CRM_SALES_WEBHOOK_URL`, `CRM_WEBHOOK_URL` — cấu hình điểm đến CRM
  - `WEBHOOK_MAX_RETRIES`, `WEBHOOK_RETRY_BACKOFF` — cấu hình cơ chế retry
  - `ZALO_OA_ACCESS_TOKEN`, `ZALO_OA_ID` — tích hợp kênh Zalo
  - `FOLLOWUP_SCHEDULE_DAYS` (D+1, D+3, D+7) — lịch gửi follow-up tự động

#### `database.py` (+16 dòng) — *Commit: "Add config, database, models" – 19/06*
- Thiết lập kết nối **PostgreSQL** thông qua SQLAlchemy.
- Cung cấp hàm `get_db()` tương thích với Dependency Injection của FastAPI.

#### `models.py` (+101 dòng) — *Commit: "Add config, database, models" – 19/06*
- Thiết kế **2 bảng database** phục vụ toàn bộ vòng đời xử lý:
  - **`CallRecord`**: Lưu thông tin cuộc gọi đầu vào (context Sales/HR, thông tin liên hệ, URL ghi âm, kết quả transcript, intent, sentiment, summary, recommended_message, trạng thái xử lý).
  - **`FollowUpTask`**: Lưu lịch trình gửi tin nhắn tự động (D+1/D+3/D+7, kênh Zalo/Email, nội dung tin, trạng thái gửi, cho phép bật/tắt thủ công từng task).
- Thiết kế **dual-context**: Một schema duy nhất phục vụ được cả luồng **Sales** (khách hàng CRM) lẫn **HR** (ứng viên phỏng vấn).

---

### 📐 2.2 Định nghĩa Dữ liệu đầu vào/ra (`app/schemas/`)

#### `request.py` (+47 dòng, cập nhật) — *Commit: "schema" – 19/06*
- Tách rõ ràng thành **3 schema** cho 3 luồng nghiệp vụ khác nhau:
  - `SalesCallRequest`: Nhận ghi âm sales call từ CRM (có `customer_id`, `salesperson_id`, Zalo/Email optional).
  - `CandidateAnalyzeRequest`: Nhận ghi âm phỏng vấn HR (có số định danh `ssn`).
  - `FollowUpConfigRequest`: Cho phép nhân viên Sales bật/tắt thủ công từng lịch gửi tin nhắn.

#### `response.py` (+112 dòng, cập nhật) — *Commit: "schema" – 19/06*
- Định nghĩa đầy đủ **5 nhóm schema phản hồi**:
  1. Phản hồi tức thì (202 Accepted) cho Sales và HR với `task_id` định danh.
  2. `AnalysisResult`: Cấu trúc kết quả AI (summary + recommended_message).
  3. `SalesWebhookResult` / `HRWebhookResult`: Payload Webhook gửi về CRM sau khi xử lý xong.
  4. `FollowUpTaskSchema` / `CallRecordDetailSchema`: Dữ liệu cho Dashboard/Client theo dõi.
  5. `HealthResponse`: Kiểm tra sức khoẻ service kèm trạng thái LLM.

---

### 🎙️ 2.3 Dịch vụ Xử lý Âm thanh — Whisper STT (`app/services/audio_service.py`)

**(+156 dòng, cập nhật lớn)** — *Commit: "service update" – 19/06*

Pipeline hoàn chỉnh 3 bước:

| Bước | Nội dung | Chi tiết kỹ thuật |
|---|---|---|
| **1. Download** | Tải file ghi âm từ URL CRM | Dùng `httpx.AsyncClient` + Stream mode; Kiểm tra extension (mp3/wav/m4a/ogg) và giới hạn dung lượng 500MB qua `Content-Length` header hoặc cộng dồn chunk |
| **2. Transcribe** | Chạy Whisper STT | Load model một lần duy nhất lúc khởi động (tránh load lại); Ép ngôn ngữ `vi` (tiếng Việt); Chạy được trên CPU |
| **3. Cleanup** | Dọn dẹp file tạm | Tự động xóa file audio sau khi xử lý xong hoặc gặp lỗi — tránh đầy ổ cứng |

---

### 🤖 2.4 Dịch vụ Phân tích AI — Local LLM (`app/services/llm_service.py`)

**(+181 dòng, cập nhật lớn)** — *Commit: "service update" – 19/06*

- **Kiến trúc Singleton**: Chỉ load model một lần, tái sử dụng cho tất cả request.
- **Backend AI**: Dùng `llama-cpp-python` để chạy mô hình GGUF cục bộ (không phụ thuộc internet, bảo mật dữ liệu cao).
- **Prompt V1**: Tích hợp sẵn 2 bộ Prompt Template theo ngữ cảnh nghiệp vụ:
  - `SALES_ANALYSIS_TEMPLATE`: Phân tích cuộc gọi bán hàng → Tóm tắt + Tin nhắn follow-up khách hàng.
  - `HR_ANALYSIS_TEMPLATE`: Phân tích phỏng vấn ứng viên → Đánh giá + Tin nhắn follow-up ứng viên.
- **Xử lý lỗi JSON**: Hàm `_safe_parse_json` tự động làm sạch và bóc tách JSON thuần từ output thô của LLM (có thể kèm Markdown code block).

---

### 📡 2.5 Dịch vụ Gửi Kết quả & Nhắn tin (`app/services/webhook_service.py`)

**(+167 dòng mới hoàn toàn)** — *Commit: "service update" – 19/06*

Module này là lớp cuối cùng trong pipeline — gửi kết quả AI ra ngoài:

- **Webhook về CRM** (hàm `deliver_webhook`):
  - Cơ chế **Exponential Backoff**: Tự động thử lại (1s → 2s → 4s → ...) nếu CRM không phản hồi.
  - Số lần thử và thời gian chờ cấu hình được trong `.env`.
  - Không crash ứng dụng khi webhook thất bại — chỉ log chi tiết và trả `False`.

- **Tích hợp kênh Zalo** (hàm `send_zalo_message`, `send_zalo_friend_request`):
  - Gửi tin nhắn CSKH qua **Zalo OA API**.
  - Dự phòng: Nếu không có `zalo_id`, dùng số điện thoại để gửi.

- **Tích hợp Email** (hàm `send_email`):
  - Placeholder sẵn sàng, chờ kết nối SMTP nội bộ của công ty.

- **Router đa kênh** (hàm `send_message`):
  - Tự động chọn kênh (Zalo/Email) phù hợp dựa trên thông tin liên hệ có sẵn của khách hàng.

---

### 🔍 2.6 Khám phá & Test API Đối tác (`192.168.25.175:8002`)

- Đã test thành công các endpoint của server đối tác:
  - `GET /deals/{deal_id}`: Lấy thông tin Deal CRM đầy đủ (stage, value, activities...)
  - `GET /deals`: Danh sách toàn bộ Deals
  - `POST /llm/recommend`: Nhận đề xuất hành động AI dựa trên `deal_id`
- Đã lưu tài liệu tham chiếu chi tiết tại [External_API_Info.md](../External_API_Info.md).
- Kết quả phân tích: API đối tác tập trung vào luồng **Deal/CRM Sales** — khác với luồng **Audio/Candidate** của chúng ta, cần xây dựng **mapper** nếu muốn tích hợp đề xuất AI từ hai bên.

### 🚀 2.7 Chuẩn bị Deploy & Tối ưu (23/06/2026)

Hôm nay đội ngũ đã tiến hành các bước chuẩn bị deploy lên server thật và phát triển tính năng tự động:
- **Tự động hoá khởi động (`app/main.py`)**: Tích hợp `@app.on_event("startup")` để tự động tạo toàn bộ bảng trong DB (`Base.metadata.create_all`) và tự động tải mô hình GGUF (`llm_service.load_model()`) ngay khi server khởi động.
- **Tối ưu Docker Compose (`docker-compose.yml`)**: Bổ sung volume mount thư mục `./models:/app/models` để đọc file LLM từ máy host vào thẳng container an toàn mà không làm phình image.

---

## 3. Metrics tiến độ

| Phase | Tổng tasks | Hoàn thành | Đang làm | Chưa bắt đầu |
|---|---|---|---|---|
| Phase 1 – Foundation | 8 | **8** ✅ | 0 | 0 |
| Phase 2 – AI Pipeline | 9 | **9** ✅ | 0 | 0 |
| Phase 3 – Rule Engine | 4 | 0 | 0 | **4** |
| Phase 4 – Agent Workflow | 3 | 0 | 0 | **3** |
| Phase 5 – Optimization | 4 | 0 | 0 | **4** |
| Phase 6 – Production | 5 | 0 | 1 ⏳ | **4** |
| **Tổng cộng** | **33** | **17 (51%)** | **1** | **15** |

---

## 4. Những việc đang còn dở / Rủi ro cần lưu ý

### ⏳ Đang thực hiện
- **Kết nối pipeline → Database**: DB schema (`CallRecord`, `FollowUpTask`) đã sẵn sàng, nhưng chưa được gọi trong luồng xử lý chính (`analyze` endpoint). Cần wire `audio_service → llm_service → lưu DB → webhook_service`.

### 🔴 Rủi ro / Phụ thuộc
- **Chưa có file GGUF model**: Cần cấu hình `LLM_MODEL_PATH` trong `.env` và download model GGUF về server trước khi chạy thực tế.
- **Chưa có token Zalo OA**: Cần điền `ZALO_OA_ACCESS_TOKEN` thật để test gửi tin nhắn Zalo thực.
- **Chưa test end-to-end**: Pipeline download → STT → LLM → DB → webhook chưa được chạy thử với data thật.

---

## 5. Kế hoạch tiếp theo

| Ưu tiên | Công việc | Người thực hiện |
|---|---|---|
| 🔴 Cao | Tải Model GGUF tiếng Việt (ví dụ Qwen2.5-7B) về thư mục `./models`. | thanhpham1108 |
| 🟡 Trung | Khởi chạy `docker-compose up` và test thử pipeline qua curl. | Cả nhóm |
| 🟢 Thấp | Bắt đầu Phase 3: Kết nối DB Rule Engine (D+1, D+3, D+7) | Quỳnh Như |

---

*Tài liệu này được tổng hợp tự động từ git history và code review ngày 23/06/2026.*
*Repo: `thanhpham1108/FollowUpAgent` | Branch: `main`*
