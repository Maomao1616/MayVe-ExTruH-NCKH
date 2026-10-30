# ExtruXY – Bản đồ dự án và lộ trình (29/10/2026)

Đọc một lần để biết: file nào làm gì, dữ liệu đi đường nào, ai được ghi vào đâu, đổi gì thì sửa ở đâu.
Ký hiệu: ✅ người dùng đã áp dụng và thử trên máy giả (SimLink) · 📦 Claude đã đưa bản vá, **chưa xác nhận đã áp dụng** (kiểm bằng `grep` trong mã thật) · ⏳ chưa làm · ⚠ giả định chưa kiểm chứng trên máy thật. **Nếu mã nguồn mới lệch với bảng dưới, mã mới là sự thật.**

## 1. Sơ đồ và cây thư mục
```
Máy vẽ (FluidNC, MKS DLC32) ⇄ cáp USB (COM)   hoặc   SimLink (máy giả)
        ⇅
Backend Python (FastAPI):  api/ (HTTP mỏng) → services/ (logic) → links/ (nói chuyện với máy)
        ⇅  HTTP /api/...
Trình duyệt:  core/api.js → core/state.js (hỏi backend mỗi 0,5 giây) → views/* hiển thị
```
```
ExtruXY/
├─ README.md                 Cài đặt, chạy, API
├─ Bat Khien EXTRUH.bat      Bấm đúp: bật venv trong backend/, mở trình duyệt, chạy server
├─ docs/                     DECISIONS · MACHINE (sự thật máy thật) · PROJECT_MAP · HANDOVER · DRAW_ROADMAP
├─ samples/                  Tệp G-code mẫu để thử
├─ backend/
│  ├─ app/
│  │  ├─ main.py             Khởi động, chặn Host/Origin lạ, phục vụ frontend
│  │  ├─ api/                Router HTTP (mỏng). Thêm router: 1 file + 1 dòng trong api/__init__.py
│  │  ├─ services/           Logic: máy, tác vụ, cấu hình mạch, hồ sơ, tab vẽ (drawing/)
│  │  └─ links/              Kết nối máy: serial thật, SimLink, giao thức FluidNC
│  ├─ data/                  (tự tạo, không lên Git) hồ sơ phần mềm + bản sao lưu YAML
│  ├─ tests/                 pytest (draw_test/ của tab vẽ)
│  └─ tools/                 Script thử nghiệm (probe_vpype.py)
└─ frontend/
   ├─ index.html · css/style.css · assets/css/tokens.css (màu + kích thước) · locales/
   └─ js/
      ├─ app.js              Vào cửa: tab, ngôn ngữ, sáng/tối, gọi init của từng view
      ├─ core/               Nền tảng: api · state · i18n · config
      ├─ lib/                Hàm thuần, không DOM, không mạng: gcode
      ├─ stores/             Dữ liệu dùng chung giữa các view: jobstore · macros · draftstore
      └─ views/              Mỗi khối giao diện một file, là chủ ghi DOM của khối đó
```
Giao diện chỉ hiển thị; backend là nguồn sự thật. **Không có thẻ SD/flash** (đã bỏ, D9): G-code luôn được gửi từng dòng từ máy tính. Giai đoạn sau, backend chạy trên **mini PC i5 thế hệ 3**.

**Chiều phụ thuộc (chỉ đi một chiều):** `views → stores → lib`, và mọi tầng → `core`. View **không import view khác** (trừ `control.js` gọi `preview.js` là khối con của nó). Muốn dùng chung thì qua `core/config.js` (`MACHINE`, `PREFS`), `core/state.js`, `stores/`, hoặc sự kiện `extruxy:*`.

