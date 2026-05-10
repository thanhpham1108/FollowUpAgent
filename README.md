# FollowUpAgent

**FollowUpAgent** is an internal AI service that automates the analysis of candidate interview audio recordings. After processing, the system generates a recommended follow-up message for the HR team to review and send.

**Key technologies:**
- **Backend API:** FastAPI (Python)
- **AI Pipeline:** LangChain + Whisper (Speech-to-Text) + Local LLM
- **Deployment:** On-premise, no internet connection required

> Weekly reports, infrastructure specs, and next steps are in the [`Reports/`](./Reports/) folder.

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────┐
│                  INTERNAL NETWORK                │
│                                                  │
│  ┌──────────┐   POST /api/v1/candidates/analyze  │
│  │          │ ─────────────────────────────────► │
│  │   CRM    │                                    │
│  │  System  │ ◄───────────────────────────────── │
│  │          │   POST /webhook/candidate-recommend │
│  └──────────┘                                    │
│                         ▲ Webhook result          │
│                         │                        │
│  ┌──────────────────────┴──────────────────────┐ │
│  │          FollowUpAgent AI Service            │ │
│  │                                              │ │
│  │   FastAPI  ──►  Whisper  ──►  Local LLM      │ │
│  │  (receive)   (STT audio)   (analyze & draft) │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Flow:**
1. CRM sends candidate SSN + internal audio URL to the AI service.
2. AI service transcribes the audio (Whisper) and analyzes the content (LLM).
3. AI sends the analysis summary and recommended message back to CRM via Webhook.
4. HR team reviews the recommendation in the CRM and decides on next steps.

---

## 2. API Contract Summary

The full API contract is available as a Postman Collection:  
📄 `FollowUpAgent_API_contract.json`

Import it into Postman, set the two variables below, and you're ready to test.

### 4.1. CRM → AI: Submit audio for analysis

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **Endpoint** | `http://127.0.0.1:8000/api/v1/candidates/analyze` |
| **Content-Type** | `application/json` |

**Request body:**
```json
{
  "ssn": "079099123456",
  "candidate_name": "Nguyen Van A",
  "audio_url": "http://{crm_server_ip}/files/079099123456_interview.mp3"
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "TASK-a1b2c3d4",
  "status": "processing",
  "message": "Audio received and is being processed in the background."
}
```

> Note: pass the audio as an internal URL, not a file upload.

---

### 4.2. AI → CRM: Webhook – Deliver result

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **Endpoint** | `http://{crm_server_ip}/webhook/candidate-recommendation` |
| **Content-Type** | `application/json` |

> Note: CRM needs to have this endpoint up before the AI finishes – otherwise the result gets dropped.

**Payload AI will send:**
```json
{
  "task_id": "TASK-a1b2c3d4",
  "ssn": "079099123456",
  "status": "completed",
  "result": {
    "summary": "Candidate has solid technical skills and communicates clearly. Expected salary: 15M VND.",
    "recommended_message": "Chào anh Nguyễn Văn A, cảm ơn anh đã tham gia phỏng vấn. Chúng tôi sẽ thông báo kết quả chính thức trong vòng 2 ngày làm việc tới. Trân trọng."
  }
}
```

