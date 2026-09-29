"""Skeleton — xem README mục "Trạng thái từng script"."""
from __future__ import annotations

from . import config


def main() -> int:
    if not config.bat_buoc(*['YOUTUBE_API_KEY']):
        return 0   # thiếu secrets thì bỏ qua, không làm đỏ workflow
    raise NotImplementedError('§10: ping lại toàn bộ videos, đặt con_song=0 cho video đã chết.')


if __name__ == "__main__":
    raise SystemExit(main())
