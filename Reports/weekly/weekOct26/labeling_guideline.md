# Hướng dẫn nghe lại và điền nhãn chuẩn

Áp dụng cho CSV do [`scripts/auto_label_ground_truth.py`](../../../backend/scripts/auto_label_ground_truth.py) xuất từ audio tuyển dụng. **AI là gợi ý**; người gán nhãn cần nghe file `.wav` theo `File_Name`, đọc transcript và điền hai cột `Human_Status_Group (Điền tay)` và `Human_Reason_Code (Điền tay)`.

## Bảng mã hiện hành

| Human group | Human reason code | Dùng khi nghe được bằng chứng này |
| ---: | --- | --- |
| 1 | `TU_CHOI_LUON` | Ứng viên nói rõ không có nhu cầu hoặc từ chối công việc |
| 1 | `KNM_DAP_MAY` | Ứng viên kết thúc cuộc gọi ngay sau lời chào, không có hẹn gọi lại |
| 1 | `SAI_SO_NHAM_SO` | Người nghe xác nhận nhầm người/nhầm số |
| 2 | `KHACH_BAN` | Ứng viên đang bận và cần liên hệ lại, ví dụ đang lái xe |
| 2 | `CUOC_GOI_RONG` | Cuộc gọi không hình thành trao đổi có ích: hộp thư thoại, chỉ alo thử mic hoặc im lặng do không có hội thoại |
| 2 | `LOI_AM_THANH` | File bị rè/mất tiếng/đứt kết nối khiến không thể hiểu nội dung chính |
| 3 | `SUY_NGHI_THEM` | Đã trao đổi và ứng viên muốn cân nhắc, chưa chốt quyết định |
| 3 | `CHUA_CHOT_NGAY` | Quan tâm hoặc đồng ý hướng đi nhưng chưa thống nhất ngày phỏng vấn/đi làm |
| 3 | `CHO_GIAY_TO` | Muốn tiếp tục nhưng phải chờ CCCD, giấy khám sức khỏe hoặc hồ sơ cần thiết |
| 3 | `HEN_XA` | Hẹn quay lại sau khoảng thời gian xa, chưa có lịch phỏng vấn cụ thể đã xác nhận |
| 4 | `HEN_PHONG_VAN` | Hai bên đã xác nhận lịch phỏng vấn/nộp hồ sơ cụ thể |
| 5 | `DI_LAM` | Đã chốt nhận việc hoặc ngày bắt đầu làm, không chỉ hỏi thông tin |

Ánh xạ trong mã: nhóm 1 → `NO_CALL`, nhóm 2 → `CALL_BACK`, nhóm 3 → `FOLLOW_UP`, nhóm 4 → `SCHEDULED`, nhóm 5 → `SUCCESS`. Nếu chọn reason code, số group phải đúng hàng trong bảng. Bản [guideline WeekOct5](../WeekOct5/labeling_guideline.md) có một ví dụ chú thích sai: mã `LOI_AM_THANH`/`CUOC_GOI_RONG` không thuộc nhóm 1.

## Trình tự gán nhãn một dòng

1. Mở `audio/<File_Name>` của cùng lô CSV, nghe toàn bộ đoạn đủ để xác định kết quả cuộc gọi. Đọc `Transcript_Cleaned` để hỗ trợ, nhưng khi transcript lệch audio thì tin audio.
2. Xem cột AI và summary để biết model hiểu gì. Đừng sao chép AI nếu chưa nghe. Nếu dòng có `Transcript_Cleaned` bắt đầu bằng `Lỗi:` hoặc các cột AI trống, xử lý lỗi pipeline trước khi chấm nhãn.
3. Chọn **một** reason code phù hợp nhất với kết quả cuối cuộc gọi. Điền đúng chuỗi chữ hoa và số group cùng hàng. Giữ nguyên cột AI để sau này so sánh; lưu một bản CSV mới nếu dùng Excel.
4. Với ca chưa rõ người nào nói, cuộc gọi bị cắt hoặc nhiều ý định trong một đoạn, ghi chú riêng ID và phần audio làm căn cứ để cùng nhóm thống nhất; không tạo reason code mới ngay trong cột Human.

## Những ca dễ nhầm

- **Dập máy và bận:** `KNM_DAP_MAY` dùng khi cúp ngang không hẹn; `KHACH_BAN` dùng khi người nghe nói đang bận hoặc đề nghị gọi lại.
- **Rỗng và âm thanh lỗi:** `CUOC_GOI_RONG` có file nghe được nhưng không có nội dung trao đổi; `LOI_AM_THANH` là chất lượng audio/kết nối làm không hiểu được. Một transcript không rỗng chưa đủ để bác bỏ lỗi âm thanh: PhoWhisper có thể sinh chữ lặp trên audio rất ít tiếng nói, dù đã đặt tham số hạn chế lặp. Hãy nghe file trước khi chọn mã.
- **Chưa chốt ngày và hẹn phỏng vấn:** `CHUA_CHOT_NGAY` khi chưa xác nhận lịch; `HEN_PHONG_VAN` khi hai bên đã chốt lịch đủ cụ thể.
- **Quan tâm và đi làm:** `SUY_NGHI_THEM`/`CHUA_CHOT_NGAY` vẫn là chăm sóc; chỉ dùng `DI_LAM` khi đã có xác nhận nhận việc hoặc bắt đầu đi làm.
- **Tên nhà máy:** “lắc xê” trong transcript được normalizer đổi thành Luxshare. Tên riêng không tự quyết định status; nghe câu trả lời của ứng viên về công việc.

## Sau khi gán nhãn

Đếm số dòng có Human đầy đủ, đối chiếu từng `Human_Reason_Code` với group theo [`classification.py`](../../../backend/app/classification/codes.py), rồi mới tính tỷ lệ AI trùng Human. Báo riêng lỗi transcript, lỗi chạy LLM và bất đồng nhãn. Ba CSV 50 dòng hiện có ở máy cục bộ đều chưa điền Human, nên chưa thể báo độ chính xác thật.
