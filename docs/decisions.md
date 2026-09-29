# Quyết định và lý do

Ghi lại **vì sao** chứ không chỉ **cái gì** — để phiên sau (hoặc model khác)
không tranh luận lại từ đầu, và để biết chỗ nào đổi được, chỗ nào không.

Mỗi mục: quyết định · ngày · lý do · phương án đã loại.

---

## QĐ-01 · Google Calendar là giao diện, không làm web UI
**2026-09-13**

Calendar có sẵn thông báo đẩy, snooze, và **chiếm chỗ trong ngày** — email thì trôi.
Hệ một người dùng mà làm web UI thì đăng nhập, hosting, frontend đều là chi phí thuần túy.

*Đã loại:* app mobile, web dashboard.

## QĐ-02 · Một lựa chọn mặc định + lối thoát, không phải menu
**2026-09-13**

Người dùng muốn "được chọn" nhưng cũng muốn "không phải nghĩ". Menu ba món ngang
hàng vẫn bắt phải nghĩ. Giải pháp: một bài đặt sẵn, kèm vài lối thoát — trạng thái
mặc định là *hành động*, không phải *quyết định*.

## QĐ-03 · Giữ thói quen được ưu tiên hơn giữ chương trình (NT-2)
**2026-09-15**

Hôm qua bỏ tập thì hôm nay tự hạ xuống bài 15 phút cường độ ≤2, không hỏi.
Cú trượt dài luôn bắt đầu từ ngày thứ hai, không phải ngày đầu.

*Đánh đổi có thật:* làm chậm tiến độ chương trình. Chấp nhận, vì mục tiêu số một
là thói quen.

## QĐ-04 · Hai tuần đầu khóa trần cường độ 3/5 (NT-5)
**2026-09-15**

Người dùng quay lại sau một thời gian nghỉ dài. Cơ và thần kinh hồi phục nhanh nhưng
**gân và dây chằng chậm hơn nhiều**. Bẫy kinh điển: tuần 1 tập đúng mức cũ → đau
5 ngày → mất niềm tin → nghỉ tiếp. Trần được cài cứng, kể cả khi người dùng đòi nặng hơn.

## QĐ-05 · Chạy trên GitHub Actions, không dùng VPS có sẵn
**2026-09-21**

VPS có sẵn là **máy của công ty**, đang chạy một dự án khác với cơ chế tự động
deploy poll `origin/main` liên tục — mỗi commit đều kích hoạt build lại rồi restart
dịch vụ. Đặt dự án cá nhân vào đó là ghép một hệ thống công việc với một app tập gym,
trên một máy không phải của mình.

GitHub Actions: miễn phí với repo private, không server phải nuôi, **không đụng gì
tới hạ tầng dự án khác**. Cron trễ 10–30 phút không sao vì job 21:00 phục vụ 06:00 hôm sau.

*Đã loại:* dùng chung repo với dự án công ty (tuyệt đối không), VPS cách ly, macOS launchd
(máy ngủ thì job không chạy).

## QĐ-06 · Trạng thái nằm trong `data/musmemo.db` commit ngược vào repo
**2026-09-21**

Đơn giản nhất cho một người dùng: workflow chạy xong thì commit file SQLite.
Ba workflow dùng chung `concurrency: musmemo-state` để không ghi chồng.

*Phương án thay thế nếu sau này thấy vướng:* Turso free tier.

## QĐ-07 · Luật 0 — khóa series
**2026-09-20**

Rất nhiều nội dung hay trên YouTube là **chương trình có thứ tự** (EPIC Day 1→30).
Luật tránh lặp 21 ngày và tránh trùng nhóm cơ 48h sẽ xáo tung thứ tự đó, biến một
chương trình có progression thành mớ video ngẫu nhiên — tức là vứt đi đúng phần
giá trị nhất trong pool.

## QĐ-08 · NT-2 thắng Luật 0; NT-5 thắng cả hai
**2026-09-22**

Spec 0.2 tự mâu thuẫn: sơ đồ vẽ Luật 0 chặn trước NT-2, phần chữ lại viết "chỉ
NT-2 mới được quyền ghi đè". Chốt theo phần chữ — hôm qua bỏ tập thì hôm nay phải
nhẹ, kể cả đang giữa chương trình.

Thêm: **trần cường độ NT-5 chặn cả bài kế tiếp của series**, vì NT-5 là luật an
toàn cho gân chứ không phải luật chấm điểm.

*Có test khóa:* `test_nt2_thang_ca_luat_0`, `test_tran_cuong_do_thang_ca_series`.

## QĐ-09 · Thang quay lại theo số ngày nghỉ
**2026-09-20**

Bản 0.1 chỉ biết "nghỉ 1 ngày" và "bắt đầu từ 0". Khoảng giữa mới là thứ xảy ra
thật: đi công tác 10 ngày, ốm một tuần. Bê logic Day Gap của Stryd (có ngưỡng theo
nghiên cứu) sang: ≤2 / 3–7 / 8–14 / 15–28 / >28 ngày.

