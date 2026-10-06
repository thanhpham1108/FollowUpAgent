# -------------------------------------------------------
# app/utils/text_normalizer.py
# Chuẩn hóa transcript STT: sửa các lỗi phát âm / nghe nhầm tên công ty, KCN
# -------------------------------------------------------
import re
from typing import Dict

# Từ điển ánh xạ Regex Pattern -> Tên chuẩn
COMPANY_NAME_PATTERNS: Dict[str, str] = {
    # Vixech (thường bị nghe thành: vi xịt, vi xéc, vi xếch, vi sét, vi xẹp)
    r"\bvi\s+xịt\b": "Vixech",
    r"\bvi\s+xéc\b": "Vixech",
    r"\bvi\s+xếch\b": "Vixech",
    r"\bvi\s+sét\b": "Vixech",
    r"\bvi\s+xẹp\b": "Vixech",
    r"\bví\s+xịt\b": "Vixech",

    # Foxconn
    r"\bfox\s*con\b": "Foxconn",
    r"\bfốc\s*con\b": "Foxconn",

    # Luxshare
    r"\blắc\s*se\b": "Luxshare",
    r"\blắc\s*xe\b": "Luxshare",
    r"\blúc\s*se\b": "Luxshare",
    r"\blux\s*se\b": "Luxshare",

    # Khu công nghiệp phổ biến
    r"\bquang\s+trâu\b": "Quang Châu",
    r"\bvân\s+chung\b": "Vân Trung",
    r"\bquế\s+vỏ\b": "Quế Võ",
}


def normalize_transcript(text: str) -> str:
    """
    Chuẩn hóa các từ bị PhoWhisper nghe nhầm thành tên công ty/KCN chính xác.
    Sử dụng regex case-insensitive (không phân biệt hoa/thường).
    """
    if not text:
        return text

    normalized = text
    for pattern, replacement in COMPANY_NAME_PATTERNS.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    return normalized
