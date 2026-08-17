# -------------------------------------------------------
# app/prompts/analysis_prompts.py — PROMPT VERSION 2
# Cải tiến so với V1:
#   1. Few-shot examples (3 ví dụ mẫu mỗi loại)
#   2. Chain-of-thought: LLM tự giải thích trước khi kết luận
#   3. Hướng dẫn rõ ràng format appointment_date (ISO 8601)
#   4. Bổ sung edge case: transcript rỗng, tiếng ồn, nói không rõ
#   5. Tách rõ system prompt và user prompt
# -------------------------------------------------------

# ===== PHÂN LOẠI TRẠNG THÁI (DÙNG CHUNG SALES & HR) =====
# Nhóm 1: Chưa tư vấn / Không liên lạc được (số sai, thuê bao)
# Nhóm 2: Cần gọi lại — Khách chưa sẵn sàng, bận hoặc cần thêm thời gian
#   - KNM_1: Không nghe máy
#   - KNM_4: Bấm phím từ chối
#   - SUY_NGHI_THEM: Cần suy nghĩ thêm
#   - KHACH_BAN: Khách đang bận
# Nhóm 3: Tiềm năng — Khách/UV quan tâm nhưng chưa chốt
#   - CHUA_CHOT_NGAY: Chưa xác định được ngày
#   - CHO_CCCD: Đang chờ giấy tờ
#   - HEN_XA: Hẹn ngày xa (> 7 ngày)
# Nhóm 4: Đã hẹn — Xác nhận thời gian cụ thể
#   - HEN_PHONG_VAN: Đã hẹn ngày phỏng vấn / ngày gặp
# Nhóm 5: Chốt thành công
#   - DI_LAM: Ứng viên/khách đồng ý đi làm/mua

_STATUS_DEFINITIONS = """\
## Bảng phân loại trạng thái:
| Nhóm | Tên | Lý do (reason_code) hợp lệ |
|------|-----|---------------------------|
| 1 | Chưa tư vấn | (để trống) |
| 2 | Cần gọi lại | KNM_1, KNM_4, SUY_NGHI_THEM, KHACH_BAN |
| 3 | Tiềm năng | CHUA_CHOT_NGAY, CHO_CCCD, HEN_XA |
| 4 | Đã hẹn lịch | HEN_PHONG_VAN |
| 5 | Chốt thành công | DI_LAM |
"""

_OUTPUT_SCHEMA = """\
## Định dạng output (JSON thuần, KHÔNG bọc markdown):
{
  "thinking": "Chuỗi suy luận ngắn gọn của bạn (2-3 câu): tín hiệu nào dẫn đến kết luận",
  "summary": "Tóm tắt khách quan nội dung cuộc gọi (1-2 câu tiếng Việt)",
  "status_group": <số nguyên 1-5>,
  "reason_code": "<mã lý do từ bảng trên, hoặc chuỗi rỗng nếu nhóm 1>",
  "appointment_date": "<ISO 8601: YYYY-MM-DDTHH:MM:00 nếu có lịch hẹn cụ thể, ngược lại null>",
  "recommended_message": "Tin nhắn follow-up ngắn gọn, thân thiện, phù hợp ngữ cảnh (tiếng Việt)"
}
"""

# ===== FEW-SHOT EXAMPLES =====
_HR_FEW_SHOT_EXAMPLES = """\
## Ví dụ mẫu (few-shot):

### Ví dụ 1 — Ứng viên không nghe máy
Tên ứng viên: Nguyễn Văn B
Nội dung: [Tiếng chuông... không có ai nghe. Hộp thư thoại bật lên]
Output:
{"thinking": "Ứng viên không nghe máy, không có tương tác nào. Đây là trường hợp KNM_1.", "summary": "Gọi cho ứng viên Nguyễn Văn B nhưng không có ai bắt máy.", "status_group": 2, "reason_code": "KNM_1", "appointment_date": null, "recommended_message": "Chào bạn Văn B, mình vừa gọi cho bạn nhưng chưa liên lạc được. Bạn có thể gọi lại cho mình theo số này không ạ? Mình đang có cơ hội việc làm phù hợp muốn chia sẻ với bạn."}

### Ví dụ 2 — Ứng viên đồng ý hẹn phỏng vấn ngày mai 9h
Tên ứng viên: Trần Thị C
Nội dung: "Ừ, ngày mai 9 giờ sáng mình đến được. Địa chỉ ở đâu vậy chị?"
Output:
{"thinking": "Ứng viên xác nhận sẽ đến phỏng vấn ngày mai lúc 9h. Đây là nhóm 4, HEN_PHONG_VAN. Ngày hôm nay là context từ cuộc gọi, tôi cần điền appointment_date tương ứng.", "summary": "Ứng viên Trần Thị C đồng ý đến phỏng vấn vào ngày mai lúc 9:00 sáng và hỏi địa chỉ.", "status_group": 4, "reason_code": "HEN_PHONG_VAN", "appointment_date": "NGAY_MAI_9H_SAU_KHI_CODE_DIEN", "recommended_message": "Chào bạn Thị C! Cảm ơn bạn đã xác nhận. Địa chỉ của chúng mình là [ĐỊA CHỈ]. Nhớ mang theo CMND/CCCD bạn nhé. Hẹn gặp bạn vào 9h sáng mai!"}

### Ví dụ 3 — Ứng viên cần suy nghĩ thêm
Tên ứng viên: Lê Văn D
Nội dung: "Mức lương đó thấp hơn mình mong đợi. Để mình cân nhắc thêm nhé, tuần sau mình trả lời."
Output:
{"thinking": "Ứng viên quan tâm nhưng chưa chốt vì mức lương. Anh ấy hứa trả lời tuần sau — đây là SUY_NGHI_THEM thuộc nhóm 2.", "summary": "Ứng viên Lê Văn D cho rằng mức lương chưa đáp ứng kỳ vọng và xin thêm thời gian suy nghĩ đến tuần sau.", "status_group": 2, "reason_code": "SUY_NGHI_THEM", "appointment_date": null, "recommended_message": "Chào bạn Văn D, cảm ơn bạn đã lắng nghe! Mình hoàn toàn hiểu khi bạn cần thêm thời gian cân nhắc. Nếu có câu hỏi gì thêm về vị trí hay chế độ đãi ngộ, cứ nhắn tin cho mình bất cứ lúc nào nhé."}
"""

