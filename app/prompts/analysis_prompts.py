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
    ReasonCode.DI_LAM: "Ứng viên thiện chí, nói sẵn sàng đi làm/nhận việc/đến nhà máy để đi làm. Không cần HR xác nhận lại. Nếu đang thiếu giấy tờ thì dùng CHO_GIAY_TO.",
    ReasonCode.HEN_PHONG_VAN: "Ứng viên đồng ý tham gia phỏng vấn. Có thể chưa chốt ngày; HR sẽ liên hệ Zalo để chọn ngày. Ngày hẹn chỉ điền khi cả hai bên đã xác nhận.",
    ReasonCode.DANG_DI_LAM: "Ứng viên đang làm nơi khác nhưng chủ động nghe, hỏi hoặc trao đổi về công việc bên mình. Cần follow-up để thuyết phục chuyển việc.",
    ReasonCode.CHO_GIAY_TO: "Ứng viên muốn tiếp tục nhưng đang chờ CCCD, giấy khám sức khỏe hoặc hồ sơ cần thiết; theo dõi giấy tờ trước khi chốt đi làm.",
    ReasonCode.HEN_XA: "Ứng viên hẹn liên hệ lại sau một khoảng thời gian xa. Summary ghi rõ khoảng thời gian; nếu không nói rõ, hẹn gọi lại sau 7 ngày.",
    ReasonCode.SUY_NGHI_THEM: "Ứng viên lưỡng lự, chưa nói sẽ đi làm hoặc phỏng vấn; chỉ hỏi thông tin và chưa cam kết bước tiếp theo.",
    ReasonCode.KHACH_BAN: "Ứng viên nói đang bận, yêu cầu liên hệ lại.",
    ReasonCode.CUOC_GOI_RONG: "Cuộc gọi dài nhưng không có nội dung tuyển dụng có ích, chỉ alo, im lặng hoặc nói chuyện không liên quan.",
    ReasonCode.LOI_AM_THANH: "Audio dài nhưng rè, mất tiếng hoặc transcript vô nghĩa khiến không hiểu được nội dung.",
    ReasonCode.KNM_DAP_MAY: "Cuộc gọi dưới 15 giây, ứng viên chủ động cúp ngay sau lời chào, không hẹn gọi lại. Nếu không chắc ai cúp, không chọn mã này.",
    ReasonCode.SAI_SO_NHAM_SO: "Người nghe xác nhận nhầm người hoặc nhầm số.",
    ReasonCode.TU_CHOI_LUON: "Ứng viên từ chối công việc hoặc yêu cầu không liên hệ nữa. Nếu đã làm nơi khác, nghe vài thông tin rồi tự kết thúc mà không muốn trao đổi tiếp, cũng dùng mã này. Phải phân biệt từ chối công việc với từ chối phương tiện, ca làm, đường đi hoặc một đề xuất riêng.",
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
Thời lượng audio: {audio_duration_seconds} giây. Kiểu tách người nói: {speaker_mode}.
Doanh nghiệp đối tác: """ + _COMPANIES + """
Khu công nghiệp: """ + _PARKS + """
Nếu dòng bắt đầu bằng HR/Ứng viên, dùng đúng nhãn đó. Nếu chỉ có Kênh 1/Kênh 2,
suy ra vai từ lời giới thiệu; nếu không chắc, không gán lời HR cho ứng viên.
Transcript:
\"\"\"
{context_data}
\"\"\"

Quy tắc:
1. SUY_NGHI_THEM khi lưỡng lự. Đồng ý kết bạn Zalo/Facebook một mình chưa phải đồng ý đi làm.
2. Người đang đi làm nơi khác mà còn hỏi, nghe và trao đổi tích cực: DANG_DI_LAM.
   Nếu họ chỉ nghe vài thông tin rồi chủ động kết thúc, không muốn tiếp tục: TU_CHOI_LUON.
3. Từ "không" chỉ là từ chối việc làm khi nó nói về công việc/tiếp tục liên hệ.
   "Không đi xe máy", "không làm ca đêm" hoặc từ chối một nhà máy riêng không tự động là TU_CHOI_LUON.
4. Đồng ý phỏng vấn: HEN_PHONG_VAN, kể cả ngày sẽ chốt sau qua Zalo.
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
   ghi thời gian hẹn; không rõ thời gian thì ghi cần gọi lại sau một tuần.
8. candidate_evidence là câu nguyên văn của ỨNG VIÊN làm căn cứ cho reason_code;
   để chuỗi rỗng khi audio không có lời ứng viên rõ ràng. Với TU_CHOI_LUON,
   refusal_basis là explicit_job_refusal hoặc employed_disengaged; các mã khác là none.
   Không bịa câu nói hoặc gán lời HR cho ứng viên.

Ví dụ ranh giới:
- "Mai anh ra, em cứ kết bạn Zalo, anh chấp nhận" → DI_LAM; summary ghi nguyên câu và HR cần đón.
- "Anh đang làm chỗ khác, lương bên em bao nhiêu, gửi Zalo anh xem" → DANG_DI_LAM.
- "Anh đang làm rồi, không có nhu cầu chuyển việc" → TU_CHOI_LUON.
- "Em đi phỏng vấn được, ngày nào để nhắn Zalo sau" → HEN_PHONG_VAN, appointment_date=null.
- "Để tháng sau mình nói tiếp" → HEN_XA, summary ghi tháng sau.
- "Không đi xe máy được, mai anh bắt xe lên nhà máy" → DI_LAM.

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
