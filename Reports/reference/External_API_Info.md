# External API Information (Server Local)

**Endpoint Overview** (retrieved from `http://192.168.25.175:8002/openapi.json`)

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/deals/{deal_id}` | Lấy chi tiết Deal theo `deal_id` (schema: `DealData`). |
| GET    | `/deals`           | Lấy danh sách Deal (một mảng `DealData`). |
| POST   | `/llm/recommend`   | Gửi `deal_id` để nhận đề xuất hành động từ LLM (payload: `LLMInput`, response: `LLMResponse`). |
| GET    | `/health`          | Kiểm tra trạng thái dịch vụ. |

**Schema Details**

- **DealData** – chứa đầy đủ thông tin Deal, bao gồm các trường như `deal_id`, `owner_id`, `company_name`, `industry`, `activities` (mảng `Activity`).
- **LLMInput** – chỉ một trường `deal_id` để yêu cầu AI tư vấn.
- **LLMResponse** – `status` + `data` (kiểu `LLMData`).
- **LLMData** – các trường: `deal_id`, `action_type`, `action_title`, `reason`, `priority`, `suggested_content`, `confidence_score`, `reference_deals`.

---

## Vì sao thông tin này không khớp với dự án của chúng ta?

- **Dự án hiện tại** của chúng ta được thiết kế để **nhận dữ liệu ứng viên** (`ssn`, `candidate_name`, `audio_url`) và thực hiện phân tích âm thanh, sau đó trả về đề xuất (summary, recommended_message) qua webhook.
- **API trên server** mà chúng ta vừa khám phá lại hướng tới **quản lý Deal** trong CRM và cung cấp một endpoint LLM để đưa ra *hành động* cho Deal.
- Vì vậy, **cấu trúc dữ liệu, tên trường và mục tiêu nghiệp vụ là khác nhau**.

## Các bước tiếp theo để đồng bộ hoá
1. **Định nghĩa lại API Contract** của chúng ta cho phù hợp với yêu cầu nhận audio của ứng viên (đã có trong `FollowUpAgent_API_contract.json`).
2. **Nếu muốn tích hợp** server trên để lấy đề xuất hành động dựa trên Deal, thì cần một **mapper**:
   - Khi nhận audio, tạo một `deal_id` tương ứng (có thể lưu vào Supabase/Rule Engine).
   - Gọi `POST /llm/recommend` với `deal_id` để nhận đề xuất, sau đó thêm vào payload webhook của chúng ta.
3. **Lưu lại tài liệu** này trong dự án để mọi thành viên có thể tham chiếu.
   - File này đã được tạo ở `Reports/External_API_Info.md`.
4. **Cập nhật README** để mô tả cách gọi API của đối tác và cách chuyển đổi dữ liệu nếu cần.

---

*File này sẽ được sử dụng như một tài liệu tham chiếu nội bộ, giúp nhóm nhớ được các endpoint và schema của server đối tác.*
