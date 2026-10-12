import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from musmemo.ingest import (  # noqa: E402
    KENH_MAC_DINH, chuan_hoa_handle, giay_tu_iso8601, series_id_tu_ten,
)


def test_handle_da_dung_thi_giu_nguyen():
    assert chuan_hoa_handle("@EmiWong") == "@EmiWong"


def test_handle_thieu_cham_thi_them_vao():
    assert chuan_hoa_handle("EmiWong") == "@EmiWong"


def test_dan_ca_link_kenh_cung_duoc():
    assert chuan_hoa_handle("https://www.youtube.com/@CarolineGirvan") == "@CarolineGirvan"
    assert chuan_hoa_handle("https://www.youtube.com/@PamelaRf1/") == "@PamelaRf1"


def test_handle_co_khoang_trang_thua():
    assert chuan_hoa_handle("  @EmiWong  ") == "@EmiWong"


def test_sau_kenh_mac_dinh_deu_hop_le():
    assert len(KENH_MAC_DINH) == 6
    assert all(h == chuan_hoa_handle(h) for h in KENH_MAC_DINH)
    assert len(set(KENH_MAC_DINH)) == 6        # không trùng


def test_doc_thoi_luong_iso8601():
    assert giay_tu_iso8601("PT32M10S") == 1930
    assert giay_tu_iso8601("PT1H2M3S") == 3723
    assert giay_tu_iso8601("rác") == 0


def test_series_id_on_dinh_qua_cac_lan_chay():
    # Bẫy đã gặp: hash() của Python đổi mỗi tiến trình, crc32 thì không.
    assert series_id_tu_ten("EPIC Heat") == series_id_tu_ten("  epic   heat ")
    assert series_id_tu_ten(None) is None
