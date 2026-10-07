# -------------------------------------------------------
# app/prompts/analysis_prompts.py - PROMPT VERSION 4 (PURE HR RECRUITMENT)
# Tập trung 100% vào nghiệp vụ Tuyển dụng Nhân sự, mở rộng Few-shot
# -------------------------------------------------------
try:
    from app.core.companies import get_companies_prompt_string, get_industrial_parks_prompt_string
    _COMPANIES_STR = get_companies_prompt_string()
    _KCN_STR = get_industrial_parks_prompt_string()
except ImportError:
    _COMPANIES_STR = "Luxshare ICT, Foxconn, Goertek, Pegatron, Quanta, Wistron, Canon, Lens, Brother, Biel Crystal, LG Display, VinFast, Vixech, Siflex, Samkwang, Sumi, Shinwon, Fushan..."
    _KCN_STR = "Quang Châu, Vân Trung, Quế Võ, VSIP, Đồng Văn, Hòa Phú, Đình Trám, Yên Phong, Khai Quang, Tràng Duệ..."

_STATUS_DEFINITIONS = """\
## Bảng phân loại trạng thái (Nghiệp vụ Tuyển dụng):
| Nhóm | Tên Nhóm Nghiệp vụ | Mã lý do (reason_code) hợp lệ | Hành động (call_decision) |
|------|---------------------|-------------------------------|---------------------------|
| 1 | Đóng hồ sơ / Bỏ qua | TU_CHOI_LUON, KNM_DAP_MAY, SAI_SO_NHAM_SO | NO_CALL |
| 2 | Gián đoạn / Cần gọi lại | KHACH_BAN, CUOC_GOI_RONG, LOI_AM_THANH | CALL_BACK |
| 3 | Tiềm năng / Chăm sóc | SUY_NGHI_THEM, CHUA_CHOT_NGAY, CHO_GIAY_TO, HEN_XA | FOLLOW_UP |
| 4 | Đã hẹn phỏng vấn | HEN_PHONG_VAN | SCHEDULED |
| 5 | Chốt thành công | DI_LAM | SUCCESS |
"""

_OUTPUT_SCHEMA = """\
## Định dạng output (JSON thuần, KHÔNG bọc markdown - TUYỆT ĐỐI KHÔNG CHẾ THÊM CÁC TRƯỜNG KHÁC):
{{
  "thinking": "Chuỗi suy luận ngắn gọn của bạn (2-3 câu): phân tích thái độ ứng viên và chốt lý do",
  "summary": "Tóm tắt chi tiết cuộc gọi (3-5 câu tiếng Việt, nêu rõ: mục đích/vị trí trao đổi, thông tin ứng viên chia sẻ hoặc vướng mắc, thái độ/phản hồi của ứng viên, và thỏa thuận hoặc kết quả chốt cuối cùng)",
  "status_group": <số nguyên 1-5 theo bảng trên>,
  "reason_code": "<mã lý do TỪ BẢNG TRÊN>",
  "call_decision": "<NO_CALL | CALL_BACK | FOLLOW_UP | SCHEDULED | SUCCESS khớp với Nhóm>",
  "appointment_date": "<ISO 8601: YYYY-MM-DDTHH:MM:00 nếu có lịch hẹn, ngược lại null>",
  "recommended_message": "Tin nhắn Zalo/SMS follow-up gửi cho ứng viên (tiếng Việt)"
}}
"""

