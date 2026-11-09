# Prompt, reason code và status group

**Mốc mã nguồn:** nhánh `testing` tại `e659a6a`. Tài liệu này mô tả phân loại cuộc gọi **tuyển dụng HR** đang có trong mã, không định nghĩa nghiệp vụ Sales.

## 1. Vì sao phải sửa

Tài liệu WeekOct5 đã nhận ra 5 nhóm trước đó chưa tương ứng rõ với hành động: từ chối/dập máy bị đặt chung với trường hợp cần gọi lại, còn người cần suy nghĩ thêm bị xếp chưa đúng nhóm chăm sóc. Prompt cũ cũng để LLM tự xuất `reason_code` dạng chuỗi tự do. CSV cũ [`data/ground_truth_review.csv`](../../../data/ground_truth_review.csv) có 8/50 dòng mang mã ngoài danh sách hiện nay, gồm `UNKNOWN`, `THONG_TIN_DAO_TAO`, `XAC_NHAN_DI_LAM`, `THONG_BAO_LUONG` và bốn mã khác. Mã tự sinh làm dữ liệu CRM và đánh giá không nhất quán.

Từ 27/10, [`app/core/classification.py`](../../../backend/app/classification/codes.py) giữ một danh sách enum; prompt, LLM service và Pydantic cùng lấy từ đó. Khi trả kết quả hợp lệ, code Python tính `status_group` và `call_decision` từ `reason_code`. LLM không còn quyền quyết định độc lập ba trường ấy. Nếu reason code lạ, phân tích phát lỗi thay vì âm thầm ghi mã lạ vào CSV.

## 2. Bảng mã hiện hành

| Nhóm | Ý nghĩa | `reason_code` hợp lệ | `call_decision` | Rule follow-up hiện tại |
| --- | --- | --- | --- | --- |
| 1 | Đóng hồ sơ / bỏ qua | `TU_CHOI_LUON`, `KNM_DAP_MAY`, `SAI_SO_NHAM_SO` | `NO_CALL` | Không tạo lịch |
| 2 | Gián đoạn / cần gọi lại | `KHACH_BAN`, `CUOC_GOI_RONG`, `LOI_AM_THANH` | `CALL_BACK` | `KHACH_BAN`: 2 giờ; hai mã còn lại: 15 phút |
| 3 | Tiềm năng / chăm sóc | `SUY_NGHI_THEM`, `CHUA_CHOT_NGAY`, `CHO_GIAY_TO`, `HEN_XA` | `FOLLOW_UP` | 3 ngày |
| 4 | Đã hẹn phỏng vấn | `HEN_PHONG_VAN` | `SCHEDULED` | Trước lịch hẹn 1 ngày; có fallback nếu ngày thiếu/sai |
| 5 | Chốt đi làm | `DI_LAM` | `SUCCESS` | Theo dõi sau 2 ngày |

**Ví dụ ranh giới:** ứng viên dập máy ngay sau lời chào → nhóm 1 `KNM_DAP_MAY`; ứng viên nói “đang lái xe, gọi lại chiều” → nhóm 2 `KHACH_BAN`; ứng viên quan tâm nhưng muốn cân nhắc → nhóm 3 `SUY_NGHI_THEM`; đã chốt ngày giờ phỏng vấn → nhóm 4 `HEN_PHONG_VAN`; đã chốt đi làm → nhóm 5 `DI_LAM`. Chỉ có lịch ngày/giờ rõ mới điền `appointment_date`.

## 3. Prompt đã thay đổi ở đâu

### 06/10: ý nghĩa nghiệp vụ và chất lượng bản tóm tắt

[`app/prompts/analysis_prompts.py`](../../../backend/app/classification/analysis_prompt.py) được viết lại để summary có **3–5 câu**, nêu bối cảnh/vị trí, thông tin hoặc vướng mắc của ứng viên, thái độ và kết quả thỏa thuận. Tám ví dụ few-shot bao phủ dập máy, từ chối, bận, suy nghĩ, chưa chốt ngày, chờ giấy tờ, hẹn phỏng vấn và đi làm. Bảng nhóm gắn trực tiếp với hành động HR. [`app/prompts/system_prompts.py`](../../../backend/app/classification/system_prompt.py) được đồng bộ về JSON và summary. Đây là phần **đã nằm trong WeekOct5**, nêu lại để giải thích nền của bản hiện tại.

### 07/10: đưa bối cảnh tên nhà máy vào prompt

Danh sách doanh nghiệp và KCN từ [`app/core/companies.py`](../../../backend/app/classification/companies.py) được ghép vào prompt HR. Prompt nêu rằng transcript là một đoạn liên tục, không tách người nói; HR thường chào trước, ứng viên thường trả lời ngắn sau đó. Mục đích là giảm nhầm lời HR thành ý định của ứng viên và viết đúng tên nhà máy trong summary/tin nhắn. Runtime hiện tiêm **110 tên doanh nghiệp và 28 KCN**; file JSON nguồn có 115 phần tử. Xem [Tên công ty và STT](companies_and_stt.md).

