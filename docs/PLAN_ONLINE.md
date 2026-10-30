# Kế hoạch đưa ExtruXY lên MiniPC và mở cho vài người dùng

Quyết định: **MiniPC Ubuntu không màn hình** cắm USB vào mạch MKS, chạy toàn bộ backend + giao diện. Python làm hết phần nặng; JavaScript chỉ nhận những việc nhẹ mà trình duyệt làm tốt hơn hoặc ngang. Không dùng host chia sẻ (không giúp giảm tải, chỉ thêm rắc rối đăng nhập chéo tên miền). Thời gian xử lý ảnh không quan trọng, chất lượng mới quan trọng.

Ký hiệu: ✅ đã làm và test · ⏳ chưa làm · ⚠ chưa kiểm chứng.

## Giai đoạn

| # | Việc | Tình trạng |
|---|---|---|
| 1 | Đo trên MiniPC thật: thời gian từng bước, RAM, máy vẽ có giật khi đang xử lý ảnh không. `Ảnh → nét` đã tự ghi thời gian từng bước (`info.timings`, hiện trên giao diện, rê chuột vào dòng trạng thái) | ⏳ chờ máy về |
| 2 | Xử lý ảnh ở **tiến trình riêng, ưu tiên thấp** (`services/drawing/isolated.py`): hủy = kết thúc hẳn tiến trình, quá giờ (600 s) và hết RAM (4 GB, chỉ Linux) chỉ làm chết tiến trình con | ✅ (Windows đã test; ⚠ giới hạn RAM chưa thử trên Ubuntu) |
| 3 | Trình duyệt **thu nhỏ ảnh trước khi gửi** (`lib/imageprep.js`) và **xem trước độ sáng ngay khi kéo ô** (`views/drawing/tonepreview.js`). Backend vẫn nhận ảnh gốc nếu trình duyệt không làm được | ✅ |
| 4 | (Tùy chọn, chỉ khi đo ở bước 1 thấy bước sắp xếp nét lâu) 2-opt chạy trong Web Worker. Phải so kết quả với Python trên cùng ảnh, sai khác dưới 2% | ⏳ |
| 5a | **Phân quyền** (mục dưới) | ⏳ |
| 5b | **Giới hạn** cho người lạ: cỡ tệp, số lần tải trong một phút, số bản thảo và dung lượng mỗi người, hàng đợi xử lý ảnh | ⏳ |
| 5c | **Triển khai Ubuntu**: dịch vụ systemd tự khởi động lại, quyền cổng USB, tên cổng cố định, nhật ký ghi ra tệp | ⏳ |
| 5d | **Cloudflare Tunnel** (một địa chỉ cho cả giao diện và backend) | ⏳ |

Quy tắc chung: mọi bước JS đều là đường nhanh tùy chọn; **backend luôn tự làm được và luôn kiểm tra lại**, không tin dữ liệu từ trình duyệt.

## 5a. Phân quyền (theo yêu cầu của chủ dự án)

| Vai trò | Vào bằng | Được làm |
|---|---|---|
| **Khách** | Không cần | Tải ảnh/SVG lên, dùng tab Tạo bản vẽ để tạo nét, lưu bản thảo, xem bản thảo |
| **Người vận hành** | Nhập **mã PIN trong Cài đặt** | Mọi thứ còn lại: kết nối và điều khiển máy, chạy G-code, Home/Zero, cấu hình máy, thư mục bản thảo, xóa/ghim bản thảo, Hàng đợi |

Yêu cầu bắt buộc: **backend phải chặn thật**, không chỉ ẩn nút. Mọi route điều khiển máy, chạy tác vụ, cấu hình, cài đặt, xóa bản thảo đều kiểm tra phiên người vận hành. Chi tiết dự kiến:
- PIN lưu dạng băm (scrypt) trong `data/`, đặt và đổi ở Cài đặt (lần đầu: đặt PIN khi chưa có).
- Nhập đúng PIN → server cấp mã phiên ngẫu nhiên (cookie `HttpOnly`, `SameSite=Strict`, `Secure` khi qua HTTPS), hết hạn sau một thời gian không dùng; có nút Đăng xuất.
- Chặn dò PIN: sai nhiều lần thì khóa tạm theo địa chỉ, cộng độ trễ tăng dần.
- Máy thật vẫn còn lớp "Mở khóa chuyển động" như hiện nay; PIN vận hành là lớp ngoài, không thay thế lớp đó.
- Giao diện: khách thấy tab Tạo bản vẽ đầy đủ; tab Điều khiển và Cài đặt khóa kèm ô nhập PIN.
- Ghi nhật ký: ai (khách/vận hành) làm gì, giờ nào, cho các thao tác điều khiển máy.

## 5b. Giới hạn cho người lạ
Vì khách tải ảnh không cần đăng nhập, trang này nằm trên internet nên cần: giới hạn cỡ tệp (đã có 40 MB), giới hạn số lần tải và số tác vụ đang chờ, trần dung lượng bản thảo của khách, tự dọn bản thảo của khách cũ nhất, và từ chối tệp không phải ảnh thật. Xử lý ảnh vốn chỉ chạy một việc một lúc nên không thể làm sập MiniPC, nhưng hàng đợi dài sẽ làm người khác chờ lâu.

## 5c. Ubuntu không màn hình
- Chạy bằng dịch vụ systemd (`Restart=always`), tài khoản riêng không có quyền root.
- Cổng USB: tài khoản dịch vụ thuộc nhóm `dialout`; thêm quy tắc udev để mạch MKS luôn có một tên cố định (ví dụ `/dev/ttyMKS`) dù cắm lại.
- Nhật ký: ghi ra tệp, giữ 3 ngày, xoay vòng (hiện chỉ nằm trong bộ nhớ).
- Giữ nguyên thư mục `data/` khi cập nhật (bản thảo, macro, sao lưu cấu hình, cài đặt, PIN băm). Đặt `EXTRUXY_DATA_DIR` (vd `/var/lib/extruxy`) để dữ liệu nằm ngoài thư mục mã.
- `/api/storage*`, `/api/macros`, `/api/jobs/resume` cũng phải vào bảng phân quyền: khách không được xem/tải dữ liệu hệ thống hay tiếp tục tác vụ.
- ⚠ Cần thử riêng trên Ubuntu: giới hạn RAM của tiến trình xử lý ảnh (`RLIMIT_AS`), cài `opencv-python-headless` và `scikit-image`, quyền ghi thư mục bản thảo.

- ⚠ Nếu sau này đóng gói thành file exe: `isolated.py` khởi động tiến trình con bằng `python -m ...` nên bản exe phải đổi cách khởi động (hoặc đặt `EXTRUXY_DRAW_INPROC=1`). Trên Ubuntu chạy từ mã nguồn thì không vướng.

## 5d. Cloudflare Tunnel
Một tên miền trỏ vào MiniPC qua `cloudflared`, chạy như dịch vụ. Bắt buộc đã xong 5a và 5b trước khi mở ra ngoài, vì từ lúc đó ai biết địa chỉ cũng gửi được ảnh. Nếu muốn thêm một lớp ngoài cổng, có thể bật Cloudflare Access (đăng nhập bằng email) mà không phải viết thêm mã.

## Chưa quyết
- Khách xem được bản thảo của nhau hay chỉ thấy của mình? (Đề xuất: mỗi khách chỉ thấy bản thảo mình tạo trong phiên; người vận hành thấy tất cả.)
- Có cần giới hạn khung giờ cho khách không?
