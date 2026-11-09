"""HR classification prompt built from the canonical reason-code table."""

from app.core.classification import REASON_CODE_GROUP, ReasonCode

try:
    from app.core.companies import get_companies_prompt_string, get_industrial_parks_prompt_string

    _COMPANIES = get_companies_prompt_string()
    _PARKS = get_industrial_parks_prompt_string()
except ImportError:
    _COMPANIES = "Luxshare ICT, Foxconn, Goertek, Pegatron, Quanta, Vixech"
    _PARKS = "Quang Châu, Vân Trung, Quế Võ, VSIP, Tràng Duệ"

_RULES = {
    ReasonCode.DI_LAM: "Ứng viên thể hiện rõ đã sẵn sàng đi làm/nhận việc/đến nhà máy để đi làm; không cần HR xác nhận lại. 'Có thể đi', 'để sắp xếp đã' hoặc hẹn gọi lại trước khi quyết định chưa phải chốt đi làm. Nếu đang thiếu giấy tờ bắt buộc thì dùng CHO_GIAY_TO.",
    ReasonCode.HEN_PHONG_VAN: "Ứng viên thể hiện rõ thiện chí và sẵn sàng đi phỏng vấn, kể cả khi còn phải sắp xếp hoặc đổi lịch. Chưa cần chốt ngày; HR sẽ liên hệ để chọn ngày. appointment_date chỉ điền khi hai bên xác nhận ngày phỏng vấn.",
    ReasonCode.TRAO_DOI_THEM: "Hai bên đã trao đổi công việc nhưng ứng viên chưa đồng ý phỏng vấn, chưa sẵn sàng đi làm, chưa từ chối và cũng không nói cần suy nghĩ. Đồng ý kết bạn Zalo/Facebook chỉ để nhận thông tin vẫn thuộc mã này. Đang làm nơi khác chỉ là bối cảnh, không phải reason code.",
    ReasonCode.CHO_GIAY_TO: "Ứng viên muốn tiếp tục nhưng đang chờ CCCD, giấy khám sức khỏe hoặc hồ sơ cần thiết; theo dõi giấy tờ trước khi chốt đi làm.",
    ReasonCode.HEN_XA: "Hai bên thống nhất liên hệ lại vào thời điểm xa hơn nhưng ứng viên chưa thể hiện rõ sẵn sàng phỏng vấn. Summary ghi mốc hẹn; nếu không rõ khoảng cách từ ngày cuộc gọi, mặc định gọi lại sau 7 ngày.",
    ReasonCode.SUY_NGHI_THEM: "Ứng viên nói rõ cần suy nghĩ hoặc cân nhắc thêm trước khi quyết định. Chỉ hỏi thông tin mà không nói cần cân nhắc thì dùng TRAO_DOI_THEM.",
    ReasonCode.KHACH_BAN: "Ứng viên nói đang bận, yêu cầu liên hệ lại.",
    ReasonCode.CUOC_GOI_RONG: "Cuộc gọi dài nhưng không có nội dung tuyển dụng có ích, chỉ alo, im lặng hoặc nói chuyện không liên quan.",
    ReasonCode.LOI_AM_THANH: "Audio dài nhưng rè, mất tiếng hoặc transcript vô nghĩa khiến không hiểu được nội dung.",
    ReasonCode.KNM_DAP_MAY: "Cuộc gọi dưới 15 giây, ứng viên chủ động cúp ngay sau lời chào, không hẹn gọi lại. Nếu không chắc ai cúp, không chọn mã này.",
    ReasonCode.SAI_SO_NHAM_SO: "Người nghe xác nhận nhầm người hoặc nhầm số.",
    ReasonCode.TU_CHOI_LUON: "Chỉ dùng khi ứng viên nói rõ từ chối chính công việc/cơ hội tuyển dụng hoặc yêu cầu không liên hệ nữa. Đang làm nơi khác, nghe rồi kết thúc cuộc gọi, từ chối một lịch phỏng vấn, không kịp xe, việc gia đình, giấy tờ hay phương tiện không đủ để đóng hồ sơ.",
}
assert set(_RULES) == set(ReasonCode)

_REASON_GUIDE = "\n".join(
    f"- {code.value} (nhóm {REASON_CODE_GROUP[code]}): {_RULES[code]}"
    for code in _RULES
)

