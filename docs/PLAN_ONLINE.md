# Kế hoạch đưa ExtruXY lên MiniPC và mở cho vài người dùng

Bản Windows mang đi (laptop, máy bạn bè): xem `DONG_GOI.md`. Tệp này chỉ cho MiniPC Ubuntu.

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
| 5c | **Triển khai Ubuntu**: Docker (đề xuất) hoặc venv + systemd, tự khởi động lại, quyền cổng USB, tên cổng cố định (udev), IP cố định trong mạng nhà | ⏳ |
| 5d | **Cloudflare Tunnel** (một địa chỉ HTTPS cho cả giao diện và backend, không mở cổng router) | ⏳ |

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

## 5c. Ubuntu không màn hình (dự kiến, ⏳ chưa thử)
Ý chính: MiniPC chạy **24/7**, cắm USB vào mạch MKS, không màn hình; quản lý qua SSH từ laptop. **Không dùng thư mục `Python/` của bản Windows** (đó là Python cho Windows, Linux không chạy được); trên Linux thư viện cài bằng pip từ `requirements.txt` trong Docker hoặc venv.

### Hai cách chạy
| | **Docker (đề xuất)** | venv + systemd |
|---|---|---|
| Cài | `docker compose up -d` | tạo venv, `pip install`, viết tệp dịch vụ systemd |
| Cập nhật | `git pull` → `docker compose up -d --build` | `git pull` → `pip install -r` → `systemctl restart` |
| Thư viện hệ thống (OpenCV) | nằm trong image, không lẫn với máy | cài thẳng vào Ubuntu |
| Cổng USB | phải đưa vào container (`devices:`), cắm lại cáp có thể phải khởi động lại container ⚠ | dùng thẳng |
| Dữ liệu | volume `./data:/data` | `EXTRUXY_DATA_DIR=/var/lib/extruxy` |

### Docker: tệp dự kiến (chưa có trong kho, viết khi MiniPC về)
`Dockerfile` (đặt ở thư mục gốc):
```dockerfile
FROM python:3.12-slim
# libglib2.0-0: OpenCV headless cần (⚠ kiểm lại khi build)
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY frontend/ frontend/
ENV EXTRUXY_DATA_DIR=/data
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
```
`docker-compose.yml`:
```yaml
services:
  plotter:
    build: .
    restart: unless-stopped          # tự bật lại khi MiniPC khởi động / server chết
    ports: ["8000:8000"]
    volumes: ["./data:/data"]        # bản thảo, macro, sao lưu nằm ngoài image: build lại không mất
    devices: ["/dev/ttyMKS:/dev/ttyMKS"]   # tên cố định do udev đặt (dưới)
    group_add: ["dialout"]
    environment:
      EXTRUXY_ALLOWED_HOSTS: "localhost,127.0.0.1,192.168.1.50,plotter.local,plotter.tenmien.com"
      EXTRUXY_UNLOCK_PIN: "doi-so-nay"
      # KHÔNG đặt EXTRUXY_IDLE_EXIT_MIN: MiniPC phải chạy suốt
```
- `.dockerignore`: `.venv`, `Python`, `data`, `export`, `_ban_cu`, `**/__pycache__`, `backend/tests`.
- `launcher/`, `Cap nhat.bat` chỉ dành cho Windows, không dùng ở đây.
- Nhật ký: `docker compose logs -f` (giữ 3 ngày: đặt `logging: {driver: json-file, options: {max-size: 10m, max-file: "3"}}`).
- Giới hạn RAM: ngoài `RLIMIT_AS` của tiến trình xử lý ảnh có thể đặt `mem_limit` cho cả container.

