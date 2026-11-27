# 07 — Mạng, kết nối và triển khai

> Viết cho người không học mạng. Gộp từ tài liệu "Triển khai" và "Mạng và tên miền" cũ (27/11/2026). Đọc phần mình cần.
> Ký hiệu: ✅ đã làm và thử · 🧪 làm rồi, chưa thử môi trường thật · ⏳ chưa làm (kế hoạch) · ⏸ tạm bỏ.
> Trạng thái 27/11/2026: giao diện mở được từ điện thoại qua 4G bằng tên miền riêng (đường ống Cloudflare chạy bằng launcher); bạn cùng dự án tải `data` + `cloudflared.exe` về máy mình cũng chạy được. Chưa đặt PIN, chưa bật Cloudflare Access. Nối mạch qua Wi-Fi bằng phần mềm: mã xong, **chưa thử trên mạch thật**. ESP32-S3 làm cầu nối: **kế hoạch**, chưa mua.

**Mục lục**
1. Bức tranh chung và sơ đồ truyền dữ liệu
2. Các phương án kết nối
3. Quy chuẩn và đường truyền
4. Số đo thời gian đi về (27/11/2026)
5. Bản mang đi Windows ✅
6. Phân quyền khách / quản lý ✅
7. Mạng LAN, phát 4G, demo không Internet
8. Chạy tay không dùng launcher, GitHub Codespaces
9. Tên miền và Cloudflare Tunnel (mở giao diện cho máy khác) ✅
10. Mang theo bằng SSD, máy chạy cố định
11. Wi-Fi (telnet) tới mạch MKS 🧪
12. WebUI của FluidNC và việc đổi giao diện
13. ESP32-S3 làm cầu nối và nút dừng cứng ⏳
14. MiniPC và máy nhỏ (Pi): tạm bỏ ⏸
15. Còn phải thử

---

# 1. Bức tranh chung và sơ đồ truyền dữ liệu

Ví dụ đời thường: **phần mềm trên máy chủ là người điều phối**, **mạch MKS là người thợ**. Có nhiều đường để điều phối nói chuyện với thợ, và một đường để người ngoài **bấm thẳng vào thợ** mà không qua điều phối (WebUI, đường số 4: nguy hiểm nhất vì vượt PIN và khóa).

```
 Điện thoại / máy khác ── trình duyệt: HTTP + SSE (cổng 8000) ── ở xa thì qua tên miền + Cloudflare
                                   │
                                   ▼
 ┌───────────── Máy chủ: laptop (sau này PC nhà hoặc server cloud) ─────────────┐
 │ phần mềm ExtruXY: PIN, khóa chuyển động, gửi từng dòng G-code, dừng an toàn   │
 └───────┬────────────────────────┬─────────────────────────┬──────────────────┘
         │ (1) USB serial          │ (2) Wi-Fi telnet         │ (3) ESP32-S3 (kế hoạch)
         │ 115200 baud, CH340      │ TCP cổng 23              │ ESP32 tự gọi ra qua Cloudflare,
         │                         │                          │ rồi nối dây UART vào mạch
         ▼                         ▼                          ▼
 ┌─────────────── MKS DLC32 (ESP32 + FluidNC 4.1.1, không sửa firmware) ───────────────┐
 │ cổng USB · telnet 23 · WebUI (HTTP 80 + WebSocket) · UART phụ (khai trong config.yaml) │
 │ nút cứng (dừng / tạm dừng) nối thẳng vào chân của mạch, không qua mạng                │
 └─────────────────────────────────────────────────────────────────────────────────────┘
         ▲ (4) WebUI: điện thoại vào thẳng mạch (fluidnc.local hoặc địa chỉ điểm phát),
               KHÔNG qua phần mềm → vượt mọi khóa phần mềm
```

Ba điều cần nhớ:
- **Đường (1), (2), (3) đều đi qua phần mềm**, nên chịu PIN và khóa chuyển động (`REAL_MODES = ("serial", "wifi")` trong `services/machine.py`; kiểu (3) sẽ thêm vào đó).
- **Đường (4) không có khóa nào ngoài mật khẩu Wi-Fi** của mạch (mục 11).
- **Mạch nhận lệnh từ mọi cổng cùng lúc.** Đang vẽ qua phần mềm mà ai bấm jog hay Home trên WebUI thì mạch vẫn làm, phần mềm không chặn được. Đang vẽ thì không bấm gì trên WebUI.

# 2. Các phương án kết nối

| Phương án | Trạng thái | Qua phần mềm (PIN, khóa)? | Tốc độ | Cần gì | Rủi ro chính |
|---|---|---|---|---|---|
| **USB** | ✅ dùng hằng ngày | Có | ~125 dòng/giây (đo 13/11/2026, [02](02_PHAN_CUNG_MAY.md) F13) | Cáp USB, máy chủ cạnh máy vẽ | Rút cáp giữa bản vẽ: máy chạy nốt bộ đệm rồi dừng |
| **Wi-Fi telnet** | 🧪 mã xong 26/11 (`telnet_link.py`, 10 bài test với mạch giả) | Có | chưa đo | Mạch và máy chủ cùng mạng | Telnet **không mật khẩu**; mất sóng thì bút có thể đang hạ |
| **WebUI của FluidNC** | ✅ chủ dự án đã vào `fluidnc.local` và địa chỉ điểm phát, điều khiển được | **Không** | thủ công | Điện thoại cùng mạng với mạch | Vượt mọi khóa; mật khẩu Wi-Fi là khóa duy nhất |
| **ESP32-S3 cầu nối** | ⏳ kế hoạch 27/11, chưa mua | Có (kiểu kết nối mới) | dự kiến gần USB nhờ kho lệnh trên ESP (mục 4, 13) | ESP32-S3 N16R8, 3 dây UART, nút cứng | Viết mã mới ở hai phía; mất Internet giữa bản vẽ |
| **MiniPC / máy nhỏ cạnh máy vẽ** | ⏸ tạm bỏ | Có | như USB | Mua máy | Chưa thử Linux (mục 14) |

Điểm phát dự phòng của mạch (`FluidNC`, `192.168.0.1`) luôn giữ làm đường cuối cùng, bất kể chọn phương án nào.

# 3. Quy chuẩn và đường truyền

| Đường | Quy chuẩn | Nguồn |
|---|---|---|
| USB ↔ mạch | Serial 115200 baud, chip CH340. Gửi **một dòng, chờ `ok`**, rồi dòng tiếp. Hàng đợi chuyển động của mạch 15 khối | [02](02_PHAN_CUNG_MAY.md) F13, `links/serial_link.py` |
| Wi-Fi ↔ mạch | TCP thô, cổng 23 (`$Telnet/Port`), mỗi lệnh một dòng kết thúc xuống dòng; ký tự tức thời (`?` `!` `~`, Ctrl-X) là một byte. Không mật khẩu. Mở kết nối chờ tối đa 5 s; **3 s không nhận byte nào thì coi là mất sóng** (`LINK_SILENT_S`) | `links/telnet_link.py`; mã FluidNC `TelnetClient.cpp` |
| Tên mạch | `$Hostname` = `fluidnc` → `fluidnc.local` (mDNS). Điểm phát dự phòng: tên mạng `FluidNC`, IP `192.168.0.1`; **mật khẩu mặc định của firmware công khai trong mã nguồn nên phải đổi** (`$AP/Password`) | `WifiConfig.cpp`, `NetSettings.cpp` |
| Giao diện ↔ phần mềm | HTTP và SSE (`/api/events`); trang hỏi `/api/status` 10 lần/giây; cổng 8000; chỉ nhận Host nằm trong danh sách cho phép | `main.py`, [03](03_CAU_TRUC_PHAN_MEM.md) |
| WebUI ↔ mạch | HTTP `/command?plain=<lệnh>` và WebSocket. Mã ở ổ D đặt WebSocket tại `/` cổng 80 (bản ESP3D cũ dùng cổng 81): **chưa kiểm trên mạch thật** | `WebUIServer.cpp` |
| UART tới ESP32-S3 | 3,3 V, nối chéo TX–RX, chung GND. FluidNC nhận cổng UART phụ qua `uart` + `uart_channel` trong `config.yaml`, không phải sửa firmware. Tốc độ baud chưa chốt | `MachineConfig.cpp` dòng 60–61 |
| Ra Internet | HTTPS qua Cloudflare; gói Free giới hạn 100 MB mỗi yêu cầu (phần mềm giới hạn 64 MB nên không vướng). WebSocket lâu dài từ thiết bị nhỏ: chưa thử với đường ống này | mục 9 |

Telnet và WebSocket đều chạy trên TCP nên **độ ổn định như nhau**. Chọn telnet vì đơn giản: không cần thư viện, không đóng gói khung.

# 4. Số đo thời gian đi về (27/11/2026)

