"""Lấy Google refresh token — chạy tay một lần trên máy local.

Không nằm trong workflow nào. Script mở trình duyệt, bạn đăng nhập và cấp
quyền, rồi nó in ra `GOOGLE_REFRESH_TOKEN` để dán vào `.env` và vào
GitHub Secrets.

    ./.venv/bin/python -m musmemo.get_token
    ./.venv/bin/python -m musmemo.get_token --ghi-env   # ghi thẳng vào .env

Chuẩn bị trước ở https://console.cloud.google.com/apis/credentials:
  1. Bật **Google Calendar API** và **Gmail API** cho project.
  2. Tạo OAuth client loại **Desktop app** (loại này cho phép redirect về
     localhost nên không cần khai báo redirect URI).
  3. Màn hình consent còn ở chế độ Testing thì thêm chính email của bạn vào
     "Test users", nếu không Google sẽ chặn ở bước đăng nhập.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from . import config

CAN = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]

#: Xin một lần cho cả ba script có gọi Google — để chỉ phải cấp quyền một lần.
#: calendar.events  publish tạo event (§3), collect đọc lại trạng thái
#: gmail.send       digest gửi email tổng kết chủ nhật (§7)
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.send",
]

_DOTENV = Path(__file__).resolve().parent.parent / ".env"


# --- Hàm thuần --------------------------------------------------------------
def thieu_scope(da_cap: Optional[List[str]]) -> List[str]:
    """Scope đã xin nhưng người dùng không cấp.

    Màn hình consent của Google cho phép bỏ tick từng quyền. Thiếu
    `gmail.send` thì `digest.py` sẽ hỏng, mà lỗi chỉ lộ ra vào chủ nhật —
    nên phát hiện ngay tại đây.
    """
    co = set(da_cap or [])
    return [s for s in SCOPES if s not in co]


def dat_token_vao_dotenv(noi_dung: str, token: str) -> str:
    """Thay giá trị GOOGLE_REFRESH_TOKEN trong .env, giữ nguyên phần còn lại."""
    dong_moi, thay = [], False
    for dong in noi_dung.splitlines():
        if dong.strip().startswith("GOOGLE_REFRESH_TOKEN="):
            dong_moi.append("GOOGLE_REFRESH_TOKEN=" + token)
            thay = True
        else:
            dong_moi.append(dong)
    if not thay:
        dong_moi.append("GOOGLE_REFRESH_TOKEN=" + token)
    return "\n".join(dong_moi) + "\n"


# --- OAuth ------------------------------------------------------------------
def _luong_oauth():
    from google_auth_oauthlib.flow import InstalledAppFlow

    cau_hinh = {
        "installed": {
            "client_id": config.lay("GOOGLE_CLIENT_ID"),
            "client_secret": config.lay("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    return InstalledAppFlow.from_client_config(cau_hinh, scopes=SCOPES)


# --- Điểm vào ---------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if not config.bat_buoc(*CAN):
        print("Tạo OAuth client loại 'Desktop app' rồi điền hai biến trên vào .env — "
              "xem hướng dẫn ở đầu file này.")
        return 0

    try:
        luong = _luong_oauth()
    except ImportError:
        print('[musmemo] thiếu thư viện OAuth — chạy: pip install -e ".[auth]"')
        return 1

    print("[musmemo] đang mở trình duyệt để cấp quyền…")
    # access_type=offline + prompt=consent là bắt buộc: thiếu thì Google chỉ trả
    # access token ngắn hạn, và những lần cấp quyền sau sẽ KHÔNG kèm refresh token.
    cred = luong.run_local_server(port=0, access_type="offline", prompt="consent")

    if not cred.refresh_token:
        print("[musmemo] Google không trả refresh token. Vào "
              "https://myaccount.google.com/permissions gỡ quyền của app rồi chạy lại.")
        return 1

    thieu = thieu_scope(cred.scopes)
    if thieu:
        print("[musmemo] CẢNH BÁO — chưa cấp đủ quyền: " + ", ".join(thieu))
        print("           Chạy lại và tick hết các ô ở màn hình consent.")

    if "--ghi-env" in argv:
        cu = _DOTENV.read_text(encoding="utf-8") if _DOTENV.exists() else ""
        _DOTENV.write_text(dat_token_vao_dotenv(cu, cred.refresh_token), encoding="utf-8")
        print("[musmemo] đã ghi GOOGLE_REFRESH_TOKEN vào .env")
    else:
        print("\nGOOGLE_REFRESH_TOKEN=" + cred.refresh_token + "\n")

    print("Còn một bước nữa: thêm đúng giá trị đó vào GitHub →")
    print("  Settings → Secrets and variables → Actions → GOOGLE_REFRESH_TOKEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
