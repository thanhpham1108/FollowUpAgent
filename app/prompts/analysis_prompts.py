# -------------------------------------------------------
# app/prompts/analysis_prompts.py - PROMPT VERSION 4 (PURE HR RECRUITMENT)
# Tập trung 100% vào nghiệp vụ Tuyển dụng Nhân sự, mở rộng Few-shot
# -------------------------------------------------------

_STATUS_DEFINITIONS = """\
## Bảng phân loại trạng thái (Nghiệp vụ Tuyển dụng):
| Nhóm | Tên Nhóm | Lý do (reason_code) hợp lệ |
|------|----------|----------------------------|
| 1 | Lỗi kết nối / Không thoại | LOI_AM_THANH, CUOC_GOI_RONG, SAI_SO_NHAM_SO |
| 2 | Cần gọi lại / Từ chối | KNM_DAP_MAY, KHACH_BAN, TU_CHOI_LUON, SUY_NGHI_THEM |
| 3 | Tiềm năng (Chưa chốt) | CHUA_CHOT_NGAY, CHO_GIAY_TO, HEN_XA |
| 4 | Đã hẹn lịch | HEN_PHONG_VAN |
| 5 | Chốt thành công | DI_LAM |
"""

_OUTPUT_SCHEMA = """\
## Định dạng output (JSON thuần, KHÔNG bọc markdown):
{
  "thinking": "Chuỗi suy luận ngắn gọn của bạn (2-3 câu): phân tích thái độ ứng viên và chốt lý do",
  "summary": "Tóm tắt khách quan nội dung cuộc gọi (1-2 câu tiếng Việt)",
  "status_group": <số nguyên 1-5>,
  "reason_code": "<mã lý do TỪ BẢNG TRÊN>",
  "appointment_date": "<ISO 8601: YYYY-MM-DDTHH:MM:00 nếu có lịch hẹn, ngược lại null>",
  "recommended_message": "Tin nhắn Zalo/SMS follow-up gửi cho ứng viên (tiếng Việt)"
}
"""