**Cách đo:** laptop gọi `https://<tên miền>/api/health` 25 lần qua một kết nối giữ nguyên, so với gọi `http://localhost:8000/api/health` 25 lần. Lệnh đi ra Cloudflare rồi quay về chính laptop; chặng ESP32 → Cloudflare → máy chủ cũng qua Cloudflare như vậy. Chỉ đọc, không đụng máy vẽ. Đây là **một lần đo ở một thời điểm**, chưa đo lúc khác trong ngày hay qua 4G.

| | Qua tên miền (Cloudflare) | Cục bộ |
|---|---|---|
| Lần đầu (mở kết nối mới) | 1,75 s | không đo riêng |
| Thấp nhất | 0,114 s | 0,0007 s |
| Phổ biến (trung vị) | ~0,13 s | ~0,001 s |
| Cao nhất | **1,16 s** (1 lần); một lần khác 0,22 s | 0,0012 s |

**Hệ quả (tính từ số đo, chưa thử trên máy thật):**

| Cách gửi G-code | Tốc độ | Nhận xét |
|---|---|---|
| Như hiện nay: một dòng, chờ `ok` | 1 ÷ 0,13 ≈ **8 dòng/giây** (USB: 125) | Chậm khoảng 16 lần; không dùng được qua Internet |
| Backend đếm ký tự, gửi dồn vài dòng | ≈ 90 dòng/giây (ước) | Lúc mạng vọt 1,16 s, hàng đợi trong mạch (15 khối, bộ đệm kênh mặc định 256 byte) chạy hết trước: máy khựng, **bút đang hạ thì có chấm mực** |
| **ESP32-S3 giữ sẵn nhiều dòng, tự gửi từng dòng xuống mạch tại chỗ** | gần USB | Mạng khựng cả giây vẫn không sao. Đây là cách được chọn (mục 13) |

Lần đầu mở kết nối mất 1,75 s: thiết bị nhỏ phải **giữ kết nối liên tục**, không mở lại mỗi lệnh. Thời gian chờ mất sóng 3 s của telnet cục bộ qua Internet phải đặt riêng.

---

# 5. Bản mang đi Windows ✅

## 5.1 Gồm gì
```
ExtruXY/
├─ Python/          Python 3.12 embeddable 64-bit + pip + thư viện (không lên Git, vài trăm MB)
├─ backend/ frontend/
├─ launcher/        start.vbs · start.ps1 · stop.vbs · stop.ps1 · tao_bieu_tuong.vbs · cap_nhat.ps1 · icon.ico
├─ data/            dữ liệu của bạn (tự tạo, không lên Git)
├─ Cap nhat.bat     cập nhật mã, giữ nguyên Python/ và data/
└─ tools/dong_goi.ps1   (máy phát triển) tạo zip bản cập nhật / bản đầy đủ vào export/
```
Máy dùng **không cần cài Python, venv hay Git**. Chỉ chạy trên Windows 64-bit. Launcher tìm Python theo thứ tự `backend\.venv\Scripts\python.exe` → `Python\python.exe` (máy mượn: mục 10).

## 5.2 Chuẩn bị `Python/` (một lần, trên máy phát triển)
1. Tải *Windows embeddable package (64-bit)* Python **3.12.x** ở python.org, giải nén vào `Python/`.
2. Sửa `Python/python312._pth` thành đúng 4 dòng: `python312.zip`, `.`, `..\backend`, `import site`. Thiếu `..\backend` thì server và tiến trình con xử lý ảnh không tìm thấy mã.
3. Ở thư mục gốc:
   ```powershell
   Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile .\Python\get-pip.py
   .\Python\python.exe .\Python\get-pip.py
   .\Python\python.exe -m pip install --no-warn-script-location -r backend\requirements.txt
   .\Python\python.exe -c "import fastapi, cv2, vpype; print('ok')"
   ```

## 5.3 Chuyển sang máy khác
| Cách | Gửi gì |
|---|---|
| GitHub + zip Python | người nhận tải *Code → Download ZIP*; bạn gửi thêm zip `Python/` (Drive hoặc GitHub **Releases**, tối đa 2 GB / tệp) |
| Một zip đầy đủ | `powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1 -Kieu daydu` → `export\VMU_PlotterPen_daydu-<ngày>.zip` |

