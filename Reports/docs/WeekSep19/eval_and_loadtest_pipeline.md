# Báo Cáo Tuần — Tuần 19/09/2026
**Dự án:** FollowUpAgent (Datacore)
**Nhánh:** `main`
**Commits tuần này:** `673c976` → `eb977a7` → `2a1ac44`

---

## Tổng quan nhanh

Tuần này hoàn thiện 2 nhóm công việc chính:
1. **Hoàn thiện tính năng sản phẩm:** Thêm API Polling và Webhook Retry Handling.
2. **Xây dựng hạ tầng kiểm thử:** Evaluation Pipeline (LLM-as-a-Judge) + Load Testing (Locust).

---

## NHÓM 1: Hoàn thiện Tính năng Sản phẩm

### 1.1 — API Polling Trạng thái Task (commit `673c976`)

**Vấn đề trước đó:**
CRM bắn Webhook vào hệ thống và nhận về ngay lập tức `202 Accepted` + `task_id`. Tuy nhiên, CRM không có cách nào biết task đó đang chạy đến đâu (đang xử lý STT? đang gọi LLM? đã xong chưa?) nếu không có Webhook callback.

**Giải pháp:**
Thêm endpoint `GET /api/v1/tasks/{task_id}` cho phép CRM chủ động kiểm tra trạng thái bất cứ lúc nào (API Polling).

**Files thay đổi:**

| File | Việc làm |
|---|---|
| `app/api/v1/endpoints/tasks.py` | **[Mới]** Endpoint polling. Query DB theo `task_id`, trả về object `TaskStatusResponse` |
| `app/api/v1/api_router.py` | Mount router `tasks` vào hệ thống với prefix `/tasks` |
| `app/schemas/response.py` | **[Mới]** Schema `TaskStatusResponse` với 8 fields |
| `app/core/models.py` | Thêm giá trị `WEBHOOK_FAILED` vào enum `CallStatus` |

**Các trạng thái Task có thể trả về:**
```
processing    → Pipeline đang xử lý (STT đang chạy / LLM đang phân tích)
completed     → Hoàn thành, kết quả đã gửi về CRM qua Webhook
failed        → Pipeline xử lý gặp lỗi kỹ thuật
webhook_failed→ Phân tích xong nhưng CRM từ chối nhận Webhook (sau 3 lần retry)
```

### 1.2 — Webhook Retry Handling (commit `673c976`)

**Vấn đề trước đó:**
Khi Webhook gửi về CRM thất bại (network timeout, CRM server down), hệ thống im lặng, không ghi nhận, và task vẫn bị đánh dấu `COMPLETED` mặc dù CRM chưa nhận được kết quả thực sự.

**Giải pháp:**
- `notify_crm_hr_webhook()` trong `webhook_service.py` đã có cơ chế retry 3 lần.
- `analyze.py` được cập nhật để kiểm tra return value (`True/False`) của hàm này.
- Nếu sau 3 lần retry vẫn fail → ghi trạng thái DB thành `WEBHOOK_FAILED` thay vì `COMPLETED`.
- **Giá trị thực tế:** Khi CRM query polling vào `/tasks/{task_id}`, sẽ nhìn thấy trạng thái `webhook_failed` và biết cần xử lý thủ công.

---

## NHÓM 2: Hạ tầng Kiểm thử

### 2.1 — Evaluation Pipeline: LLM-as-a-Judge (commit `2a1ac44`)

**Vấn đề:**
Làm sao biết Qwen2.5 đang phân tích chính xác hay đang "ảo giác" (bịa thông tin không có trong Transcript)? Không thể dùng Rule-based (regex) vì output là ngôn ngữ tự nhiên. Không thể để chính Qwen2.5 tự chấm điểm mình (self-enhancement bias — nó sẽ tự đẩy số lên).

**Giải pháp: LLM-as-a-Judge với 2 lớp đánh giá độc lập**

**Lớp 1 — Deterministic (Exact Match):**
So sánh `status_group` và `reason_code` trả về với Ground Truth trong `dataset/samples.json`. Tính % chính xác tuyệt đối.

**Lớp 2 — Judge (Ngữ nghĩa):**
Một model khác hoàn toàn (**Llama3.1** — khác họ với Qwen) đọc Transcript gốc và kết quả JSON của Qwen2.5, chấm điểm 2 tiêu chí:
- `hallucination_score` (1-5): Có bịa thông tin không có trong Transcript không?
- `logic_score` (1-5): Việc gán nhóm & reason_code có hợp lý không?

Đặc điểm quan trọng: Prompt bắt buộc Judge phải viết `critique` (lý luận bằng chứng từ Transcript) **trước** khi cho điểm, tránh lazy scoring.

**Files đã tạo:**
```
tests/eval/
├── dataset/samples.json   # 8 ca test bao phủ đủ 5 nhóm và các reason_code thực tế
├── prompts.py             # Judge Prompt Template với Chain-of-Thought bắt buộc
├── judge.py               # Class LLMJudge gọi Llama3.1 qua Ollama API
└── run_eval.py            # Script chính: chạy 8 ca, in bảng console, lưu JSON report
```

**Cách chạy:**
```bash
python -m tests.eval.run_eval
```

