import os
import httpx
import whisper
import logging
from pathlib import Path
from app.core.config import settings

# Giả định các Exception này được định nghĩa trong app/core/exceptions.py
# Nếu chưa có, bạn có thể tự tạo exception class kế thừa từ Exception
try:
    from app.core.exceptions import AudioDownloadError, AudioValidationError
except ImportError:
    class AudioDownloadError(Exception): pass
    class AudioValidationError(Exception): pass

logger = logging.getLogger(__name__)

# Load model một lần khi khởi động (tránh load lại mỗi request)
_model = None


def get_whisper_model():
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
        _model = whisper.load_model(settings.WHISPER_MODEL, device=settings.WHISPER_DEVICE)
        logger.info("Whisper model loaded.")
    return _model


async def download_audio(audio_url: str, task_id: str) -> Path:
    """
    1. Kiểm tra extension từ URL.
    2. Dùng httpx.AsyncClient tải audio từ URL nội bộ CRM (Stream nhận header trước để check size).
    3. Lưu vào: AUDIO_DOWNLOAD_DIR/{task_id}_{filename}
    4. Trả về đường dẫn local tới file đã tải dạng Path object.
    """
    # Lấy extension từ URL
    url_path = Path(audio_url.split("?")[0])  # Loại bỏ query params nếu có
    extension = url_path.suffix.lower().lstrip(".")

    # 1. Kiểm tra extension hợp lệ
    if extension not in settings.allowed_extensions_list:
        raise AudioValidationError(
            f"Định dạng file .{extension} không được hỗ trợ. Chỉ chấp nhận: {settings.ALLOWED_AUDIO_EXTENSIONS}"
        )

    # Đảm bảo thư mục lưu trữ tồn tại
    download_dir = Path(settings.AUDIO_DOWNLOAD_DIR)
    download_dir.mkdir(parents=True, exist_ok=True)

    # Đặt tên file theo chuẩn: {task_id}_{filename}
    dest_file_path = download_dir / f"{task_id}_{url_path.name}"

    try:
        # Sử dụng stream=True để đọc content-length trước khi kéo toàn bộ file về
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("GET", audio_url) as response:
                if response.status_code != 200:
                    raise AudioDownloadError(f"Không thể tải file, CRM phản hồi mã lỗi: {response.status_code}")

                # 2. Kiểm tra kích thước file qua Header Content-Length (nếu có)
                content_length = response.headers.get("Content-Length")
                max_bytes = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
                if content_length and int(content_length) > max_bytes:
                    raise AudioValidationError(f"File vượt quá dung lượng cho phép ({settings.MAX_AUDIO_SIZE_MB}MB)")

                # Tiến hành ghi file bất đồng bộ theo từng block chunk
                # Đề phòng trường hợp server không trả về Content-Length, ta cộng dồn để check dung lượng
                bytes_downloaded = 0
                with open(dest_file_path, "wb") as f:
                    async edit_iterator in response.aiter_bytes(chunk_size=8192):
                        bytes_downloaded += len(edit_iterator)
                        if bytes_downloaded > max_bytes:
                            # Xóa file tạm đang ghi dở trước khi raise lỗi
                            if dest_file_path.exists():
                                dest_file_path.unlink()
                            raise AudioValidationError(f"File tải về thực tế vượt quá giới hạn dung lượng ({settings.MAX_AUDIO_SIZE_MB}MB)")
                        
                        f.write(edit_iterator)

        logger.info(f"Đã tải thành công audio về: {dest_file_path}")
        return dest_file_path

    except httpx.HTTPError as he:
        logger.error(f"Lỗi kết nối mạng khi tải audio từ {audio_url}: {he}")
        raise AudioDownloadError(f"Lỗi mạng khi tải file từ CRM: {he}")
    except Exception as e:
        if not isinstance(e, (AudioValidationError, AudioDownloadError)):
            logger.error(f"Lỗi không xác định khi tải audio: {e}")
            raise AudioDownloadError(f"Quá trình tải file thất bại: {e}")
        raise


def transcribe_audio(file_path: Path) -> dict:
    """
    Chạy Whisper STT trên file audio cục bộ.
    Trả về dict với transcript, language, segments.
    """
    model = get_whisper_model()
    str_path = str(file_path.resolve())
    logger.info(f"Đang tiến hành nhận diện (STT): {str_path}")

    result = model.transcribe(
        str_path,
        language="vi",            # Ép dịch tiếng Việt theo yêu cầu hệ thống
        task="transcribe",
        verbose=False,
        fp16=False,               # Chạy mặc định trên CPU (hoặc GPU ko hỗ trợ nửa chính xác)
    )

    return {
        "text": result["text"].strip(),
        "language": result.get("language", "vi"),
        "segments": result.get("segments", []),
    }


async def speech_to_text(audio_url: str, task_id: str) -> str:
    """
    Full pipeline: download audio → transcribe → cleanup.
    Trả về chuỗi văn bản (transcript).
    """
    file_path: Path = None
    try:
        # Cập nhật truyền thêm task_id phục vụ đặt tên file định danh
        file_path = await download_audio(audio_url, task_id)
        result = transcribe_audio(file_path)
        return result["text"]
    except Exception as e:
        logger.error(f"STT pipeline thất bại cho task {task_id} (URL: {audio_url}): {e}")
        raise
    finally:
        # Dọn dẹp file sau khi xử lý xong (hoặc lỗi) tránh tràn ổ cứng
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"Đã dọn dẹp file tạm: {file_path}")