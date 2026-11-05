# 11 — Tình trạng và việc cần làm

> Sổ làm việc, cập nhật 05/11/2026. Một nơi duy nhất cho "cái gì xong / chưa kiểm chứng / còn phải làm".
> Cỡ việc: **S** vài giờ · **M** nửa đến một ngày · **L** nhiều ngày.

## 1. Tình trạng chung
| Khối | Tính năng | Đã kiểm ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95 % | ~65 % |
| Tạo bản vẽ (ảnh, SVG, bản thảo, hàng đợi) | ~92 % | ~50 % |
| Cài đặt, cấu hình máy | ~90 % | ~70 % |
| Phân quyền, bản mang đi | ~85 % | ~60 % |

Test tự động: máy chủ ~397 bài (`python -m pytest` trong `backend`), giao diện 33 bài. Thiếu chủ yếu là **in thật trên giấy** và **thử trên MiniPC**.

Mục tiêu trước mắt cho phần web điều khiển: chốt thông số chuẩn bằng bản in → đo thời gian thật → (nếu có) tab Beta → MiniPC + Docker + Cloudflare. Camera, nút cứng, ESP32 thêm lúc nào cũng được.

## 2. Đã xong gần đây
- [x] 05/11: hướng trục X / Y trên giấy **đúng** (chủ dự án xác nhận).
- [x] 03–04/11: thuật toán tô mới (mỗi mức một dải, khoảng cách theo nét thật, quay đầu nửa vòng tròn, xoắn ốc nối khe), viền cắt râu + khép vòng + làm phẳng màu, bộ mô phỏng mực `tools/ink_sim.py`.
- [x] 03/11: Z nhấc 3, vẽ 5000, chờ 0,05 s, hạ bút 2000; Home tự nâng bút; khoảng cách nét theo nét thật 0,55 mm; bài thử 7.5.
- [x] 02/11: đăng nhập PIN (khách chỉ xem), đèn công tắc X / Y, trạng thái 10 lần / giây, vệt bút bám G-code, ô tốc độ hạ bút, bút 0,5, công cụ sinh G-code thử tốc độ.

## 3. Thử trên máy thật (không cần code)
Cách làm từng bài ở [07_THU_NGHIEM.md](07_THU_NGHIEM.md); làm xong chép mẫu ở 07 mục 8, điền số, gửi kèm ảnh.

- [ ] Đặt `data\pin.txt` (`admin=…`, `unlock=…`) bằng **số khó đoán**; vào bằng điện thoại xem có ra giao diện khách.
- [ ] Tắt Wi-Fi của mạch MKS trước khi cho người khác vào mạng.
- [ ] Bài 7.4: chụp cận đo bề rộng nét ở 3000 / 5000 / 6000 → in lại tờ hiệu chỉnh ở tốc độ đã chốt → sửa `LINE_WIDTH_RATIO` nếu khác 1,375.
- [ ] Thang xám 3 preset (Chân dung, Phong cảnh, Cận cảnh).
- [ ] Vẽ lại Phong cảnh với mặc định mới; chụp cận mép khối xem còn giọt mực ở chỗ quay đầu không.
- [ ] Bài 7.1 (đo thời gian một chu kỳ nhấc bút), 7.3 (gia tốc), 7.5 (vệt kéo), mỗi bài một tờ.
- [ ] Thời gian Home, Z nâng / hạ thật, cung G2 / G3.
- [ ] Đèn X / Y sáng đúng khi tay đè công tắc.
- [ ] Tiếp tục từ điểm dừng trên máy thật: hủy giữa chừng → Home → Tiếp tục, so nét chồng.
- [ ] Đo thời gian vẽ thật so với ước tính; ghi vào [07_THU_NGHIEM.md](07_THU_NGHIEM.md) mục 7.

