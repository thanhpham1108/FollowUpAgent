# Nguồn audio, tải recordings và quy trình gán nhãn

## 1. Vì sao lệnh cũ chỉ tải 50 audio

[`scripts/extract_audio_urls.py`](../../../backend/scripts/extract_audio_urls.py) gọi `GET /deals`, duyệt từng `/deals/{id}` và lấy `activities[].linkCall`. Theo log Thanh gửi, lần chạy thấy **19 deals, 50 link** và tải 50 file. `--limit 150` là mức trần, nên không tạo ra dữ liệu mới nếu API `/deals` chỉ có 50 link. Trong CSV 50 dòng cũ, bỏ tiền tố số thứ tự của tên file thì chỉ còn **39 call ID khác nhau**; một số cuộc gọi được tham chiếu lặp.

Khi đổi `API_BASE` thành `http://192.168.25.175:8000/docs`, script cũ cố parse trang HTML Swagger như JSON và báo `Expecting value`. `/docs` là trang tài liệu, không phải endpoint dữ liệu. Địa chỉ gốc phải dừng ở `:8000`.

## 2. API recordings mới

Ảnh tài liệu API từ bên cung cấp và response Thanh chạy trên `ood-master` xác nhận các đường dẫn:

| Endpoint | Nội dung | Vai trò |
| --- | --- | --- |
| `GET /docs` | HTML Swagger | Xem API |
| `GET /openapi.json` | JSON mô tả API | Xem path, tham số, response |
| `GET /recordings` | JSON danh sách ID | Lấy các `call_id` |
| `GET /media/play/{call_id}.wav` | Dữ liệu WAV | Tải audio theo ID |

Response đã nhìn thấy: object có `count`, `limit`, `offset`, `recordings`; `recordings[0]` là chuỗi `"18483292"`; `count=713`, `limit=100`, `offset=0`, trang đầu nhận 100 ID. Vì vậy 100 là **số bản ghi của trang đầu**, không chứng minh đó là 100 file mới. Thanh sau đó quyết định **tải toàn bộ** thay vì chọn 100 mã chưa rõ thứ tự. Tổng tại lần chạy thực tế có thể thay đổi nếu server thêm bản ghi.

## 3. Script tải mới đã làm gì

[`scripts/download_recordings.py`](../../../backend/scripts/download_recordings.py) được tạo ở commit `62c66ff` và đẩy lên `testing`. Chế độ inventory đi qua các trang; chế độ `--select all --download` chọn tất cả ID và tải tuần tự. Script kiểm tra `count`, `offset`, số phần tử, ID hợp lệ và mã trùng; từ chối danh sách không nhất quán. Mỗi audio tải vào `.wav.part`, kiểm tra header RIFF/WAVE và `Content-Length` nếu có, rồi mới đổi tên thành `.wav`. File đã hợp lệ được bỏ qua khi chạy lại. Nó lưu `all_call_ids.txt`, `manifest.json`, `selected_call_ids.txt`, thư mục `audio/` và `failed_call_ids.txt`.

Lệnh triển khai trên `ood-master` sau khi pull nhánh `testing`:

```bash
python scripts/download_recordings.py --out-dir data/recordings_import --select all --download
```

**Trạng thái bằng chứng:** 4 kiểm thử cục bộ cho script đã chạy đạt, bao gồm lấy đủ trang, phát hiện offset sai, bỏ qua WAV hợp lệ và từ chối file tải thiếu. Máy Mac trong phiên này không kết nối được API `192.168.25.175:8000` và không truy cập được terminal server. Do đó báo cáo không khẳng định đã có đủ 713 file WAV trên server. Cần kiểm tra `failed_call_ids.txt`, số ID được chọn và số WAV thực tế ở `data/recordings_import/audio/`.

## 4. Gán nhãn: chạy thành phần nào của pipeline

[`scripts/auto_label_ground_truth.py`](../../../backend/scripts/auto_label_ground_truth.py) chạy trực tiếp trên file cục bộ:

