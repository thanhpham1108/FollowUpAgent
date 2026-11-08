# -------------------------------------------------------
# app/services/llm_service.py
# Giao tiếp với Local LLM (Ollama API) thay vì file GGUF
# -------------------------------------------------------
import logging
import json
import re
import unicodedata
import httpx
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.schemas.response import AnalysisResult
from app.core.classification import GROUP_CALL_DECISION, REASON_CODE_GROUP, ReasonCode
from app.core.exceptions import LLMProcessingError
from app.prompts.analysis_prompts import HR_ANALYSIS_TEMPLATE
from app.prompts.system_prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
VIETNAM_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")
_WEEKDAYS_VI = ("thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ Nhật")


class ClassificationNeedsReview(LLMProcessingError):
    """Không đủ bằng chứng để tự động chốt reason code."""


_REFUSAL_PATTERNS = (
    r"\bkhong co nhu cau\b",
    r"\bkhong quan tam\b",
    r"\bkhong muon (?:nhan viec|di lam|lam viec)\b",
    r"\bkhong dong y (?:nhan viec|di lam)\b",
    r"\bkhong (?:nhan viec|di lam|lam viec)\b",
    r"\bthoi (?:khong di|khong lam)\b",
    r"\bdung goi (?:nua|lai)\b",
    r"\btu choi (?:cong viec|loi moi|di lam)\b",
)
_EMPLOYED_PATTERNS = (r"\bdang di lam\b", r"\bdi lam roi\b", r"\bda co viec\b", r"\bdang lam\b")
_DISENGAGED_PATTERNS = (r"\b(?:cup may|ngat may|ket thuc cuoc goi)\b", r"\bkhong muon trao doi tiep\b")
_INTEREST_PATTERNS = (
    r"\b(?:ung vien|anh|chi) hoi (?:ve|them)\b",
    r"\b(?:ung vien|anh|chi) muon tim hieu\b",
    r"\b(?:ung vien|anh|chi) quan tam\b",
    r"\bdong y ket ban\b",
)
_POSITIVE_PATTERNS = (
    r"\bdong y (?:nhan viec|di lam|den lam|den phong van)\b",
    r"\bxac nhan (?:di lam|nhan viec)\b",
    r"\bsan sang (?:di lam|nhan viec)\b",
    r"\bchot (?:lich phong van|ngay di lam|di lam)\b",
    r"\bhen phong van\b",
    r"\bmai (?:anh|em|minh) ra\b",
)


def _plain_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "").casefold().replace("đ", "d")
    letters = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", " ", letters).strip()


def _candidate_quote_is_supported(quote: str, transcript: str) -> bool:
    quote_text = _plain_text(quote).strip()
    if not quote_text:
        return False
    lines = transcript.splitlines()
    labeled = any("Ứng viên:" in line for line in lines)
    source = " ".join(line.split("Ứng viên:", 1)[1] for line in lines if "Ứng viên:" in line) if labeled else transcript
    return quote_text in _plain_text(source)


def _needs_refusal_recheck(parsed: dict, transcript: str) -> bool:
    if parsed.get("reason_code") != ReasonCode.TU_CHOI_LUON.value:
        return False
    summary = _plain_text(parsed.get("summary", ""))
    quote = parsed.get("candidate_evidence") or ""
    quote_text = _plain_text(quote)
    positive_summary = any(
        not re.search(r"\b(?:khong|chua)\s+$", summary[max(0, match.start() - 12):match.start()])
        for pattern in _POSITIVE_PATTERNS
        for match in re.finditer(pattern, summary)
    )
    if positive_summary or not _candidate_quote_is_supported(quote, transcript):
        return True
    if parsed.get("refusal_basis") == "employed_disengaged":
        return (
            not any(re.search(pattern, quote_text) for pattern in _EMPLOYED_PATTERNS)
            or not any(re.search(pattern, summary) for pattern in _DISENGAGED_PATTERNS)
            or any(re.search(pattern, summary) for pattern in _INTEREST_PATTERNS)
        )
    if parsed.get("refusal_basis") == "explicit_job_refusal":
        return not any(re.search(pattern, quote_text) for pattern in _REFUSAL_PATTERNS)
    return True


def _appointment_date(parsed: dict, reason_code: ReasonCode) -> str | None:
    if reason_code != ReasonCode.HEN_PHONG_VAN:
        return None
    value = parsed.get("appointment_date")
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError as exc:
        raise LLMProcessingError(f"appointment_date không hợp lệ: {value!r}") from exc


def _follow_up_days(parsed: dict, reason_code: ReasonCode) -> int | None:
    if reason_code != ReasonCode.HEN_XA:
        return None
    value = parsed.get("follow_up_days")
    if value is None:
        return 7
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 365:
        raise LLMProcessingError(f"follow_up_days không hợp lệ: {value!r}")
    return value