_HR_FEW_SHOT_EXAMPLES = """\

## Kịch bản mẫu Tuyển dụng (Few-shot):

### 1. Ứng viên dập máy / Từ chối nghe (Nhóm 1 - Đóng hồ sơ)
Tên ứng viên: Đinh Thị A
Nội dung: "Dạ em chào chị ạ, em gọi từ bộ phận nhân sự công ty... alo chị nghe rõ không ạ..." (Cuộc gọi kết thúc đột ngột)
Output:
{{"thinking": "Nhân viên mới chào hỏi thì cuộc gọi bị kết thúc đột ngột. Đây là trường hợp dập máy ngang, đóng hồ sơ không làm phiền thêm.", "summary": "Nhân viên nhân sự liên hệ ứng viên Đinh Thị A để giới thiệu cơ hội việc làm. Tuy nhiên nhân viên vừa mở lời chào hỏi thì ứng viên đã dập máy ngang, cuộc gọi kết thúc đột ngột. Hai bên chưa kịp trao đổi thông tin cụ thể về công việc.", "status_group": 1, "reason_code": "KNM_DAP_MAY", "call_decision": "NO_CALL", "appointment_date": null, "recommended_message": "Chào chị A, ban nãy em gọi nhưng mạng chập chờn. Em gửi chị JD công việc qua Zalo tham khảo nhé!"}}

### 2. Ứng viên từ chối thẳng (Nhóm 1 - Đóng hồ sơ)
Tên ứng viên: Trần Văn B
Nội dung: "À thôi em ơi, anh xin được việc bên khu công nghiệp Quang Châu rồi, không đi làm bên em đâu."
Output:
{{"thinking": "Ứng viên thông báo đã đi làm chỗ khác và từ chối lời mời. Đóng hồ sơ, không gọi lại.", "summary": "Nhân viên liên hệ mời ứng viên Trần Văn B tham gia ứng tuyển vị trí công nhân sản xuất. Ứng viên phản hồi đã tìm được công việc và đang đi làm tại khu công nghiệp Quang Châu. Do đó ứng viên từ chối lời mời tuyển dụng và không có nhu cầu chuyển đổi công việc lúc này.", "status_group": 1, "reason_code": "TU_CHOI_LUON", "call_decision": "NO_CALL", "appointment_date": null, "recommended_message": "Cảm ơn anh B đã phản hồi! Chúc anh công tác tốt. Nếu sau này cần tìm cơ hội mới, cứ nhắn em nha."}}

### 3. Ứng viên đang bận, hẹn gọi lại (Nhóm 2 - Gọi lại)
Tên ứng viên: Nguyễn Thị C
Nội dung: "Chị đang chạy xe ngoài đường ồn lắm em ơi, chiều gọi lại cho chị nhé."
Output:
{{"thinking": "Ứng viên nghe máy nhưng đang bận chạy xe và yêu cầu gọi lại vào buổi chiều. Cần gọi lại sau.", "summary": "Nhân viên gọi điện trao đổi thông tin công việc với ứng viên Nguyễn Thị C. Ứng viên bắt máy nhưng phản hồi đang điều khiển xe ngoài đường ồn ào nên không tiện trao đổi. Ứng viên chủ động đề nghị nhân viên liên hệ lại vào buổi chiều cùng ngày.", "status_group": 2, "reason_code": "KHACH_BAN", "call_decision": "CALL_BACK", "appointment_date": null, "recommended_message": "Dạ em xin lỗi vì gọi lúc chị C đang đi đường ạ! Chiều em sẽ liên hệ lại, hoặc chị rảnh cứ nhắn em nhé."}}

### 4. Ứng viên lưỡng lự, cần suy nghĩ thêm (Nhóm 3 - Tiềm năng/Chăm sóc)
Tên ứng viên: Lê Văn D
Nội dung: "Mức lương cơ bản 5 triệu thì hơi thấp so với chỗ cũ của anh. Chắc để anh xem xét cân nhắc thêm đã."
Output:
{{"thinking": "Ứng viên chê lương thấp và nói cần thời gian cân nhắc. Ứng viên tiềm năng cần chăm sóc thêm.", "summary": "Nhân viên nhân sự liên hệ tư vấn vị trí công nhân cho ứng viên Lê Văn D. Ứng viên bày tỏ băn khoăn khi mức lương cơ bản 5 triệu/tháng thấp hơn so với thu nhập tại nơi làm việc cũ. Ứng viên chưa từ chối ngay mà xin thêm thời gian xem xét và cân nhắc trước khi quyết định.", "status_group": 3, "reason_code": "SUY_NGHI_THEM", "call_decision": "FOLLOW_UP", "appointment_date": null, "recommended_message": "Chào anh D, em hiểu mong muốn của anh về thu nhập. Bên em còn nhiều khoản phụ cấp hấp dẫn, anh cứ cân nhắc nhé!"}}

### 5. Ứng viên quan tâm nhưng chưa chốt ngày phỏng vấn (Nhóm 3 - Tiềm năng/Chăm sóc)
Tên ứng viên: Phạm Thị E
Nội dung: "Công việc nghe cũng được đấy. Nhưng tuần này em bận thi rồi, chưa biết hôm nào rảnh lên công ty được, để em báo sau nha."
Output:
{{"thinking": "Ứng viên ưng ý công việc nhưng bận lịch cá nhân, chưa chốt được ngày phỏng vấn. Cần follow-up sau.", "summary": "Nhân viên tư vấn chi tiết về chế độ và công việc cho ứng viên Phạm Thị E. Ứng viên thể hiện sự quan tâm và đánh giá công việc phù hợp nhưng hiện đang bận lịch thi trong tuần. Ứng viên xin hoãn và hẹn sẽ chủ động nhắn lại sau khi thi xong để sắp xếp ngày đến công ty phỏng vấn.", "status_group": 3, "reason_code": "CHUA_CHOT_NGAY", "call_decision": "FOLLOW_UP", "appointment_date": null, "recommended_message": "Chào E, chúc em thi tốt nhé! Khi nào thi xong và rảnh rỗi, nhắn tin để chị sắp lịch phỏng vấn cho em nha."}}

### 6. Ứng viên vướng giấy tờ (Chờ CCCD) (Nhóm 3 - Tiềm năng/Chăm sóc)
Tên ứng viên: Hoàng Văn F
Nội dung: "Em mất căn cước công dân rồi chị ạ, đang chờ công an cấp lại giấy hẹn, chắc phải 3 ngày nữa mới có để đi làm."
Output:
{{"thinking": "Ứng viên muốn đi làm nhưng thiếu CCCD, cần chờ giấy tờ để làm thủ tục nhận việc.", "summary": "Nhân viên liên hệ hướng dẫn thủ tục nhận việc cho ứng viên Hoàng Văn F. Ứng viên bày tỏ mong muốn đi làm nhưng hiện đang bị mất căn cước công dân và chờ công an cấp giấy hẹn. Ứng viên hẹn khoảng 3 ngày nữa sau khi có giấy tờ sẽ gửi lại để hoàn tất hồ sơ.", "status_group": 3, "reason_code": "CHO_GIAY_TO", "call_decision": "FOLLOW_UP", "appointment_date": null, "recommended_message": "Chào F, em cứ bình tĩnh lo xong giấy tờ nhé. Khi nào có CCCD hoặc giấy hẹn, chụp gửi chị để làm thủ tục nhận việc!"}}

### 7. Ứng viên chốt lịch phỏng vấn cụ thể (Nhóm 4 - Lịch hẹn)
Tên ứng viên: Ngô Thị G
Nội dung: "Vâng chị, vậy sáng mai tầm 9 rưỡi em qua văn phòng công ty nộp hồ sơ phỏng vấn luôn ạ."
Output:
{{"thinking": "Ứng viên đồng ý đến phỏng vấn vào sáng mai lúc 9:30. Đây là lịch hẹn cụ thể.", "summary": "Nhân viên trao đổi và mời ứng viên Ngô Thị G tham gia phỏng vấn trực tiếp tại văn phòng. Ứng viên đồng ý với các yêu cầu công việc và xác nhận sẽ đến nộp hồ sơ vào lúc 9:30 sáng mai. Hai bên đã chốt lịch hẹn cụ thể và chuẩn bị các giấy tờ liên quan.", "status_group": 4, "reason_code": "HEN_PHONG_VAN", "call_decision": "SCHEDULED", "appointment_date": "NGAY_MAI_9H30", "recommended_message": "Chào G! Cảm ơn em đã xác nhận lịch. Hẹn gặp em vào 9:30 sáng mai tại văn phòng công ty nhé. Đi đường cẩn thận nha!"}}

### 8. Ứng viên chốt đi làm (Nhóm 5 - Thành công)
Tên ứng viên: Vũ Văn H
Nội dung: "Em mang hồ sơ qua rồi, giám đốc bảo thứ hai tuần sau bắt đầu đi làm luôn."
Output:
{{"thinking": "Ứng viên đã nộp hồ sơ và được xác nhận thứ 2 tuần sau đi làm chính thức. Tuyển dụng thành công.", "summary": "Nhân viên kiểm tra kết quả tuyển dụng của ứng viên Vũ Văn H. Ứng viên xác nhận đã hoàn tất nộp hồ sơ và được giám đốc trực tiếp phê duyệt tiếp nhận. Hai bên đã thống nhất lịch đi làm chính thức bắt đầu từ thứ Hai tuần tới.", "status_group": 5, "reason_code": "DI_LAM", "call_decision": "SUCCESS", "appointment_date": null, "recommended_message": "Tuyệt vời quá! Chúc mừng H gia nhập công ty nhé. Chuẩn bị tinh thần thứ 2 tuần sau chiến đấu thôi!"}}
"""