**Output mẫu:**
```
Status Group Accuracy : 7/8 (87.5%)
Reason Code Accuracy  : 6/8 (75.0%)
Avg Hallucination Score : 4.75/5.00  🟢
Avg Logic Score         : 4.25/5.00  🟢
```

**Thiết kế để chạy trên Server Test:**
- `JUDGE_OLLAMA_BASE_URL` và `JUDGE_MODEL_NAME` đọc từ biến môi trường → dễ override trên server.

### 2.2 — Load Testing: Locust (commit `2a1ac44`)

**Vấn đề:**
Hệ thống chỉ mới được test thủ công bằng 1 cURL duy nhất. Chưa biết khi 20–50 CRM request bắn vào cùng lúc thì hệ thống có bị crash, queue bị tràn, hoặc DB query chậm không.

**Giải pháp:** Dùng Locust — framework load testing Python — giả lập nhiều users đồng thời.

**Kịch bản test được thiết kế:**

| Task | Tỷ trọng | Mục tiêu đo |
|---|---|---|
| Happy Path (`POST /analyze` đúng payload) | 70% | API response time khi nhận request |
| Bad Data (thiếu `audio_url`) | 20% | Tốc độ validation (kỳ vọng 422) |
| Health Check (`GET /health`) | 10% | Uptime & overhead |
| Polling (`GET /tasks/{id}`) | 20% | Hiệu năng DB query dưới tải |

**Thiết kế để chạy trên Server Test:**
- `LOCUST_AUDIO_URL` đọc từ ENV → server không ra internet vẫn test được bằng file nội bộ.
- Hỗ trợ mode `--headless` cho server không có GUI.

```bash
# Có UI
locust -f tests/load_test/locustfile.py --host http://localhost:18000

# Headless (server)
locust -f tests/load_test/locustfile.py --host http://localhost:18000 --headless -u 20 -r 2 -t 60s
```

---

## NHÓM 3: Tài liệu & Cấu trúc Dự án

### 3.1 — Phân tách Dev Dependencies

Tạo `requirements-dev.txt` mới chứa `locust`, `pytest`, `pytest-asyncio`. Không nhét vào `requirements.txt` production để server chính không phải cài đồ test.

### 3.2 — Cập nhật Setup Guide

[`complete_setup_guide.md`](file:///Users/macos/Desktop/BK/URA/Datacore/Reports/docs/WeekAugust30/complete_setup_guide.md) được thêm 3 phần mới:
- **Phần 10:** Hướng dẫn cài + chạy Evaluation Pipeline từng bước
- **Phần 11:** Hướng dẫn cài + chạy Load Test (có UI và headless)
- **Phần 12:** Troubleshooting các lỗi hay gặp khi eval & load test

### 3.3 — Cập nhật `.env.example`

Thêm 3 biến ENV mới được document rõ ràng:
```
JUDGE_OLLAMA_BASE_URL=http://localhost:11434/v1
JUDGE_MODEL_NAME=llama3.1
LOCUST_AUDIO_URL=
```

---

## Tóm tắt các file thay đổi trong tuần

| File | Loại | Mô tả |
|---|---|---|
| `app/api/v1/endpoints/tasks.py` | 🆕 Mới | API Polling endpoint |
| `app/api/v1/api_router.py` | ✏️ Sửa | Mount tasks router |
| `app/api/v1/endpoints/analyze.py` | ✏️ Sửa | Xử lý webhook_failed |
| `app/core/models.py` | ✏️ Sửa | Thêm enum `WEBHOOK_FAILED` |
| `app/schemas/response.py` | ✏️ Sửa | Thêm `TaskStatusResponse` |
| `tests/eval/__init__.py` | 🆕 Mới | Package marker |
| `tests/eval/dataset/samples.json` | 🆕 Mới | 8 Ground Truth samples |
| `tests/eval/prompts.py` | 🆕 Mới | Judge Prompt Templates |
| `tests/eval/judge.py` | 🆕 Mới | LLMJudge class |
| `tests/eval/run_eval.py` | 🆕 Mới | Script chạy eval pipeline |
| `tests/load_test/__init__.py` | 🆕 Mới | Package marker |
| `tests/load_test/locustfile.py` | 🆕 Mới | Locust load test scenarios |
| `requirements-dev.txt` | 🆕 Mới | Dev/Test dependencies |
| `.env.example` | ✏️ Sửa | Thêm Judge & Locust ENV vars |
| `complete_setup_guide.md` | ✏️ Sửa | Thêm Phần 10, 11, 12 |

---

## Trạng thái & Bước tiếp theo

**Tuần này đã hoàn thành ✅:**
- Toàn bộ pipeline chức năng (CRM → STT → LLM → DB → Webhook) đã ổn định.
- Cơ chế Retry & trạng thái `WEBHOOK_FAILED` đã được xử lý.
- Eval Pipeline và Load Test đã sẵn sàng chạy trên server.

**Cần làm sau khi push lên Server Test:**
1. Pull Llama3.1 về Ollama server: `ollama pull llama3.1`
2. Cài dev deps: `pip install -r requirements-dev.txt`
3. Chạy Eval: `python -m tests.eval.run_eval` → xem % chính xác thực tế của Qwen2.5
4. Chạy Load Test: `locust ... --headless -u 20 -r 2 -t 60s` → đo response time và failure rate
5. Dựa vào kết quả Eval để quyết định có cần tinh chỉnh Prompt trong `app/prompts/` không.
