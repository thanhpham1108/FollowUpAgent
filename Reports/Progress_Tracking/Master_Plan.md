# Kế hoạch Tổng thể & Tiến độ Dự án

*Cập nhật lần cuối: 08/06/2026*

## Phase 1: Foundation & Integration
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Define data flow | 31/03 - 14/04 | ✅ Hoàn thành | |
| Quyết định Rule Engine tách database (Supabase) | 15/04 - 28/04 | ✅ Hoàn thành | |
| Chốt kiến trúc: FastAPI + LangChain | 15/04 - 28/04 | ✅ Hoàn thành | |
| Thống nhất API Contract (JSON I/O) | Tuần 5-6 | ✅ Hoàn thành | File `FollowUpAgent_API_contract.json` |
| Khởi tạo repo + Docker + base FastAPI | Tuần 5-6 | ✅ Hoàn thành | Cấu trúc thư mục chuẩn |
| Tạo Webhook endpoint nhận audio | Tuần 5-6 | ✅ Hoàn thành | Đã hoàn thành Endpoint `/analyze` |
| Mock pipeline | Tuần 5-6 | ⏳ Đang thực hiện | BackgroundTask hiện đang mock bằng hàm sleep |
| Kết nối thử CRM | Tuần 5-6 | ❌ Chưa bắt đầu | Cần gọi thử từ CRM thật |

## Phase 2: AI Pipeline Core
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Tích hợp Whisper | Tuần 7-8 | ❌ Chưa bắt đầu | Chuyển Audio -> Text |
| Gọi LLM | Tuần 7-8 | ❌ Chưa bắt đầu | LangChain tích hợp |
| Viết System Prompt V1 (JSON) | Tuần 7-8 | ❌ Chưa bắt đầu | |
| Handle lỗi JSON | Tuần 7-8 | ❌ Chưa bắt đầu | |
| Logging toàn bộ output vào Supabase | Tuần 7-8 | ❌ Chưa bắt đầu | |

## Phase 3: Rule Engine & Intelligence Layer
| Task | Thời gian dự kiến | Trạng thái | Ghi chú |
|---|---|---|---|
| Kết nối DB Rule (D + 1, D + 3, D + 7) | Tuần 9-10 | ❌ Chưa bắt đầu | |
| Map Intent -> Rule | Tuần 9-10 | ❌ Chưa bắt đầu | |
| Query DB để quyết định ngày hẹn | Tuần 11-12 | ❌ Chưa bắt đầu | |
| Tạo Audit Log (AI decision tracking) | Tuần 11-12 | ❌ Chưa bắt đầu | |

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
