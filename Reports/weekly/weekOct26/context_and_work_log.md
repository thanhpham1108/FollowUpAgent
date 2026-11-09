# Nhật ký công việc từ báo cáo WeekOct5 đến 27/10/2026

## 1. Bối cảnh và ranh giới bằng chứng

Dự án FollowUpAgent xử lý cuộc gọi tuyển dụng: nhận URL audio qua API, bóc băng bằng PhoWhisper, chuẩn hóa transcript, phân tích bằng Qwen qua Ollama, lưu DB, áp rule follow-up và gửi webhook CRM. Máy triển khai là `ood-master` với conda `datacore`; chi tiết môi trường CUDA/P100 đã ghi ở [WeekOct5](../WeekOct5/context_and_work_log.md) và không có commit mới cho phần cài GPU trong giai đoạn này.

Báo cáo WeekOct5 đã bao gồm cập nhật 06/10 về 5 nhóm, summary và normalizer. Phần 06/10 bên dưới là **nhắc lại nền kỹ thuật** để câu chuyện liên tục; các thay đổi mới sau đó bắt đầu từ 07/10. Lịch sử Git không có commit từ 08/10 đến 26/10 trên nhánh hiện tại; tài liệu này không suy diễn công việc trong khoảng trống đó.

**Bổ sung tiền sử bị sót:** ngày 02/10, commit `a37d16a` đưa `no_repeat_ngram_size=3`, `repetition_penalty=1.1` và `temperature=0.0` vào lệnh sinh transcript của PhoWhisper để hạn chế chữ lặp trên audio ít/không có tiếng nói. Commit `7130138` cùng ngày bỏ `temperature=0.0`, giữ lại hai tham số chống lặp. Đây là thay đổi **trước mốc WeekOct5**, không phải tính năng mới của tuần 26/10.

## 2. Dòng thời gian

| Ngày/commit | Thay đổi được ghi nhận | Lý do và kết quả |
| --- | --- | --- |
| 06/10 — `462454a` | Điều chỉnh rule 5 nhóm; thêm `call_decision`; summary 3–5 câu và 8 ví dụ; đưa normalizer sau STT | Các nhóm cũ trộn từ chối với gọi lại; tóm tắt quá ngắn; tên công ty/KCN nghe sai |
| 07/10 — `70073eb` | Thêm `app/core/companies.py`, mở rộng regex tên công ty/KCN, đưa danh mục vào prompt | Giúp LLM biết bối cảnh các nhà máy Việc 3 Miền và giảm lỗi tên riêng |
| 27/10 — `d7a9d0f` | Tạo enum 12 reason code, bảng mã→nhóm→hành động; prompt lấy danh sách từ bảng; JSON Schema và chế độ thử lại JSON; CSV review không ghi đè | CSV cũ xuất hiện mã tự tạo như `THONG_TIN_DAO_TAO`, `XAC_NHAN_DI_LAM`; cần buộc mô hình theo danh sách đã quy định |
| 27/10 — `a6d9c53` | Mở rộng regex Luxshare cho “lắc xê”, “lắc xé”, “lác xe”, “lát xe” | Mẫu transcript thực tế vẫn nghe “Luxshare” thành “lắc xê” |
| 27/10 — `62c66ff` | Tạo script `download_recordings.py`, kiểm thử tải/phân trang, hướng dẫn HTTP | Nguồn `/deals` chỉ thấy 50 file cũ; 100 là giới hạn một trang `/recordings`, không phải tổng bản ghi |
| 27/10 — `e659a6a` | Thêm `--audio-dir`, `--output`, `--limit` cho script gán nhãn | Audio mới nằm trong `data/recordings_import/audio/`; lệnh cũ chỉ quét `data/*.wav` |

Các commit từ 27/10 đã được đẩy lên nhánh `testing`. Sự có mặt của mã nguồn trên Git không chứng minh một lệnh cụ thể đã chạy thành công trên `ood-master`.

## 3. Chi tiết thay đổi theo thành phần

### Prompt và phân loại

