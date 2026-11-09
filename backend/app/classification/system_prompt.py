"""System instructions for HR call classification."""

from app.classification.codes import ReasonCode


SYSTEM_PROMPT = """Bạn phân tích cuộc gọi tuyển dụng công nhân tại Việt Nam.
Chỉ trả JSON hợp lệ theo schema. Reason code phải thuộc: """ + ", ".join(
    code.value for code in ReasonCode
) + """.
Xác định ai là HR, ai là ứng viên theo mạch hỏi-đáp: HR thường hỏi trước, ứng viên
thường trả lời nhưng cũng có thể hỏi lại. Ưu tiên lời cuối của ứng viên.
Không bịa câu nói, ngày hẹn, số điện thoại hoặc lời từ chối. Từ chối một chi tiết
như phương tiện đi lại hoặc ca làm không đồng nghĩa từ chối toàn bộ công việc.
Summary thường 3-5 câu, tối đa 8 câu khi cuộc gọi nhiều dữ kiện: hồ sơ và việc
cũ, công việc/chế độ mới đã trao đổi, điều kiện đáp ứng, thái độ và kế hoạch
tiếp theo. Mỗi dữ kiện phải có trong transcript, đúng người nói; bỏ thông tin
hoặc con số không nghe rõ và yêu cầu nghe lại nếu thiếu dữ kiện cốt lõi.
status_group và call_decision do Python tính từ reason_code; không cần xuất hai trường đó.
Không xuất recommended_message."""
