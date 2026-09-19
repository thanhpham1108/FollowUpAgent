# Bug Log — FollowUpAgent (Ngày 30/08/2026)

Tài liệu ghi lại tất cả lỗi gặp phải trong quá trình triển khai và cách khắc phục.

---

## BUG #1 — Apache chặn cổng 8080
**Triệu chứng:** Gọi `curl http://localhost:8080/api/...` nhận về trang HTML `301 Moved Permanently` của Apache thay vì JSON của FastAPI.

**Nguyên nhân:** Trên server `poc-ood-2`, Apache đang lắng nghe cổng 8080 và điều hướng toàn bộ traffic sang domain ngoài. FastAPI cũng đang cố bind vào cổng này → xung đột.

**Fix:** Đổi cổng chạy FastAPI sang `18000` (cổng tự do, không bị chiếm):
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 18000
```

---

## BUG #2 — File audio 404 Not Found khi tải
**Triệu chứng:** Log báo `Không thể tải file, CRM phản hồi mã lỗi: 404`.

**Nguyên nhân:** Lệnh `python -m http.server 8001` được chạy ở sai thư mục (không phải `/home/thanhpnc/datacore/FollowUpAgent`), nên server không tìm thấy file `.wav`.

**Fix:** Bắt buộc phải `cd` vào đúng thư mục chứa file audio trước khi bật file server:
```bash
cd /home/thanhpnc/datacore/FollowUpAgent
python -m http.server 8001
```

---

## BUG #3 — LLM trả về JSON có `"thinking"` block gây lỗi parse
**Triệu chứng:** Log báo `Xử lý LLM thất bại` với thông báo liên quan đến `thinking`.

**Nguyên nhân:** Model Qwen2.5 được thiết kế để trả về **Chain-of-Thought (CoT)** — tức là nó tự suy luận trước trong một thẻ `<think>...</think>` hay một khối text rời, rồi mới ra kết quả JSON. Code cũ chỉ làm `json.loads()` thẳng → fail.

**Fix:** Viết lại hàm `_safe_parse_json()` trong `app/services/llm_service.py` với regex để bóc tách cục JSON đầu tiên ra khỏi đống text thừa:
```python
match = re.search(r"\{[\s\S]*\}", text)
if match:
    return json.loads(match.group(0))
```

---

## BUG #4 — `KeyError: '\n  "thinking"'` trong bước tạo prompt
**Triệu chứng:** Traceback chỉ rõ lỗi tại `analysis_prompts.py`, dòng `.format(...)`.

**Nguyên nhân (thực sự):** File `analysis_prompts.py` sử dụng f-string (`f"""..."""`) để nhúng các biến `_OUTPUT_SCHEMA`, `_HR_FEW_SHOT_EXAMPLES`. Trong các string này có chứa JSON mẫu với dấu `{` và `}`. Python xử lý 2 tầng: tầng 1 f-string "ăn" hết `{{` `}}`, tầng 2 `.format()` lại gặp `{thinking}` không có trong args → `KeyError`.

**Fix:** Escape toàn bộ dấu ngoặc nhọn literal trong `_OUTPUT_SCHEMA`, `_HR_FEW_SHOT_EXAMPLES`, `_SALES_FEW_SHOT_EXAMPLES` thành `{{` và `}}`:
```python
# Trước
{"thinking": "...", "summary": "..."}
# Sau
{{"thinking": "...", "summary": "..."}}
```
**File sửa:** `app/prompts/analysis_prompts.py`

---

## BUG #5 — Ollama timeout khi cold start (lần chạy đầu tiên)
**Triệu chứng:** Log Ollama báo `llama-server started in 88.46 seconds` nhưng FastAPI trả lỗi `Lỗi kết nối tới Ollama` sau đúng 2 phút (`120s`).

**Nguyên nhân:** Ollama cần ~90 giây để nạp model `Qwen2.5 7B Q4` từ ổ đĩa lên VRAM của GPU NVIDIA L4 (lần đầu tiên khi model chưa có trong cache). Code cũ chỉ đợi tối đa 120 giây → gần hết timeout khi model vừa xong thì lại không còn thời gian generate.

**Fix:** Tăng timeout của `httpx.AsyncClient` từ `120.0s` lên `300.0s` (5 phút):
```python
# app/services/llm_service.py — dòng 142
async with httpx.AsyncClient(timeout=300.0) as client:
```

---

## Kết quả cuối cùng ✅

Sau khi vá toàn bộ 5 bugs trên, pipeline E2E chạy thành công hoàn toàn:

```
psql> SELECT contact_name, status, intent, summary FROM call_records ORDER BY created_at DESC LIMIT 1;

     contact_name     |  status   | intent  | summary
----------------------+-----------+---------+--------------------------------------------
 Nguyen Van Test OOD3 | COMPLETED | HEN_XA  | Ứng viên đã gửi lời mời và đang chờ kết quả. Có lịch hẹn phỏng vấn vào 02/12.
(1 row)
```
