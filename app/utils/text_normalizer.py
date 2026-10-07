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

    # Foxconn / Hồng Hải
    r"\bfox\s*con\b": "Foxconn",
    r"\bfốc\s*con\b": "Foxconn",
    r"\bhồng\s+hải\s+foxconn\b": "Foxconn",

    # Luxshare
    r"\blắc\s*se\b": "Luxshare",
    r"\blắc\s*xe\b": "Luxshare",
    r"\blúc\s*se\b": "Luxshare",
    r"\blux\s*se\b": "Luxshare",

    # Goertek
    r"\bgô\s+tếch\b": "Goertek",
    r"\bgo\s+tếch\b": "Goertek",
    r"\bgơ\s+tếch\b": "Goertek",
    r"\bgô\s+tẹc\b": "Goertek",

    # Pegatron
    r"\bpê\s+ga\s+tron\b": "Pegatron",
    r"\bpe\s+ga\s+tron\b": "Pegatron",

    # Quanta
    r"\bquang\s+ta\b": "Quanta",
    r"\bquan\s+ta\b": "Quanta",

    # Wistron
    r"\buýt\s+stron\b": "Wistron",
    r"\buýt\s+tron\b": "Wistron",

    # Canon
    r"\bca\s+nông\b": "Canon",
    r"\bcan\s+nông\b": "Canon",

    # Khu công nghiệp & VSIP
    r"\bvi\s+xíp\b": "VSIP",
    r"\bvi\s+sịp\b": "VSIP",
    r"\bquang\s+trâu\b": "Quang Châu",
    r"\bvân\s+chung\b": "Vân Trung",
    r"\bquế\s+vỏ\b": "Quế Võ",
    r"\bđình\s+chám\b": "Đình Trám",
    r"\bđồng\s+văng\b": "Đồng Văn",
    r"\byên\s+phông\b": "Yên Phong",
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
