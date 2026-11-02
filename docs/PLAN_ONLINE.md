# PLAN_ONLINE — phân quyền, MiniPC và Cloudflare Tunnel

Cập nhật 02/11/2026 (đã gộp `PLAN_ACCESS.md` vào mục 2). Một chỗ cho mọi việc "cho người khác vào giao diện": phân quyền (mục 2, **code được ngay trên laptop**), mạng LAN / phát 4G (mục 3), MiniPC Ubuntu (mục 4–5), Cloudflare Tunnel (mục 6). Bản Windows mang đi: `DONG_GOI.md`. Ý tưởng nâng cao (tài khoản người dùng, hàng chờ nhiều người, nét gốc…): [FUTURE_UPGRADE_BETA.md](FUTURE_UPGRADE_BETA.md) phần B.

**Ký hiệu**: ✅ CHỐT / đã làm và test · 💡 ĐỀ XUẤT (chưa chốt) · ⚠ CHƯA KIỂM CHỨNG · ⏳ CHƯA LÀM.

## 1. Giai đoạn

| # | Việc | Tình trạng |
|---|---|---|
| 1 | Đo trên MiniPC thật: thời gian từng bước (`info.timings`, rê chuột vào dòng trạng thái tab vẽ), RAM, máy vẽ có giật khi đang xử lý ảnh không | ⏳ chờ máy về |
| 2 | Xử lý ảnh ở **tiến trình riêng, ưu tiên thấp** (`services/drawing/isolated.py`): hủy = kết thúc tiến trình, quá giờ 600 s, RAM 4 GB (chỉ Linux) | ✅ (⚠ giới hạn RAM chưa thử Ubuntu) |
| 3 | Trình duyệt **thu nhỏ ảnh trước khi gửi** (`lib/imageprep.js`) và **xem trước độ sáng** (`views/drawing/tonepreview.js`). Backend vẫn tự làm được và luôn kiểm lại | ✅ |
| 4 | **Phân quyền khách / quản lý** + khách gửi ảnh vào `customer/` (mục 2) | ⏳ thiết kế xong |
| 5 | **Triển khai Ubuntu**: Docker (đề xuất) hoặc venv + systemd, quyền cổng USB, tên cổng cố định (udev), IP cố định (mục 4–5) | ⏳ |
| 6 | **Cloudflare Tunnel** (mục 6). **Chỉ nối sau khi xong #4 và test** | ⏳ |

Quy tắc chung: mọi bước JS đều là đường nhanh tùy chọn; **backend luôn tự làm được và luôn kiểm tra lại**, không tin dữ liệu từ trình duyệt. Không dùng host chia sẻ (DECISIONS O1).

---

## 2. Phân quyền: khách và quản lý

### 2.1 Nguyên tắc
- Máy vẽ chỉ có **một**. Người cần vẽ liên hệ trực tiếp chủ máy; chủ máy tự đặt giấy, bút, tự tạo nét, tự bấm chạy. ✅
- Nguyên tắc an toàn cũ **không nới** (`AI_START.md` mục 4).
- **Backend chặn thật**, frontend chỉ ẩn nút cho gọn.
- **Chặn mặc định**: route nào không nằm trong danh sách mở cho khách thì cần quản lý. Route mới thêm sau này tự bị chặn.

### 2.2 Hai vai trò ✅

| | **Khách** (không đăng nhập) | **Quản lý** (1 tài khoản) |
|---|---|---|
| Xem trạng thái máy (vị trí, trạng thái, đèn công tắc, tiến độ) | ✔ chỉ đọc | ✔ |
| Tab Điều khiển: nạp tệp G-code, xem trước khung | ✔ (chạy trong trình duyệt) | ✔ |
| Tab vẽ: tải ảnh, cắt vùng, xám/trắng, sáng tối, chọn khổ giấy | ✔ (chạy trong trình duyệt) | ✔ |
| Nút **"Gửi cho người vận hành"** → thư mục `customer/` | ✔ | – |
| Tạo nét (vector), G-code, lưu bản thảo, xem bản thảo | ✘ | ✔ |
| Xem / mở / xóa ảnh khách gửi | ✘ | ✔ |
| Điều khiển máy, chạy tệp, terminal, macro, cấu hình máy, hồ sơ, lưu trữ, cài đặt | ✘ | ✔ |