## 4. Chưa kiểm chứng (cần máy hoặc môi trường thật)
| Việc | Cách kiểm |
|---|---|
| Khoảng cách nét / số mức / gamma từng preset | thang xám + ảnh thật ([07_THU_NGHIEM.md](07_THU_NGHIEM.md)) |
| Quay đầu nửa vòng tròn có hết giọt mực | chụp cận |
| `G4 P` tính bằng giây trên FluidNC 4.1.1 | đo |
| Thời gian ước tính (chưa tính gia tốc) | so với thời gian thật, thêm hệ số |
| Biên lùi 64 dòng khi tiếp tục có đủ | hủy bản vẽ dài, tiếp tục |
| Xử lý ảnh trên MiniPC i5-3210M; giới hạn RAM trên Ubuntu | `info.timings`, `htop` |
| Chia màu với ảnh có màu rất nhỏ | ảnh nhiều màu nền sáng |
| Giao diện trên điện thoại thật (cắt ảnh bằng ngón tay, hộp "Tác vụ đã dừng") | điện thoại |
| Bản mang đi trên máy sạch (Visual C++ của OpenCV) | máy bạn bè |

## 5. Code tiếp, xếp theo ưu tiên
| # | Việc | Cỡ | Vì sao |
|---|---|---|---|
| 1 | Ghi số liệu tác vụ ra CSV (giờ, trạng thái, vị trí, tốc độ thật `FS:`, bộ đệm `Bf:`) + biểu đồ | M | mọi số đo sau dựa vào đây; thấy chỗ máy "đói lệnh"; tự chỉnh hệ số ước tính |
| 2 | Đường cong tông từ thang xám in thật | S | tông giữa đúng với mắt (cần tờ in trước) |
| 3 | Hồ sơ tốc độ theo loại bản vẽ (Chữ / Tranh / Đẹp nhất) | S–M | đổi gia tốc, chờ, tốc độ một lần bấm |
| 4 | Trình hiệu chỉnh nhấc bút (hàng gạch nhiều mức chờ, chọn hàng đẹp) | S–M | nhấc bút là chi phí lớn nhất khi vẽ chữ |
| 5 | Khách gửi ảnh vào `customer/` + danh sách cho quản lý | M–L | hết cảnh gửi ảnh qua lại ([08_TRIEN_KHAI.md](08_TRIEN_KHAI.md) B4) |
| 6 | Tab Beta in PDF: preset "Văn bản", đường kẻ vector, hai bút | L | mục tiêu chữ viết ([10_HUONG_PHAT_TRIEN.md](10_HUONG_PHAT_TRIEN.md) 1.1) |
| 7 | Cảm biến bút + hai nút cứng Tạm dừng / Chạy tiếp (YAML + dây, đèn "Bút") | S + dây | an toàn, biết bút nâng thật |
| 8 | ESP32-S3: bảng điều khiển không dây, đo điện năng, đo nhiệt (chọn 1–2) | L | phần IoT trình diễn được |
| 9 | Tự hiệu chỉnh bằng ảnh chụp tờ mẫu (ArUco) | M | khỏi đo tay bề rộng nét |
| 10 | Mã QR địa chỉ, đổi PIN trên giao diện, `.devcontainer/` | S | demo nhanh hơn |

## 6. Khi có MiniPC
- [ ] Đo thời gian xử lý ảnh, RAM, máy có giật không.
- [ ] Docker + quyền cổng USB + tên cổng cố định (udev), IP cố định.
- [ ] Thử Origin / cookie qua Cloudflare Tunnel; chỉ mở ra ngoài khi đã đặt PIN.

## 7. Cần bạn cung cấp / quyết
- Ảnh tờ hiệu chỉnh, thang xám và số đo sau mỗi buổi thử.
- Chưa đặt PIN quản lý thì cho ai vào cũng là quản lý (đang vậy) hay chặn hẳn khi mở ra ngoài.
- Hướng ưu tiên tiếp: chữ PDF, IoT (ESP32), hay tốc độ / chất lượng nét.
- Thiết bị demo không mạng: router mini (hoặc 4G), in sẵn mã QR.
- Dụng cụ đo có sẵn: máy hiện sóng, logic analyzer?