## QĐ-10 · `series_id` lấy từ `zlib.crc32` tên series
**2026-09-25**

Cần ID ổn định qua mọi lần chạy ingest. `hash()` của Python đổi mỗi tiến trình
nên không dùng được. crc32 thì cố định. Kèm cột `series_ten` để còn đọc được tên.

*Đã loại:* thêm bảng `series` riêng — không đáng cho một người dùng.

## QĐ-11 · "4 nút" trong §1 được hiện thực thành link trực tiếp
**2026-09-25**

Không có server thì không thể có nút thật trong mô tả event Calendar. Lối thoát
được dựng sẵn từ tối hôm trước và đưa vào event dưới dạng **link tới video thay thế**
— bấm là mở luôn, không cần round-trip.

Kéo theo: lối thoát trùng đúng bài chính thì **bị lọc bỏ** — hiện ra còn gây mất
tin tưởng hơn là không có.

*Lưu ý:* §1 vẽ 4 nút nhưng §5 luật 7 chỉ nói 3. Theo §5. Nút "Bài khác cùng nhóm" chưa làm.

## QĐ-12 · Kê tải theo nhóm cơ, chưa theo từng bài trong video
**2026-09-25**

Bảng `video_exercises` (§6, v1.1) chưa có dữ liệu, nên chưa biết video hôm nay có
động tác gì. Tạm map: thân dưới → squat/hip thrust/RDL, thân trên → đẩy vai/chèo.
Đủ dùng và sẽ chính xác hơn khi làm v1.1 (nguồn: chapters trong mô tả video).

## QĐ-13 · Model mặc định `claude-opus-5`, không tự hạ vì tiền
**2026-09-25**

Gắn tag video là việc phân loại đơn giản, Haiku thừa sức. Nhưng hạ model là quyết
định của người dùng, không phải của người viết code. Để sẵn biến `ANTHROPIC_MODEL`
trong `.env.example` kèm gợi ý.

## QĐ-14 · Tên: repo `musmemo`
**2026-09-25**

Người dùng chọn, lý do: muốn người khác phải đoán, và thích ba chữ M.
Đọc nhanh nghe ra "muscle memory" — vừa đúng khoa học với người quay lại tập sau
khi nghỉ, vừa đúng nghĩa đen (event 6 giờ sáng là một tờ memo).

*Chưa chốt:* spec vẫn gọi sản phẩm là "Sáng Mai". Đồng bộ hay giữ hai tên — §11 câu 07.

## QĐ-15 · Ngày cardio/giãn cơ mặc định tìm video không tạ
**2026-09-25**

Lỗi phát hiện khi chạy thử: ngày cardio dò hết 5 bậc nới lỏng cho `dumbbell` rồi
mới chịu rơi sang bodyweight, và báo là "đã nới lỏng luật" dù chẳng có gì sai.
Sửa: `dung_cu` mặc định phụ thuộc loại buổi.

## QĐ-16 · Tín hiệu "hôm nay tập chưa" lấy từ RSVP của event
**2026-09-25**

`collect.py` cần phân biệt `done` / `skipped` / `swapped` mà không có server, nên
không có nút thật (xem [QĐ-11](#qđ-11)). Ba phương án cân nhắc: mặc định lạc quan
(không chạm), đổi màu event (~4 chạm), RSVP (1 chạm).

Chọn **RSVP**. Lý do: ít chạm nhất, dùng UI có sẵn của Google Calendar nên không
phải dạy người dùng quy ước gì, và số trạng thái khớp đúng:

| RSVP | `sessions.trang_thai` |
|---|---|
| `accepted` | `done` |
| `declined` | `skipped` |
| `tentative` | `swapped` — có mặt nhưng đổi bài (§7) |
| `needsAction` | chưa trả lời — chưa chốt xử lý thế nào |

*Đã loại:* mặc định lạc quan — NT-2 sẽ gần như không bao giờ kích hoạt, mà NT-2
là một trong hai mũi tên đứt nét làm nên toàn bộ trí thông minh của hệ thống (§0).
Đổi màu — đọc `colorId` thì chắc chắn được, nhưng bắt người dùng nhớ quy ước màu
lúc 6 giờ sáng.

**Chưa kiểm chứng được:** Google Calendar có hiện nút RSVP cho event do chính
người dùng tạo hay không. Tài liệu Calendar API không nói, và diễn đàn Google
cũng không có câu trả lời dứt khoát. Người tạo event thường được tự động đặt
`responseStatus: accepted` và không thấy nút "Going?".

Phải thử thật trước khi viết `collect.py`. Nếu không hiện nút, lối thoát đã biết:
tạo event trên **một calendar phụ** rồi mời email chính làm khách — tài liệu Google
có phân biệt "event creator" với "calendar event organizer", nên hướng này có cơ sở.
Nếu cả hai đều không được thì quay lại phương án đổi màu.

*Kéo theo:* `publish.py` phải thêm `attendees` vào event — hiện chưa có.
