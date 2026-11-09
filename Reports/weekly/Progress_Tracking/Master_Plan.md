# Kế hoạch Tổng thể & Tiến độ Dự án

*Cập nhật lần cuối: 23/06/2026*

## Phase 1: Foundation & Integration
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Define data flow | 31/03 - 14/04 | ✅ Hoàn thành | |
| Quyết định Rule Engine tách database (Supabase) | 15/04 - 28/04 | ✅ Hoàn thành | |
| Chốt kiến trúc: FastAPI + LangChain | 15/04 - 28/04 | ✅ Hoàn thành | |
| Thống nhất API Contract (JSON I/O) | Tuần 5-6 | ✅ Hoàn thành | File `FollowUpAgent_API_contract.json` |
| Khởi tạo repo + Docker + base FastAPI | Tuần 5-6 | ✅ Hoàn thành | Cấu trúc thư mục chuẩn |
| Tạo Webhook endpoint nhận audio | Tuần 5-6 | ✅ Hoàn thành | Đã hoàn thành Endpoint `/analyze` |
| Mock pipeline | Tuần 5-6 | ✅ Hoàn thành | Pipeline services đã implement thực, thay thế mock sleep |
| Kết nối thử CRM (External API) | Tuần 5-6 | ✅ Hoàn thành | Đã khám phá & test API đối tác tại `192.168.25.175:8002` |

## Phase 2: AI Pipeline Core
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Cấu hình hệ thống (`config.py`, `database.py`) | Tuần 7-8 | ✅ Hoàn thành | Pydantic BaseSettings v2, SQLAlchemy. *Commit 19/06* |
| Thiết kế DB Schema (`models.py`) | Tuần 7-8 | ✅ Hoàn thành | `CallRecord` + `FollowUpTask`, hỗ trợ cả Sales & HR context. *Commit 19/06* |
| Mở rộng API Schemas (`request.py`, `response.py`) | Tuần 7-8 | ✅ Hoàn thành | Tách rõ `SalesCallRequest` và `CandidateAnalyzeRequest`. *Commit 19/06* |
| Tích hợp Whisper STT (`audio_service.py`) | Tuần 7-8 | ✅ Hoàn thành | Pipeline download → STT → cleanup đầy đủ, validation size & format. *Commit 19/06* |
| Tích hợp Local LLM GGUF (`llm_service.py`) | Tuần 7-8 | ✅ Hoàn thành | Singleton, llama-cpp-python, Prompt V1 Sales & HR. *Commit 19/06* |
| Webhook delivery & đa kênh (`webhook_service.py`) | Tuần 7-8 | ✅ Hoàn thành | Exponential backoff retry, Zalo OA, Email. *Commit 19/06* |
| Viết System Prompt V1 (JSON) | Tuần 7-8 | ✅ Hoàn thành | Template Sales & HR tích hợp trong `llm_service.py` |
| Handle lỗi JSON output LLM | Tuần 7-8 | ✅ Hoàn thành | Hàm `_safe_parse_json` trong `llm_service.py` |
| Logging toàn bộ output vào Database | Tuần 7-8 | ⏳ Đang thực hiện | DB schema có sẵn, chưa wire vào pipeline xử lý chính |

## Phase 3: Rule Engine & Intelligence Layer
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Kết nối DB Rule (D + 1, D + 3, D + 7) | Tuần 9-10 | ✅ Hoàn thành | Đã chuyển sang Rule 5 nhóm trạng thái (10 phút, 1 ngày, 2 ngày, 3 ngày) |
| Map Intent -> Rule | Tuần 9-10 | ✅ Hoàn thành | Prompt ép LLM sinh ra `status_group` và `reason_code` cho Rule Engine |
| Query DB để quyết định ngày hẹn | Tuần 11-12 | ✅ Hoàn thành | Rule Engine tự trích xuất `appointment_date` (Nhóm 4) và lập lịch |
| Tạo Audit Log (AI decision tracking) | Tuần 11-12 | ✅ Hoàn thành | Bảng `AuditLog` lưu lại raw JSON và quyết định của AI |

## Phase 4: Agent Workflow hoàn chỉnh
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Xây chain: Input -> Whisper -> LLM -> Rule engine -> output | Tuần 11-12 | ❌ Chưa bắt đầu | |
| Tách module rõ: transcription, intent detection, decision engine | Tuần 13-14 | ❌ Chưa bắt đầu | |
| Refactor code | Tuần 13-14 | ❌ Chưa bắt đầu | |

## Phase 5: Optimization & Hardening
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Exception handling: Timeout API, Audio lỗi, JSON sai format | Tuần 13-14 | ❌ Chưa bắt đầu | |
| Retry mechanism | Tuần 15-16 | ❌ Chưa bắt đầu | |
| Tối ưu latency: async FastAPI, batch processing nếu cần | Tuần 15-16 | ❌ Chưa bắt đầu | |
| Prompt V2 | Tuần 15-16 | ❌ Chưa bắt đầu | |

## Phase 6: Production Readiness
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Dockerize full system | Tuần 17-18 | ❌ Chưa bắt đầu | Đã có bản base |
| Deploy (cloud/VPS) | Tuần 17-18 | ❌ Chưa bắt đầu | |
| Monitoring (Supabase dashboard) | Tuần 17-18 | ❌ Chưa bắt đầu | |
| Test với data thật từ CRM | Tuần 17-18 | ❌ Chưa bắt đầu | |
| Demo cho stakeholder | Tuần 17-18 | ❌ Chưa bắt đầu | |
