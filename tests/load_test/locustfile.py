# -------------------------------------------------------
# tests/load_test/locustfile.py
# Giả lập tải cho FollowUpAgent API
# -------------------------------------------------------
# Yêu cầu:
#   pip install locust
#
# Cách chạy trên server test:
#   export LOCUST_API_HOST=http://<server-ip>:8000
#   export LOCUST_AUDIO_URL=http://<internal-storage>/sample.mp3  # nếu không ra internet
#   locust -f tests/load_test/locustfile.py --host $LOCUST_API_HOST --headless -u 20 -r 2 -t 60s
#
# Cách chạy local (có UI):
#   locust -f tests/load_test/locustfile.py --host http://localhost:8000
#   Sau đó mở: http://localhost:8089
# -------------------------------------------------------
import os
import random
from locust import HttpUser, task, between

# ── Audio URL mẫu ─────────────────────────────────────────────────────────────
# Ưu tiên đọc từ ENV — quan trọng khi server test không ra internet
# Nếu có file audio nội bộ trên server: export LOCUST_AUDIO_URL=http://10.0.0.x/audio.mp3
_DEFAULT_AUDIO_URLS = [
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
]
_env_audio = os.getenv("LOCUST_AUDIO_URL")
SAMPLE_AUDIO_URLS = [_env_audio] if _env_audio else _DEFAULT_AUDIO_URLS


SAMPLE_CANDIDATES = [
    {"ssn": "001234567890", "candidate_name": "Nguyễn Văn A"},
    {"ssn": "079234567891", "candidate_name": "Trần Thị B"},
    {"ssn": "048201234567", "candidate_name": "Lê Minh C"},
    {"ssn": "030199012345", "candidate_name": "Phạm Thị D"},
    {"ssn": "056202109876", "candidate_name": "Võ Hoàng E"},
]


class FollowUpUser(HttpUser):
    """
    Giả lập 1 CRM System bắn request phân tích audio.
    wait_time: mỗi user đợi 1-3 giây giữa các request (thực tế hơn).
    """
    wait_time = between(1, 3)

    # ── Task 1 (70%): Happy Path ───────────────────────────────────────────────
    @task(7)
    def analyze_candidate_happy_path(self):
        """Gửi request chuẩn đầy đủ. Kỳ vọng: 202 Accepted."""
        candidate = random.choice(SAMPLE_CANDIDATES)
        audio_url = random.choice(SAMPLE_AUDIO_URLS)

        payload = {
            "ssn": candidate["ssn"],
            "candidate_name": candidate["candidate_name"],
            "audio_url": audio_url,
        }
        with self.client.post(
            "/api/v1/candidates/analyze",
            json=payload,
            catch_response=True,
            name="POST /analyze [Happy Path]",
        ) as resp:
            if resp.status_code == 202:
                resp.success()
            else:
                resp.failure(
                    f"Kỳ vọng 202, nhận {resp.status_code}: {resp.text[:200]}"
                )

    # ── Task 2 (20%): Bad Data ─────────────────────────────────────────────────
    @task(2)
    def analyze_candidate_bad_payload(self):
        """Gửi payload thiếu audio_url. Kỳ vọng: 422 Unprocessable Entity."""
        candidate = random.choice(SAMPLE_CANDIDATES)

        payload = {
            "ssn": candidate["ssn"],
            "candidate_name": candidate["candidate_name"],
            # audio_url bị thiếu cố tình
        }
        with self.client.post(
            "/api/v1/candidates/analyze",
            json=payload,
            catch_response=True,
            name="POST /analyze [Bad Payload - Missing audio_url]",
        ) as resp:
            # 422 là đúng — Pydantic validation reject request
            if resp.status_code == 422:
                resp.success()
            else:
                resp.failure(
                    f"Kỳ vọng 422, nhận {resp.status_code}: {resp.text[:200]}"
                )

    # ── Task 3 (10%): Health Check ────────────────────────────────────────────
    @task(1)
    def health_check(self):
        """Kiểm tra endpoint /api/v1/health. Kỳ vọng: 200 OK."""
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
            name="GET /api/v1/health",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(
                    f"Health check thất bại. Status: {resp.status_code}"
                )

    # ── Task 4: Polling Task Status ───────────────────────────────────────────
    @task(2)
    def poll_task_status(self):
        """
        Giả lập CRM polling kiểm tra trạng thái 1 task_id fake.
        Kỳ vọng: 404 Not Found (task_id không tồn tại) hoặc 200 nếu may mắn.
        Mục đích: test DB query performance dưới tải.
        """
        fake_task_id = f"TASK-{''.join(random.choices('abcdef0123456789', k=8))}"
        with self.client.get(
            f"/api/v1/tasks/{fake_task_id}",
            catch_response=True,
            name="GET /tasks/{task_id} [Polling]",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(
                    f"Unexpected status {resp.status_code}: {resp.text[:200]}"
                )
