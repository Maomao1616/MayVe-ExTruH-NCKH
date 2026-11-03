# Việc cần làm (tóm tắt)

Cập nhật 02/11/2026. Chỉ liệt kê, không giải thích dài. Chi tiết từng việc: [docs/FUTURE_UPGRADE_BETA.md](docs/FUTURE_UPGRADE_BETA.md) (ý tưởng, thư viện, số liệu), [docs/PLAN_ONLINE.md](docs/PLAN_ONLINE.md) (phân quyền, MiniPC, demo), [docs/KIEM_TRA_VE.md](docs/KIEM_TRA_VE.md) (cách thử trên giấy), [docs/STATUS.md](docs/STATUS.md) (cái gì xong / chưa kiểm chứng). Cách tìm code: [HUONG_DAN_DOC_CODE.md](HUONG_DAN_DOC_CODE.md).

Cỡ việc: **S** nhỏ (vài giờ) · **M** vừa (nửa đến một ngày) · **L** lớn (nhiều ngày).

## 1. Đã xong gần đây
- [x] Đăng nhập PIN: khách chỉ xem, quản lý điều khiển (PIN đặt ở `data\pin.txt`)
- [x] Đèn công tắc X / Y (hai vòng tròn ở đầu bảng Vị trí), trạng thái 10 lần/giây, vệt bút bám theo G-code
- [x] Ô "Tốc độ hạ bút" (hạ chậm, nhấc nhanh) và bút 0,5 trong danh sách chọn
- [x] Công cụ sinh G-code thử tốc độ: `python tools/make_test_gcode.py`
- [x] 03/11/2026: Z nhấc 3, tốc độ vẽ 5000, chờ 0,05 s, hạ bút 2000; Home tự nâng bút trước; khoảng cách nét tính theo nét thật 0,55 mm (1,1 mm cho bút 0,4), mặc định 5 mức; thêm bài thử 7.5 (vệt kéo)

## 2. Thử trên máy thật (không cần code)
- [ ] Đặt `data\pin.txt` (`admin=…`, `unlock=…`), vào bằng điện thoại: có ra giao diện khách không
- [ ] Tắt Wi-Fi của mạch MKS trước khi cho người khác vào mạng (không thì họ điều khiển được qua WebUI)
- [ ] Tờ hiệu chỉnh 8 dải cho từng bút (Sakura 0,4 / bi 0,5 / 0,2 nếu có), chụp ảnh gửi lại
- [ ] Thang xám 3 preset (Chân dung, Phong cảnh, Cận cảnh)
- [ ] Bài thử 7.1, 7.3, 7.4, **7.5** (nhấc bút, gia tốc, tốc độ từng bút, vệt kéo) bằng tệp trong `export\test-gcode\`, **mỗi bài một tờ giấy** (7.2 mất bước đã đạt 03/11)
- [ ] Chụp cận đo bề rộng nét ở 3000 / 5000 / 6000 mm/min (7.4), rồi in lại tờ hiệu chỉnh ở tốc độ đã chốt; sửa `LINE_WIDTH_RATIO` nếu khác 1,375
- [ ] Vẽ lại Phong cảnh với mặc định mới, so với bản cũ; chụp cận mép trên / dưới khối để xem giọt mực
- [ ] Hướng X / Y trên giấy, Z nâng / hạ thật, thời gian Home, cung G2 / G3 (MACHINE.md mục B)
- [ ] Đèn X / Y sáng đúng khi tay đè công tắc hành trình
- [ ] Đo thời gian vẽ thật so với ước tính của phần mềm; ghi vào bảng KIEM_TRA_VE mục 6, 7

## 3. Code tiếp, xếp theo ưu tiên
| # | Việc | Cỡ | Vì sao |
|---|---|---|---|
| 1 | Ghi số liệu tác vụ ra CSV (vị trí, tốc độ thật, bộ đệm `Bf`) + biểu đồ | M | Mọi số đo sau dựa vào đây; thấy chỗ máy "đói lệnh" |
| 2 | Hồ sơ tốc độ theo loại bản vẽ (Chữ / Tranh / Đẹp nhất) | S–M | Đổi gia tốc, chờ, tốc độ một lần bấm |
| 3 | Trình hiệu chỉnh nhấc bút (vẽ hàng gạch với nhiều thời gian chờ, chọn hàng đẹp) | S–M | Nhấc bút là chi phí lớn nhất khi vẽ chữ |
| 4 | Khách gửi ảnh vào `customer/` + danh sách "Khách gửi" cho quản lý | M–L | Hết cảnh gửi ảnh qua lại |
| 5 | Tab Beta in PDF: preset "Văn bản", đường kẻ vẽ bằng vector, hai bút | L | Mục tiêu chữ viết |
| 6 | Chữ PDF mức "Vừa": Sauvola, `medial_axis`, skan tỉa râu, làm mượt, `deduplicate` | M | Nét chữ sạch hơn, ít thêm RAM |
| 7 | Cảm biến bút + hai nút cứng Tạm dừng / Chạy tiếp (sửa YAML, nối dây, thêm đèn "Bút") | S + dây | An toàn, biết bút nâng thật |
| 8 | ESP32-S3: bảng điều khiển không dây, đo điện năng, đo nhiệt (chọn 1–2) | L | Phần IoT demo được |
| 9 | Vệt bút theo dòng G-code cho macro / tiếp tục tác vụ | S | Hiện chỉ áp cho tệp đang chạy |
| 10 | Mã QR địa chỉ trên giao diện, đổi PIN quản lý ngay trên giao diện | S | Demo nhanh hơn |
| 11 | Thêm `.devcontainer/` cho Codespaces | S | Bạn bè chạy thử không cần cài |

## 4. Khi có MiniPC
- [ ] Đo thời gian xử lý ảnh, RAM, máy có giật không (`info.timings`)
- [ ] Docker + quyền cổng USB + tên cổng cố định (udev), IP cố định
- [ ] Thử Origin / cookie qua Cloudflare Tunnel; chỉ mở ra ngoài khi đã đặt PIN
- [ ] Ghi số đo vào FUTURE_UPGRADE_BETA mục 13

## 5. Để dành (chưa xếp lịch)
- Tài khoản người dùng + thư mục riêng + hàng chờ nhiều người + lưu nét gốc
- Chữ viết tay (bộ chữ, lấy mẫu trên màn hình cảm ứng) và AI tạo ảnh qua mạng
- Mô hình ONNX tìm nét (TEED, Informative Drawings), đường giữa từ vector
- Camera: mã ArUco tự căn giấy, đo SSIM / OCR trên tờ đã vẽ
- Nguồn 24 V, đổi vi bước, ArcWelder (cung G2 / G3) sau khi thử cung trên máy thật

## 6. Cần bạn cung cấp / quyết
- Ảnh tờ hiệu chỉnh và số đo sau buổi thử
- Chốt: chưa đặt PIN quản lý thì cho ai vào cũng là quản lý (đang vậy) hay chặn hẳn khi mở ra ngoài
- Chọn hướng ưu tiên: chữ PDF, IoT (ESP32), hay tốc độ / chất lượng nét
- Chuẩn bị demo không mạng: router mini (hoặc 4G), in sẵn mã QR
- Dụng cụ có sẵn: máy hiện sóng, logic analyzer, ESP32-S3? (quyết định hướng đo servo)
