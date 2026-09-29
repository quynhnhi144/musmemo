"""Đọc cấu hình từ biến môi trường (.env local, Secrets trên GitHub Actions)."""
from __future__ import annotations

import os
from pathlib import Path

_DOTENV = Path(__file__).resolve().parent.parent / ".env"
if _DOTENV.exists():  # nạp thủ công để khỏi cần phụ thuộc python-dotenv
    for _dong in _DOTENV.read_text(encoding="utf-8").splitlines():
        _dong = _dong.strip()
        if _dong and not _dong.startswith("#") and "=" in _dong:
            _k, _v = _dong.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.split("#")[0].strip())


def lay(ten: str, mac_dinh: str = "") -> str:
    return os.environ.get(ten, mac_dinh)


def bat_buoc(*ten: str) -> bool:
    """True nếu đủ secrets. Thiếu thì in ra và trả False để script tự bỏ qua."""
    thieu = [t for t in ten if not os.environ.get(t)]
    if thieu:
        print("[musmemo] bỏ qua — chưa cấu hình: " + ", ".join(thieu))
        return False
    return True


TZ = lay("MUSMEMO_TZ", "Asia/Ho_Chi_Minh")
GIO_TAP = lay("MUSMEMO_GIO_TAP", "06:00")
TRAN_TA_KG = float(lay("MUSMEMO_TRAN_TA_KG", "30"))
