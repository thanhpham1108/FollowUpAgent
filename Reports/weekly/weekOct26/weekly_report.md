# Báo cáo tuần 26/10/2026 — FollowUpAgent

**Cập nhật:** 27/10/2026. **Mốc báo cáo trước:** [WeekOct5](../WeekOct5/context_and_work_log.md), đã chứa một số thay đổi 06/10. **Nhánh mã nguồn:** `testing` đến commit `e659a6a`.

## 1. Tiến độ chính từ mốc báo cáo trước

### Phân loại cuộc gọi tuyển dụng

Bộ mã HR hiện có **12 reason code trong 5 status group**. Mỗi mã có đúng một nhóm và một `call_decision`. Prompt lấy danh sách từ cùng bảng enum; LLM service chỉ chấp nhận mã thuộc enum và Python suy ra nhóm/hành động. Việc này xử lý hiện tượng AI tự tạo `THONG_TIN_DAO_TAO`, `XAC_NHAN_DI_LAM` và các mã khác từng thấy trong CSV cũ. Các kết quả chạy thành công không còn chứa mã ngoài danh sách, nhưng độ đúng của **lựa chọn mã** vẫn cần người nghe kiểm chứng.

Quy tắc hành động: nhóm 1 không gọi lại; nhóm 2 gọi lại sau 15 phút hoặc 2 giờ; nhóm 3 chăm sóc sau 3 ngày; nhóm 4 nhắc trước lịch phỏng vấn 1 ngày; nhóm 5 theo dõi sau 2 ngày. Chi tiết từng mã ở [tài liệu prompt và phân loại](prompt_and_classification.md).

### Prompt và chất lượng transcript

Từ thay đổi 06/10, prompt yêu cầu summary 3–5 câu và có 8 ví dụ HR. Ngày 07/10, bổ sung danh sách doanh nghiệp/KCN vào ngữ cảnh; ngày 27/10, siết danh sách reason code và đổi ví dụ ngày hẹn sang ISO 8601. Transcript được chuẩn hóa tên riêng sau PhoWhisper; ví dụ “lắc xê” thành Luxshare. Dữ liệu JSON nguồn có 115 đơn vị, còn danh sách Python thực sự được ghép vào prompt có 110 tên và 28 KCN. [Chi tiết STT và danh mục](companies_and_stt.md).

Một điều chỉnh cũ ngày 02/10 cần ghi lại: `transcribe_audio()` truyền `no_repeat_ngram_size=3` và `repetition_penalty=1.1` cho PhoWhisper nhằm hạn chế chữ lặp trên audio ít tiếng nói. Script gán nhãn dùng đúng hàm này. Chưa có bước phát hiện im lặng trước STT, nên không thể coi hai tham số là cách bảo đảm loại hết transcript bịa từ file câm.

### Audio và đánh nhãn

Script `/deals` cũ chỉ lấy được **50 link từ 19 deals**. API mới `/recordings` trả `count=713`, mỗi trang 100 ID theo output trên `ood-master`. Đã viết script lấy đủ trang và tải WAV có kiểm tra, sau đó sửa script gán nhãn để nhận thư mục audio mới. CSV review in transcript và dự đoán AI, giữ hai cột Human để người đánh nhãn. Script gán nhãn chạy STT và LLM; nó không chạy Rule Engine hay gửi webhook. [Luồng audio và gán nhãn](audio_and_labeling.md).

## 2. Kết quả kiểm tra được tại thời điểm báo cáo

| Kiểm tra | Quan sát | Kết luận thực tế |
| --- | --- | --- |
| CSV cũ 50 dòng | 8 mã AI ngoài bộ 12 mã hiện hành | Cần giữ bản cũ làm bằng chứng lỗi, không dùng làm kết quả mới |
| Hai CSV mới, mỗi file 50 dòng | 0 mã lạ; không có cặp reason/group sai; 43 và 44 dòng `LOI_AM_THANH` | Hợp lệ về cú pháp mã; cần nghe lại nhiều ca nhóm 2 |
| Ba CSV 50 dòng | Hai cột Human đều trống | Chưa đo được accuracy của AI |
| Kiểm thử cục bộ | 6 test cho phân trang/WAV và Luxshare chạy đạt | Chưa thay thế test live trên API, STT và Ollama |
| API recordings | Server báo 713 ID trong response mà Thanh đã chạy | Chưa có bằng chứng tải đủ 713 WAV hoặc gán nhãn 713 file trong workspace cục bộ |

## 3. Những sửa đổi có tác động vận hành

- Request LLM thử JSON Schema trước và thử lại JSON mode khi gặp một số lỗi 400/422 liên quan định dạng. Cần kiểm tra với phiên bản Ollama/model thực tế; fallback không bao phủ mọi kiểu lỗi.
- `context_type="sales"` hiện bị từ chối rõ ràng. Các schema/webhook Sales trước đây còn tồn tại; muốn mở lại phải thiết kế bộ mã riêng thay vì dùng nhãn tuyển dụng.
- `docker-compose.yml` dùng driver `postgresql+asyncpg`; lịch hẹn nhóm 4 parse ISO và quy đổi giờ Việt Nam sang UTC trước khi lưu.
- Script gán nhãn hiện nhận `--audio-dir`, `--output`, `--limit`. Có thể thử 5 file từ thư mục tải mới trước khi chạy toàn bộ; CSV cũ không bị ghi đè.

## 4. Công việc kế tiếp

1. Trên server, xác nhận số WAV hợp lệ bằng số ID dự định tải và xem `failed_call_ids.txt`; chạy lại script tải nếu còn lỗi.
2. Chạy thử 5 audio qua STT/LLM, đọc transcript và summary, rồi chạy toàn bộ lô. Lưu log và CSV để đối chiếu.
3. Nghe lại các ca `LOI_AM_THANH` có transcript dài; điền hai cột Human theo [bảng mã hiện hành](labeling_guideline.md), sau đó mới tính accuracy theo reason code và status group.
4. Kiểm tra request schema/fallback trên Ollama của `ood-master`; sửa nếu deployment từ chối định dạng.
5. Đối chiếu 115 phần tử dữ liệu nguồn với 110 tên được đưa vào prompt; kiểm tra các regex chuẩn hóa tên riêng trên mẫu thực tế.

**Giới hạn báo cáo:** Các thay đổi được truy theo 6 commit 06/10–27/10 và dữ liệu cục bộ. Không có commit ngày 08–26/10 trên nhánh hiện tại, log tải 713 file, hoặc nhãn Human đã hoàn thành trong nguồn được kiểm tra.
