# -------------------------------------------------------
# app/services/audio_service.py
# Logic tải file audio từ nội bộ, kiểm tra định dạng
# -------------------------------------------------------
# Functions:
#
# async download_audio(audio_url: str, task_id: str) -> Path
#   1. Dùng httpx.AsyncClient tải audio từ URL nội bộ CRM
#   2. Kiểm tra extension (chỉ cho phép: .mp3, .wav, .m4a, .ogg)
#   3. Kiểm tra kích thước file (max: MAX_AUDIO_SIZE_MB)
#   4. Lưu vào: AUDIO_DOWNLOAD_DIR/{task_id}_{filename}
#   5. Trả về đường dẫn local tới file đã tải
#
# Exceptions:
#   - AudioDownloadError    : Không tải được file
#   - AudioValidationError  : File sai định dạng hoặc quá lớn
#
# TODO: Implement download logic
# -------------------------------------------------------
