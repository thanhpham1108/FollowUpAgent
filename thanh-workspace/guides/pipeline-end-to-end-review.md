# Phiên review end-to-end — FollowUpAgent

> Cập nhật theo code trong repo ngày 11/11/2026. Đây là tài liệu làm việc để cùng review từng phần, không phải xác nhận rằng service trên server đang dùng đúng phiên bản hoặc cấu hình này.

## Cách dùng tài liệu

Đi từ Phần 01 đến Phần 12. Sau mỗi phần, đối chiếu file được dẫn, ghi câu hỏi/điểm cần sửa ngay trong phiên làm việc và đánh dấu ô **Đã review**. “Đã xây dựng” ở đây nghĩa là có code trong repo; “đã thử” dựa trên báo cáo lịch sử; “chưa xác minh” nghĩa là chưa kiểm tra trạng thái server hoặc dữ liệu đầy đủ trong phiên này.

**Ba nguồn sự thật cần tách riêng:**

1. **Code hiện tại:** xác định service sẽ làm gì nếu chạy từ checkout này.
2. **Cấu hình trên server:** quyết định model, DB, URL webhook và các giá trị thực tế. File cấu hình thật không có trong Git.
3. **Báo cáo cũ:** ghi lại những thử nghiệm đã làm, nhưng có thể dùng đường dẫn hoặc reason code đã thay đổi.

**Tổng quan trạng thái:** API HR, tải audio, STT, chuẩn hóa transcript, phân tích qua Ollama, rule engine, PostgreSQL, webhook, polling và script label hàng loạt đều đã có code. Nhóm đã từng thử luồng đầy đủ với PostgreSQL và webhook theo [báo cáo Week Sep 07](../../Reports/weekly/WeekSep07/system_flow.md). Chưa có bằng chứng trong repo rằng toàn bộ 713 audio đã được người nghe xác nhận nhãn và service đã tích hợp production với CRM.

### Mục lục 12 phần

| Phần | Chủ đề | Kết quả cần nắm khi review |
|---|---|---|
| 01 | Bản đồ repo và hai luồng | Biết code, tài liệu và dữ liệu nằm ở đâu |
| 02 | CRM gọi service | Biết điều gì kích hoạt pipeline và nhận task_id |
| 03 | Nguồn audio và tải file | Phân biệt audio live với lô recording |
| 04 | STT | Biết model nào được gọi, transcript được tạo ra sao |
| 05 | Chuẩn hóa transcript | Biết tên công ty/KCN được sửa ở lớp nào |
| 06 | Ollama và prompt | Biết LLM nhận dữ liệu gì và trả cấu trúc gì |
| 07 | Reason code và guard | Biết cách chốt nhãn, nhóm, action |
| 08 | Summary và ngày hẹn | Biết trường nào được giữ, trường nào cần nghe lại |
| 09 | Rule engine và PostgreSQL | Biết dữ liệu và lịch follow-up được lưu ra sao |
| 10 | Webhook, polling, health | Biết CRM nhận kết quả và xem lỗi bằng cách nào |
| 11 | Lô 713 audio và evaluation | Biết cách tạo CSV, nhãn người và đo kết quả |
| 12 | Deploy, giới hạn và checklist | Biết phần nào đã thử, phần nào còn phải xác minh |

### Hai luồng không được nhập làm một

~~~text
A. Service cho CRM
CRM --POST audio_url--> FastAPI --BackgroundTask--> tải WAV/MP3
    --> STT --> normalizer --> Ollama --> rule engine + PostgreSQL
    --> webhook trả kết quả về CRM
CRM --GET task_id--> API polling --> PostgreSQL

B. Làm ground truth / evaluation
API /recordings --> download_recordings.py --> WAV local
    --> auto_label_ground_truth.py --> CSV + trace + error log
    --> người nghe/đọc summary --> chọn Human_Reason_Code trong Excel/CSV
    --> so sánh nhãn AI với nhãn người
~~~

Luồng B **không** gọi endpoint CRM, không tạo CallRecord/FollowUpTask và không bắn webhook. Luồng A **không** tự chạy chỉ vì file audio mới được lưu trên server ghi âm; hệ thống CRM phải gửi request đến FastAPI.

---

## 01. Bản đồ repo và trách nhiệm

**Mục đích.** Xác định file nào là code chạy, file nào là dữ liệu, file nào chỉ là lịch sử.

**Đầu vào:** repo hiện tại. **Đầu ra:** đường dẫn để lần theo từng bước.

