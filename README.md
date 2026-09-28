# 🎧 FollowUpAgent - End-to-End AI Call Analysis Pipeline

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-00a393)
![PyTorch](https://img.shields.io/badge/PyTorch-CUDA_11.8-ee4c2c)
![Ollama](https://img.shields.io/badge/Ollama-Qwen_2.5-black)

FollowUpAgent is an enterprise-ready, fully automated AI pipeline designed to analyze customer and candidate phone calls. It securely downloads audio from internal PBX/CRMs, transcribes speech to text using **PhoWhisper** (GPU-accelerated), analyzes the conversation nuances using **Local LLMs (Ollama/Qwen)**, and triggers a Rule Engine to schedule follow-up actions—all running in the background.

## 🌟 Key Features

- **🚀 Async & Non-Blocking**: Built on FastAPI. Returns 202 Accepted instantly to the CRM while processing heavy ML workloads in the background.
- **🧠 Local AI Processing**: 100% data privacy. Both Speech-to-Text and LLM logic run entirely locally without relying on external cloud APIs.
- **🚥 Smart Concurrency Control**: Implements syncio.Semaphore and Thread Locks to prevent RAM/CPU thrashing when hit with concurrent requests.
- **🛡️ Auto GPU-Fallback**: Automatically detects CUDA compatibility (sm_60 / Tesla P100 supported). Falls back to CPU gracefully if GPU drivers fail.
- **🧱 Strict JSON LLM Output**: Forces Ollama to output valid, parseable JSON data using native API format flags and few-shot prompting techniques.
- **⚙️ Production Deployment**: Includes Linux systemd service configurations for instant server deployment and high availability.

---

## 🏗️ System Architecture

`mermaid
flowchart LR
    %% External
    CRM[(🏢 Company CRM)]
    
    %% API
    subgraph Gateway ["🌐 API & Concurrency"]
        direction TB
        API(⚡ FastAPI Server)
        Queue{🚥 Semaphore Lock}
        API --- Queue
    end

    %% AI Pipeline
    subgraph AI_Pipeline ["🧠 AI Processing Pipeline"]
        direction LR
        STT(🎙️ PhoWhisper GPU)
        LLM(🤖 Ollama Qwen2.5)
        Rules(⚙️ Rule Engine)
        STT --> LLM --> Rules
    end

    %% Webhook
    Webhook((🚀 Webhook Service))

    %% Flow
    CRM -->|"1. POST Audio URL"| API
    API -.->|"2. HTTP 202"| CRM
    
    Queue ==>|"3. Background Stream"| STT
    Rules ==>|"4. Analysis JSON"| Webhook
    Webhook ==>|"5. Push Result"| CRM

    %% Colors
    classDef external fill:#2c3e50,stroke:#34495e,stroke-width:2px,color:#fff
    classDef api fill:#27ae60,stroke:#2ecc71,stroke-width:2px,color:#fff
    classDef ai fill:#8e44ad,stroke:#9b59b6,stroke-width:2px,color:#fff
    classDef hook fill:#d35400,stroke:#e67e22,stroke-width:2px,color:#fff

    class CRM external
    class API,Queue api
    class STT,LLM,Rules ai
    class Webhook hook
`

---

## 🛠️ Prerequisites

- **OS:** Linux (Ubuntu/CentOS) recommended for production.
- **Hardware:** NVIDIA GPU (Tesla P100 / T4 / RTX series) highly recommended.
- **Software:** 
  - Conda / Python 3.10+
  - PostgreSQL
  - Ollama (running on port 11434 with model qwen2.5:7b-instruct)

---

## 🚀 Installation & Setup

**1. Clone the repository and set up the environment:**
`ash
conda create -n datacore python=3.10 -y
conda activate datacore
`

**2. Install PyTorch with CUDA (Example for CUDA 11.8):**
`ash
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
`

**3. Install project dependencies:**
`ash
pip install -r requirements.txt
`

**4. Configure Environment Variables:**
Copy .env.example to .env and configure your database and CRM webhook endpoints. Do NOT hardcode WHISPER_DEVICE=cpu if you intend to use a GPU.

**5. Start the Server (Development):**
`ash
python -m uvicorn app.main:app --host 0.0.0.0 --port 18000
`

---

## 📦 Production Deployment (Systemd)

To deploy the application as a permanent background service on a Linux server:

`ash
cd deploy
chmod +x setup_service.sh
./setup_service.sh
`

You can monitor the service health using:
`ash
sudo systemctl status followup-agent.service
sudo journalctl -u followup-agent.service -f
`

---

## 🧪 Included Utilities

### Load Tester (scripts/load_test.py)
Stress-test the concurrency queue and monitor processing times.
`ash
python scripts/load_test.py --url http://localhost:18000 --audio-url http://localhost:8001/test.wav --count 10 --poll
`

### Audio Scraper (scripts/extract_audio_urls.py)
Utility to scrape real production audio links from internal CRM APIs for testing.
`ash
python scripts/extract_audio_urls.py --limit 50 --output urls.txt
`

---
*Built with ❤️ for High-Performance Voice AI Integrations.*