Người nhận: chuột phải zip → Properties → **Unblock** → giải nén (zip Python giải nén **vào trong** thư mục mã, cạnh `backend\`) → bấm `launcher\tao_bieu_tuong.vbs` **một lần** → bấm icon **VMU PlotterPen** → lần đầu cho phép tường lửa ở **Mạng riêng tư**. 🧪 Máy sạch có thể đòi cài *Microsoft Visual C++ Redistributable x64* cho OpenCV.

## 5.4 Dùng hằng ngày
| Việc | Làm gì |
|---|---|
| Bật | bấm icon. Server chạy ẩn, trình duyệt mở `http://<IP LAN>:8000` |
| Tắt | không cần: đóng hết trang 10 phút thì tự tắt (đang vẽ thì chờ xong). Tắt ngay: `launcher\stop.vbs` |
| Máy khác cùng mạng | mở đúng địa chỉ trình duyệt đang hiện. Đã đặt PIN quản lý thì máy khác vào là khách |
| **Đặt PIN** | mở / tạo `data\pin.txt`, dòng `admin=<PIN>` (chữ / số / ký hiệu, 4–64 ký tự, không khoảng trắng, không dấu tiếng Việt). Từ 09/11/2026 có thể **đổi ngay trong Cài đặt → PIN quản lý** (nhập PIN cũ + PIN mới hai lần; áp dụng ngay, các trình duyệt khác bị đăng xuất; chưa có PIN thì chỉ cần nhập PIN mới). PIN mở khóa chuyển động (`unlock=`) **không dùng**: không ghi dòng đó thì bấm mở khóa là mở luôn. Tệp này không lên Git, không vào bản đóng gói. **Đừng dùng số dễ đoán** khi cho người ngoài vào mạng |
| Đổi icon | `launcher\icon.ico` phải là tệp .ico thật (đổi đuôi .png không hiện). Chuyển bằng Pillow rồi bấm lại `tao_bieu_tuong.vbs` |

## 5.5 Cập nhật bằng `Cap nhat.bat`
Người đóng gói: `powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1` → `export\VMU_PlotterPen_capnhat-<ngày-giờ>.zip` (~0,3 MB: `backend/`, `frontend/`, `launcher/`).
Người dùng: Unblock zip → chép **nguyên tệp zip** cạnh `Cap nhat.bat` → bấm đúp → chờ **XONG** → bấm icon (Ctrl+F5 nếu giao diện còn cũ).

`Cap nhat.bat`: tắt server → giải nén vào thư mục tạm, kiểm có `backend\app\main.py` và `frontend\index.html` → cất bản đang dùng vào `_ban_cu\` → thay `backend\ frontend\ launcher\` (không đụng `Python\`, `data\`, `.venv`) → `requirements.txt` đổi thì tự `pip install` (**cần Internet**). Quay lại bản cũ: tắt server, chép ba thư mục trong `_ban_cu\` ra.

## 5.6 Khi có lỗi
| Hiện tượng | Cách xử lý |
|---|---|
| "Server khong bat len duoc" kèm `No module named …` | `Python\` thiếu thư viện → chạy lại lệnh pip ở mục 5.2 |
| `Khong tim thay …\Python\python.exe` | thư mục `Python` sai chỗ / sai tên |
| Trang báo `bad_host` | mở bằng địa chỉ lạ: dùng địa chỉ trình duyệt tự mở, hoặc `http://localhost:8000` trên chính máy đó |
| Máy khác không vào được | tường lửa chặn `python.exe` (cho phép ở Private), hoặc khác mạng |
| Cổng 8000 bị chiếm | tắt chương trình đó, hoặc sửa `$port` trong `start.ps1` và `stop.ps1` |
| Lỗi khác | xem `data\server-loi.txt` |

Ghi chú kỹ thuật: `start.ps1` đặt `EXTRUXY_ALLOWED_HOSTS=localhost,127.0.0.1,<IP>`, `EXTRUXY_DATA_DIR`, `EXTRUXY_IDLE_EXIT_MIN=10`, chạy uvicorn `--host 0.0.0.0 --port 8000`. Chọn IP: card mạng có tuyến ra router ưu tiên cao nhất, bỏ `169.254.x.x`. Tệp `launcher/*.ps1, *.vbs` viết ASCII không dấu (PowerShell 5.1 đọc UTF-8 không BOM sai dấu).

---

# 6. Phân quyền khách / quản lý

## 6.1 Nguyên tắc ✅
- Máy vẽ chỉ có một. Người cần vẽ liên hệ chủ máy; chủ máy đặt giấy, bút, tạo nét, bấm chạy.
- **Máy chủ chặn thật**, giao diện chỉ ẩn nút cho gọn.
- **Chặn mặc định**: route nào không nằm trong danh sách mở cho khách thì cần quản lý. Route mới thêm sau này tự bị chặn.

## 6.2 Hai vai trò ✅
| | Khách (không đăng nhập) | Quản lý (PIN) |
|---|---|---|
| Xem trạng thái máy, tiến độ, đèn công tắc | ✔ chỉ đọc | ✔ |
| Nạp G-code, xem trước khung (chạy trong trình duyệt) | ✔ | ✔ |
| Tải ảnh, cắt, xem trước sáng tối, chọn khổ giấy (trong trình duyệt) | ✔ | ✔ |
| **Gửi ảnh cho người vận hành** (`data/customer/`, tự xóa sau vài ngày) | ✔ | – |
| Tạo nét, G-code, bản thảo | ✘ | ✔ |
| Điều khiển máy, terminal, macro, cấu hình, lưu trữ | ✘ | ✔ |

## 6.3 Đăng nhập quản lý ✅ (`app/auth.py`, `api/auth.py`, `core/auth.js`, `views/auth.js`)
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

Mở cho khách (`GUEST_ROUTES`): `GET /api/health`, `/api/status`, `/api/events` (SSE, khách chỉ nhận trạng thái), `/api/connection`, `/api/draw/schema`, `/api/auth/*`, **`POST /api/customer`** (gửi ảnh), tệp giao diện. Thêm route cho khách = thêm đúng một dòng vào danh sách **và** sửa `tests/test_auth.py` (test quét mọi route, route ngoài danh sách phải trả 401).

## 6.4 Khách gửi ảnh vào `customer/` ✅ (09/11/2026; `api/customer.py`, `services/customer.py`, `views/customer.js`)
1. **Khách** (không đăng nhập) chọn ảnh ở tab Tạo bản vẽ: cắt, chọn khổ giấy / lề / kích thước / xoay (khung ảnh hiện trên tờ giấy, không có nét), chỉnh tông và chọn preset / kiểu nét mong muốn (chỉ xem trước **ảnh xám**, không có mô phỏng G-code), điền tên + ghi chú (không bắt buộc), bấm **"Gửi ảnh"**. Khách không thấy mục "Thông số vẽ" (tốc độ, Z, chờ) và không gửi được các số đó.
2. Trình duyệt thu nhỏ ảnh còn ≤ 1600 px (JPEG) rồi `POST /api/customer` (multipart: `file` + `meta` = `{name, note, params}`). Máy chủ **giải mã rồi ghi lại thành JPEG** (không bao giờ lưu nguyên tệp khách gửi; bỏ EXIF; nền trong suốt thành trắng), tối đa 3 MB / 60 triệu điểm; thông số chỉ nhận khóa `[a-z0-9-]`, giá trị chuỗi ≤ 40 ký tự / số / bool, tổng ≤ 8 KB.
3. Lưu ở `data/customer/<giờ>-<8 ký tự ngẫu nhiên>/` (`image.jpg` + `meta.json`). **Tự xóa sau `customer_days` ngày** (mặc định **5**, chỉnh 1–30 ở Cài đặt → Bản thảo → "Ảnh khách gửi giữ"); dọn mỗi lần gửi / liệt kê, không có luồng nền. Bản thảo (SVG, G-code, JSON) **không** tự xóa, vẫn theo hạn mức 50 bản / MB.
4. Giới hạn: **6 ảnh / giờ** theo từng nguồn (qua Cloudflare dùng `CF-Connecting-IP`), tối đa **100 mục** và **300 MB** (đầy thì báo "hộp ảnh đầy").
5. **Quản lý** thấy hộp thư "Ảnh khách gửi" trong tab Tạo bản vẽ (ảnh nhỏ, tên, ghi chú, giờ gửi, ngày tự xóa; chấm ● = chưa xem; làm mới mỗi 30 s). **Mở** = nạp ảnh + điền lại vùng cắt và các ô thông số khách chọn (chỉ các ô tiền xử lý / kiểu nét / màu / bố trí / cỡ bút, danh sách trắng) rồi **bạn tự bấm "Tạo nét"**; **Xóa** = hộp xác nhận rồi xóa khỏi máy chủ.
API: `POST /api/customer` (khách); `GET /api/customer`, `GET /api/customer/{id}/image`, `POST /api/customer/{id}/seen`, `DELETE /api/customer/{id}` (quản lý).

---

# 7. Mạng LAN, phát 4G, demo không Internet

- Launcher đã mở cho mạng (`--host 0.0.0.0`, tự thêm IP vào danh sách Host).
- **Giao diện chạy được khi không có Internet** ✅: không tải gì từ ngoài (không CDN, không font Google).
- Wi-Fi của mạch MKS **không cần** vào mạng (USB là đủ). Vào thì có thêm đường điều khiển qua WebUI FluidNC, **vượt qua mọi khóa của phần mềm**: tắt hoặc đặt mật khẩu mạnh trước demo.
- **Đặt PIN quản lý** (`admin=`) trước khi cho người khác vào mạng; PIN mở khóa chuyển động chưa dùng.

**Vào giao diện từ điện thoại (khi laptop đã có Wi-Fi)**
1. Nối laptop vào Wi-Fi **trước**, rồi mới bấm icon **VMU PlotterPen** (launcher đọc IP lúc bật). Đã bật rồi mới nối Wi-Fi: chạy `launcher\stop.vbs`, bấm icon lại.
2. Trang tự mở trên laptop với địa chỉ dạng `http://192.168.x.x:8000`: đó là địa chỉ cần dùng. Không thấy thì mở PowerShell gõ `ipconfig`, lấy dòng *IPv4 Address* của Wi-Fi, thêm `:8000`.
3. Điện thoại nối **cùng Wi-Fi** (tắt 4G cho chắc), mở trình duyệt, gõ đúng địa chỉ đó, bắt đầu bằng `http://` (không phải `https://`).
4. Lần đầu Windows hỏi tường lửa: chọn **Mạng riêng tư**. Không hỏi mà điện thoại vẫn không vào: Settings → Network & internet → Wi-Fi → mạng đang nối → **Private network**.
5. Chưa đặt PIN thì ai vào cũng là quản lý: đặt `admin=` trước (mục 5.4).

| Triệu chứng | Thường là |
|---|---|
| điện thoại xoay mãi, laptop thì vào được | Wi-Fi công cộng (trường, quán) không cho hai máy thấy nhau ("client isolation"): dùng điện thoại phát Wi-Fi hoặc router mini |
| trang báo `bad_host` | gõ địa chỉ khác địa chỉ launcher mở (tên máy, IP cũ). IP đổi mỗi lần nối lại mạng: bấm lại icon, dùng địa chỉ mới |
| chỉ vào được khi tắt tường lửa | mạng đang xếp là Public: đổi sang Private (bước 4) |

| Cách phát Wi-Fi cho demo | Internet | Ghi chú |
|---|---|---|
| **Router du lịch / router mini** (cắm USB 5 V) | không cần | ổn định nhất, nhiều máy vào cùng lúc; giữ chỗ IP → in sẵn **mã QR** địa chỉ |
| Router 4G bỏ túi | có | như trên + dùng được Cloudflare Quick Tunnel |
| Điện thoại phát 4G | có | dễ nhất (buổi thử 03/11); số máy vào giới hạn, IP đổi mỗi lần, có thể tự tắt khi màn hình tắt |
| Laptop Windows "Mobile hotspot" | ⚠ | Windows thường đòi có kết nối để chia sẻ |

**Phát 4G từ điện thoại:** cho laptop vào mạng phát **trước** rồi mới bấm icon (launcher đọc IP lúc bật). Windows thường xếp mạng phát là **Public** → đổi sang Private hoặc cho phép cả Public ở tường lửa. Android thường `192.168.43.x`, iPhone `172.20.10.x`. Dữ liệu giữa laptop và điện thoại không ra Internet nên gần như không tốn 4G.

**Cho người ở xa xem** (cần 4G): `cloudflared tunnel --url http://localhost:8000` tạo địa chỉ tạm `*.trycloudflare.com`, không cần tài khoản (chỉ để thử, tối đa 200 yêu cầu đồng thời). **Chỉ dùng sau khi đặt PIN quản lý.**

**Mở ra ngoài ngay trên laptop** ✅: xem mục 9 (tên miền, Cloudflare Tunnel, `data\mang.txt`, nút QR trên header).

💡 Ý tưởng chưa thử: cổng đón (captive portal) bằng dnsmasq để điện thoại vào Wi-Fi là tự mở giao diện.

---

# 8. Chạy tay không dùng launcher, GitHub Codespaces

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

# 9. Tên miền và Cloudflare Tunnel (mở giao diện cho máy khác) ✅

Đường **chạy ngay trên laptop**, đã chạy thật. Dùng Cloudflare Tunnel + mã QR.

## 9.1 Bức tranh một dòng

```
Điện thoại / máy khác ──► https://plotter.tenmien.com ──► Cloudflare ══(đường ống)══► laptop: cloudflared ──► phần mềm (cổng 8000)
```

Laptop **tự gọi ra** Cloudflare và giữ một đường ống. Người ngoài vào địa chỉ trên, Cloudflare chuyển qua đường ống về phần mềm. **Không mở cổng router, không cần IP công cộng, có sẵn HTTPS (khóa).**

## 9.2 Các từ sẽ gặp (lời thường)

| Từ | Nghĩa |
|---|---|
| **Tên miền** (`tenmien.com`) | "Tên nhà" trên Internet. Bạn lấy `.tech` miễn phí 1 năm từ Student Pack; hết năm phải trả tiền gia hạn nếu muốn giữ. |
| **Tên con** (subdomain, `plotter.`) | Phần đứng **trước** tên miền: `plotter.tenmien.com`. Giống một "phòng" trong nhà. Một tên miền tạo được vô số tên con miễn phí. Ta dùng riêng `plotter.` cho máy vẽ, để tên miền gốc còn trống cho việc khác (vd trang giới thiệu). Tên con đặt gì cũng được (`ve.`, `may.`…), miễn **khớp ở mọi chỗ** (mục 9.5). |
| **DNS** | "Danh bạ" Internet: đổi tên chữ thành địa chỉ máy. |
| **Nameserver** | Máy giữ danh bạ của tên miền bạn. Ta đổi sang của Cloudflare để Cloudflare được tạo mục `plotter.` và nối vào đường ống. |
| **Cloudflare** | Công ty cung cấp đường ống miễn phí (gói Free). |
| **`cloudflared`** | Chương trình nhỏ trên laptop, tạo và giữ đường ống. |
| **Tunnel (đường ống)** | Kết nối do laptop mở **ra ngoài**; vì vậy không cần mở cổng vào. |
| **Host** | Tên người ta gõ để vào. Phần mềm chỉ nhận Host nằm trong danh sách cho phép (chống trang lạ giả mạo); `data\mang.txt` thêm tên của bạn vào danh sách. |

## 9.3 Đã làm xong những gì

| Việc | Ở đâu |
|---|---|
| Tên miền đưa vào Cloudflare (gói Free) | trang Cloudflare ✅ |
| Đổi nameserver ở nhà đăng ký `.tech` sang `<tên-1>.ns.cloudflare.com` + `<tên-2>.ns.cloudflare.com` | trang nhà đăng ký ✅ (đã lan ra, tên miền Active) |
| Cài `cloudflared` | laptop ✅ |
| Launcher đọc `data\mang.txt` (thêm tên miền, giữ server không tự tắt, bật đường ống, đặt địa chỉ cho QR); `stop` tắt luôn đường ống | `launcher/start.ps1`, `stop.ps1` ✅ (đã chạy thật 24/11/2026, mở được từ 4G) |
| Máy chủ nhận tên miền con dạng `.trycloudflare.com` (dấu chấm đầu = mọi tên con) | `backend/app/main.py` |
| **Nút QR trên header**: hiện 2 mã, địa chỉ Internet và địa chỉ trong mạng nhà (điện thoại cùng Wi-Fi). **Khách cũng thấy nút**, nhưng chỉ nhận mã địa chỉ Internet (IP mạng nhà chỉ cho quản lý). Hộp thoại vừa màn điện thoại, có hiệu ứng mở (tắt khi máy bật chế độ giảm chuyển động) | `api/share.py`, `services/share.py`, `views/share.js`, `polish.css` |

## 9.4 Các bước đã làm (24/11/2026, tên miền đã **Active**; giữ lại để làm lại ở máy khác)

Tên miền Active khi Cloudflare báo email "is now active" hoặc trang tên miền hiện chữ Active.

**Bước C: tạo đường ống** (PowerShell, mỗi lệnh một lần):
1. `cloudflared tunnel login` → trình duyệt mở ra, chọn tên miền `tenmien.com`, bấm Authorize. Ghi một tệp `cert.pem` vào `%USERPROFILE%\.cloudflared\`.
2. `cloudflared tunnel create plotter` → tạo đường ống tên `plotter`, in ra một **mã dài** (Tunnel ID) và tệp `<mã>.json` (chìa khóa đường ống, **bí mật**, không đưa lên Git hay gửi cho ai).
3. `cloudflared tunnel route dns plotter plotter.tenmien.com` → tạo mục `plotter.` trong danh bạ, trỏ vào đường ống.

**Bước D: tệp cấu hình** `%USERPROFILE%\.cloudflared\config.yml`:
```yaml
tunnel: <mã dài ở bước C2>
credentials-file: C:\Users\ducwt\.cloudflared\<mã dài>.json
ingress:
  - hostname: plotter.tenmien.com
    service: http://localhost:8000
  - service: http_status:404
```
Hai dòng `ingress` nghĩa là: tên `plotter.…` thì chuyển vào phần mềm (cổng 8000), tên khác thì trả 404.

**Tệp `data\mang.txt`** (không lên Git):
```
host=plotter.tenmien.com
url=https://plotter.tenmien.com
giu_bat=1
tunnel=plotter
```
| Dòng | Tác dụng |
|---|---|
| `host=` | thêm tên vào danh sách Host được phép |
| `url=` | địa chỉ hiện ở mã QR Internet |
| `giu_bat=1` | server không tự tắt sau 10 phút đóng trang (có dòng `tunnel=` thì **tự coi như `giu_bat=1`**, nếu không server tắt mà đường ống mồ côi; tắt bằng icon **Tắt**) |
| `tunnel=` | launcher chạy `cloudflared tunnel run plotter` cùng server |

**Bước E: thử.** Tắt rồi bật lại phần mềm bằng icon (launcher chỉ đọc `mang.txt` khi bật server mới). Tắt Wi-Fi trên điện thoại, dùng 4G, quét mã QR "Từ bất kỳ đâu". Lỗi đường ống: `data\tunnel-loi.txt`; lỗi server: `data\server-loi.txt`.

**Chỉ cần thử nhanh, không tên miền** (địa chỉ đổi mỗi lần): `host=.trycloudflare.com` trong `mang.txt`, rồi chạy tay `cloudflared tunnel --url http://localhost:8000` và mở địa chỉ `https://….trycloudflare.com` mà nó in ra.

## 9.5 Chỗ dễ sai

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| "Host không được phép" (403, `bad_host`) | tên trong `host=` không khớp tên đang gõ; chưa tắt / bật lại launcher |
| Vào được nhưng không đăng nhập được | đang vào bằng `http://` mà không phải `https://`; hoặc PIN chưa đặt (xem mục 9.6) |
| Không vào được từ 4G, trong nhà vẫn vào | đường ống chưa chạy (`tunnel-loi.txt`), hoặc laptop ngủ |
| Hộp thoại "Đường hầm Cloudflare bị tắt ngay lúc khởi động" (hoặc `tunnel-loi.txt` có `panic` / `0xc0000005`) | cloudflared sập khi khởi động trên máy mượn (25/11/2026, chưa rõ nguyên nhân: USB thiếu dòng, máy quá cũ, hay diệt virus). Launcher đã tự chép `cloudflared.exe` sang thư mục tạm của máy rồi chạy ở đó (loại trừ USB đọc sai) và báo bằng hộp thoại. Kiểm: `Get-FileHash` tệp phải khớp bản chính thức cùng số bản; chạy `cloudflared.exe --version` |
| Sửa giao diện xong, điện thoại vẫn hiện bản cũ | trình duyệt hoặc Cloudflare giữ tệp cũ. Từ 26/11/2026 máy chủ gửi `Cache-Control: no-cache` cho tệp giao diện, nên **khởi động lại phần mềm** rồi tải lại cứng một lần; Cloudflare còn giữ bản cũ thì Caching → Purge Everything (hoặc đợi vài giờ) |
| Chạy được vài phút rồi mất | laptop vào chế độ ngủ: Cài đặt Windows → Nguồn → không ngủ khi cắm sạc |
| QR chỉ hiện "Chưa có địa chỉ" | không bật bằng launcher (icon), hoặc `mang.txt` thiếu dòng `url=` |
| QR mạng nhà không quét được | điện thoại không cùng Wi-Fi; hoặc Windows xếp mạng là Public (đổi sang Private, mục 7) |

## 9.6 An toàn (đọc kỹ)

- Chủ dự án **chọn không bắt buộc PIN** khi mở ra ngoài. Hệ quả: **chưa đặt PIN thì bất kỳ ai có địa chỉ đều là quản lý và mở khóa được máy**, kể cả cho máy chạy G-code. Tên `plotter.…` không bí mật (địa chỉ web bị lộ qua lịch sử, ảnh chụp màn hình, mã QR).
- Máy thật vẫn mặc định **chỉ đọc**; chạy được là sau khi mở khóa chuyển động (tự khóa lại sau 15 phút). Nên **đặt PIN trước khi nhờ người khác thử**: dòng `admin=<số>` và `unlock=<số>` trong `data\pin.txt`.
- Trước khi cho **người ngoài** vào lâu dài, nên bật thêm **Cloudflare Access** (đăng nhập bằng email; có gói miễn phí cho nhóm nhỏ, số người chưa kiểm): lớp khóa thứ hai trước cả PIN. Chưa làm.
- Chìa khóa đường ống (`<mã>.json`, `cert.pem` trong `%USERPROFILE%\.cloudflared\`) nằm **ngoài** thư mục dự án; đừng chép vào repo.

## 9.7 Tắt

Bấm icon **Tắt**: dừng server và dừng đường ống (chỉ tiến trình `cloudflared` chạy đúng tên trong dòng `tunnel=`, không đụng đường ống khác). Tắt hẳn việc mở ra ngoài: xóa `data\mang.txt` rồi bật lại. Ngắt hẳn từ phía Cloudflare: xóa mục DNS `plotter` hoặc `cloudflared tunnel delete plotter`.

## 9.8 Giới hạn đã biết

- Máy chủ (laptop) phải bật, có mạng và **không ngủ**. Máy chủ ở nhà hoặc trên cloud kèm ESP32-S3 sẽ bỏ ràng buộc "cạnh máy vẽ" (mục 13).
- Mỗi trang hỏi `/api/status` 10 lần/giây: nhiều người cùng xem thì nên giãn nhịp cho khách. IP nguồn qua đường ống luôn là 127.0.0.1, nên phân biệt người bằng cookie phiên, không bằng IP.
- Đã thử (24/11/2026): mở giao diện từ điện thoại qua 4G thành công. Chưa thử: đăng nhập PIN và thao tác ghi qua tên miền (Origin / cookie), nhiều người cùng lúc, laptop ngủ rồi bật lại.

---

# 10. Mang theo bằng SSD, dùng máy mượn (ghi 24/11/2026; **làm 25/11/2026: launcher đã chạy được ở máy chính; chưa thử máy thứ hai**)

Bối cảnh: chủ dự án không có laptop, mượn máy; có một ổ SSD ngoài để mang `Python\` và `data\` đi. Làm từ 25/11 (việc: [12](12_VIEC_CAN_LAM.md) mục 4.4).

| Quyết định | Lý do |
|---|---|
| Mỗi máy chỉ **chạy** đường ống `plotter` bằng **chìa khóa `.json`** (không cần `cert.pem`, không đăng nhập tài khoản Cloudflare trên máy mượn) | `cert.pem` chỉ cần khi **tạo** đường ống; chìa khóa cho phép chạy |
| `launcher\cloudflared.exe` mang theo, không cài | máy mượn không cài gì |
| Chìa khóa để ở `data\cloudflared\` (Git bỏ qua) | cùng chỗ với `data\` |
| **Chỉ bật đường ống trên một máy một lúc** | hai máy cùng giữ chìa khóa và cùng chạy thì Cloudflare chia người vào cho cả hai |
| SSD định dạng **exFAT**; clone **kho gốc** vào SSD; `git pull` để cập nhật | exFAT cả Windows và Ubuntu đọc được; `origin` là kho gốc nên pull không liên quan tới fork |
| **`data\` trên SSD là bản duy nhất** | Git bỏ qua `data\`; sao lưu định kỳ, **không đưa lên Git** (có PIN) |
| Python: **mang theo thư mục `Python\`** (bản không cần cài, 3.12 x64, ~590 MB, đủ thư viện): cố định, không phụ thuộc máy mượn, không cần Internet. **Không chép `.venv`**; `Cai may moi.bat` (tạo lại venv bằng Python 3.12 của máy) chỉ là đường dự phòng. Launcher thử chạy thật `.venv` rồi `Python\`; không cái nào chạy được thì báo chạy `Cai may moi.bat`. Muốn chạy test trên máy mượn: một lần `Python\python.exe -m pip install -r backend\requirements-dev.txt`. Khi `requirements.txt` đổi: cập nhật một lần vào `Python\` trên SSD (cần Internet) | `.venv` ghi cứng đường dẫn Python của máy đã tạo nó (`pyvenv.cfg`: `home = …`), sang máy khác thì hỏng; thư viện cài vào venv của dự án nên Python hệ thống của máy mượn vẫn sạch. Đã sửa 25/11/2026 (bỏ ý `libs\`) |
| Sửa mã ở máy mượn: **fork** kho gốc, clone fork, push lên fork, **Pull Request** về kho gốc; kho gốc duyệt rồi gộp; trên SSD `git pull` | đăng nhập GitHub trên máy mượn phải là tài khoản sở hữu fork; **đăng xuất sau khi dùng** (Credential Manager nhớ) |
| Máy Linux / máy nhỏ sau này: ⏸ tạm bỏ (mục 14); `data\` chép sang, chìa khóa `.json` dùng được trên Linux | mục 14 |

**Cái cần mang theo SSD (đều bị Git bỏ qua):** `Python\`, `data\` (~5 MB: bản thảo, hồ sơ, `pin.txt`, `mang.txt`, `cloudflared\` chứa chìa khóa `.json`) và `launcher\cloudflared.exe` (tải từ Cloudflare). **Không cần:** `backend\.venv` (~580 MB, tạo lại nếu cần), `export\` (~570 MB: kết quả đo, ảnh thử, phiếu giao việc; chép riêng thư mục nào cần), `.playwright-mcp\`, `__pycache__\`. Ngoài kho: ghi nhớ của Claude nằm ở `~\.claude\projects\…\memory` của từng máy.

**Đã thử (25/11/2026, máy chính):** tạm đổi tên thư mục `.cloudflared` của người dùng (không còn `config.yml`, `cert.pem`), bật bằng icon với `launcher\cloudflared.exe` + chìa khóa trong `data\cloudflared\` → mở được giao diện từ 4G. Chưa thử trên máy thứ hai. Chưa kiểm: "dubious ownership" của Git trên ổ ngoài; Docker đọc ghi thư mục `data` trên exFAT; Zero Trust gói Free có đòi thẻ khi đăng ký không (nếu đòi thì **không dùng**, cách USB vẫn đủ).

**Máy chạy cố định (chủ dự án chốt 26/11/2026):** laptop của bạn cùng dự án là **máy chạy cố định**; máy ở nhà chỉ để code; bỏ cách mang SSD đi. Gửi cả `data\` (kể cả `pin.txt`, chìa khóa `cloudflared\`) cho bạn đó (người cùng dự án, chủ dự án chấp nhận). Trên laptop đó: clone repo, chạy `Cai may moi.bat`, tải `cloudflared.exe` từ GitHub (kiểm mã băm), cập nhật mã bằng `git pull`. **`data\` trên laptop đó là bản chính**; `data\` ở nhà chỉ để thử. **Chỉ máy đó bật đường ống**: máy ở nhà bỏ dòng `tunnel=` trong `data\mang.txt` (hai máy cùng bật thì Cloudflare chia người xem sang cả hai). **27/11:** bạn đó tải `data` (zip) cùng `cloudflared.exe` về máy mình và chạy được (chủ dự án báo); chưa nối được mạch vì chưa biết cài Wi-Fi cho mạch (mục 11).

---

# 11. Wi-Fi (telnet) tới mạch MKS 🧪

Mục đích: thêm **một lựa chọn** nối máy chủ với mạch không cần dây USB, vẫn giữ USB. Mã đã xong và có test với mạch giả; **chưa nối thử mạch thật bằng phần mềm** (bạn cùng dự án thử 27/11 chưa nối được vì chưa biết cài Wi-Fi cho mạch).

## 11.1 Đã chốt (chủ dự án, 26–27/11/2026)
- Firmware **4.1.1** (chủ dự án tự nạp, xác nhận). Mạch đặt chế độ vào Wi-Fi có sẵn trước (`STA>AP`: điểm phát 4G của điện thoại); không vào được thì **tự phát điểm phát dự phòng**. Chủ dự án tự cài và đã vào được cả `fluidnc.local` lẫn địa chỉ điểm phát để điều khiển bằng WebUI (27/11).
- Máy chủ nối thẳng mạch qua telnet, không qua WebUI, không đăng nhập. Mất sóng: 3 giây không có dữ liệu thì coi là đứt.
- Backend gửi G-code **từng dòng, chờ `ok`** (`services/job.py`); mạch không chạy tệp từ bộ nhớ, không cần thẻ SD.
- **Không sửa firmware FluidNC.** Không thay WebUI của FluidNC bằng tab Điều khiển của mình (mục 12).
- Giao diện ↔ máy chủ giữ HTTP + SSE ([08](08_QUYET_DINH_THIET_KE.md) A6), không đổi WebSocket.

## 11.2 Đọc mã FluidNC (chỉ đọc, `D:\FluidNC-4.1.1`; thư mục không có Git nên chưa chắc giống hệt bản trên mạch)
| Điều | Mã nói | Tệp (thư mục `FluidNC/src/`) |
|---|---|---|
| Telnet | Mặc định bật, cổng 23 (`$Telnet/Enable`, `$Telnet/Port`) | `WebUI/TelnetServer.cpp` |
| Nhận gì | TCP thô: G-code + ký tự tức thời; chỉ bỏ các chuỗi điều khiển telnet bắt đầu bằng byte 0xFF | `TelnetClient.cpp` |
| Mật khẩu | **Không có.** Số máy nối cùng lúc = trần mặc định của thư viện ESP32 (con số chưa kiểm chứng) | `TelnetClient.cpp`, `TelnetServer.cpp` |
| Mất kết nối | Chỉ xóa kênh; **không tạm dừng, không nâng bút**; chạy hết ~15 lệnh đã nhận rồi đứng | `TelnetClient::closeOnDisconnectLocked` |
| Mạng dự phòng | `FluidNC`, IP `192.168.0.1`; mật khẩu mặc định (công khai trong mã nguồn, **phải đổi**: `$AP/Password`) | `WifiConfig.cpp` 681–683; chế độ `STA>AP` dòng 35–42 |
| Tiết kiệm điện Wi-Fi | `$WiFi/PsMode` mặc định `None` (phản hồi nhanh nhất) | `esp32/WifiImpl.cpp` |
| Tên và IP | `$Hostname` = `fluidnc` (mDNS `fluidnc.local`); xem IP bằng `$System/IP` | `NetSettings.cpp`, `WifiConfig.cpp` |
| Lệnh cài Wi-Fi | `$WiFi/Mode`, `$Sta/SSID`, `$Sta/Password`, `$AP/SSID`, `$AP/Password` | `WifiConfig.cpp` 678–698 |
| Bộ nhớ tệp của mạch (bản 4 MB) | 192 KB (`min_littlefs.csv`): chứa `config.yaml` + WebUI `index.html.gz` (~110 KB) | `min_littlefs.csv` |

## 11.3 Đã làm trong phần mềm (26/11, commit `3962d63`)
| Tệp | Thay đổi |
|---|---|
| `backend/app/links/telnet_link.py` (mới) | `TelnetLink(BaseLink)`, `kind="wifi"`; mở kết nối chờ 5 s, mất sóng 3 s, luồng đọc thức dậy mỗi 0,5 s; ghi có thời hạn riêng |
| `backend/app/services/machine.py` | `connect(..., host, tcp_port)`, `mode="wifi"`. **Sửa an toàn:** hằng `REAL_MODES = ("serial", "wifi")` thay các chỗ chỉ kiểm `"serial"` → khóa chuyển động áp cho cả Wi-Fi |
| `backend/app/api/machine.py` | `ConnectRequest`: `mode` thêm `"wifi"`, `host` (chỉ chữ, số, `.`, `-`), `tcp_port` 1–65535 |
| `frontend` (Cài đặt → Kết nối) | Lựa chọn "Máy thật (Wi-Fi, telnet)", ô địa chỉ (mặc định `fluidnc.local`), cảnh báo không mật khẩu |
| `backend/tests/test_telnet_link.py` (mới) | Mạch giả qua TCP: nối; Wi-Fi vẫn khóa chuyển động; chạy trọn tác vụ; mất sóng giữa chừng thì dừng và chạy tiếp được; im lặng thì báo mất; cổng đóng thì báo lỗi gọn; thiếu host thì từ chối |

## 11.4 Đã kiểm lại 27/11/2026 (bạn cùng dự án rà mã trên commit `062ff85`; Claude đối chiếu từng điểm với mã)
- `pytest` 694 qua, 1 hỏng chập chờn (`test_old_logs_are_pruned` khi chạy song song 6 tiến trình; chạy riêng thì qua). `node --test` **chưa chạy** trên máy đó (chưa cài Node).
- Các lỗi cũ đã sửa: nút áp dụng cấu hình mạch giờ cũng khóa cho Wi-Fi; thời hạn ghi tách riêng khỏi thời hạn đọc; chú thích đầu tệp; thêm 3 bài test (ghi sau khi đóng, byte `0xFF`, dòng dài trên 4096 byte).
- Còn lại, mức thấp (đều đúng với mã) — **đã sửa 27/11/2026** (`TelnetFilter` lọc đủ chuỗi điều khiển telnet và giữ trạng thái qua các lần đọc; ghi lỗi / quá hạn thì báo mất kết nối ngay, chỉ một lần; ô baud chỉ kiểm khi dùng USB; `tests/test_telnet_link.py` 23 bài, đã kiểm đột biến):
  - `telnet_link.py`: mới bỏ byte `0xFF` lẻ, chưa bỏ đủ chuỗi điều khiển telnet 3 byte. FluidNC không chủ động gửi chuỗi đó nên chưa ảnh hưởng.
  - `telnet_link.py`: ghi bị quá thời hạn thì báo lỗi nhưng không đóng kết nối ngay; việc đóng chờ luồng đọc phát hiện (≤ 3 s).
  - `settings.js`: chế độ Wi-Fi vẫn kiểm ô baud dù đã ẩn (thừa một bước, không gây lỗi).
- **Chưa kiểm chứng:** nối mạch thật; đo tốc độ; đối chiếu lại mã FluidNC trên máy bạn (máy đó không có `D:\FluidNC-4.1.1`).

## 11.5 Rủi ro đã biết
| Rủi ro | Cách giảm |
|---|---|
| Telnet không mật khẩu: ai cùng mạng gửi lệnh thẳng vào mạch, **vượt PIN và khóa** | Chỉ dùng điểm phát điện thoại có mật khẩu mạnh; không dùng Wi-Fi trường, quán |
| Mạng dự phòng còn mật khẩu mặc định | Đổi `$AP/Password` (việc 2 ở 11.6) |
| Mất sóng giữa bản vẽ: bút có thể đang hạ → loang mực | Chạy tiếp bằng "Tiếp tục từ điểm dừng"; đo số giây báo mất ở việc 5 |
| Điện thoại gọi điện, tắt màn, hết pin → tắt điểm phát | Cắm sạc; đo ở việc 5 |
| Mạch rơi về mạng dự phòng → máy chủ vào mạng `FluidNC` → mất Internet → mất đường ống Cloudflare | Chỉ điều khiển tại chỗ lúc đó |
| Dừng khẩn không qua Wi-Fi được | Nút cứng (mục 13) |
| **Mạch nhận lệnh từ mọi cổng cùng lúc** (telnet, WebUI, USB) | Đang vẽ thì không bấm gì trên WebUI; mật khẩu Wi-Fi là khóa chung |
| Telnet khóa bằng sửa firmware (`ENABLE_AUTHENTICATION`) | **Không làm:** chỉ khóa việc đọc / ghi cài đặt `$`, không khóa G-code; lại phải biên dịch và nạp lại firmware. Khóa thật là mật khẩu điểm phát |

## 11.6 Việc còn phải làm
| # | Việc | Ai |
|---|---|---|
| 1 | Kiểm trên mạch (chỉ đọc): `$I`, `$WiFi/Mode`, `$Telnet/Enable`, `$Telnet/Port`, `$WiFi/PsMode`, `$System/IP`. Không gửi mật khẩu cho ai | chủ dự án |
| 2 | Đổi mật khẩu mạng dự phòng (`$AP/Password`) hoặc đặt `$WiFi/Mode=STA` | chủ dự án (ghi xuống mạch = người bấm) |
| 3 | Nối thử qua Wi-Fi bằng phần mềm, **chỉ xem trạng thái**, không chạy (khởi động lại phần mềm trước) | chủ dự án |
| 4 | Viết `tools/do_duong_truyen.py`: gửi 500 lần `$G` (chỉ đọc, chạy được cả khi Alarm), in số dòng/giây và thời gian đi–về (trung vị / 95 % / lớn nhất); `--serial COMx` hoặc `--host fluidnc.local` | Claude, chưa làm |
| 5 | Đo: `$G` qua USB và qua Wi-Fi; tệp 7.6 (bút nâng, vẽ trên không; mốc USB ~125 dòng/giây); tắt điểm phát giữa chừng, ghi số giây báo mất, mạch chạy thêm bao lâu, bút ở đâu | chủ dự án |
| 6 | Quyết theo số đo: gần bằng USB thì dùng; chậm thì gửi dồn; hay rớt thì giữ USB làm chính | cùng quyết |

# 12. WebUI của FluidNC và việc đổi giao diện

## 12.1 Ba thứ riêng biệt (hay nhầm)
| Thứ | Nằm ở đâu | Việc của nó |
|---|---|---|
| Firmware FluidNC (C++) | Bộ nhớ chương trình của ESP32, đã nạp sẵn | Nhận từng dòng G-code, điều khiển động cơ, trả `ok` và trạng thái. Đây là "lõi" |
| `config.yaml` + `index.html.gz` | Bộ nhớ tệp (flash) 192 KB | `config.yaml` khai máy; `index.html.gz` (~110 KB) là trang WebUI |
| Trang WebUI đang chạy | **Trình duyệt** của điện thoại / laptop | JS của WebUI gửi lệnh về firmware qua HTTP `/command?plain=` hoặc WebSocket |

Ví dụ đời thường: firmware là người thợ trong xưởng; WebUI là cái bảng nút bấm gắn trên tường; bấm nút chỉ là đưa cho thợ tờ giấy "làm việc này".

Nguồn gốc (suy luận, chưa có nguồn nói thẳng ở phần lịch sử): Grbl gốc chỉ có cổng serial; Grbl_ESP32 (2018) lấy phần mạng (máy chủ web, telnet) từ ESP3D của Luc Lebosse (đầu tệp `WebUIServer.cpp`, `TelnetServer.cpp` ghi "Copyright (c) 2014 Luc Lebosse"). WebSocket có để **đẩy chữ trả lời của máy lên trình duyệt ngay**. Không có WebUI vẫn bấm qua cổng 80 được: mạch có sẵn trang nhỏ ~6,8 KB nhúng trong firmware (`NoFile.h`) và đường `http://fluidnc.local/command?plain=<lệnh>`.

## 12.2 Tệp WebUI của chủ dự án (đã xem 27/11, chỉ đọc)
- `D:\index.html.gz` (111 625 byte) do chủ dự án **tải từ bộ nhớ flash của mạch về**. Giải nén ra một bản sao để xem: là ESP3D-WEBUI bản `github.com/MitchBradley/ESP3D-WEBUI@a690c889`, dùng **Bootstrap 3.3.7**, **một tệp duy nhất** 505 KB (JS, CSS, HTML chung), JS gọi mạch qua WebSocket.
- Mã nguồn (27/11): **đúng là `a690c889`**: đóng gói lại bản này ra cùng 330 hàm, 370 `id` với tệp trên mạch. FluidNC chép sẵn một bản WebUI vào mỗi lần phát hành; ESP3D-WEBUI 3.x của Luc **không** hỗ trợ FluidNC nên không dùng. Mã đã chép vào **`webui/`** (gốc: nhánh `revamp` @`028ae9cf`, mới hơn 12 commit, không cần lệnh firmware mới; tính năng `/ui/<tên>/` chỉ bật khi đặt ở đó). Giấy phép GPL-3.0, cách đóng gói và luật sửa: `webui/README.md`. Bản `revamp` nén **121 KB** (bản trên mạch 111,6 KB).
- Mạch chỉ phát tệp tên đúng `index.html.gz` (`WebUIServer.cpp` dòng 667); tệp tên khác bị **tải về** thay vì hiện (dòng 708–709). Muốn thay trang thì **thay đúng tên đó**; giữ `D:\index.html.gz` để trả lại.

## 12.3 Vì sao không đưa tab Điều khiển của mình vào mạch
Tab Điều khiển chỉ là vỏ; **khóa chuyển động, PIN, gửi từng dòng, dừng an toàn, chạy tiếp, nhật ký đều nằm ở backend Python**, mạch không có Python. Trang trên điện thoại mà tự gửi từng dòng thì điện thoại tắt màn là bản vẽ dừng. Thêm một cửa điều khiển nữa không qua PIN cũng là giảm an toàn. Kết luận: giữ WebUI gốc làm đường cứu hộ; mọi điều khiển bản vẽ đi qua phần mềm.

## 12.4 Đổi giao diện WebUI, giữ nguyên chức năng (ý của chủ dự án 27/11, **chưa làm**)
| | Cách A: chèn CSS của mình vào tệp có sẵn | Cách B: build lại từ mã nguồn GitHub |
|---|---|---|
| Làm gì | Giải nén, thêm một khối `<style>` đè lên Bootstrap, nén lại thành `index.html.gz` | Tải mã nguồn về thư mục riêng, sửa HTML/CSS, build bằng Node |
| Chức năng | Không đổi (không đụng JS) | Dễ lỡ tay đổi; phải thử kỹ |
| Làm được | Màu, chữ, nút to cho ngón tay, khoảng cách; **sắp lại khối thì hạn chế** | Sắp lại thành khối như tab Điều khiển của mình |
| Dung lượng | Tăng vài KB (CSS của mình nén khoảng 9 KB) | Tùy mức sửa; ước tính còn nằm trong 192 KB nhưng chưa build thử |

Thứ tự: làm A trước, thấy chưa đủ thì sang B. Chủ dự án tự tải tệp mới lên bộ nhớ tệp của mạch; Claude không ghi xuống mạch. **Chủ dự án chốt 27/11:** khối khung phải **dễ nhìn như web của mình**; máy chỉ dùng bút nên **ẩn spindle / laser**; macro hiện không có nút để bấm; **giữ nguyên mọi chức năng JS**, chỉ đổi giao diện (làm sau). Chốt 27/11: đi **cách B**, mã ở `webui/` (gốc nhánh `revamp`), đã đóng gói thử được. Tệp thành phẩm để **ở gốc repo, cùng cấp README** (tên tệp: chưa chốt), ghi chú ở `webui/README.md`. **Chưa kiểm chứng:** chức năng thật chỉ thử được sau khi nạp lên mạch; dung lượng còn trống trên mạch.

Phương án khác (ý 26/11, chưa quyết): một **trang cứu hộ riêng** ≤ 30 KB nén chỉ có trạng thái và tọa độ, Mở khóa, Home, jog, bút lên xuống, Tạm dừng / Chạy tiếp / Dừng; không xử lý ảnh, không gửi từng dòng.

# 13. ESP32-S3 làm cầu nối và nút dừng cứng ⏳

Ý của chủ dự án (27/11): máy chủ (PC ở nhà hoặc server cloud) chạy phần mềm; quanh máy vẽ chỉ cần **một ESP32-S3** nối vào Internet và nối dây tín hiệu vào mạch MKS. Không cần cấu hình chung Wi-Fi nội bộ giữa máy chủ và mạch; vẫn giữ điểm phát dự phòng của mạch. **Đây là thêm một phương pháp**, USB và telnet giữ nguyên.

```
 Điện thoại ─► tên miền ─► Cloudflare ─► máy chủ (backend: ảnh, G-code, PIN, khóa, nhật ký)
                                               ▲
                  ESP32-S3 tự gọi ra (WebSocket bảo mật, chìa khóa riêng, giữ kết nối liên tục)
                          │ dây UART: TX, RX, GND
                          ▼
                       MKS (uart1 + uart_channel1 trong config.yaml)
```

## 13.1 Vì sao ESP32 phải "tự gọi ra" và có kho lệnh
- `cloudflared` chạy trên Windows / Linux / Mac, **không chạy được trên ESP32**. Nên đảo chiều: ESP32 gọi tới tên miền, Cloudflare chuyển về máy chủ. Backend thêm một kiểu kết nối mới nhận thiết bị này.
- ESP32 vẫn phải vào một mạng có Internet; cài Wi-Fi cho ESP32 **một lần** (trang cài riêng trên ESP). Wi-Fi công cộng hay bắt đăng nhập qua trang web thì ESP không qua được: mang điện thoại phát 4G, để sẵn hai mạng.
- Số đo mục 4 (0,13 s thường, có lần 1,16 s) cho thấy **không thể gửi một dòng rồi chờ `ok` qua Internet**. Phân việc: **máy chủ quyết định** (chạy, dừng, chạy tiếp, biết dòng nào), **ESP thực hiện** (giữ sẵn nhiều dòng, tự gửi từng dòng xuống mạch tại chỗ, chờ `ok` tại chỗ). 10 000 dòng ≈ 200 KB; ESP32-S3 N16R8 có 512 KB RAM + 8 MB PSRAM (thông số hãng), dư sức. Lưu lượng thật chỉ khoảng 2,5 KB/giây.
- Phải tính kỹ phần dừng an toàn và chạy tiếp (đang ở [08](08_QUYET_DINH_THIET_KE.md) và `services/machine.py`): chia việc giữa máy chủ và ESP là phần việc lớn nhất. Sửa `JobRunner` là chỗ quan trọng nhất của backend nên phải hỏi chủ dự án trước khi làm.
- **Mô hình trễ** (`tools/mo_phong_gui_lenh.py`, 27/11; mô hình, chưa đo): 3000 dòng nét 0,5 mm (lý tưởng 11,2 s). Gửi từng dòng chờ `ok` qua mạng: 570 s; đếm ký tự qua mạng: 48 s, khựng ~2 300 lần; **kho ESP 5000 dòng, gói 1000, nạp trước 2000: ~11,9 s, 0 khựng**, kể cả 4G giật (0,3 s, vọt 3 s, 8 %). Gói nhỏ 200 dòng vẫn khựng khi mạng giật.
- **Chốt hướng (chủ dự án 27/11: ESP giữ dữ liệu, tải dần):** kho ≥ 5000 dòng trong PSRAM, gói ~1000 dòng, nạp trước ~2000 dòng (hoặc cả bài nếu ngắn hơn) rồi mới chạy; ESP gửi xuống MKS bằng đếm ký tự tại chỗ; ký tự tức thời chuyển ngay, Ctrl-X xóa kho. Chi tiết, giao thức nháp, gói việc: [phiếu P01](../scripts/P01-esp32-s3-cau-noi.md).

## 13.2 Phía mạch MKS (không sửa firmware)
FluidNC 4.1.1 nhận thêm một cổng UART qua `config.yaml` (`uart:` và `uart_channel:`, `MachineConfig.cpp` dòng 60–61); cổng phụ vào cùng danh sách kênh với USB (`UartChannel.cpp` dòng 36) nên nhận G-code và trả trạng thái giống USB. Mới đọc mã, **chưa thử trên mạch**. Không dùng chung cổng UART của USB (CH340).

**Đã đọc sơ đồ 27/11 (chưa đo bằng đồng hồ; bảng đầy đủ ở [phiếu P01](../scripts/P01-esp32-s3-cau-noi.md) mục 2):**
| Việc | Kết quả |
|---|---|
| Đang dùng (chủ dự án) | 2 driver X, Y (I2S `gpio.16, 17, 21`); chân **S của cổng TTL** = `gpio.32` (servo bút); endstop X, Y = `gpio.36`, `gpio.35`. Còn lại trống |
| UART phụ | **EXP2 chân 6 = IO23 (TX của MKS), chân 1 = IO19 (RX của MKS), chân 9 = GND**; nối thẳng ESP32, không dính IC đệm. EXP2 chân 8 là RESET: không đụng. EXP1 chân 3, 4, 5, 7 đi qua IC đệm một chiều nên không dùng làm RX |
| Nút Tạm dừng cứng | **J11 (cổng Z-endstop) = IO34**, chỉ vào, đã có kéo lên + lọc RC: `feed_hold_pin: gpio.34:low` |
| Probe J12 (IO22) | để cho cảm biến bút (docs/09 mục 3.1) hoặc nút Chạy tiếp |
| Nguồn ESP32-S3 | Mini560 5 V riêng (chủ dự án đã đặt); chung GND với MKS, không nối 5 V / 3V3 sang nhau |
| Baud, bộ đệm UART phụ | baud mặc định 115200, mode 8N1 (`Uart.cpp`); bộ đệm nhận cổng UART phụ **chưa kiểm** (kênh mặc định 256 byte) |

## 13.3 Nút dừng cứng (nối thẳng vào chân của MKS, không qua mạng)
Khai trong `config.yaml` mục `control:` (`Control.cpp`):
| Chân | Việc FluidNC làm |
|---|---|
| `feed_hold_pin` | Tạm dừng, như gửi `!`. **Dùng làm nút chính** (êm, giữ vị trí, chạy tiếp được) |
| `cycle_start_pin` | Chạy tiếp, như gửi `~` (cặp với nút tạm dừng) |
| `reset_pin` | Reset mềm, như Ctrl-X |
| `estop_pin` (và `fault_pin`, cùng việc) | Dừng gấp, **không giảm tốc (có thể mất vị trí)**, báo động nghiêm trọng chỉ reset mềm mới gỡ. Chú thích trong mã: nút này chỉ dừng ở mức tín hiệu điều khiển, dừng khẩn thật còn phải cắt nguồn. Có thêm hay không: chủ dự án quyết |

Lớp an toàn: (1) nút cứng thẳng MKS, mất Internet hay ESP treo vẫn chạy; (2) ESP **tự gửi `!`** khi mất kết nối với máy chủ quá N giây lúc đang vẽ (N chưa chốt; phải viết trong mã ESP); (3) điểm phát dự phòng của mạch.

## 13.4 An toàn và các việc còn mở
- Lệnh chuyển động từ Internet vào máy thật: ESP32 và máy chủ có **chìa khóa bí mật riêng** (để trong `data\`, không lên Git); PIN và khóa chuyển động vẫn ở backend; Cloudflare Access cân nhắc.
- Máy chủ chuyển lên cloud: đo RAM đỉnh bằng `tools/do_thoi_gian.py` trước khi chọn gói; backend **chưa từng chạy trên Linux**.
- Camera khi máy chủ ở xa: **chưa chốt** (ESP32-CAM chỉ để xem, hoặc webcam + máy nhỏ cạnh máy vẽ).
- Thứ tự: (1) tài liệu ✅; (2) đọc sơ đồ MKS ✅ (chưa đo); (3) mô hình trễ ✅; (4) đo chân bằng đồng hồ, mua ESP32-S3 N16R8; (5) mạch giả ESP + kiểu kết nối `esp` ở backend (hỏi trước); (6) mã ESP. Chưa có dòng mã ESP nào. Gói việc: [phiếu P01](../scripts/P01-esp32-s3-cau-noi.md) mục 4.

---

# 14. MiniPC và máy nhỏ (Pi): tạm bỏ ⏸

**Chủ dự án chốt 26–27/11/2026: bỏ MiniPC cho đến khi có quyết định mới.** Máy chính là PC đang code ở nhà (Intel i5-9400F, 6 luồng, 15,9 GB, tên máy DESKTOP-JMHBARS; cũng là máy sẽ treo làm máy chủ); hướng IoT chọn ESP32-S3 (mục 13). Nội dung cũ (so sánh Docker và systemd, `Dockerfile`, `docker-compose.yml`, tên cổng USB cố định bằng `udev`, IP cố định, Cloudflare Tunnel trên Linux) **không còn trong tệp này**; xem trong lịch sử Git: `git show 062ff85:docs/08_TRIEN_KHAI.md` (mục E, F).

Điều đã cân nhắc khi quyết (27/11), để khỏi bàn lại:
| | Máy nhỏ cạnh máy vẽ (Pi / MiniPC) | ESP32-S3 cầu nối (đã chọn) |
|---|---|---|
| Phần mềm | Chạy nguyên backend, USB tại chỗ. Pi (ARM) chưa từng thử: gói `opencv`, `pymupdf` phải kiểm; backend chưa từng chạy Linux | Phải viết mã ESP và kiểu kết nối mới, chia việc với backend |
| Giá | Pi đủ RAM cộng phụ kiện có thể đắt ngang MiniPC cũ | Rẻ |
| Camera | Webcam USB cắm thẳng | ESP32-CAM chỉ để xem (chưa chốt) |
| Lý do chọn | Không chọn: chủ dự án chỉ cần **một con gửi lệnh** | Chọn |

Nếu sau này mua máy nhỏ: chọn ARM 64-bit, RAM theo số đo `do_thoi_gian.py`, Ubuntu 24.04 (có sẵn Python 3.12, đúng bản dự án dùng), nguồn tốt; tránh Android box. Đây là tiêu chí chung, chưa kiểm cho mẫu nào.

# 15. Còn phải thử

| Việc | Cách |
|---|---|
| Máy sạch không cài gì (Visual C++ của OpenCV); nhánh `pip install` của `Cap nhat.bat` | thử trên máy bạn bè |
| Điện thoại thật vào giao diện khách | đặt PIN, vào bằng điện thoại |
| Origin / Host / cookie qua Cloudflare khi **ghi** (đăng nhập PIN, thao tác) | cấu hình thật |
| Nối mạch qua Wi-Fi bằng phần mềm; đo tốc độ và mất sóng | mục 11.6 |
| Đo độ trễ qua Cloudflare lúc khác trong ngày và qua 4G | lặp lại cách ở mục 4 |
| WebUI: bản trên mạch có phải `a690c889`; WebSocket cổng nào | xem trên mạch (mục 12) |
| ESP32-S3: chân trống, nguồn, baud UART; thử "kho lệnh" trên máy giả có trễ | mục 13 |
| Thời gian xử lý ảnh, RAM trên máy chủ mới (cloud / Linux) | `tools/do_thoi_gian.py` ([11](11_THU_NGHIEM.md) mục 9) |
| Chưa đặt PIN thì mở ra ngoài sao | **không bắt buộc** (chủ dự án chọn 24/11/2026, launcher không chặn): chưa đặt thì **ai có địa chỉ cũng là quản lý** và mở khóa được máy. Nên đặt trước khi đưa địa chỉ cho người khác (mục 9.6) |