| Vị trí | Đang chứa gì | Vai trò |
|---|---|---|
| [backend/app/](../../backend/app/) | FastAPI, audio, classification, followup, database, webhook | Code service |
| [backend/scripts/](../../backend/scripts/) | tải recording, auto label, transcript, load test | Công cụ chạy thủ công |
| [backend/eval/](../../backend/eval/) | dữ liệu mẫu, judge, script đánh giá | Evaluation tách khỏi API |
| [backend/perf/](../../backend/perf/) | kịch bản Locust | Đo tải |
| [backend/deploy/](../../backend/deploy/) | systemd unit và setup script | Vận hành server |
| [backend/tests/](../../backend/tests/) | kiểm tra hành vi code | Tài liệu kiểm tra đã viết, không chạy trong phiên này |
| [Reports/](../../Reports/) | báo cáo tuần, slide, API tham khảo | Lịch sử và trình bày |
| [thanh-workspace/](../) | guide đang dùng, ghi chú, API contract | Tài liệu làm việc |
| data/ | WAV/ZIP/CSV/Excel trên máy chạy | Dữ liệu thực tế, bị loại khỏi Git bởi [.gitignore](../../.gitignore) |
| [.env.example](../../.env.example) | mẫu biến môi trường | Tham khảo; giá trị thật nằm trong .env ngoài Git |

**Cách xây dựng.** Repo đã được gom thành backend/, Reports/ và thanh-workspace/. Entrypoint FastAPI là [main.py](../../backend/app/main.py). README gốc là [README.md](../../README.md).

**Điểm cần nhớ.** Một số file Sales, email và Zalo còn trong code/schema, nhưng API được mount để phân tích cuộc gọi hiện tại chỉ có endpoint ứng viên HR. Script cũ lấy audio từ /deals vẫn tồn tại; lô 713 dùng API /recordings.

- [ ] Đã review phần 01.
- **Ghi chú/điểm cần sửa:** …

---

## 02. CRM gọi service và tạo task

**Mục đích.** Hiểu chính xác sự kiện khởi chạy pipeline và phản hồi đầu tiên cho CRM.

**Đầu vào:** HTTP POST đến **/api/v1/candidates/analyze** với JSON gồm ssn, candidate_name, audio_url. audio_url là URL tải file, không phải file đính kèm. Cấu trúc được khai báo ở [request.py](../../backend/app/schemas/request.py).

**Luồng code hiện tại:**

1. [main.py](../../backend/app/main.py) tạo FastAPI, đăng ký xử lý lỗi và mount router dưới /api/v1.
2. [api_router.py](../../backend/app/api/v1/api_router.py) mount /candidates, /tasks và /health.
3. [analyze.py](../../backend/app/api/v1/endpoints/analyze.py) tạo mã dạng TASK-xxxxxxxx, đưa process_candidate_audio vào FastAPI BackgroundTasks.
4. API trả **202 Accepted** ngay với task_id, status=processing và message. Kết quả phân tích chưa có trong phản hồi này.
5. Sau phản hồi, tác vụ chạy trong tiến trình FastAPI: tạo CallRecord rồi tải audio, STT, LLM, DB, webhook.

**Đầu ra của bước nhận request:** task_id để CRM dùng khi hỏi trạng thái. Schema phản hồi nằm ở [response.py](../../backend/app/schemas/response.py).

**Cách xây dựng:** FastAPI + Pydantic để kiểm tra JSON đầu vào, BackgroundTasks để tiếp tục xử lý sau HTTP 202. Không có queue bền vững như Redis/Celery trong luồng hiện tại, dù config còn biến REDIS_URL. CallRecord được tạo **bên trong** background task, nên một yêu cầu polling rất sớm có thể nhận 404 trước khi record đầu tiên được commit.

**Điểm chưa xác minh:** service thật có đang chạy trên server hay CRM đã cấu hình gọi endpoint này khi recording được lưu. Bản API contract trong [api-contract.json](../reference/api-contract.json) là tài liệu tham khảo cũ; ví dụ của nó còn recommended_message, khác schema trả về hiện hành.

- [ ] Đã review phần 02.
- **Ghi chú/điểm cần sửa:** …

---

## 03. Nguồn audio và tải file

**Mục đích.** Phân biệt hai cách hệ thống nhận audio.

### 03A. Khi CRM gọi service

**Đầu vào:** audio_url trong request. [audio/service.py](../../backend/app/audio/service.py) lấy đuôi file từ URL, chỉ nhận các extension cấu hình (mặc định mp3, wav, m4a, ogg), tải bằng httpx theo stream và kiểm tra giới hạn kích thước qua Content-Length lẫn số byte đã nhận.

