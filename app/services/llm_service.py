# -------------------------------------------------------
# app/services/llm_service.py
# Giao tiếp với Local LLM (Ollama API) thay vì file GGUF
# -------------------------------------------------------
import logging
import json
import httpx
from typing import Optional

from app.core.config import settings
from app.schemas.response import AnalysisResult
from app.core.exceptions import LLMProcessingError

try:
    from app.prompts.analysis_prompts import SALES_ANALYSIS_TEMPLATE, HR_ANALYSIS_TEMPLATE
    from app.prompts.system_prompts import SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = "Bạn là chuyên viên phân tích cuộc gọi. Chỉ trả về JSON thuần."
    # Fallback lại các Prompt Template gốc của bạn nếu chưa kịp tách file
    SALES_ANALYSIS_TEMPLATE = """Bạn là chuyên gia phân tích cuộc gọi bán hàng/tư vấn. Hãy phân tích cuộc hội thoại sau và phân loại khách hàng vào 1 trong 5 nhóm.
Nhóm 1: Chưa tư vấn
Nhóm 2: Cần gọi lại (Lý do: KNM_1, KNM_4, SUY_NGHI_THEM, KHACH_BAN)
Nhóm 3: UV Tiềm năng (Lý do: CHUA_CHOT_NGAY, CHO_CCCD, HEN_XA)
Nhóm 4: Hẹn phỏng vấn (Lý do: HEN_PHONG_VAN)
Nhóm 5: Đi làm tạm tính (Lý do: DI_LAM)

Tên khách hàng: {contact_name}
Nội dung hội thoại:
\"\"\"
{context_data}
\"\"\"
Trả về JSON đúng cấu trúc:
{{"summary": "Tóm tắt cuộc gọi", "status_group": 1, "reason_code": "Mã lý do", "appointment_date": null, "recommended_message": "Tin nhắn gợi ý"}}"""
    
    HR_ANALYSIS_TEMPLATE = """Bạn là chuyên gia phân tích cuộc gọi tuyển dụng. Hãy phân tích đoạn hội thoại sau và phân loại ứng viên vào 1 trong 5 nhóm.
Nhóm 1: Chưa tư vấn
Nhóm 2: Cần gọi lại (Lý do: KNM_1, KNM_4, SUY_NGHI_THEM, KHACH_BAN)
Nhóm 3: UV Tiềm năng (Lý do: CHUA_CHOT_NGAY, CHO_CCCD, HEN_XA)
Nhóm 4: Hẹn phỏng vấn (Lý do: HEN_PHONG_VAN)
Nhóm 5: Đi làm tạm tính (Lý do: DI_LAM)

Tên ứng viên: {contact_name}
Nội dung cuộc gọi:
\"\"\"
{context_data}
\"\"\"
Trả về JSON đúng cấu trúc:
{{"summary": "Tóm tắt cuộc gọi", "status_group": 1, "reason_code": "Mã lý do", "appointment_date": null, "recommended_message": "Tin nhắn gợi ý"}}"""

logger = logging.getLogger(__name__)


