import asyncio
import importlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.classification.codes import REASON_CODE_GROUP, ReasonCode
from app.schemas.response import AnalysisResult

llm_module = importlib.import_module("app.classification.llm")


def test_canonical_codes_and_output_invariants():
    assert "CHUA_CHOT_NGAY" not in ReasonCode.__members__
    assert "DANG_DI_LAM" not in ReasonCode.__members__
    assert REASON_CODE_GROUP[ReasonCode.TRAO_DOI_THEM] == 3
    result = AnalysisResult(
        summary="Ứng viên đang đi làm nơi khác nhưng hỏi về công việc.",
        status_group=1,
        reason_code=ReasonCode.TRAO_DOI_THEM,
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
    assert llm_module._needs_refusal_recheck(
        real,
        "[00:01] Ứng viên: Anh không có nhu cầu. "
        "[00:15] Ứng viên: Mai anh ra nhà máy để đi làm.",
    )

    employed_only = {
        "reason_code": "TU_CHOI_LUON",
        "summary": "Ứng viên đang đi làm nơi khác, nghe tư vấn rồi kết thúc cuộc gọi.",
        "candidate_evidence": "Anh đang đi làm rồi",
        "refusal_basis": "explicit_job_refusal",
    }
    assert llm_module._needs_refusal_recheck(
        employed_only, "Ứng viên: Anh đang đi làm rồi"
    )
    stop_contact = {
        "reason_code": "TU_CHOI_LUON",
        "summary": "Ứng viên yêu cầu không liên hệ nữa.",
        "candidate_evidence": "Đừng gọi cho anh nữa",
        "refusal_basis": "stop_contact",
    }
    assert not llm_module._needs_refusal_recheck(
        stop_contact, "Ứng viên: Đừng gọi cho anh nữa"
    )


def test_declining_monday_interview_is_not_job_refusal_or_confirmed_start():
    transcript = (
        "HR: Thứ Hai anh có rảnh đi phỏng vấn không? "
        "Ứng viên: Anh không đi làm thứ Hai được vì việc gia đình, không kịp xe. "
        "Có thể anh đi trước ngày 15. "
        "HR: Ngày 13 hoặc 14 em gọi lại nhé. Ứng viên: Ok em."
    )
    wrong_refusal = {
        "reason_code": "TU_CHOI_LUON",
        "summary": "Ứng viên không đi thứ Hai vì việc gia đình, hẹn gọi lại ngày 13/14.",
        "candidate_evidence": "Anh không đi làm thứ Hai được vì việc gia đình",
        "refusal_basis": "explicit_job_refusal",
    }
    assert llm_module._needs_refusal_recheck(wrong_refusal, transcript)

    premature_success = {
        "reason_code": "DI_LAM",
        "summary": "Ứng viên có thể đi trước ngày 15, HR sẽ liên hệ lại ngày 13/14.",
        "candidate_evidence": "Có thể anh đi trước ngày 15",
    }
    assert llm_module._needs_success_recheck(premature_success, transcript)

    confirmed_success = {
        "reason_code": "DI_LAM",
        "summary": "Ứng viên xác nhận sẽ đến nhà máy làm việc vào ngày mai.",
        "candidate_evidence": "Mai anh ra nhà máy đi làm",
    }
    assert not llm_module._needs_success_recheck(
        confirmed_success, "Ứng viên: Mai anh ra nhà máy đi làm"
    )
    confirmed_success["summary"] += " HR sẽ liên hệ lại qua Zalo để hướng dẫn đường đi."
    assert not llm_module._needs_success_recheck(
        confirmed_success, "Ứng viên: Mai anh ra nhà máy đi làm"
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


def test_conditional_start_is_rechecked_as_interview_willingness():
    answers = [
        {
            "summary": "Ứng viên có thể đi trước ngày 15, hẹn gọi lại ngày 13/14.",
            "reason_code": "DI_LAM",
            "appointment_date": None,
            "follow_up_days": None,
            "candidate_evidence": "Có thể anh đi trước ngày 15",
            "refusal_basis": "none",
        },
        {
            "summary": "Ứng viên bận việc gia đình và không kịp xe thứ Hai. Anh nói 'Có thể anh đi trước ngày 15' nhưng chưa xác nhận ngày đi làm. HR đã tư vấn việc làm và hẹn gọi lại ngày 13 hoặc 14 để thống nhất. Hai bên đã có Zalo để trao đổi tiếp.",
            "reason_code": "HEN_PHONG_VAN",
            "appointment_date": None,
            "follow_up_days": None,
            "candidate_evidence": "Có thể anh đi trước ngày 15",
            "refusal_basis": "none",
        },
    ]

    class Response:
        status_code = 200
        text = ""

        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(self.content)}}]}

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            return Response(answers.pop(0))

    transcript = "HR: Thứ Hai anh đi phỏng vấn được không? Ứng viên: Có thể anh đi trước ngày 15. HR: Ngày 13/14 em gọi lại. Ứng viên: Ok em."
    trace = []
    with patch.object(llm_module.httpx, "AsyncClient", Client):
        result = asyncio.run(llm_module.llm_service.analyze_audio(
            transcript, "Ứng viên", trace_callback=trace.append,
        ))
    assert not answers
    assert result.reason_code == ReasonCode.HEN_PHONG_VAN
    assert result.status_group == 4
    assert result.appointment_date is None
    assert result.follow_up_days is None
    assert [entry["event"] for entry in trace] == [
        "model_response", "guard", "model_response", "guard", "final",
    ]
    assert [entry["attempt"] for entry in trace if entry["event"] == "model_response"] == [1, 2]
    assert trace[0]["parsed"]["reason_code"] == "DI_LAM"
    assert trace[2]["parsed"]["reason_code"] == "HEN_PHONG_VAN"
    assert trace[-1]["outcome"] == "accepted"