**Xử lý:** audio được lưu tạm với tên ghép task_id và tên file gốc trong AUDIO_DOWNLOAD_DIR. Sau khi STT xong hoặc lỗi, finally xóa file tạm. [audio/files.py](../../backend/app/audio/files.py) còn có hàm dọn file quá hạn để dùng ngoài luồng chính; không thấy scheduler gọi hàm này trong luồng service.

**Đầu ra:** Path của file tạm để STT đọc; transcript được giữ trong DB, audio tạm không được giữ lại bởi luồng chính.

### 03B. Khi lấy lô recording để gán nhãn

**Đầu vào:** API nội bộ /recordings trả object có count, limit, offset và danh sách recording ID. [download_recordings.py](../../backend/scripts/download_recordings.py) phân trang, kiểm tra count/offset/mã trùng và tải từng mã từ /media/play/{call_id}.wav.

**Xử lý:** script có các lựa chọn all, first, last, highest-id hoặc danh sách ID chính xác. Nó ghi all_call_ids.txt, selected_call_ids.txt, manifest.json, failed_call_ids.txt và WAV trong data/recordings_import/audio. File WAV hợp lệ được giữ để resume; file đang tải dùng đuôi .part.

**Đầu ra:** bộ WAV local để chạy script label. [extract_audio_urls.py](../../backend/scripts/extract_audio_urls.py) là script cũ quét /deals và linkCall, từng lấy 50 audio cũ; không phải đường lấy lô /recordings 713 file.

**Giới hạn:** ID lớn hơn chưa chắc có ngày ghi âm mới hơn. Lệnh tải có thể chạy lại nhưng phải chọn đúng ID/lô theo API. Không suy từ /docs rằng đây là JSON data: /docs chỉ là trang Swagger; endpoint dữ liệu là /recordings. Xem [guide API recording](audio-from-crm-api.md).

- [ ] Đã review phần 03.
- **Ghi chú/điểm cần sửa:** …

---

## 04. STT: audio thành transcript

**Mục đích.** Hiểu model nào nghe audio và lỗi STT sẽ ảnh hưởng gì tới LLM.

**Đầu vào:** file audio local. Service nhận file sau bước tải; script gán nhãn đọc trực tiếp WAV trong thư mục.

**Luồng code trong [audio/service.py](../../backend/app/audio/service.py):**

1. get_whisper_model tải một model Transformers automatic-speech-recognition và cache instance cho các lần tiếp theo.
2. Chọn GPU cuda:0 nếu dùng được, nếu không thì CPU; có thử CPU khi load GPU thất bại.
3. Pipeline dùng chunk_length_s=30 và return_timestamps=True; code đưa **nguyên file** vào STT, không tách hai kênh/người nói.
4. Khi generate, dùng no_repeat_ngram_size=3 và repetition_penalty=1.1 để giảm chữ lặp.
5. Đọc thời lượng bằng wave nếu là WAV hợp lệ; với định dạng khác, duration_seconds có thể là None.
6. Chuyển raw text qua normalizer ở Phần 05, trả text, language, chunks và duration_seconds.
7. Trong service, asyncio.to_thread giúp không giữ event loop khi STT chạy; semaphore cho phép một tác vụ STT cùng lúc.

**Đầu ra:** transcript đã chuẩn hóa; service lưu vào CallRecord.transcript. LLM nhận văn bản này, không nghe trực tiếp audio.

**Cấu hình:** code dùng PHOWHISPER_MODEL từ [config.py](../../backend/app/core/config.py). Giá trị mặc định trong code là vinai/PhoWhisper-large, còn [.env.example](../../.env.example) ghi vinai/PhoWhisper-medium. Các CSV tên “Whisper v3 Turbo” phản ánh thử nghiệm; tên file CSV không chứng minh server hiện đang chạy model đó. Cần đọc .env và log nạp model trên server để xác nhận.

**Giới hạn hiện tại:** chống lặp khi generate không phải bộ phát hiện im lặng/VAD. Audio im lặng, mất tiếng hoặc nói chồng lấn vẫn có thể sinh transcript sai; không có diarization đáng tin cậy. Không dùng transcript AI làm nguồn sự thật khi làm ground truth.

- [ ] Đã review phần 04.
- **Ghi chú/điểm cần sửa:** …

---

## 05. Chuẩn hóa tên công ty và khu công nghiệp

**Mục đích.** Hiểu vì sao “lắc xê” có thể thành Luxshare trước khi LLM phân tích.

**Đầu vào:** raw transcript từ STT. **Đầu ra:** transcript đã thay thế một số cách ghi sai.

[normalizer.py](../../backend/app/audio/normalizer.py) áp dụng các regex không phân biệt hoa/thường cho những cách STT thường ghi sai tên Luxshare, Foxconn, Goertek, Pegatron, Quanta, VSIP và một số khu công nghiệp. Hàm normalize_transcript được gọi ngay trong transcribe_audio.