_SALES_FEW_SHOT_EXAMPLES = """\
## Ví dụ mẫu (few-shot):

### Ví dụ 1 — Khách hàng đang bận
Tên khách hàng: Phạm Thị E
Nội dung: "Xin lỗi tôi đang họp, gọi lại sau nhé."
Output:
{"thinking": "Khách đang bận không thể nói chuyện. Đây là KHACH_BAN thuộc nhóm 2.", "summary": "Khách hàng Phạm Thị E đang bận họp và yêu cầu gọi lại sau.", "status_group": 2, "reason_code": "KHACH_BAN", "appointment_date": null, "recommended_message": "Dạ em xin lỗi vì đã làm phiền chị lúc chị đang bận ạ! Em sẽ liên hệ lại với chị sau. Nếu chị có thời gian rảnh, chị cứ nhắn cho em nhé!"}

### Ví dụ 2 — Khách đồng ý mua / đăng ký
Tên khách hàng: Hoàng Văn F
Nội dung: "Được rồi, anh đồng ý. Anh sẽ chuyển tiền đặt cọc hôm nay."
Output:
{"thinking": "Khách hàng đã đồng ý mua và cam kết chuyển tiền. Đây là trường hợp DI_LAM thuộc nhóm 5.", "summary": "Khách hàng Hoàng Văn F đồng ý mua và cam kết chuyển tiền đặt cọc trong ngày.", "status_group": 5, "reason_code": "DI_LAM", "appointment_date": null, "recommended_message": "Chào anh Văn F! Cảm ơn anh đã tin tưởng lựa chọn. Em sẽ gửi thông tin tài khoản chuyển khoản ngay cho anh ạ. Mình cùng hoàn thiện thủ tục nhé!"}

### Ví dụ 3 — Khách cần chờ giấy tờ
Tên khách hàng: Nguyễn Thị G
Nội dung: "Tôi muốn đăng ký nhưng đang chờ xác nhận từ ngân hàng. Khoảng 3-4 ngày nữa."
Output:
{"thinking": "Khách có ý định nhưng đang vướng giấy tờ ngân hàng. Đây là CHO_CCCD thuộc nhóm 3.", "summary": "Khách hàng Nguyễn Thị G muốn đăng ký nhưng đang chờ xác nhận từ ngân hàng, dự kiến 3-4 ngày.", "status_group": 3, "reason_code": "CHO_CCCD", "appointment_date": null, "recommended_message": "Dạ em hiểu ạ, chị cứ xử lý phần ngân hàng trước nhé! Khi nào ngân hàng xác nhận xong, chị nhắn em là mình hoàn tất ngay. Em luôn sẵn sàng hỗ trợ chị ạ!"}
"""

# ===== MAIN TEMPLATES =====

HR_ANALYSIS_TEMPLATE = f"""\
{_STATUS_DEFINITIONS}
{_OUTPUT_SCHEMA}
{_HR_FEW_SHOT_EXAMPLES}

---
## Nhiệm vụ thực tế:
Tên ứng viên: {{contact_name}}
Nội dung cuộc gọi:
\"\"\"
{{context_data}}
\"\"\"

Lưu ý quan trọng:
- Nếu transcript rỗng hoặc không nghe rõ → status_group=2, reason_code="KNM_1"
- appointment_date phải là ISO 8601 (YYYY-MM-DDTHH:MM:00) nếu có lịch hẹn cụ thể, ngược lại là null
- recommended_message phải thân thiện, ngắn gọn (<150 từ), viết thẳng cho ứng viên đọc (không phải hướng dẫn cho HR)
- Chỉ trả về JSON thuần, không có bất kỳ text nào khác bên ngoài dấu ngoặc nhọn

JSON output:\
"""

SALES_ANALYSIS_TEMPLATE = f"""\
{_STATUS_DEFINITIONS}
{_OUTPUT_SCHEMA}
{_SALES_FEW_SHOT_EXAMPLES}

---
## Nhiệm vụ thực tế:
Tên khách hàng: {{contact_name}}
Nội dung hội thoại:
\"\"\"
{{context_data}}
\"\"\"

Lưu ý quan trọng:
- Nếu transcript rỗng hoặc không nghe rõ → status_group=2, reason_code="KNM_1"
- appointment_date phải là ISO 8601 (YYYY-MM-DDTHH:MM:00) nếu có lịch hẹn cụ thể, ngược lại là null
- recommended_message phải thân thiện, ngắn gọn (<150 từ), viết thẳng cho khách đọc (không phải hướng dẫn cho sales)
- Chỉ trả về JSON thuần, không có bất kỳ text nào khác bên ngoài dấu ngoặc nhọn

JSON output:\
"""