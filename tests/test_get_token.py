import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from musmemo.get_token import SCOPES, dat_token_vao_dotenv, thieu_scope  # noqa: E402


def test_cap_du_scope_thi_khong_thieu_gi():
    assert thieu_scope(list(SCOPES)) == []


def test_bo_tick_gmail_thi_bao_thieu():
    chi_calendar = [s for s in SCOPES if "gmail" not in s]
    assert thieu_scope(chi_calendar) == [s for s in SCOPES if "gmail" in s]


def test_khong_co_scope_nao_thi_thieu_het():
    assert thieu_scope(None) == list(SCOPES)


def test_va_token_thay_dong_cu_va_giu_phan_con_lai():
    cu = "YOUTUBE_API_KEY=abc\nGOOGLE_REFRESH_TOKEN=token_cu\nGOOGLE_CALENDAR_ID=primary\n"
    moi = dat_token_vao_dotenv(cu, "token_moi")
    assert "GOOGLE_REFRESH_TOKEN=token_moi" in moi
    assert "token_cu" not in moi
    assert "YOUTUBE_API_KEY=abc" in moi
    assert "GOOGLE_CALENDAR_ID=primary" in moi


def test_va_token_them_moi_khi_chua_co_dong_nao():
    moi = dat_token_vao_dotenv("YOUTUBE_API_KEY=abc\n", "token_moi")
    assert moi.splitlines() == ["YOUTUBE_API_KEY=abc", "GOOGLE_REFRESH_TOKEN=token_moi"]


def test_va_token_vao_file_rong():
    assert dat_token_vao_dotenv("", "t") == "GOOGLE_REFRESH_TOKEN=t\n"
