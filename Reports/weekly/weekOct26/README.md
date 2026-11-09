# FollowUpAgent — tổng hợp cập nhật đến 27/10/2026

**Mốc đối chiếu:** [`WeekOct5`](../WeekOct5/context_and_work_log.md) (tài liệu đó đã ghi cả thay đổi ngày 06/10). **Mã nguồn đối chiếu:** nhánh `testing`, commit `e659a6a`. **Phạm vi:** những thay đổi có bằng chứng trong Git, mã nguồn, CSV cục bộ và kết quả API mà Thanh đã gửi trong phiên làm việc. Đây là báo cáo tiến độ; không xem các kết quả AI chưa được người kiểm tra là ground truth.

**Bổ sung ngày 28/10:** [phần audio và gán nhãn](audio_and_labeling.md) ghi thêm chế độ chạy tiếp cho 713 file ở commit `26f1e0b`; các phần còn lại giữ mốc báo cáo 27/10.

## Đọc theo mục đích

| Tài liệu | Nội dung |
| --- | --- |
| [Slide LaTeX](followupagent_oct26_slides.tex) | Beamer 8 slide, tổng hợp tiến độ đến 28/10; biên dịch bằng XeLaTeX |
| [Báo cáo tuần 26/10](weekly_report.md) | Bản trình bày ngắn cho nhóm, kết quả và việc tiếp theo |
| [Nhật ký công việc](context_and_work_log.md) | Dòng thời gian, từng file sửa và lý do, những gì đã xác minh |
| [Prompt và phân loại](prompt_and_classification.md) | 12 reason code, 5 status group, chặn mã lạ, luồng Ollama, điểm cần xem lại |
| [Audio và gán nhãn](audio_and_labeling.md) | 50 audio cũ, API `/recordings` 713 mã, script tải, CSV review và trạng thái server |
| [Hướng dẫn gán nhãn](labeling_guideline.md) | Bảng mã chuẩn và cách điền hai cột Human sau khi nghe audio |
| [Tên công ty và STT](companies_and_stt.md) | Danh mục 115/110 tên, text normalizer, trường hợp Luxshare |

## Tóm tắt để báo cáo nhóm

1. **Phân loại HR đã có một nguồn quy định trong mã nguồn.** `ReasonCode` có 12 giá trị, ánh xạ cố định sang 5 nhóm và 5 `call_decision`. Prompt lấy danh sách từ nguồn này. Khi LLM trả mã ngoài danh sách, phân tích báo lỗi thay vì ghi một mã mới vào kết quả.
2. **Prompt được mở rộng và siết lại.** Từ 06/10, tóm tắt yêu cầu 3–5 câu; bảng nhóm, bối cảnh tuyển công nhân, 8 ví dụ mẫu và tên doanh nghiệp/KCN được đưa vào prompt. Ngày 27/10, prompt và schema Ollama giới hạn reason code; nhóm và hành động được suy ra trong Python. Mẫu ngày hẹn được đổi sang ISO 8601.
3. **STT có giới hạn lặp và hậu xử lý tên riêng.** Từ 02/10, `transcribe_audio()` truyền `no_repeat_ngram_size=3` và `repetition_penalty=1.1` để hạn chế chữ lặp từ audio ít tiếng nói; chưa có bước phát hiện im lặng. Regex sau đó chuẩn hóa Vixech, Luxshare, Foxconn, Goertek, Pegatron, Quanta, Wistron, Canon và một số KCN. Riêng “lắc xê” → Luxshare được bổ sung ngày 27/10. JSON gốc có 115 đơn vị; danh sách prompt có 110 tên và 28 KCN.
4. **Nguồn audio mới khác nguồn 50 cuộc gọi cũ.** Script `/deals` chỉ tìm 50 link từ 19 deals. API `/recordings` trả `count=713`, `limit=100`, `offset=0` theo response Thanh đưa; 100 là kích thước trang. Script mới phân trang, tải WAV từ `/media/play/{call_id}.wav`, kiểm tra file và hỗ trợ chạy lại.
5. **Gán nhãn là bước tạo bản nháp để người rà soát.** Script dùng PhoWhisper + LLM, in kết quả từng file và ghi CSV có hai cột Human để trống. Đã thêm `--audio-dir`, `--output`, `--limit` để xử lý thư mục audio mới, thử 5 file rồi mới chạy toàn bộ.

## Trạng thái xác minh

- **Đã xác minh trong repo:** 6 commit từ 06/10 đến 27/10; ánh xạ 12 mã/5 nhóm; hai CSV review mới (50 dòng mỗi file) chỉ dùng mã hợp lệ; 6 kiểm thử cục bộ cho downloader và Luxshare chạy đạt.
- **Chưa xác minh từ máy này:** đã tải đủ 713 WAV trên `ood-master`, đã chạy gán nhãn 713 cuộc gọi, độ chính xác sau khi người nghe, và mức hỗ trợ JSON Schema của Ollama đang triển khai. Chưa có log hoặc CSV từ lô 713 trong workspace cục bộ.
- **Dữ liệu lịch sử:** CSV cũ 50 dòng có 8 mã AI ngoài bộ quy định hiện nay; cả ba CSV cục bộ đều còn trống hai cột Human.

## Mốc Git dùng để truy vết

`462454a` (06/10: rule, summary, STT) → `70073eb` (07/10: tên đối tác/KCN) → `d7a9d0f` (27/10: bộ mã và schema) → `a6d9c53` (27/10: Luxshare) → `62c66ff` (27/10: tải recordings) → `e659a6a` (27/10: gán nhãn từ thư mục tùy chọn).

**Ghi chú lưu trữ hiện tại:** `Reports/` đã được đưa vào Git khi cấu trúc lại repo. Nội dung dưới đây là báo cáo lịch sử tháng 10; hướng dẫn thao tác mới nằm trong `thanh-workspace/`.
