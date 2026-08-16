# -------------------------------------------------------
# app/prompts/analysis_prompts.py
# Prompt yêu cầu AI trích xuất thông tin
# -------------------------------------------------------
# Function: build_analysis_prompt(candidate_name: str) -> str
#
# Prompt yêu cầu AI phân tích:
#   1. Tóm tắt nội dung cuộc phỏng vấn
#   2. Đánh giá kỹ năng giao tiếp
#   3. Mức lương kỳ vọng (nếu đề cập)
#   4. Tâm lý / thái độ ứng viên
#   5. Gợi ý tin nhắn follow-up cho HR
#
# Output format: JSON với 2 fields:
#   - summary: str
#   - recommended_message: str
#
# TODO: Implement prompt builder
# -------------------------------------------------------
# -------------------------------------------------------
# app/prompts/analysis_prompts.py
# Prompt Template yêu cầu AI phân tích cuộc gọi Sales/HR
# -------------------------------------------------------
# Được import bởi app/services/llm_service.py.
# Nếu file này lỗi/thiếu, llm_service sẽ tự dùng bản fallback
# hard-code sẵn trong chính nó (giữ để service không bao giờ crash
# vì thiếu prompt, nhưng bản chuẩn nên luôn nằm ở đây).
# -------------------------------------------------------

SALES_ANALYSIS_TEMPLATE = """Bạn là chuyên gia phân tích cuộc gọi bán hàng/tư vấn. Hãy phân tích cuộc hội thoại sau và phân loại khách hàng vào 1 trong 5 nhóm.
Nhóm 1: Chưa tư vấn
Nhóm 2: Cần gọi lại (Lý do: KNM_1, KNM_4, SUY_NGHI_THEM, KHACH_BAN)
Nhóm 3: UV Tiềm năng (Lý do: CHUA_CHOT_NGAY, CHO_CCCD, HEN_XA)
Nhóm 4: Hẹn phỏng vấn (Lý do: HEN_PHONG_VAN)
Nhóm 5: Đi làm tạm tính (Lý do: DI_LAM)

Tên khách hàng: {contact_name}
Nội dung hội thoại:
\"\"\"
{context_data}
\"\"\"
Trả về JSON đúng cấu trúc:
{{"summary": "Tóm tắt cuộc gọi", "status_group": 1, "reason_code": "Mã lý do", "appointment_date": null, "recommended_message": "Tin nhắn gợi ý"}}"""


HR_ANALYSIS_TEMPLATE = """Bạn là chuyên gia phân tích cuộc gọi tuyển dụng. Hãy phân tích đoạn hội thoại sau và phân loại ứng viên vào 1 trong 5 nhóm.
Nhóm 1: Chưa tư vấn
Nhóm 2: Cần gọi lại (Lý do: KNM_1, KNM_4, SUY_NGHI_THEM, KHACH_BAN)
Nhóm 3: UV Tiềm năng (Lý do: CHUA_CHOT_NGAY, CHO_CCCD, HEN_XA)
Nhóm 4: Hẹn phỏng vấn (Lý do: HEN_PHONG_VAN)
Nhóm 5: Đi làm tạm tính (Lý do: DI_LAM)

Tên ứng viên: {contact_name}
Nội dung cuộc gọi:
\"\"\"
{context_data}
\"\"\"
Trả về JSON đúng cấu trúc:
{{"summary": "Tóm tắt cuộc gọi", "status_group": 1, "reason_code": "Mã lý do", "appointment_date": null, "recommended_message": "Tin nhắn gợi ý"}}"""