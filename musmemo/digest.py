"""Skeleton — xem README mục "Trạng thái từng script"."""
from __future__ import annotations

from . import config


def main() -> int:
    if not config.bat_buoc(*['GOOGLE_REFRESH_TOKEN', 'MUSMEMO_EMAIL']):
        return 0   # thiếu secrets thì bỏ qua, không làm đỏ workflow
    raise NotImplementedError('§7: email chủ nhật — streak, tải đã tăng, ô nhập cân nặng và vòng eo.')


if __name__ == "__main__":
    raise SystemExit(main())
