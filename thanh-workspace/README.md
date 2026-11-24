# Thanh workspace

Đây là nơi lưu hướng dẫn thao tác và bối cảnh hiện tại của FollowUpAgent. Chạy lệnh từ **repo root**, nơi có `backend/`, `.env` và `data/`.

## Hướng dẫn đang dùng

- [Tải audio từ API recording](guides/audio-from-crm-api.md): xem endpoint, lấy ID và tải WAV trên server.
- [Gán nhãn cuộc gọi](guides/labeling-guideline.md): taxonomy hiện tại, các ca ranh giới và lệnh chạy thử.
- [Prompt Gemini hỗ trợ gán nhãn](guides/ground-truth-labeling-guide.md): tóm tắt audio để người gán nhãn tham khảo trước khi tự chọn reason code.
- [Chạy lại 713 recording](guides/relabel-713.md): lệnh trên server, kiểm tra mẫu và resume.
- [Review và đánh giá pipeline](guides/pipeline-end-to-end-review.md): cách chấm lô audio và thử tải service.
- [Bàn giao tích hợp CRM cho Datacore](guides/crm-integration-handover.md): điểm kích hoạt, payload, webhook, polling và checklist nghiệm thu.
- [Ghi chú thiết lập server](guides/server-setup-lessons.md): bài học và lỗi đã gặp.
- [API contract mẫu cũ](reference/api-contract.json): bản Postman tham khảo. Dùng tài liệu bàn giao CRM để tra payload hiện tại.

## Bản ghi lịch sử

[`archive/session-2026-10-25.md`](archive/session-2026-10-25.md) phản ánh trạng thái tại ngày viết. Một số đường dẫn, mã phân loại và lệnh trong bản ghi này đã cũ; dùng README ở repo root và hai hướng dẫn trên để thao tác hiện tại.

`Reports/` chứa báo cáo và slide theo từng kỳ. `data/` chứa audio/CSV chạy thực tế trên server và không được đưa vào Git.
