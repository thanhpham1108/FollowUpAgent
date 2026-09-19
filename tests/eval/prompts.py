# -------------------------------------------------------
# tests/eval/prompts.py
# Prompt Template cho Judge LLM (llama3.1)
# -------------------------------------------------------
# Judge KHÔNG được biết đáp án kỳ vọng — nó chỉ đọc
# Transcript gốc và Output của Qwen2.5 rồi chấm điểm.
# -------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """Bạn là chuyên gia QA (Quality Assurance) trong lĩnh vực AI phân tích cuộc gọi tuyển dụng nhân sự tại Việt Nam.
Nhiệm vụ của bạn là đánh giá chất lượng kết quả phân tích do một AI khác (không phải bạn) sinh ra.
Bạn chỉ được trả về JSON thuần, không thêm bất kỳ text nào bên ngoài JSON."""

JUDGE_USER_PROMPT_TEMPLATE = """Hãy đánh giá kết quả phân tích cuộc gọi dưới đây theo 2 tiêu chí.

## TRANSCRIPT GỐC (Nguồn sự thật duy nhất):
\"\"\"
{transcript}
\"\"\"

## KẾT QUẢ PHÂN TÍCH CỦA AI:
```json
{ai_output}
```

## HỆ THỐNG PHÂN LOẠI:
- Nhóm 1: Chưa tư vấn được
- Nhóm 2: Cần gọi lại (KNM_1=Cúp máy sớm, KNM_4=Từ chối thẳng, SUY_NGHI_THEM=Cần suy nghĩ, KHACH_BAN=Bận)
- Nhóm 3: Ứng viên tiềm năng (CHUA_CHOT_NGAY, CHO_CCCD, HEN_XA)
- Nhóm 4: Đã hẹn phỏng vấn (HEN_PHONG_VAN)
- Nhóm 5: Đi làm ngay (DI_LAM)

## TIÊU CHÍ CHẤM ĐIỂM:

### Tiêu chí 1: Hallucination (Chống ảo giác) — Thang 1-5
Hệ thống AI có bịa đặt thông tin KHÔNG CÓ trong Transcript không?
- 5: Mọi thông tin trong kết quả đều có căn cứ từ Transcript.
- 3: Có 1-2 chi tiết nhỏ không chính xác hoặc suy luận quá xa.
- 1: Bịa đặt rõ ràng thông tin không tồn tại trong Transcript.

### Tiêu chí 2: Logical Reasoning (Tính hợp lý lập luận) — Thang 1-5
Việc gán nhóm (status_group) và mã lý do (reason_code) có phù hợp với nội dung Transcript không?
- 5: Phân loại chính xác, summary tóm tắt đúng trọng tâm.
- 3: Phân loại gần đúng nhưng reason_code chưa chính xác nhất.
- 1: Phân loại sai hoàn toàn so với nội dung cuộc gọi.

## HƯỚNG DẪN BẮT BUỘC:
1. Suy luận từng bước (Chain-of-Thought) trong trường "critique" TRƯỚC KHI đưa ra điểm số.
2. critique phải nêu bằng chứng cụ thể trích dẫn từ Transcript.
3. Chỉ trả về JSON, không thêm text nào khác.

Trả về JSON với cấu trúc sau:
{{
  "hallucination_score": <int 1-5>,
  "logic_score": <int 1-5>,
  "critique": "<Lý do chi tiết, bằng chứng từ Transcript>"
}}"""
