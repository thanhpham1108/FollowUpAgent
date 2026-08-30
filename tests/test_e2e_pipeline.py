import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.api.v1.endpoints.analyze import process_candidate_audio
from app.schemas.request import CandidateAnalyzeRequest
from app.schemas.response import AnalysisResult
from app.core.database import SessionLocal
from app.core.models import CallRecord, CallStatus

@pytest.mark.asyncio
async def test_e2e_pipeline_success():
    """
    Test toàn bộ luồng xử lý E2E: DB -> STT (mocked) -> LLM (mocked) -> Rule Engine -> Webhook.
    Sử dụng dữ liệu giả lập vì máy local hiện tại không có GPU để chạy PhoWhisper / LLaMA.
    """
    task_id = "TASK-test-1234"
    request = CandidateAnalyzeRequest(
        ssn="123456789",
        candidate_name="Nguyen Van A",
        audio_url="http://fake-crm.com/22685287.pcm.wav"
    )

    mock_analysis_result = AnalysisResult(
        summary="Ứng viên giao tiếp tốt, mong muốn mức lương 15tr.",
        status_group=4,
        reason_code="HEN_PHONG_VAN",
        appointment_date="2026-08-20T09:00:00",
        recommended_message="Chào bạn, mời bạn đến phỏng vấn lúc 9h ngày 20/08."
    )

    with patch("app.api.v1.endpoints.analyze.speech_to_text", new_callable=AsyncMock) as mock_stt, \
         patch("app.api.v1.endpoints.analyze.llm_service.analyze_audio", new_callable=AsyncMock) as mock_llm, \
         patch("app.api.v1.endpoints.analyze.notify_crm_hr_webhook", new_callable=AsyncMock) as mock_webhook:
        
        # Setup giá trị trả về cho các hàm bất đồng bộ
        mock_stt.return_value = "Xin chào, tôi tên là Nguyễn Văn A. Tôi muốn ứng tuyển..."
        mock_llm.return_value = mock_analysis_result

        # Chạy pipeline chính
        await process_candidate_audio(task_id, request)

        # 1. Kiểm tra Webhook có được gọi đúng format payload hay không
        mock_webhook.assert_called_once()
        webhook_args = mock_webhook.call_args[0][0]
        assert webhook_args["task_id"] == task_id
        assert webhook_args["ssn"] == request.ssn
        assert webhook_args["status"] == "completed"
        assert webhook_args["result"]["summary"] == mock_analysis_result.summary

    from sqlalchemy.future import select

    # 2. Kiểm tra trạng thái dữ liệu đã lưu vào PostgreSQL (hoặc test DB async)
    async with SessionLocal() as db:
        result = await db.execute(select(CallRecord).filter(CallRecord.id == task_id))
        record = result.scalars().first()
        
        assert record is not None
        assert record.status == CallStatus.COMPLETED
        assert record.transcript == mock_stt.return_value
        assert record.summary == mock_analysis_result.summary
        assert record.intent == mock_analysis_result.reason_code
        
        # Xóa record test
        await db.delete(record)
        await db.commit()
    
    print("✅ E2E Pipeline test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_e2e_pipeline_success())
