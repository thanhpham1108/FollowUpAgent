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
