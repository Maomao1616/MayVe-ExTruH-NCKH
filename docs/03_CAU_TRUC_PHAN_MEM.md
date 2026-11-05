# 03 — Cấu trúc phần mềm: thư mục, frontend, backend, cách tìm và sửa mã

> Dành cho người đọc không học lập trình. Tài liệu này **không dạy viết code**. Nó giải thích mỗi chức năng nằm ở đâu,
> muốn sửa / thêm / bỏ thì động vào chỗ nào, để tự lần ra đúng tệp khi cần nhờ người khác (hoặc AI) sửa.
> Chi tiết từng tab: [04_TAB_DIEU_KHIEN.md](04_TAB_DIEU_KHIEN.md), [05_TAB_TAO_BAN_VE.md](05_TAB_TAO_BAN_VE.md).

**Mục lục**
1. Ba tầng nói chuyện với nhau
2. Cây thư mục
3. Frontend (giao diện)
4. Backend (máy chủ)
5. Dữ liệu trên đĩa và biến môi trường
6. Tìm, sửa, thêm, bỏ một chức năng
7. Tab Cài đặt
8. Giao diện: CSS và hiệu ứng
9. Kiểm tra sau khi sửa
10. Học thêm ở đâu

---

## 1. Ba tầng nói chuyện với nhau

Hình dung một nhà hàng:

| Nhà hàng | Phần mềm | Nằm ở |
|---|---|---|
| Thực đơn, bàn ghế khách thấy | **Giao diện** (frontend): nút, ô, màu, chữ | `frontend/` (chạy trong trình duyệt) |
| Bồi bàn ghi món, mang món ra | **API**: các "đường gọi" như `/api/draw/import`, `/api/jobs` | `frontend/js/core/api.js` ↔ `backend/app/api/` |
| Nhà bếp | **Máy chủ Python** (backend): xử lý ảnh, sinh G-code, điều khiển máy | `backend/app/services/` |
| Lò nướng | **Máy vẽ** (mạch MKS + FluidNC) qua USB | `backend/app/links/` |

Giao diện chia ba thứ, mỗi thứ một ngôn ngữ:
| Ngôn ngữ | Vai trò | Ở đâu |
|---|---|---|
| HTML | **bộ xương**: có những nút, ô, khối nào | `frontend/index.html` (cả trang một tệp) |
| CSS | **quần áo**: màu, cỡ, vị trí, hiệu ứng | `frontend/css/`, màu ở `frontend/assets/css/tokens.css` |
| JavaScript | **cơ bắp**: bấm nút thì làm gì | `frontend/js/` |

Chữ hiển thị (tiếng Việt / tiếng Anh) **không** viết thẳng trong HTML / JS mà nằm ở `frontend/locales/vi.json` và `en.json`.

---

## 2. Cây thư mục

```
ExtruXY/
├─ README.md                 cài đặt, chạy, kiểm tra
├─ docs/                     tài liệu (01 … 11 cho người đọc; AI_* cho AI)
├─ frontend/                 GIAO DIỆN (không cần bước build, mở là chạy)
│  ├─ index.html             toàn bộ nút, ô, khối của 3 tab
│  ├─ css/                   style.css (nền) → drawing.css (tab vẽ) → polish.css (lớp chỉnh sau cùng, thắng các lớp trước)
│  ├─ assets/css/tokens.css  bảng màu, cỡ chữ, bo góc dùng chung; hai bản sáng / tối
│  ├─ locales/               vi.json, en.json: mọi chữ hiển thị (hai tệp phải cùng khóa)
│  ├─ js/                    xem mục 3
│  └─ tests/                 test JavaScript (node --test)
├─ backend/                  MÁY CHỦ PYTHON
│  ├─ app/                   xem mục 4
│  ├─ tests/                 test tự động (pytest); draw_test/ cho tab vẽ
│  └─ requirements.txt       danh sách thư viện
├─ tools/                    export_context.py (xuất mã cho AI + bản đồ mã) · dong_goi.ps1 (đóng gói zip)
│                            make_test_gcode.py (G-code bài thử tốc độ) · ink_sim.py (mô phỏng mực)
├─ launcher/                 bật / tắt phần mềm bằng icon (Windows)
├─ Cap nhat.bat              cập nhật bản mang đi
├─ Python/                   (không lên Git) Python 3.12 mang theo cho máy không cài Python
└─ data/                     (không lên Git, tự tạo) bản thảo, macro, sao lưu, hồ sơ, PIN
```

