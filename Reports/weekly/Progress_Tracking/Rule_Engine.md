# FollowUpAgent - Rule Engine & Workflow

*Tài liệu định nghĩa các quy tắc xử lý tự động (Rule Engine) cho dự án FollowUpAgent.*

## Nhóm 1: Trạng thái "Chưa tư vấn"
- **Lý do / Nội dung:** Đơn đã nhận nhưng Sale chưa gọi.
- **Quy định xử lý:** Gọi điện trong vòng 10 phút từ lúc nhận đơn. Check Telegram có thông báo.
- **Dateline (Thời hạn xử lý):** 10 phút.

## Nhóm 2: Trạng thái "Cần gọi lại"
- **Lý do 1:** Không nghe máy lần 1, 2, 3 (Nội dung: KNM 1,2,3 lần).
  - **Quy định 1:** Gọi tối thiểu 3 lần vào 3 khung giờ khác nhau trong ngày. Tương tác thêm với trực page để có thêm thông tin (link FB, Tikmess). Ghi chú rõ: KNM1, KNM2...
  - **Dateline 1:** 1 ngày.
- **Lý do 2:** Không nghe máy lần 4, 5, 6 (Nội dung: KNM 4,5,6 lần).
  - **Quy định 2:** Gọi 1-2 lần trong các ngày tiếp theo. Nếu vẫn không nghe, hủy trạng thái thành "UV không tiềm năng - KNM > 3 lần". Note rõ KNM 7,8...
  - **Dateline 2:** 3 ngày.
- **Lý do 3:** Suy nghĩ thêm (Nội dung: Ứng viên cân nhắc, chưa chốt, chưa gửi CCCD, cần tư vấn thêm).
  - **Quy định 3:** Chăm sóc thường xuyên trên Zalo. Cập nhật 2 ngày/lần. Ghi rõ chân dung khách hàng.
  - **Dateline 3:** 3 ngày.
- **Lý do 4:** Khách bận, gọi lại sau (Nội dung: Bận, đi đường, chưa muốn nghe tư vấn).
  - **Quy định 4:** Sale chủ động hẹn giờ gọi lại và chọn giờ hẹn trên CRM. Nếu liên hệ lại được thì chuyển sang lý do "Suy nghĩ / Tiềm năng". Nếu không liên hệ được quá 3 lần thì chuyển sang "KNM > 3 lần".
  - **Dateline 4:** 3 ngày.

## Nhóm 3: Trạng thái "UV Tiềm năng"
- **Lý do 1:** Người lao động (NLĐ) có nhu cầu, chưa chốt ngày (Nội dung: Nhà có việc, ốm, chờ cắt hợp đồng).
  - **Quy định 1:** Hẹn ngày cụ thể gọi lại. Note rõ chân dung ứng viên.
  - **Dateline 1:** 3 ngày.
- **Lý do 2:** NLĐ có nhu cầu, chờ gửi CCCD để lên hẹn.
  - **Quy định 2:** Đồng bộ trạng thái chat Zalo với trạng thái CRM. Hẹn ngày cụ thể gọi lại.
  - **Dateline 2:** 3 ngày.
- **Lý do 3:** Lịch hẹn xa (Nội dung: Hẹn 1-2 tháng, qua năm mới đi làm).
  - **Quy định 3:** Đồng bộ trạng thái chat Zalo với trạng thái CRM. Note rõ chân dung ứng viên.
  - **Dateline 3:** 3 ngày.

## Nhóm 4: Trạng thái "Hẹn phỏng vấn"
- **Lý do / Nội dung:** Xác nhận phỏng vấn (Khách hẹn ngày phỏng vấn và cung cấp đủ CCCD).
- **Quy định xử lý:** Hẹn đúng số điện thoại ứng viên đang dùng. Điền đầy đủ CCCD và thông tin. Chọn đúng vị trí tuyển dụng, hình thức phỏng vấn.
- **Dateline:** Không quy định (Chốt lịch theo ngày hẹn thực tế).

## Nhóm 5: Trạng thái "Đi làm tạm tính"
- **Lý do / Nội dung:** Sale chăm sóc nắm được khách đã đi làm, cập nhật Đi làm tạm tính trước.
- **Quy định xử lý:** Cập nhật sau khi khách hoàn tất xuống xưởng.
- **Dateline:** 2 ngày.