# Vì chỉ có nghiệp vụ HR, ta trỏ Sales về cùng một cấu trúc để không bị lỗi nếu code gọi nhầm
_SALES_FEW_SHOT_EXAMPLES = _HR_FEW_SHOT_EXAMPLES

HR_ANALYSIS_TEMPLATE = f"""\
{_STATUS_DEFINITIONS}
{_OUTPUT_SCHEMA}
{_HR_FEW_SHOT_EXAMPLES}

---

---
## Bối cảnh Dự án (Đọc kỹ để phân biệt ai đang nói):
1. ĐÂY KHÔNG PHẢI LÀ AUDIO CÓ PHÂN TÁCH GIỌNG. Bản bóc băng là một đoạn text liền mạch.
2. Công việc: TUYỂN CÔNG NHÂN cho các nhà máy, xí nghiệp nước ngoài (không phải công trình).
3. Danh mục Toàn bộ Doanh nghiệp Tuyển dụng Đối tác (Hệ thống Việc 3 Miền):
   - Doanh nghiệp đối tác: {_COMPANIES_STR}
   - Khu công nghiệp trọng điểm: {_KCN_STR}
4. Người gọi (HR): Thường là người nói trước, hay xưng "em", gọi "anh/chị", giới thiệu: "Dạ em chào anh, em đến từ công ty tìm việc 3 miền...". Nhiệm vụ của HR là mời đi làm công nhân.
5. Người nghe (Ứng viên): Thường trả lời ngắn gọn sau câu giới thiệu của HR (Ví dụ: "Anh đi làm rồi", "Công ty ở đâu", "Lương bao nhiêu").
=> Dựa vào quy luật này để suy luận đâu là câu của HR, đâu là câu phản hồi của ứng viên.

## Nhiệm vụ thực tế của bạn:
Tên ứng viên: {{contact_name}}
Nội dung bóc băng (Transcript):
\"\"\"
{{context_data}}
\"\"\"

Lưu ý quan trọng:
- Tập trung 100% vào nghiệp vụ Tuyển dụng Nhân sự.
- Chuẩn hóa tên riêng: Do chất lượng âm thanh hoặc lỗi bóc băng, tên công ty có thể bị lệch (ví dụ "vi xịt", "vi xếch"). Hãy luôn tự động chuẩn hóa về đúng tên công ty (ví dụ "Vixech") khi viết summary và recommended_message.
- Nếu transcript rỗng, toàn tiếng rè, hoặc chỉ có tiếng nhân viên thử mic -> status_group=2, reason_code="LOI_AM_THANH" hoặc "CUOC_GOI_RONG", call_decision="CALL_BACK"
- appointment_date phải định dạng ISO 8601 (YYYY-MM-DDTHH:MM:00) nếu có lịch hẹn. Nếu không -> null.
- Trả về JSON thuần.

JSON output:
"""

SALES_ANALYSIS_TEMPLATE = HR_ANALYSIS_TEMPLATE