Một lớp khác là [companies.py](../../backend/app/classification/companies.py): danh mục đối tác và khu công nghiệp được nhúng vào prompt để LLM có ngữ cảnh. Danh mục này **không** tự sửa transcript; normalizer mới là bước thay chữ trước khi gửi Ollama.

**Giới hạn:** regex chỉ bao phủ các biến thể đã viết trong file, không xác minh audio thực sự nói tên công ty nào. Thay thế sai sẽ đi tiếp vào summary và reason code. Nếu không nghe chắc tên công ty, người review cần đối chiếu audio.

- [ ] Đã review phần 05.
- **Ghi chú/điểm cần sửa:** …

---

## 06. Ollama, prompt và JSON đầu ra

**Mục đích.** Xác định LLM nhận gì, sinh gì và code xử lý output sai ra sao.

**Đầu vào:** transcript đã chuẩn hóa, tên ứng viên, thời lượng nếu đọc được, thời điểm phân tích theo múi giờ Việt Nam. [analysis_prompt.py](../../backend/app/classification/analysis_prompt.py) chứa định nghĩa reason code, quy tắc phân vai và summary; [system_prompt.py](../../backend/app/classification/system_prompt.py) đặt các ràng buộc chung.

**Các bước trong [llm.py](../../backend/app/classification/llm.py):**

1. Dựng prompt với ngày hiện tại, ngày mai/ngày kia và các mốc thứ Hai theo giờ Việt Nam, danh sách công ty/KCN, transcript nguyên mạch. Không có bước tách speaker cố định.
2. Gọi Ollama qua OpenAI-compatible /v1/chat/completions với model từ OLLAMA_MODEL_NAME, temperature=0, max_tokens=1100.
3. Yêu cầu response_format json_schema với các trường: summary, reason_code, appointment_date, follow_up_days, candidate_evidence, refusal_basis, summary_needs_review, summary_review_reason.
4. Nếu Ollama từ chối JSON schema bằng lỗi định dạng được nhận biết, thử JSON mode rồi prompt JSON thuần. Parser cũng bóc JSON khỏi code fence/text thừa khi cần.
5. Nếu JSON không có reason_code hoặc lỗi kết nối, raise LLMProcessingError. Trong script batch lỗi được ghi để retry; trong service task chuyển trạng thái failed.
6. Không hỗ trợ phân loại Sales qua analyze_audio: context_type khác hr bị từ chối. Các schema Sales còn trong repo không tạo ra một luồng Sales đang hoạt động tại endpoint này.

**Đầu ra:** AnalysisResult sau khi code kiểm tra reason code, tính group/action và kiểm tra ngày. Các trường chỉ phục vụ guard/trace như candidate_evidence và summary_needs_review không nằm trong AnalysisResult gửi webhook.

**Lưu ý ngày:** ngày tương đối trong transcript cũ được tính từ **ngày chạy phân tích trên server**, vì request không mang ngày ghi âm. Khi xử lý lại recording lịch sử, ngày suy ra có thể lệch ngày cuộc gọi thực.

- [ ] Đã review phần 06.
- **Ghi chú/điểm cần sửa:** …

---

## 07. Reason code, status group và guard

**Mục đích.** Thấy được một nhãn AI được chốt theo những lớp nào, thay vì coi output LLM là kết luận cuối.

**Nguồn chuẩn:** [codes.py](../../backend/app/classification/codes.py). Nhóm và action do Python suy ra từ reason code; model không được tự định nghĩa nhóm mới.

| Nhóm | Reason code được phép | Action |
|---|---|---|
| 1 | TU_CHOI_LUON, KNM_DAP_MAY, SAI_SO_NHAM_SO | NO_CALL |
| 2 | KHACH_BAN, CUOC_GOI_RONG, LOI_AM_THANH | CALL_BACK |
| 3 | TRAO_DOI_THEM, HEN_XA | FOLLOW_UP |
| 4 | HEN_PHONG_VAN | SCHEDULED |
| 5 | DI_LAM | SUCCESS |

**Cách chốt trong [llm.py](../../backend/app/classification/llm.py):**