def test_refusal_guard_keeps_ambiguous_retry_in_follow_up_with_review_flag():
    answer = {
        "summary": "Ứng viên đang làm nơi khác, hỏi lương và nhận thông tin qua Zalo.",
        "reason_code": "TU_CHOI_LUON",
        "appointment_date": None,
        "follow_up_days": None,
        "candidate_evidence": "Anh đang đi làm rồi",
        "refusal_basis": "explicit_job_refusal",
    }

    class Response:
        status_code = 200
        text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(answer)}}]}

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            return Response()

    trace = []
    with patch.object(llm_module.httpx, "AsyncClient", Client):
        result = asyncio.run(llm_module.llm_service.analyze_audio(
            "Ứng viên: Anh đang đi làm rồi, gửi Zalo anh xem thêm.",
            "Ứng viên", trace_callback=trace.append,
        ))
    assert sum(entry["event"] == "model_response" for entry in trace) == 2
    assert result.reason_code == ReasonCode.TRAO_DOI_THEM
    assert result.call_decision.value == "FOLLOW_UP"
    assert "cần nghe lại" in result.summary.lower()
    assert "từ chối công việc" not in result.summary.lower()
    assert trace[-2]["event"] == "fallback"
    assert trace[-2]["requires_review"] is True
    assert trace[-1]["outcome"] == "accepted"
    assert trace[-1]["requires_review"] is True


def test_truncated_model_json_is_reported_before_reason_guard():
    class Response:
        status_code = 200
        text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"reason_code": "TU_CHOI_LUON"'}}]}

    class Client:
        async def post(self, url, json):
            return Response()

    trace = []
    with pytest.raises(llm_module.LLMProcessingError, match="JSON không hợp lệ"):
        asyncio.run(llm_module.llm_service._request_analysis(
            Client(), {}, trace_callback=trace.append,
        ))
    assert trace[0]["event"] == "model_response"
    assert trace[0]["parsed"] == {}


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
