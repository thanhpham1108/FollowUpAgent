# -------------------------------------------------------
# tests/eval/judge.py
# Giao tiếp với Judge LLM (llama3.1 qua Ollama)
# -------------------------------------------------------
# Tái dụng _safe_parse_json của LLMService để bóc JSON
# từ output của Llama3.1 (Llama cũng hay trả kèm text thừa)
# -------------------------------------------------------
import json
import os
import re
import logging
import httpx
from typing import Optional

from tests.eval.prompts import JUDGE_SYSTEM_PROMPT, JUDGE_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# ── Cấu hình Judge Model — đọc từ ENV để linh hoạt trên server test ──────────
# Trên server: export JUDGE_OLLAMA_BASE_URL=http://<server-ip>:11434/v1
# Trên server: export JUDGE_MODEL_NAME=llama3.2  (nếu RAM ít, dùng model nhỏ hơn)
# Fallback về localhost nếu không có ENV (chạy local OK)
OLLAMA_BASE_URL = os.getenv("JUDGE_OLLAMA_BASE_URL", os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434/v1"))
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "llama3.1")


def _safe_parse_json(text: str) -> dict:
    """
    Bóc tách JSON thuần từ output của LLM.
    Tái dụng logic từ LLMService._safe_parse_json để xử lý nhất quán.
    """
    text = text.strip()

    # Bước 1: Loại bỏ markdown code block nếu có
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()

    # Bước 2: Thử parse thẳng
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Bước 3: Dùng regex bóc cục JSON đầu tiên
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            logger.warning(f"[Judge] Bóc tách JSON bằng regex thất bại: {e}")

    logger.error(f"[Judge] Không thể parse JSON từ response. 200 ký tự đầu: {text[:200]}")
    return {}


class LLMJudge:
    """
    Gọi llama3.1 qua Ollama để chấm điểm kết quả của Qwen2.5.
    Trả về JudgeScore gồm hallucination_score, logic_score, critique.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model_name: str = JUDGE_MODEL_NAME,
        timeout: float = 180.0,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout

    def check_availability(self) -> bool:
        """Kiểm tra xem Ollama có đang chạy và có model judge không."""
        try:
            resp = httpx.get(
                f"{self.base_url.replace('/v1', '')}/api/tags", timeout=5.0
            )
            if resp.status_code != 200:
                return False
            available_models = [m["name"] for m in resp.json().get("models", [])]
            is_available = any(self.model_name in m for m in available_models)
            if not is_available:
                logger.error(
                    f"[Judge] Model '{self.model_name}' chưa được pull về Ollama. "
                    f"Chạy: ollama pull {self.model_name}"
                )
            return is_available
        except Exception as e:
            logger.error(f"[Judge] Không kết nối được Ollama: {e}")
            return False

    def evaluate(
        self,
        transcript: str,
        ai_output: dict,
    ) -> Optional[dict]:
        """
        Chấm điểm 1 sample.

        Args:
            transcript: Đoạn hội thoại gốc.
            ai_output: Output JSON dict của Qwen2.5 (AnalysisResult.model_dump()).

        Returns:
            dict với keys: hallucination_score, logic_score, critique
            hoặc None nếu Judge lỗi.
        """
        user_prompt = JUDGE_USER_PROMPT_TEMPLATE.format(
            transcript=transcript,
            ai_output=json.dumps(ai_output, ensure_ascii=False, indent=2),
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 800,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions", json=payload
                )
                response.raise_for_status()
                raw_text = response.json()["choices"][0]["message"]["content"]

            parsed = _safe_parse_json(raw_text)
            if not parsed:
                logger.error(f"[Judge] Không parse được response. Raw: {raw_text[:300]}")
                return None

            # Validate các trường bắt buộc
            required_keys = {"hallucination_score", "logic_score", "critique"}
            if not required_keys.issubset(parsed.keys()):
                logger.error(f"[Judge] Thiếu trường trong response: {parsed}")
                return None

            return {
                "hallucination_score": int(parsed["hallucination_score"]),
                "logic_score": int(parsed["logic_score"]),
                "critique": str(parsed["critique"]),
            }

        except httpx.RequestError as e:
            logger.error(f"[Judge] Lỗi kết nối Ollama: {e}")
            return None
        except Exception as e:
            logger.error(f"[Judge] Lỗi không xác định: {e}")
            return None


# Singleton
llm_judge = LLMJudge()
