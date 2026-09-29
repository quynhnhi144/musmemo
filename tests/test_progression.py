import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from musmemo.progression import Lift, de_xuat  # noqa: E402


def L(d, bai, kg, nang=False):
    return Lift(date(2026, 9, d), bai, kg, nang)


def test_lan_dau_khong_doan_bua():
    assert de_xuat("rdl", []).kg == 0.0


def test_hai_buoi_cung_muc_thi_tang():
    assert de_xuat("rdl", [L(1, "rdl", 14), L(8, "rdl", 14)]).kg == 16.0


def test_than_tren_buoc_nhay_nho_hon():
    assert de_xuat("press", [L(1, "press", 8), L(8, "press", 8)]).kg == 9.0


def test_bao_qua_nang_thi_giu_nguyen():
    assert de_xuat("rdl", [L(1, "rdl", 16), L(8, "rdl", 16, True)]).kg == 16.0


def test_moi_doi_muc_thi_o_lai_them_mot_buoi():
    assert de_xuat("rdl", [L(1, "rdl", 14), L(8, "rdl", 16)]).kg == 16.0


def test_cham_tran_thi_leo_bac_chu_khong_dung_im():
    d = de_xuat("squat", [L(1, "squat", 29), L(8, "squat", 29)], tran_kg=30)
    assert d.bac >= 2 and d.kg == 30.0