---

## 3. Frontend (giao diện)

### 3.1 Bốn tầng, phụ thuộc một chiều
```
views/   (mỗi tab / khối một tệp, là chủ duy nhất ghi lên phần tử HTML của khối đó)
  ↓ dùng
stores/  (dữ liệu dùng chung giữa các view: tệp G-code đang nạp, bản thảo, macro)
  ↓ dùng
lib/     (công thức thuần: không đụng giao diện, không gọi mạng → test được)
  mọi tầng ↓ dùng
core/    (nền móng: gọi máy chủ, hỏi trạng thái, dịch chữ, hằng số máy)
```
Quy tắc: view **không** dùng view khác (trừ `control.js` dùng `preview.js` là khối con). Muốn chia sẻ thì qua `stores/`, `core/` hoặc sự kiện `extruxy:*`. **Một phần tử HTML chỉ một tệp được ghi**, tránh hai nơi tranh nhau.

### 3.2 Từng tệp
| Tầng | Tệp | Vai trò |
|---|---|---|
| vào cửa | `app.js` | chọn tab, ngôn ngữ, sáng / tối, gọi `init…` của từng view |
| core | `api.js` | **nơi duy nhất** gọi máy chủ (`fetch`) |
| | `state.js` | **nơi duy nhất** hỏi trạng thái: `/api/status` mỗi 100 ms, `/api/log` (terminal) 300 ms–1 s |
| | `config.js` | hằng số máy (`MACHINE`: vùng 285 × 318, Z bút), tùy chọn (`PREFS`), nhịp hỏi (`POLL`), chiều khung 2D (`VIEW`) |
| | `i18n.js` · `auth.js` | dịch chữ · vai trò khách / quản lý của trình duyệt |
| lib | `gcode.js` | đọc G-code thành đoạn để xem trước, cảnh báo dòng bị cấm, bám tiến trình |
| | `paper.js` | bố trí trên tờ giấy (bản JS của `layout.py`, có test đối chiếu) |
| | `imageprep.js` | thu nhỏ ảnh trước khi gửi + công thức độ sáng (khớp `raster_in.py` / `tone.py`) |
| | `drafts.js` | định dạng số liệu bản thảo |
| stores | `jobstore.js` · `draftstore.js` · `macros.js` | tệp G-code đang nạp · danh sách bản thảo · macro |
| views | `control.js`, `preview.js`, `terminal.js`, `header.js`, `dock.js` | tab Điều khiển và các khối chung |
| | `drawing.js` + `drawing/` (`params`, `canvas`, `crop`, `presets`, `tonepreview`) | tab Tạo bản vẽ |
| | `drafts.js` | danh sách bản thảo (tab vẽ) + Hàng đợi (tab Điều khiển) |
| | `settings.js`, `storage.js` | tab Cài đặt |
| | `auth.js` | khung đăng nhập ở đầu trang |

---

## 4. Backend (máy chủ)

### 4.1 Ba lớp
```
api/       HTTP mỏng: nhận yêu cầu, kiểm kiểu dữ liệu (pydantic), gọi services, trả JSON
  ↓
services/  logic thật: điều khiển máy, chạy G-code, cấu hình, hồ sơ, tab vẽ (drawing/)
  ↓
links/     nói chuyện với máy: serial thật (pyserial) hoặc máy giả
```