- Nếu LLM trả TU_CHOI_LUON, guard kiểm tra câu candidate_evidence có trong transcript, nghĩa từ chối có nhắm vào việc làm/ngừng liên hệ không, summary có ý định tích cực hay mốc tiếp tục, và có lời sau đó đổi ý không.
- Nếu LLM trả DI_LAM, guard kiểm tra câu bằng chứng, dấu hiệu cam kết có điều kiện và sự mâu thuẫn với summary.
- Khi guard nghi ngờ, LLM được hỏi lại **một lần**. Từ chối vẫn không đủ bằng chứng thì hệ thống tạm chuyển TRAO_DOI_THEM và đánh dấu cần review trong trace. DI_LAM vẫn không đủ căn cứ sau lần hai thì raise ClassificationNeedsReview, không ghi dòng AI thành công ở batch.
- KNM_DAP_MAY bị chặn nếu không biết thời lượng hoặc audio dài từ 15 giây trở lên.
- SUY_NGHI_THEM và CHO_GIAY_TO từ output cũ được quy đổi thành TRAO_DOI_THEM. DANG_DI_LAM và CHUA_CHOT_NGAY không còn là mã hợp lệ.

**Giới hạn:** transcript không có speaker label tin cậy. Guard kiểm tra câu nói tồn tại trong transcript, nhưng với transcript chép liền, việc chứng minh câu đó thực sự do ứng viên nói vẫn cần người nghe audio. Regex guard chỉ bao phủ các câu diễn đạt được lập trình.

**Đầu ra:** một reason_code, status_group và call_decision trong AnalysisResult. Xem [labeling-guideline.md](labeling-guideline.md) để review các ca ranh giới.

- [ ] Đã review phần 07.
- **Ghi chú/điểm cần sửa:** …

---

## 08. Summary, appointment_date và tín hiệu cần nghe lại

**Mục đích.** Hiểu nội dung HR thực sự nhận được, và khi nào cần người nghe kiểm tra.

**Summary.** Prompt yêu cầu thường 3–5 câu, có thể 6–8 câu khi cuộc gọi có nhiều dữ kiện: hồ sơ/công việc cũ của ứng viên, nhà máy/khu muốn đến, hợp đồng và chế độ đã trao đổi, điều kiện đáp ứng/giấy tờ, thái độ và kế hoạch tiếp theo. Thông tin phải có trong transcript và đúng người nói. recommended_message đã bỏ khỏi AnalysisResult; cột legacy trong model DB còn tồn tại nhưng luồng mới không điền.

**Ngày phỏng vấn.** appointment_date chỉ chứa YYYY-MM-DD khi reason_code là HEN_PHONG_VAN và hai bên đã xác nhận ngày; không rõ ngày thì null. Với các mã khác, validator buộc null. Ngày bắt đầu đi làm, nếu được nói rõ, nằm trong summary chứ không phải appointment_date.

**Hẹn xa.** follow_up_days chỉ có hiệu lực cho HEN_XA; nếu model trả null, code mặc định 7 ngày. Khoảng hợp lệ trong llm.py là 1–365 ngày.

**Review.** Model có thể đặt summary_needs_review và summary_review_reason. Script batch ghi tín hiệu này vào decision trace và error log. Trong service, các trường review không được đưa vào AnalysisResult/webhook; HR nhận summary nhưng không có một cờ review riêng trong payload hiện tại.

**Hai ca mốc đã từng được người dùng hiệu chỉnh:** 18522754.wav là DI_LAM; 18571597.wav là HEN_PHONG_VAN với appointment_date=null. Đây là ca tham chiếu, không thay cho đánh giá trên toàn bộ dữ liệu.

**Prompt Gemini:** [ground-truth-labeling-guide.md](ground-truth-labeling-guide.md) dùng để tóm tắt audio cho người gán nhãn tham khảo trước khi tự chọn reason code.

- [ ] Đã review phần 08.
- **Ghi chú/điểm cần sửa:** …

---

## 09. Rule engine và PostgreSQL

**Mục đích.** Theo dõi dữ liệu từ lúc nhận request tới khi có lịch follow-up.

**Khởi tạo:** [database.py](../../backend/app/core/database.py) tạo SQLAlchemy async engine/SessionLocal từ DATABASE_URL. Khi FastAPI startup, [main.py](../../backend/app/main.py) chạy Base.metadata.create_all. Bảng được khai báo ở [models.py](../../backend/app/core/models.py).

| Bảng | Dữ liệu chính được code dùng | Khi nào ghi |
|---|---|---|
| call_records | task ID, context HR, contact ID/name, audio URL, transcript, summary, intent, status, lỗi | Tạo lúc background task bắt đầu, cập nhật qua pipeline |
| followup_tasks | call_record_id, scheduled_at, day_offset, channel, status | Rule engine tạo nếu nhóm cần lịch |
| audit_logs | action, decision, details, timestamp | Sau LLM và khi rule engine chạy |

**Trạng thái CallRecord:** pending, processing, completed, failed, webhook_failed. Endpoint tạo record với processing; completed được commit sau LLM, trước webhook. Nếu webhook hết retry thì đổi thành webhook_failed. Nếu STT/LLM/rule engine lỗi thì chuyển failed và thử gửi webhook báo lỗi.

