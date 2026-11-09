# Báo cáo Tiến độ – Ngày 09/06/2026

**Dự án:** FollowUpAgent (UC04) – Nhận audio phỏng vấn ứng viên, phân tích bằng AI, gửi tư vấn về CRM.
**Giai đoạn hiện tại:** Phase 1 – Foundation & Integration

---

## PHẦN 1: Những việc đã làm trong tuần

### 1.1 Khởi tạo Repository (Kho mã nguồn)

Nhóm đã tạo xong một Repository trên GitHub với cấu trúc chuẩn Production-ready, sẵn sàng cho việc mở rộng và tích hợp AI ở các giai đoạn sau. Repo gồm các thành phần chính sau:

#### Thư mục `app/` — Toàn bộ mã nguồn ứng dụng
- **`app/api/`**: Chứa các endpoint (đường dẫn API) để hệ thống CRM gọi vào. Hiện tại đã có endpoint `POST /api/v1/candidates/analyze` — đây là "cổng vào" duy nhất để CRM đẩy thông tin ứng viên kèm link audio sang cho hệ thống AI.
- **`app/schemas/`**: Chứa các lớp kiểm tra dữ liệu (Pydantic Models). Khi CRM gửi JSON sang, hệ thống sẽ tự động kiểm tra xem dữ liệu có đúng định dạng không (ví dụ: `ssn` phải là chuỗi, `audio_url` phải là đường link hợp lệ). Nếu sai, hệ thống trả lỗi ngay mà không cần chạy AI — tiết kiệm tài nguyên.
- **`app/services/`**: Thư mục chuẩn bị sẵn cho Phase 2. Đây là nơi sẽ chứa logic nghiệp vụ chính: tải audio, gọi Whisper chuyển giọng nói thành chữ, gọi LLM phân tích, và gửi webhook trả kết quả.
- **`app/prompts/`**: Thư mục chuẩn bị sẵn cho việc lưu trữ các System Prompt (câu lệnh chỉ dẫn cho AI). Khi vào Phase 2, nhóm sẽ viết prompt hướng dẫn AI: "Dựa vào nội dung phỏng vấn này, hãy tóm tắt và đề xuất tin nhắn follow-up cho ứng viên."
- **`app/core/`**: Chứa cấu hình hệ thống (biến môi trường, API key, đường dẫn model AI...).
- **`app/utils/`**: Các hàm tiện ích dùng chung cho nhiều module.

#### Thư mục `tests/` — Kiểm thử tự động
- Đã chuẩn bị sẵn các file test (`test_schemas.py`, `test_analyze.py`, `test_health.py`) với các trường hợp kiểm thử được định nghĩa rõ ràng. Khi viết code xong ở Phase 2, nhóm sẽ chạy các test này để đảm bảo hệ thống hoạt động đúng.

#### Các file cấu hình quan trọng
- **`Dockerfile`**: Đóng gói ứng dụng thành container Docker, giúp deploy lên bất kỳ server nào chỉ với 1 lệnh.
- **`requirements.txt`**: Danh sách thư viện Python cần thiết (FastAPI, Pydantic, httpx, llama-cpp-python...).
- **`.env.example`**: Mẫu file cấu hình biến môi trường (Webhook URL, đường dẫn model AI, giới hạn kích thước file audio...).
- **`.gitignore`**: Đảm bảo các file nhạy cảm (mật khẩu, API key) và thư mục nặng (`.venv/`) không bị đẩy lên GitHub.

#### File hợp đồng API
- **`FollowUpAgent_API_contract.json`**: Đây là "bản hợp đồng" quy định chính xác cấu trúc dữ liệu mà CRM cần gửi sang và cấu trúc dữ liệu mà AI sẽ trả về qua webhook. File này sẽ được bàn giao cho team CRM để họ lập trình phần gửi dữ liệu.

### 1.2 Cơ chế xử lý ngầm (Background Tasks)

Đây là điểm kỹ thuật quan trọng nhất đã hoàn thành trong tuần:
- Quá trình AI nghe và phân tích audio rất tốn thời gian (có thể vài phút). Nếu bắt CRM đứng chờ cho đến khi AI xử lý xong, đường truyền mạng sẽ bị timeout (ngắt kết nối).
- Giải pháp: Áp dụng cơ chế **BackgroundTasks** của FastAPI. Khi CRM gửi request vào, hệ thống lập tức trả về mã `202 Accepted` kèm một `task_id` (ví dụ: `TASK-a1b2c3d4`) trong chưa đầy 0.01 giây. Đồng thời, một tiến trình ngầm sẽ âm thầm chạy: tải audio → phân tích → gửi kết quả về CRM qua webhook. CRM không cần phải chờ đợi.

### 1.3 Thống nhất API Contract