### 4.2 Từng tệp
| Tệp | Vai trò |
|---|---|
| `main.py` | khởi động FastAPI; chỉ nhận Host được phép, chặn POST từ trang khác, giới hạn cỡ yêu cầu, kiểm vai trò; phục vụ `frontend/` |
| `auth.py` · `api/auth.py` | phân quyền: phiên quản lý bằng PIN (cookie ngẫu nhiên trong RAM, 12 giờ, sai 5 lần khóa 60 s), danh sách route cho khách `GUEST_ROUTES` |
| `paths.py` | **một chỗ** quy định thư mục dữ liệu và 3 thư mục con |
| `idle.py` | tự tắt server khi đóng hết trang 10 phút (chỉ bản mang đi) |
| `api/machine.py` | `connect, status, command, realtime, log, jobs, jobs/cancel, jobs/resume, motion…` |
| `api/config.py` | cấu hình trên mạch, hồ sơ phần mềm |
| `api/draw.py` | `/api/draw/*` của tab vẽ (không gọi máy) |
| `api/storage.py` | macro, xem / tải thư mục dữ liệu |
| `services/machine.py` | **bộ não**: kết nối, trạng thái, nhật ký, đoán Home, khóa chuyển động, dừng an toàn |
| `services/job.py` | làm sạch G-code, gửi từng dòng chờ `ok` |
| `services/resume.py` | điểm dừng, tiếp tục từ dòng an toàn |
| `services/machine_config.py` | đọc / sửa / lưu YAML trên mạch (thư viện PyYAML), sao lưu |
| `services/profile.py` | hồ sơ phần mềm (`data/profile.json`): Z bút, tốc độ bút, bước jog tối đa |
| `services/macros.py` · `services/storage.py` | macro trên đĩa · xem thư mục dữ liệu (chỉ đọc) |
| `services/drawing/` | dây chuyền tab vẽ ([05_TAB_TAO_BAN_VE.md](05_TAB_TAO_BAN_VE.md) mục 9) |
| `links/protocol.py` | đọc từng dòng máy gửi (trạng thái, `ok`, `error`, `ALARM`, `MSG`); lệnh nào là chỉ đọc; tên mã lỗi |
| `links/serial_link.py` · `sim_link.py` · `base.py` | cổng COM thật · máy giả · khuôn chung |

### 4.3 Luồng dữ liệu chính
- **Điều khiển:** nút → `api.js` → `/api/command | realtime | jobs` → `MachineService` (kiểm chung một cửa) → `JobRunner` (gửi từng dòng) → `SerialLink` / `SimLink` → mạch. Trạng thái đi ngược lại qua `state.js` ([04_TAB_DIEU_KHIEN.md](04_TAB_DIEU_KHIEN.md) mục 3–4).
- **Tạo bản vẽ:** chọn tệp → trình duyệt thu nhỏ ảnh → `/api/draw/import` → tác vụ nền ở tiến trình con → nét lưu trong RAM → trình duyệt kéo thả khung → `/api/draw/gcode` → `/api/draw/drafts` (lưu đĩa) → tab Điều khiển nạp bản thảo ([05_TAB_TAO_BAN_VE.md](05_TAB_TAO_BAN_VE.md) mục 4).

---

## 5. Dữ liệu trên đĩa và biến môi trường

Gốc dữ liệu = `data/` ở thư mục gốc dự án (tự tạo, không lên Git). Đổi bằng `EXTRUXY_DATA_DIR`. Giao diện không cho đổi đường dẫn (người lạ không trỏ được máy chủ ghi ra chỗ khác).

| Thứ | Ở đâu (trong `data/`) | Ghi chú |
|---|---|---|
| Bản thảo | `drafts/` | mỗi bản một thư mục: `meta.json`, `draw[-<n>-<màu>].gcode`, `preview.svg` |
| Sao lưu cấu hình mạch | `config_backups/` | tạo trước mỗi lần "Lưu vào mạch" |
| Macro | `macros/` | mỗi macro một tệp JSON |
| Hồ sơ phần mềm | `profile.json` | Z bút, tốc độ bút, bước jog |
| Hạn mức bản thảo | `draw_settings.json` | số bản, MB |
| Điểm dừng tác vụ | `resume.json` | xóa khi tác vụ chạy trọn |
| PIN | `pin.txt` | `admin=…`, `unlock=…` (bản mang đi đọc lúc bật) |
| Lỗi khởi động | `server-loi.txt` | chỉ bản mang đi |