**Lịch từ [rules.py](../../backend/app/followup/rules.py):**

| Nhóm | Quy tắc hiện tại |
|---|---|
| 1 NO_CALL | Không tạo FollowUpTask |
| 2 CALL_BACK | KHACH_BAN: sau 2 giờ; CUOC_GOI_RONG/LOI_AM_THANH: sau 15 phút |
| 3 FOLLOW_UP | TRAO_DOI_THEM: sau 3 ngày; HEN_XA: theo follow_up_days, mặc định 7 ngày |
| 4 SCHEDULED | Có ngày phỏng vấn: nhắc 09:00 giờ Việt Nam ngày trước đó; chưa có ngày: sau 1 ngày |
| 5 SUCCESS | Theo dõi sau 2 ngày |

**Đầu ra:** một FollowUpTask có channel=zalo, message_content=None, status=scheduled khi có lịch. Code này **lên lịch trong DB**, chưa thấy tiến trình đọc task đến hạn để gửi tin nhắn hoặc nhắc HR tự động. Các hàm gửi Zalo/email ở [webhook.py](../../backend/app/integrations/webhook.py) không được gọi từ rule engine.

**Giới hạn lưu trữ:** CallRecord có transcript, summary và intent nhưng không có cột appointment_date hoặc follow_up_days. Ngày phỏng vấn được dùng để tính scheduled_at, có trong audit/webhook payload, nhưng không lưu thành trường riêng trong CallRecord. Rule engine tự tạo AuditLog và analyze.py cũng tạo thêm log RULE_EVALUATION; cần xem có trùng bản ghi log mong muốn không.

- [ ] Đã review phần 09.
- **Ghi chú/điểm cần sửa:** …

---

## 10. Webhook, polling và health

**Mục đích.** Xác định CRM nhận kết quả theo hai cách và biết các trạng thái lỗi.

**Webhook:** [analyze.py](../../backend/app/api/v1/endpoints/analyze.py) gửi task_id, ssn, status và result=AnalysisResult.model_dump(). [integrations/webhook.py](../../backend/app/integrations/webhook.py) ưu tiên CRM_WEBHOOK_URL, nếu trống dùng WEBHOOK_URL; POST JSON bằng httpx, retry theo WEBHOOK_MAX_RETRIES với backoff tăng dần. Khi thất bại, CallRecord chuyển webhook_failed; kết quả AI vẫn đã lưu trong DB ở mức các cột hiện có. Khi pipeline lỗi, gửi payload status=failed và error.

**Polling:** GET **/api/v1/tasks/{task_id}** trong [tasks.py](../../backend/app/api/v1/endpoints/tasks.py) đọc CallRecord và trả status, contact_name, summary, intent, error_message, created_at. Không tìm thấy ID thì 404. Response này không gồm transcript, lịch FollowUpTask, appointment_date hoặc toàn bộ AnalysisResult.

**Health:** GET **/api/v1/health** trong [health.py](../../backend/app/api/v1/endpoints/health.py) trả status, uptime_seconds, llm_ready. Hiện [llm.py](../../backend/app/classification/llm.py) có is_ready() luôn trả True; vì vậy health không chứng minh Ollama thật sự kết nối được dù startup đã thử gọi /api/tags.

**Điểm vận hành:** FastAPI BackgroundTasks không phải queue bền vững; cần xem lại hành vi khi process chết giữa chừng nếu đưa vào vận hành số lượng lớn. Không thấy cơ chế gửi lại webhook_failed sau khi CRM phục hồi trong luồng hiện tại.

- [ ] Đã review phần 10.
- **Ghi chú/điểm cần sửa:** …

---

## 11. Lô 713 audio, nhãn người và evaluation

**Mục đích.** Phân biệt nhãn AI tự sinh với ground truth do con người quyết định.

### 11A. Dữ liệu hiện có

Máy local có data/audio.zip chứa **713 WAV với 713 tên file duy nhất**. Các CSV đang thấy trong data/ là các bản thử: ground_truth_review_713_nov09.csv có 7 dòng, bản v6 có 30 dòng, bản v7 có 28 dòng. Những con số này chỉ nói về file local, không phản ánh số dòng CSV trên server. Không đọc được trạng thái server từ checkout này.

[ground_truth_713_labeling.xlsx](../../data/ground_truth_713_labeling.xlsx) liệt kê 713 tên audio. Người gán nhãn chọn Human_Reason_Code từ dropdown, status group/action tự quy đổi và Review Flag đánh dấu ca cần rà. Bộ chấm đọc Excel và CSV AI trực tiếp theo File_Name.