- Đã chốt xong cấu trúc JSON cho cả 2 chiều giao tiếp:
  - **CRM → AI**: `{ "ssn": "...", "candidate_name": "...", "audio_url": "..." }`
  - **AI → CRM (Webhook)**: `{ "task_id": "...", "ssn": "...", "status": "completed", "result": { "summary": "...", "recommended_message": "..." } }`

---

## PHẦN 2: Hạ tầng đã được cung cấp & Hạn chế phát hiện

### 2.1 Hạ tầng đã sử dụng được
- Nhóm đã được cấp quyền truy cập vào server nội bộ (`thanhpnc@ood-master`) thông qua SSH.
- Server này nằm trong cùng mạng LAN với hệ thống CRM mock tại địa chỉ `192.168.25.175:8002`.
- Nhóm đã kết nối thành công và truy vấn được dữ liệu từ server CRM mock.

### 2.2 Hạn chế phát hiện: Dữ liệu API chưa phù hợp
Sau khi khảo sát toàn bộ API trên server CRM mock, nhóm phát hiện rằng **dữ liệu hiện tại chưa liên quan trực tiếp đến dự án FollowUpAgent**. Cụ thể:

| Endpoint hiện có | Dữ liệu trả về | Liên quan đến dự án? |
|---|---|---|
| `GET /deals/{deal_id}` | Thông tin Deal (giao dịch bán hàng) | ❌ Không — Đây là dữ liệu cho dự án Sales, không phải Audio ứng viên |
| `GET /deals` | Danh sách Deal | ❌ Không |
| `POST /llm/recommend` | Đề xuất hành động cho Deal | ❌ Không — Endpoint này nhận `deal_id`, không nhận `audio_url` |
| `GET /health` | Kiểm tra trạng thái | ✅ Có thể dùng chung |

**Kết luận:** Server hiện tại **không có endpoint nào** cho phép gửi thông tin ứng viên (`ssn`, `candidate_name`) kèm link audio (`audio_url`), và cũng không có endpoint webhook để nhận kết quả phân tích từ AI.

### 2.3 Giải pháp đề xuất
- Nhóm đã chủ động soạn sẵn tài liệu yêu cầu mở rộng API (`Reports/API_Expansion_Request.md`), trong đó mô tả chi tiết 2 endpoint cần bổ sung:
  1. `POST /candidates/analyze` — Để CRM đẩy thông tin ứng viên + link audio sang AI.
  2. `POST /candidates/webhook` — Để AI gửi kết quả phân tích trả ngược về CRM.
- **Hành động tiếp theo:** Sẽ liên hệ trực tiếp với anh phụ trách môi trường (quản trị server) để gửi yêu cầu mở rộng API, đảm bảo dữ liệu đầu vào phù hợp với luồng nghiệp vụ của dự án.

---

## PHẦN 3: Kế hoạch 2 tuần tới — Phase 2 (AI Pipeline Core)

Khi API đã được mở rộng và dữ liệu audio đã sẵn sàng, nhóm sẽ chuyển sang Phase 2 với các công việc sau:

| STT | Công việc | Mô tả chi tiết | Thời gian |
|-----|-----------|----------------|-----------|
| 1 | **Tích hợp Whisper** | Sử dụng mô hình OpenAI Whisper để chuyển file audio phỏng vấn thành văn bản (Speech-to-Text). Đây là bước đầu tiên trong pipeline AI. | Tuần 7 |
| 2 | **Gọi LLM (Large Language Model)** | Tích hợp LangChain để đưa nội dung phỏng vấn (đã chuyển thành text) vào mô hình ngôn ngữ lớn. LLM sẽ đọc hiểu, phân tích và đưa ra nhận xét. | Tuần 7 |
| 3 | **Viết System Prompt V1** | Soạn câu lệnh chỉ dẫn cho AI, yêu cầu AI trả về kết quả dưới dạng JSON chuẩn (gồm `summary` và `recommended_message`). Đây là phần quyết định chất lượng đầu ra của AI. | Tuần 7-8 |
| 4 | **Handle lỗi JSON** | Xử lý trường hợp AI trả về JSON sai cấu trúc hoặc thiếu trường. Đảm bảo hệ thống không bị crash khi AI "ảo giác". | Tuần 8 |
| 5 | **Logging vào Supabase** | Lưu toàn bộ input/output của AI vào database Supabase để theo dõi, kiểm tra chất lượng và phục vụ audit sau này. | Tuần 8 |

**Mục tiêu cuối Phase 2:** Hệ thống có thể nhận file audio thật, chuyển thành text, đưa qua AI phân tích, và trả về kết quả JSON chuẩn chỉnh — tất cả hoạt động tự động trong pipeline chạy ngầm.
