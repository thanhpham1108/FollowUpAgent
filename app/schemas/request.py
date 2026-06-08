# -------------------------------------------------------
# app/schemas/request.py
# Cấu trúc JSON nhận từ CRM
# -------------------------------------------------------
# Model: AnalyzeRequest
#   - ssn: str            → Mã số thuế / CCCD ứng viên
#   - candidate_name: str → Tên ứng viên
#   - audio_url: HttpUrl  → URL nội bộ tới file audio
#
# Ví dụ request từ CRM:
# {
#   "ssn": "079099123456",
#   "candidate_name": "Nguyen Van A",
#   "audio_url": "http://192.168.1.200/files/079099123456_interview.mp3"
# }
#
from pydantic import BaseModel, HttpUrl

class AnalyzeRequest(BaseModel):
    ssn: str
    candidate_name: str
    audio_url: HttpUrl# -------------------------------------------------------
