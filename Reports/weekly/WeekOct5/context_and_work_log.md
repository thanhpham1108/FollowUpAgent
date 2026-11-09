# Context & Work Log — Tuần Oct 5, 2026

Tài liệu này lưu lại toàn bộ tiến độ, các tinh chỉnh kỹ thuật và bối cảnh dự án để tiếp tục công việc liền mạch ngay cả khi đổi tài khoản chat.

---

## 1. Thông tin Máy chủ & Phần cứng (Server Environment)

- **Máy chủ:** `ood-master` (Cụm HPC / Open OnDemand).
- **GPU:** 2x **NVIDIA Tesla P100 PCIe 16GB** (Kiến trúc Pascal, Compute Capability `sm_60`).
- **Môi trường Conda:** `datacore` (Python 3.10).
- **Thư mục dự án:** `~/datacore/FollowUpAgent` (Local workspace: `/Users/macos/Desktop/BK/URA/Datacore`).

### Các lỗi thư viện đã fix để chạy được GPU P100:
1. **PyTorch rơi về CPU:** PyTorch CUDA 12 mặc định đã bỏ kernel cho `sm_60`.
   - **Đã xử lý:** Cài bản `torch==2.1.2+cu118` và `torchaudio==2.1.2+cu118`.
2. **Xung đột NumPy:** NumPy 2.x bị lỗi với PyTorch 2.1.2.
   - **Đã xử lý:** Khóa `numpy<2` (đang dùng `numpy-1.26.4`).
3. **Transformers và Torchvision:**
   - Đã gỡ `torchvision` (dự án chỉ dùng audio & text, tránh lỗi `register_fake`).
   - Khóa `transformers<4.47` (đang dùng `transformers-4.46.3`).
4. **Ollama nhận GPU P100:**
   - Ollama tự nhận qua runner `cuda_v12` với **15.9 GiB VRAM** (`100% GPU`).

---

## 2. Quy trình Khởi động Hệ thống (3 Tab Terminal)

Mỗi lần restart máy chủ hoặc mở phiên làm việc mới, chạy theo đúng thứ tự:

### Tab 1: Ollama Server
```bash
OLLAMA_KEEP_ALIVE=-1 ollama serve
# Kiểm tra GPU: ollama run qwen2.5:7b-instruct "hi" && ollama ps (phải hiện 100% GPU)
```

### Tab 2: Database & API Server
```bash
conda activate datacore
cd ~/datacore/FollowUpAgent

# 1. Bật Postgres (nếu chưa bật)
pg_ctl -D ~/pgdata -l ~/pgdata/logfile start

# 2. Khởi động API Server
python -m uvicorn app.main:app --host 0.0.0.0 --port 18000
```

### Tab 3: Mock CRM File Server (Phục vụ file âm thanh test)
```bash
conda activate datacore
cd ~/datacore/FollowUpAgent
python -m http.server 8001
```

---

## 3. Thay đổi Mới Nhất về Audio Service & Prompt LLM (06/10/2026)

### Nâng cấp trường `summary` (Hướng 1: Chi tiết 3–5 câu):
- **Vấn đề cũ:** Prompt ban đầu chỉ yêu cầu 1–2 câu khiến tóm tắt trả về CRM quá ngắn, thiếu bối cảnh và lý do ứng viên phản hồi.
- **Đã thay đổi:**
  - Cập nhật [`app/prompts/analysis_prompts.py`](../../../backend/app/classification/analysis_prompt.py): Yêu cầu tóm tắt 3–5 câu tiếng Việt, nêu rõ mục đích/vị trí trao đổi, thông tin ứng viên chia sẻ hoặc vướng mắc, thái độ/phản hồi, và thỏa thuận hoặc kết quả chốt cuối cùng.
  - Nâng cấp toàn bộ **8 ví dụ mẫu Few-shot** sang chuẩn 3–5 câu giàu ngữ cảnh.
  - Đồng bộ yêu cầu JSON schema trong [`app/prompts/system_prompts.py`](../../../backend/app/classification/system_prompt.py).