### 11B. Script auto label

[auto_label_ground_truth.py](../../backend/scripts/auto_label_ground_truth.py) mặc định đọc data/recordings_import/audio, yêu cầu 713 WAV nếu dùng đúng thư mục mặc định, ghi data/recordings_import/ground_truth_review_713_merged.csv. Mỗi file đi qua transcribe_audio rồi llm_service.analyze_audio.

CSV có File_Name, transcript, các trường AI và **hai cột Human để trống**. File _decision_trace.jsonl lưu response/guard/fallback theo lượt; _error_log.csv ghi lỗi và ca cần nghe lại. --resume đọc các dòng thành công để bỏ qua, thử lại file chưa có kết quả; dừng sau 5 lỗi hệ thống liên tiếp. Các ca ClassificationNeedsReview không được ghi là dòng AI thành công. Script batch không tạo CallRecord, lịch hoặc webhook. Hướng dẫn vận hành nằm ở [relabel-713.md](relabel-713.md).

### 11C. Người gán nhãn và Gemini

Prompt trong [ground-truth-labeling-guide.md](ground-truth-labeling-guide.md) yêu cầu Gemini nghe audio và viết summary. Người gán nhãn tự quyết định reason code khi nghe/đọc; output Gemini không tự trở thành ground truth. Với ca không rõ người nói, ý định hoặc audio lỗi, cần nghe lại và ghi cờ review.

### 11D. Evaluation và performance

[eval/run_eval.py](../../backend/eval/run_eval.py) hiện chạy worker LLM trên các transcript mẫu trong [samples.json](../../backend/eval/dataset/samples.json) và so reason code/status group với đáp án. Dataset hiện có 12 case mẫu; Llama3.1 judge chấm hallucination/logic theo transcript. Đây là bộ eval mẫu, **chưa phải** kết quả accuracy trên 713 audio có nhãn người.

#### Chấm lô audio từ file có sẵn

Từ thư mục gốc của repo, chạy lệnh dưới đây với bản Excel đã nhận từ nhóm gán nhãn. Nếu đầu vào nhãn người là CSV thì có thể bỏ bước cài `openpyxl`.

```bash
python -m pip install openpyxl
python backend/eval/score_batch.py \
  --human data/ground_truth_713_labeling.xlsx \
  --ai data/recordings_import/ground_truth_review_713_merged.csv \
  --out-dir data/eval/baseline
```

[score_batch.py](../../backend/eval/score_batch.py) ghép theo `File_Name` và báo lỗi nếu trùng tên. Cột nhãn người để trống được đếm là chưa gán nhãn. Script tìm `_decision_trace.jsonl` và `_error_log.csv` cạnh CSV AI. Dùng `--trace` hoặc `--error-log` nếu hai file nằm ở chỗ khác.

- `metrics.json` ghi coverage trên tập có nhãn người và ghi accuracy trên các ca có cả nhãn người lẫn kết quả AI hợp lệ. Macro F1 lấy trung bình các mã xuất hiện ở nhãn người hoặc AI trong tập chấm. Precision hoặc recall thiếu mẫu có giá trị `null`.
- `incorrect_no_call` đếm ca AI gán `NO_CALL` khi nhãn người có action khác. Số ca do `TU_CHOI_LUON` được tách riêng. Khi coverage chưa đủ, đọc tỷ lệ trên các ca đã chấm cùng số ca còn thiếu.
- `review` báo số ca có cờ nghe lại và số ca chưa biết trạng thái review. Khi có trace, bộ chấm dùng kết quả cuối của từng file. Ca có output hợp lệ và cờ review vẫn được chấm, đồng thời xuất hiện trong danh sách cần xem.
- `reason_confusion.csv` và `action_confusion.csv` có hàng là nhãn người, cột là nhãn AI. Action người được quy đổi từ reason code. Nếu CSV có `AI_Call_Decision`, script chấm action đó và đánh dấu khi nó lệch bảng quy đổi.
- `cases_to_review.csv` ghi tên file, hai nhãn, hai action và lý do cần xem. Dùng tên file để đối chiếu audio, transcript và trace khi bạn phân tích nguyên nhân.

Có thể chạy với nhãn từng phần. Nếu chưa có cặp nhãn hợp lệ, bảng đếm vẫn có kết quả và điểm để `null`. Dùng cùng bản nhãn người và cùng tập audio khi so các model.

#### Thử 20 request đồng thời

Chạy trên instance test dùng DB và webhook test. Tạo `data/loadtest_audio_urls.txt` chứa 20 URL audio mà FastAPI tải được, mỗi dòng một URL.