## 2. Backend (`backend/app/`)
| File | Vai trò |
|---|---|
| `main.py` | Khởi động; chỉ nhận Host cục bộ, chặn POST từ trang khác, giới hạn kích thước request; phục vụ `frontend/` |
| `api/machine.py` | `health, ports, connection, connect, disconnect, status, command, realtime, log, jobs, jobs/cancel` (`reset`/`soft`/`hard`), `motion` |
| `api/config.py` | `GET/POST /api/machine/config`, `POST /api/machine/config/save`, `GET/PUT /api/profile` |
| `api/draw.py` | `/api/draw/*` của tab Tạo bản vẽ (không gọi máy) |
| `services/machine.py` | **Bộ não:** kết nối, trạng thái, nhật ký, đoán Home (`[MSG:Homed:XY]`), khóa/mở khóa chuyển động, dừng an toàn (soft/hard, xác nhận nâng bút), `query()` gom phản hồi nhiều dòng |
| `services/job.py` | Chạy G-code: làm sạch dòng, gửi từng dòng chờ `ok`, lỗi/alarm/timeout kèm Feed Hold, hủy |
| `services/machine_config.py` | Đọc/sửa/lưu YAML trên mạch (`$CD`, `$/axes/...`, `$CD=/localfs/...`), sao lưu bản gốc về `data/config_backups/` |
| `services/profile.py` | Hồ sơ phần mềm (`data/profile.json`): Z bút 3 nấc, tốc độ bút, bước jog tối đa |
| `services/drawing/` | Tab Tạo bản vẽ: SVG → nét → bố trí → G-code (xem `DRAW_ROADMAP.md`) |
| `links/protocol.py` | Đọc từng dòng máy gửi (trạng thái, `ok`, `error`, `ALARM`); lệnh chỉ đọc theo `$CMD` thật; tên mã theo `$E`/`$A` |
| `links/serial_link.py`, `sim_link.py`, `base.py` | Cổng COM thật / máy giả (hiệu chỉnh theo log board thật) / khuôn chung |

## 3. Frontend (`frontend/`)
| File | Vai trò |
|---|---|
| `index.html`, `css/style.css`, `assets/css/tokens.css` | Khung tab và giao diện. Màu, khoảng cách, kích thước nút: chỉ sửa `tokens.css` |
| `locales/vi.json`, `en.json` | Mọi chữ hiển thị (hai file phải khớp khóa) |
| `js/app.js` | Vào cửa: tab, ngôn ngữ, sáng/tối, gọi `init*` của các view |
| `js/core/api.js` | Nơi **duy nhất** gọi backend |
| `js/core/state.js` | Nơi **duy nhất** thăm dò; `isConnected()`, `isStale()`, `firmwareLabel()`, `refreshNow()` |
| `js/core/config.js` | Giá trị dùng chung: `MACHINE` (máy, bút; Cài đặt ghi đè), `PREFS` (Hoạt động), `POLL`, `VIEW` |
| `js/core/i18n.js` | Dịch chữ |
| `js/lib/gcode.js` | Đọc G-code (thuần tính toán; có `cleanLine`) |
| `js/stores/jobstore.js` | Tệp G-code đang nạp (Điều khiển ghi, khung 2D đọc; tab vẽ giao tệp qua `setFile`) |
| `js/stores/macros.js` | Macro: kiểm tra hợp lệ + kho `localStorage` |
| `js/stores/draftstore.js` | Danh sách bản thảo (`/api/draw/drafts`) dùng chung cho tab Tạo bản vẽ và Hàng đợi; ghim, đẩy ưu tiên, xóa, nạp vào Điều khiển |
| `js/lib/paper.js` | Bố trí tờ giấy / khung vẽ / xoay (bản JS của `layout.py`, test đối chiếu backend: `node --test frontend/tests/paper.test.mjs`) |
| `js/lib/drafts.js` | Định dạng số liệu bản thảo |
| `js/views/header.js` | Đầu trang + ô trạng thái trên thanh tab + thanh cảnh báo + nút ↻ |
| `js/views/terminal.js` | Terminal và nút Tạm dừng / Tiếp tục / Hủy jog / Reset / Mở khóa |
| `js/views/control.js` | Tab Điều khiển: trạng thái, mở khóa chuyển động, jog, **thanh bút 3 nấc**, Zero, Home (hỏi lại), tệp G-code (cảnh báo gốc vị trí khi chưa Home), **ghi đè tốc độ**, tiến trình, hủy tác vụ. Hàng đợi công việc do `drafts.js` lo |
| `js/views/preview.js` | Khung 2D (khối con của Điều khiển). Đang chạy đúng tệp đã nạp: vết vẽ theo đường của tệp (`trackProgress`), cung tròn không bị gãy theo nhịp hỏi vị trí |
| `js/views/settings.js` | Tab Cài đặt: kết nối (nhớ cổng lần trước) · Hoạt động · **Cấu hình máy** (YAML trên mạch + hồ sơ phần mềm + nạp bản sao lưu) |
| `js/views/dock.js` | Dock bên trái: macro |
| `js/views/drawing.js` | Tab Tạo bản vẽ: nạp tệp → tác vụ nền (tiến trình, hủy) → nét nháp → bố trí → G-code → bản thảo / sang Điều khiển. Phần con: `views/drawing/params.js` (các ô ⇄ dữ liệu gửi backend), `views/drawing/canvas.js` (canvas giấy A6/A5/A4, kéo – co giãn – hít lề) |
| `js/views/drafts.js` | Danh sách bản thảo (tab vẽ) + Hàng đợi công việc (tab Điều khiển) + hộp xem ảnh nháp |

