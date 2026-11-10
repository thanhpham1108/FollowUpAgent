"""HR classification prompt built from the canonical reason-code table."""

from app.classification.codes import REASON_CODE_GROUP, ReasonCode

try:
    from app.classification.companies import get_companies_prompt_string, get_industrial_parks_prompt_string

    _COMPANIES = get_companies_prompt_string()
    _PARKS = get_industrial_parks_prompt_string()
except ImportError:
    _COMPANIES = "Luxshare ICT, Foxconn, Goertek, Pegatron, Quanta, Vixech"
    _PARKS = "Quang Châu, Vân Trung, Quế Võ, VSIP, Tràng Duệ"

_RULES = {
    ReasonCode.DI_LAM: "Ứng viên xác nhận sẽ nhận việc hoặc chủ động nói sẽ đến nhà máy để bắt đầu làm, kể cả ngày cụ thể sẽ nhắn qua Zalo; không cần HR xác nhận lại. Một khả năng còn điều kiện hoặc lời HR đề xuất chưa phải quyết định của ứng viên. Nếu còn thiếu giấy tờ bắt buộc để nhận việc thì dùng TRAO_DOI_THEM và ghi rõ giấy tờ cần bổ sung trong summary.",
    ReasonCode.HEN_PHONG_VAN: "Ứng viên thể hiện rõ thiện chí và sẵn sàng đi phỏng vấn, kể cả khi còn phải sắp xếp hoặc đổi lịch. Chưa cần chốt ngày; HR sẽ liên hệ để chọn ngày. appointment_date chỉ điền khi hai bên xác nhận ngày phỏng vấn.",
    ReasonCode.TRAO_DOI_THEM: "Hai bên đã trao đổi công việc nhưng ứng viên chưa chốt phỏng vấn/nhận việc và không từ chối. Bao gồm chỉ nhận thông tin qua Zalo/Facebook, cần suy nghĩ thêm, hoặc muốn tiếp tục nhưng đang chờ CCCD, giấy khám sức khỏe hay hồ sơ bắt buộc. Summary phải ghi rõ lý do còn theo dõi và việc HR cần làm. Đang làm nơi khác chỉ là bối cảnh, không phải reason code.",
    ReasonCode.HEN_XA: "Hai bên thống nhất liên hệ lại vào thời điểm xa hơn nhưng ứng viên chưa thể hiện rõ sẵn sàng phỏng vấn. Summary ghi mốc hẹn; nếu không rõ khoảng cách từ ngày cuộc gọi, mặc định gọi lại sau 7 ngày.",
    ReasonCode.KHACH_BAN: "Ứng viên nói đang bận, yêu cầu liên hệ lại.",
    ReasonCode.CUOC_GOI_RONG: "Cuộc gọi dài nhưng không có nội dung tuyển dụng có ích, chỉ alo, im lặng hoặc nói chuyện không liên quan.",
    ReasonCode.LOI_AM_THANH: "Audio dài nhưng rè, mất tiếng hoặc transcript vô nghĩa khiến không hiểu được nội dung.",
    ReasonCode.KNM_DAP_MAY: "Cuộc gọi dưới 15 giây, ứng viên chủ động cúp ngay sau lời chào, không hẹn gọi lại. Nếu không chắc ai cúp, không chọn mã này.",
    ReasonCode.SAI_SO_NHAM_SO: "Người nghe xác nhận nhầm người hoặc nhầm số.",
    ReasonCode.TU_CHOI_LUON: "Chỉ dùng khi lời cuối của ứng viên từ chối rõ chính cơ hội việc làm hoặc yêu cầu ngừng liên hệ. Phải trích được nguyên văn lời ứng viên nói về việc đó. Đang làm nơi khác, kết thúc cuộc gọi, từ chối một lịch, một phương tiện, một nhà máy hoặc còn việc gia đình không đủ để đóng hồ sơ.",
}
assert set(_RULES) == set(ReasonCode)

_REASON_GUIDE = "\n".join(
    f"- {code.value} (nhóm {REASON_CODE_GROUP[code]}): {_RULES[code]}"
    for code in _RULES
)

