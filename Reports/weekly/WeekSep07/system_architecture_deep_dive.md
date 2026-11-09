# Giải Phẫu Toàn Hệ Thống FollowUpAgent — Cấp Độ Từng Dòng Code

> Tài liệu này giải thích **từng file một** trong dự án, kèm code thực tế và lý do tại sao code được viết như vậy.
> Đây là tài liệu học ngược (Reverse Engineering) từ code → hiểu nguyên lý.

---

## Mục Lục

1. [Sơ Đồ Kiến Trúc Tổng Quan](#0-so-do)
2. [app/main.py — Cổng Vào Hệ Thống](#1-mainpy)
3. [app/core/config.py — Bộ Não Cấu Hình](#2-configpy)
4. [app/core/database.py — Kết Nối Database](#3-databasepy)
5. [app/core/models.py — Bản Thiết Kế Database](#4-modelspy)
6. [app/core/exceptions.py — Hệ Thống Xử Lý Lỗi](#5-exceptionspy)
7. [app/schemas/request.py — Cổng Kiểm Tra Dữ Liệu Đầu Vào](#6-requestpy)
8. [app/schemas/response.py — Khuôn Đúc Dữ Liệu Đầu Ra](#7-responsepy)
9. [app/api/v1/api_router.py — Bảng Điều Hướng](#8-api_routerpy)
10. [app/api/v1/endpoints/analyze.py — Bộ Điều Phối Chính](#9-analyzepy)
11. [app/api/v1/endpoints/tasks.py — API Tra Cứu Trạng Thái](#10-taskspy)
12. [app/api/v1/endpoints/health.py — Kiểm Tra Sức Khoẻ](#11-healthpy)
13. [app/services/audio_service.py — Tai Nghe + Phiên Dịch](#12-audio_servicepy)
14. [app/services/llm_service.py — Bộ Não Phân Tích AI](#13-llm_servicepy)
15. [app/services/webhook_service.py — Người Đưa Thư](#14-webhook_servicepy)
16. [app/services/rule_engine.py — Bộ Luật Nghiệp Vụ](#15-rule_enginepy)
17. [app/prompts/ — Kịch Bản Giao Tiếp AI](#16-prompts)
18. [app/utils/logger.py — Hệ Thống Ghi Nhật Ký](#17-loggerpy)
19. [scripts/load_test.py — Công Cụ Test Tải](#18-load_testpy)
20. [Luồng Dữ Liệu Đầy Đủ (End-to-End)](#19-e2e-flow)

---

## 0. Sơ Đồ Kiến Trúc Tổng Quan

```
CRM ──POST──▶ [analyze.py] ──▶ [BackgroundTask] ──▶ [audio_service]──▶ GPU (PhoWhisper)
                                                 │
                                                 ├──▶ [llm_service] ──▶ Ollama (Qwen2.5)
                                                 │
                                                 ├──▶ [rule_engine] ──▶ DB (followup_tasks)
                                                 │
                                                 └──▶ [webhook_service] ──▶ CRM (kết quả)

CRM ──GET───▶ [tasks.py] ──▶ DB (call_records) ──▶ {status, summary,...}
```

**Nguyên tắc kiến trúc:** `main.py` khởi động → Nhận Request → Endpoints xử lý routing → Services xử lý logic → DB lưu trạng thái.

---

## 1. `app/main.py` — Cổng Vào Hệ Thống

**Vai trò:** File đầu tiên chạy khi bật server. Nó "lắp ráp" toàn bộ hệ thống.

```python
app = FastAPI(
    title="FollowUpAgent API",
    description="...",
    version="1.0.0"
)
```
Dòng này tạo ra ứng dụng FastAPI. Tương tự như khai báo "mở nhà hàng". Mọi thứ sau đó đều gắn vào biến `app` này.

```python
register_exception_handlers(app)
```
Đăng ký ngay "bộ lọc lỗi toàn cầu" — nếu bất kỳ chỗ nào trong hệ thống ném ra Exception, hàm này sẽ chặn lại và trả về JSON thay vì trả về trang lỗi Python xấu xí.

```python
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    llm_service.load_model()
```
Đây là "nghi lễ khởi động" — chạy 1 lần duy nhất khi server bật:
- `Base.metadata.create_all` → Tự động tạo tất cả bảng DB nếu chưa có (an toàn, không xóa dữ liệu cũ)
- `llm_service.load_model()` → Kiểm tra xem Ollama đang sống không

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.include_router(api_router, prefix="/api/v1")
```
- `CORSMiddleware` cho phép mọi domain gọi vào API (cần cho môi trường nội bộ)
- `prefix="/api/v1"` → Mọi endpoint đều có tiền tố này. Ví dụ: `/analyze` → `/api/v1/candidates/analyze`

---

## 2. `app/core/config.py` — Bộ Não Cấu Hình

**Vai trò:** Đọc file `.env` và biến thành Object Python dùng được ở mọi nơi.

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://..."
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_RETRY_BACKOFF: float = 1.0
    OLLAMA_API_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL_NAME: str = "qwen2.5:7b-instruct"
    ...
```
`BaseSettings` là ma thuật của Pydantic: Nó tự động tìm biến tương ứng trong file `.env`. Nếu không có thì dùng giá trị default ở trên. Nếu bro thay đổi file `.env` → Hệ thống tự động cập nhật mà không cần sửa code.

```python
settings = Settings()   # Dòng cuối file
```
Tạo 1 instance duy nhất (Singleton). Mọi file khác chỉ cần `from app.core.config import settings` là dùng được ngay. Không ai tạo thêm Settings nữa.

```python
@property
def followup_days(self) -> List[int]:
    return [int(d.strip()) for d in self.FOLLOWUP_SCHEDULE_DAYS.split(",")]
```
`FOLLOWUP_SCHEDULE_DAYS = "1,3,7"` trong .env → Property này tự biến chuỗi đó thành `[1, 3, 7]` để code dùng được.

---

## 3. `app/core/database.py` — Kết Nối Database

**Vai trò:** Khởi tạo "đường ống" kết nối tới PostgreSQL.

```python
engine = create_async_engine(settings.DATABASE_URL, echo=False)
```
`create_async_engine` → Tạo kết nối bất đồng bộ. Quan trọng: Đây là **Async Engine**, không phải Sync. Nếu dùng Sync Engine trong code Async, server sẽ bị treo.

`echo=False` → Tắt chế độ in ra mọi câu SQL. Nếu đặt `echo=True` khi debug sẽ thấy từng câu `INSERT`, `SELECT` chạy qua.

```python
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
```
`SessionLocal` không phải là session — nó là **nhà máy tạo session**. Mỗi lần cần thao tác DB, ta gọi `async with SessionLocal() as db:` để lấy 1 session mới.

- `autocommit=False` → Phải gọi `await db.commit()` thủ công. Không tự động lưu
- `expire_on_commit=False` → Sau khi commit, object vẫn giữ nguyên dữ liệu (không bị xóa sạch)

```python
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```
Hàm này dùng cho **Dependency Injection** của FastAPI. Các endpoint có thể khai báo `db: AsyncSession = Depends(get_db)` để tự động nhận session.

---

## 4. `app/core/models.py` — Bản Thiết Kế Database

**Vai trò:** Định nghĩa cấu trúc bảng trong PostgreSQL bằng Python thay vì viết SQL.

```python
class CallStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    WEBHOOK_FAILED = "webhook_failed"
```
Enum này đóng vai trò "hợp đồng" — chỉ những giá trị này mới được phép gán vào cột `status`. Python sẽ tự ném lỗi nếu ai cố tình gán giá trị khác.

`WEBHOOK_FAILED` là trạng thái đặc biệt: Pipeline AI chạy thành công (kết quả đã lưu DB), nhưng bước gửi về CRM thất bại hoàn toàn sau 3 lần thử.

```python
class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(String, primary_key=True, default=lambda: f"TASK-{uuid.uuid4().hex[:8]}")
    status = Column(Enum(CallStatus), default=CallStatus.PENDING)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    intent = Column(String, nullable=True)
    recommended_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
```
- `id = TASK-xxxxxxxx` → Khóa chính (Primary Key) tự sinh, không dùng số tự tăng mà dùng UUID để không đoán được
- `transcript` → Kết quả sau khi PhoWhisper dịch file âm thanh ra chữ
- `intent` → Mã phân loại từ LLM (Ví dụ: `KNM_1`, `HEN_PHONG_VAN`)
- `nullable=True` → Cho phép rỗng, vì ban đầu khi tạo record thì những trường này chưa có giá trị

```python
followup_tasks = relationship("FollowUpTask", back_populates="call_record", cascade="all, delete-orphan")
audit_logs = relationship("AuditLog", back_populates="call_record", cascade="all, delete-orphan")
```
Quan hệ 1-Nhiều: 1 CallRecord có thể có nhiều FollowUpTask và nhiều AuditLog. `cascade="all, delete-orphan"` → Xóa CallRecord sẽ tự xóa sạch tất cả task và log liên quan.

---

## 5. `app/core/exceptions.py` — Hệ Thống Xử Lý Lỗi

**Vai trò:** Thay vì để lỗi bay ra lung tung, file này định nghĩa các "hộp lỗi" chuẩn hóa.

```python
class AppBaseException(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    def __init__(self, message: str = None):
        self.message = message or "Đã có lỗi xảy ra."
```
Lớp cha cho mọi lỗi nghiệp vụ. Mỗi lỗi con kế thừa và tùy chỉnh `status_code` và `error_code`:

```python
class AudioDownloadError(AppBaseException):
    status_code = 502  # Bad Gateway — lỗi từ server bên ngoài (CRM)
    error_code = "AUDIO_DOWNLOAD_ERROR"

class AudioValidationError(AppBaseException):
    status_code = 422  # Unprocessable Entity — dữ liệu không hợp lệ

class LLMProcessingError(AppBaseException):
    status_code = 500  # Lỗi nội bộ
```

```python
@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message, "path": str(request.url.path)}
    )
```
Handler này là "bộ lọc cuối" — bắt mọi lỗi `AppBaseException` và biến nó thành JSON chuẩn trả về client. CRM nhận được thông báo lỗi rõ ràng thay vì traceback Python.

---

## 6. `app/schemas/request.py` — Cổng Kiểm Tra Dữ Liệu Đầu Vào

**Vai trò:** Định nghĩa "hợp đồng" dữ liệu CRM phải gửi lên. Không cần viết code kiểm tra thủ công.

```python
class CandidateAnalyzeRequest(BaseModel):
    ssn: str = Field(..., description="Số CCCD/CMND")   # ... = bắt buộc
    candidate_name: str = Field(..., description="Tên ứng viên")
    audio_url: HttpUrl = Field(..., description="URL file ghi âm")
```
`HttpUrl` → Pydantic tự động kiểm tra định dạng URL. Nếu CRM gửi `"audio_url": "abc123"` (không phải URL), FastAPI trả về lỗi `422 Unprocessable Entity` ngay lập tức, không cần viết `if not url.startswith("http")`.

Payload CRM phải gửi:
```json
{
  "ssn": "012345678901",
  "candidate_name": "Nguyễn Văn A",
  "audio_url": "http://crm.internal/recordings/abc.wav"
}
```

---

## 7. `app/schemas/response.py` — Khuôn Đúc Dữ Liệu Đầu Ra

**Vai trò:** Định nghĩa JSON trả về cho CRM — bảo đảm format nhất quán.

```python
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str   # "pending | processing | completed | failed | webhook_failed"
    contact_name: Optional[str] = None
    summary: Optional[str] = None
    intent: Optional[str] = None
    recommended_message: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
```
Schema này được dùng cho endpoint `GET /api/v1/tasks/{task_id}`. FastAPI tự động serialize object này thành JSON chuẩn.

---

## 8. `app/api/v1/api_router.py` — Bảng Điều Hướng

**Vai trò:** Gom tất cả router con và quyết định URL prefix.

```python
from app.api.v1.endpoints import analyze, health, tasks

api_router = APIRouter()
api_router.include_router(analyze.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(tasks.router,   prefix="/tasks",      tags=["tasks"])
api_router.include_router(health.router,                        tags=["health"])
```
Kết hợp với `prefix="/api/v1"` trong `main.py`:
- `analyze.router` → tất cả endpoint trong `analyze.py` = `/api/v1/candidates/...`
- `tasks.router` → tất cả endpoint trong `tasks.py` = `/api/v1/tasks/...`

---

## 9. `app/api/v1/endpoints/analyze.py` — Bộ Điều Phối Chính

**Vai trò:** Nhận request, phát task_id, tung ra BackgroundTask và phối hợp toàn bộ pipeline.

### API Entry Point
```python
@router.post("/analyze", response_model=CandidateAnalyzeResponse, status_code=202)
async def analyze_candidate_audio(request: CandidateAnalyzeRequest, background_tasks: BackgroundTasks):
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"
    background_tasks.add_task(process_candidate_audio, task_id=task_id, request=request)
    return CandidateAnalyzeResponse(task_id=task_id, status="processing", message="...")
```
Điều quan trọng nhất ở đây là thứ tự:
1. Tạo `task_id` ngẫu nhiên
2. `add_task()` — ĐĂNG KÝ công việc nặng vào hàng chờ, **chưa chạy ngay**
3. `return` — TRẢ LỜI NGAY cho CRM trong vòng ~50ms
4. Sau khi trả lời xong → FastAPI mới bắt đầu chạy `process_candidate_audio` ở nền

### Hàm Pipeline Ngầm
```python
async def process_candidate_audio(task_id: str, request: CandidateAnalyzeRequest):
    async with SessionLocal() as db:
        try:
            # Bước 1: Tạo record DB với status=PROCESSING
            record = CallRecord(id=task_id, status=CallStatus.PROCESSING, ...)
            db.add(record)
            await db.commit()

            # Bước 2: Tải + Dịch âm thanh
            transcript = await speech_to_text(str(request.audio_url), task_id)

            # Bước 3: Phân tích bằng AI
            analysis_result = await llm_service.analyze_audio(transcript, request.candidate_name, "hr")

            # Bước 4: Cập nhật DB thành COMPLETED
            record.summary = analysis_result.summary
            record.status = CallStatus.COMPLETED
            await db.commit()

            # Bước 5: Chạy Rule Engine để lên lịch Follow-up
            await rule_engine_service.evaluate_rules(call_record=record, analysis=analysis_result, db=db)

            # Bước 6: Gửi kết quả về CRM qua Webhook
            webhook_ok = await notify_crm_hr_webhook(webhook_payload)
            if not webhook_ok:
                record.status = CallStatus.WEBHOOK_FAILED  # Ghi nhận thất bại
                await db.commit()

        except Exception as e:
            record.status = CallStatus.FAILED   # Ghi nhận lỗi pipeline
            record.error_message = str(e)
            await db.commit()
```
Toàn bộ pipeline nằm trong 1 khối `async with SessionLocal() as db:` — đảm bảo 1 session DB duy nhất dùng xuyên suốt. Kết thúc khối `with`, session tự đóng.

---

## 10. `app/api/v1/endpoints/tasks.py` — API Tra Cứu Trạng Thái

**Vai trò:** CRM dùng để polling (hỏi thăm) xem task đã xong chưa.

```python
@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    async with SessionLocal() as db:
        result = await db.execute(select(CallRecord).where(CallRecord.id == task_id))
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy task: {task_id}")

        return TaskStatusResponse(
            task_id=record.id,
            status=record.status.value,   # .value để lấy chuỗi "completed" thay vì Enum object
            summary=record.summary,
            ...
        )
```
`select(CallRecord).where(CallRecord.id == task_id)` → Câu SQL tương đương: `SELECT * FROM call_records WHERE id = 'TASK-xyz'`

`scalar_one_or_none()` → Lấy 1 dòng duy nhất, hoặc `None` nếu không tìm thấy. Không raise lỗi tự động.

---

## 12. `app/services/audio_service.py` — Tai Nghe + Phiên Dịch

**Vai trò:** Tải file âm thanh về máy và dịch ra chữ tiếng Việt.

### Khởi tạo Model (Lazy Loading)
```python
_model = None  # Biến toàn cục, ban đầu rỗng

def get_whisper_model():
    global _model
    if _model is None:    # Chỉ load lần đầu tiên
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        _model = pipeline(
            "automatic-speech-recognition",
            model=settings.PHOWHISPER_MODEL,   # "vinai/PhoWhisper-medium"
            device=device,
            chunk_length_s=30,       # Xử lý audio theo từng đoạn 30 giây
            return_timestamps=True   # Trả kèm timestamp để phân đoạn
        )
    return _model
```
Kỹ thuật **Lazy Loading** — Model nặng (~1.5GB) chỉ nạp lần đầu tiên có người dùng. Từ lần 2 trở đi, trả về `_model` đã có sẵn trong RAM.

### Download Audio — Stream Mode
```python
async with client.stream("GET", audio_url) as response:
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > max_bytes:
        raise AudioValidationError("File quá lớn")

    bytes_downloaded = 0
    with open(dest_file_path, "wb") as f:
        async for chunk in response.aiter_bytes(chunk_size=8192):
            bytes_downloaded += len(chunk)
            if bytes_downloaded > max_bytes:
                dest_file_path.unlink()   # Xóa file đang ghi dở
                raise AudioValidationError("File quá lớn")
            f.write(chunk)
```
Download theo **chunk** (8KB mỗi lần) thay vì tải toàn bộ vào RAM — an toàn khi file audio lớn hàng trăm MB. Kiểm tra giới hạn kích thước từ cả 2 phía: Header `Content-Length` (nếu server CRM cung cấp) và đếm thực tế khi tải.

### Bước Quan Trọng Nhất — asyncio.to_thread
```python
async def speech_to_text(audio_url: str, task_id: str) -> str:
    file_path = await download_audio(audio_url, task_id)
    # ❗ transcribe_audio là hàm đồng bộ (blocking) — chạy trong GPU
    result = await asyncio.to_thread(transcribe_audio, file_path)
    return result["text"]
```
`asyncio.to_thread()` là chìa khóa:
- `transcribe_audio()` gọi GPU để dịch âm thanh, có thể mất 30-60 giây và **blocking** (chiếm hoàn toàn thread đang chạy)
- Nếu gọi trực tiếp trong code async → Server FastAPI bị treo hoàn toàn trong 60 giây đó, không nhận được request nào khác
- `asyncio.to_thread()` → Tạo thread mới riêng biệt để chạy hàm blocking, thread chính của FastAPI vẫn tự do xử lý request khác

---

## 13. `app/services/llm_service.py` — Bộ Não Phân Tích AI

**Vai trò:** Gửi transcript cho Ollama và nhận về kết quả phân loại.

### Pattern Singleton
```python
class LLMService:
    _instance: Optional["LLMService"] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

llm_service = LLMService()  # Tạo 1 instance duy nhất
```
`__new__` chạy trước `__init__`. Lần đầu tạo object → `_instance = None` → tạo mới và lưu vào `_instance`. Lần 2 trở đi → trả về `_instance` cũ. Đảm bảo không bao giờ có 2 LLMService cùng tồn tại.

### Giao Tiếp Với Ollama
```python
payload = {
    "model": "qwen2.5:7b-instruct",
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt}  # prompt = bảng phân loại + ví dụ + transcript
    ],
    "temperature": 0.0,  # Ép AI không được "sáng tạo", phải tuân thủ JSON
    "max_tokens": 1500   # Đủ chỗ cho thinking block + JSON output
}

async with httpx.AsyncClient(timeout=300.0) as client:
    response = await client.post(
        f"{settings.OLLAMA_API_BASE_URL}/chat/completions",  # http://localhost:11434/v1/chat/completions
        json=payload
    )
    raw_text = response.json()["choices"][0]["message"]["content"]
```
Đây là giao tiếp chuẩn **OpenAI API format**. Ollama "nhái" lại giao thức của OpenAI nên code giao tiếp với Ollama giống hệt với ChatGPT API.

`timeout=300.0` → Lần đầu tiên gọi, Ollama cần nạp model 7B lên VRAM (~90 giây). Nếu timeout nhỏ hơn, request sẽ bị cắt giữa chừng.

### Hàm "Bóc Tách JSON" Từ AI
```python
def _safe_parse_json(self, text: str) -> dict:
    # Bước 1: Bỏ markdown code block nếu có (```json ... ```)
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()

    # Bước 2: Thử parse thẳng
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Bước 3: Dùng regex tìm cục JSON đầu tiên (xử lý khi có <think>...</think> trước)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
```
Qwen2.5 là model "reasoning" — trước khi trả JSON, nó thường "suy nghĩ to" và sinh ra đoạn text như `Okay, let me analyze...` hoặc `<think>...</think>`. Hàm này dùng 3 lớp regex để "xé rào", bỏ qua mọi thứ thừa và chỉ giữ lại phần JSON thực sự.

---

## 14. `app/services/webhook_service.py` — Người Đưa Thư

**Vai trò:** Gửi kết quả phân tích ngược về CRM, tự động thử lại nếu thất bại.

### Exponential Backoff Logic
```python
async def deliver_webhook(payload, target_url: str) -> bool:
    max_retries = settings.WEBHOOK_MAX_RETRIES  # Mặc định: 3
    base_backoff = settings.WEBHOOK_RETRY_BACKOFF  # Mặc định: 1.0 giây

    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(1, max_retries + 1):
            try:
                response = await client.post(target_url, json=json_data)
                response.raise_for_status()  # Ném lỗi nếu HTTP 4xx/5xx
                return True   # Thành công → thoát ngay

            except Exception as e:
                if attempt < max_retries:
                    sleep_time = base_backoff * (2 ** (attempt - 1))
                    # Lần 1 thất bại → chờ 1s × 2^0 = 1 giây
                    # Lần 2 thất bại → chờ 1s × 2^1 = 2 giây
                    # Lần 3 thất bại → hết lượt, bỏ cuộc
                    await asyncio.sleep(sleep_time)

    return False  # Hết 3 lần vẫn thất bại
```
Công thức `base_backoff * (2 ** (attempt - 1))` là chuẩn **Exponential Backoff**: Mỗi lần thất bại, thời gian chờ tăng gấp đôi. Tránh spam liên tục vào CRM khi CRM đang bị quá tải.

### Routing Theo Nghiệp Vụ
```python
async def notify_crm_hr_webhook(payload: dict) -> bool:
    url = settings.CRM_WEBHOOK_URL or settings.WEBHOOK_URL  # Ưu tiên URL chuyên biệt, fallback về URL chung
    return await deliver_webhook(payload=payload, target_url=url)
```
Wrapper đơn giản để code `analyze.py` không cần quan tâm đến URL cụ thể nào.

---

## 15. `app/services/rule_engine.py` — Bộ Luật Nghiệp Vụ

**Vai trò:** Đọc kết quả phân tích của AI → Tự động lên lịch nhắc nhở theo nghiệp vụ HR.

```python
if status_group == 1:
    scheduled_at = now + timedelta(minutes=10)    # Nhóm 1: Gọi lại sau 10 phút
elif status_group == 2:
    if reason_code in ["KNM_1", "KNM_2", "KNM_3"]:
        scheduled_at = now + timedelta(days=1)    # Không nghe máy → gọi lại sau 1 ngày
    else:
        scheduled_at = now + timedelta(days=3)    # Bận/cần suy nghĩ → gọi lại sau 3 ngày
elif status_group == 4:
    appt_date = datetime.strptime(analysis.appointment_date, "%Y-%m-%d")
    scheduled_at = appt_date - timedelta(days=1)  # Nhóm 4: Nhắc 1 ngày trước lịch hẹn
```

Sau khi tính `scheduled_at`, ghi vào bảng `followup_tasks`:
```python
task = FollowUpTask(
    call_record_id=call_record.id,
    scheduled_at=scheduled_at,
    channel="zalo",
    message_content=analysis.recommended_message,  # Tin nhắn AI đã soạn sẵn
    status=FollowUpStatus.SCHEDULED,
)
db.add(task)
await db.commit()
```

---

## 16. `app/prompts/` — Kịch Bản Giao Tiếp AI

### `system_prompts.py` — Vai Trò Của AI
```python
SYSTEM_PROMPT = """
Bạn là một hệ thống AI phân tích cuộc gọi chuyên nghiệp.

## Nguyên tắc bất biến:
1. Chỉ trả về JSON thuần — không có text nào bên ngoài JSON
2. Luôn dùng tiếng Việt cho các trường text
3. Không bịa đặt — chỉ kết luận dựa trên nội dung thực tế
4. reason_code phải khớp chính xác với danh sách hợp lệ
"""
```
`system_prompt` là "thân phận" của AI — nó nhận vai như diễn viên. Câu lệnh này gửi ở đầu mỗi request, trước khi nội dung cuộc gọi.

### `analysis_prompts.py` — Cấu Trúc Prompt 3 Lớp
Template được ghép từ 3 phần:
```python
HR_ANALYSIS_TEMPLATE = f"""
{_STATUS_DEFINITIONS}   # Bảng phân loại 5 nhóm + mã lý do

{_OUTPUT_SCHEMA}        # Định dạng JSON cần trả về

{_HR_FEW_SHOT_EXAMPLES} # 3 ví dụ mẫu để AI học theo

---
## Nhiệm vụ thực tế:
Tên ứng viên: {contact_name}
Nội dung cuộc gọi:
\"\"\"
{context_data}
\"\"\"
JSON output:
"""
```
**Few-Shot Prompting** là kỹ thuật cốt lõi: Thay vì chỉ ra lệnh cho AI, ta đưa ví dụ cụ thể để nó "bắt chước". 3 ví dụ mẫu trong prompt giúp AI hiểu đúng format cần trả về và giảm đáng kể tỷ lệ output sai cấu trúc.

---

## 17. `app/utils/logger.py` — Hệ Thống Ghi Nhật Ký

**Vai trò:** Cấu hình log một lần cho toàn hệ thống — in ra màn hình AND ghi vào file.

```python
_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
# Output: [2026-09-07 21:00:00] [INFO] [app.services.llm_service] Đang phân tích...
```

```python
file_handler = RotatingFileHandler(
    "logs/followup_agent.log",
    maxBytes=10 * 1024 * 1024,  # 10MB mỗi file
    backupCount=5                # Giữ lại 5 file cũ nhất
)
```
`RotatingFileHandler` → Khi file log đầy 10MB, tự động tạo file mới và đổi tên file cũ thành `.log.1`, `.log.2`... Không bao giờ để log ăn hết ổ cứng.

```python
def get_logger(name: str) -> logging.Logger:
    _configure_root_logger()   # Chỉ cấu hình 1 lần (flag _configured)
    return logging.getLogger(name)
```
Mỗi file trong project gọi `logger = get_logger(__name__)`. `__name__` là tên module Python đầy đủ, ví dụ `app.services.llm_service` → Log có thể trace được nguồn gốc từng dòng.

---

## 18. `scripts/load_test.py` — Công Cụ Test Tải

**Vai trò:** Bắn nhiều request đồng thời để kiểm tra hệ thống xử lý song song.

```python
async def main():
    # Tạo danh sách coroutine (công việc)
    tasks = [
        send_request(client, api_url, audio_url, i+1)
        for i in range(count)  # count = 5 hoặc 10
    ]

    # asyncio.gather() = chạy TẤT CẢ task CÙNG LÚC
    results = await asyncio.gather(*tasks)
```
`asyncio.gather()` là chìa khóa: Nó không chạy lần lượt mà phóng tất cả request cùng một lúc. Hệ thống phải tiếp nhận đồng loạt → cho thấy được FastAPI `BackgroundTasks` có thực sự xử lý song song không.

```bash
# Sử dụng:
python scripts/load_test.py --url http://localhost:18000 --audio-url http://host/test.wav --count 5 --poll
```
Flag `--poll`: Sau khi gửi xong → tự động hỏi thăm từng `task_id` mỗi 5 giây cho đến khi tất cả `completed`.

---

## 19. Luồng Dữ Liệu Đầy Đủ End-to-End

Đây là hành trình của 1 request từ khi CRM gửi đến khi nhận kết quả:

```
[CRM]
  │ POST /api/v1/candidates/analyze
  │ {"ssn": "123", "candidate_name": "A", "audio_url": "http://crm/audio.wav"}
  ▼
[FastAPI — analyze.py]
  │ Pydantic validate CandidateAnalyzeRequest
  │ task_id = "TASK-a1b2c3d4"
  │ BackgroundTasks.add_task(process_candidate_audio, ...)
  │ RETURN 202 Accepted {"task_id": "TASK-a1b2c3d4", "status": "processing"}
  ▼
[CRM nhận được 202, đi về, muốn biết kết quả thì gọi GET /tasks/TASK-a1b2c3d4]

[Chạy ngầm — process_candidate_audio]
  │
  ├─ DB: INSERT call_records (id=TASK-a1b2c3d4, status=PROCESSING)
  │
  ├─ audio_service.download_audio()
  │   ├─ httpx.stream GET "http://crm/audio.wav"
  │   ├─ Kiểm tra size (header + thực tế)
  │   └─ Ghi ./data/TASK-a1b2c3d4_audio.wav
  │
  ├─ asyncio.to_thread(transcribe_audio, file_path)
  │   └─ PhoWhisper pipeline trên GPU cuda:0
  │      → transcript = "Chào bạn, mình đang gọi về vị trí..."
  │
  ├─ DB: UPDATE call_records SET transcript=...
  │
  ├─ llm_service.analyze_audio(transcript, "A", "hr")
  │   ├─ Build prompt = _STATUS_DEFINITIONS + _OUTPUT_SCHEMA + _FEW_SHOTS + transcript
  │   ├─ POST http://localhost:11434/v1/chat/completions
  │   │   body: {model: qwen2.5, messages: [...], temperature: 0.0}
  │   ├─ Ollama trả về: {"thinking": "...", "summary": "...", "status_group": 3, ...}
  │   └─ _safe_parse_json() bóc JSON thuần từ response
  │
  ├─ DB: UPDATE call_records SET status=COMPLETED, summary=..., intent=HEN_XA
  │
  ├─ AuditLog: INSERT (action=LLM_ANALYSIS, decision=status_group=3, reason=HEN_XA)
  │
  ├─ rule_engine.evaluate_rules()
  │   ├─ status_group=3 → scheduled_at = now + 3 days
  │   ├─ DB: INSERT followup_tasks (scheduled_at=..., channel=zalo, message_content=...)
  │   └─ DB: INSERT audit_logs (action=RULE_EVALUATION)
  │
  └─ webhook_service.notify_crm_hr_webhook()
      ├─ Lần 1: POST http://crm/webhook/hr → thành công → DB không thay đổi
      │  (Nếu thất bại → chờ 1s → Lần 2 → chờ 2s → Lần 3)
      │  (Nếu vẫn thất bại → DB: UPDATE status=WEBHOOK_FAILED)
      └─ [END]
```

---

*Tài liệu được tạo ngày 07/09/2026. Phiên bản code: commit 673c976.*
