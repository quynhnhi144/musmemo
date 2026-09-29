# CLAUDE.md — bộ nhớ dự án MusMemo

File này được đọc tự động khi mở phiên làm việc trong repo. Mục đích: bất kỳ
phiên nào, bất kỳ model nào, cũng nối tiếp được công việc mà không cần hỏi lại
từ đầu. **Đọc hết file này trước khi sửa code.**

## Dự án là gì

Mỗi tối 21:00 hệ thống chọn đúng **một** buổi tập cho sáng hôm sau từ playlist
YouTube của người dùng, đẩy vào Google Calendar kèm mức tạ cụ thể, rồi học từ
những hôm bị bỏ tập. Một người dùng duy nhất, chạy trên GitHub Actions.

**Mục tiêu thật sự là xây lại thói quen tập luyện, không phải tối ưu thành tích.**
Mọi đánh đổi thiết kế đều nghiêng về phía đó.

## Tài liệu

| Ở đâu | Cái gì |
|---|---|
| [docs/spec.md](docs/spec.md) | Đặc tả đầy đủ. Mọi `§N` trong code và commit trỏ về đây |
| [docs/decisions.md](docs/decisions.md) | Các quyết định đã chốt và **lý do**. Đọc trước khi định làm khác đi |
| https://claude.ai/artifact/Du8y4sRy5o1aHGRa3yS9TS | Bản spec dạng trang web (cùng nội dung, cần đăng nhập) |

## Người dùng

Hồ sơ cá nhân — nền tảng thể chất, thiết bị, giờ tập, mục tiêu, điểm xuất phát —
nằm ở **`PROFILE.local.md`**. File đó bị `.gitignore` vì **repo này là public**.
Đọc nó trước khi đụng vào logic chọn bài hoặc kê tải; thiếu nó thì mọi con số
trong spec chỉ là ví dụ.

Không có file? Hỏi người dùng rồi dựng lại theo `PROFILE.example.md`.
**Đừng chép nội dung đó ngược vào CLAUDE.md hay `docs/`.**

| | |
|---|---|
| Ngôn ngữ | Tiếng Việt. Nhưng mọi thứ ra ngoài repo viết tiếng Anh — xem mục "Ngôn ngữ" bên dưới |

## Trạng thái hiện tại

```
✅ models.py       kiểu dữ liệu, tên trường bám §4
✅ schedule.py     §5 đầy đủ — thang quay lại, NT-2, Luật 0, lọc, chấm điểm, nới lỏng
✅ progression.py  §6 — luật tăng tải và bậc thang khi chạm trần 30 kg
✅ db.py           schema §4 + migration cộng cột
✅ config.py       đọc .env / Secrets, thiếu thì bỏ qua êm
✅ ingest.py       playlist → YouTube API → Claude gắn tag → DB
✅ publish.py      chọn bài + kê tạ + tạo event Calendar; có --dry-run
⬜ collect.py      đọc lại event hôm qua, suy ra done/skipped/swapped
⬜ digest.py       email tổng kết chủ nhật
⬜ health.py       ping lại video chết
✅ get_token.py    lấy Google refresh token (chạy tay một lần, cần extra [auth])
```

34 test, chạy offline trong ~0.03s. **Chưa có secrets nào được cấu hình** nên ba
workflow theo lịch hiện chỉ in "chưa cấu hình" rồi thoát 0.

## Lệnh

```bash
./.venv/bin/python -m pytest -q                  # 34 test, không cần mạng
./.venv/bin/python -m musmemo.get_token          # OAuth một lần; --ghi-env để ghi thẳng .env
./.venv/bin/python -m musmemo.db                 # tạo/nâng cấp data/musmemo.db
./.venv/bin/python -m musmemo.publish --dry-run  # in event ra, không gọi mạng
./.venv/bin/python -m musmemo.ingest             # cần YOUTUBE_API_KEY + ANTHROPIC_API_KEY
./.venv/bin/python -m musmemo.ingest --retag     # gắn tag lại toàn bộ
```

## Bất biến — đừng phá

Đây là những thứ **có test khóa lại**. Nếu thấy chúng vướng víu, đọc
[docs/decisions.md](docs/decisions.md) trước khi đổi.

1. **Lõi thuật toán không có phụ thuộc ngoài.** `schedule.py` và `progression.py`
   chỉ dùng stdlib, nhận trạng thái vào và trả quyết định ra — không mạng, không
   DB. Đó là lý do test chạy được ở mọi nơi trong vài mili giây. Đừng import
   `anthropic` hay `googleapiclient` vào hai file đó.
2. **Thứ tự quyền lực trong §5:** thang quay lại → NT-2 → Luật 0 → lọc/chấm điểm.
   Và **trần cường độ NT-5 thắng tất cả** vì nó bảo vệ gân, không phải luật chấm điểm.
3. **`swapped` không phải `skipped`.** Bấm "không có tạ" vẫn tính là có mặt:
   streak giữ nguyên, NT-2 không kích hoạt, không ghi dòng `lifts` nào.
4. **Scheduler không bao giờ trả về rỗng im lặng.** Hết bài thì nới lỏng luật
   từng bậc và **ghi lại đã nới cái gì** vào `kh.noi_long`.
5. **Không so sánh với quá khứ của người dùng** (NT-3). Không PR cũ, không cự ly
   cũ, không "bạn từng...". Mốc 0 là `users.tuan_bat_dau`.