Nhật ký hệ thống **không ghi ra tệp** (chỉ nằm trong bộ nhớ, hiện ở terminal).

| Biến môi trường (đều tùy chọn) | Tác dụng |
|---|---|
| `EXTRUXY_ADMIN_PIN` | PIN quản lý. Không đặt = ai vào cũng là quản lý |
| `EXTRUXY_UNLOCK_PIN` | PIN mở khóa chuyển động |
| `EXTRUXY_ALLOW_MOTION=1` | mở khóa chuyển động cố định (máy thật mặc định chỉ đọc) |
| `EXTRUXY_UNLOCK_MINUTES` | tự khóa lại sau chừng này phút (15; 0 = tắt) |
| `EXTRUXY_NO_UNLOCK=1` | cấm mở khóa từ giao diện |
| `EXTRUXY_ALLOWED_HOSTS` | danh sách Host được gọi API (mặc định chỉ cục bộ) |
| `EXTRUXY_DATA_DIR` | thư mục dữ liệu |
| `EXTRUXY_IDLE_EXIT_MIN` | tự tắt server khi không có trang nào mở (launcher đặt 10) |
| `EXTRUXY_DRAW_INPROC=1` | xử lý ảnh ngay trong tiến trình server (test, gỡ lỗi) |
| `EXTRUXY_DRAW_TIMEOUT_S` · `EXTRUXY_DRAW_MAX_MB` | trần thời gian (600 s) · trần RAM, chỉ Linux (4096 MB) của tiến trình xử lý ảnh |

---

## 6. Tìm, sửa, thêm, bỏ một chức năng

### 6.1 Tìm: đi ngược từ chữ trên màn hình
Mỗi bước là một lần **Ctrl+Shift+F** (tìm trong mọi tệp) trong VS Code. Ví dụ ô "Chi tiết viền":

| Bước | Tìm | Ra | Hiểu được |
|---|---|---|---|
| 1 | `Chi tiết viền` | `vi.json`: `"drawing.style.outlineDetail": "Chi tiết viền"` | tên khóa chữ |
| 2 | `drawing.style.outlineDetail` | `index.html`: `<select id="style-outline-detail">` | ô có **id** `style-outline-detail` |
| 3 | `style-outline-detail` | `views/drawing/params.js`: `["style-outline-detail", "style", "outline_detail", "str"]` | ô gửi tham số `outline_detail` |
| 4 | `outline_detail` (trong `backend`) | `spec.py` (khai báo), `styles.py` → `edges.py` (dùng thật) | nơi thuật toán đọc giá trị |

```
Chữ trên màn hình → khóa trong vi.json → id trong index.html → tệp JS dùng id đó
→ hàm trong api.js → đường /api/… → tệp trong backend/app/api/ → hàm trong backend/app/services/
```
Tên nhất quán: id HTML gạch ngang (`style-outline-detail`), tham số Python gạch dưới (`outline_detail`), khóa chữ dấu chấm (`drawing.style.outlineDetail`).

| Phím VS Code | Tác dụng |
|---|---|
| Ctrl+Shift+F | tìm chữ trong cả dự án |
| Ctrl+P | mở nhanh tệp theo tên |
| F12 / Shift+F12 | nhảy tới nơi viết hàm / mọi nơi dùng hàm |
| Ctrl+Shift+O | danh sách hàm trong tệp đang mở |

### 6.2 Sửa: đổi gì ở đâu
| Muốn sửa | Sửa ở |
|---|---|
| Chữ hiển thị | `vi.json` **và** `en.json` (cùng khóa) |
| Màu | `frontend/assets/css/tokens.css` (vd `--highlight` là màu cam nhấn) |
| Cỡ, khoảng cách, bố cục, điện thoại | `frontend/css/polish.css` (khối `@media (max-width: 760px)` cho điện thoại) |
| Một con số của thuật toán | **hằng số viết HOA ở đầu tệp Python**, có chú thích tiếng Việt (vd `LINE_WIDTH_RATIO` trong `styles.py`, `GAP_MM` trong `edges.py`) |
| Giới hạn / mặc định ô thông số vẽ | `backend/app/services/drawing/spec.py` |
| Bộ thông số dựng sẵn | `frontend/js/views/drawing/presets.js` |
| Tốc độ, gia tốc, hành trình trên mạch | giao diện: Cài đặt → Cấu hình máy (không sửa mã) |
| Z bút, tốc độ bút | giao diện: Cài đặt → Cấu hình máy, mục App |
| Thời gian chờ tác vụ, sai số nâng bút | `services/job.py` (`RESPONSE_TIMEOUT_S`, `STATUS_STALE_S`), `services/machine.py` (`PEN_TOL_MM`) |
| Lệnh nào là chỉ đọc | `links/protocol.py` |