HR_ANALYSIS_TEMPLATE = _REASON_GUIDE + """

Bạn phân tích cuộc gọi tuyển công nhân. Chỉ dùng thông tin trong transcript của cuộc gọi này.
Tên ứng viên: {contact_name}
Thời điểm phân tích ở Việt Nam: {current_date} ({current_weekday}).
Ngày mai: {tomorrow_date}; ngày kia: {day_after_tomorrow};
thứ Hai tuần sau: {next_monday_date}; thứ Hai tới: {monday_after_next_date}.
Thời lượng audio: {audio_duration_seconds} giây.
Doanh nghiệp đối tác: """ + _COMPANIES + """
Khu công nghiệp: """ + _PARKS + """
Transcript chép liền mạch, chưa xác định người nói. HR thường giới thiệu và hỏi
trước, ứng viên thường trả lời nhưng cũng có thể hỏi lại. Dựa vào mạch hỏi-đáp,
cách xưng hô và đoạn cuối để suy ra vai nói; nếu không chắc, không gán lời HR
cho ứng viên. Không biến lời HR đề xuất thành quyết định của ứng viên.
Transcript:
\"\"\"
{context_data}
\"\"\"

Trước khi chọn reason_code, tự kiểm tra theo thứ tự (không in các bước suy luận):
1. Xác định các câu của ứng viên và quyết định CUỐI CÙNG của họ. Nếu họ từng
   nói chưa đi được nhưng sau đó nói sẽ đi, lấy ý định sau cùng. Phân biệt
   công việc hiện tại với công việc đã nghỉ; không suy ra ý định từ nơi từng làm.
2. Nếu thấy từ phủ định, xác định chính xác đối tượng bị từ chối: công việc,
   tiếp tục liên hệ, hay chỉ là ngày phỏng vấn, phương tiện, ca làm, giấy tờ,
   nhà máy cụ thể. Chỉ hai đối tượng đầu có thể là TU_CHOI_LUON.
3. TU_CHOI_LUON cần đồng thời: lời từ chối rõ của ứng viên trong transcript,
   đúng đối tượng là cơ hội việc làm hoặc liên hệ tiếp, và không có quyết định
   tiếp tục trao đổi/đi làm ở đoạn sau. Thiếu bất kỳ điều kiện nào thì không
   chọn TU_CHOI_LUON; tuyệt đối không dùng suy đoán từ summary làm bằng chứng.
4. Ứng viên xác nhận sẽ đến nhận việc/đi làm thì DI_LAM. Nếu thể hiện rõ
   sẵn sàng đi phỏng vấn thì HEN_PHONG_VAN, kể cả khi còn phải đổi ngày hoặc
   chốt ngày sau qua Zalo. Chỉ hẹn Zalo để xem thông tin, nói cần cân nhắc,
   hoặc chờ giấy tờ bắt buộc trước khi nhận việc thì TRAO_DOI_THEM.
   Chọn các mã còn lại theo định nghĩa ở trên. Đang làm nơi khác không tự nó
   là lời từ chối. Khi không đủ căn cứ để khẳng định từ chối hay cam kết nhưng
   hai bên vẫn trao đổi việc làm, dùng TRAO_DOI_THEM.
5. candidate_evidence là một đoạn NGẮN, chép nguyên văn từ transcript,
   tối đa 30 từ, do ứng viên nói và trực tiếp chứng minh mã đã chọn. Không
   ghép lời từ hai vị trí, không chép câu ví dụ/quy tắc, không bịa hoặc lặp
   lại câu. Nếu không nghe rõ lời ứng viên thì để chuỗi rỗng. Với
   TU_CHOI_LUON, refusal_basis phải là explicit_job_refusal hoặc stop_contact;
   mọi mã khác là none.
6. Summary là bản tóm tắt cuộc gọi tuyển dụng cho HR, thường 3-5 câu; nếu
   cuộc gọi có nhiều dữ kiện rõ ràng thì dùng 6-8 câu. Chỉ ghi nội dung có
   trong transcript. Gom các nội dung đã được nói rõ theo thứ tự:
   (a) tên, năm sinh, quê và nơi ở hiện tại của ỨNG VIÊN; việc hiện tại, công
   ty từng làm, loại hợp đồng cũ và tình trạng trên hệ thống/tái tuyển nếu có;
   (b) tỉnh, khu công nghiệp, nhà máy ứng viên muốn đến, loại hợp đồng mới
   (chính thức/thời vụ), lương cơ bản, phụ cấp và thưởng được hai bên trao đổi;
   (c) điều kiện/vướng mắc: thể lực, thị lực, hình xăm, tóc nhuộm, học vấn,
   khả năng tính toán, giấy tờ, tài khoản ngân hàng và Zalo nếu có đề cập;
   (d) thái độ và quyết định cuối của ứng viên: muốn đi, còn cân nhắc, đang
   sắp xếp, hay từ chối; nêu căn cứ trong lời nói/hành động, không đoán cảm xúc;
   (e) phương tiện, mốc dự kiến xuống nhận việc/phỏng vấn, ai cần xác nhận
   lịch và ứng viên cần hoàn thiện việc gì trước khi đi.
   Với TRAO_DOI_THEM, nói rõ ứng viên còn cân nhắc, đang chờ giấy tờ nào,
   hay chỉ muốn nhận thêm thông tin; HR phải theo dõi việc tương ứng.
   Không bắt buộc đủ mọi mục; bỏ mục vắng mặt để ưu tiên dữ kiện quan trọng.
   Phân biệt điều HR tư vấn với yêu cầu/cam kết của ứng viên. Ghi mức lương
   cơ bản, phụ cấp và thưởng đã trao đổi nếu transcript nói rõ khoản nào,
   mức bao nhiêu và điều kiện nhận; nêu đó là thông tin HR tư vấn, không phải
   khoản ứng viên chắc chắn sẽ được nhận. Không cộng các khoản thành thu nhập
   chắc chắn hoặc biến đề xuất của HR thành lời đồng ý của ứng viên.
   Không lấy tên Zalo, quê, tuổi, nghề của HR làm thông tin ứng viên; phân biệt
   việc cũ đã kết thúc với việc đang làm và nơi muốn đến với nơi đang ở.
   Trước khi trả JSON, tự đối chiếu từng tên, số, địa điểm, trạng thái, mốc
   thời gian với transcript và đúng người nói; chi tiết không chắc thì bỏ.
   Nếu thiếu ngày nhận việc/phỏng vấn, ghi rõ chưa chốt thay vì tự suy ra.
   Nếu summary và reason_code mâu thuẫn, đọc lại transcript và chọn lại mã;
   không sửa sự thật trong summary để khớp mã. Không chép lời quảng bá,
   quy tắc hoặc tự điền dữ kiện còn thiếu.
   Nếu transcript không đủ rõ để xác định quyết định cuối, nơi ứng tuyển,
   điều kiện đáp ứng hoặc mốc quan trọng cho HR, đặt summary_needs_review=true
   và ghi ngắn gọn điều cần nghe lại vào summary_review_reason. Chi tiết phụ
   không chắc chỉ cần bỏ. Nếu đủ căn cứ thì false và để reason chuỗi rỗng.
7. appointment_date chỉ chứa YYYY-MM-DD khi hai bên xác nhận NGÀY phỏng vấn;
   thiếu ngày hoặc chỉ có ngày HR đề xuất thì null. Không cần giờ.
   Các mã khác luôn có appointment_date=null. Ngày bắt đầu đi làm ghi trong summary.
8. Tính ngày tương đối từ ngày hệ thống ở trên. "Thứ Hai tuần sau" = {next_monday_date};
   "thứ Hai tới" = {monday_after_next_date}. Không lấy ngày từ cuộc khác.
   HEN_XA: nếu ứng viên nói rõ số ngày/tuần thì điền follow_up_days tương ứng;
   không rõ thì null để hệ thống mặc định 7 ngày. Các mã khác: follow_up_days=null.

Chỉ trả JSON thuần:
{{
  "summary": "3-8 câu tiếng Việt tuỳ nội dung",
  "reason_code": "một mã chính xác trong danh sách trên",
  "appointment_date": null,
  "follow_up_days": null,
  "candidate_evidence": "trích nguyên văn hoặc chuỗi rỗng",
  "refusal_basis": "none",
  "summary_needs_review": false,
  "summary_review_reason": ""
}}
"""
