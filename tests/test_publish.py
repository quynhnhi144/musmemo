"""Test cho phần thuần của ingest.py và publish.py — không chạm mạng."""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from musmemo.ingest import giay_tu_iso8601, series_id_tu_ten          # noqa: E402
from musmemo.models import (  # noqa: E402
    DONE, KHONG_TA, LOWER, SKIPPED, SWAPPED, TA_DON, HoSo, Session, Video,
)
from musmemo.progression import Lift                                   # noqa: E402
from musmemo.publish import (  # noqa: E402
    mo_ta_event, tai_de_xuat, tinh_streak, tom_tat_event,
)
from musmemo.schedule import chon_bai                                  # noqa: E402

T4 = date(2026, 9, 23)   # thứ Tư  -> mẫu tuần: thân trên
T2 = date(2026, 9, 21)   # thứ Hai -> mẫu tuần: thân dưới


def v(i, nhom=LOWER, cd=3, dung_cu=TA_DON, phut=30):
    return Video(id=i, youtube_id="yt%d" % i, tieu_de="Bài %d" % i, kenh="Kênh",
                 thoi_luong_giay=phut * 60, nhom_co=nhom, cuong_do=cd, dung_cu=dung_cu)


# --- ingest -----------------------------------------------------------------
def test_doc_thoi_luong_iso8601():
    assert giay_tu_iso8601("PT32M10S") == 1930
    assert giay_tu_iso8601("PT1H2M3S") == 3723
    assert giay_tu_iso8601("") == 0 and giay_tu_iso8601("hỏng") == 0


def test_series_id_on_dinh_qua_cac_lan_chay():
    """Không dùng hash() của Python vì nó đổi mỗi tiến trình."""
    assert series_id_tu_ten("EPIC Heat") == series_id_tu_ten("epic  heat")
    assert series_id_tu_ten(None) is None
    assert series_id_tu_ten("EPIC Heat") != series_id_tu_ten("EPIC Fire")


# --- streak -----------------------------------------------------------------
def test_streak_dem_ngay_lien_tiep():
    ls = [Session(ngay=T4 - timedelta(days=i), trang_thai=DONE) for i in range(3)]
    assert tinh_streak(ls, T4) == 3


def test_swapped_khong_pha_streak():
    ls = [Session(ngay=T4, trang_thai=SWAPPED),
          Session(ngay=T4 - timedelta(days=1), trang_thai=DONE)]
    assert tinh_streak(ls, T4) == 2


def test_skipped_lam_dut_streak():
    ls = [Session(ngay=T4, trang_thai=DONE),
          Session(ngay=T4 - timedelta(days=1), trang_thai=SKIPPED),
          Session(ngay=T4 - timedelta(days=2), trang_thai=DONE)]
    assert tinh_streak(ls, T4) == 1


def test_chu_nhat_khong_cong_nhung_cung_khong_dut():
    cn = date(2026, 9, 20)                      # chủ nhật
    ls = [Session(ngay=cn - timedelta(days=1), trang_thai=DONE),
          Session(ngay=cn + timedelta(days=1), trang_thai=DONE)]
    assert tinh_streak(ls, cn + timedelta(days=1)) == 2


def test_chua_co_lich_su_thi_streak_bang_0():
    assert tinh_streak([], T4) == 0


# --- nội dung event ---------------------------------------------------------
def test_event_co_link_muc_ta_va_loi_thoat():
    pool = [v(i) for i in range(1, 4)] + [v(9, dung_cu=KHONG_TA)]
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool, [])   # thứ Hai = thân dưới
    tai = tai_de_xuat(LOWER, [Lift(date(2026, 9, 1), "rdl", 14.0),
                              Lift(date(2026, 9, 8), "rdl", 14.0)], 30.0)
    html = mo_ta_event(kh, tai, streak=5, ngay_thu=6, tong_ngay=14)

    assert "youtube.com/watch?v=" in html
    assert "16 kg" in html                      # 14 -> 16 theo luật §6
    assert "Ngày 6/14" in html and "🔥 5 ngày" in html
    assert "Không có tạ" in html                # lối thoát bodyweight
    assert kh.ly_do in html                     # luôn giải thích được vì sao


def test_event_khong_im_lang_khi_khong_chon_duoc_bai():
    """§5 luật 8 — thà báo rõ còn hơn gửi một event trống."""
    kh = chon_bai(T4, HoSo(), [], [])
    html = mo_ta_event(kh, [], streak=0)
    assert "chưa chọn được bài" in html
    assert "ingest" in html                     # nói luôn cách sửa
    assert "chưa chọn" in tom_tat_event(kh)


def test_cham_tran_30kg_thi_event_noi_ro():
    tai = tai_de_xuat(LOWER, [Lift(date(2026, 9, 1), "squat", 29.0),
                              Lift(date(2026, 9, 8), "squat", 29.0)], 30.0)
    squat = [t for t in tai if t.bai_tap == "squat"][0]
    assert squat.bac >= 2 and "trần" in squat.ly_do
