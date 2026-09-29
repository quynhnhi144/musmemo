"""§5 — chọn bài cho ngày hôm sau.

Hàm `chon_bai` là thuần: nhận trạng thái vào, trả quyết định ra. Không đụng mạng,
không đụng DB. Nhờ vậy toàn bộ luật test được offline trong vài mili giây.

Thứ tự áp dụng (thứ tự CHÍNH LÀ ưu tiên):
    1. Thang quay lại theo số ngày nghỉ  (§8)
    2. NT-2 — hôm qua bỏ tập            (§2)   ← ghi đè được cả Luật 0
    3. Luật 0 — khóa series             (§5)
    4. Lọc → chấm điểm → chọn           (§5 luật 2–7)
    5. Nới lỏng dần nếu rỗng            (§5 luật 8)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from .models import (
    CARDIO, CORE, FULL, KHONG_TA, LOWER, MIEN_LUAT_48H, MOBILITY, SKIPPED,
    TA_DON, UPPER, HoSo, KeHoach, Session, Video,
)

# --- Mẫu tuần §8. 0 = thứ Hai … 6 = Chủ nhật -------------------------------
MAU_TUAN: Dict[int, str] = {
    0: LOWER, 1: CARDIO, 2: UPPER, 3: MOBILITY, 4: FULL, 5: CARDIO, 6: "nghi",
}

CUA_SO_LAP_VIDEO = 21     # §5 luật 4 — không lặp lại video trong 21 ngày
# §5 luật 5 — "48 giờ" quy về ngày: loại nếu nhóm cơ đó đã tập hôm nay hoặc hôm qua.
CUA_SO_NHOM_CO_NGAY = 2
PHUT_BAI_NHE = 15         # NT-2
CUONG_DO_BAI_NHE = 2


# --- Thang quay lại §8 ------------------------------------------------------
def xu_ly_nghi(so_ngay: int, tran_hien_tai: int) -> Tuple[int, str, bool]:
    """Trả (trần cường độ mới, nhãn giải thích, có reset mốc 0 không).

    Bê logic Day Gap của Stryd sang, xem §12.
    """
    if so_ngay <= 2:
        return tran_hien_tai, "binh_thuong", False
    if so_ngay <= 7:
        return tran_hien_tai, "bo_qua_phan_thieu", False
    if so_ngay <= 14:
        return max(1, tran_hien_tai - 1), "ha_mot_bac", False
    if so_ngay <= 28:
        return 3, "ve_ramp_tuan_1_2", False
    return 3, "khoi_dong_lai", True


def so_ngay_nghi(lich_su: Sequence[Session], hom_nay: date) -> int:
    """Số ngày kể từ buổi tập gần nhất. Chưa tập buổi nào -> 0 (ngày đầu tiên)."""
    gan_nhat = max((s.ngay for s in lich_su if s.co_tap), default=None)
    return 0 if gan_nhat is None else (hom_nay - gan_nhat).days


# --- Bộ lọc §5 --------------------------------------------------------------
def _da_dung_gan_day(v: Video, lich_su: Sequence[Session], hom_nay: date) -> bool:
    moc = hom_nay - timedelta(days=CUA_SO_LAP_VIDEO)
    return any(s.video_id == v.id and s.ngay > moc for s in lich_su if s.co_tap)


def _nhom_co_con_moi(v: Video, lich_su: Sequence[Session], hom_nay: date) -> bool:
    if v.nhom_co in MIEN_LUAT_48H:
        return True
    return not any(
        s.nhom_co == v.nhom_co and (hom_nay - s.ngay).days < CUA_SO_NHOM_CO_NGAY
        for s in lich_su if s.co_tap
    )


def _ngay_cuoi_tap_nhom(nhom: str, lich_su: Sequence[Session]) -> Optional[date]:
    ngay = [s.ngay for s in lich_su if s.co_tap and s.nhom_co == nhom]
    return max(ngay) if ngay else None


def _diem(v: Video, lich_su: Sequence[Session], hom_nay: date, ngan_sach: int) -> float:
    """§5 luật 6. Điểm càng cao càng được ưu tiên."""
    cuoi = _ngay_cuoi_tap_nhom(v.nhom_co, lich_su)
    # Nhóm cơ lâu chưa chạm tới thì ưu tiên; chưa từng tập coi như 60 ngày.
    ngay_cu = 60 if cuoi is None else min((hom_nay - cuoi).days, 60)
    diem_nhom = ngay_cu * 2.0
    # Thời lượng càng sát ngân sách càng tốt.
    diem_dai = -abs(v.phut - ngan_sach) * 1.5
    # Kênh bạn ít bấm "đổi bài" thì được cộng điểm.
    doi = sum(1 for s in lich_su if s.ly_do_doi and s.video_id == v.id)
    return diem_nhom + diem_dai - doi * 5.0


def _loc(
    pool: Sequence[Video], nhom_co: str, tran: int, dung_cu: str,
    lich_su: Sequence[Session], hom_nay: date,
    bo_luat_48h: bool = False, cua_so_lap: int = CUA_SO_LAP_VIDEO,
    nhom_mo_rong: Optional[set] = None,
) -> List[Video]:
    nhom_ok = nhom_mo_rong or {nhom_co}
    ra = []
    for v in pool:
        if not v.con_song or v.nhom_co not in nhom_ok:
            continue
        if v.cuong_do > tran or v.dung_cu != dung_cu:
            continue
        moc = hom_nay - timedelta(days=cua_so_lap)
        if any(s.video_id == v.id and s.ngay > moc for s in lich_su if s.co_tap):
            continue
        if not bo_luat_48h and not _nhom_co_con_moi(v, lich_su, hom_nay):
            continue
        ra.append(v)
    return ra


_NHOM_LAN_CAN = {LOWER: {LOWER, FULL}, UPPER: {UPPER, FULL}, FULL: {FULL, LOWER, UPPER}}


def _chon_voi_noi_long(
    pool, nhom_co, tran, dung_cu, lich_su, hom_nay, ngan_sach,
) -> Tuple[Optional[Video], List[str]]:
    """§5 luật 8 — nới lỏng từng bậc, không bao giờ trả về rỗng một cách im lặng."""
    da_noi: List[str] = []
    buoc = [
        dict(),
        dict(bo_luat_48h=True),
        dict(bo_luat_48h=True, cua_so_lap=10),
        dict(bo_luat_48h=True, cua_so_lap=10,
             nhom_mo_rong=_NHOM_LAN_CAN.get(nhom_co, {nhom_co})),
        dict(bo_luat_48h=True, cua_so_lap=0,
             nhom_mo_rong=_NHOM_LAN_CAN.get(nhom_co, {nhom_co})),
    ]
    nhan = ["", "bo_luat_48h", "lap_10_ngay", "nhom_lan_can", "cho_phep_lap_lai"]
    for i, kw in enumerate(buoc):
        ung_vien = _loc(pool, nhom_co, tran, dung_cu, lich_su, hom_nay, **kw)
        if ung_vien:
            if nhan[i]:
                da_noi.append(nhan[i])
            ung_vien.sort(key=lambda v: _diem(v, lich_su, hom_nay, ngan_sach), reverse=True)
            return ung_vien[0], da_noi
        if nhan[i]:
            da_noi.append(nhan[i])
    return None, da_noi


# --- Luật 0 §5 --------------------------------------------------------------
def _tap_ke_tiep_trong_series(
    pool: Sequence[Video], lich_su: Sequence[Session], tran: int,
) -> Optional[Video]:
    gan_nhat = next(
        (s for s in reversed(sorted(lich_su, key=lambda s: s.ngay))
         if s.co_tap and s.series_id is not None), None,
    )
    if gan_nhat is None or gan_nhat.series_order is None:
        return None
    ke_tiep = [
        v for v in pool
        if v.series_id == gan_nhat.series_id
        and v.series_order == gan_nhat.series_order + 1
        and v.con_song
    ]
    if not ke_tiep:
        return None
    v = ke_tiep[0]
    # NT-5 là luật an toàn, không phải luật chấm điểm: trần cường độ thắng cả Luật 0.
    return v if v.cuong_do <= tran else None


# --- Điểm vào ---------------------------------------------------------------
def chon_bai(
    hom_nay: date, ho_so: HoSo, pool: Sequence[Video], lich_su: Sequence[Session],
) -> KeHoach:
    thu = hom_nay.weekday()
    loai = MAU_TUAN[thu]
    ngan_sach = ho_so.ngan_sach_phut.get(thu, 30)

    gap = so_ngay_nghi(lich_su, hom_nay)
    tran, nhan_gap, reset = xu_ly_nghi(gap, ho_so.tran_cuong_do)

    kh = KeHoach(
        ngay=hom_nay, loai_buoi=loai, video=None, ly_do="",
        tran_cuong_do=tran, ngan_sach_phut=ngan_sach,
        so_ngay_nghi=gap, xu_ly_nghi=nhan_gap,
    )
    if reset:
        kh.ly_do = "Nghỉ hơn 28 ngày — khởi động lại từ đầu. "

    if loai == "nghi":
        kh.ly_do += "Chủ nhật: nghỉ và check-in tuần."
        return kh

    # NT-2 ghi đè mọi thứ, kể cả Luật 0.
    hom_qua = next((s for s in lich_su if s.ngay == hom_nay - timedelta(days=1)), None)
    if hom_qua is not None and hom_qua.trang_thai == SKIPPED:
        tran = min(tran, CUONG_DO_BAI_NHE)
        ngan_sach = PHUT_BAI_NHE
        kh.tran_cuong_do, kh.ngan_sach_phut = tran, ngan_sach
        kh.ly_do += "NT-2: hôm qua bỏ tập nên hôm nay hạ xuống bài nhẹ 15 phút. "
    else:
        trong_series = _tap_ke_tiep_trong_series(pool, lich_su, tran)
        if trong_series is not None:
            kh.video = trong_series
            kh.ly_do += "Luật 0: đang giữa series, lấy bài kế tiếp theo đúng thứ tự."
            kh.loi_thoat = _dung_loi_thoat(pool, trong_series.nhom_co, tran, lich_su,
                                           hom_nay, ngan_sach, trong_series)
            return kh

    nhom = loai
    # Ngày cardio và giãn cơ vốn không dùng tạ — đừng bắt nó dò hết các bậc
    # nới lỏng cho 'dumbbell' rồi mới rơi sang bodyweight.
    dung_cu_chinh = KHONG_TA if loai in (CARDIO, MOBILITY) else TA_DON
    video, da_noi = _chon_voi_noi_long(pool, nhom, tran, dung_cu_chinh, lich_su,
                                       hom_nay, ngan_sach)
    if video is None and dung_cu_chinh == TA_DON:
        video, da_noi2 = _chon_voi_noi_long(pool, nhom, tran, KHONG_TA, lich_su,
                                            hom_nay, ngan_sach)
        da_noi = da_noi + ["chuyen_sang_bodyweight"] + da_noi2

    kh.video = video
    kh.noi_long = da_noi
    if video is None:
        kh.ly_do += ("Pool không còn bài nào hợp — cần thêm video, xem §5. "
                     "Event vẫn được tạo kèm cảnh báo này.")
    elif not kh.ly_do:
        cuoi = _ngay_cuoi_tap_nhom(video.nhom_co, lich_su)
        lech = abs(video.phut - ngan_sach)
        kh.ly_do = (
            "Nhóm {} lâu nhất chưa chạm tới ({}); {} phút so với ngân sách {} phút{}."
            .format(video.nhom_co,
                    "chưa từng tập" if cuoi is None else "lần cuối " + cuoi.isoformat(),
                    video.phut, ngan_sach,
                    "" if lech <= 8 else " — lệch {} phút, pool chưa có bài sát hơn".format(lech))
        )
    kh.loi_thoat = _dung_loi_thoat(pool, nhom, tran, lich_su, hom_nay, ngan_sach, video)
    return kh


def _dung_loi_thoat(pool, nhom, tran, lich_su, hom_nay, ngan_sach, bai_chinh=None):
    """§5 luật 7 — tính sẵn từ tối hôm trước để bấm nút là đổi ngay.

    Một lối thoát trùng đúng bài chính thì vô nghĩa, và hiện ra còn gây mất tin
    tưởng hơn là không có. Lọc bỏ những cái đó.
    """
    tru = {bai_chinh.id} if bai_chinh is not None else set()
    con_lai = [v for v in pool if v.id not in tru]

    ra = {}
    # Chỉ có nghĩa khi bài chính đang cần tạ.
    if bai_chinh is None or bai_chinh.dung_cu == TA_DON:
        ra["khong_co_ta"] = _chon_voi_noi_long(
            con_lai, nhom, tran, KHONG_TA, lich_su, hom_nay, ngan_sach)[0]
    dc = bai_chinh.dung_cu if bai_chinh is not None else TA_DON
    ra["nhe_hon"] = _chon_voi_noi_long(
        con_lai, nhom, CUONG_DO_BAI_NHE, dc, lich_su, hom_nay, PHUT_BAI_NHE)[0]
    # Ngày vốn đã là cardio thì "chạy thay" không phải một lựa chọn khác.
    if nhom != CARDIO:
        ra["chay_thay"] = _chon_voi_noi_long(
            con_lai, CARDIO, tran, KHONG_TA, lich_su, hom_nay, ngan_sach)[0]
    return {k: v for k, v in ra.items() if v is not None}