### Chuẩn hóa lại 5 Nhóm Trạng thái & Thêm trường `call_decision`:
- **Vấn đề cũ:** Nhóm 2 bị ôm đồm lẫn lộn giữa từ chối (`TU_CHOI_LUON`), dập máy (`KNM_DAP_MAY`), bận (`KHACH_BAN`) và tiềm năng (`SUY_NGHI_THEM`), khiến HR không rõ ai cần gọi lại, ai bỏ qua.
- **Đã chuẩn hóa 5 Nhóm 1-1 với Hành động của HR:**
  - **Nhóm 1 (Đóng hồ sơ / Bỏ qua - `call_decision="NO_CALL"`):** `TU_CHOI_LUON`, `KNM_DAP_MAY` (chốt dập máy cũng không gọi lại), `SAI_SO_NHAM_SO`. Rule Engine **không lên lịch gọi**.
  - **Nhóm 2 (Gián đoạn / Cần gọi lại - `call_decision="CALL_BACK"`):** `KHACH_BAN` (hẹn 2h), `CUOC_GOI_RONG`, `LOI_AM_THANH` (hẹn 15p).
  - **Nhóm 3 (Tiềm năng / Chăm sóc - `call_decision="FOLLOW_UP"`):** `SUY_NGHI_THEM`, `CHUA_CHOT_NGAY`, `CHO_GIAY_TO`, `HEN_XA`. Rule Engine nhắc chăm sóc sau 3 ngày.
  - **Nhóm 4 (Đã có lịch phỏng vấn - `call_decision="SCHEDULED"`):** `HEN_PHONG_VAN`. Nhắc trước 1 ngày.
  - **Nhóm 5 (Chốt thành công - `call_decision="SUCCESS"`):** `DI_LAM`. Theo dõi sau 2 ngày.

### Cấu trúc kết quả trả về CRM (Webhook Payload chuẩn mới):
```json
{
  "task_id": "TASK-xxxx",
  "ssn": "079099xxxxxx",
  "status": "completed",
  "result": {
    "summary": "Nhân viên nhân sự liên hệ tư vấn vị trí công nhân cho ứng viên Lê Văn D. Ứng viên bày tỏ băn khoăn khi mức lương cơ bản 5 triệu/tháng thấp hơn so với thu nhập tại nơi làm việc cũ. Ứng viên chưa từ chối ngay mà xin thêm thời gian xem xét và cân nhắc trước khi quyết định.",
    "status_group": 3,
    "reason_code": "SUY_NGHI_THEM",
    "call_decision": "FOLLOW_UP",
    "appointment_date": null,
    "recommended_message": "Chào anh D, em hiểu mong muốn của anh về thu nhập. Bên em còn nhiều khoản phụ cấp hấp dẫn, anh cứ cân nhắc nhé!"
  }
}
```

### Chuẩn hóa tên thương hiệu / KCN (Khắc phục lỗi STT nghe nhầm "vi xịt" -> "Vixech"):
- **Module xử lý:** [`app/utils/text_normalizer.py`](../../../backend/app/audio/normalizer.py).
- **Hậu xử lý STT:** Tự động bắt các mẫu regex phổ biến (`vi xịt`, `vi xéc`, `vi xếch`, `vi sét`, `quang trâu`...) và thay thế thành tên chuẩn (`Vixech`, `Quang Châu`...) ngay sau khi PhoWhisper hoàn tất bóc băng.
- **Tiêm ngữ cảnh vào LLM:** Bổ sung danh sách các nhà máy (Vixech, Foxconn, Luxshare...) và KCN vào [`app/prompts/analysis_prompts.py`](../../../backend/app/classification/analysis_prompt.py) để mô hình tự động sửa lỗi và luôn viết đúng chính tả trong `summary` và `recommended_message`.

---

## 4. Kịch bản Test Đang Thực hiện (Load Test & Multi-requests)

Để kiểm tra hiệu năng khi có nhiều request đồng thời qua GPU P100:
```bash
conda activate datacore
cd ~/datacore/FollowUpAgent

python scripts/load_test.py \
  --url http://localhost:18000 \
  --audio-url http://localhost:8001/22685287.pcm.wav \
  --count 5 \
  --poll
```
Theo dõi GPU bằng lệnh:
```bash
watch -n 1 nvidia-smi
```

---

## 5. Việc Tiếp Theo (Next Steps)