class LLMService:
    _instance: Optional["LLMService"] = None

    def __new__(cls, *args, **kwargs):
        """Pattern: Singleton — Đảm bảo chỉ tạo duy nhất 1 instance hệ thống"""
        if not cls._instance:
            cls._instance = super(LLMService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def load_model(self) -> None:
        """Kiểm tra kết nối tới Ollama khi hệ thống startup"""
        logger.info(f"Đang kiểm tra kết nối tới Ollama tại: {settings.OLLAMA_API_BASE_URL}")
        try:
            # Lấy status từ Ollama
            response = httpx.get(f"{settings.OLLAMA_API_BASE_URL.replace('/v1', '')}/api/tags", timeout=5.0)
            if response.status_code == 200:
                logger.info(f"Kết nối Ollama thành công. Các model có sẵn: {[m['name'] for m in response.json().get('models', [])]}")
            else:
                logger.warning(f"Ollama phản hồi mã lỗi {response.status_code}")
        except Exception as e:
            logger.error(f"Không thể kết nối tới Ollama API: {e}. Vui lòng đảm bảo Ollama đang chạy ở cổng 11434.")

    def is_ready(self) -> bool:
        """Luôn trả về True vì Ollama chạy độc lập"""
        return True

    def _safe_parse_json(self, text: str) -> dict:
        """
        Hàm bóc tách phần JSON thuần từ dữ liệu thô sinh ra bởi LLM.
        Xử lý được các trường hợp:
        - JSON thuần
        - JSON bọc trong ```json ... ```
        - JSON lẫn lộn với 'thinking' block hoặc text thừa trước/sau
        """
        import re
        text = text.strip()

        # Bước 1: Loại bỏ markdown code block nếu có
        if "```" in text:
            # Lấy phần trong block ```json ... ``` hoặc ``` ... ```
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                text = match.group(1).strip()

        # Bước 2: Thử parse thẳng (trường hợp đơn giản nhất)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Bước 3: Dùng regex để bóc cục JSON đầu tiên trong đống text thừa
        # (Xử lý trường hợp Qwen trả về 'thinking' block nằm trước JSON)
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"Bóc tách JSON bằng regex thất bại: {e}. Text gốc (150 ký tự đầu): {text[:150]}")

        logger.error(f"Không thể bóc tách JSON từ response của LLM. Text gốc: {text[:300]}")
        return {}

    async def analyze_audio(self, transcript: str, contact_name: str, context_type: str = "hr") -> AnalysisResult:
        """
        Xử lý phân tích dữ liệu bằng cách gửi HTTP Request tới Ollama
        """
        try:
            context_data = transcript

            # Lựa chọn Template
            if context_type == "sales":
                prompt = SALES_ANALYSIS_TEMPLATE.format(contact_name=contact_name, context_data=context_data)
            else:
                prompt = HR_ANALYSIS_TEMPLATE.format(contact_name=contact_name, context_data=context_data)

            logger.info(f"Đang đẩy dữ liệu phân tích ({context_type}) cho: {contact_name} qua Ollama...")
            
            # Tạo payload chuẩn OpenAI API compatible cho Ollama — dùng system prompt V2
            payload = {
                "model": settings.OLLAMA_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,  # Tối thiểu sáng tạo — JSON phải chuẩn xác
                "max_tokens": 1500   # Tăng lên để có đủ chỗ cho chain-of-thought
            }

            # Gửi HTTP Request bất đồng bộ
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_API_BASE_URL}/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            # Lấy kết quả từ Ollama và loại bỏ trường 'thinking' trước khi ép kiểu
            raw_text = data["choices"][0]["message"]["content"]
            parsed_data = self._safe_parse_json(raw_text)
            parsed_data.pop("thinking", None)  # Loại bỏ chain-of-thought khỏi kết quả cuối

            # Ép kiểu định dạng và trả về Object Pydantic AnalysisResult chuẩn hóa
            return AnalysisResult(
                summary=parsed_data.get("summary", "Không thể trích xuất phần tóm tắt."),
                status_group=int(parsed_data.get("status_group", 1)),
                reason_code=str(parsed_data.get("reason_code", "UNKNOWN")),
                appointment_date=parsed_data.get("appointment_date"),
                recommended_message=parsed_data.get("recommended_message", "Không thể tạo tin nhắn gợi ý.")
            )

        except httpx.RequestError as e:
            logger.error(f"Lỗi kết nối tới Ollama: {e}")
            raise LLMProcessingError(f"Không thể kết nối tới Ollama API: {e}")
        except Exception as e:
            logger.error(f"Xử lý LLM thất bại cho đối tượng {contact_name}: {e}")
            raise LLMProcessingError(f"Quá trình phân tích dữ liệu hội thoại gặp sự cố cục bộ: {e}")


# Tạo duy nhất 1 biến instance sẵn sàng để đăng ký tại app.state khi chạy ứng dụng FastAPI
llm_service = LLMService()