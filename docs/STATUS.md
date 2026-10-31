# STATUS — tình trạng và việc còn lại (cập nhật 31/10/2026, sau đợt giao diện điện thoại, cắt ảnh, lọc G-code, bản mang đi)

Một nơi duy nhất cho "cái gì xong / chưa / chưa kiểm chứng". Ký hiệu: ✅ xong và có test · 🧪 xong nhưng **chưa kiểm chứng trên máy/môi trường thật** · ⏳ chưa làm · ❌ đã bỏ.
Mục tiêu hiện tại: **một trình điều khiển máy vẽ chạy trên laptop**, mang sang máy Windows khác bằng bản mang đi (`DONG_GOI.md`). MiniPC Ubuntu (Docker, IP cố định, Cloudflare Tunnel): kế hoạch ở `PLAN_ONLINE.md`, chưa làm. AI nhận diện ngôn ngữ tự nhiên: ngoài phạm vi.

## 1. Tổng quan
| Khối | Tính năng | Kiểm chứng ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95% | ~60% |
| Tạo bản vẽ (SVG, ảnh, bản thảo, hàng đợi) | ~90% | ~45% |
| Cài đặt, hồ sơ máy, cấu hình YAML | ~90% | ~70% |
| Tài liệu, test | ~90% | |

Tổng: khoảng 88–90% tính năng, 60–65% kiểm chứng. Thiếu chủ yếu là thử máy thật và thử nhiều ảnh thật. Test tự động: backend 357 (`python -m pytest`), frontend 32 (`node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs frontend/tests/gcode.test.mjs`).

## 2. Đã xong
**Điều khiển:** kết nối SimLink/Serial, trạng thái 0,5 s, jog (`$J`), Home, Zero, thanh bút 3 nấc, nạp + xem trước + chạy G-code từng dòng chờ `ok` (**kiểm tệp lúc nạp**: dòng bị chặn hiện đỏ kèm số dòng và lý do, khóa nút Chạy; lưu ý hiện vàng), ghi đè tốc độ, hủy 3 chế độ (reset/soft/hard) với xác nhận nâng bút, **tiếp tục từ điểm dừng** (hủy / lỗi / mất kết nối; 🧪 chưa thử máy thật), terminal, dock (macro lưu ở máy chủ + Tệp nhanh = bản thảo đã ghim), mở khóa chuyển động có hẹn giờ + PIN tùy chọn, hàng đợi công việc.
**Cài đặt:** kết nối nhớ cổng, hoạt động, cấu hình máy (đọc/áp dụng/lưu YAML trên mạch, sao lưu, hoàn tác), hồ sơ phần mềm, hạn mức bản thảo, **Lưu trữ dữ liệu** (xem và tải nội dung 3 thư mục cố định: bản thảo, sao lưu cấu hình, macro; thư mục gốc đổi bằng biến môi trường `EXTRUXY_DATA_DIR`).
**Tạo bản vẽ:** SVG (vpype) và ảnh PNG/JPG/WEBP; khổ A6/A5/A4 + tùy chọn; ba kiểu tô (zigzag, sóng, xoắn ốc) + viền + phủ viền; 2–4 màu (mỗi màu một tệp G-code, tên có mã màu); 3 preset (Chân dung, Phong cảnh, Mạch điện/Bản vẽ); canvas kéo/co giãn/xoay/hít lề; tự tạo lại nét khi kéo khung lệch >12%; tự cân sáng; xử lý ảnh ở tiến trình riêng ưu tiên thấp (hủy sạch, giới hạn thời gian/RAM); trình duyệt thu nhỏ ảnh trước khi gửi và xem trước độ sáng ngay; bản thảo trên đĩa (ghim, ưu tiên, tự dọn); thời gian từng bước; **nhập G-code có sẵn thành bản thảo** (một tệp một bản); **tờ mẫu hiệu chỉnh bút** (chữ F, thước 100 mm, 8 dải tô) tạo thành bản thảo; **cắt ảnh** ngay trên khung ảnh gốc (kéo vùng, co giãn góc/cạnh, khóa tỷ lệ tự do / theo khung giấy / 1:1 / 4:3 / 3:4 / 16:9).
**Giao diện:** hai theme, hai ngôn ngữ (vi/en), thương hiệu VMU PlotterPen, bố cục tab Điều khiển (trạng thái một dòng, jog + tọa độ, 2D + tiến trình, terminal dài chạm hàng đợi), hiệu ứng (tắt khi hệ điều hành bật giảm chuyển động); **điện thoại / máy tính bảng**: tab Điều khiển một cột, thứ tự khung 2D → Tệp G-code → Vị trí → Jog → Terminal (chỉ đổi khi màn hình ≤ 760px), hàng đợi ẩn cột Thời gian / Số liệu; tab Tạo bản vẽ khi một cột (≤ 1100px): Khung vẽ trên giấy ngay sau Thông tin bản vẽ.
❌ Đã bỏ: thẻ SD/Flash, tab Công việc, stipple/TSP art, **nhật ký hệ thống ghi ra tệp** (log quá dài, khó đọc; terminal vẫn hiện log trong bộ nhớ), ô nhập đường dẫn thư mục bản thảo.