### 6.3 Thêm một ô thông số vẽ (5 chỗ)
1. `spec.py`: một dòng `Param("ten", "kiểu", mặc_định, min, max)` vào đúng nhóm.
2. Tệp Python dùng nó (`styles.py`, `edges.py`…): đọc `style.ten`.
3. `index.html`: `<label>` + ô `id="nhom-ten"`.
4. `views/drawing/params.js`: một dòng trong bảng `FIELDS`.
5. `vi.json` + `en.json`: khóa chữ nhãn, lựa chọn, gợi ý.

### 6.4 Thêm một nút
1. `index.html`: `<button id="ten-nut" data-i18n="khoa.chu">` trong khối cần hiện.
2. JS của tab đó: `$("ten-nut")?.addEventListener("click", hamXuLy)` trong hàm `init…`.
3. Cần máy chủ làm gì: thêm hàm vào `core/api.js`, route vào `backend/app/api/…py`, logic vào `backend/app/services/…`. Route mới **mặc định chỉ quản lý** gọi được.
4. Khóa chữ ở hai tệp ngôn ngữ.

### 6.5 Bỏ một chức năng: tìm hết các "sợi dây"
1. Bắt đầu từ **id** trong `index.html` → tìm id → ra đoạn JS gắn sự kiện.
2. Ghi lại **mọi tên** đoạn đó dùng: hàm xử lý, hàm trong `api.js`, khóa chữ.
3. Tìm từng tên. Tên chỉ còn dùng cho chức năng này thì bỏ; còn nơi khác dùng thì giữ.
4. Bỏ theo chiều: HTML → JS → `api.js` → khóa chữ (hai tệp) → tài liệu. Phần máy chủ có thể giữ.
5. Chạy kiểm tra (mục 9).

Ví dụ thật: bỏ nút "Tạo tờ mẫu hiệu chỉnh bút" = bỏ nút trong `index.html` + hàm `createCalibration` trong `drawing.js` + `drawCalibration` trong `api.js` + 3 khóa `drawing.calibration.*`; **giữ** route `POST /api/draw/calibration` để in lại khi cần.

---

## 7. Tab Cài đặt

| Khối | Việc |
|---|---|
| Kết nối | chọn chế độ (máy thật `serial` / máy giả `sim`), cổng COM (nhớ cổng lần trước), Kết nối / Ngắt |
| Giao diện chung · Hoạt động | ngôn ngữ, sáng / tối; nhịp cập nhật terminal, hỏi lại trước Home, phím tắt jog |
| Bản thảo | số bản tối đa, dung lượng tối đa (thư mục cố định). Vượt thì xóa bản cũ nhất không ghim |
| Lưu trữ dữ liệu | xem (không sửa) và tải về nội dung bản thảo, sao lưu cấu hình, macro, tệp lẻ |
| **Cấu hình máy** | mục **Máy**: đọc YAML đang chạy trên mạch (`$CD`), sửa các mục được phép (tốc độ, gia tốc, hành trình, Home, servo; danh sách `FIELDS` trong `machine_config.py`), **Áp dụng** (`$/axes/...`, chỉ trong RAM, hàng đổi có dấu ●), **Lưu vào mạch** (sao lưu bản gốc về máy tính rồi `$CD=/localfs/<tệp>`), nạp bản sao lưu. Không cho sửa chân GPIO, kinematics, stepping. Mục **App**: Z bút 3 nấc, tốc độ bút, bước jog tối đa (lưu `data/profile.json`) |