**Quy ước:** mỗi tab một file view với một hàm vào cửa; mỗi khối là một hàm riêng bên trong. **Một phần tử HTML chỉ một chủ ghi** (kiểm: `grep -rn "<id>" frontend/js`). Báo ra terminal bằng sự kiện `extruxy:message` (terminal giữ tiếng Anh).

## 4. Đổi X thì sửa ở đâu
| Muốn đổi | Sửa ở |
|---|---|
| Tốc độ, gia tốc, hành trình, Home, servo (trên mạch) | Giao diện: Cài đặt → Cấu hình máy → Áp dụng / Lưu vào mạch. Mục được phép sửa: `FIELDS` trong `services/machine_config.py` |
| Z bút 3 nấc, tốc độ bút, bước jog tối đa | Giao diện: Cài đặt → Cấu hình máy (mục App). Mặc định: `services/profile.py` và `MACHINE` trong `core/config.js` |
| Khung 2D ngược chiều | `core/config.js` (`VIEW.flipX/flipY`) |
| Nhịp thăm dò, ngưỡng "dữ liệu cũ" | Giao diện: Cài đặt → Hoạt động; mặc định `core/config.js` (`PREFS`, `POLL`) |
| Một dòng chữ | `vi.json` và `en.json` (cùng khóa) |
| Dòng trạng thái trong terminal | `views/terminal.js` (`STATUS_ECHO`, `SHOW_TIME`) |
| Màu, khoảng cách, cỡ nút | `assets/css/tokens.css` |
| Mở/khóa chuyển động | Nút giao diện; biến môi trường: `EXTRUXY_ALLOW_MOTION=1` (mở cố định), `EXTRUXY_UNLOCK_MINUTES` (mặc định 15; 0 tắt tự khóa), `EXTRUXY_UNLOCK_PIN`, `EXTRUXY_NO_UNLOCK=1` |
| Host được phép gọi API (chạy qua LAN) | biến môi trường `EXTRUXY_ALLOWED_HOSTS`; xem `main.py` |
| Thời gian chờ tác vụ / mất báo cáo trạng thái | `services/job.py` (`RESPONSE_TIMEOUT_S`, `STATUS_STALE_S`, `FINISH_IDLE_REPORTS`) |
| Sai số / thời gian chờ xác nhận nâng bút | `services/machine.py` (`PEN_TOL_MM`, `PEN_LIFT_MAX_S`) |
| Trình tự Dừng êm / Dừng gấp | `services/machine.py` (`_stop_sequence`) |
| Lệnh nào là "chỉ đọc" | `links/protocol.py` |
| Hành vi máy giả | `links/sim_link.py` |
| Kiểm tra/lưu macro | `stores/macros.js` |

## 5. Chạy và thử (PowerShell, trong `backend`, đã bật venv)
* Chạy: `uvicorn app.main:app --reload` (đang sửa code) hoặc bấm đúp `Bat Khien EXTRUH.bat` ở thư mục gốc (bật venv, mở trình duyệt, không `--reload`) → `http://127.0.0.1:8000/`.
* Test backend: `python -m pytest`.
* Sửa Python xong phải tắt (Ctrl+C) và chạy lại server. Chữ không đổi: Ctrl+Shift+R hoặc F12 → Network → Disable cache. Lỗi lạ: F12 → Console, dán dòng đỏ.
* Thói quen: áp từng bước nhỏ → test → thử bằng sim → commit Git.