```text
WAV → PhoWhisper → normalize_transcript → Qwen/Ollama HR → CSV review
```

Nó in tiến độ, nhóm/mã/hành động và 100 ký tự đầu summary lên terminal; mỗi file ghi một dòng CSV và flush ngay. Hai cột cuối `Human_Status_Group (Điền tay)` và `Human_Reason_Code (Điền tay)` để trống. Script không gọi Rule Engine, không tạo follow-up task trong DB và không gửi webhook CRM. Chỉ sau khi người nghe và điền cột Human, file review mới có nhãn chuẩn để so với AI.

Ở bước PhoWhisper, script gọi chung `transcribe_audio()`, nơi đã đặt `no_repeat_ngram_size=3` và `repetition_penalty=1.1` từ 02/10 để hạn chế sinh chữ lặp. Quy tắc này không phát hiện audio im lặng; file không có tiếng nói vẫn có thể có transcript do model sinh ra. Xem [Tên công ty và STT](companies_and_stt.md).

Trước commit `e659a6a`, script chỉ quét `data/*.wav`, nên bỏ qua thư mục tải mới `data/recordings_import/audio/`. Commit đó thêm `--audio-dir`, `--output`, `--limit` nhưng chưa tiếp tục từ dòng dang dở. **Cập nhật 28/10, commit `26f1e0b`:** thêm `--resume`, `--expected-count`, log lỗi riêng và dừng sau 5 lỗi liên tiếp cho lô 713 file.

Thử 5 file để kiểm tra STT và LLM trên server:

```bash
python scripts/auto_label_ground_truth.py \
  --audio-dir data/recordings_import/audio \
  --output data/recordings_import/review_sample.csv \
  --limit 5
```

Sau khi kiểm tra mẫu, chạy toàn bộ 713 file `.wav` đã tải được. `--resume` giữ một CSV và thử lại những file chưa thành công:

```bash
python scripts/auto_label_ground_truth.py \
  --audio-dir data/recordings_import/audio \
  --output data/recordings_import/ground_truth_review_713.csv \
  --expected-count 713 --resume
```

Nếu có audio tải lỗi, script chặn trước khi gán nhãn vì số WAV chưa đủ 713. Trong chế độ `--resume`, CSV chính chỉ chứa dòng thành công; lỗi STT/LLM được ghi vào file `_error_log.csv` riêng và file thiếu được thử lại khi chạy lại cùng lệnh. Script dừng sau 5 lỗi liên tiếp để tránh xử lý vô ích cả lô. Chạy 713 file có thể kéo dài vì xử lý tuần tự từng cuộc gọi và mỗi cuộc gọi có bước STT/LLM.

## 5. Dữ liệu review đã có trên máy cục bộ

| CSV | Dòng | Định dạng | Quan sát |
| --- | ---: | --- | --- |
| `data/ground_truth_review.csv` | 50 | `Transcript_Raw`; chưa có `AI_Call_Decision` | 8 mã AI ngoài taxonomy mới; Human trống |
| `data/ground_truth_review_20261027_063914.csv` | 50 | `Transcript_Cleaned`, thêm decision và tin nhắn | 0 mã ngoài taxonomy; 43 `LOI_AM_THANH`; Human trống |
| `data/ground_truth_review_20261027_080357.csv` | 50 | Cùng định dạng mới | 0 mã ngoài taxonomy; 44 `LOI_AM_THANH`; Human trống |

Đây là ba bản xuất của bộ 50 tên file cũ, không phải dữ liệu review của 713 cuộc gọi. Chưa có file CSV 713 dòng trong workspace này. Xem [Prompt và phân loại](prompt_and_classification.md) để hiểu vì sao 0 mã lạ chưa đồng nghĩa với phân loại chính xác.

Tài liệu học HTTP và từng câu lệnh vẫn ở [`HUONG_DAN_TAI_AUDIO_TU_CRM_API.md`](../../../HUONG_DAN_TAI_AUDIO_TU_CRM_API.md).
