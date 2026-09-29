"""Test cho §5. Không cần mạng, không cần DB — chạy bằng python hệ thống."""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from musmemo.models import (  # noqa: E402
    CARDIO, DONE, KHONG_TA, LOWER, SKIPPED, SWAPPED, TA_DON, UPPER,
    HoSo, Session, Video,
)
from musmemo.schedule import chon_bai, so_ngay_nghi, xu_ly_nghi  # noqa: E402

T2 = date(2026, 9, 21)   # thứ Hai -> LOWER theo MAU_TUAN
T4 = date(2026, 9, 23)   # thứ Tư  -> UPPER
CN = date(2026, 9, 27)   # Chủ nhật -> nghỉ


def v(i, nhom=LOWER, cd=3, dung_cu=TA_DON, phut=30, sid=None, sord=None):
    return Video(id=i, youtube_id="y%d" % i, tieu_de="V%d" % i, kenh="K",
                 thoi_luong_giay=phut * 60, nhom_co=nhom, cuong_do=cd,
                 dung_cu=dung_cu, series_id=sid, series_order=sord)


def pool_day_du():
    p = []
    for i, nhom in enumerate([LOWER, UPPER, CARDIO], start=1):
        for k in range(4):
            p.append(v(i * 10 + k, nhom=nhom, phut=28 + k))
            p.append(v(i * 100 + k, nhom=nhom, dung_cu=KHONG_TA, phut=25 + k))
    return p


def test_ngay_nghi_va_thang_quay_lai():
    assert xu_ly_nghi(1, 5) == (5, "binh_thuong", False)
    assert xu_ly_nghi(10, 5) == (4, "ha_mot_bac", False)
    assert xu_ly_nghi(20, 5) == (3, "ve_ramp_tuan_1_2", False)
    assert xu_ly_nghi(40, 5)[2] is True          # reset mốc 0

    ls = [Session(ngay=T2 - timedelta(days=9), trang_thai=DONE, nhom_co=LOWER)]
    assert so_ngay_nghi(ls, T2) == 9


def test_swapped_van_tinh_la_co_tap():
    """§7 — bấm 'không có tạ' không được phá streak."""
    ls = [Session(ngay=T2 - timedelta(days=1), trang_thai=SWAPPED, nhom_co=UPPER)]
    assert so_ngay_nghi(ls, T2) == 1
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool_day_du(), ls)
    assert "NT-2" not in kh.ly_do          # NT-2 không được kích hoạt


def test_nt2_ghi_de_khi_hom_qua_bo_tap():
    ls = [Session(ngay=T2 - timedelta(days=1), trang_thai=SKIPPED)]
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool_day_du(), ls)
    assert kh.ngan_sach_phut == 15
    assert kh.tran_cuong_do <= 2
    assert "NT-2" in kh.ly_do


def test_luat_0_khoa_series():
    pool = pool_day_du() + [v(900, sid=7, sord=1), v(901, sid=7, sord=2)]
    ls = [Session(ngay=T2 - timedelta(days=2), trang_thai=DONE, video_id=900,
                  nhom_co=LOWER, series_id=7, series_order=1)]
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool, ls)
    assert kh.video.id == 901
    assert "Luật 0" in kh.ly_do


def test_nt2_thang_ca_luat_0():
    """Rule text §5: chỉ NT-2 mới được ghi đè Luật 0."""
    pool = pool_day_du() + [v(900, sid=7, sord=1), v(901, sid=7, sord=2)]
    ls = [Session(ngay=T2 - timedelta(days=1), trang_thai=SKIPPED, video_id=900,
                  nhom_co=LOWER, series_id=7, series_order=1)]
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool, ls)
    assert kh.video is None or kh.video.id != 901
    assert "NT-2" in kh.ly_do


def test_tran_cuong_do_thang_ca_series():
    """NT-5 là luật an toàn: trần chặn cả bài kế tiếp của series."""
    pool = pool_day_du() + [v(900, sid=7, sord=1), v(901, sid=7, sord=2, cd=5)]
    ls = [Session(ngay=T2 - timedelta(days=2), trang_thai=DONE, video_id=900,
                  nhom_co=LOWER, series_id=7, series_order=1)]
    kh = chon_bai(T2, HoSo(tran_cuong_do=3), pool, ls)
    assert kh.video is None or kh.video.id != 901


def test_khong_lap_video_trong_21_ngay():
    pool = [v(1), v(2)]
    ls = [Session(ngay=T2 - timedelta(days=3), trang_thai=DONE, video_id=1, nhom_co=UPPER)]
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool, ls)
    assert kh.video.id == 2


def test_luon_co_ba_loi_thoat():
    pool = pool_day_du() + [v(777, nhom=LOWER, cd=1, phut=15)]   # bài nhẹ để thoát
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool, [])
    assert set(kh.loi_thoat) == {"khong_co_ta", "nhe_hon", "chay_thay"}
    assert kh.loi_thoat["khong_co_ta"].dung_cu == KHONG_TA


def test_loi_thoat_khong_bao_gio_trung_bai_chinh():
    """Một lối thoát trỏ về đúng bài đang hiện là vô nghĩa và làm mất tin tưởng."""
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool_day_du(), [])
    assert kh.video is not None
    assert all(alt.id != kh.video.id for alt in kh.loi_thoat.values())


def test_ngay_cardio_khong_doi_ta_va_khong_chao_chay_thay():
    """Ngày cardio vốn không dùng tạ; 'chạy thay' cũng không phải lựa chọn khác."""
    T7 = date(2026, 9, 26)                       # thứ Bảy -> cardio
    kh = chon_bai(T7, HoSo(tran_cuong_do=5), pool_day_du(), [])
    assert kh.video is not None and kh.video.dung_cu == KHONG_TA
    assert "chay_thay" not in kh.loi_thoat
    assert "khong_co_ta" not in kh.loi_thoat
    assert not kh.noi_long, "ngày cardio không được phải nới lỏng luật"


def test_khong_bao_gio_tra_ve_rong_im_lang():
    """§5 luật 8 — pool cạn thì phải nới lỏng, và phải nói ra là đã nới."""
    pool = [v(1, nhom=LOWER)]
    ls = [Session(ngay=T2 - timedelta(days=1), trang_thai=DONE, video_id=1, nhom_co=LOWER)]
    kh = chon_bai(T2, HoSo(tran_cuong_do=5), pool, ls)
    assert kh.noi_long, "phải ghi lại là đã nới lỏng luật"


def test_chu_nhat_la_ngay_nghi():
    kh = chon_bai(CN, HoSo(), pool_day_du(), [])
    assert kh.video is None and kh.loai_buoi == "nghi"
