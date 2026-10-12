"""§3 Ingest — video YouTube → metadata → LLM gắn tag → bảng videos.

Hai nguồn: một playlist tự thả tay, hoặc `--kenh` kéo thẳng từ các kênh đã chọn.
Chạy tay mỗi khi muốn bổ sung pool. Mỗi video chỉ gọi LLM **một lần**
rồi lưu vĩnh viễn; lần chạy sau bỏ qua video đã có (trừ khi truyền --retag).
"""
from __future__ import annotations

import itertools
import re
import sys
import zlib
from typing import Dict, Iterator, List, Optional

from . import config
from .db import ket_noi, khoi_tao

CAN = ["YOUTUBE_API_KEY", "MUSMEMO_PLAYLIST_ID", "ANTHROPIC_API_KEY"]
#: Chế độ --kenh không cần playlist nào cả.
CAN_KENH = ["YOUTUBE_API_KEY", "ANTHROPIC_API_KEY"]

#: §10 nói pool là rủi ro số một của dự án, và nó nằm ở phía người dùng chứ
#: không phải phía code. Người dùng chốt sáu kênh này (12/10/2026) — curation
#: diễn ra ở mức *kênh* thay vì mức *từng video*, đủ để gỡ thế bí.
KENH_MAC_DINH = [
    "@hanagianganhofficial",
    "@EmiWong",
    "@PamelaRf1",
    "@TRAINWITHGAINSBYBRAINS",
    "@CarolineGirvan",
    "@yuukasagawa5483",
]

