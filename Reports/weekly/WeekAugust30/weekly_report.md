# Báo Cáo Tiến Độ (Tuần 30/08/2026)
**Dự án:** FollowUpAgent
**Môi trường triển khai:** Master Node (poc-ood-2)

---

## 1. Các Hạng Mục Đã Hoàn Thành (Accomplishments)

Trong tuần qua, team đã hoàn tất việc xây dựng và kiểm thử thành công toàn bộ luồng pipeline End-to-End (E2E) trên môi trường Server Linux không sử dụng Docker. Các hạng mục chính bao gồm:

### 1.1 Triển khai hạ tầng Native (Non-Docker)
- Cài đặt thành công môi trường **Conda** cô lập cho dự án.
- Thiết lập **PostgreSQL** native (cổng 5433) làm cơ sở dữ liệu chính.
- Khắc phục sự cố xung đột cổng (Apache chiếm 8080) bằng cách chuyển FastAPI sang cổng **18000**.
- Cài đặt thành công **Ollama Standalone** và kéo model `Qwen2.5:7b-instruct`.

### 1.2 Tích hợp & Sửa lỗi lõi AI (AI Core)
- Tích hợp **PhoWhisper-medium** để bóc băng (Speech-to-Text) hoàn toàn offline trên GPU (cuda:0).
- Giải quyết triệt để lỗi parse JSON khi LLM trả về các khối tư duy (`<think>`, `"thinking"` block).
- Sửa lỗi `KeyError` nghiêm trọng trong **Prompt Template** bằng cách escape các chuỗi định dạng JSON (Few-shot prompting).
- Xử lý lỗi **Model Cold-Start Timeout** (Tăng giới hạn chờ của httpx client lên 300 giây để nạp model 4.7GB).

### 1.3 Nghiệm thu E2E Pipeline
Hệ thống đã nhận tín hiệu từ hệ thống giả lập CRM một cách trơn tru:
1. Nhận File âm thanh từ File Server (port 8001).
2. STT bóc băng chính xác.
3. LLM phân loại chính xác nhóm khách hàng / ứng viên (Status Group & Intent).
4. Ghi nhận lịch sử vào cơ sở dữ liệu `call_records` với trạng thái `COMPLETED`.
5. Bắn Webhook mang kết quả cuối cùng sang `webhook.site` (Mã phản hồi 200 OK).

### 1.4 Tài liệu hóa (Documentation)
Đã xuất xưởng bộ tài liệu bàn giao kỹ thuật chuẩn mực bao gồm:
- **Hướng dẫn cài đặt từ con số 0** (`complete_setup_guide.md`)
- **Tài liệu luồng hệ thống** (`system_flow.md`)
- **Nhật ký bắt lỗi & khắc phục sự cố** (`bug_log.md`)

---

## 2. Kế Hoạch Tiếp Theo (Next Steps)

Để đưa hệ thống vào môi trường Production thực tế với CRM thật, các hạng mục dưới đây cần được ưu tiên trong tuần tới:

### 2.1 Hoàn thiện API
- **Xây dựng API Polling (`GET /api/v1/tasks/{task_id}`):** Hiện tại hệ thống đang xử lý bất đồng bộ (trả về `202 Accepted`). Cần một endpoint để Front-end hoặc CRM chủ động kiểm tra trạng thái tiến trình (Pending, Processing, Completed, Failed).

### 2.2 Tối ưu Webhook & Quản lý lỗi
- **Cơ chế Retry Webhook:** Xây dựng hàng đợi (queue) hoặc vòng lặp retry thông minh (Exponential backoff) trong trường hợp CRM đích bị sập hoặc quá tải.
- **Log lưu vết Webhook:** Lưu trạng thái HTTP (200, 404, 500) của Webhook vào một bảng `webhook_logs` trong DB để dễ dàng audit.

### 2.3 Tối ưu Hiệu năng AI (Performance)
- **Giữ Model trên VRAM (Keep-alive):** Hiện tại lần chạy đầu tiên bị chậm (~90s) do Cold Start. Cần tinh chỉnh cấu hình của Ollama để giữ model `Qwen2.5` thường trực trên VRAM (hoặc nạp sẵn lúc khởi động server).
- **Tối ưu tốc độ STT:** Đánh giá tốc độ của `PhoWhisper-medium` trên GPU L4, nếu cần thiết có thể chuyển sang model nhỏ hơn (PhoWhisper-base) nếu yêu cầu về thời gian thực (Real-time) cao hơn độ chính xác tuyệt đối.

### 2.4 Kết nối hệ thống thật
- Tắt giả lập `http.server 8001` và `webhook.site`.
- Trỏ cấu hình `WEBHOOK_URL` về API chính thức của công ty.
- Tiến hành Load Test (Bắn 10-50 request đồng thời) để xem giới hạn chịu đựng của card đồ họa.
