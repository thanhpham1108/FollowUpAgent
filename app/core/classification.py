"""Canonical recruitment reason codes and their workflow mapping."""

from enum import Enum


class ReasonCode(str, Enum):
    TU_CHOI_LUON = "TU_CHOI_LUON"
    KNM_DAP_MAY = "KNM_DAP_MAY"
    SAI_SO_NHAM_SO = "SAI_SO_NHAM_SO"
    KHACH_BAN = "KHACH_BAN"
    CUOC_GOI_RONG = "CUOC_GOI_RONG"
    LOI_AM_THANH = "LOI_AM_THANH"
    SUY_NGHI_THEM = "SUY_NGHI_THEM"
    CHUA_CHOT_NGAY = "CHUA_CHOT_NGAY"
    CHO_GIAY_TO = "CHO_GIAY_TO"
    HEN_XA = "HEN_XA"
    HEN_PHONG_VAN = "HEN_PHONG_VAN"
    DI_LAM = "DI_LAM"

    def __str__(self) -> str:
        return self.value


class CallDecision(str, Enum):
    NO_CALL = "NO_CALL"
    CALL_BACK = "CALL_BACK"
    FOLLOW_UP = "FOLLOW_UP"
    SCHEDULED = "SCHEDULED"
    SUCCESS = "SUCCESS"

    def __str__(self) -> str:
        return self.value


REASON_CODE_GROUP = {
    ReasonCode.TU_CHOI_LUON: 1,
    ReasonCode.KNM_DAP_MAY: 1,
    ReasonCode.SAI_SO_NHAM_SO: 1,
    ReasonCode.KHACH_BAN: 2,
    ReasonCode.CUOC_GOI_RONG: 2,
    ReasonCode.LOI_AM_THANH: 2,
    ReasonCode.SUY_NGHI_THEM: 3,
    ReasonCode.CHUA_CHOT_NGAY: 3,
    ReasonCode.CHO_GIAY_TO: 3,
    ReasonCode.HEN_XA: 3,
    ReasonCode.HEN_PHONG_VAN: 4,
    ReasonCode.DI_LAM: 5,
}

GROUP_CALL_DECISION = {
    1: "NO_CALL",
    2: "CALL_BACK",
    3: "FOLLOW_UP",
    4: "SCHEDULED",
    5: "SUCCESS",
}


def reason_codes_for_group(group: int) -> tuple[ReasonCode, ...]:
    return tuple(code for code, code_group in REASON_CODE_GROUP.items() if code_group == group)
