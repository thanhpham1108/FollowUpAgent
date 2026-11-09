# Tên nhà máy, KCN và chuẩn hóa transcript

## 1. Vấn đề quan sát được

PhoWhisper có thể nghe tên riêng thành từ thông thường. Tài liệu WeekOct5 đã ghi “vi xịt” → Vixech. Ngày 27/10, Thanh cung cấp transcript có “nhà máy ở **lắc xê** Nghệ An” trong khi tên đúng là **Luxshare**. Một quy tắc cũ đã bắt “lắc se/lắc xe” nhưng chưa bắt đủ biến thể âm/vần của ca thực tế.

## 2. Hai lớp xử lý đang có

1. [`app/services/audio_service.py`](../../../backend/app/audio/service.py) gọi PhoWhisper, sau đó gọi `normalize_transcript()` trước khi chuyển transcript cho LLM và ghi CSV. [`app/utils/text_normalizer.py`](../../../backend/app/audio/normalizer.py) dùng regex không phân biệt hoa/thường để sửa một số biến thể âm cụ thể: Vixech, Foxconn, Luxshare, Goertek, Pegatron, Quanta, Wistron, Canon; cùng Quang Châu, Vân Trung, Quế Võ, Đình Trám, Đồng Văn, Yên Phong và VSIP.
2. [`app/prompts/analysis_prompts.py`](../../../backend/app/classification/analysis_prompt.py) đưa tên các đối tác và KCN vào ngữ cảnh LLM, nhắc model viết đúng trong summary và recommended message. Việc này giúp ở lớp diễn giải, nhưng không thay thế kiểm tra thủ công transcript khi âm thanh khó nghe.

## 3. Rule chống lặp khi PhoWhisper gặp audio thiếu tiếng nói

Thanh từng thấy file gần như không có tiếng nói nhưng PhoWhisper vẫn sinh nhiều chữ lặp. Để hạn chế hiện tượng này, commit **02/10 `a37d16a`** thêm `generate_kwargs` vào [`transcribe_audio()`](../../../backend/app/audio/service.py): `no_repeat_ngram_size=3`, `repetition_penalty=1.1` và ban đầu cả `temperature=0.0`. Commit **02/10 `7130138`** bỏ `temperature=0.0`; code hiện giữ đúng hai tham số đầu.

Script gán nhãn [`auto_label_ground_truth.py`](../../../backend/scripts/auto_label_ground_truth.py) dùng `transcribe_audio()` nên áp dụng rule. Luồng API `speech_to_text()` cũng gọi cùng hàm. Script bóc băng độc lập [`generate_transcripts.py`](../../../backend/scripts/generate_transcripts.py) tự tạo pipeline khác và **không truyền** hai tham số này.

Đây là giới hạn trong bước **sinh chữ**, không phải bộ nhận diện audio im lặng. Chưa có phép đo năng lượng âm thanh, VAD hoặc ngưỡng `no_speech` riêng trong mã dự án trước khi gọi STT. Nếu đầu vào gần như câm nhưng model vẫn sinh một transcript có vẻ hợp lệ, normalizer và LLM vẫn có thể xử lý nó như lời nói thật; cần nghe mẫu để xác nhận. Prompt HR có hướng dẫn chọn `LOI_AM_THANH`/`CUOC_GOI_RONG` khi transcript rỗng hoặc toàn tiếng rè, nhưng hướng dẫn đó không tự phát hiện một transcript dài bị STT bịa lặp.

## 4. Các đợt thay đổi

- **06/10, `462454a`:** tạo normalizer nền, nối vào `transcribe_audio()` ngay sau STT; sửa Vixech và một số KCN thường sai.
- **07/10, `70073eb`:** bổ sung các mẫu nghe sai của Goertek, Pegatron, Quanta, Wistron, Canon, VSIP và KCN khác; tạo danh sách đối tác trong `app/core/companies.py` để tiêm vào prompt thay vì ghi vài tên mẫu trong prompt.
- **27/10, `a6d9c53`:** mở regex Luxshare để bắt `lắc xê`, `lắc xé`, `lắc xế`, `lắcxé`, `lác xe`, `lạc xe`, `lát xe` và các dạng cũ. Câu mẫu “nhà máy ở lắc xê nghệ an” phải trở thành “nhà máy ở Luxshare nghệ an”.

## 5. Số lượng danh mục chính xác

[`data/viec3mien_companies.json`](../../../data/viec3mien_companies.json) có **115 phần tử** theo dữ liệu lưu cục bộ. [`app/core/companies.py`](../../../backend/app/classification/companies.py) hiện khai báo **110 chuỗi doanh nghiệp** và **28 KCN**. Prompt lấy danh sách Python, vì vậy **không nên báo rằng toàn bộ 115 bản ghi JSON đang được tiêm vào prompt**. Cũng không phải mỗi tên trong 110 tên đều có regex riêng; normalizer chỉ bắt các biến thể được định nghĩa cụ thể trong file.

Danh mục đầy đủ của mốc trước nằm trong [catalog WeekOct5](../WeekOct5/viec3mien_companies_catalog.md). Khi cập nhật, cần đối chiếu 5 phần tử khác biệt và tên trùng/biến thể trước khi sửa danh sách runtime.

## 6. Kiểm tra và giới hạn

- Hai kiểm thử cục bộ cho Luxshare và câu mẫu chạy đạt trong lượt `python3 -m unittest tests.test_download_recordings tests.test_text_normalizer -q` ngày 27/10. File [`tests/test_text_normalizer.py`](../../../tests/test_text_normalizer.py) đang **chưa được Git theo dõi** ở workspace này; không coi đó là kiểm thử đã triển khai trên server.
- Regex hậu xử lý có thể thay nhầm một cụm từ đời thường giống tên công ty; cần so transcript với audio thật ở các ca khó.
- Các bản CSV cục bộ đã có cột `Transcript_Cleaned`, nhưng chưa có nhãn Human để đo riêng tác động của normalizer lên chất lượng phân loại.
