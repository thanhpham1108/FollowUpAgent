# -------------------------------------------------------
# app/services/llm_service.py
# Giao tiếp với Local LLM (Load model, truyền input)
# -------------------------------------------------------
# Class: LLMService
#
# Methods:
#   load_model()
#     → Load GGUF model qua llama-cpp-python khi startup
#
#   is_ready() -> bool
#     → Kiểm tra model đã load chưa
#
#   async analyze_audio(audio_path: Path, candidate_name: str) -> AnalysisResult
#     1. Đọc file audio
#     2. Tạo prompt từ module prompts/
#     3. Gửi audio + prompt vào Local Multimodal LLM
#     4. Parse JSON response từ model
#     5. Trả về AnalysisResult (summary + recommended_message)
#
# Pattern: Singleton — chỉ 1 instance, giữ trong app.state
#
# Exceptions:
#   - LLMProcessingError : LLM xử lý thất bại
#
# TODO: Implement LLM service
# -------------------------------------------------------
