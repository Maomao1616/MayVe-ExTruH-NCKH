# STATUS — tình trạng và việc còn lại (cập nhật 30/10/2026)

Một nơi duy nhất cho "cái gì xong / chưa / chưa kiểm chứng". Ký hiệu: ✅ xong và có test · 🧪 xong nhưng **chưa kiểm chứng trên máy/môi trường thật** · ⏳ chưa làm · ❌ đã bỏ.
Mục tiêu hiện tại: **một trình điều khiển máy vẽ chạy trên laptop**. Docker, AI nhận diện ngôn ngữ tự nhiên: ngoài phạm vi.

## 1. Tổng quan
| Khối | Tính năng | Kiểm chứng ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95% | ~60% |
| Tạo bản vẽ (SVG, ảnh, bản thảo, hàng đợi) | ~90% | ~45% |
| Cài đặt, hồ sơ máy, cấu hình YAML | ~90% | ~70% |
| Tài liệu, test | ~90% | |

Tổng: khoảng 88–90% tính năng, 60–65% kiểm chứng. Thiếu chủ yếu là thử máy thật và thử nhiều ảnh thật. Test tự động: backend 276 (`python -m pytest`), frontend 15 (`node --test ...`).

## 2. Đã xong
**Điều khiển:** kết nối SimLink/Serial, trạng thái 0,5 s, jog (`$J`), Home, Zero, thanh bút 3 nấc, nạp + xem trước + chạy G-code từng dòng chờ `ok`, ghi đè tốc độ, hủy 3 chế độ (reset/soft/hard) với xác nhận nâng bút, terminal, dock macro, mở khóa chuyển động có hẹn giờ + PIN tùy chọn, hàng đợi công việc.
**Cài đặt:** kết nối nhớ cổng, hoạt động, cấu hình máy (đọc/áp dụng/lưu YAML trên mạch, sao lưu, hoàn tác), hồ sơ phần mềm, thư mục và hạn mức bản thảo.
**Tạo bản vẽ:** SVG (vpype) và ảnh PNG/JPG/WEBP; khổ A6/A5/A4 + tùy chọn; ba kiểu tô (zigzag, sóng, xoắn ốc) + viền + phủ viền; 2–4 màu (mỗi màu một tệp G-code, tên có mã màu); 3 preset (Chân dung, Phong cảnh, Mạch điện/Bản vẽ); canvas kéo/co giãn/xoay/hít lề; tự tạo lại nét khi kéo khung lệch >12%; tự cân sáng; xử lý ảnh ở tiến trình riêng ưu tiên thấp (hủy sạch, giới hạn thời gian/RAM); trình duyệt thu nhỏ ảnh trước khi gửi và xem trước độ sáng ngay; bản thảo trên đĩa (ghim, ưu tiên, tự dọn); thời gian từng bước.
**Giao diện:** hai theme, hai ngôn ngữ (vi/en), thương hiệu VMU PlotterPen, bố cục tab Điều khiển (trạng thái một dòng, jog + tọa độ, 2D + tiến trình, terminal dài chạm hàng đợi), hiệu ứng (tắt khi hệ điều hành bật giảm chuyển động).
❌ Đã bỏ: thẻ SD/Flash, tab Công việc, stipple/TSP art, giao diện cắt ảnh (backend vẫn nhận `crop_*`).

## 3. Chưa kiểm chứng (🧪) — cần máy thật hoặc môi trường thật
| Việc | Cách kiểm |
|---|---|
| Hướng trục X+/Y+ trên giấy, `VIEW.flipX/flipY` (`core/config.js`) | vẽ vuông có đánh dấu góc |
| Z bút lên/xuống thật, nâng bút sau Dừng gấp thật sự xảy ra | quan sát |
| Thời gian Home, cung G2/G3, `G4 P` tính bằng giây trên FluidNC 4.1.1 | đo |
| Thời gian ước tính (chưa tính gia tốc) | so với thời gian chạy thật vài lần, thêm hệ số |
| Khoảng cách gạch mặc định (2 × bề rộng bút), 3 preset, ngưỡng viền (`edges.py`), góc 45° | vẽ dải đậm nhạt mẫu bút 0,2 và 0,4, chỉnh `presets.js`/`spec.py` |
| Xử lý ảnh trên MiniPC i5-3210M (đo `info.timings`, RAM, máy có giật không) | chạy ảnh mẫu |
| Giới hạn RAM `RLIMIT_AS` của tiến trình xử lý ảnh, cài `opencv-python-headless`/`scikit-image` trên Ubuntu | thử trên Ubuntu |
| Chia màu với ảnh có màu rất nhỏ (ảnh đêm: đèn cam bị gộp) | thử ảnh nền sáng nhiều màu |

## 4. Việc còn lại
**Cho mục tiêu "chạy trên laptop":**
| # | Việc | Ghi chú |
|---|---|---|
| 1 | Nhật ký hệ thống ghi ra tệp, xoay vòng giữ 3 ngày | hiện chỉ nằm trong bộ nhớ |
| 2 | "Tiếp tục từ dòng N" khi giữa chừng hết mực / xô giấy | bản chân dung chạy 15–25 phút |
| 3 | Test cho `frontend/js/lib/gcode.js` (bộ đọc G-code, quyết định xem trước và cảnh báo) | chưa có test JS |
| 4 | Nút tạo tệp mẫu dải đậm nhạt để hiệu chỉnh bút | hỗ trợ việc thử máy thật |
| 5 | (Tùy chọn) làm `clean_gcode` chặn thêm `G92/G10/G28/G53` | hiện chỉ chặn `$` và ký tự realtime |
| 6 | (Tùy chọn) thời gian ước tính có gia tốc | cần số liệu máy thật |
| 7 | Kiểm tra giao diện ở màn hình hẹp sau lần chia lại bố cục | chủ yếu kiểm trên màn hình rộng |
| 8 | (Tùy chọn) giao diện cắt ảnh | người dùng đã chỉnh vùng cần vẽ trước khi gửi |

**Để mở cho nhiều người dùng (MiniPC Ubuntu):** xem bảng giai đoạn trong `PLAN_ONLINE.md` — phân quyền khách/vận hành bằng PIN (backend chặn thật), giới hạn cho người lạ, triển khai systemd + udev, Cloudflare Tunnel. **Chưa có đăng nhập**: không mở ra internet trước khi làm xong phân quyền và giới hạn.

**Đóng gói:** chưa làm exe. Cách nhẹ nhất: thư mục "mang đi" có sẵn Python và thư viện, kèm `Bat Khien EXTRUH.bat`. PyInstaller `--onedir` làm được nhưng `isolated.py` khởi động tiến trình con bằng `python -m` nên bản exe phải đổi cách khởi động hoặc đặt `EXTRUXY_DRAW_INPROC=1`.
