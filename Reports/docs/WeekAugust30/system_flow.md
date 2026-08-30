# Tổng Kết Luồng Hoạt Động — FollowUpAgent

## Kiến trúc tổng thể

```
CRM/Caller ──POST──► FastAPI (port 18000) ──► [Background Task]
                                                      │
                          ┌───────────────────────────┤
                          │                           │
                          ▼                           ▼
               [1] Tải audio từ URL           [5] Lưu kết quả
               (httpx → CRM/File Server)      vào PostgreSQL
                          │
                          ▼
               [2] STT: PhoWhisper-medium
               (cuda:0, vinai/PhoWhisper)
                          │
                          ▼
               [3] Xây dựng Prompt
               (few-shot + chain-of-thought)
                          │
                          ▼
               [4] Phân tích LLM: Qwen2.5 7B
               (Ollama API localhost:11434)
                          │
                          ▼
               [5] Bắn Webhook → CRM
               (webhook.site / CRM endpoint)
```

---

## Chi tiết từng bước

### Bước 1 — Nhận Request từ CRM
- **Endpoint:** `POST /api/v1/candidates/analyze`
- **Payload:** `ssn`, `candidate_name`, `audio_url`
- **Phản hồi ngay:** `202 Accepted` + `task_id` (async, không block CRM)
- **Background task** được tạo để xử lý toàn bộ pipeline phía sau.

### Bước 2 — Tải và nhận dạng giọng nói (STT)
- **Service:** `app/services/audio_service.py`
- **Flow:** Tải file audio bằng `httpx.get(audio_url)` → lưu tạm vào `data/` → đưa qua PhoWhisper pipeline
- **Model:** `vinai/PhoWhisper-medium` chạy trên `cuda:0` (GPU NVIDIA L4)
- **Output:** Văn bản transcript tiếng Việt (dạng string)
- Dọn dẹp file tạm sau khi STT hoàn thành.

### Bước 3 — Xây dựng Prompt (Chain-of-Thought)
- **Service:** `app/services/llm_service.py` + `app/prompts/`
- **Template:** `HR_ANALYSIS_TEMPLATE` hoặc `SALES_ANALYSIS_TEMPLATE` tùy `context_type`
- **Cấu trúc prompt:** Bảng phân loại 5 nhóm + Schema JSON output + 3 ví dụ few-shot + transcript thực tế
- **System prompt:** Yêu cầu model chỉ trả về JSON, dùng tiếng Việt

### Bước 4 — Phân tích bằng LLM (Qwen2.5 7B)
- **API:** `POST http://localhost:11434/v1/chat/completions` (OpenAI-compatible)
- **Model:** `qwen2.5:7b-instruct` chạy qua Ollama (GGUF Q4_K_M, 4.36 GiB)
- **Timeout:** 300 giây (phòng hờ cold start lần đầu ~90 giây)
- **Parse output:** Hàm `_safe_parse_json()` dùng regex bóc JSON ra khỏi thinking block
- **Kết quả:** Object `AnalysisResult` gồm: `summary`, `status_group`, `reason_code`, `appointment_date`, `recommended_message`

### Bước 5 — Lưu Database + Bắn Webhook
- **Database:** PostgreSQL (port 5433) → bảng `call_records`
- **Các trường lưu:** `contact_name`, `status=COMPLETED`, `intent` (reason_code), `summary`, `recommended_message`, `appointment_date`
- **Webhook:** `POST` đến `WEBHOOK_URL` (webhook.site hoặc CRM thật) với payload JSON đầy đủ, retry 3 lần nếu thất bại

---

## Cấu hình môi trường (poc-ood-2)

| Thành phần | Cổng | Ghi chú |
|---|---|---|
| FastAPI (Uvicorn) | 18000 | `python -m uvicorn app.main:app --host 0.0.0.0 --port 18000` |
| Ollama | 11434 | `./bin/ollama serve &` |
| PostgreSQL | 5433 | Native, không Docker |
| File Server (test) | 8001 | `python -m http.server 8001` (giả lập CRM) |

## Kết quả nghiệm thu

```
contact_name: Nguyen Van Test OOD3
status:       COMPLETED
intent:       HEN_XA
summary:      Ứng viên đã gửi lời mời và đang chờ kết quả. Có lịch hẹn phỏng vấn vào 02/12.
```
- Webhook bắn thành công: `HTTP 200 OK` ✅
- Dữ liệu lưu PostgreSQL: `status=COMPLETED` ✅