1. Chạy load test song song (5–10 requests) trên P100 để ghi nhận thời gian bóc băng và suy luận trung bình mỗi cuộc gọi.
2. Kiểm tra chất lượng của `summary` mới sinh ra từ file ghi âm thực tế.
3. Đánh nhãn dữ liệu thực tế theo file [`Reports/docs/WeekOct5/labeling_guideline.md`](labeling_guideline.md) để đánh giá độ chính xác (Eval Pipeline).
4. Chuẩn bị hồ sơ bàn giao chính thức theo file [`README.md`](../../README.md) đã viết lại.

---

## 6. Danh sách File Đã Sửa Đổi & Nội dung Chi tiết (Changelog)

| STT | File thay đổi | Loại thay đổi | Nội dung chi tiết |
|:---:|:---|:---:|:---|
| 1 | [`app/schemas/response.py`](../../../backend/app/schemas/response.py) | **Sửa** | Thêm trường `call_decision: str = "NO_CALL"` vào model `AnalysisResult`. |
| 2 | [`app/services/rule_engine.py`](../../../backend/app/followup/rules.py) | **Sửa** | Cập nhật logic tính lịch hẹn theo 5 nhóm chuẩn mới:<br>• Nhóm 1 (`NO_CALL`): Không lên lịch (`scheduled_at = None`).<br>• Nhóm 2 (`CALL_BACK`): Nhắc sau 15p - 2h.<br>• Nhóm 3 (`FOLLOW_UP`): Nhắc Zalo chăm sóc sau 3 ngày.<br>• Nhóm 4 (`SCHEDULED`): Nhắc trước 1 ngày.<br>• Nhóm 5 (`SUCCESS`): Theo dõi sau 2 ngày. |
| 3 | [`app/prompts/analysis_prompts.py`](../../../backend/app/classification/analysis_prompt.py) | **Sửa** | • Nâng cấp yêu cầu `summary` từ 1–2 câu thành đoạn văn 3–5 câu chi tiết.<br>• Bổ sung bảng 5 nhóm chuẩn và trường `call_decision`.<br>• Viết lại toàn bộ 8 kịch bản Few-shot chuẩn 3–5 câu.<br>• Bổ sung danh sách đối tác (Vixech, Foxconn, Luxshare...) và chỉ dẫn tự sửa lỗi chính tả STT. |
| 4 | [`app/prompts/system_prompts.py`](../../../backend/app/classification/system_prompt.py) | **Sửa** | Đồng bộ schema mong đợi của System Prompt (summary 3–5 câu, `call_decision`). |
| 5 | [`app/utils/text_normalizer.py`](../../../backend/app/audio/normalizer.py) | **Tạo mới** | Module xử lý Regex thay thế các từ bị nghe nhầm: `vi xịt`/`vi xéc`/`vi xếch` → `Vixech`, `quang trâu` → `Quang Châu`, v.v. |
| 6 | [`app/services/audio_service.py`](../../../backend/app/audio/service.py) | **Sửa** | Tích hợp hàm `normalize_transcript` vào ngay sau khi PhoWhisper bóc băng xong trong `transcribe_audio`. |
| 7 | [`Reports/docs/WeekOct5/labeling_guideline.md`](labeling_guideline.md) | **Sửa** | Cập nhật bảng tra cứu đánh nhãn theo đúng 5 nhóm nghiệp vụ mới. |
| 8 | [`Reports/docs/WeekOct5/context_and_work_log.md`](context_and_work_log.md) | **Tạo mới** | Tài liệu lưu toàn bộ bối cảnh máy chủ, GPU P100, quy trình chạy và các thay đổi đã thực hiện. |
| 9 | [`data/viec3mien_companies.json`](../../data/viec3mien_companies.json) | **Tạo mới** | Dữ liệu thô 115 doanh nghiệp tuyển dụng cào từ API gateway của Việc 3 Miền. |
| 10 | [`Reports/docs/WeekOct5/viec3mien_companies_catalog.md`](viec3mien_companies_catalog.md) | **Tạo mới** | Bảng danh mục tra cứu 115 đối tác tuyển dụng kèm địa chỉ KCN và tỉnh thành. |
| 11 | [`app/core/companies.py`](../../../backend/app/classification/companies.py) | **Tạo mới** | Module nạp toàn bộ danh sách 110+ đối tác tuyển dụng và 28 KCN trọng điểm, tự động tiêm động vào Prompt của LLM. |