## 3. Chưa kiểm chứng (🧪) — cần máy thật hoặc môi trường thật
| Việc | Cách kiểm |
|---|---|
| Hướng trục X+/Y+ trên giấy, `VIEW.flipX/flipY` (`core/config.js`) | vẽ vuông có đánh dấu góc |
| Z bút lên/xuống thật, nâng bút sau Dừng gấp thật sự xảy ra | quan sát |
| Thời gian Home, cung G2/G3, `G4 P` tính bằng giây trên FluidNC 4.1.1 | đo |
| Thời gian ước tính (chưa tính gia tốc) | so với thời gian chạy thật vài lần, thêm hệ số |
| Khoảng cách gạch mặc định (2 × bề rộng bút), 3 preset, ngưỡng viền (`edges.py`), góc 45° | in **tờ mẫu hiệu chỉnh bút** (Tạo bản vẽ → Bản thảo đã lưu) với bút 0,2 và 0,4, chỉnh `presets.js`/`spec.py` |
| Tiếp tục từ dòng N: hủy giữa chừng → Home → Tiếp tục, bút có tới đúng đầu nét; biên lùi 64 dòng (`RESUME_MARGIN`) có đủ; gốc Zero có giữ nguyên sau Home | hủy một bản vẽ dài, Home, bấm Tiếp tục, so nét chồng |
| Xử lý ảnh trên MiniPC i5-3210M (đo `info.timings`, RAM, máy có giật không) | chạy ảnh mẫu |
| Giới hạn RAM `RLIMIT_AS` của tiến trình xử lý ảnh, cài `opencv-python-headless`/`scikit-image` trên Ubuntu | thử trên Ubuntu |
| Chia màu với ảnh có màu rất nhỏ (ảnh đêm: đèn cam bị gộp) | thử ảnh nền sáng nhiều màu |

## 4. Việc còn lại
**Cho mục tiêu "chạy trên laptop":**
| # | Việc | Ghi chú |
|---|---|---|
| 1 | Kiểm giao diện bằng mắt các phần chưa chụp: hộp "Tác vụ đã dừng", bảng Lưu trữ, Tệp nhanh trong dock, tab Cài đặt chia 2 cột; cắt ảnh bằng ngón tay trên điện thoại thật | đã chụp bằng Chrome chạy ngầm: tab Điều khiển ở 390 / 900 / 1440 px, khung kiểm tệp G-code, cắt ảnh |
| 2 | Điểm dừng chỉ ghi khi backend còn sống (mất điện hoặc tắt server giữa chừng thì không có) | muốn chắc hơn: ghi mốc tiến độ định kỳ |
| 3 | (Tùy chọn) thời gian ước tính có gia tốc | cần số liệu máy thật |

**Để mở cho nhiều người dùng (MiniPC Ubuntu):** xem bảng giai đoạn trong `PLAN_ONLINE.md` — phân quyền khách/vận hành bằng PIN (backend chặn thật), giới hạn cho người lạ, triển khai systemd + udev, Cloudflare Tunnel. **Chưa có đăng nhập**: không mở ra internet trước khi làm xong phân quyền và giới hạn.

**Đóng gói:** ✅ bản mang đi = `Python/` embeddable + `launcher/` + `Cap nhat.bat`, hướng dẫn đầy đủ ở `DONG_GOI.md`. Đã thử `Python/` embeddable thật (server + nạp ảnh qua tiến trình con). Đã thử trong thư mục tạm có dấu cách: bật ẩn, lấy đúng IP LAN, máy khác gọi được, nạp ảnh (tiến trình con) chạy, tự tắt khi không có trang, `stop.ps1`, đóng gói + cập nhật (giữ data, cất bản cũ). 🧪 **Chưa thử:** máy sạch không cài gì (thư viện Visual C++ của OpenCV), nhánh `pip install` của `Cap nhat.bat` khi `requirements.txt` đổi.
