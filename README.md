# MusMemo

*Đọc nhanh lên thì nghe ra. Không thì cứ để đó đoán tiếp.*

Mỗi tối 21:00, hệ thống chọn đúng **một** buổi tập cho sáng hôm sau từ playlist YouTube
của bạn, đẩy vào Google Calendar kèm mức tạ cụ thể, rồi học từ những hôm bạn bỏ tập.

## Tài liệu

| | |
|---|---|
| [Bản đồ MusMemo](https://claude.ai/artifact/BaqDfjreKi4sJYDxa3kVFo?sk=yr0QWUuVK_veXnIYSV7qPg) | **Mới vào thì xem cái này trước.** Hai sơ đồ: một vòng 24 giờ, và luồng Google OAuth |
| [CLAUDE.md](CLAUDE.md) | **Sắp sửa code thì đọc cái này.** Bộ nhớ dự án: trạng thái, lệnh, bất biến, cạm bẫy |
| [docs/spec.md](docs/spec.md) | Đặc tả đầy đủ. Mọi `§N` trong code trỏ về đây |
| [docs/decisions.md](docs/decisions.md) | Các quyết định đã chốt và **lý do** |

Bản spec dạng trang web (cùng nội dung) — chưa chia sẻ, chỉ chủ tài khoản mở được:
https://claude.ai/artifact/Du8y4sRy5o1aHGRa3yS9TS

## Vì sao chạy trên GitHub Actions

Không có server để nuôi, và **không đụng gì tới hạ tầng của dự án khác**. Ba workflow
theo lịch làm toàn bộ công việc; trạng thái nằm trong `data/musmemo.db` được commit
ngược lại repo sau mỗi lần chạy.

| Workflow | Giờ VN | Việc |
|---|---|---|
| `nightly-schedule` | 21:00 hằng ngày | Chọn bài, tạo event Calendar cho 06:00 sáng mai |
| `daily-collect` | 12:00 hằng ngày | Đọc lại buổi hôm qua, ghi `sessions` + `lifts` |
| `weekly-digest` | CN 20:00 | Email tổng kết tuần |
| `tests` | mỗi lần push | Chạy test cho §5 và §6 |

Cron của GitHub tính theo UTC và có thể trễ 10–30 phút. Không sao: job 21:00 tạo event
cho 06:00 hôm sau, dư 9 tiếng.

## Chạy thử tại máy

Lõi thuật toán **không có phụ thuộc ngoài**, chạy được bằng python hệ thống:

```bash
python3 -m venv .venv && ./.venv/bin/pip install pytest
./.venv/bin/python -m pytest -q      # 34 test, ~0.03s, không cần mạng
./.venv/bin/python -m musmemo.db     # tạo data/musmemo.db
./.venv/bin/python -m musmemo.publish --dry-run   # xem event sẽ trông thế nào
```

## Trạng thái từng script

| Module | Trạng thái | Ghi chú |
|---|---|---|
| `models.py` | ✅ xong | Kiểu dữ liệu, tên bám §4 |
| `schedule.py` | ✅ xong, có test | §5 đầy đủ: thang quay lại, NT-2, Luật 0, lọc, chấm điểm, nới lỏng |
| `progression.py` | ✅ xong, có test | §6: luật tăng tải và bậc thang khi chạm trần 30 kg |
| `db.py` | ✅ xong | Schema §4 |
| `config.py` | ✅ xong | Đọc `.env` / Secrets, thiếu thì bỏ qua êm |
| `ingest.py` | ✅ xong | Playlist → YouTube API → Claude gắn tag → DB. Cảnh báo khi pool còn mỏng |
| `publish.py` | ✅ xong, có test | Chọn bài + kê tạ + tạo event. `--dry-run` in ra event mà không gọi mạng |
| `collect.py` | ⬜ skeleton | Cần OAuth Google |
| `digest.py` | ⬜ skeleton | Cần OAuth Google |
| `health.py` | ⬜ skeleton | Cần `YOUTUBE_API_KEY` |
| `get_token.py` | ✅ xong, có test | OAuth một lần, cần extra `[auth]` |

Script chưa cấu hình secrets sẽ **in ra rồi thoát 0**, không làm đỏ workflow.

## Cấu hình

Copy `.env.example` → `.env` để chạy local. Trên GitHub: Settings → Secrets and
variables → Actions. `MUSMEMO_GIO_TAP` và `MUSMEMO_TRAN_TA_KG` để ở tab *Variables*
(không phải bí mật), phần còn lại ở tab *Secrets*.

## Còn nợ

- §11 trong spec — 7 câu chưa chốt, trong đó câu 01 (30 kg mỗi tay hay cả bộ) ảnh
  hưởng trực tiếp tới `progression.py`.
- §6 v1.1 — bảng `video_exercises` đã có trong schema nhưng chưa dùng.
- §10 — "nợ nhóm cơ theo tuần" chưa làm.
