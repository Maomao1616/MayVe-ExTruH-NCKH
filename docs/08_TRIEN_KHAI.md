# 08 — Triển khai: bản mang đi, phân quyền, mạng, MiniPC, Cloudflare

> Dành cho người dùng và người đóng gói. Các phần độc lập, đọc phần mình cần.
> Ký hiệu: ✅ đã làm và thử · 🧪 làm rồi, chưa thử môi trường thật · ⏳ chưa làm (kế hoạch).

**Mục lục**
- A. Bản mang đi Windows (máy không cài Python) ✅
- B. Phân quyền khách / quản lý ✅ (khách gửi ảnh ⏳)
- C. Mạng LAN, phát 4G, demo không Internet
- D. Chạy tay không dùng launcher, GitHub Codespaces
- E. MiniPC Ubuntu (Docker, cổng USB, IP cố định) ⏳
- F. Cloudflare Tunnel ⏳
- G. Còn phải thử

---

# A. Bản mang đi Windows ✅

## A1. Gồm gì
```
ExtruXY/
├─ Python/          Python 3.12 embeddable 64-bit + pip + thư viện (không lên Git, vài trăm MB)
├─ backend/ frontend/
├─ launcher/        start.vbs · start.ps1 · stop.vbs · stop.ps1 · tao_bieu_tuong.vbs · cap_nhat.ps1 · icon.ico
├─ data/            dữ liệu của bạn (tự tạo, không lên Git)
├─ Cap nhat.bat     cập nhật mã, giữ nguyên Python/ và data/
└─ tools/dong_goi.ps1   (máy phát triển) tạo zip bản cập nhật / bản đầy đủ vào export/
```
Máy dùng **không cần cài Python, venv hay Git**. Chỉ chạy trên Windows 64-bit. Launcher tìm Python theo thứ tự `Python\python.exe` → `backend\.venv\Scripts\python.exe`.

## A2. Chuẩn bị `Python/` (một lần, trên máy phát triển)
1. Tải *Windows embeddable package (64-bit)* Python **3.12.x** ở python.org, giải nén vào `Python/`.
2. Sửa `Python/python312._pth` thành đúng 4 dòng: `python312.zip`, `.`, `..\backend`, `import site`. Thiếu `..\backend` thì server và tiến trình con xử lý ảnh không tìm thấy mã.
3. Ở thư mục gốc:
   ```powershell
   Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile .\Python\get-pip.py
   .\Python\python.exe .\Python\get-pip.py
   .\Python\python.exe -m pip install --no-warn-script-location -r backend\requirements.txt
   .\Python\python.exe -c "import fastapi, cv2, vpype; print('ok')"
   ```

## A3. Chuyển sang máy khác
| Cách | Gửi gì |
|---|---|
| GitHub + zip Python | người nhận tải *Code → Download ZIP*; bạn gửi thêm zip `Python/` (Drive hoặc GitHub **Releases**, tối đa 2 GB / tệp) |
| Một zip đầy đủ | `powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1 -Kieu daydu` → `export\VMU_PlotterPen_daydu-<ngày>.zip` |

