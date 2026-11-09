# FollowUpAgent – Weekly Report

> **Week:** May 5 – May 10, 2026  
> **Team:** Datacore  
> **Project:** FollowUpAgent – AI-powered HR Interview Analysis

---

## 1. This Week's Progress

| # | Task | Status |
|---|------|--------|
| 1 | Define system architecture (offline AI deployment) | ✅ Done |
| 2 | Identify hardware requirements for Datacore | ✅ Done |
| 3 | Design API contract with CRM team | ✅ Done |



---

## 2. Infrastructure Requirements (For Datacore)

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

## 3. Focus for This Week

This week we'll report primarily on the API contract and the infrastructure requirements requested by Datacore. Key actions:

- Finalize and present the API contract to the CRM team and capture feedback.
- Confirm the server provisioning timeline and ensure a GPU with ≥ 24GB VRAM is allocated.
- Prepare a minimal FastAPI skeleton (health-check) for validation on the test VM.
- Schedule a short sync with Datacore to confirm internal network and PostgreSQL access constraints.

---



---

## 5. API Contract — Summary

Purpose: define how CRM hands candidate audio to the local AI service and how the AI returns results.

Overview:

- CRM -> AI: POST candidate metadata + an `audio_url` to the AI endpoint. The AI queues processing and returns a `task_id` (202 Accepted).
- AI -> CRM: when processing completes, AI POSTs the result to CRM's webhook URL indicated in the API contract.
- All network traffic is internal only; audio must be hosted on an internal HTTP(S) URL reachable by the AI server.

Key endpoints (from `FollowUpAgent_API_contract.json`):

- `POST http://127.0.0.1:8000/api/v1/candidates/analyze`
	- Body (JSON):

```json
{
	"ssn": "079099123456",
	"candidate_name": "Nguyen Van A",
	"audio_url": "http://{{crm_server_ip}}/files/079099123456_interview.mp3"
}
```

	- Response: `202 Accepted` (queued)

```json
{
	"task_id": "TASK-a1b2c3d4",
	"status": "processing",
	"message": "Audio received and is being processed in the background."
}
```

- Webhook (CRM must provide): `POST http://{{crm_server_ip}}/webhook/candidate-recommendation`
	- AI posts result when ready. Example payload:

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

Contract variables (placeholders):

- `ai_server_ip`: default `127.0.0.1` (local AI service)
- `crm_server_ip`: example `192.168.1.200` — CRM should provide the real internal IP

Integration notes / recommendations:

- Ensure the `audio_url` is reachable from the AI server (internal network access). Host files on the CRM server or an internal store.
- CRM must expose the webhook endpoint and return a 200 OK; otherwise the AI may drop or log-but-not-retry results.
- The contract currently does not mandate authentication. If you require secure delivery, add either a shared HMAC header or a short-lived bearer token to the webhook and ingest endpoints.
- Use `task_id` for idempotency and tracking. Store `task_id` on the CRM side so retries or duplicated webhooks can be deduplicated.
- Recommend exponential-backoff retries on webhook failures and operational logging on both sides.

Slide tips: include the sample request, the 202 response, and the webhook payload as three separate slides to show the end-to-end flow.




## 6. Roadmap (slower 4‑week plan)

We’ll spread work across four weeks so the team can focus, review the module spec, and validate each core flow before moving on.

| # | Task | Target Date | Owner |
|---|------|-------------|-------|
| 1 | Provision a small test server (VM) for the FastAPI service | Week 1 (by May 19) | FollowUpAgent Team (request VM from Datacore) |
| 2 | Produce a Module Specification document (list modules, file responsibilities, interfaces, and simple API contracts) | Week 1 (by May 19) | FollowUpAgent Team |
| 3 | Set up a minimal FastAPI skeleton (health‑check + routing) | Week 2 (by May 26) | FollowUpAgent Team |
| 4 | Implement basic ingestion flow (accept `audio_url`, return `task_id`) | Week 3 (by Jun 2) | FollowUpAgent Team |
| 5 | Implement webhook delivery and retry strategy (basic sender) | Week 3 (by Jun 2) | FollowUpAgent Team |
| 6 | Add basic E2E test with sample audio and Postman collection | Week 4 (by Jun 9) | FollowUpAgent Team & CRM |
| 7 | Draft README + developer onboarding docs; handoff for CRM review | Week 4 (by Jun 9) | FollowUpAgent Team & CRM |
| 8 | Design Whisper + LLM integration and performance test plan (no heavy infra changes yet) | Week 4 (by Jun 9) | FollowUpAgent Team (design) |

Notes:
- Week 1 remains light to finalize the module spec and confirm VM details.
- Week 2 focuses on skeleton and developer onboarding so Week 3 can implement ingestion and webhook reliably.
- This schedule keeps the heavy model integration as a design task until basic flows are validated.

- Datacore: provides requested VM/GPU and internal network access; the FollowUpAgent Team will coordinate provisioning requests.

---

## 7. Project Skeleton — Modules & Files

Goal: provide a minimal, clear structure so each developer knows where to implement features.

- `app/main.py` — FastAPI application entrypoint; mounts routers and startup/shutdown events.
- `app/api/v1/candidates.py` — API routes: `POST /api/v1/candidates/analyze`, health endpoint, and task status endpoints.
- `app/schemas.py` — Pydantic request/response models (CandidateIn, TaskStatus, WebhookPayload, etc.).
- `app/services/transcription.py` — wrapper around Whisper or chosen STT; accepts `audio_url`, returns raw transcript.
- `app/services/analysis.py` — runs LLM-based analysis on transcript; returns `summary` and `recommended_message`.
- `app/services/task_queue.py` — lightweight in‑process queue or adapter to a job runner (holds `task_id`, status updates).
- `app/webhook/sender.py` — posts results to CRM webhook with retry/backoff and logging.
- `app/core/config.py` — configuration (server ports, CRM webhook URL template, retry limits); reads env vars.
- `app/db/postgres.py` — optional: PostgreSQL client for persisting tasks and results (if needed).
- `tests/` — unit and integration tests, plus a Postman collection in `tests/postman/` for manual verification.
- `README.md` — setup, run, environment variables, and quick Postman test instructions.
- `requirements.txt` — Python deps for the skeleton (FastAPI, Uvicorn, HTTPX, Pydantic, pytest).

Optional files (later): `Dockerfile`, `docker-compose.yml`, `migrations/` (if using DB), monitoring scripts.

Suggested next step: I can scaffold these files (empty modules + function stubs) so your team can implement them incrementally. Recommend starting with `app/main.py`, `app/api/v1/candidates.py`, and `app/schemas.py`.
