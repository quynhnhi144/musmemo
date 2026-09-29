"""§3 Publisher — chọn bài cho sáng mai và tạo event Google Calendar.

Chạy 21:00 mỗi tối. Phần dựng nội dung event là hàm thuần (có test); phần gọi
Google API nằm tách ở cuối file.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from typing import Dict, List, Optional, Sequence

from . import config
from .db import ket_noi, khoi_tao
from .models import CARDIO, FULL, HoSo, KeHoach, LOWER, MOBILITY, Session, UPPER, Video
from .progression import DeXuat, Lift, de_xuat
from .schedule import chon_bai

CAN = ["GOOGLE_REFRESH_TOKEN", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]

#: Đến v1.1 (bảng video_exercises) ta mới biết video hôm nay có động tác nào.
#: Tạm thời kê tải theo nhóm cơ — xem §6.
BAI_THEO_NHOM = {
    LOWER: ["squat", "hip_thrust", "rdl"],
    UPPER: ["press", "row"],
    FULL: ["squat", "press", "row"],
}
TEN_BAI = {"squat": "Squat", "hip_thrust": "Hip thrust", "rdl": "RDL",
           "press": "Đẩy vai", "row": "Chèo", "lunge": "Lunge"}
TEN_NHOM = {LOWER: "Thân dưới", UPPER: "Thân trên", FULL: "Full body",
            CARDIO: "Cardio", MOBILITY: "Giãn cơ"}


# --- Hàm thuần, có test -----------------------------------------------------
def tinh_streak(lich_su: Sequence[Session], den_ngay: dt.date) -> int:
    """Số ngày có mặt liên tiếp, đếm ngược từ `den_ngay`.

    `swapped` vẫn tính là có mặt (§7). Chủ nhật là ngày nghỉ theo lịch nên
    không cộng streak nhưng cũng không làm đứt. Chỉ `skipped` — hoặc một ngày
    thường không có buổi nào — mới đứt chuỗi.
    """
    trang_thai = {s.ngay: s.trang_thai for s in lich_su}
    da_chot = [n for n, t in trang_thai.items()
               if t in ("done", "swapped", "skipped") and n <= den_ngay]
    if not da_chot:
        return 0
    streak, ngay = 0, max(da_chot)
    for _ in range(400):
        tt = trang_thai.get(ngay)
        if tt in ("done", "swapped"):
            streak += 1
        elif tt == "skipped":
            break
        elif ngay.weekday() != 6:      # 6 = chủ nhật
            break
        ngay -= dt.timedelta(days=1)
    return streak


def tai_de_xuat(nhom_co: str, lifts: Sequence[Lift], tran_kg: float) -> List[DeXuat]:
    return [de_xuat(b, lifts, tran_kg) for b in BAI_THEO_NHOM.get(nhom_co, [])]


def _link(v: Video) -> str:
    return "https://www.youtube.com/watch?v=" + v.youtube_id


def mo_ta_event(
    kh: KeHoach, tai: Sequence[DeXuat], streak: int,
    ngay_thu: Optional[int] = None, tong_ngay: Optional[int] = None,
    form_url: str = "",
) -> str:
    """Nội dung mô tả event. Trả HTML — Google Calendar hiển thị được thẻ cơ bản."""
    d: List[str] = []
    dau = []
    if ngay_thu and tong_ngay:
        dau.append("Ngày %d/%d" % (ngay_thu, tong_ngay))
    if streak > 0:
        dau.append("🔥 %d ngày liên tiếp" % streak)
    if dau:
        d.append("<b>" + " · ".join(dau) + "</b>")

    v = kh.video
    if v is None:
        d.append("<b>Hôm nay chưa chọn được bài.</b>")
        d.append(kh.ly_do)
        d.append("Thường là do pool video còn mỏng — thêm vài video rồi chạy lại ingest.")
        return "<br>".join(d)

    d.append("<b>%s — %s</b>" % (TEN_NHOM.get(v.nhom_co, v.nhom_co), v.tieu_de))
    d.append("%s · %d phút · cường độ %d/5" % (v.kenh, v.phut, v.cuong_do))
    d.append('▶ <a href="%s">%s</a>' % (_link(v), _link(v)))

    if tai:
        d.append("")
        d.append("<b>Mức tạ hôm nay</b>")
        for t in tai:
            ten = TEN_BAI.get(t.bai_tap, t.bai_tap)
            kg = "chọn mức thấy nhẹ" if t.kg == 0 else "%g kg" % t.kg
            d.append("&nbsp;&nbsp;%-12s <b>%s</b> — %s" % (ten, kg, t.ly_do))

    lt = kh.loi_thoat or {}
    nhan = [("khong_co_ta", "Không có tạ"), ("nhe_hon", "Nhẹ hơn, 15′"),
            ("chay_thay", "Chạy thay")]
    co = [(t, lt[k]) for k, t in nhan if lt.get(k)]
    if co:
        d.append("")
        d.append("<b>Không hợp hôm nay?</b>")
        for t, alt in co:
            d.append('&nbsp;&nbsp;%s → <a href="%s">%s</a>' % (t, _link(alt), alt.tieu_de))

    d.append("")
    if form_url:
        d.append('Tập xong: <a href="%s">ghi lại mức tạ</a> (15 giây)' % form_url)
    else:
        d.append("Tập xong thì trả lời email tổng kết chủ nhật để ghi mức tạ.")
    d.append("<small>%s</small>" % kh.ly_do)
    if kh.noi_long:
        d.append("<small>Đã nới lỏng luật: %s</small>" % ", ".join(kh.noi_long))
    return "<br>".join(d)


def tom_tat_event(kh: KeHoach) -> str:
    if kh.video is None:
        return "Tập — chưa chọn được bài"
    return "%s — %s" % (TEN_NHOM.get(kh.video.nhom_co, kh.video.nhom_co),
                        kh.video.tieu_de[:60])


# --- Đọc DB -----------------------------------------------------------------
def _doc_ho_so(con) -> HoSo:
    r = con.execute("SELECT * FROM users WHERE id=1").fetchone()
    ns = {}
    try:
        ns = {int(k): int(v) for k, v in json.loads(r["ngan_sach_phut"] or "{}").items()}
    except (ValueError, TypeError):
        pass
    hs = HoSo(gio_tap=r["gio_tap"] or config.GIO_TAP,
              tran_cuong_do=r["tran_cuong_do"] or 3)
    if ns:
        hs.ngan_sach_phut = ns
    if r["tuan_bat_dau"]:
        hs.tuan_bat_dau = dt.date.fromisoformat(r["tuan_bat_dau"])
    return hs


def _doc_pool(con) -> List[Video]:
    return [Video(id=r["id"], youtube_id=r["youtube_id"], tieu_de=r["tieu_de"],
                  kenh=r["kenh"] or "", thoi_luong_giay=r["thoi_luong_giay"],
                  nhom_co=r["nhom_co"], cuong_do=r["cuong_do"], dung_cu=r["dung_cu"],
                  series_id=r["series_id"], series_order=r["series_order"],
                  con_song=bool(r["con_song"]))
            for r in con.execute("SELECT * FROM videos WHERE con_song=1")]


def _doc_lich_su(con) -> List[Session]:
    sql = ("SELECT s.*, v.series_id, v.series_order FROM sessions s "
           "LEFT JOIN videos v ON v.id = s.video_id ORDER BY s.ngay")
    return [Session(ngay=dt.date.fromisoformat(r["ngay"]), trang_thai=r["trang_thai"],
                    video_id=r["video_id"], nhom_co=r["nhom_co"],
                    series_id=r["series_id"], series_order=r["series_order"],
                    ly_do_doi=r["ly_do_doi"])
            for r in con.execute(sql)]


def _doc_lifts(con) -> List[Lift]:
    return [Lift(ngay=dt.date.fromisoformat(r["ngay"]), bai_tap=r["bai_tap"],
                 kg=r["kg"], qua_nang=bool(r["qua_nang"]))
            for r in con.execute("SELECT * FROM lifts ORDER BY ngay")]


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


def _day_len_calendar(kh: KeHoach, hs: HoSo, mo_ta: str, event_cu: Optional[str]) -> str:
    svc = _dich_vu_calendar()
    gio, phut = (int(x) for x in (hs.gio_tap or "06:00").split(":"))
    bat_dau = dt.datetime.combine(kh.ngay, dt.time(gio, phut))
    dai = kh.video.phut if kh.video else kh.ngan_sach_phut
    body = {
        "summary": tom_tat_event(kh),
        "description": mo_ta,
        "start": {"dateTime": bat_dau.isoformat(), "timeZone": config.TZ},
        "end": {"dateTime": (bat_dau + dt.timedelta(minutes=dai)).isoformat(),
                "timeZone": config.TZ},
        "reminders": {"useDefault": False,
                      "overrides": [{"method": "popup", "minutes": 0}]},
    }
    cal = config.lay("GOOGLE_CALENDAR_ID", "primary")
    if event_cu:
        return svc.events().update(calendarId=cal, eventId=event_cu,
                                   body=body).execute()["id"]
    return svc.events().insert(calendarId=cal, body=body).execute()["id"]


# --- Điểm vào ---------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    chay_thu = "--dry-run" in argv

    if not chay_thu and not config.bat_buoc(*CAN):
        return 0

    con = ket_noi()
    khoi_tao(con)
    hs = _doc_ho_so(con)
    pool, lich_su, lifts = _doc_pool(con), _doc_lich_su(con), _doc_lifts(con)
    if not pool:
        print("[musmemo] pool rỗng — chạy `python -m musmemo.ingest` trước.")
        return 0

    mai = dt.date.today() + dt.timedelta(days=1)
    kh = chon_bai(mai, hs, pool, lich_su)
    tai = tai_de_xuat(kh.video.nhom_co, lifts, config.TRAN_TA_KG) if kh.video else []
    streak = tinh_streak(lich_su, mai - dt.timedelta(days=1))

    ngay_thu = tong = None
    if hs.tuan_bat_dau:
        ngay_thu = (mai - hs.tuan_bat_dau).days + 1
        tong = 14 if ngay_thu <= 14 else 30

    mo_ta = mo_ta_event(kh, tai, streak, ngay_thu, tong,
                        config.lay("MUSMEMO_FORM_URL"))

    if chay_thu:
        print("=== %s · %s ===" % (mai.isoformat(), tom_tat_event(kh)))
        print(mo_ta.replace("<br>", "\n").replace("&nbsp;", " "))
        return 0

    cu = con.execute("SELECT gcal_event_id FROM sessions WHERE ngay=?",
                     (mai.isoformat(),)).fetchone()
    eid = _day_len_calendar(kh, hs, mo_ta, cu["gcal_event_id"] if cu else None)
    con.execute(
        "INSERT INTO sessions (ngay, video_id, nhom_co, trang_thai, gcal_event_id) "
        "VALUES (?,?,?,'planned',?) "
        "ON CONFLICT(user_id, ngay) DO UPDATE SET video_id=excluded.video_id, "
        "nhom_co=excluded.nhom_co, gcal_event_id=excluded.gcal_event_id",
        (mai.isoformat(), kh.video.id if kh.video else None,
         kh.video.nhom_co if kh.video else None, eid))
    con.commit()
    print("[musmemo] %s — %s (event %s)" % (mai.isoformat(), tom_tat_event(kh), eid))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