- Không có đăng ký, không có tài khoản "người dùng" (để FUTURE_UPGRADE_BETA mục 7). ✅
- Quản lý dùng tab vẽ **y như hiện tại**: nạp ảnh / đổi preset / cắt vùng thì tự tạo nét, không thêm hàng chờ. Chỉ một người tạo nét nên không ai hủy việc của ai. ✅
- Trạng thái máy dùng chung, backend hỏi máy **một** lần rồi trả cho mọi trình duyệt (đã như vậy).

### 2.3 Đăng nhập quản lý 💡

| Mục | Đề xuất |
|---|---|
| Mật khẩu | Biến môi trường `EXTRUXY_ADMIN_PASSWORD` (launcher đặt giống dòng PIN trong `start.ps1`). Không có form tạo tài khoản. |
| So mật khẩu | `secrets.compare_digest` (như PIN mở khóa, `services/machine.py:219`). Mật khẩu chỉ nằm trong biến môi trường nên chưa cần băm. |
| Phiên | Mã `secrets.token_urlsafe(32)` lưu trong RAM (khởi động lại thì đăng nhập lại). Cookie `HttpOnly`, `SameSite=Strict`, thêm `Secure` khi chạy qua HTTPS. Hết hạn ~12 giờ. |
| Nhập sai | Sai 5 lần liên tiếp → khóa đăng nhập 60 giây cho **mọi nguồn** (qua tunnel mọi yêu cầu đều từ 127.0.0.1). |
| Chưa đặt mật khẩu | 💡 Giữ đúng như hôm nay (ai vào cũng là quản lý) để chạy tay khi code không phiền; giao diện hiện **dải cảnh báo đỏ** "chưa đặt mật khẩu quản lý". **Bắt buộc đặt** khi cho máy khác vào và khi lên Cloudflare. Cần chủ dự án chốt. |
| Đăng xuất / hết phiên | 💡 Tự khóa chuyển động lại. |