### Cổng USB cố định (udev, làm trên máy Ubuntu)
Mạch MKS dùng chip CH340 (thường `1a86:7523`; ⚠ kiểm bằng `lsusb` khi cắm vào MiniPC). Tạo `/etc/udev/rules.d/99-mks.rules`:
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="ttyMKS", GROUP="dialout", MODE="0660"
```
`sudo udevadm control --reload && sudo udevadm trigger`, cắm lại cáp, kiểm `ls -l /dev/ttyMKS`. Trong phần mềm chọn cổng `/dev/ttyMKS`. (Cách venv: thêm tài khoản chạy dịch vụ vào nhóm `dialout`.)

### Cách venv + systemd (nếu không dùng Docker)
`/etc/systemd/system/extruxy.service`:
```ini
[Unit]
Description=VMU PlotterPen
After=network-online.target
[Service]
User=extruxy
WorkingDirectory=/opt/extruxy/backend
Environment=EXTRUXY_DATA_DIR=/var/lib/extruxy
Environment=EXTRUXY_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50,plotter.local,plotter.tenmien.com
ExecStart=/opt/extruxy/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
Restart=always
[Install]
WantedBy=multi-user.target
```
`sudo systemctl enable --now extruxy`; xem nhật ký `journalctl -u extruxy -f`.

### Việc còn phải làm / thử
- `/api/storage*`, `/api/macros`, `/api/jobs/resume` phải vào bảng phân quyền 5a: khách không được xem/tải dữ liệu hệ thống hay tiếp tục tác vụ.
- ⚠ Thử riêng trên Ubuntu: giới hạn RAM `RLIMIT_AS`, cài `opencv-python-headless`/`scikit-image`, quyền ghi `data/`, SimLink + serial thật, thời gian xử lý ảnh trên i5-3210M (bước 1).
- ⚠ Nếu đóng gói thành exe: `isolated.py` khởi động tiến trình con bằng `python -m ...` nên phải đổi cách khởi động (hoặc `EXTRUXY_DRAW_INPROC=1`). Chạy từ mã nguồn / Docker thì không vướng.

## 5c'. Cấu hình IP trong mạng nhà (dự kiến)
Backend chặn mọi địa chỉ không có trong `EXTRUXY_ALLOWED_HOSTS` (chống DNS rebinding, `main.py`), nên **IP/tên MiniPC phải cố định** và ghi vào biến đó.

| Cách | Làm gì | Ghi chú |
|---|---|---|
| **Giữ chỗ DHCP trên router (đề xuất)** | Vào trang quản trị router (thường `192.168.1.1`) → DHCP / *Address Reservation* / *Static Lease* → chọn MAC của MiniPC → gán `192.168.1.50` | không phải sửa gì trên Ubuntu; đổi router thì làm lại |
| IP tĩnh trên Ubuntu | sửa `/etc/netplan/*.yaml`: `dhcp4: no`, `addresses: [192.168.1.50/24]`, `routes: [{to: default, via: 192.168.1.1}]`, `nameservers: {addresses: [1.1.1.1]}` → `sudo netplan apply` | chọn IP ngoài dải DHCP của router để khỏi trùng |
| Tên `plotter.local` | `sudo hostnamectl set-hostname plotter` + `sudo apt install avahi-daemon` | Windows 10/11, điện thoại đa số mở được `http://plotter.local:8000`; vẫn nên giữ IP cố định làm dự phòng |

Sau đó: thêm IP và tên vào `EXTRUXY_ALLOWED_HOSTS` (hoặc tạm `"*"` khi thử, **không dùng `*` khi mở ra internet**). Tường lửa Ubuntu (`ufw`): chỉ mở 8000 cho mạng nhà, `sudo ufw allow from 192.168.1.0/24 to any port 8000`; khi đã dùng Cloudflare Tunnel thì không cần mở cổng nào ra ngoài.

## 5d. Cloudflare Tunnel (dự kiến, ⏳ chưa thử)
**Là gì:** chương trình `cloudflared` chạy trên MiniPC **tự gọi ra** máy chủ Cloudflare và giữ một đường hầm; người ngoài vào `https://plotter.tenmien.com` thì Cloudflare chuyển qua đường hầm tới `http://localhost:8000`. **Không mở cổng router, không cần IP tĩnh công cộng**, có sẵn HTTPS.

**Điều kiện trước:** xong 5a (PIN vận hành, backend chặn thật) và 5b (giới hạn khách). Từ lúc mở, ai biết địa chỉ cũng gửi được ảnh.

**Cần:** một tên miền (mua ở đâu cũng được) đã chuyển DNS về Cloudflare (tài khoản miễn phí đủ dùng).

**Các bước (trên MiniPC):**
1. Cài: `sudo apt install cloudflared` (theo hướng dẫn kho gói của Cloudflare) hoặc chạy bằng Docker image `cloudflare/cloudflared`.
2. Đăng nhập: `cloudflared tunnel login` (mở đường link trên laptop, chọn tên miền).
3. Tạo đường hầm: `cloudflared tunnel create plotter` → ghi lại mã đường hầm, tệp khóa nằm ở `~/.cloudflared/<mã>.json`.
4. Trỏ tên: `cloudflared tunnel route dns plotter plotter.tenmien.com`.
5. Tệp `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <mã>
   credentials-file: /home/<user>/.cloudflared/<mã>.json
   ingress:
     - hostname: plotter.tenmien.com
       service: http://localhost:8000
     - service: http_status:404
   ```
6. Chạy như dịch vụ: `sudo cloudflared service install` (hoặc thêm một service `cloudflared` vào `docker-compose.yml`, `command: tunnel run`, mạng chung với `plotter` → `service: http://plotter:8000`).
7. Thêm `plotter.tenmien.com` vào `EXTRUXY_ALLOWED_HOSTS`, khởi động lại server.

**Khớp với backend hiện có:**
- `cloudflared` giữ nguyên Host `plotter.tenmien.com` → phải có trong `EXTRUXY_ALLOWED_HOSTS`, nếu không trang báo `bad_host`.
- Trình duyệt gửi `Origin: https://plotter.tenmien.com` → khớp Host → lớp chặn "Origin lạ" của `main.py` vẫn cho qua. Không cần sửa mã.
- Cookie phiên PIN (5a) phải có `Secure` khi chạy qua HTTPS.
- Phần mềm hỏi `/api/status` mỗi 0,4 s cho mỗi trang mở: qua tunnel vẫn chạy, nhưng nhiều khách cùng lúc thì nên giãn nhịp cho khách (5b).
- Tải ảnh lớn: gói Cloudflare miễn phí giới hạn **100 MB/yêu cầu**; trần của phần mềm là 64 MB (`MAX_BODY_BYTES`) và 40 MB/ảnh nên không vướng.

**Thêm một lớp ngoài cổng (không viết mã):** Cloudflare Zero Trust → Access → Application → `plotter.tenmien.com` → chỉ cho các email được duyệt (gửi mã qua email). Có thể chỉ khóa đường dẫn điều khiển và để trang vẽ mở cho khách.

## Chưa quyết
- Khách xem được bản thảo của nhau hay chỉ thấy của mình? (Đề xuất: mỗi khách chỉ thấy bản thảo mình tạo trong phiên; người vận hành thấy tất cả.)
- Có cần giới hạn khung giờ cho khách không?
