"""Skeleton — xem README mục "Trạng thái từng script"."""
from __future__ import annotations

from . import config


def main() -> int:
    if not config.bat_buoc(*['GOOGLE_REFRESH_TOKEN', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']):
        return 0   # thiếu secrets thì bỏ qua, không làm đỏ workflow
    raise NotImplementedError('§3 Collector: đọc lại event hôm qua, suy ra done/skipped/swapped, ghi sessions + lifts.')


if __name__ == "__main__":
    raise SystemExit(main())
