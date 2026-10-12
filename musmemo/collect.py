"""§3 Collector — đọc lại event đã qua, suy ra đã tập hay không.

Chạy 12:00 mỗi trưa, sau buổi 06:00 sáu tiếng. Nguồn sự thật là **RSVP** mà
người dùng bấm ngay trong event Calendar — xem QĐ-16. Phần suy luận là hàm
thuần (có test); phần gọi Google API nằm tách ở cuối file.
"""
from __future__ import annotations

import datetime as dt
import sys
from typing import Dict, List, Optional, Sequence, Tuple

from . import config
from .db import ket_noi, khoi_tao
from .models import DONE, SKIPPED, SWAPPED
from .progression import Lift
from .publish import tai_de_xuat

CAN = ["GOOGLE_REFRESH_TOKEN", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]

#: §7 — ba nút Google dựng sẵn trong event khớp đúng ba trạng thái của §4.
#: Không phải trùng hợp may mắn: đó là lý do QĐ-16 chọn RSVP thay vì đổi màu.
THEO_RSVP: Dict[str, Tuple[str, Optional[str]]] = {
    "accepted":    (DONE,    None),
    "declined":    (SKIPPED, None),
    "tentative":   (SWAPPED, "doi_bai"),
    # Không bấm gì cả — xem QĐ-18. Coi là có mặt (giữ streak, không kích hoạt
    # NT-2) nhưng không ghi `lifts`, nên tải cũng không tự tăng.
    "needsAction": (SWAPPED, "khong_tra_loi"),
}

#: Event bị xoá khỏi lịch. Xoá hẳn một buổi tập là tín hiệu bỏ rõ ràng hơn
#: cả việc bấm "Không".
DA_XOA = (SKIPPED, "da_xoa_event")


# --- Hàm thuần, có test -----------------------------------------------------
def rsvp_cua_minh(event: Dict) -> str:
    """Lấy `responseStatus` của chính chủ lịch trong một event Calendar.

    Google đánh dấu `self: true` cho đúng một khách — là bản sao event nằm trên
    lịch của người đang gọi API. Event không có khách nào thì coi như chưa trả
    lời, vì khi đó Calendar không hiện nút RSVP để mà bấm.
    """
    for khach in event.get("attendees") or []:
        if khach.get("self"):
            return khach.get("responseStatus") or "needsAction"
    return "needsAction"


def suy_trang_thai(event: Optional[Dict]) -> Tuple[str, Optional[str]]:
    """(trang_thai, ly_do_doi) từ một event — hoặc từ việc nó đã biến mất."""
    if event is None or event.get("status") == "cancelled":
        return DA_XOA
    return THEO_RSVP.get(rsvp_cua_minh(event), THEO_RSVP["needsAction"])


def lifts_cua_buoi(
    ngay: dt.date, nhom_co: Optional[str], lich_su: Sequence[Lift], tran_kg: float,
) -> List[Lift]:
    """Mức tạ ghi lại cho một buổi đã tập.

    Chưa có form nhập tay (§11 câu 04 còn treo), nên mặc định là **ghi đúng mức
    đã kê**: người dùng mở event ra thấy "Hip thrust 20 kg" rồi bấm "Có" thì
    coi như đã nâng 20 kg. Không ghi gì thì `lifts` rỗng vĩnh viễn và §6 nằm
    chết — hệ thống không bao giờ tăng tải được.

    Sai số tự chữa: kê quá nặng thì buổi sau người dùng báo `qua_nang` và §6
    giữ nguyên mức. Xem QĐ-19.
    """
    if not nhom_co:
        return []
    return [Lift(ngay=ngay, bai_tap=t.bai_tap, kg=t.kg, qua_nang=False)
            for t in tai_de_xuat(nhom_co, lich_su, tran_kg) if t.kg > 0]


