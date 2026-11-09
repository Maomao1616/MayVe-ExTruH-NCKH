# 01 — Tổng quan dự án VMU PlotterPen

> Dành cho người đọc, kể cả người không học lập trình. Đọc tệp này trước, rồi đi theo bảng "Đọc gì tiếp" ở mục 6.

## 1. Dự án là gì

**VMU PlotterPen** (thư mục `ExtruXY`) là một **máy vẽ bằng bút** tự làm, kèm **phần mềm điều khiển chạy trên trình duyệt web**.
- Người dùng đưa vào một ảnh chụp, một hình vẽ hoặc tệp SVG.
- Phần mềm biến ảnh thành các **đường nét**, rồi thành **G-code** (danh sách lệnh "đi tới tọa độ này, hạ bút, nhấc bút").
- Máy cầm bút kéo trên giấy theo G-code và vẽ lại bức ảnh.

Mục tiêu: một **sản phẩm thật chạy được**, tích hợp IoT (điều khiển qua mạng, nhiều người xem), tối ưu cho phần cứng rẻ. Buổi trình diễn phải chạy **không cần Internet** (tự phát Wi-Fi). Đây là đề tài nghiên cứu cấp trường, khoa Điện tử.

## 2. Hệ thống gồm những gì

```
 ┌──────────────┐  Wi-Fi / mạng LAN   ┌──────────────────────────┐   cáp USB   ┌────────────────────┐
 │ Điện thoại,  │ ─────────────────►  │ Máy chủ (laptop / MiniPC) │ ──────────► │ Mạch MKS DLC32 V2.1 │
 │ laptop khác  │   trình duyệt web   │  phần mềm Python          │  (CH340)    │ firmware FluidNC    │
 └──────────────┘                     └──────────────────────────┘             └─────────┬──────────┘
                                                                                         │
                                                            2 động cơ bước (X, Y) + servo nâng bút (Z)
                                                                                         │
                                                                              khung CoreXY + bút + giấy
```

| Khối | Là gì | Chi tiết ở |
|---|---|---|
| **Cơ khí** | khung CoreXY (dựa trên mẫu Extruh pen plotter), vùng vẽ 285 × 318 mm, giấy A6 / A5 / A4. Bút **hạ bằng trọng lực**, servo chỉ nâng bút lên | [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) |
| **Điện tử** | mạch MKS DLC32 V2.1, 2 driver TMC2209, 2 động cơ NEMA17, servo 9 g, nguồn 12 V 6 A | [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) |
| **Firmware** | FluidNC v4.1.1 (có sẵn, **không sửa**). Nhận G-code qua USB, điều khiển động cơ | [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) |
| **Máy chủ** | chương trình Python (FastAPI). Giữ cổng USB, xử lý ảnh, sinh G-code, gửi từng dòng cho máy, kiểm an toàn | [03_CAU_TRUC_PHAN_MEM.md](03_CAU_TRUC_PHAN_MEM.md) |
| **Giao diện** | trang web (HTML, CSS, JavaScript thuần, không framework). Chỉ hiển thị và gửi yêu cầu cho máy chủ | [03_CAU_TRUC_PHAN_MEM.md](03_CAU_TRUC_PHAN_MEM.md) |

Quy tắc quan trọng nhất: **giao diện không bao giờ tự nói chuyện với máy vẽ.** Mọi lệnh đi qua máy chủ, máy chủ kiểm lại cho an toàn.

## 3. Ba tab của giao diện

| Tab | Việc | Tài liệu |
|---|---|---|
| **Điều khiển** | kết nối, xem trạng thái, jog, Home, đặt gốc, nâng hạ bút, nạp + xem trước + chạy G-code, hủy an toàn, tiếp tục từ điểm dừng, terminal, macro, hàng đợi | [04_TAB_DIEU_KHIEN.md](04_TAB_DIEU_KHIEN.md) |
| **Tạo bản vẽ** | ảnh / SVG → nét (zigzag, sóng, xoắn ốc, viền; 1–4 màu) → đặt lên giấy → G-code → lưu bản thảo. **Không bao giờ gọi máy** | [05_TAB_TAO_BAN_VE.md](05_TAB_TAO_BAN_VE.md), [06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md) |
| **Cài đặt** | cổng kết nối, ngôn ngữ, giao diện sáng / tối, cấu hình máy (đọc / ghi cấu hình trên mạch qua USB), hồ sơ bút, hạn mức bản thảo, xem dữ liệu | [03_CAU_TRUC_PHAN_MEM.md](03_CAU_TRUC_PHAN_MEM.md) mục 7 |

Hai tab chính nối nhau qua **bản thảo trên đĩa**:
```
Tạo bản vẽ  ──lưu──►  bản thảo (G-code + ảnh minh họa)  ──nạp──►  Điều khiển  ──xem trước + xác nhận──►  chạy
```

## 4. Hai vai trò người dùng

