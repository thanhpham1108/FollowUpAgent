# Yêu cầu mở rộng API từ phía đối tác

**Mục tiêu**: Cung cấp một endpoint cho FollowUpAgent để nhận dữ liệu ứng viên và file audio, đồng thời nhận kết quả phân tích từ AI.

## 1. API hiện tại (được cung cấp)
| Method | Path | Mô tả | Schema |
|--------|------|------|--------|
| GET    | `/deals/{deal_id}` | Trả về thông tin Deal | `DealData` |
| GET    | `/deals` | Danh sách Deal | `DealData[]` |
| POST   | `/llm/recommend` | Nhận `deal_id` → trả đề xuất hành động | `LLMInput` → `LLMResponse` |
| GET    | `/health` | Kiểm tra trạng thái dịch vụ | `HealthResponse` |

Những endpoint trên **không** đáp ứng yêu cầu **nhận audio của ứng viên** (`ssn`, `candidate_name`, `audio_url`).

## 2. Yêu cầu API mới
| Method | Path | Request Body (JSON) | Response Body (JSON) | Mục đích |
|--------|------|---------------------|----------------------|----------|
| **POST** | `/candidates/analyze` | ```json
{ "ssn": "string", "candidate_name": "string", "audio_url": "string (http/https)" }
``` | ```json
{ "task_id": "string", "status": "processing", "message": "Audio received and is being processed in the background." }
``` | Nhận audio, khởi tạo background task để phân tích. |
| **POST** | `/candidates/webhook` | ```json
{ "task_id": "string", "ssn": "string", "status": "completed", "result": { "summary": "string", "recommended_message": "string" } }
``` | ```json
{ "ack": true }
``` | Webhook mà AI sẽ gọi khi hoàn tất phân tích, trả kết quả cho CRM. |

### Các yêu cầu bổ sung
1. **Authentication**: Đề nghị sử dụng token Bearer hoặc API‑Key để bảo vệ các endpoint.
2. **CORS**: Cho phép origin của hệ thống FollowUpAgent (`http://<our‑host>`) gọi được.
3. **Status codes**:   
   - `202 Accepted` cho `/candidates/analyze` (task được nhận và sẽ chạy nền).   
   - `200 OK` cho webhook phản hồi thành công.   
   - `400 Bad Request` khi dữ liệu không hợp lệ, `401 Unauthorized` khi token thiếu/không đúng.
4. **Rate limiting**: Đề xuất giới hạn 30 request/phút cho mỗi client.

## 3. Lý do cần mở rộng
- FollowUpAgent được thiết kế để **phân tích audio phỏng vấn** và trả về đề xuất cho nhân sự.  
- Hiện tại chỉ có các endpoint liên quan đến Deal và LLM, không thể đáp ứng luồng nghiệp vụ của chúng tôi.
- Khi có API mới, chúng tôi có thể **tích hợp liền mạch**: CRM → FollowUpAgent → AI → Webhook trả kết quả → CRM.

## 4. Đề xuất thời gian
- **Phiên bản MVP**: Cung cấp `/candidates/analyze` và `/candidates/webhook` trong vòng **2‑3 tuần** để chúng tôi có thể demo trong sprint tới.
- **Bản ổn định**: Hoàn thiện auth, rate‑limit, tài liệu Swagger trong 1‑2 tuần tiếp theo.

---

*Vui lòng xác nhận khả năng triển khai và cung cấp thông tin endpoint (URL, auth token) để chúng tôi cập nhật trong `FollowUpAgent_API_contract.json`.*