- [`app/prompts/analysis_prompts.py`](../../../backend/app/classification/analysis_prompt.py): bảng 5 nhóm lấy mã từ `classification.py`, nêu rõ HR tuyển công nhân, transcript không tách giọng, cách phân biệt HR với ứng viên; giữ 8 kịch bản minh họa và yêu cầu summary 3–5 câu. Danh mục doanh nghiệp/KCN được ghép động vào prompt. Ví dụ hẹn phỏng vấn đổi từ `NGAY_MAI_9H30` sang `2026-11-15T09:30:00` để phù hợp parser lịch.
- [`app/prompts/system_prompts.py`](../../../backend/app/classification/system_prompt.py): đưa toàn bộ mã hợp lệ vào system prompt và cấm dịch/ghép/tự tạo mã; yêu cầu JSON thuần, không bịa chi tiết, ngày hẹn ISO 8601.
- [`app/core/classification.py`](../../../backend/app/classification/codes.py): 12 `ReasonCode` và 5 `CallDecision`, ánh xạ cố định. Đây là nguồn quy định để prompt và kết quả không lệch nhau.
- [`app/services/llm_service.py`](../../../backend/app/classification/llm.py): chỉ nhận `context_type="hr"`; gửi schema JSON có enum reason code; khi server trả 400/422 với một số dấu hiệu không hỗ trợ schema, thử lại bằng JSON mode. Mã AI trả về được ép vào `ReasonCode`; mã lạ gây `LLMProcessingError`. `status_group`/`call_decision` được suy ra trong Python, không tin hai trường đó nếu LLM tự ghi sai.
- [`app/schemas/response.py`](../../../backend/app/schemas/response.py): Pydantic buộc `reason_code` và `call_decision` theo enum; validator tính lại nhóm và hành động từ mã.
- [`tests/eval/dataset/samples.json`](../../../tests/eval/dataset/samples.json): sửa expected code/group ở các ca cũ để khớp taxonomy mới; chưa có bằng chứng một lượt eval model hoàn chỉnh sau thay đổi.

Chi tiết ý nghĩa từng mã và những giới hạn của prompt ở [Prompt và phân loại](prompt_and_classification.md).

### STT, tên riêng và lịch follow-up

- [`app/services/audio_service.py`](../../../backend/app/audio/service.py): sau khi PhoWhisper nhận dạng, gọi `normalize_transcript()`; CSV mới ghi `Transcript_Cleaned` từ luồng này. Việc thay tên bằng regex không huấn luyện lại PhoWhisper.
- Cùng hàm `transcribe_audio()` truyền `generate_kwargs={"no_repeat_ngram_size": 3, "repetition_penalty": 1.1}` cho PhoWhisper. Script gán nhãn 713 file gọi hàm này nên kế thừa quy tắc chống lặp. Mã hiện **không có bước phát hiện im lặng/VAD** trước STT; hai tham số trên không bảo đảm transcript rỗng khi audio không có lời nói. Script [`generate_transcripts.py`](../../../backend/scripts/generate_transcripts.py) tạo pipeline riêng và không truyền hai tham số đó.
- [`app/utils/text_normalizer.py`](../../../backend/app/audio/normalizer.py): thêm các cách nghe sai tên nhà máy/KCN, rồi bổ sung thêm Luxshare sau ca “lắc xê”.
- [`app/core/companies.py`](../../../backend/app/classification/companies.py): danh mục Python dùng trong prompt có **110 tên doanh nghiệp** và **28 KCN** tại thời điểm kiểm tra; JSON nguồn [`data/viec3mien_companies.json`](../../../data/viec3mien_companies.json) có **115 phần tử**. Vì vậy câu mô tả “tiêm đủ 115 công ty” trong vài comment/tài liệu cũ không đúng chính xác với danh sách runtime hiện nay.
- [`app/services/rule_engine.py`](../../../backend/app/followup/rules.py): Nhóm 1 không tạo lịch; nhóm 2 hẹn 15 phút hoặc 2 giờ; nhóm 3 là 3 ngày; nhóm 4 nhắc trước hẹn 1 ngày; nhóm 5 theo dõi sau 2 ngày. Từ commit `d7a9d0f`, lịch ISO 8601 không timezone được hiểu theo giờ Việt Nam rồi đổi sang UTC trước khi lưu.
- [`docker-compose.yml`](../../../docker-compose.yml): `DATABASE_URL` chuyển sang `postgresql+asyncpg://...` cho kết nối async; đây là sửa cấu hình, không có bằng chứng deploy Compose trong giai đoạn này.

