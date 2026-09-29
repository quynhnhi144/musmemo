"""Kiểu dữ liệu dùng chung. Tên trường bám sát §4 của spec để tra ngược cho dễ."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

# §4 videos.nhom_co
LOWER, UPPER, FULL, CORE, CARDIO, MOBILITY = (
    "lower", "upper", "full", "core", "cardio", "mobility",
)
# §4 videos.dung_cu
KHONG_TA, TA_DON = "none", "dumbbell"
# §4 sessions.trang_thai
PLANNED, DONE, SKIPPED, SWAPPED = "planned", "done", "skipped", "swapped"

#: Nhóm cơ được miễn luật "tránh trùng trong 48h" (§5 luật 5).
MIEN_LUAT_48H = {CORE, MOBILITY}


@dataclass(frozen=True)
class Video:
    id: int
    youtube_id: str
    tieu_de: str
    kenh: str
    thoi_luong_giay: int
    nhom_co: str
    cuong_do: int                      # 1..5
    dung_cu: str                       # KHONG_TA | TA_DON
    series_id: Optional[int] = None    # §4, mới ở 0.2
    series_order: Optional[int] = None
    con_song: bool = True

    @property
    def phut(self) -> int:
        return round(self.thoi_luong_giay / 60)


@dataclass(frozen=True)
class Session:
    """Một dòng lịch sử. `nhom_co` lưu kèm để tra cứu không cần join lại videos."""
    ngay: date
    trang_thai: str
    video_id: Optional[int] = None
    nhom_co: Optional[str] = None
    series_id: Optional[int] = None
    series_order: Optional[int] = None
    ly_do_doi: Optional[str] = None

    @property
    def co_tap(self) -> bool:
        """swapped vẫn tính là có tập — xem §7."""
        return self.trang_thai in (DONE, SWAPPED)


@dataclass
class HoSo:
    """§4 users."""
    gio_tap: str = "06:00"
    tuan_bat_dau: Optional[date] = None
    tran_cuong_do: int = 3
    ngan_sach_phut: Dict[int, int] = field(
        # 0 = thứ Hai … 6 = Chủ nhật
        default_factory=lambda: {0: 32, 1: 22, 2: 40, 3: 15, 4: 45, 5: 40, 6: 0}
    )


@dataclass
class KeHoach:
    """Kết quả của scheduler cho một ngày."""
    ngay: date
    loai_buoi: str
    video: Optional[Video]
    ly_do: str                     # vì sao chọn bài này — hiện trong event, và để debug
    tran_cuong_do: int
    ngan_sach_phut: int
    so_ngay_nghi: int
    xu_ly_nghi: str
    loi_thoat: Dict[str, Optional[Video]] = field(default_factory=dict)
    noi_long: List[str] = field(default_factory=list)