| | Khách (không đăng nhập) | Quản lý (nhập PIN) |
|---|---|---|
| Xem trạng thái máy, xem trước G-code, xem trước ảnh | ✔ | ✔ |
| **Gửi ảnh cho chủ máy** (cắt, khổ giấy, tông, kiểu nét mong muốn; chỉ xem trước ảnh xám) | ✔ | – |
| Hộp thư "Ảnh khách gửi", tạo nét, lưu bản thảo, điều khiển máy, cấu hình | ✘ | ✔ |

PIN đặt trong tệp `data\pin.txt` (không lên Git). Chưa đặt PIN thì ai vào cũng là quản lý. Chi tiết: [08_TRIEN_KHAI.md](08_TRIEN_KHAI.md) phần B.

## 5. Từ điển nhanh

| Từ | Nghĩa |
|---|---|
| **CoreXY** | kiểu khung hai động cơ cố định cùng kéo một dây đai chung; đầu bút chạy nhanh, nhẹ |
| **G-code** | ngôn ngữ lệnh của máy CNC / máy vẽ: `G0` chạy nhanh không vẽ, `G1` chạy có vẽ, `Z` nâng hạ bút, `F` tốc độ (mm/phút) |
| **FluidNC** | firmware chạy trên mạch, nhận G-code và điều khiển động cơ |
| **Home** | chạy về công tắc hành trình để máy biết mình đang ở đâu |
| **Zero / gốc làm việc** | đặt điểm (0,0) của bản vẽ tại chỗ bút đang đứng |
| **Jog** | đẩy đầu bút đi một đoạn bằng tay |
| **Feed Hold** | tạm dừng giữa chừng (byte `!`), chạy tiếp bằng `~` |
| **Alarm** | máy tự khóa vì lỗi (chạm công tắc, chưa Home…); gỡ bằng `$X` |
| **Bản thảo** | một bản vẽ đã lưu: G-code + ảnh minh họa + thông số |
| **Nét (stroke)** | một đường liền bút không nhấc, là một dãy điểm (x, y) tính bằng mm |
| **Mặt nạ (mask)** | ảnh đen trắng: điểm nào vẽ / bỏ |
| **Skeleton** | đường giữa rộng 1 điểm ảnh của một nét dày |
| **API / route** | một "đường gọi" của máy chủ, vd `POST /api/jobs` |
| **Máy giả (SimLink)** | máy FluidNC bắt chước trong phần mềm, dùng khi chưa cắm máy thật |

## 6. Đọc gì tiếp

Tài liệu đánh số từ nhỏ đến lớn. Người đọc lần đầu đi theo thứ tự; người viết báo cáo dùng mục "Dùng cho báo cáo".

| # | Tệp | Nội dung | Dùng cho báo cáo |
|---|---|---|---|
| 01 | **Tổng quan** (tệp này) | dự án là gì, hệ thống, các tab, từ điển | Giới thiệu |
| 02 | [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) | linh kiện, thông số, cấu hình FluidNC, hành vi firmware đã xác nhận, kết quả thử máy | Thiết kế phần cứng |
| 03 | [03_CAU_TRUC_PHAN_MEM.md](03_CAU_TRUC_PHAN_MEM.md) | cây thư mục, frontend, backend, luồng dữ liệu, dữ liệu trên đĩa, cách tìm / sửa mã, kiểm tra | Kiến trúc phần mềm |
| 04 | [04_TAB_DIEU_KHIEN.md](04_TAB_DIEU_KHIEN.md) | nút, luồng lệnh, gửi G-code, dừng an toàn, tiếp tục | Điều khiển, an toàn |
| 05 | [05_TAB_TAO_BAN_VE.md](05_TAB_TAO_BAN_VE.md) | nút, preset, luồng dữ liệu, tham số, API, bản thảo | Phần mềm tạo bản vẽ |
| 06 | [06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md) | **chi tiết thuật toán ảnh → nét**, thư viện dùng / không dùng / có thể thêm | Thuật toán (phần chính) |
| 07 | [07_THU_NGHIEM.md](07_THU_NGHIEM.md) | cách thử trên giấy, bài thử tốc độ, bảng ghi kết quả | Thực nghiệm |
| 08 | [08_TRIEN_KHAI.md](08_TRIEN_KHAI.md) | bản mang đi Windows, phân quyền, mạng / demo, MiniPC, Cloudflare | Triển khai, IoT |
| 09 | [09_QUYET_DINH_THIET_KE.md](09_QUYET_DINH_THIET_KE.md) | chọn gì, vì sao | Lý do lựa chọn |
| 10 | [10_HUONG_PHAT_TRIEN.md](10_HUONG_PHAT_TRIEN.md) | ý tưởng để dành: tab Beta PDF, chữ tay, IoT, ESP32 | Hướng phát triển |
| 11 | [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md) | tình trạng, việc cần làm, cần bạn quyết | (sổ làm việc) |
| AI | [AI_START.md](AI_START.md), [AI_CODEMAP.md](AI_CODEMAP.md) | **chỉ cho AI**: quy tắc, bẫy, bản đồ mã sinh tự động | không |

Cài đặt và chạy phần mềm: [README.md](../README.md) ở thư mục gốc.