```bash
python backend/scripts/load_test.py --url http://localhost:18000 \
  --audio-urls data/loadtest_audio_urls.txt --count 20 --poll
```

Chạy một lượt với `--count 1` để kiểm tra đường đi trước. Ghi số request được nhận, số task lỗi hoặc timeout, thời gian hoàn tất lô và số callback thực nhận theo `task_id`. Script polling có thể thấy `completed` trước lúc gửi webhook, vì vậy dùng log của webhook test để xác nhận giao thành công và đo thời gian đến lúc nhận callback. STT hiện xử lý một tác vụ mỗi lần trong một tiến trình FastAPI. [Script load test](../../backend/scripts/load_test.py) · [Luồng API](../../backend/app/api/v1/endpoints/analyze.py) · [Code STT](../../backend/app/audio/service.py)


- [ ] Đã review phần 11.
- **Ghi chú/điểm cần sửa:** …

---

## 12. Deploy, hiện trạng và checklist kết thúc phiên

**Mục đích.** Nối code với cách chạy trên server và lập danh sách kiểm tra trước khi kết luận dự án đã sẵn sàng tích hợp.

**Chạy service:** từ repo root, cài backend/requirements.txt rồi chạy Uvicorn với --app-dir backend và app.main:app. [followup-agent.service](../../backend/deploy/followup-agent.service) chạy trên port 18000 bằng Conda env datacore; [setup_service.sh](../../backend/deploy/setup_service.sh) copy unit vào systemd và restart. Giá trị trong unit là đường dẫn theo server đã cấu hình, cần kiểm tra trước khi áp dụng ở máy khác.

**Cấu hình cần đối chiếu trên server:** DATABASE_URL, OLLAMA_API_BASE_URL, OLLAMA_MODEL_NAME, PHOWHISPER_MODEL, AUDIO_DOWNLOAD_DIR, MAX_AUDIO_SIZE_MB, CRM_WEBHOOK_URL/WEBHOOK_URL. [.env.example](../../.env.example) là ví dụ, không chứng minh .env thật. Không đưa mật khẩu/token hoặc nội dung audio vào guide.

### Bảng tình trạng để cập nhật trong phiên review

| Hạng mục | Điều đã thấy trong repo/lịch sử | Cần xác minh thêm |
|---|---|---|
| API HR → STT → LLM → DB → webhook | Code đầy đủ; báo cáo cũ đã thử end-to-end | Server có chạy đúng checkout/config hiện tại không |
| PostgreSQL và webhook | Có schema, commit, retry và báo cáo thử thành công | CRM thật đã nhận payload đúng hợp đồng chưa |
| Model STT | Có pipeline Transformers, cấu hình qua PHOWHISPER_MODEL | Model thực tế trên server là PhoWhisper hay Whisper v3 Turbo |
| Nhận audio mới | Endpoint nhận request chứa audio_url | CRM có gửi POST tự động sau khi lưu recording không |
| Lịch follow-up | Có FollowUpTask trong DB | Ai đọc và thực hiện task đến hạn |
| Lô 713 | Local ZIP đủ 713 tên WAV | Server có đủ WAV hợp lệ và CSV xử lý đủ không |
| Ground truth | Có Excel dropdown và prompt Gemini summary | Nhãn Human đã được người nghe xác nhận bao nhiêu file |
| Evaluation thực tế | Có 12 case mẫu và judge | Metrics trên lô 713 chưa có |
| Monitoring/khả năng chịu lỗi | Có health, polling, audit, load-test scripts | Health Ollama, task bị ngắt, webhook retry sau lỗi cần đánh giá |

### Checklist chung trước khi đóng phiên review

- [ ] Đã duyệt đủ 12 phần và cập nhật các ô ghi chú.
- [ ] Biết phiên bản commit, .env và model đang chạy trên server.
- [ ] Xác nhận cách CRM kích hoạt POST và hợp đồng webhook thật.
- [ ] Xác nhận số WAV/CSV/nhãn Human của lô 713 trên server.
- [ ] Liệt kê các ca phân loại sai và đo bằng nhãn người, không bằng nhãn AI.
- [ ] Chốt các việc còn thiếu cho prototype: xử lý task bền vững, cờ review cho HR, thực thi lịch follow-up, kiểm tra health thực, và dữ liệu ngày ghi âm.
- [ ] Chỉ sau khi có dữ liệu đánh giá mới chọn model STT/LLM cuối cùng và mức sẵn sàng tích hợp.

**Quy tắc cập nhật guide:** khi code hoặc taxonomy đổi, sửa phần tương ứng và ghi ngày/commit. Những tài liệu lịch sử trong Reports/ được giữ nguyên theo thời điểm viết; không dùng chúng để thay code hiện hành.
