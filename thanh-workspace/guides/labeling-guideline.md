# Quy tắc gán nhãn cuộc gọi tuyển dụng — 10/11/2026

Áp dụng cho lượt gán nhãn mới. Các CSV và báo cáo tháng 10 là dữ liệu lịch sử; không đổi nhãn cũ hàng loạt. Nghe audio và đọc toàn bộ cuộc gọi trước khi chọn **một** reason code theo quyết định cuối của ứng viên. Transcript một luồng không có nhãn người nói đáng tin cậy: dựa vào mạch hỏi đáp và cách xưng hô để phân biệt HR với ứng viên.

| Nhóm | Reason code | Khi dùng | Hành động |
|---|---|---|---|
| 1 | `TU_CHOI_LUON` | Ứng viên từ chối rõ chính công việc/cơ hội tuyển dụng, hoặc yêu cầu ngừng liên hệ | Đóng hồ sơ |
| 1 | `KNM_DAP_MAY` | Audio dưới 15 giây, ứng viên chủ động cúp ngay, không hẹn lại | Đóng hồ sơ |
| 1 | `SAI_SO_NHAM_SO` | Người nghe xác nhận nhầm số/nhầm người | Đóng hồ sơ |
| 2 | `KHACH_BAN` | Ứng viên đang bận, cần gọi lại | Gọi lại sau 2 giờ |
| 2 | `CUOC_GOI_RONG` | Audio dài nhưng không có nội dung tuyển dụng hữu ích | Gọi lại sau 15 phút |
| 2 | `LOI_AM_THANH` | Audio dài, mất/rè tiếng hoặc transcript vô nghĩa | Gọi lại sau 15 phút |
| 3 | `TRAO_DOI_THEM` | Đã trao đổi nhưng chưa chốt: muốn biết thêm, cần cân nhắc hoặc đang chờ giấy tờ bắt buộc; summary ghi rõ lý do và việc HR cần theo dõi | Theo dõi sau 3 ngày |
| 3 | `HEN_XA` | Hẹn liên hệ lại về sau mà chưa thể hiện rõ thiện chí phỏng vấn | Theo mốc hẹn; không rõ thì sau 7 ngày |
| 4 | `HEN_PHONG_VAN` | Sẵn sàng phỏng vấn, kể cả chưa chốt ngày hoặc phải đổi lịch đề xuất | HR liên hệ chốt ngày; nếu có ngày thì nhắc trước ngày hẹn |
| 5 | `DI_LAM` | Ứng viên xác nhận rõ sẵn sàng đi làm/nhận việc | Theo dõi nhận việc |

`DANG_DI_LAM` đã bỏ. Đang làm ở nơi khác là **bối cảnh** cần ghi trong summary, không phải nhãn. Nếu họ vẫn hỏi về công việc hoặc đồng ý nhận thông tin Zalo mà chưa cam kết, dùng `TRAO_DOI_THEM`. Nếu họ đồng ý phỏng vấn/đi làm, dùng `HEN_PHONG_VAN`/`DI_LAM` tương ứng. Chỉ nghe tư vấn rồi ngắt máy không đủ để gán `TU_CHOI_LUON`.

`SUY_NGHI_THEM` và `CHO_GIAY_TO` là mã lịch sử. Lượt gán nhãn mới dùng `TRAO_DOI_THEM` cho cả hai tình huống; giữ nguyên CSV cũ và chỉ quy đổi mã khi so sánh với taxonomy mới. Nếu còn thiếu giấy tờ bắt buộc để nhận việc, chưa chốt `DI_LAM`.

Từ “không” phải được đọc trong ngữ cảnh. Không đi xe máy, không kịp xe thứ Hai, từ chối một ngày phỏng vấn hay đang bận việc gia đình **không** phải từ chối công việc. Nếu mô hình đưa `TU_CHOI_LUON` hoặc `DI_LAM` nhưng bằng chứng không chắc, hệ thống thử phân loại lại một lần. Nếu vẫn thiếu căn cứ từ chối, hệ thống gán tạm `TRAO_DOI_THEM` và ghi vào error log để nghe lại; `DI_LAM` thiếu căn cứ vẫn cần người kiểm tra.

Mốc kiểm tra đã thống nhất:

- `18522754.wav`: hỏi kỹ Luxshare, đường đi và Zalo, nói “mai anh ra” → `DI_LAM`.
- `18571597.wav`: không kịp phỏng vấn thứ Hai vì việc gia đình, nhưng có thiện chí đi phỏng vấn trước ngày 15; HR hẹn liên hệ 13/14 → `HEN_PHONG_VAN`, `appointment_date=null`. Summary ghi rõ ngày gọi lại và lý do đổi lịch.

Summary thường 3–5 câu, tối đa 8 câu khi nhiều dữ kiện: hồ sơ, công việc đã trao đổi, thái độ/điều kiện của ứng viên, quyết định cuối và việc HR cần làm. Với `TRAO_DOI_THEM`, ghi rõ đang cân nhắc điều gì, còn thiếu giấy tờ nào hoặc chỉ muốn nhận thêm thông tin. `appointment_date` chỉ là ngày phỏng vấn đã được hai bên xác nhận (`YYYY-MM-DD`); các mã khác để `null`. `follow_up_days` chỉ áp dụng cho `HEN_XA`.

## Chạy thử trên server

Từ thư mục `~/datacore/FollowUpAgent`, script mặc định đọc `data/recordings_import/audio`, yêu cầu đủ 713 WAV và xuất sang `data/recordings_import/ground_truth_review_713_merged.csv`. Dùng các bước trong [hướng dẫn chạy 713 recording](relabel-713.md) để không resume nhầm CSV cũ.

```bash
python backend/scripts/auto_label_ground_truth.py --limit 10 --output data/recordings_import/ground_truth_review_713_merged.csv
```

CSV dùng để người gán nhãn điền tay. File cùng tên hậu tố `_decision_trace.jsonl` ghi kết quả thô, mã đề xuất, câu bằng chứng, lần phân loại lại và quyết định guard theo từng audio. File `_error_log.csv` ghi các audio cần nghe lại/lỗi. Kiểm tra các ca nêu trên và 10 audio đầu trước khi chạy toàn bộ 713; không coi nhãn AI là ground truth khi chưa nghe và duyệt.