# --- Đọc/ghi DB -------------------------------------------------------------
def _buoi_cho_xu_ly(con, den_ngay: dt.date) -> List[Dict]:
    """Mọi buổi còn `planned` tính đến hôm nay, cũ nhất trước.

    Quét cả quá khứ chứ không chỉ hôm qua: job có thể lỡ một ngày vì GitHub
    Actions trễ hoặc máy bạn mất mạng, và buổi bị bỏ sót vẫn phải được chốt.
    """
    sql = ("SELECT ngay, video_id, nhom_co, gcal_event_id FROM sessions "
           "WHERE trang_thai='planned' AND ngay <= ? ORDER BY ngay")
    return [dict(r) for r in con.execute(sql, (den_ngay.isoformat(),))]


def _doc_lifts(con) -> List[Lift]:
    return [Lift(ngay=dt.date.fromisoformat(r["ngay"]), bai_tap=r["bai_tap"],
                 kg=r["kg"], qua_nang=bool(r["qua_nang"]))
            for r in con.execute("SELECT * FROM lifts ORDER BY ngay")]


def _ghi_buoi(con, ngay: str, trang_thai: str, ly_do: Optional[str],
              lifts: Sequence[Lift]) -> None:
    con.execute("UPDATE sessions SET trang_thai=?, ly_do_doi=? WHERE ngay=?",
                (trang_thai, ly_do, ngay))
    for l in lifts:
        con.execute("INSERT INTO lifts (ngay, bai_tap, kg, qua_nang) VALUES (?,?,?,0)",
                    (ngay, l.bai_tap, l.kg))


# --- Google Calendar --------------------------------------------------------
def _dich_vu_calendar():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    cred = Credentials(
        token=None,
        refresh_token=config.lay("GOOGLE_REFRESH_TOKEN"),
        client_id=config.lay("GOOGLE_CLIENT_ID"),
        client_secret=config.lay("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    return build("calendar", "v3", credentials=cred, cache_discovery=False)


def _lay_event(svc, cal: str, eid: str) -> Optional[Dict]:
    """Event, hoặc None nếu đã bị xoá khỏi lịch."""
    from googleapiclient.errors import HttpError
    try:
        return svc.events().get(calendarId=cal, eventId=eid).execute()
    except HttpError as e:
        if e.resp.status in (404, 410):
            return None
        raise


# --- Điểm vào ---------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    chay_thu = "--dry-run" in argv

    if not chay_thu and not config.bat_buoc(*CAN):
        return 0

    con = ket_noi()
    khoi_tao(con)
    hom_nay = dt.date.today()
    cho_xu_ly = _buoi_cho_xu_ly(con, hom_nay)
    if not cho_xu_ly:
        print("[musmemo] không có buổi nào chờ chốt.")
        return 0

    svc = None if chay_thu else _dich_vu_calendar()
    cal = config.lay("GOOGLE_CALENDAR_ID", "primary")
    tran = config.TRAN_TA_KG

    for b in cho_xu_ly:
        ngay = b["ngay"]
        if not b["gcal_event_id"]:
            # Chưa bao giờ lên được Calendar — không có gì để đọc.
            print("[musmemo] %s — bỏ qua, buổi này không có event." % ngay)
            continue

        ev = None if chay_thu else _lay_event(svc, cal, b["gcal_event_id"])
        trang_thai, ly_do = suy_trang_thai(ev)

        lifts: List[Lift] = []
        if trang_thai == DONE:
            lifts = lifts_cua_buoi(dt.date.fromisoformat(ngay), b["nhom_co"],
                                   _doc_lifts(con), tran)

        if chay_thu:
            print("=== %s === %s%s" % (ngay, trang_thai,
                                       " (%s)" % ly_do if ly_do else ""))
            for l in lifts:
                print("    %-12s %g kg" % (l.bai_tap, l.kg))
            continue

        _ghi_buoi(con, ngay, trang_thai, ly_do, lifts)
        con.commit()
        mo_ta = "%s%s" % (trang_thai, " · %s" % ly_do if ly_do else "")
        them = " · ghi %d dòng lifts" % len(lifts) if lifts else ""
        print("[musmemo] %s — %s%s" % (ngay, mo_ta, them))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
