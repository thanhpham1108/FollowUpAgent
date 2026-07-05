# Báo cáo Tiến độ Tuần (Weekly Report)
**Ngày lập báo cáo**: 05/07/2026
**Giai đoạn**: Hoàn tất Phase 3 (Rule Engine & Intelligence Layer)

---

## 1. Tóm tắt kết quả đạt được
Trong thời gian qua, team đã tập trung hiện thực hóa **Phase 3**, đưa hệ thống từ một bộ khung pipeline xử lý audio đơn giản trở thành một **Agent tự động ra quyết định** dựa trên các quy tắc nghiệp vụ (Business Rules) của Sale/HR. Toàn bộ các công việc trong Phase 3 đã hoàn tất 100% về mặt code và tích hợp.

## 2. Chi tiết các hạng mục đã triển khai (Phase 3)

### 2.1. Rule Engine Core (`app/services/rule_engine.py`)
- Đã xây dựng thành công module `RuleEngineService` để xử lý các quyết định lên lịch Follow-up tự động.
- Áp dụng thành công bộ quy tắc 5 nhóm nghiệp vụ thực tế của công ty vào code:
  - **Nhóm 1 (Chưa tư vấn)**: Đặt lệnh gọi lại trong 10 phút.
  - **Nhóm 2 (Cần gọi lại)**: Đặt lệnh gọi lại sau 1 ngày (nếu KHÔNG NGHE MÁY 1,2,3) hoặc 3 ngày (các trường hợp bận/suy nghĩ thêm).
  - **Nhóm 3 (Tiềm năng)**: Đặt lệnh chăm sóc sau 3 ngày.
  - **Nhóm 4 (Hẹn phỏng vấn)**: Tự động tính toán ngày nhắc lịch dựa trên `appointment_date` trích xuất từ AI.
  - **Nhóm 5 (Đi làm tạm tính)**: Đặt lịch chăm sóc sau 2 ngày.

### 2.2. Tracking & Audit (Bảo đảm tính minh bạch)
- Khởi tạo bảng `AuditLog` trong cơ sở dữ liệu (`models.py`) để lưu giữ mọi quyết định của AI và Rule Engine.
- Mỗi khi `RuleEngineService` chạy, hệ thống sẽ lưu lại `input_group`, `input_reason` từ LLM và lịch trình `scheduled_at` được tạo ra. Đảm bảo 100% Local và có thể tra cứu khi cần (Troubleshooting).

### 2.3. Nâng cấp LLM Prompts (`llm_service.py`)
- Viết lại System Prompt để gò AI vào đúng khuôn khổ 5 nhóm nghiệp vụ.
- Bắt buộc LLM trả về cấu trúc JSON nghiêm ngặt (chứa `status_group`, `reason_code`, `appointment_date`) nhằm phục vụ Rule Engine.
- Tinh chỉnh Schema Pydantic (`response.py`) tương ứng.

### 2.4. Khép kín luồng xử lý (End-to-End Integration)
- Tích hợp toàn diện `RuleEngineService` vào API `/analyze` (`analyze.py`).
- Fix các lỗi tiềm ẩn (UnboundLocalError, Database Session conflict) nhằm đảm bảo nếu Rule Engine có lỗi, hệ thống vẫn lưu được kết quả STT/LLM mà không bị sập hay rollback sai.
- Luồng dữ liệu hoàn chỉnh hiện tại: `Audio -> Whisper STT -> Local GGUF LLM -> Rule Engine -> Database (CallRecord + FollowUpTask + AuditLog) -> CRM Webhook`.

### 2.5. Tài liệu hóa dự án
- Bổ sung tài liệu nghiệp vụ [Rule_Engine.md](Rule_Engine.md).
- Cập nhật tiến độ `Master_Plan.md` và `Current_Week.md`.

---

## 3. Khó khăn / Điểm nghẽn (Blockers) hiện tại
- **Môi trường Deploy**: Hệ thống đang ở trạng thái chờ có Server/GPU để tải file model `.gguf` thực tế. Không thể test E2E với Audio thật do thiếu mô hình LLM Local.
- **Tích hợp CRM Đối tác**: Chờ API Contract hoàn chỉnh từ phía CRM đối tác để khớp dữ liệu đầu ra.

## 4. Kế hoạch Tuần tới (Next Steps)
- Khởi động **Phase 4: Agent Workflow hoàn chỉnh**.
- Tiến hành Refactor hệ thống thành dạng Chain/Graph (Tách bạch rõ Transcription Module, Intent Detection Module, Decision Engine) giúp dễ mở rộng sau này.
- Set up Docker Compose với GPU để kiểm thử thực tế toàn bộ luồng với một file âm thanh mẫu.
