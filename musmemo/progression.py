"""§6 — tăng tải và bậc thang khi chạm trần tạ."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

THAN_DUOI = {"squat", "hip_thrust", "rdl", "lunge"}
THAN_TREN = {"press", "row"}

BUOC_NHAY = {"duoi": 2.0, "tren": 1.0}

BAC = {
    1: "them_ky",
    2: "don_phuong",       # Bulgarian split squat, RDL một chân…
    3: "tempo",            # hạ chậm 3 giây, dừng 2 giây
    4: "them_rep",         # 8 → 12 rep, nghỉ 90 → 60 giây
}


@dataclass(frozen=True)
class Lift:
    ngay: object
    bai_tap: str
    kg: float
    qua_nang: bool = False


@dataclass
class DeXuat:
    bai_tap: str
    kg: float
    bac: int
    ly_do: str


def _buoc(bai_tap: str) -> float:
    return BUOC_NHAY["duoi"] if bai_tap in THAN_DUOI else BUOC_NHAY["tren"]


def de_xuat(bai_tap: str, lich_su: Sequence[Lift], tran_kg: float = 30.0) -> DeXuat:
    """Mức tạ cho buổi tới.

    Luật: hai buổi liên tiếp cùng mức mà không báo "quá nặng" thì tăng một bước.
    Báo quá nặng thì giữ nguyên thêm hai buổi rồi mới thử lại.
    """
    cua_bai = [l for l in lich_su if l.bai_tap == bai_tap]
    cua_bai.sort(key=lambda l: l.ngay)

    if not cua_bai:
        return DeXuat(bai_tap, 0.0, 1, "Lần đầu — chọn mức bạn thấy nhẹ, rồi ghi lại.")

    hien_tai = cua_bai[-1].kg
    buoc = _buoc(bai_tap)

    if cua_bai[-1].qua_nang:
        return DeXuat(bai_tap, hien_tai, 1,
                      "Buổi trước bạn báo quá nặng — giữ nguyên {:g} kg.".format(hien_tai))

    # Đã chạm trần: không thêm ký nữa, leo sang bậc kế tiếp.
    if hien_tai + buoc > tran_kg:
        bac = 2 if len(cua_bai) < 6 else (3 if len(cua_bai) < 12 else 4)
        return DeXuat(bai_tap, tran_kg, bac,
                      "Đã chạm trần {:g} kg — chuyển sang {}.".format(tran_kg, BAC[bac]))

    hai_buoi_cung_muc = len(cua_bai) >= 2 and cua_bai[-2].kg == hien_tai
    if hai_buoi_cung_muc:
        return DeXuat(bai_tap, hien_tai + buoc, 1,
                      "Hai buổi liền ở {:g} kg — thử {:g} kg.".format(hien_tai, hien_tai + buoc))
    return DeXuat(bai_tap, hien_tai, 1,
                  "Mới đổi mức tuần trước — ở lại {:g} kg thêm một buổi.".format(hien_tai))