### 27/10: chặn mã tự tạo và chuẩn hóa ngày hẹn

- Bảng trong prompt được sinh bằng `reason_codes_for_group()` nên luôn dùng mã enum hiện tại.
- System prompt liệt kê cả 12 mã, yêu cầu chọn đúng một mã, không dịch, ghép hoặc tạo mã khác; vẫn yêu cầu chỉ kết luận từ transcript và trả JSON thuần.
- Ví dụ nhóm 4 đổi `appointment_date` từ dạng chữ `NGAY_MAI_9H30` thành ISO `2026-11-15T09:30:00`. [`app/services/rule_engine.py`](../../../backend/app/followup/rules.py) parse ISO, hiểu timestamp không có offset theo giờ Việt Nam rồi đổi sang UTC.
- Template Sales giả dùng chung HR và fallback prompt khi import lỗi đã được bỏ. [`app/services/llm_service.py`](../../../backend/app/classification/llm.py) hiện chủ động từ chối `context_type` khác `hr`.

## 4. Đường đi của một kết quả LLM

1. `transcribe_audio()` lấy chữ từ PhoWhisper và gọi normalizer tên riêng.
2. `analyze_audio()` ghép system prompt với HR template, gửi `/chat/completions` của Ollama với `temperature=0` và `response_format` JSON Schema. Schema có enum 12 mã, 5 nhóm, 5 hành động và các trường summary, ngày hẹn, tin nhắn, thinking.
3. Nếu server trả HTTP 400/422 và nội dung lỗi chứa chuỗi nhận diện schema/format, code thử lại bằng `format: "json"`. Chưa có kết quả kiểm tra tính tương thích trên Ollama/model đang triển khai cho mọi trường hợp lỗi.
4. Python parse JSON, bỏ `thinking`, ép `reason_code` thành `ReasonCode`, suy ra nhóm/hành động từ bảng. [`AnalysisResult`](../../../backend/app/schemas/response.py) xác nhận lần nữa và ghi đè nhóm/hành động theo mã.
5. Nếu code lạ hoặc JSON lỗi, `LLMProcessingError` được ném ra. Script gán nhãn sẽ ghi dòng lỗi; full API pipeline đánh dấu tác vụ lỗi theo xử lý hiện có. Không có bước “tự sửa” mã lạ thành mã gần nhất.

Quy tắc này đảm bảo **tính hợp lệ của mã trên những kết quả thành công**; nó không chứng minh mô hình hiểu đúng cuộc gọi. Chất lượng phải đo với cột Human sau khi nghe audio.

## 5. Số liệu CSV cục bộ và cách đọc

| Tệp review | Số dòng | Mã ngoài 12 mã | `LOI_AM_THANH` | Nhãn Human |
| --- | ---: | ---: | ---: | --- |
| `ground_truth_review.csv` (định dạng cũ) | 50 | 8 | 42 | 0/50 đã điền |
| `ground_truth_review_20261027_063914.csv` | 50 | 0 | 43 | 0/50 đã điền |
| `ground_truth_review_20261027_080357.csv` | 50 | 0 | 44 | 0/50 đã điền |

Hai bản review mới là **hai lần xuất của 50 tên file**, không phải 100 cuộc gọi độc lập. Với các reason code hợp lệ, không phát hiện cặp `AI_Status_Group` lệch bảng ánh xạ. Các dòng `LOI_AM_THANH` trong hai bản mới đều có transcript không rỗng; đó là tín hiệu cần nghe kiểm tra, chưa phải bằng chứng nhãn sai. Chưa thể tính precision/accuracy vì Human chưa được điền.

## 6. Điểm cần rà tiếp khi đọc prompt

- Ví dụ few-shot nhóm 1 `KNM_DAP_MAY` có `call_decision=NO_CALL` nhưng `recommended_message` lại gợi ý gửi Zalo. Rule engine hiện không tạo lịch cho nhóm 1; thông điệp gợi ý vẫn có thể gây hiểu nhầm nếu CRM hiển thị hoặc tự gửi theo trường này.
- `LOI_AM_THANH` rất cao trong hai file review. Cần nghe các mẫu có transcript dài và phân biệt âm thanh lỗi thực với khả năng model chọn nhãn mặc định.
- Yêu cầu summary 3–5 câu là yêu cầu prompt; mã hiện không đếm câu để cưỡng chế. Cần đo trên CSV thực tế.
- Schema có thể bị Ollama từ chối tùy phiên bản/model; fallback chỉ được kích hoạt cho 400/422 có dấu hiệu cụ thể. Cần smoke test trên server.
- Bộ 12 mã chỉ dành cho HR. Schema và webhook Sales cũ còn trong repo nhưng LLM hiện không xử lý `sales`; cần taxonomy riêng nếu mở lại.