HR_ANALYSIS_TEMPLATE = _REASON_GUIDE + """

Bạn phân tích cuộc gọi tuyển công nhân. Quyết định CUỐI CÙNG của ỨNG VIÊN quyết định reason_code.
Tên ứng viên: {contact_name}
Thời điểm phân tích ở Việt Nam: {current_date} ({current_weekday}).
Ngày mai: {tomorrow_date}; ngày kia: {day_after_tomorrow};
thứ Hai tuần sau: {next_monday_date}; thứ Hai tới: {monday_after_next_date}.
Thời lượng audio: {audio_duration_seconds} giây.
Doanh nghiệp đối tác: """ + _COMPANIES + """
Khu công nghiệp: """ + _PARKS + """
Transcript chép liền mạch, chưa xác định người nói. HR thường giới thiệu và hỏi
trước, ứng viên thường trả lời. Nhưng ứng viên cũng có thể hỏi về lương, đường đi,
nhà máy hoặc Zalo; không tự gán mọi câu hỏi cho HR. Dựa vào mạch hỏi-đáp và cách
xưng hô để xác định ai nói; nếu không chắc, không gán lời HR cho ứng viên.
Transcript:
\"\"\"
{context_data}
\"\"\"

Quy tắc:
1. TRAO_DOI_THEM khi chỉ trao đổi thông tin, kể cả đồng ý kết bạn Zalo/Facebook;
   SUY_NGHI_THEM khi ứng viên nói rõ cần cân nhắc. Nếu ứng viên đang làm nơi khác,
   ghi tình trạng đó và mức quan tâm vào summary, rồi chọn mã theo quyết định cuối.
2. Không coi việc cuộc gọi kết thúc hoặc ứng viên đang làm nơi khác là lời từ chối.
   Nếu ứng viên nghe tư vấn mà không có cam kết hoặc lời từ chối: TRAO_DOI_THEM.
3. Từ "không" chỉ là từ chối việc làm khi nó nói về công việc/tiếp tục liên hệ.
   "Không đi xe máy", "không làm ca đêm", "không kịp xe thứ Hai" hoặc từ chối
   một lịch phỏng vấn/nhà máy riêng không tự động là TU_CHOI_LUON.
   Xác định đối tượng bị từ chối và đọc tiếp toàn bộ cuộc gọi trước khi chốt.
4. Có thiện chí rõ và sẵn sàng phỏng vấn: HEN_PHONG_VAN, kể cả khi phải hoãn
   lịch đề xuất hoặc ngày sẽ chốt sau qua Zalo. Không đòi hỏi ứng viên nói đúng
   chữ "đồng ý" nếu toàn bộ đối thoại cho thấy họ sẵn sàng phỏng vấn.
   appointment_date chỉ chứa YYYY-MM-DD khi hai bên xác nhận NGÀY phỏng vấn;
   thiếu ngày hoặc chỉ có ngày HR đề xuất thì null. Không cần giờ.
   Các mã khác luôn có appointment_date=null. Ngày bắt đầu đi làm ghi trong summary.
5. Tính ngày tương đối từ ngày hệ thống ở trên. "Thứ Hai tuần sau" = {next_monday_date};
   "thứ Hai tới" = {monday_after_next_date}. Không lấy năm/ngày ở ví dụ làm ngày cuộc gọi.
6. HEN_XA: nếu ứng viên nói rõ số ngày/tuần, điền follow_up_days tương ứng
   (2 tuần = 14 ngày; tháng sau ≈ 30 ngày); không rõ thì null để hệ thống
   mặc định 7 ngày. Các mã khác: follow_up_days=null.
7. Summary 3-5 câu, đủ bối cảnh, vướng mắc, quyết định cuối và việc HR cần làm tiếp.
   Trích nguyên văn một câu quan trọng của ứng viên nếu nghe rõ. Nếu ứng viên đồng ý
   kết bạn Zalo/Facebook, ghi rõ kênh và lời đáp; "dạ/vâng" sau lời đề nghị được
   xem là đồng ý. Ghi số điện thoại nghe rõ; không đoán số bị mất. Với HEN_XA,
   ghi thời gian hẹn; không rõ thời gian thì ghi cần gọi lại sau một tuần. Nếu
   ngày 13/14 chỉ là đề xuất gọi lại, ghi vào summary nhưng appointment_date=null.
   Nếu ứng viên đang làm nơi khác, ghi rõ nơi làm nếu họ nói, thông tin HR đã
   tư vấn và thái độ sau khi nghe; không suy đoán tên công ty.
8. candidate_evidence là câu nguyên văn của ỨNG VIÊN làm căn cứ cho reason_code;
   để chuỗi rỗng khi audio không có lời ứng viên rõ ràng. Với TU_CHOI_LUON,
   refusal_basis là explicit_job_refusal hoặc stop_contact; các mã khác là none.
   Không bịa câu nói hoặc gán lời HR cho ứng viên.

Ví dụ ranh giới:
- "Mai anh ra, em cứ kết bạn Zalo, anh chấp nhận" → DI_LAM; summary ghi nguyên câu và HR cần đón.
- "Anh đang làm chỗ khác, lương bên em bao nhiêu, gửi Zalo anh xem" → TRAO_DOI_THEM; summary ghi nơi đang làm, lương đã tư vấn và ứng viên muốn xem thêm qua Zalo.
- "Trước anh làm ở Foxconn, giờ đang nghỉ" → ghi quá khứ trong summary; không suy ra ý định từ tình trạng việc làm.
- "Anh đang làm rồi, không có nhu cầu chuyển việc" → TU_CHOI_LUON.
- "Đừng gọi cho anh nữa" → TU_CHOI_LUON, refusal_basis=stop_contact.
- "Em đồng ý kết bạn Zalo để xem thông tin" → TRAO_DOI_THEM nếu chưa nói muốn phỏng vấn/đi làm.
- "Em đi phỏng vấn được, ngày nào để nhắn Zalo sau" → HEN_PHONG_VAN, appointment_date=null.
- "Để tháng sau mình nói tiếp" → HEN_XA, summary ghi tháng sau.
- "Không đi xe máy được, mai anh bắt xe lên nhà máy" → DI_LAM.
- "Thứ Hai anh không kịp xe vì việc gia đình; có thể đi phỏng vấn trước ngày 15; ngày 13/14 em gọi lại nhé" → HEN_PHONG_VAN. Chưa chốt ngày phỏng vấn nên appointment_date=null; summary ghi việc gia đình, mốc 13/14, khả năng đi trước 15 và cần xác nhận lại.

Chỉ trả JSON thuần:
{{
  "summary": "3-5 câu tiếng Việt",
  "reason_code": "một mã chính xác trong danh sách trên",
  "appointment_date": null,
  "follow_up_days": null,
  "candidate_evidence": "trích nguyên văn hoặc chuỗi rỗng",
  "refusal_basis": "none"
}}
"""