6. **Chỉ lưu link YouTube, không tải video.** Vi phạm ToS.

## Quy ước code

- **Tên trường tiếng Việt, bám đúng §4** (`nhom_co`, `cuong_do`, `dung_cu`,
  `con_song`...). Cố ý: để tra ngược từ code về spec không phải dịch.
- **Chú thích bằng tiếng Việt**, và ghi `§N` khi một đoạn code hiện thực một luật.
- **Script gọi mạng phải thoát 0 khi thiếu secrets** (`config.bat_buoc`), để
  workflow không đỏ trước lúc cấu hình xong.
- Viết hàm thuần trước, phần I/O tách xuống cuối file.

## Luật nền — học từ dự án khác, không dùng tài sản của công ty

**Học thì thoải mái.** Cấu trúc, cách thiết kế, quy ước, bài học vận hành từ các
dự án khác — kể cả dự án công ty — đều là tham chiếu tốt. Cứ mượn, đó là cách làm
việc bình thường.

**Dùng thì tuyệt đối không.** Ranh giới nằm ở *tài sản và danh tính*, không nằm ở
*ý tưởng*:

| Học được | Không dùng |
|---|---|
| Cấu trúc thư mục, cách tách module | Email, domain, tài khoản, secret của công ty |
| Quy ước code, cách viết tài liệu | Hạ tầng công ty để chạy dự án này |
| Bài học vận hành, cạm bẫy đã gặp | Code, config, dữ liệu chép nguyên từ repo công ty |

Email dùng cho dự án: lấy từ `git config user.email`. **Đừng lấy email từ ngữ cảnh
phiên làm việc** — ngữ cảnh có thể đang mang email công ty.

Khi ghi một bài học mượn từ dự án khác vào `docs/`: ghi *bài học*, không cần ghi
*tên dự án*. Repo đang private nhưng có thể có ngày mở public, mà bài học thì
không mất gì khi bỏ tên đi. QĐ-05 là ví dụ.

Trước khi đẩy bất cứ thứ gì ra ngoài repo — trang web, commit, secret, tài liệu
công khai — quét lại một lượt các từ khoá liên quan tới công ty.

## Ngôn ngữ — trong repo tiếng Việt, ra ngoài tiếng Anh

**Mọi thứ rời khỏi repo đều viết bằng tiếng Anh.** Cụ thể: commit message, tên
nhánh, tiêu đề và mô tả pull request, issue, release note, và bất kỳ nội dung nào
được đẩy lên hoặc công bố ra ngoài.

**Giữ tiếng Việt** ở phía trong: trao đổi trong phiên làm việc, chú thích trong
code, tên trường bám §4, và toàn bộ `docs/`.

Ranh giới là *ai đọc*, không phải *file nào*. Khi phân vân: thứ chỉ mình người
dùng và các phiên làm việc đọc thì tiếng Việt; thứ người ngoài có thể đọc thì
tiếng Anh.

Mã `§N` giữ nguyên trong commit tiếng Anh — đó là mã tra cứu, không phải chữ.
Lịch sử git bắt đầu lại từ một commit duy nhất bằng tiếng Anh khi repo chuyển
sang public — ba commit tiếng Việt ban đầu không còn trên remote.

## Cạm bẫy đã gặp

- **`\b` không hoạt động trong `sed` của macOS.** Đừng dùng word-boundary khi
  đổi tên hàng loạt.
- **`.venv` nhúng đường dẫn tuyệt đối** — đổi tên thư mục dự án là phải dựng lại.
- **`hash()` của Python đổi mỗi tiến trình.** `series_id` dùng `zlib.crc32` mới
  ổn định qua các lần chạy.
- **Test không bắt được lỗi tích hợp.** Bốn lỗi thật chỉ lộ ra khi chạy
  `publish --dry-run` với dữ liệu giả. Luôn chạy thử đầu-cuối, đừng chỉ tin test.
- **OAuth để ở chế độ Testing thì refresh token chết sau 7 ngày.** Đây là hành vi
  cố ý của Google với app External + Testing, không phải lỗi. Phải bấm
  **Publish app** cho sang "In production" thì token mới sống lâu. Bỏ qua bước
  này thì GitHub Actions chạy ngon đúng một tuần rồi hỏng lặng lẽ.
- **Cron của GitHub tính theo UTC** và trễ được 10–30 phút. Không sao vì job
  21:00 tạo event cho 06:00 hôm sau.

## Còn nợ

**Bốn câu ở §11 chưa có câu trả lời** — xem cuối [docs/spec.md](docs/spec.md).
Câu 02 (điểm xuất phát) quyết định mốc thời gian mục tiêu có thực tế hay không.
Câu trả lời ghi vào `PROFILE.local.md`, không ghi vào repo.

Việc kỹ thuật tiếp theo, theo thứ tự: `collect.py` → `digest.py` → `health.py`.
**`collect.py` đang chờ một phép thử:** Calendar có hiện nút RSVP cho event do
chính mình tạo không — xem [QĐ-16](docs/decisions.md). Cần chạy `get_token.py`
với OAuth thật rồi tạo một event thử mới biết. Và người dùng cần dựng playlist ~40 video —
đây là rủi ro số một của cả dự án, xem §10.
