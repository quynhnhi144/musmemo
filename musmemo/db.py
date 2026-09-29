"""§4 — schema SQLite. Tên cột bám đúng spec để tra ngược cho dễ."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DUONG_DAN_MAC_DINH = Path(__file__).resolve().parent.parent / "data" / "musmemo.db"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, gio_tap TEXT NOT NULL DEFAULT '06:00',
  ngan_sach_phut TEXT NOT NULL DEFAULT '{}', tran_cuong_do INTEGER NOT NULL DEFAULT 3,
  tuan_bat_dau TEXT, block_het_han TEXT
);

CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1,
  youtube_id TEXT NOT NULL UNIQUE, tieu_de TEXT NOT NULL, kenh TEXT,
  thoi_luong_giay INTEGER NOT NULL, nhom_co TEXT NOT NULL,
  cuong_do INTEGER NOT NULL CHECK (cuong_do BETWEEN 1 AND 5),
  dung_cu TEXT NOT NULL CHECK (dung_cu IN ('none','dumbbell')),
  series_id INTEGER, series_order INTEGER, series_ten TEXT,
  nguon TEXT NOT NULL DEFAULT 'manual', con_song INTEGER NOT NULL DEFAULT 1,
  them_luc TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_videos_series ON videos(series_id, series_order);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1,
  ngay TEXT NOT NULL, video_id INTEGER REFERENCES videos(id), nhom_co TEXT,
  trang_thai TEXT NOT NULL CHECK (trang_thai IN ('planned','done','skipped','swapped')),
  ly_do_doi TEXT, phut_thuc_te INTEGER, gcal_event_id TEXT,
  UNIQUE (user_id, ngay)
);

CREATE TABLE IF NOT EXISTS lifts (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1,
  ngay TEXT NOT NULL, bai_tap TEXT NOT NULL, kg REAL NOT NULL,
  reps INTEGER, qua_nang INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_lifts_bai ON lifts(user_id, bai_tap, ngay);

-- Để v1.1 (§6): cho phép event kê tải theo từng bài trong video.
CREATE TABLE IF NOT EXISTS video_exercises (
  id INTEGER PRIMARY KEY, video_id INTEGER NOT NULL REFERENCES videos(id),
  bai_tap TEXT NOT NULL, thu_tu INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1,
  tuan TEXT NOT NULL, can_nang REAL, vong_eo REAL, an_uong INTEGER,
  UNIQUE (user_id, tuan)
);
"""


def ket_noi(duong_dan=None) -> sqlite3.Connection:
    p = Path(duong_dan or DUONG_DAN_MAC_DINH)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def khoi_tao(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.execute("INSERT OR IGNORE INTO users (id) VALUES (1)")
    _va_them_cot(con)
    con.commit()


def _va_them_cot(con: sqlite3.Connection) -> None:
    """Thêm cột mới cho DB đã tồn tại. SQLite không có IF NOT EXISTS cho cột."""
    for bang, cot, kieu in (("videos", "series_ten", "TEXT"),):
        co = {r["name"] for r in con.execute("PRAGMA table_info(%s)" % bang)}
        if cot not in co:
            con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (bang, cot, kieu))


if __name__ == "__main__":
    c = ket_noi()
    khoi_tao(c)
    print("DB sẵn sàng:", DUONG_DAN_MAC_DINH)