_ANALYSIS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "reason_code": {"type": "string", "enum": [code.value for code in ReasonCode]},
        "appointment_date": {"type": ["string", "null"]},
        "follow_up_days": {"type": ["integer", "null"]},
        "candidate_evidence": {"type": "string"},
        "refusal_basis": {"type": "string", "enum": ["none", "explicit_job_refusal", "employed_disengaged"]},
    },
    "required": [
        "summary",
        "reason_code",
        "appointment_date",
        "follow_up_days",
        "candidate_evidence",
        "refusal_basis",
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

    async def _request_analysis(self, client: httpx.AsyncClient, payload: dict) -> dict:
        endpoint = f"{settings.OLLAMA_API_BASE_URL}/chat/completions"
        response = await client.post(endpoint, json=payload)
        for response_format in ({"type": "json_object"}, None):
            if response.status_code not in (400, 422) or not any(
                marker in response.text.lower()
                for marker in ("json_schema", "json schema", "response_format", "response format")
            ):
                break
            fallback_payload = dict(payload)
            if response_format is None:
                fallback_payload.pop("response_format", None)
                logger.warning("Ollama không hỗ trợ JSON mode; thử lại bằng prompt JSON thuần.")
            else:
                fallback_payload["response_format"] = response_format
                logger.warning("Ollama không hỗ trợ JSON Schema; thử lại bằng JSON mode.")
            response = await client.post(endpoint, json=fallback_payload)
        response.raise_for_status()
        raw_text = response.json()["choices"][0]["message"]["content"]
        return self._safe_parse_json(raw_text)

    async def analyze_audio(
        self,
        transcript: str,
        contact_name: str,
        context_type: str = "hr",
        *,
        reference_datetime: datetime | None = None,
        audio_duration_seconds: float | None = None,
        speaker_mode: str = "mixed",
    ) -> AnalysisResult:
        """
        Xử lý phân tích dữ liệu bằng cách gửi HTTP Request tới Ollama
        """
        if context_type != "hr":
            raise LLMProcessingError(f"Chưa có bộ reason_code cho context_type={context_type!r}")

        try:
            if reference_datetime is not None and reference_datetime.tzinfo is None:
                raise ValueError("reference_datetime phải có múi giờ")
            now_vn = (reference_datetime or datetime.now(VIETNAM_TZ)).astimezone(VIETNAM_TZ)
            today = now_vn.date()
            next_monday = today + timedelta(days=7 - today.weekday())
            prompt = HR_ANALYSIS_TEMPLATE.format(
                contact_name=contact_name,
                context_data=transcript,
                current_date=today.isoformat(),
                current_weekday=_WEEKDAYS_VI[today.weekday()],
                tomorrow_date=(today + timedelta(days=1)).isoformat(),
                day_after_tomorrow=(today + timedelta(days=2)).isoformat(),
                next_monday_date=next_monday.isoformat(),
                monday_after_next_date=(next_monday + timedelta(days=7)).isoformat(),
                audio_duration_seconds=(
                    f"{audio_duration_seconds:.1f}" if audio_duration_seconds is not None else "không rõ"
                ),
                speaker_mode=speaker_mode,
            )

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
                "max_tokens": 1100
            }

            # Gửi HTTP Request bất đồng bộ (Tăng timeout lên 300s để phòng hờ Ollama load model lần đầu quá lâu)
            async with httpx.AsyncClient(timeout=300.0) as client:
                parsed_data = await self._request_analysis(client, payload)
                if _needs_refusal_recheck(parsed_data, transcript):
                    logger.warning("TU_CHOI_LUON thiếu bằng chứng hoặc mâu thuẫn summary; phân loại lại một lần.")
                    retry_payload = {
                        **payload,
                        "messages": [
                            *payload["messages"],
                            {
                                "role": "user",
                                "content": (
                                    "Kiểm tra lại kết luận trước khi trả JSON. Kết quả trước chọn "
                                    "TU_CHOI_LUON nhưng thiếu câu nói của ứng viên hoặc summary "
                                    "có dấu hiệu tích cực. Trích đúng câu nói của ỨNG VIÊN vào "
                                    "candidate_evidence; chỉ giữ TU_CHOI_LUON khi từ chối CÔNG VIỆC "
                                    "hoặc đang làm nơi khác và chủ động kết thúc trao đổi. "
                                    "Nếu còn quan tâm khi đang đi làm nơi khác: DANG_DI_LAM. "
                                    "Nếu sẵn sàng đi làm: DI_LAM. Nếu lưỡng lự: SUY_NGHI_THEM. "
                                    "Phân tích lại toàn bộ transcript và trả JSON đúng schema."
                                ),
                            },
                        ],
                    }
                    parsed_data = await self._request_analysis(client, retry_payload)
                    if _needs_refusal_recheck(parsed_data, transcript):
                        raise ClassificationNeedsReview(
                            "Không đủ bằng chứng để đóng hồ sơ bằng TU_CHOI_LUON; "
                            "cần người nghe kiểm tra audio."
                        )

            # Chỉ suy ra hành động sau khi phân loại vượt qua kiểm tra từ chối.
            reason_code = ReasonCode(parsed_data["reason_code"])
            if reason_code == ReasonCode.KNM_DAP_MAY and (
                audio_duration_seconds is None or audio_duration_seconds >= 15
            ):
                raise ClassificationNeedsReview(
                    "KNM_DAP_MAY chỉ dùng khi audio dưới 15 giây và ứng viên chủ động cúp máy."
                )
            status_group = REASON_CODE_GROUP[reason_code]
            call_decision = GROUP_CALL_DECISION[status_group]

            return AnalysisResult(
                summary=parsed_data.get("summary") or "Không có tóm tắt.",
                status_group=status_group,
                reason_code=reason_code,
                call_decision=call_decision,
                appointment_date=_appointment_date(parsed_data, reason_code),
                follow_up_days=_follow_up_days(parsed_data, reason_code),
            )

        except httpx.RequestError as e:
            logger.error(f"Lỗi kết nối tới Ollama: {e}")
            raise LLMProcessingError(f"Không thể kết nối tới Ollama API: {e}")
        except LLMProcessingError:
            raise
        except Exception as e:
            import traceback
            logger.error(f"Xử lý LLM thất bại cho đối tượng {contact_name}: {e}")
            logger.error(f"Chi tiết lỗi:\n{traceback.format_exc()}")
            raise LLMProcessingError(f"Quá trình phân tích dữ liệu hội thoại gặp sự cố cục bộ: {e}")


# Tạo duy nhất 1 biến instance sẵn sàng để đăng ký tại app.state khi chạy ứng dụng FastAPI
llm_service = LLMService()
