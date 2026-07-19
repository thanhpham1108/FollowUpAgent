# -------------------------------------------------------
# app/utils/file_manager.py
# Xóa / dọn dẹp file audio tạm thời
# -------------------------------------------------------
# Functions:
#
# cleanup_audio(file_path: Path) -> None
#   - Xóa file audio tạm sau khi xử lý xong
#   - Log hành động cleanup
#   - Bỏ qua nếu file không tồn tại (FileNotFoundError)
#
# ensure_data_dir(dir_path: Path) -> None
#   - Tạo thư mục data/ nếu chưa có
#
# TODO: Implement file management functions
# -------------------------------------------------------
# -------------------------------------------------------
# app/utils/file_manager.py
# Quản lý phụ trợ thư mục/file audio tạm (ngoài vòng đời
# tự dọn dẹp đã có sẵn trong audio_service.speech_to_text)
# -------------------------------------------------------
import logging
import shutil
from pathlib import Path
from typing import Union

from app.core.config import settings

logger = logging.getLogger(__name__)


def ensure_data_dir(dir_path: Union[str, Path, None] = None) -> Path:
    """
    Tạo thư mục lưu trữ dữ liệu tạm nếu chưa tồn tại.
    Mặc định dùng settings.AUDIO_DOWNLOAD_DIR nếu không truyền dir_path.
    """
    path = Path(dir_path) if dir_path is not None else Path(settings.AUDIO_DOWNLOAD_DIR)
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Đã đảm bảo thư mục tồn tại: {path.resolve()}")
    except Exception as e:
        logger.error(f"Không thể tạo thư mục {path}: {e}")
        raise
    return path


def cleanup_audio(file_path: Union[str, Path]) -> None:
    """
    Xóa 1 file audio tạm cụ thể.
    Dùng cho các trường hợp NGOÀI luồng chính (audio_service đã tự dọn trong finally):
      - Script dọn rác định kỳ (cron/scheduler)
      - Xóa file khi admin xóa CallRecord theo id
      - Cleanup thủ công khi debug
    Không raise exception — chỉ log, tránh làm gián đoạn tiến trình gọi nó.
    """
    path = Path(file_path)
    try:
        path.unlink()
        logger.info(f"Đã dọn dẹp file audio tạm: {path}")
    except FileNotFoundError:
        logger.debug(f"File audio tạm không tồn tại (có thể đã bị xóa trước đó): {path}")
    except Exception as e:
        logger.warning(f"Xóa file audio tạm thất bại ({path}): {e}")


def cleanup_orphaned_files(max_age_hours: int = 24) -> int:
    """
    Quét settings.AUDIO_DOWNLOAD_DIR, xóa các file tồn tại lâu hơn max_age_hours.
    Dùng cho trường hợp process bị crash/kill giữa chừng khiến khối `finally`
    trong speech_to_text() không kịp chạy, để lại file rác vĩnh viễn.
    Trả về số lượng file đã xóa. Nên gọi định kỳ (cron job hoặc APScheduler).
    """
    import time

    download_dir = ensure_data_dir()
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    removed_count = 0

    for item in download_dir.iterdir():
        if not item.is_file():
            continue
        try:
            file_age = now - item.stat().st_mtime
            if file_age > max_age_seconds:
                item.unlink()
                removed_count += 1
                logger.info(f"Đã dọn file rác quá hạn ({file_age/3600:.1f}h): {item}")
        except Exception as e:
            logger.warning(f"Không thể kiểm tra/xóa file {item}: {e}")

    if removed_count:
        logger.info(f"Cleanup định kỳ hoàn tất: đã xóa {removed_count} file rác trong {download_dir}")
    return removed_count


def cleanup_dir(dir_path: Union[str, Path], remove_root: bool = False) -> None:
    """
    Dọn dẹp nội dung một thư mục (nhiều file trung gian). remove_root=True
    sẽ xóa luôn cả thư mục gốc sau khi dọn.
    """
    path = Path(dir_path)
    if not path.exists():
        logger.debug(f"Thư mục không tồn tại, bỏ qua dọn dẹp: {path}")
        return

    try:
        if remove_root:
            shutil.rmtree(path)
            logger.info(f"Đã xóa toàn bộ thư mục: {path}")
        else:
            for item in path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            logger.info(f"Đã dọn dẹp nội dung bên trong thư mục: {path}")
    except Exception as e:
        logger.warning(f"Dọn dẹp thư mục thất bại ({path}): {e}")