import asyncio
import importlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.classification import REASON_CODE_GROUP, ReasonCode
from app.schemas.response import AnalysisResult

llm_module = importlib.import_module("app.services.llm_service")


def test_canonical_codes_and_output_invariants():
    assert "CHUA_CHOT_NGAY" not in ReasonCode.__members__
    assert REASON_CODE_GROUP[ReasonCode.DANG_DI_LAM] == 3
    result = AnalysisResult(
        summary="Ứng viên đang đi làm nơi khác nhưng hỏi về công việc.",
        status_group=1,
        reason_code=ReasonCode.DANG_DI_LAM,
        appointment_date="2026-11-09",
        follow_up_days=14,
    )
    assert result.status_group == 3
    assert result.call_decision.value == "FOLLOW_UP"
    assert result.appointment_date is None
    assert result.follow_up_days is None
    assert "recommended_message" not in result.model_dump()


def test_refusal_requires_candidate_evidence_not_hr_negation():
    transcript = "[00:01] HR: Nếu anh không đi xe máy được thì đi xe bus.\n[00:05] Ứng viên: Mai anh ra."
    proposed = {
        "reason_code": "TU_CHOI_LUON",
        "summary": "Ứng viên đồng ý đến nhà máy.",
        "candidate_evidence": "không đi xe máy",
        "refusal_basis": "explicit_job_refusal",
    }
    assert llm_module._needs_refusal_recheck(proposed, transcript)
    real = {
        "reason_code": "TU_CHOI_LUON",
        "summary": "Ứng viên không có nhu cầu nhận công việc.",
        "candidate_evidence": "Anh không có nhu cầu",
        "refusal_basis": "explicit_job_refusal",
    }
    assert not llm_module._needs_refusal_recheck(
        real, "[00:01] Ứng viên: Anh không có nhu cầu."
    )


def test_date_only_and_hen_xa_fallback():
    assert llm_module._appointment_date(
        {"appointment_date": "2026-11-09T09:00:00"}, ReasonCode.HEN_PHONG_VAN
    ) == "2026-11-09"
    assert llm_module._appointment_date(
        {"appointment_date": "2026-11-09"}, ReasonCode.DI_LAM
    ) is None
    assert llm_module._follow_up_days({"follow_up_days": None}, ReasonCode.HEN_XA) == 7
    assert llm_module._follow_up_days({"follow_up_days": 14}, ReasonCode.HEN_XA) == 14


def test_llm_prompt_uses_server_date_and_rejects_long_knm():
    class Response:
        status_code = 200
        text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "summary": "Ứng viên cúp máy.",
                "reason_code": "KNM_DAP_MAY",
                "appointment_date": None,
                "follow_up_days": None,
                "candidate_evidence": "",
                "refusal_basis": "none",
            })}}]}

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            prompt = json["messages"][1]["content"]
            assert "thứ Hai tuần sau: 2026-11-09" in prompt
            assert "thứ Hai tới: 2026-11-16" in prompt
            assert "20.0 giây" in prompt
            return Response()

    with patch.object(llm_module.httpx, "AsyncClient", Client):
        with pytest.raises(llm_module.ClassificationNeedsReview):
            asyncio.run(llm_module.llm_service.analyze_audio(
                "HR: Chào anh. Ứng viên: Alo.",
                "Ứng viên",
                reference_datetime=datetime(2026, 11, 8, tzinfo=timezone.utc),
                audio_duration_seconds=20,
            ))


def test_ollama_schema_fallback_uses_openai_compatible_json_mode():
    formats = []

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = "unsupported response_format json_schema" if status_code == 400 else ""

        def raise_for_status(self):
            assert self.status_code == 200

        def json(self):
            return {"choices": [{"message": {"content": '{"reason_code":"DI_LAM"}'}}]}

    class Client:
        async def post(self, url, json):
            formats.append(json.get("response_format"))
            return Response(400 if len(formats) == 1 else 200)

    result = asyncio.run(llm_module.llm_service._request_analysis(
        Client(), {"response_format": {"type": "json_schema"}}
    ))
    assert formats == [{"type": "json_schema"}, {"type": "json_object"}]
    assert result["reason_code"] == "DI_LAM"
