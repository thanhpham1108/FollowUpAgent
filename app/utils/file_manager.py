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
