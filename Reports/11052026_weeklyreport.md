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

## 3. Next Steps (2‑week plan)

We’ll move deliberately, focusing on one thing at a time.

| # | Task | Target Date | Owner |
|---|------|-------------|-------|
| 1 | Provision a small test server (VM) for the FastAPI service | Week 1 (by May 8) | Datacore |
| 2 | Set up a minimal FastAPI skeleton (just a health‑check endpoint) | Week 1 (by May 9) | Datacore |
| 3 | Write a simple “hello‑world” Postman request to verify the endpoint | Week 1 (by May 10) | Both |
| 4 | Draft a short README for the FastAPI repo (no Docker yet) | Week 2 (by May 13) | Both |
| 5 | Review the API contract with the CRM team and capture any feedback | Week 2 (by May 14) | All |
| 6 | Plan how to integrate Whisper and the LLM in the next phase | Week 2 (by May 15) | Datacore |
