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
from app.core.classification import GROUP_CALL_DECISION, REASON_CODE_GROUP, ReasonCode
from app.core.exceptions import LLMProcessingError
from app.prompts.analysis_prompts import HR_ANALYSIS_TEMPLATE
from app.prompts.system_prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_ANALYSIS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "status_group": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "reason_code": {"type": "string", "enum": [code.value for code in ReasonCode]},
        "call_decision": {
            "type": "string",
            "enum": list(dict.fromkeys(GROUP_CALL_DECISION.values())),
        },
        "appointment_date": {"type": ["string", "null"]},
        "recommended_message": {"type": "string"},
        "thinking": {"type": "string"},
    },
    "required": [
        "summary",
        "status_group",
        "reason_code",
        "call_decision",
        "appointment_date",
        "recommended_message",
        "thinking",
    ],
    "additionalProperties": False,
}


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
        if context_type != "hr":
            raise LLMProcessingError(f"Chưa có bộ reason_code cho context_type={context_type!r}")

        try:
            prompt = HR_ANALYSIS_TEMPLATE.format(contact_name=contact_name, context_data=transcript)

            logger.info(f"Đang đẩy dữ liệu phân tích ({context_type}) cho: {contact_name} qua Ollama...")
            
            # Tạo payload chuẩn OpenAI API compatible cho Ollama — dùng system prompt V2
            payload = {
                "model": settings.OLLAMA_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "recruitment_call_analysis",
                        "strict": True,
                        "schema": _ANALYSIS_OUTPUT_SCHEMA,
                    },
                },
                "temperature": 0.0,  # Tối thiểu sáng tạo -> JSON phải chuẩn xác
                "max_tokens": 1500   # Tăng lên để có đủ chỗ cho chain-of-thought
            }

            # Gửi HTTP Request bất đồng bộ (Tăng timeout lên 300s để phòng hờ Ollama load model lần đầu quá lâu)
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_API_BASE_URL}/chat/completions",
                    json=payload
                )
                if response.status_code in (400, 422) and any(
                    marker in response.text.lower()
                    for marker in ("json_schema", "json schema", "response_format", "response format")
                ):
                    logger.warning("Ollama không hỗ trợ JSON Schema; thử lại bằng JSON mode.")
                    payload.pop("response_format")
                    payload["format"] = "json"
                    response = await client.post(
                        f"{settings.OLLAMA_API_BASE_URL}/chat/completions",
                        json=payload
                    )
                response.raise_for_status()
                data = response.json()
            
            # Lấy kết quả từ Ollama và loại bỏ trường 'thinking' trước khi ép kiểu
            raw_text = data["choices"][0]["message"]["content"]
            parsed_data = self._safe_parse_json(raw_text)
            parsed_data.pop("thinking", None)

            reason_code = ReasonCode(parsed_data["reason_code"])
            status_group = REASON_CODE_GROUP[reason_code]
            call_decision = GROUP_CALL_DECISION[status_group]

            return AnalysisResult(
                summary=parsed_data.get("summary") or "Không có tóm tắt.",
                status_group=status_group,
                reason_code=reason_code,
                call_decision=call_decision,
                appointment_date=parsed_data.get("appointment_date"),
                recommended_message=parsed_data.get("recommended_message") or ""
            )

        except httpx.RequestError as e:
            logger.error(f"Lỗi kết nối tới Ollama: {e}")
            raise LLMProcessingError(f"Không thể kết nối tới Ollama API: {e}")
        except Exception as e:
            import traceback
            logger.error(f"Xử lý LLM thất bại cho đối tượng {contact_name}: {e}")
            logger.error(f"Chi tiết lỗi:\n{traceback.format_exc()}")
            # Log thêm raw_text nếu có thể (dùng biến cục bộ nếu đã được gán)
            try:
                logger.error(f"RAW TEXT từ LLM: {raw_text}")
            except Exception:
                pass
            raise LLMProcessingError(f"Quá trình phân tích dữ liệu hội thoại gặp sự cố cục bộ: {e}")


# Tạo duy nhất 1 biến instance sẵn sàng để đăng ký tại app.state khi chạy ứng dụng FastAPI
llm_service = LLMService()