## 6. Lộ trình và tình trạng
| # | Giai đoạn | Tình trạng |
|---|---|---|
| 1 | Nền tảng: backend, SimLink, kết nối, terminal, an toàn | ✅ |
| 2 | Tab Điều khiển: trạng thái, jog, bút, Zero, Home | ✅ |
| 3 | G-code và khung 2D: nạp, xem trước/phát lại, chạy từng dòng, tiến trình, hủy | ✅ |
| 4 | Sửa 4 lỗi backend + nút mở khóa chuyển động (hướng C) | ✅ |
| 5 | Dock + macro + chỉ báo đầu trang (`macros.js`, `dock.js`, `header.js`) | 📦 (chờ áp dụng, rồi dọn khối thừa) |
| 6 | Timeout Feed Hold, poller, Reset xóa lỗi cũ, test hồi quy | 📦 |
| 7 | Hủy tác vụ an toàn (Dừng êm / Dừng gấp): backend + hộp thoại | 📦 (backend mới chỉ ở bản sao của Claude) |
| 8 | **Hồ sơ máy trong Cài đặt** (F7) | ⏳ kế tiếp |
| 9 | **Làm đẹp giao diện:** nút ↻, thanh cảnh báo, trạng thái chờ/rỗng/lỗi, màn hình hẹp | ⏳ kế tiếp |
| 10 | Hàng chờ công việc: thiết kế backend (F6) | ⏳ |
| 11 | Việc backend ghi nhận: log rotation 3 ngày, dòng `sys` tiếng Anh, `homed_axes` | ⏳ |
| 12 | **Thử máy thật** (Phần B `handover-prompt.md`), chỉnh Z/hướng trục/`VIEW` | Khi có motor/servo |
| 13 | Hoàn thiện SimLink theo dữ liệu thật | Sau 12 |
| 14 | **Tab Tạo bản vẽ** (AI khác, song song): theo `DRAW_ROADMAP.md` | ⏳ chạy song song |
| 15 | Mini PC: xác thực + PIN thật, WiFi/USB, gửi trước nhiều dòng (D10), Tiếp tục từ dòng N, thư viện G-code (D11), PWA | Chỉ khi cần |
| — | ~~Thẻ SD/Flash, tab Công việc~~ | **Đã bỏ** (D9, F8) |

## 7. Quy tắc làm song song tab Tạo bản vẽ (AI khác)
| Quy tắc | Nội dung |
|---|---|
| **Chỉ được sửa** | `js/views/drawing.js`, file mới trong `backend/app/services/drawing/` và `api/draw.py`, khóa `draw.*` ở **cuối** hai file ngôn ngữ, phần HTML của panel Tạo bản vẽ, test mới |
| **Không được sửa** | `services/machine.py`, `job.py`, `links/protocol.py`, `core/state.js`, `views/control.js`, `terminal.js`, `dock.js`, `header.js`, `settings.js`. `core/api.js` chỉ được **thêm** hàm `draw*` ở cuối. Cần đổi chỗ khác thì hỏi chủ dự án |
| **Backend** | Router riêng `api/draw.py` (đã gắn trong `api/__init__.py`). Đầu vào ảnh, đầu ra G-code dạng văn bản + thống kê. **Không gọi máy trực tiếp** |
| **Giao nhận G-code** | Đưa vào `stores/jobstore.js` → `setFile(...)` để tab Điều khiển xem trước, tích xác nhận, chạy. Không tự chạy |
| **Định dạng G-code** | Theo `lib/gcode.js`/`services/job.py`: bắt đầu `G90 G21`; có `F` (tránh cảnh báo thiếu tốc độ); dòng ≤ 200 ký tự; không `$`, không `G92/G10/G28/G53`; bút lên/xuống theo `MACHINE.penUpZ/penDownZ` trong `core/config.js` (hồ sơ máy); mỗi nét kết thúc bút lên. **Tránh quá nhiều đoạn rất ngắn** (xem D10: gửi từng dòng chờ `ok` có thể làm máy giật) — gộp/đơn giản hóa nét |
| **Vùng vẽ** | Lấy từ `MACHINE` trong `core/config.js` (285 × 318 mm, cập nhật theo YAML khi đọc cấu hình), không tự đặt số riêng |
| **Git** | Nhánh riêng `draw`, commit nhỏ, kéo từ nhánh chính mỗi ngày. Hai file ngôn ngữ là chỗ dễ xung đột nhất → chỉ thêm khóa ở cuối |
| **Quy ước chung** | A1–A8 và F4: không framework, không build, giải thích bằng lời thường, mỗi phần mới có test, ghi rõ chưa kiểm chứng gì |
| **Hạ tầng** | Xử lý ảnh chạy trên máy cá nhân/mini PC (cần Python 3.12 + vpype, Pillow, numpy, opencv); không dùng Raspberry Pi/hosting chia sẻ |