Người nhận: chuột phải zip → Properties → **Unblock** → giải nén (zip Python giải nén **vào trong** thư mục mã, cạnh `backend\`) → bấm `launcher\tao_bieu_tuong.vbs` **một lần** → bấm icon **VMU PlotterPen** → lần đầu cho phép tường lửa ở **Mạng riêng tư**. 🧪 Máy sạch có thể đòi cài *Microsoft Visual C++ Redistributable x64* cho OpenCV.

## A4. Dùng hằng ngày
| Việc | Làm gì |
|---|---|
| Bật | bấm icon. Server chạy ẩn, trình duyệt mở `http://<IP LAN>:8000` |
| Tắt | không cần: đóng hết trang 10 phút thì tự tắt (đang vẽ thì chờ xong). Tắt ngay: `launcher\stop.vbs` |
| Máy khác cùng mạng | mở đúng địa chỉ trình duyệt đang hiện. Đã đặt PIN quản lý thì máy khác vào là khách |
| **Đặt PIN** | mở / tạo `data\pin.txt`, dòng `admin=<PIN>` (chữ / số / ký hiệu, 4–64 ký tự, không khoảng trắng, không dấu tiếng Việt). Từ 09/11/2026 có thể **đổi ngay trong Cài đặt → PIN quản lý** (nhập PIN cũ + PIN mới hai lần; áp dụng ngay, các trình duyệt khác bị đăng xuất; chưa có PIN thì chỉ cần nhập PIN mới). PIN mở khóa chuyển động (`unlock=`) **không dùng**: không ghi dòng đó thì bấm mở khóa là mở luôn. Tệp này không lên Git, không vào bản đóng gói. **Đừng dùng số dễ đoán** khi cho người ngoài vào mạng |
| Đổi icon | `launcher\icon.ico` phải là tệp .ico thật (đổi đuôi .png không hiện). Chuyển bằng Pillow rồi bấm lại `tao_bieu_tuong.vbs` |

## A5. Cập nhật bằng `Cap nhat.bat`
Người đóng gói: `powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1` → `export\VMU_PlotterPen_capnhat-<ngày-giờ>.zip` (~0,3 MB: `backend/`, `frontend/`, `launcher/`).
Người dùng: Unblock zip → chép **nguyên tệp zip** cạnh `Cap nhat.bat` → bấm đúp → chờ **XONG** → bấm icon (Ctrl+F5 nếu giao diện còn cũ).

`Cap nhat.bat`: tắt server → giải nén vào thư mục tạm, kiểm có `backend\app\main.py` và `frontend\index.html` → cất bản đang dùng vào `_ban_cu\` → thay `backend\ frontend\ launcher\` (không đụng `Python\`, `data\`, `.venv`) → `requirements.txt` đổi thì tự `pip install` (**cần Internet**). Quay lại bản cũ: tắt server, chép ba thư mục trong `_ban_cu\` ra.

## A6. Khi có lỗi
| Hiện tượng | Cách xử lý |
|---|---|
| "Server khong bat len duoc" kèm `No module named …` | `Python\` thiếu thư viện → chạy lại lệnh pip ở A2 |
| `Khong tim thay …\Python\python.exe` | thư mục `Python` sai chỗ / sai tên |
| Trang báo `bad_host` | mở bằng địa chỉ lạ: dùng địa chỉ trình duyệt tự mở, hoặc `http://localhost:8000` trên chính máy đó |
| Máy khác không vào được | tường lửa chặn `python.exe` (cho phép ở Private), hoặc khác mạng |
| Cổng 8000 bị chiếm | tắt chương trình đó, hoặc sửa `$port` trong `start.ps1` và `stop.ps1` |
| Lỗi khác | xem `data\server-loi.txt` |

Ghi chú kỹ thuật: `start.ps1` đặt `EXTRUXY_ALLOWED_HOSTS=localhost,127.0.0.1,<IP>`, `EXTRUXY_DATA_DIR`, `EXTRUXY_IDLE_EXIT_MIN=10`, chạy uvicorn `--host 0.0.0.0 --port 8000`. Chọn IP: card mạng có tuyến ra router ưu tiên cao nhất, bỏ `169.254.x.x`. Tệp `launcher/*.ps1, *.vbs` viết ASCII không dấu (PowerShell 5.1 đọc UTF-8 không BOM sai dấu).

---

# B. Phân quyền khách / quản lý

## B1. Nguyên tắc ✅
- Máy vẽ chỉ có một. Người cần vẽ liên hệ chủ máy; chủ máy đặt giấy, bút, tạo nét, bấm chạy.
- **Máy chủ chặn thật**, giao diện chỉ ẩn nút cho gọn.
- **Chặn mặc định**: route nào không nằm trong danh sách mở cho khách thì cần quản lý. Route mới thêm sau này tự bị chặn.

## B2. Hai vai trò ✅
| | Khách (không đăng nhập) | Quản lý (PIN) |
|---|---|---|
| Xem trạng thái máy, tiến độ, đèn công tắc | ✔ chỉ đọc | ✔ |
| Nạp G-code, xem trước khung (chạy trong trình duyệt) | ✔ | ✔ |
| Tải ảnh, cắt, xem trước sáng tối, chọn khổ giấy (trong trình duyệt) | ✔ | ✔ |
| Gửi ảnh cho người vận hành (`customer/`) | ⏳ | – |
| Tạo nét, G-code, bản thảo | ✘ | ✔ |
| Điều khiển máy, terminal, macro, cấu hình, lưu trữ | ✘ | ✔ |

## B3. Đăng nhập quản lý ✅ (`app/auth.py`, `api/auth.py`, `core/auth.js`, `views/auth.js`)
| Mục | Cách làm |
|---|---|
| PIN | dòng `admin=` trong `data/pin.txt` (máy chủ tự đọc; đổi ở Cài đặt), nếu không có thì biến `EXTRUXY_ADMIN_PIN`. Đăng nhập sai 5 lần khóa 60 giây, đổi PIN sai PIN cũ cũng tính vào bộ đếm đó |
| So PIN | `secrets.compare_digest` (chống đoán theo thời gian) |
| Phiên | mã ngẫu nhiên `secrets.token_urlsafe(32)` lưu trong RAM; cookie `HttpOnly`, `SameSite=Strict` (thêm `Secure` khi qua HTTPS); hết hạn 12 giờ |
| Nhập sai | 5 lần liên tiếp → khóa đăng nhập 60 giây (cho mọi nguồn, vì qua tunnel mọi yêu cầu đều từ 127.0.0.1) |
| Chưa đặt PIN | ai vào cũng là quản lý, giao diện hiện nhãn cam "Chưa đặt PIN quản lý". **Bắt buộc đặt** khi cho máy khác vào mạng |
| Đăng xuất | tự khóa chuyển động lại; trang tải lại để mọi khối khởi động đúng vai trò |

Route: `POST /api/auth/login {pin}`, `POST /api/auth/logout`, `GET /api/auth/me` → `{role, pin_set}`.
**Hai lớp khóa chuyển động độc lập**: (1) người gọi phải là quản lý, (2) máy phải đang mở khóa có hẹn giờ (+ PIN mở khóa nếu đặt). Khách biết PIN mở khóa cũng không chạy được máy.

Mở cho khách (`GUEST_ROUTES`): `GET /api/health`, `/api/status`, `/api/connection`, `/api/draw/schema`, `/api/auth/*`, tệp giao diện. Thêm route cho khách = thêm đúng một dòng vào danh sách **và** sửa `tests/test_auth.py` (test quét mọi route, route ngoài danh sách phải trả 401).

## B4. Khách gửi ảnh vào `customer/` ⏳ (kế hoạch)
1. Khách chọn ảnh, cắt, xem trước sáng tối, chọn khổ giấy (đều trong trình duyệt), điền tên / số điện thoại + ghi chú, bấm **"Gửi cho người vận hành"** → `POST /api/customer`.
2. Máy chủ lưu `data/customer/<giờ>_<6 ký tự ngẫu nhiên>/image.png + info.json`; kiểm ảnh thật (Pillow `verify`, trần 10 MB, ~25 triệu điểm), **lưu lại thành tệp mới** (bỏ EXIF, gồm vị trí GPS); tối đa ~200 bài / 1 GB; **tự xóa sau 3 ngày**; tối đa 1 bài mỗi 10 giây.
3. Quản lý mở danh sách "Khách gửi" → bấm một mục → ảnh nạp kèm đúng vùng cắt / sáng tối / khổ giấy → tạo nét → lưu bản thảo → vẽ.

Ước lượng: route + thư mục 1,5 giờ; tab vẽ chế độ khách (vẽ ảnh xem trước lên giấy, ô tên / ghi chú / gửi) 2–3 giờ; danh sách cho quản lý 1,5 giờ.

---

# C. Mạng LAN, phát 4G, demo không Internet

- Launcher đã mở cho mạng (`--host 0.0.0.0`, tự thêm IP vào danh sách Host).
- **Giao diện chạy được khi không có Internet** ✅: không tải gì từ ngoài (không CDN, không font Google).
- Wi-Fi của mạch MKS **không cần** vào mạng (USB là đủ). Vào thì có thêm đường điều khiển qua WebUI FluidNC, **vượt qua mọi khóa của phần mềm**: tắt hoặc đặt mật khẩu mạnh trước demo.
- **Đặt cả PIN quản lý và PIN mở khóa** trước khi cho người khác vào mạng.

| Cách phát Wi-Fi cho demo | Internet | Ghi chú |
|---|---|---|
| **Router du lịch / router mini** (cắm USB 5 V) | không cần | ổn định nhất, nhiều máy vào cùng lúc; giữ chỗ IP → in sẵn **mã QR** địa chỉ |
| Router 4G bỏ túi | có | như trên + dùng được Cloudflare Quick Tunnel |
| Điện thoại phát 4G | có | dễ nhất (buổi thử 03/11); số máy vào giới hạn, IP đổi mỗi lần, có thể tự tắt khi màn hình tắt |
| MiniPC Ubuntu tự phát (`nmcli`, chế độ AP) | không cần | card Wi-Fi phải hỗ trợ AP (`iw list`) |
| Laptop Windows "Mobile hotspot" | ⚠ | Windows thường đòi có kết nối để chia sẻ |

**Phát 4G từ điện thoại:** cho laptop vào mạng phát **trước** rồi mới bấm icon (launcher đọc IP lúc bật). Windows thường xếp mạng phát là **Public** → đổi sang Private hoặc cho phép cả Public ở tường lửa. Android thường `192.168.43.x`, iPhone `172.20.10.x`. Dữ liệu giữa laptop và điện thoại không ra Internet nên gần như không tốn 4G.

**Cho người ở xa xem** (cần 4G): `cloudflared tunnel --url http://localhost:8000` tạo địa chỉ tạm `*.trycloudflare.com`, không cần tài khoản (chỉ để thử, tối đa 200 yêu cầu đồng thời). **Chỉ dùng sau khi đặt PIN quản lý.**

💡 Ý tưởng chưa thử: cổng đón (captive portal) bằng dnsmasq để điện thoại vào Wi-Fi là tự mở giao diện.

---

# D. Chạy tay không dùng launcher, GitHub Codespaces

**Máy chỉ có `Python\`:**
```powershell
cd backend
$env:EXTRUXY_ALLOWED_HOSTS = "localhost,127.0.0.1,192.168.43.10"   # IP thật của laptop (ipconfig); chỉ dùng trên laptop thì bỏ
$env:EXTRUXY_UNLOCK_PIN = "đổi-số-này"
$env:EXTRUXY_ADMIN_PIN = "đổi-số-này"
..\Python\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Cửa sổ phải để mở; lỗi hiện ngay trên đó; tắt bằng Ctrl+C; không tự tắt sau 10 phút. Máy có venv thì thay bằng `.venv\Scripts\python.exe`.

**GitHub Codespaces** 🧪 (thử tab vẽ trên cloud, không dùng được máy thật vì cổng USB ở chỗ bạn):
```bash
cd backend && pip install -r requirements.txt
EXTRUXY_ALLOWED_HOSTS="*" python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Tab Ports → cổng 8000 → để **Private**. ⚠ Cổng chuyển tiếp có thể đổi Host / Origin (báo `bad_origin` thì sửa chỗ kiểm ở `main.py`). Xóa Codespace là mất `data/`.

---

# E. MiniPC Ubuntu ⏳ (kế hoạch, chưa có máy)

MiniPC (i5-3210M, 8 GB) chạy 24/7, cắm USB vào mạch MKS, không màn hình, quản lý qua SSH. **Không dùng `Python/` của Windows.**

| | **Docker (đề xuất)** | venv + systemd (dự phòng) |
|---|---|---|
| Cài | `docker compose up -d` | tạo venv, `pip install`, tệp dịch vụ systemd |
| Cập nhật | `git pull` → `docker compose up -d --build` | `git pull` → `pip install -r` → `systemctl restart` |
| Thư viện hệ thống OpenCV | nằm trong image | cài vào Ubuntu |
| Cổng USB | đưa vào container (`devices:`); cắm lại cáp có thể phải khởi động lại container ⚠ | dùng thẳng |
| Dữ liệu | volume `./data:/data` | `EXTRUXY_DATA_DIR=/var/lib/extruxy` |

`Dockerfile` dự kiến:
```dockerfile
FROM python:3.12-slim
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
`docker-compose.yml` dự kiến:
```yaml
services:
  plotter:
    build: .
    restart: unless-stopped
    ports: ["8000:8000"]
    volumes: ["./data:/data"]
    devices: ["/dev/ttyMKS:/dev/ttyMKS"]
    group_add: ["dialout"]
    environment:
      EXTRUXY_ALLOWED_HOSTS: "localhost,127.0.0.1,192.168.1.50,plotter.local,plotter.tenmien.com"
      EXTRUXY_UNLOCK_PIN: "đổi-số-này"
      EXTRUXY_ADMIN_PIN: "đổi-số-này"
      # KHÔNG đặt EXTRUXY_IDLE_EXIT_MIN: MiniPC phải chạy suốt
    logging: {driver: json-file, options: {max-size: 10m, max-file: "3"}}
```
`.dockerignore`: `.venv`, `Python`, `data`, `export`, `_ban_cu`, `**/__pycache__`, `backend/tests`.

**Tên cổng USB cố định (udev):** mạch MKS dùng chip CH340 (thường `1a86:7523`, ⚠ kiểm bằng `lsusb`). Tạo `/etc/udev/rules.d/99-mks.rules`:
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="ttyMKS", GROUP="dialout", MODE="0660"
```
rồi `sudo udevadm control --reload && sudo udevadm trigger`, chọn cổng `/dev/ttyMKS` trong phần mềm.

**systemd (nếu không dùng Docker):** `/etc/systemd/system/extruxy.service` chạy `/opt/extruxy/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`, `Restart=always`, `Environment=EXTRUXY_DATA_DIR=…`, `EXTRUXY_ALLOWED_HOSTS=…`; `sudo systemctl enable --now extruxy`; nhật ký `journalctl -u extruxy -f`.

**IP cố định:** máy chủ chặn mọi Host không nằm trong `EXTRUXY_ALLOWED_HOSTS` (chống DNS rebinding), nên IP / tên phải cố định.
| Cách | Làm gì |
|---|---|
| **Giữ chỗ DHCP trên router** (đề xuất) | trang router → DHCP / Address Reservation → MAC của MiniPC → `192.168.1.50` |
| IP tĩnh trên Ubuntu | `/etc/netplan/*.yaml`: `dhcp4: no`, `addresses`, `routes`, `nameservers` → `sudo netplan apply` |
| Tên `plotter.local` | `hostnamectl set-hostname plotter` + `apt install avahi-daemon` (Android có thể không nhận `.local`) |

Tường lửa: `sudo ufw allow from 192.168.1.0/24 to any port 8000`.

---

# F. Cloudflare Tunnel ⏳

**Là gì:** `cloudflared` chạy trên MiniPC **tự gọi ra** Cloudflare và giữ một đường hầm. Người ngoài vào `https://plotter.tenmien.com`, Cloudflare chuyển tới `http://localhost:8000`. Không mở cổng router, không cần IP công cộng, có sẵn HTTPS.

**Điều kiện trước:** đã đặt PIN quản lý và thử phân quyền. Cần một tên miền đã chuyển DNS về Cloudflare (tài khoản miễn phí đủ).

Các bước: `cloudflared tunnel login` → `cloudflared tunnel create plotter` → `cloudflared tunnel route dns plotter plotter.tenmien.com` → `~/.cloudflared/config.yml`:
```yaml
tunnel: <mã>
credentials-file: /home/<user>/.cloudflared/<mã>.json
ingress:
  - hostname: plotter.tenmien.com
    service: http://localhost:8000
  - service: http_status:404
```
→ `sudo cloudflared service install` (hoặc thêm service `cloudflared` vào `docker-compose.yml`) → thêm `plotter.tenmien.com` vào `EXTRUXY_ALLOWED_HOSTS`.

Khớp với máy chủ:
- IP nguồn luôn là 127.0.0.1 → phân biệt người bằng cookie phiên, không bằng IP.
- Trình duyệt gửi `Origin: https://plotter.tenmien.com` → dự kiến khớp Host nên lớp chặn "Origin lạ" vẫn cho qua ⚠ thử thật.
- Mỗi trang hỏi `/api/status` 10 lần/giây: nhiều khách cùng lúc thì nên giãn nhịp cho khách.
- Gói miễn phí giới hạn 100 MB / yêu cầu; phần mềm giới hạn 64 MB nên không vướng.

---

# G. Còn phải thử

| Việc | Cách |
|---|---|
| Máy sạch không cài gì (Visual C++ của OpenCV); nhánh `pip install` của `Cap nhat.bat` | thử trên máy bạn bè |
| Điện thoại thật vào giao diện khách | đặt PIN, vào bằng điện thoại |
| Thời gian xử lý ảnh, RAM, máy có giật trên MiniPC | `info.timings` (rê chuột dòng trạng thái tab vẽ), `htop` |
| Giới hạn RAM của tiến trình xử lý ảnh, cài OpenCV / scikit-image trên Ubuntu | trên MiniPC |
| Origin / Host / cookie qua Cloudflare, Codespaces | cấu hình thật |
| Chưa đặt PIN thì cho mọi người làm quản lý (như hiện tại) hay chặn hẳn khi mở ra ngoài | chủ dự án quyết |