### Audio và gán nhãn

- [`scripts/extract_audio_urls.py`](../../../backend/scripts/extract_audio_urls.py) là script `/deals` cũ. Lần chạy trên server tìm 19 deals, 50 link; `--limit 150` không thể làm xuất hiện 100 file mới. Đặt `API_BASE` thành `/docs` gây lỗi parse HTML thành JSON.
- [`scripts/download_recordings.py`](../../../backend/scripts/download_recordings.py) là script mới cho `GET /recordings` và `GET /media/play/{call_id}.wav`. Nó đi hết các trang, kiểm tra offset/count/ID, lưu danh sách, tải vào `.part`, xác thực header WAV, bỏ qua file hợp lệ khi chạy lại và ghi `failed_call_ids.txt`.
- [`scripts/auto_label_ground_truth.py`](../../../backend/scripts/auto_label_ground_truth.py) ghi `Transcript_Cleaned`, nhóm, mã, hành động, ngày hẹn, summary, tin nhắn và hai cột Human. Từ `e659a6a`, nó có thể trỏ đến thư mục audio mới và thử `--limit 5`.
- [`HUONG_DAN_TAI_AUDIO_TU_CRM_API.md`](../../../HUONG_DAN_TAI_AUDIO_TU_CRM_API.md) giải thích `/docs` (HTML), `/openapi.json` (sơ đồ API), JSON danh sách và cách tải trên server.

## 4. Những gì đã kiểm tra được

- Ba CSV cục bộ có 50 dòng/file. File cũ có 8 mã ngoài danh sách 12 mã hiện tại. Hai file tạo lúc 06:39 và 08:03 ngày 27/10 không có mã ngoài danh sách và không có cặp reason/group sai theo bảng mã; hai cột Human đều trống. Đây là kiểm tra **tính hợp lệ của mã**, chưa phải độ đúng của nhãn.
- 6 kiểm thử cục bộ cho script tải recordings và các biến thể Luxshare chạy đạt ngày 27/10. Các kiểm thử dùng response giả; không kiểm tra kết nối API nội bộ từ máy này.
- Server trả `count=713`, `limit=100`, `offset=0`, `recordings[0]="18483292"` theo output Thanh gửi. Không có log hoàn tất tải 713 WAV hoặc CSV gán nhãn 713 dòng trong workspace cục bộ.

## 5. Việc còn cần làm và rủi ro có thật

1. **Xác minh dữ liệu thực tế:** đếm WAV hợp lệ và `failed_call_ids.txt` trên server. Chạy nhãn thử 5 file, sau đó toàn bộ; đối chiếu Human với AI trước khi tính accuracy.
2. **Xem lại `LOI_AM_THANH`:** hai lần review mới gán 43/50 và 44/50 vào mã này; cả các transcript ở những dòng đó đều không rỗng (độ dài 6–469 và 6–577 ký tự). Điều này đòi hỏi nghe mẫu và đọc transcript, chưa đủ để kết luận mã sai.
3. **Xác nhận Ollama:** đường schema và fallback chưa được đo trên bản Ollama/model triển khai. Nếu cả hai định dạng request đều bị từ chối, một file sẽ ghi dòng lỗi trong CSV.
4. **Sales:** `analyze_audio(context_type="sales")` hiện trả lỗi rõ ràng vì chỉ có taxonomy HR. Các schema/webhook Sales cũ vẫn tồn tại; cần bộ mã Sales riêng nếu mở lại luồng đó.
5. **Danh mục tên công ty:** đối chiếu 115 phần tử JSON gốc với 110 tên đang tiêm vào prompt; xem các regex có thay sai từ thông thường không.
6. **Tài liệu cũ:** [guideline WeekOct5](../WeekOct5/labeling_guideline.md) có ví dụ chú thích nhầm mã của nhóm 1. Dùng [guideline mới](labeling_guideline.md) cho lô hiện tại.

Ý tưởng JEV/decision model đã được nhắc trong trao đổi, nhưng không có commit hay tích hợp JEV trong repo đến mốc báo cáo này.
