# -------------------------------------------------------
# app/services/llm_service.py
# Giao tiếp với Local LLM (Load model, truyền input)
# -------------------------------------------------------
import asyncio
import logging
import json
from pathlib import Path
from typing import Optional

# Thư viện llama-cpp-python cho mô hình GGUF cục bộ
try:
    from llama_cpp import Llama
except ImportError:
    # Dự phòng giả lập nếu môi trường dev chưa cài compiled binary
    class Llama:
        def __init__(self, *args, **kwargs): pass
        def __call__(self, *args, **kwargs): return {"choices": [{"text": "{}"}]}

from app.core.config import settings
from app.schemas.response import AnalysisResult
from app.core.exceptions import LLMProcessingError

# Import các mẫu prompt được quản lý tập trung từ thư mục app/prompts/
# Giả định cấu trúc file từ sơ đồ folder trước đó của bạn
try:
    from app.prompts.analysis_prompts import SALES_ANALYSIS_TEMPLATE, HR_ANALYSIS_TEMPLATE
except ImportError:
    # Fallback lại các Prompt Template gốc của bạn nếu chưa kịp tách file
    SALES_ANALYSIS_TEMPLATE = """Bạn là chuyên gia phân tích cuộc gọi bán hàng. Hãy phân tích cuộc hội thoại sau và trả về JSON.
Tên khách hàng: {contact_name}
Nội dung hội thoại:
\"\"\"
{context_data}
\"\"\"
Trả về JSON đúng cấu trúc:
{{"summary": "Tóm tắt ngắn gọn cuộc gọi", "recommended_message": "Tin nhắn follow-up gợi ý"}}"""
    
    HR_ANALYSIS_TEMPLATE = """Bạn là chuyên gia phân tích phỏng vấn tuyển dụng. Hãy phân tích cuộc phỏng vấn sau và trả về JSON.
Tên ứng viên: {contact_name}
Nội dung cuộc phỏng vấn:
\"\"\"
{context_data}
\"\"\"
Trả về JSON đúng cấu trúc:
{{"summary": "Tóm tắt năng lực ứng viên", "recommended_message": "Tin nhắn follow-up gửi ứng viên"}}"""

logger = logging.getLogger(__name__)


class LLMService:
    _instance: Optional["LLMService"] = None
    _model: Optional[Llama] = None

    def __new__(cls, *args, **kwargs):
        """Pattern: Singleton — Đảm bảo chỉ tạo duy nhất 1 instance hệ thống"""
        if not cls._instance:
            cls._instance = super(LLMService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def load_model(self) -> None:
        """Load GGUF model qua llama-cpp-python khi hệ thống startup"""
        if self._model is not None:
            logger.info("Local GGUF Model đã được load từ trước.")
            return

        model_path = settings.LLM_MODEL_PATH
        if not model_path or not Path(model_path).exists():
            logger.error(f"Không tìm thấy file model GGUF tại đường dẫn: {model_path}")
            # Nếu không tìm thấy file GGUF cục bộ, hệ thống sẽ log cảnh báo dữ dội
            return

        try:
            logger.info(f"Đang tiến hành load Local GGUF Model tại: {model_path}")
            # Khởi tạo mô hình cục bộ hỗ trợ tính toán trên CPU/GPU
            self._model = Llama(
                model_path=model_path,
                n_ctx=4096,         # Số lượng token context tối đa
                n_threads=4,        # Điều chỉnh số lượng luồng CPU tuỳ hệ thống
                n_gpu_layers=settings.LLM_GPU_LAYERS,
                verbose=False
            )
            logger.info("Local GGUF Model đã được tải thành công lên bộ nhớ.")
        except Exception as e:
            logger.error(f"Khởi tạo Llama-cpp thất bại: {e}")
            self._model = None

    def is_ready(self) -> bool:
        """Kiểm tra xem model đã sẵn sàng hoạt động hay chưa"""
        return self._model is not None

    def _safe_parse_json(self, text: str) -> dict:
        """Hàm bóc tách phần JSON thuần từ dữ liệu thô sinh ra bởi LLM"""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Bóc tách JSON thất bại: {e}. Đoạn text gốc: {text[:150]}")
            return {}

    async def analyze_audio(self, transcript: str, contact_name: str, context_type: str = "hr") -> AnalysisResult:
        """
        Xử lý phân tích dữ liệu đa phương tiện từ tệp cục bộ hoặc bản dịch thô.
        1. Nhận transcript (văn bản dịch từ âm thanh).
        2. Dựng Prompt Template tùy biến theo loại cấu trúc (Sales hoặc HR).
        3. Đẩy vào xử lý bằng Local GGUF Model.
        4. Trả ra dữ liệu chuẩn hóa dạng AnalysisResult.
        """
        if not self.is_ready():
            raise LLMProcessingError("Hệ thống AI chưa được tải thành công. Vui lòng thử lại sau.")

        try:
            context_data = transcript

            # 2. Lựa chọn Template thích hợp cho từng kịch bản nghiệp vụ
            if context_type == "sales":
                prompt = SALES_ANALYSIS_TEMPLATE.format(contact_name=contact_name, context_data=context_data)
            else:
                prompt = HR_ANALYSIS_TEMPLATE.format(contact_name=contact_name, context_data=context_data)

            logger.info(f"Đang đẩy dữ liệu phân tích ({context_type}) cho: {contact_name}")
            
            # 3. Gửi Prompt vào Local LLM GGUF
            # ❗ Quan trọng: self._model() là hàm đồng bộ (blocking), phải bọc vào to_thread
            # để server không bị "freeze" khi AI đang suy nghĩ
            def _run_llm():
                return self._model(
                    prompt,
                    max_tokens=1024,
                    temperature=0.3,
                    stop=["<\/s>", "</s>"]
                )
            response = await asyncio.to_thread(_run_llm)
            
            raw_text = response["choices"][0]["text"]
            parsed_data = self._safe_parse_json(raw_text)

            # 4. Ép kiểu định dạng và trả về Object Pydantic AnalysisResult chuẩn hóa
            return AnalysisResult(
                summary=parsed_data.get("summary", "Không thể trích xuất phần tóm tắt."),
                recommended_message=parsed_data.get("recommended_message", "Không thể tạo tin nhắn gợi ý.")
            )

        except Exception as e:
            logger.error(f"Xử lý LLM thất bại cho đối tượng {contact_name}: {e}")
            raise LLMProcessingError(f"Quá trình phân tích dữ liệu hội thoại gặp sự cố cục bộ: {e}")


# Tạo duy nhất 1 biến instance sẵn sàng để đăng ký tại app.state khi chạy ứng dụng FastAPI
llm_service = LLMService()