_ISO = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def giay_tu_iso8601(s: str) -> int:
    """'PT1H2M3S' -> 3723. Trả 0 nếu không đọc được."""
    m = _ISO.fullmatch(s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def series_id_tu_ten(ten: Optional[str]) -> Optional[int]:
    """ID ổn định qua mọi lần chạy — hash của Python đổi mỗi tiến trình nên
    không dùng được; crc32 thì cố định."""
    if not ten:
        return None
    return zlib.crc32(" ".join(ten.lower().split()).encode("utf-8"))


# --- YouTube Data API -------------------------------------------------------
def _goi_youtube(duong_dan: str, **tham_so):
    import json
    import urllib.parse
    import urllib.request

    tham_so["key"] = config.lay("YOUTUBE_API_KEY")
    url = "https://www.googleapis.com/youtube/v3/%s?%s" % (
        duong_dan, urllib.parse.urlencode(tham_so))
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def id_trong_playlist(playlist_id: str) -> Iterator[str]:
    trang = None
    while True:
        kw = dict(part="contentDetails", playlistId=playlist_id, maxResults=50)
        if trang:
            kw["pageToken"] = trang
        data = _goi_youtube("playlistItems", **kw)
        for it in data.get("items", []):
            vid = it.get("contentDetails", {}).get("videoId")
            if vid:
                yield vid
        trang = data.get("nextPageToken")
        if not trang:
            return


def chuan_hoa_handle(s: str) -> str:
    """Nhận '@Ten', 'Ten', hoặc cả link kênh — trả về '@Ten'."""
    s = (s or "").strip().rstrip("/")
    if "youtube.com/" in s:
        s = s.rsplit("/", 1)[-1]
    return s if s.startswith("@") else "@" + s


def uploads_cua_kenh(handle: str) -> Optional[str]:
    """@handle → id playlist 'uploads' của kênh đó.

    Mọi kênh đều có sẵn một playlist chứa toàn bộ video đã đăng. Đọc nó giống
    hệt đọc playlist thường, nên **không cần quyền ghi YouTube** — đó là lý do
    chế độ này tồn tại thay vì bắt người dùng tự dựng playlist.
    """
    data = _goi_youtube("channels", part="contentDetails",
                        forHandle=chuan_hoa_handle(handle))
    items = data.get("items") or []
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def id_tu_cac_kenh(handles: List[str], moi_kenh: int) -> List[str]:
    """Video mới nhất của từng kênh, gộp lại và bỏ trùng, giữ nguyên thứ tự."""
    ra: List[str] = []
    for h in handles:
        up = uploads_cua_kenh(h)
        if not up:
            print("[musmemo] ⚠ không tìm thấy kênh %s — bỏ qua." % h)
            continue
        lay = list(itertools.islice(id_trong_playlist(up), moi_kenh))
        print("[musmemo] %-30s lấy %d video mới nhất" % (chuan_hoa_handle(h), len(lay)))
        ra.extend(lay)
    return list(dict.fromkeys(ra))


def chi_tiet_video(ids: List[str]) -> List[Dict]:
    ra = []
    for i in range(0, len(ids), 50):     # API nhận tối đa 50 id mỗi lần
        data = _goi_youtube("videos", part="snippet,contentDetails,status",
                            id=",".join(ids[i:i + 50]))
        ra.extend(data.get("items", []))
    return ra


# --- Gắn tag bằng Claude ----------------------------------------------------
def _mo_hinh_tag():
    from typing import Optional as Opt

    from pydantic import BaseModel, Field
    try:
        from typing import Literal
    except ImportError:                                  # py<3.8
        from typing_extensions import Literal            # type: ignore

    class Tag(BaseModel):
        nhom_co: Literal["lower", "upper", "full", "core", "cardio", "mobility"]
        cuong_do: int = Field(ge=1, le=5)
        dung_cu: Literal["none", "dumbbell"]
        series_ten: Opt[str] = Field(
            default=None,
            description="Tên chương trình nếu video thuộc một series có thứ tự, "
                        "ví dụ 'EPIC Heat'. Null nếu video đứng một mình.")
        series_order: Opt[int] = Field(
            default=None, description="Số thứ tự trong series, ví dụ 12.")
        ghi_chu: str = Field(description="Một câu giải thích vì sao gắn như vậy.")

    return Tag


HUONG_DAN = """Bạn đang phân loại một video tập luyện trên YouTube cho một hệ thống
tự xếp lịch tập.

Quy ước:
- nhom_co: chọn nhóm cơ CHÍNH. 'full' khi video tập toàn thân; 'cardio' cho chạy,
  HIIT, nhảy; 'mobility' cho giãn cơ, yoga phục hồi; 'core' chỉ khi video tập
  riêng bụng và lưng dưới.
- cuong_do 1-5: 1 là giãn cơ nhẹ, 3 là buổi tập đều đặn bình thường,
  5 là rất nặng hoặc tới ngưỡng.
- dung_cu: 'dumbbell' nếu video CẦN tạ để tập đúng. 'none' nếu tập tay không
  hoặc tạ chỉ là tuỳ chọn.
- series_ten và series_order: chỉ điền khi tiêu đề cho thấy video nằm trong một
  chương trình có thứ tự (ví dụ 'Day 12', 'Week 3', 'EPIC Heat #12'). Nếu không
  chắc thì để null — đoán sai sẽ khoá lịch tập vào một chuỗi không có thật.
"""


def gan_tag(video: Dict) -> Dict:
    import anthropic

    sn = video.get("snippet", {})
    mo_ta = (sn.get("description") or "")[:1500]
    noi_dung = (
        "Tiêu đề: %s\nKênh: %s\nThời lượng: %d giây\n\nMô tả:\n%s"
        % (sn.get("title", ""), sn.get("channelTitle", ""),
           giay_tu_iso8601(video.get("contentDetails", {}).get("duration", "")),
           mo_ta)
    )
    client = anthropic.Anthropic()
    kq = client.messages.parse(
        model=config.lay("ANTHROPIC_MODEL", "claude-opus-5-5"),
        max_tokens=16000,
        system=HUONG_DAN,
        messages=[{"role": "user", "content": noi_dung}],
        output_format=_mo_hinh_tag(),
    )
    return kq.parsed_output.model_dump()


# --- Ghi vào DB -------------------------------------------------------------
SQL_UPSERT = """
INSERT INTO videos (youtube_id, tieu_de, kenh, thoi_luong_giay, nhom_co,
                    cuong_do, dung_cu, series_id, series_order, series_ten,
                    nguon, con_song)
VALUES (?,?,?,?,?,?,?,?,?,?, 'manual', 1)
ON CONFLICT(youtube_id) DO UPDATE SET
  tieu_de=excluded.tieu_de, kenh=excluded.kenh,
  thoi_luong_giay=excluded.thoi_luong_giay, nhom_co=excluded.nhom_co,
  cuong_do=excluded.cuong_do, dung_cu=excluded.dung_cu,
  series_id=excluded.series_id, series_order=excluded.series_order,
  series_ten=excluded.series_ten, con_song=1
"""


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    retag = "--retag" in argv
    che_do_kenh = "--kenh" in argv
    if not config.bat_buoc(*(CAN_KENH if che_do_kenh else CAN)):
        return 0

    con = ket_noi()
    khoi_tao(con)
    da_co = {r["youtube_id"] for r in con.execute("SELECT youtube_id FROM videos")}

    if che_do_kenh:
        moi_kenh = 12
        if "--moi" in argv:
            try:
                moi_kenh = int(argv[argv.index("--moi") + 1])
            except (IndexError, ValueError):
                pass
        handles = [a for a in argv if a.startswith("@")] or KENH_MAC_DINH
        ids = id_tu_cac_kenh(handles, moi_kenh)
        print("[musmemo] tổng %d video từ %d kênh (đã bỏ trùng)" % (len(ids), len(handles)))
    else:
        ids = list(id_trong_playlist(config.lay("MUSMEMO_PLAYLIST_ID")))
        print("[musmemo] playlist có %d video" % len(ids))
    can_lam = ids if retag else [v for v in ids if v not in da_co]
    if not can_lam:
        print("[musmemo] không có video mới — xong.")
        return 0

    moi, chet = 0, 0
    for v in chi_tiet_video(can_lam):
        vid = v["id"]
        if v.get("status", {}).get("privacyStatus") == "private":
            chet += 1
            continue
        giay = giay_tu_iso8601(v.get("contentDetails", {}).get("duration", ""))
        if giay < 240:        # dưới 4 phút gần như chắc chắn không phải buổi tập
            print("[musmemo] bỏ qua (quá ngắn, %ds): %s" % (giay, v["snippet"]["title"]))
            continue
        t = gan_tag(v)
        con.execute(SQL_UPSERT, (
            vid, v["snippet"]["title"], v["snippet"].get("channelTitle", ""), giay,
            t["nhom_co"], t["cuong_do"], t["dung_cu"],
            series_id_tu_ten(t.get("series_ten")), t.get("series_order"),
            t.get("series_ten"),
        ))
        con.commit()
        moi += 1
        print("[musmemo] %-9s cd=%d %-8s %2d′  %s" % (
            t["nhom_co"], t["cuong_do"], t["dung_cu"], round(giay / 60),
            v["snippet"]["title"][:60]))

    print("[musmemo] đã gắn tag %d video (%d video riêng tư bị bỏ)." % (moi, chet))
    _canh_bao_pool(con)
    return 0


def _canh_bao_pool(con) -> None:
    """§5 — pool mỏng thì luật 4 và 5 sẽ liên tục phải nới lỏng. Nói sớm còn hơn
    để người dùng tự phát hiện qua việc lịch bắt đầu lặp."""
    tong = con.execute("SELECT COUNT(*) c FROM videos WHERE con_song=1").fetchone()["c"]
    if tong < 40:
        print("[musmemo] ⚠ pool mới có %d video, spec khuyến nghị ≥40." % tong)
    thieu = con.execute(
        "SELECT nhom_co, COUNT(*) c FROM videos "
        "WHERE con_song=1 AND dung_cu='none' GROUP BY nhom_co").fetchall()
    co = {r["nhom_co"]: r["c"] for r in thieu}
    for nhom in ("lower", "upper", "full"):
        if co.get(nhom, 0) < 3:
            print("[musmemo] ⚠ chỉ có %d video bodyweight cho '%s' — cần ≥3 để nút "
                  "'không có tạ' luôn dùng được." % (co.get(nhom, 0), nhom))
    nhe = con.execute("SELECT COUNT(*) c FROM videos WHERE con_song=1 "
                      "AND cuong_do<=2 AND thoi_luong_giay<=1200").fetchone()["c"]
    if nhe < 3:
        print("[musmemo] ⚠ chỉ có %d video nhẹ (cường độ ≤2, ≤20 phút). NT-2 cần "
              "chúng để hạ tải sau ngày bỏ tập, và nút 'nhẹ hơn 15′' cũng vậy." % nhe)


if __name__ == "__main__":
    raise SystemExit(main())