---

## 8. Giao diện: CSS và hiệu ứng

| Hiệu ứng trong dự án | Kỹ thuật | Từ khóa tra |
|---|---|---|
| Khối mở / thu gọn trượt mềm | `<details>` + `::details-content` + `transition` + `interpolate-size` | *CSS details animation* |
| Nút sáng khi rê chuột | `:hover` + `transition` | *CSS transition* |
| Kéo bản thảo đổi thứ tự, dòng khác trượt nhường chỗ | `transform: translateY` + Pointer Events + `requestAnimationFrame` | *FLIP animation*, *pointer events drag* |
| Điện thoại khác bố cục máy tính | `@media (max-width: …)` | *responsive media query* |
| Đổi thứ tự khối trên điện thoại không sửa HTML | `display: contents` + `order` | *CSS order* |
| Xếp hàng / cột | `display: flex`, `display: grid` | *CSS flexbox*, *CSS grid* |
| Một chỗ đổi màu cả trang, sáng / tối | biến CSS `--ten-bien` trong `tokens.css`, `color-mix()` | *CSS custom properties* |
| Tắt hiệu ứng cho người không thích chuyển động | `@media (prefers-reduced-motion: reduce)` | *prefers-reduced-motion* |
| Ẩn phần quản lý với khách | lớp `body.role-guest` + CSS (chỉ ẩn, bảo mật nằm ở máy chủ) | |

Lớp `polish.css` nạp sau cùng; xóa dòng `<link>` của nó là quay về giao diện gốc.

---

## 9. Kiểm tra sau khi sửa

| Kiểm | Cách | Báo gì |
|---|---|---|
| Test máy chủ (~397 bài) | trong `backend`, đã bật venv: `python -m pytest` | số bài đạt / hỏng; hỏng = có chỗ khác bị ảnh hưởng |
| Test giao diện (33 bài) | ở thư mục gốc: `node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs frontend/tests/gcode.test.mjs` | như trên |
| Xem giao diện | sửa Python thì tắt và chạy lại server; trình duyệt **Ctrl+F5**; **F12 → Console** xem dòng đỏ | lỗi chữ, nút không chạy |
| Thử bằng máy giả | Cài đặt → Kết nối → `sim` | mọi nút chạy được khi chưa có máy |
| Lưới an toàn | Git: `git diff` xem đã đổi gì; `git checkout -- <tệp>` quay về bản đã commit | |

Công thức có bản JS song song (`layout.py` ↔ `paper.js`, `tone.py` / `raster_in.py` ↔ `imageprep.js`): đổi bên nào thì sinh lại số chuẩn (`python frontend/tests/fixtures/make_image_fixtures.py`) và chạy test cả hai bên.

---

## 10. Học thêm ở đâu

| Nguồn | Có gì |
|---|---|
| MDN Web Docs (`developer.mozilla.org`) | nghĩa chính xác của mọi thẻ HTML, thuộc tính CSS, hàm JS |
| web.dev, CSS-Tricks ("Complete Guide to Flexbox / Grid") | hướng dẫn bố cục, hiệu ứng |
| caniuse.com | trình duyệt nào hỗ trợ tính năng nào |
| F12 trong Chrome / Edge | bấm vào phần tử, xem nó ăn CSS nào, sửa thử trực tiếp |
| OpenCV-Python Tutorials (`docs.opencv.org`) | từng phép xử lý ảnh có ảnh trước / sau |
| scikit-image Gallery | skeletonize, bộ lọc, phân vùng |
| vpype docs (`vpype.readthedocs.io`) | lệnh tối ưu nét cho máy vẽ |
| awesome-plotters (GitHub `beardicus/awesome-plotters`) | công cụ, thuật toán của cộng đồng máy vẽ |
| FluidNC wiki (`wiki.fluidnc.com`) | lệnh và cấu hình firmware |

Mẹo tìm: gõ **tiếng Anh, cụ thể một bước, kèm tên thư viện** ("opencv skeleton thick line centerline python" tốt hơn nhiều "chuyển ảnh thành nét vẽ").
