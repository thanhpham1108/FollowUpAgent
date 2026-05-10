# FollowUpAgent – Weekly Progress Report

> **Week:** May 5 – May 10, 2026  
> **Team:** Datacore  
> **Project:** FollowUpAgent – AI-powered HR Interview Analysis (POC)

---

## 1. Project Overview

**FollowUpAgent** is an internal AI service that automates the analysis of candidate interview audio recordings. After processing, the system generates a recommended follow-up message for the HR team to review and send.

**Key technologies:**
- **Backend API:** FastAPI (Python)
- **AI Pipeline:** LangChain + Whisper (Speech-to-Text) + Local LLM
- **Deployment:** On-premise, no internet connection required

---

## 2. This Week's Progress

| # | Task | Status |
|---|------|--------|
| 1 | Define system architecture (offline AI deployment) | ✅ Done |
| 2 | Identify hardware requirements for Datacore | ✅ Done |
| 3 | Design API contract with CRM team | ✅ Done |
| 4 | Export Postman Collection for CRM integration | ✅ Done |
| 5 | Write project README and weekly report | ✅ Done |

---

## 3. System Architecture

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

## 4. API Contract Summary

The full API contract is available as a Postman Collection:  
📄 `FollowUpAgent_API_Contract.postman_collection.json`

Import it into Postman, set the two variables below, and you're ready to test.

### 4.1. CRM → AI: Submit audio for analysis

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **Endpoint** | `http://{ai_server_ip}:8000/api/v1/candidates/analyze` |
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

> ⚠️ **CRM must send audio as a URL (internal link), NOT as a direct file upload.**

---

### 4.2. AI → CRM: Webhook – Deliver result

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **Endpoint** | `http://{crm_server_ip}/webhook/candidate-recommendation` |
| **Content-Type** | `application/json` |

> ⚠️ **CRM must implement and expose this endpoint to receive the AI result.**

**Payload AI will send:**
```json
{
  "task_id": "TASK-a1b2c3d4",
  "ssn": "079099123456",
  "status": "completed",
  "result": {
    "summary": "Candidate has solid technical skills and communicates clearly. Expected salary: 15M VND.",
    "recommended_message": "Hi Nguyen Van A, thank you for your interview. Our HR team will follow up with the official result within 2 business days."
  }
}
```

---

## 5. Infrastructure Requirements (For Datacore)

Datacore is expected to provision the following server by **May 12, 2026**:

| Component | Minimum Requirement |
|-----------|-------------------|
| **CPU** | 12–16 vCPU |
| **RAM** | 32 GB |
| **GPU** | 1× NVIDIA GPU with **≥ 24GB VRAM** (e.g., RTX 3090, RTX 4090, A10G, L4) |
| **Storage** | 200 GB SSD |
| **OS** | Ubuntu 22.04 / 24.04 |
| **Network** | Internal only – no internet access required |
| **Database** | PostgreSQL 15+ |

> **Why GPU?** Running both Whisper (Speech-to-Text) and a local LLM (7–8B parameters, e.g., Llama-3-8B or Qwen-2.5-7B) in production requires at least 24GB VRAM for acceptable response time. CPU-only execution would result in processing times of several minutes per audio file.

---

## 6. Next Steps

| # | Task | Target Date | Owner |
|---|------|-------------|-------|
| 1 | Datacore provisions and hands over server | May 12, 2026 | Datacore |
| 2 | API alignment meeting with CRM + all 3 teams | Week 1, May | All teams |
| 3 | CRM implements Webhook endpoint | TBD | CRM team |
| 4 | Set up FastAPI project skeleton | After server handover | Datacore team |
| 5 | Integrate Whisper (STT) module | After server handover | Datacore team |
| 6 | Integrate local LLM via vLLM/Ollama | After server handover | Datacore team |
| 7 | End-to-end POC test with real audio sample | TBD | All teams |