_HR_FEW_SHOT_EXAMPLES = """\
## Kịch bản mẫu Tuyển dụng (Few-shot):

### 1. Ứng viên dập máy / Từ chối nghe
Tên ứng viên: Đinh Thị A
Nội dung: "Dạ em chào chị ạ, em gọi từ bộ phận nhân sự công ty... alo chị nghe rõ không ạ..." (Cuộc gọi kết thúc đột ngột)
Output:
{"thinking": "Nhân viên mới chào hỏi thì cuộc gọi bị kết thúc đột ngột. Đây là trường hợp dập máy ngang.", "summary": "Nhân viên vừa chào hỏi thì ứng viên đã dập máy.", "status_group": 2, "reason_code": "KNM_DAP_MAY", "appointment_date": null, "recommended_message": "Chào chị A, ban nãy em gọi nhưng mạng chập chờn. Em gửi chị JD công việc qua Zalo nhé!"}

### 2. Ứng viên từ chối (Đã có việc / Không phù hợp)
Tên ứng viên: Trần Văn B
Nội dung: "À thôi em ơi, anh xin được việc bên khu công nghiệp Quang Châu rồi, không đi làm bên em đâu."
Output:
{"thinking": "Ứng viên thông báo đã đi làm chỗ khác và từ chối lời mời. Đây là từ chối thẳng.", "summary": "Ứng viên Trần Văn B báo đã đi làm ở KCN Quang Châu nên không có nhu cầu.", "status_group": 2, "reason_code": "TU_CHOI_LUON", "appointment_date": null, "recommended_message": "Cảm ơn anh B đã phản hồi! Chúc anh công tác tốt. Nếu sau này cần tìm cơ hội mới, cứ nhắn em nha."}

### 3. Ứng viên đang bận, hẹn gọi lại
Tên ứng viên: Nguyễn Thị C
Nội dung: "Chị đang chạy xe ngoài đường ồn lắm em ơi, chiều gọi lại cho chị nhé."
Output:
{"thinking": "Ứng viên nghe máy nhưng đang bận chạy xe và yêu cầu gọi lại vào buổi chiều.", "summary": "Ứng viên Nguyễn Thị C đang đi xe ngoài đường, hẹn gọi lại vào buổi chiều.", "status_group": 2, "reason_code": "KHACH_BAN", "appointment_date": null, "recommended_message": "Dạ em xin lỗi vì gọi lúc chị C đang đi đường ạ! Chiều em sẽ liên hệ lại, hoặc chị rảnh cứ nhắn em nhé."}

### 4. Ứng viên lưỡng lự, cần suy nghĩ thêm
Tên ứng viên: Lê Văn D
Nội dung: "Mức lương cơ bản 5 triệu thì hơi thấp so với chỗ cũ của anh. Chắc để anh xem xét cân nhắc thêm đã."
Output:
{"thinking": "Ứng viên chê lương thấp và nói cần thời gian cân nhắc. Chưa từ chối hẳn nhưng cần suy nghĩ.", "summary": "Ứng viên Lê Văn D thấy lương cơ bản 5 triệu hơi thấp nên xin thời gian suy nghĩ thêm.", "status_group": 2, "reason_code": "SUY_NGHI_THEM", "appointment_date": null, "recommended_message": "Chào anh D, em hiểu mong muốn của anh về thu nhập. Bên em còn nhiều khoản phụ cấp hấp dẫn, anh cứ cân nhắc nhé!"}

### 5. Ứng viên quan tâm nhưng chưa chốt ngày phỏng vấn
Tên ứng viên: Phạm Thị E
Nội dung: "Công việc nghe cũng được đấy. Nhưng tuần này em bận thi rồi, chưa biết hôm nào rảnh lên công ty được, để em báo sau nha."
Output:
{"thinking": "Ứng viên ưng ý công việc nhưng bận lịch cá nhân, chưa chốt được ngày phỏng vấn.", "summary": "Ứng viên Phạm Thị E quan tâm công việc nhưng vướng lịch thi, hẹn sẽ chốt ngày phỏng vấn sau.", "status_group": 3, "reason_code": "CHUA_CHOT_NGAY", "appointment_date": null, "recommended_message": "Chào E, chúc em thi tốt nhé! Khi nào thi xong và rảnh rỗi, nhắn tin để chị sắp lịch phỏng vấn cho em nha."}

### 6. Ứng viên vướng giấy tờ (Chờ CCCD)
Tên ứng viên: Hoàng Văn F
Nội dung: "Em mất căn cước công dân rồi chị ạ, đang chờ công an cấp lại giấy hẹn, chắc phải 3 ngày nữa mới có để đi làm."
Output:
{"thinking": "Ứng viên muốn đi làm nhưng thiếu CCCD, cần chờ giấy tờ.", "summary": "Ứng viên Hoàng Văn F đang chờ cấp lại CCCD, khoảng 3 ngày nữa mới có thể đi làm.", "status_group": 3, "reason_code": "CHO_GIAY_TO", "appointment_date": null, "recommended_message": "Chào F, em cứ bình tĩnh lo xong giấy tờ nhé. Khi nào có CCCD hoặc giấy hẹn, chụp gửi chị để làm thủ tục nhận việc!"}

### 7. Ứng viên chốt lịch phỏng vấn cụ thể
Tên ứng viên: Ngô Thị G
Nội dung: "Vâng chị, vậy sáng mai tầm 9 rưỡi em qua văn phòng công ty nộp hồ sơ phỏng vấn luôn ạ."
Output:
{"thinking": "Ứng viên đồng ý đến phỏng vấn vào sáng mai lúc 9:30. Đây là lịch hẹn rõ ràng.", "summary": "Ứng viên Ngô Thị G chốt lịch đến văn phòng nộp hồ sơ phỏng vấn vào 9:30 sáng mai.", "status_group": 4, "reason_code": "HEN_PHONG_VAN", "appointment_date": "NGAY_MAI_9H30", "recommended_message": "Chào G! Cảm ơn em đã xác nhận lịch. Hẹn gặp em vào 9:30 sáng mai tại văn phòng công ty nhé. Đi đường cẩn thận nha!"}

### 8. Ứng viên chốt đi làm
Tên ứng viên: Vũ Văn H
Nội dung: "Em mang hồ sơ qua rồi, giám đốc bảo thứ hai tuần sau bắt đầu đi làm luôn."
Output:
{"thinking": "Ứng viên đã nộp hồ sơ và được xác nhận thứ 2 tuần sau đi làm chính thức. Thuộc nhóm thành công.", "summary": "Ứng viên Vũ Văn H báo cáo đã được nhận và thứ hai tuần sau bắt đầu đi làm.", "status_group": 5, "reason_code": "DI_LAM", "appointment_date": null, "recommended_message": "Tuyệt vời quá! Chúc mừng H gia nhập công ty nhé. Chuẩn bị tinh thần thứ 2 tuần sau chiến đấu thôi!"}
"""

# Vì chỉ có nghiệp vụ HR, ta trỏ Sales về cùng một cấu trúc để không bị lỗi nếu code gọi nhầm
_SALES_FEW_SHOT_EXAMPLES = _HR_FEW_SHOT_EXAMPLES

HR_ANALYSIS_TEMPLATE = f"""\
{_STATUS_DEFINITIONS}
{_OUTPUT_SCHEMA}
{_HR_FEW_SHOT_EXAMPLES}

---
## Nhiệm vụ thực tế của bạn:
Tên ứng viên: {{contact_name}}
Nội dung bóc băng (Transcript):
\"\"\"
{{context_data}}
\"\"\"

Lưu ý quan trọng:
- Tập trung 100% vào nghiệp vụ Tuyển dụng Nhân sự.
- Nếu transcript rỗng, toàn tiếng rè, hoặc chỉ có tiếng nhân viên thử mic -> status_group=1, reason_code="LOI_AM_THANH" hoặc "CUOC_GOI_RONG"
- appointment_date phải định dạng ISO 8601 (YYYY-MM-DDTHH:MM:00) nếu có lịch hẹn. Nếu không -> null.
- Trả về JSON thuần.

JSON output:
"""

SALES_ANALYSIS_TEMPLATE = HR_ANALYSIS_TEMPLATE