Endpoint mới: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` → `{role: "admin"|"guest", password_set}`.

**Hai lớp khóa chuyển động** (đã kiểm mã: mở khóa là **chung cả máy**, `allow_motion` trong `services/machine.py`):
1. Người gọi phải là quản lý (lớp mới).
2. Máy phải đang mở khóa có hẹn giờ (+ PIN nếu đặt), như hiện tại.
Hai kiểm tra độc lập; có lớp 1 thì khách không mở khóa được dù biết PIN.

### 2.4 Bảng route (đã đối chiếu `backend/app/api/*.py`)

**Mở cho khách** (danh sách trắng, chỉ những route này):

| Route | Vì sao |
|---|---|
| `GET /api/health` | trang ẩn báo "còn mở" (`state.js`) |
| `GET /api/status`, `GET /api/connection` | xem trạng thái chung, chỉ đọc. ⚠ Kiểm `status` có trả tên tệp / thông báo lỗi nào không nên lộ không |
| `GET /api/draw/schema` | khai báo tham số để vẽ ô nhập tab vẽ |
| `POST /api/customer` (mới) | khách gửi ảnh, **chỉ ghi, không đọc lại được** |
| `/api/auth/*` (mới) | đăng nhập |
| Tệp tĩnh frontend | giao diện |

**Còn lại đều cần quản lý**:
- `api/machine.py`: `/motion`, `/ports`, `/connect`, `/disconnect`, `/command`, `/realtime`, `/log` (terminal), `/jobs`, `/jobs/resume` (GET/POST/DELETE), `/jobs/cancel`.
- `api/config.py`: `/machine/config*`, `/profile`.
- `api/storage.py`: `/macros*`, `/storage`, `/storage/file` (trang này cho tải **mọi** tệp).
- `api/draw.py`: mọi route trừ `/schema`, gồm `/import`, `/svg`, `/tasks/*`, `/gcode`, `/drafts*`, `/drafts/import-gcode`, `/calibration`, `/settings`.
- `GET/DELETE /api/customer*` (mới, phía quản lý).

⚠ Kiểm: lúc mở trang, frontend có gọi `/api/profile`, `/api/draw/settings`, `/api/macros`, `/api/ports` không. Nếu có thì ở chế độ khách phải bỏ qua lỗi 401 hoặc không gọi.

### 2.5 Khách gửi ảnh: thư mục `customer/` ✅ (ý chủ dự án) + 💡 (cách làm)

**Luồng**
1. Khách chọn ảnh → trình duyệt hiện ảnh gốc, cắt vùng (`views/drawing/crop.js`), xem trước xám/trắng + sáng tối (`views/drawing/tonepreview.js`, `lib/imageprep.js`), chọn khổ giấy / xoay / lề (`lib/paper.js`). **Không gọi** `/api/draw/import`.
2. Khách điền tên hoặc số điện thoại (bắt buộc) + ghi chú (ví dụ "muốn vẽ màu", "cỡ A5").
3. Bấm **"Gửi cho người vận hành"** → `POST /api/customer` (multipart: ảnh + `info` JSON).
4. Quản lý mở danh sách **"Khách gửi"** trong tab vẽ → bấm một mục → ảnh được nạp kèm đúng vùng cắt / sáng tối / khổ giấy khách đã chọn → tự tạo nét như bình thường → lưu bản thảo → vẽ.

**Backend**
- Thư mục: `data/customer/<YYYYMMDD-HHMMSS>_<6 ký tự ngẫu nhiên>/` gồm `image.png` (hoặc `.jpg`) + `info.json`. Thêm `"customer": "customer"` vào `paths.AREAS` để trang Lưu trữ thấy luôn.
- `info.json`: `name` (≤ 60 ký tự), `note` (≤ 500), `crop`, các ô sáng tối (`image-*`), khổ giấy / xoay / lề, `preset`, giờ gửi. Kiểm bằng pydantic; ô sai thì bỏ ô đó, không từ chối cả ảnh.
- **Kiểm ảnh thật**: trần 10 MB; mở bằng Pillow, `verify()`, trần ~25 triệu điểm ảnh; **lưu lại thành tệp mới** (bỏ EXIF, gồm vị trí GPS trong ảnh điện thoại). Tệp đổi đuôi / tệp lạ bị từ chối.
- **Trần thư mục**: ~200 bài hoặc ~1 GB; đầy thì trả `customer_full`.
- **Tự xóa sau 3 ngày**, dọn mỗi lần có bài mới và lúc khởi động (không cần luồng nền). Muốn giữ thì quản lý lưu thành bản thảo.
- Chống gửi dồn: tối đa 1 bài mỗi 10 giây cho toàn máy.
- Route quản lý: `GET /api/customer`, `GET /api/customer/{id}/image`, `DELETE /api/customer/{id}`. `id` kiểm regex như S3 (chống vượt đường dẫn).
- Trên trang gửi ghi: "Ảnh được lưu tối đa 3 ngày, chỉ người vận hành xem được."

**Khách gửi ảnh gì** 💡: ảnh gốc đã thu nhỏ ở trình duyệt (cạnh dài ≤ 4000 px), **chưa cắt**, kèm vùng cắt dạng số. Quản lý cắt lại hoặc đổi bút được mà không phải xin lại ảnh (thứ tự xử lý P4: cắt/thu nhỏ trước, lọc sau).

**Frontend** (`views/drawing.js`, đã đọc mã)
- Nạp ảnh hiện tự gọi vector hóa ở **4 chỗ**: chọn tệp (`drawing.js:129`), áp vùng cắt (`:58`), đổi preset (`:294`), kéo khung lệch >12% (`:282`), cộng nút "Tạo nét" (`:429`). Chế độ khách: tắt cả 5.
- ⚠ Khung giấy hiện chỉ vẽ **nét** từ backend (`S.src`, `S.layers`); khách không có nét nên cần vẽ **ảnh xem trước** vào đúng ô trên giấy. Phần thêm lớn nhất ở frontend.
- Ẩn: nút G-code, lưu bản thảo, danh sách bản thảo, chia màu. Hiện: ô tên, ô ghi chú, nút gửi.
- Tab Điều khiển chế độ khách: giữ trạng thái + nạp/xem trước G-code (`lib/gcode.js`); ẩn jog, Home, bút, chạy, terminal, macro, mở khóa. Tab Cài đặt: ẩn hết trừ ngôn ngữ / giao diện.
- Cách ẩn: `body.role-guest` + CSS ẩn phần có `data-admin`, cộng kiểm ở từng view chỗ có logic tự chạy.

### 2.6 Thứ tự làm và ước lượng 💡

| # | Việc | Tệp chính | Ước lượng |
|---|---|---|---|
| 1 | Đăng nhập quản lý + chặn mặc định ở backend | `app/auth.py` (mới), `api/__init__.py` (gắn `Depends(require_admin)` cho mọi router, một router riêng cho danh sách trắng), `main.py` | 2–3 giờ |
| 2 | Test phân quyền tự động (2.7) | `tests/test_auth.py` (mới) | 1 giờ |
| 3 | Frontend: đăng nhập / đăng xuất, `role-guest`, ẩn phần quản lý, dải cảnh báo | `core/api.js`, `index.html`, `css/polish.css`, các view, `locales/*.json` | 2 giờ |
| 4 | Thư mục `customer/` + route gửi / xem / xóa | `api/customer.py`, `services/customer.py` (mới), `paths.py` | 1,5 giờ |
| 5 | Tab vẽ chế độ khách: tắt tự tạo nét, vẽ ảnh xem trước lên giấy, ô tên / ghi chú / gửi | `views/drawing.js`, `views/drawing/canvas.js` | 2–3 giờ |
| 6 | Danh sách "Khách gửi" cho quản lý, bấm là nạp kèm thông số | `views/drawing.js`, `stores/` | 1,5 giờ |
| 7 | Launcher: dòng mật khẩu quản lý cạnh dòng PIN | `launcher/start.ps1`, `DONG_GOI.md` | 15 phút |
| 8 | Cập nhật `DECISIONS.md` (O2), `STATUS.md`, `ARCHITECTURE.md`, sinh lại `CODEMAP.md` | | 30 phút |

Mục 1–3 + 7 đủ để thử "khách xem / quản lý điều khiển". Mục 4–6 là phần khách gửi ảnh.

### 2.7 Kiểm thử
Backend: `cd backend && python -m pytest`, dữ liệu trong thư mục tạm (`conftest.py`).
- **Test quét toàn bộ route**: lặp qua `app.openapi()["paths"]` (không dùng `app.routes`, xem AI_START bẫy), gọi mỗi route khi chưa đăng nhập; route ngoài danh sách trắng phải trả 401.
- Đăng nhập đúng / sai / khóa 60 giây sau 5 lần sai; cookie sai, hết hạn, đã đăng xuất.
- Khách không mở khóa được chuyển động, không gửi được `$J`, `/command`, `/jobs`.
- Chưa đặt mật khẩu: hành vi đúng như hôm nay (test cũ vẫn xanh).
- `POST /api/customer`: ảnh thật lưu được và mất EXIF; tệp giả ảnh bị từ chối; quá 10 MB bị từ chối; đầy thư mục trả `customer_full`; bài > 3 ngày bị dọn; `id` lạ (`../`) bị từ chối; khách không đọc lại được.

---

## 3. Mạng LAN / phát 4G từ điện thoại (thử được ngay)
- Launcher đã mở cho mạng (`--host 0.0.0.0`, thêm IP laptop vào `EXTRUXY_ALLOWED_HOSTS`, `start.ps1:36-44`). Các bước cụ thể (tường lửa, IP, chạy tay không launcher): `DONG_GOI.md` mục 8.
- Chưa có mục 2 thì **đặt PIN mở khóa**: mở khóa là chung cả máy, laptop mở thì điện thoại cũng chạy được máy.
- Wi-Fi của MKS **không** cần vào mạng (USB là đủ); vào thì có thêm đường điều khiển qua WebUI FluidNC, vượt qua mọi khóa của phần mềm.
- `idle.py` chỉ tự tắt server khi đặt `EXTRUXY_IDLE_EXIT_MIN` (launcher đặt 10); trang của khách cũng tính là "còn mở"; đang chạy G-code thì không tắt. MiniPC không đặt biến này.

---

## 4. Ubuntu không màn hình (dự kiến, ⏳ chưa thử)
MiniPC chạy **24/7**, cắm USB vào mạch MKS, không màn hình; quản lý qua SSH từ laptop. **Không dùng thư mục `Python/` của bản Windows**; trên Linux cài thư viện bằng pip từ `requirements.txt` trong Docker hoặc venv.

### Hai cách chạy
| | **Docker (đề xuất)** | venv + systemd |
|---|---|---|
| Cài | `docker compose up -d` | tạo venv, `pip install`, viết tệp dịch vụ systemd |
| Cập nhật | `git pull` → `docker compose up -d --build` | `git pull` → `pip install -r` → `systemctl restart` |
| Thư viện hệ thống (OpenCV) | nằm trong image | cài thẳng vào Ubuntu |
| Cổng USB | phải đưa vào container (`devices:`), cắm lại cáp có thể phải khởi động lại container ⚠ | dùng thẳng |
| Dữ liệu | volume `./data:/data` | `EXTRUXY_DATA_DIR=/var/lib/extruxy` |

### Docker: tệp dự kiến (chưa có trong kho, viết khi MiniPC về)
`Dockerfile` (thư mục gốc):
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
      EXTRUXY_ADMIN_PASSWORD: "doi-mat-khau-nay"   # sau khi làm mục 2
      # KHÔNG đặt EXTRUXY_IDLE_EXIT_MIN: MiniPC phải chạy suốt
```
- `.dockerignore`: `.venv`, `Python`, `data`, `export`, `_ban_cu`, `**/__pycache__`, `backend/tests`.
- `launcher/`, `Cap nhat.bat` chỉ dành cho Windows.
- Nhật ký: `docker compose logs -f` (giữ 3 ngày: `logging: {driver: json-file, options: {max-size: 10m, max-file: "3"}}`).
- Giới hạn RAM: ngoài `RLIMIT_AS` của tiến trình xử lý ảnh có thể đặt `mem_limit` cho cả container.

### Cổng USB cố định (udev)
Mạch MKS dùng chip CH340 (thường `1a86:7523`; ⚠ kiểm bằng `lsusb`). Tạo `/etc/udev/rules.d/99-mks.rules`:
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

### Còn phải thử trên Ubuntu ⚠
Giới hạn RAM `RLIMIT_AS`, cài `opencv-python-headless`/`scikit-image`, quyền ghi `data/`, SimLink + serial thật, thời gian xử lý ảnh trên i5-3210M (giai đoạn 1). Nếu đóng gói thành exe: `isolated.py` khởi động tiến trình con bằng `python -m ...` nên phải đổi cách khởi động (hoặc `EXTRUXY_DRAW_INPROC=1`).

## 5. IP cố định trong mạng nhà (dự kiến)
Backend chặn mọi địa chỉ không có trong `EXTRUXY_ALLOWED_HOSTS` (chống DNS rebinding, `main.py`), nên **IP/tên MiniPC phải cố định** và ghi vào biến đó.

| Cách | Làm gì | Ghi chú |
|---|---|---|
| **Giữ chỗ DHCP trên router (đề xuất)** | Trang quản trị router (thường `192.168.1.1`) → DHCP / *Address Reservation* → chọn MAC của MiniPC → gán `192.168.1.50` | không sửa gì trên Ubuntu; đổi router thì làm lại |
| IP tĩnh trên Ubuntu | `/etc/netplan/*.yaml`: `dhcp4: no`, `addresses: [192.168.1.50/24]`, `routes: [{to: default, via: 192.168.1.1}]`, `nameservers: {addresses: [1.1.1.1]}` → `sudo netplan apply` | chọn IP ngoài dải DHCP |
| Tên `plotter.local` | `sudo hostnamectl set-hostname plotter` + `sudo apt install avahi-daemon` | vẫn nên giữ IP cố định làm dự phòng |

Sau đó thêm IP và tên vào `EXTRUXY_ALLOWED_HOSTS` (tạm `"*"` khi thử, **không dùng `*` khi mở ra internet**). Tường lửa `ufw`: `sudo ufw allow from 192.168.1.0/24 to any port 8000`; dùng Cloudflare Tunnel thì không mở cổng nào ra ngoài.

## 6. Cloudflare Tunnel (dự kiến, ⏳ chưa thử)
**Là gì:** `cloudflared` chạy trên MiniPC **tự gọi ra** Cloudflare và giữ một đường hầm; người ngoài vào `https://plotter.tenmien.com` thì Cloudflare chuyển tới `http://localhost:8000`. **Không mở cổng router, không cần IP tĩnh công cộng**, có sẵn HTTPS.

**Điều kiện trước:** xong mục 2 (đăng nhập quản lý, chặn mặc định, test). Cần một tên miền đã chuyển DNS về Cloudflare (tài khoản miễn phí đủ dùng).

**Các bước (trên MiniPC):**
1. Cài: `sudo apt install cloudflared` (theo kho gói của Cloudflare) hoặc Docker image `cloudflare/cloudflared`.
2. `cloudflared tunnel login` (mở link trên laptop, chọn tên miền).
3. `cloudflared tunnel create plotter` → ghi lại mã đường hầm, tệp khóa ở `~/.cloudflared/<mã>.json`.
4. `cloudflared tunnel route dns plotter plotter.tenmien.com`.
5. `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <mã>
   credentials-file: /home/<user>/.cloudflared/<mã>.json
   ingress:
     - hostname: plotter.tenmien.com
       service: http://localhost:8000
     - service: http_status:404
   ```
6. Chạy như dịch vụ: `sudo cloudflared service install` (hoặc thêm service `cloudflared` vào `docker-compose.yml`, `command: tunnel run`, mạng chung với `plotter` → `service: http://plotter:8000`).
7. Thêm `plotter.tenmien.com` vào `EXTRUXY_ALLOWED_HOSTS`, khởi động lại server.

**Khớp với backend:**
- **IP nguồn luôn là 127.0.0.1** → không dùng IP để tin cậy hay phân biệt người; dùng cookie phiên (mục 2.3).
- `cloudflared` giữ nguyên Host → phải có trong `EXTRUXY_ALLOWED_HOSTS`, nếu không trang báo `bad_host` (`main.py:52`).
- Trình duyệt gửi `Origin: https://plotter.tenmien.com` → dự kiến khớp Host nên lớp chặn "Origin lạ" (`main.py:56`) vẫn cho qua. ⚠ Thử trên cấu hình thật.
- Cookie phiên phải có `Secure` khi chạy qua HTTPS.
- Mỗi trang mở hỏi `/api/status` 10 lần/giây: nhiều khách cùng lúc thì nên giãn nhịp cho khách.
- Gói Cloudflare miễn phí giới hạn **100 MB/yêu cầu**; trần của phần mềm 64 MB (`MAX_BODY_BYTES`), ảnh khách gửi 10 MB nên không vướng.
- Lớp ngoài cổng (không viết mã): Cloudflare Zero Trust → Access (xem FUTURE_UPGRADE_BETA mục 11).

## 7. Chưa kiểm chứng / chưa quyết

| Việc | Cách |
|---|---|
| Chưa đặt mật khẩu quản lý thì cho mọi người làm quản lý (như hôm nay) hay chặn | Chủ dự án chốt (mục 2.3) |
| Origin/Host qua Cloudflare Tunnel, cookie `Secure` | Thử cấu hình thật trên MiniPC |
| Origin/Host qua cổng chuyển tiếp của GitHub Codespaces | Thử (`DONG_GOI.md` mục 8.3) |
| `GET /api/status` có lộ gì không nên cho khách thấy | Đọc `services/machine.py` phần tạo trạng thái |
| Frontend lúc mở trang gọi những route nào | Đọc `app.js` / các view |
| Canvas tab vẽ vẽ ảnh xem trước được không | Đọc `views/drawing/canvas.js` |
| Giao diện trên điện thoại dùng được không | Thử bằng điện thoại thật |
| Có cần giới hạn khung giờ cho khách không | Chủ dự án quyết sau khi chạy thử |
