import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from musmemo.collect import (  # noqa: E402
    lifts_cua_buoi, rsvp_cua_minh, suy_trang_thai,
)
from musmemo.models import DONE, LOWER, SKIPPED, SWAPPED  # noqa: E402
from musmemo.progression import Lift  # noqa: E402


def EV(rsvp, **them):
    """Event Calendar tối thiểu, với chính chủ lịch là khách."""
    ev = {"attendees": [{"email": "toi@gmail.com", "self": True,
                         "responseStatus": rsvp}]}
    ev.update(them)
    return ev


# --- đọc RSVP ---------------------------------------------------------------
def test_lay_dung_khach_la_chinh_minh():
    ev = {"attendees": [
        {"email": "nguoi_khac@gmail.com", "responseStatus": "declined"},
        {"email": "toi@gmail.com", "self": True, "responseStatus": "accepted"},
    ]}
    assert rsvp_cua_minh(ev) == "accepted"


def test_event_khong_co_khach_thi_coi_nhu_chua_tra_loi():
    # Không có khách thì Calendar không hiện nút RSVP để mà bấm.
    assert rsvp_cua_minh({}) == "needsAction"
    assert rsvp_cua_minh({"attendees": []}) == "needsAction"


def test_khach_chua_co_response_status():
    assert rsvp_cua_minh({"attendees": [{"self": True}]}) == "needsAction"


# --- ba nút RSVP → ba trạng thái §4 -----------------------------------------
def test_bam_co_la_da_tap():
    assert suy_trang_thai(EV("accepted")) == (DONE, None)


def test_bam_khong_la_bo_tap():
    assert suy_trang_thai(EV("declined")) == (SKIPPED, None)


def test_bam_co_the_la_doi_bai_khong_phai_bo():
    # Bất biến #3: swapped ≠ skipped — vẫn tính là có mặt.
    trang_thai, ly_do = suy_trang_thai(EV("tentative"))
    assert trang_thai == SWAPPED
    assert ly_do == "doi_bai"


def test_khong_bam_gi_thi_khong_bi_tinh_la_bo_tap():
    # QĐ-18: im lặng không được phép làm đứt streak hay kích hoạt NT-2.
    trang_thai, ly_do = suy_trang_thai(EV("needsAction"))
    assert trang_thai == SWAPPED
    assert ly_do == "khong_tra_loi"


def test_xoa_event_la_bo_tap():
    assert suy_trang_thai(None) == (SKIPPED, "da_xoa_event")
    assert suy_trang_thai(EV("accepted", status="cancelled")) == (SKIPPED, "da_xoa_event")


def test_response_status_la_gia_tri_la_thi_khong_doan_bua():
    trang_thai, _ = suy_trang_thai(EV("bogus"))
    assert trang_thai == SWAPPED      # rơi về nhánh an toàn, không phải skipped


# --- ghi lifts --------------------------------------------------------------
def test_buoi_dau_tien_chua_biet_muc_nao_thi_khong_ghi_gi():
    # de_xuat trả 0 kg cho lần đầu — không ghi dòng lifts nào cho đỡ nhiễu.
    assert lifts_cua_buoi(date(2026, 10, 12), LOWER, [], 30.0) == []


def test_ghi_dung_muc_da_ke():
    lich_su = [Lift(date(2026, 10, 1), "squat", 20.0),
               Lift(date(2026, 10, 8), "squat", 20.0)]
    ra = lifts_cua_buoi(date(2026, 10, 12), LOWER, lich_su, 30.0)
    squat = [l for l in ra if l.bai_tap == "squat"]
    assert len(squat) == 1
    assert squat[0].kg == 22.0          # §6: hai buổi cùng mức thì tăng 2 kg
    assert squat[0].ngay == date(2026, 10, 12)
    assert squat[0].qua_nang is False


def test_ngay_cardio_khong_co_nhom_co_thi_khong_ghi_lifts():
    assert lifts_cua_buoi(date(2026, 10, 12), None, [], 30.0) == []


def test_khong_vuot_tran_ta():
    lich_su = [Lift(date(2026, 10, 1), "squat", 30.0),
               Lift(date(2026, 10, 8), "squat", 30.0)]
    ra = lifts_cua_buoi(date(2026, 10, 12), LOWER, lich_su, 30.0)
    assert all(l.kg <= 30.0 for l in ra)
