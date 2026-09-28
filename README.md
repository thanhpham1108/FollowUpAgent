# FollowUpAgent

**FollowUpAgent** là hệ thống AI nội bộ tự động phân tích file ghi âm phỏng vấn của ứng viên. Dựa trên nội dung cuộc gọi, hệ thống sử dụng AI (Speech-to-Text và Large Language Model) để tạo tóm tắt và đề xuất thông điệp follow-up (phản hồi) cho bộ phận Nhân sự (HR).

---

## 1. Yêu cầu hệ thống (Prerequisites)

Để hệ thống hoạt động với hiệu suất tốt nhất, server triển khai cần đáp ứng các yêu cầu sau:

- **Hệ điều hành:** Linux (Khuyến nghị Ubuntu 22.04 LTS).
- **Phần cứng:** Yêu cầu có GPU NVIDIA để tăng tốc quá trình xử lý AI (PhoWhisper & LLM).
- **Phần mềm cài đặt sẵn:**
  - [Docker](https://docs.docker.com/engine/install/) & [Docker Compose](https://docs.docker.com/compose/install/).
  - [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (để Docker có thể nhận diện GPU).
  - Máy chủ đã cài đặt hoặc có kết nối đến hệ thống **Ollama** (với model `qwen2.5:7b-instruct` hoặc tương đương).

---

## 2. Hướng dẫn cài đặt & Triển khai (Setup & Deployment)

Hệ thống được đóng gói hoàn toàn bằng Docker, giúp quá trình triển khai trở nên dễ dàng và đồng nhất.

### Bước 1: Chuẩn bị mã nguồn
Clone hoặc giải nén mã nguồn vào thư mục trên server:
```bash
git clone <repository_url>
cd FollowUpAgent
```

### Bước 2: Cấu hình môi trường
Tạo file `.env` từ file mẫu `.env.example`:
```bash
cp .env.example .env
```
Mở file `.env` và chỉnh sửa lại các thông số quan trọng:
- `DATABASE_URL`: Cấu hình chuỗi kết nối database (nếu không dùng db mặc định của docker-compose).
- `OLLAMA_API_BASE_URL` & `OLLAMA_MODEL_NAME`: URL trỏ tới server Ollama.
- `WEBHOOK_URL`, `CRM_WEBHOOK_URL`: Địa chỉ Webhook của hệ thống CRM để nhận kết quả phân tích.

### Bước 3: Khởi chạy dịch vụ
Hệ thống đi kèm cấu hình tự động triển khai CSDL PostgreSQL và API Service:
```bash
docker-compose up -d --build
```

Kiểm tra trạng thái các container:
```bash
docker-compose logs -f
```

Hệ thống sẽ khả dụng tại: `http://localhost:8000`. Bạn có thể truy cập `http://localhost:8000/docs` (Swagger UI) để xem và test thử các API.

---

## 3. Cấu trúc thư mục (Folder Structure)

```text
FollowUpAgent/
├── app/               # Source code chính của ứng dụng FastAPI
├── data/              # Thư mục chứa file audio tải về (mount vào Docker)
├── tests/             # Unit tests, Eval pipeline và Load testing scripts
├── Reports/           # Báo cáo hàng tuần, specs hạ tầng và kế hoạch
├── scripts/           # Các script hỗ trợ tự động hóa
├── Dockerfile         # Đóng gói FollowUpAgent API & AI Pipeline
├── docker-compose.yml # Quản lý các dịch vụ (PostgreSQL, Agent Service)
├── .env.example       # File biến môi trường mẫu
└── FollowUpAgent_API_contract.json # Collection Postman tài liệu API
```

---

## 4. Kiến trúc hệ thống (Architecture)

```text
┌─────────────────────────────────────────────────┐
│                  INTERNAL NETWORK               │
│                                                 │
│  ┌──────────┐   POST /api/v1/candidates/analyze │
│  │          │ ─────────────────────────────────►│
│  │   CRM    │                                   │
│  │  System  │ ◄─────────────────────────────────│
│  │          │   POST /webhook/candidate-recommend│
│  └──────────┘                                   │
│                         ▲ Trả kết quả Webhook   │
│                         │                       │
│  ┌──────────────────────┴──────────────────────┐│
│  │          FollowUpAgent AI Service           ││
│  │                                             ││
│  │   FastAPI  ──►  Whisper  ──►  Local LLM     ││
│  │  (Receive)    (STT audio)  (Analyze & Draft)││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**Luồng xử lý:**
1. CRM gửi ID ứng viên (SSN) và URL chứa file ghi âm nội bộ sang hệ thống AI.
2. AI tải audio, bóc băng giọng nói thành văn bản (dùng PhoWhisper).
3. LLM phân tích văn bản, tóm tắt và dự thảo câu trả lời follow-up.
4. Hệ thống đẩy kết quả trả lại CRM thông qua cơ chế Webhook.

---

## 5. Tích hợp API (API Contract Summary)

Tài liệu API chi tiết được cung cấp dưới dạng Postman Collection.
Vui lòng import file: `FollowUpAgent_API_contract.json` vào Postman để thử nghiệm toàn bộ luồng.

### 5.1 Gửi yêu cầu phân tích Audio
- **Endpoint:** `POST /api/v1/candidates/analyze`
- **Body:**
```json
{
  "ssn": "079099123456",
  "candidate_name": "Nguyen Van A",
  "audio_url": "http://{crm_server_ip}/files/079099123456_interview.mp3"
}
```
*(Hệ thống sẽ trả về mã 202 Accepted và tiến hành xử lý ngầm)*

### 5.2 Nhận kết quả từ Webhook
Khi xử lý xong, hệ thống AI sẽ tự động POST kết quả tới webhook của CRM:
```json
{
  "task_id": "TASK-a1b2c3d4",
  "ssn": "079099123456",
  "status": "completed",
  "result": {
    "summary": "Ứng viên giao tiếp tốt, kỹ năng kỹ thuật vững...",
    "recommended_message": "Chào anh Nguyễn Văn A, cảm ơn anh đã tham gia phỏng vấn..."
  }
}
```

---

## 6. Bảo trì & Xử lý sự cố (Troubleshooting)

- **Lỗi không nhận diện được GPU (Nvidia driver error):** Hãy đảm bảo máy chủ đã cài đặt `nvidia-container-toolkit` và đã khởi động lại Docker daemon (`sudo systemctl restart docker`).
- **Lỗi không kết nối được Database:** Kiểm tra lại thông số `DATABASE_URL` trong `.env` và đảm bảo cổng `5432` hoặc `5433` không bị trùng lặp trên host.
- **Xem file log của hệ thống AI:** Chạy lệnh `docker logs followup-agent-gpu --tail 100 -f`.
