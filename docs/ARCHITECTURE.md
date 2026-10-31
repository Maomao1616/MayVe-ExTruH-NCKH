# ARCHITECTURE — kiến trúc và bản đồ dự án

Đọc để biết: khối nào làm gì, dữ liệu đi đường nào, quy tắc phụ thuộc, đổi gì thì sửa ở đâu. Tình trạng và việc còn lại:
`STATUS.md`. Danh sách tệp kèm token và route API: `CODEMAP.md` (sinh tự động). **Nếu mã lệch với tài liệu, mã mới là sự thật.**

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
├─ README.md                 Giới thiệu, cài đặt, chạy, kiểm tra
├─ Cap nhat.bat             Bản mang đi: thay backend/ frontend/ launcher/ từ file zip, giữ Python/ và data/
├─ launcher/                start.vbs/.ps1 (server chạy ẩn + mở trình duyệt) · stop · tao_bieu_tuong.vbs · cap_nhat.ps1 · icon.ico
├─ Python/                  (không lên Git) Python 3.12 embeddable + thư viện; _pth có ..\backend
├─ data/                    (tự tạo, không lên Git) drafts/ · config_backups/ · macros/ + profile.json, draw_settings.json, resume.json
├─ docs/                     AI_START · STATUS · ARCHITECTURE · CODEMAP · DECISIONS · MACHINE(+RAW) · DRAW_ROADMAP · BRIEF · PLAN_ONLINE · EXPORT_FOR_AI
├─ tools/                   export_context.py (xuất mã cho AI + CODEMAP) · dong_goi.ps1 (zip bản cập nhật / đầy đủ)
├─ samples/                  Tệp G-code mẫu để thử
├─ backend/
│  ├─ app/
│  │  ├─ main.py             Khởi động, chặn Host/Origin lạ, phục vụ frontend
│  │  ├─ api/                Router HTTP (mỏng). Thêm router: 1 file + 1 dòng trong api/__init__.py
│  │  ├─ services/           Logic: máy, tác vụ, cấu hình mạch, hồ sơ, tab vẽ (drawing/)
│  │  └─ links/              Kết nối máy: serial thật, SimLink, giao thức FluidNC
│  ├─ tests/                 pytest (draw_test/ của tab vẽ)
│  └─ tools/                 Script thử nghiệm (probe_vpype.py)
└─ frontend/
   ├─ index.html · css/{style,drawing,polish}.css · assets/css/tokens.css (màu + kích thước) · locales/ · tests/
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
| `paths.py` | **Một chỗ** quy định thư mục dữ liệu và 3 thư mục con cố định (`EXTRUXY_DATA_DIR`) |
| `services/resume.py` | Điểm dừng của tác vụ: lưu, tính dòng bắt đầu lại an toàn, kiểm WCO (`/api/jobs/resume`) |
| `services/macros.py` · `services/storage.py` · `api/storage.py` | Macro CRUD trên đĩa · xem/tải nội dung thư mục dữ liệu (chỉ đọc) |
| `services/drawing/calibration.py` | Tờ mẫu hiệu chỉnh bút (`POST /api/draw/calibration`) |
| `js/views/storage.js` | Cài đặt → Lưu trữ dữ liệu (chỉ xem + tải) |
| `services/drawing/` | Tab Tạo bản vẽ: SVG hoặc ảnh → nét → bố trí → G-code (xem `DRAW_ROADMAP.md`). Ảnh (chạy ở tiến trình riêng, `isolated.py`): `raster_in` (đọc, cắt, cỡ làm việc) → `tone` (sắc độ) → `styles` + `hatch` (zigzag/sóng/xoắn ốc) hoặc `edges` + `trace` (viền) → `palette` (2–4 màu) → `optimize`; ghép ở `raster.py` |
| `links/protocol.py` | Đọc từng dòng máy gửi (trạng thái, `ok`, `error`, `ALARM`); lệnh chỉ đọc theo `$CMD` thật; tên mã theo `$E`/`$A` |
| `links/serial_link.py`, `sim_link.py`, `base.py` | Cổng COM thật / máy giả (hiệu chỉnh theo log board thật) / khuôn chung |

## 3. Frontend (`frontend/`)
| File | Vai trò |
|---|---|
| `index.html`, `assets/css/tokens.css` | Khung ba tab. Màu (`--highlight` cam nhấn, `--paper*` giấy/mực canvas), hai bản tối/sáng: chỉ sửa `tokens.css` |
| `css/style.css` · `css/drawing.css` · `css/polish.css` | Nền chung · riêng tab vẽ · lớp tinh chỉnh nạp sau cùng (bố cục tab Điều khiển, hiệu ứng, tên thương hiệu; xóa dòng `<link>` của nó để quay về như cũ) |
| `locales/vi.json`, `en.json` | Mọi chữ hiển thị (hai file phải khớp khóa) |
| `js/app.js` | Vào cửa: tab, ngôn ngữ, sáng/tối, gọi `init*` của các view |
| `js/core/api.js` | Nơi **duy nhất** gọi backend |
| `js/core/state.js` | Nơi **duy nhất** thăm dò; `isConnected()`, `isStale()`, `firmwareLabel()`, `refreshNow()` |
| `js/core/config.js` | Giá trị dùng chung: `MACHINE` (máy, bút; Cài đặt ghi đè), `PREFS` (Hoạt động), `POLL`, `VIEW` |
| `js/core/i18n.js` | Dịch chữ |
| `js/lib/gcode.js` | Đọc G-code (thuần tính toán; có `cleanLine`) |
| `js/stores/jobstore.js` | Tệp G-code đang nạp (Điều khiển ghi, khung 2D đọc; tab vẽ giao tệp qua `setFile`) |
| `js/stores/macros.js` | Macro: kiểm tra nhanh + bản sao trong bộ nhớ, lưu thật ở máy chủ (`/api/macros`) |
| `js/lib/imageprep.js` | Thu nhỏ ảnh trước khi gửi + công thức xem trước độ sáng (khớp `raster_in.py`/`tone.py`, có test) |
| `js/stores/draftstore.js` | Danh sách bản thảo (`/api/draw/drafts`) dùng chung cho tab Tạo bản vẽ và Hàng đợi; ghim, đẩy ưu tiên, xóa, nạp vào Điều khiển |
| `js/lib/paper.js` | Bố trí tờ giấy / khung vẽ / xoay (bản JS của `layout.py`, test đối chiếu backend: `node --test frontend/tests/paper.test.mjs`) |
| `js/lib/drafts.js` | Định dạng số liệu bản thảo |
| `js/views/header.js` | Đầu trang + ô trạng thái trên thanh tab + thanh cảnh báo + nút ↻ |
| `js/views/terminal.js` | Terminal và nút Tạm dừng / Tiếp tục / Hủy jog / Reset / Mở khóa |
| `js/views/control.js` | Tab Điều khiển: trạng thái, mở khóa chuyển động, jog, **thanh bút 3 nấc**, Zero, Home (hỏi lại), tệp G-code (cảnh báo gốc vị trí khi chưa Home), **ghi đè tốc độ**, tiến trình, hủy tác vụ. Hàng đợi công việc do `drafts.js` lo |
| `js/views/preview.js` | Khung 2D (khối con của Điều khiển). Đang chạy đúng tệp đã nạp: vết vẽ theo đường của tệp (`trackProgress`), cung tròn không bị gãy theo nhịp hỏi vị trí |
| `js/views/settings.js` | Tab Cài đặt: kết nối (nhớ cổng lần trước) · Hoạt động · **Cấu hình máy** (YAML trên mạch + hồ sơ phần mềm + nạp bản sao lưu) |
| `js/views/dock.js` | Dock bên trái: macro + Tệp nhanh (bản thảo đã ghim) |
| `js/views/drawing.js` | Tab Tạo bản vẽ: nạp tệp → tác vụ nền (tiến trình, hủy) → nét nháp → bố trí → G-code → bản thảo / sang Điều khiển. Phần con: `views/drawing/params.js` (các ô ⇄ dữ liệu gửi backend), `views/drawing/canvas.js` (canvas giấy A6/A5/A4, kéo – co giãn – hít lề), `views/drawing/presets.js` (bộ thông số dựng sẵn: dữ liệu), `views/drawing/tonepreview.js` (xem trước ảnh sau chỉnh sáng) |
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

## 5. Chạy và thử
* Chạy: `uvicorn app.main:app --reload` trong `backend/` (đang sửa code) → `http://127.0.0.1:8000/`. Bản mang đi: icon Desktop → `launcher/start.vbs` → `start.ps1` (Python/ embeddable, `--host 0.0.0.0`, tự đặt `EXTRUXY_ALLOWED_HOSTS` theo IP LAN, `EXTRUXY_IDLE_EXIT_MIN=10`).
* Test backend (trong `backend`, đã bật venv): `python -m pytest` (~270 test, ~70 s). Test frontend (từ gốc): `node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs`.
* Sửa Python xong phải tắt (Ctrl+C) và chạy lại server. Chữ không đổi: Ctrl+Shift+R hoặc F12 → Network → Disable cache. Lỗi lạ: F12 → Console, dán dòng đỏ.
* Thói quen: áp từng bước nhỏ → test → thử bằng sim → commit Git.
* Cài thư viện (lần đầu hoặc sau khi cập nhật): `pip install -r requirements.txt -r requirements-dev.txt`.

## 6. Luồng dữ liệu chính
**Điều khiển máy:** trình duyệt `state.js` hỏi `GET /api/status` mỗi 0,5 s → `MachineService` giữ trạng thái từ báo cáo của firmware. Lệnh: `api.js` → `/api/command|realtime|motion|jobs` → `MachineService` → `JobRunner` (gửi từng dòng, chờ `ok`) → `SerialLink`/`SimLink`. Mọi lệnh đi qua một chỗ kiểm tra (khóa chuyển động, đang dừng, đang chạy tác vụ).

**Tạo bản vẽ:** chọn tệp → (ảnh: trình duyệt thu nhỏ về đúng cỡ, `lib/imageprep.js`) → `POST /api/draw/import` → `tasks.py` (một luồng) → `isolated.py` (tiến trình con ưu tiên thấp) → `raster.build_raster` (đọc → sắc độ → tô nét/viền/chia màu → vpype) → lớp nét lưu ở `store.TASKS` (3 bản gần nhất) → `GET .../preview` (nét rút gọn, tọa độ nguồn) → canvas tự bố trí bằng `lib/paper.js` (bản JS của `layout.py`) → `POST /api/draw/gcode` (bố trí + G-code, **không lưu**) → `POST /api/draw/drafts` (lưu bản thảo vào đĩa) → tab Điều khiển nạp bản thảo (`draftstore.loadIntoControl` → `jobstore.setFile`) → xem trước → xác nhận → chạy.

**Kéo khung bản vẽ:** lệch quá 12% so với cỡ lúc tạo nét thì giao diện tự tạo lại nét (`scheduleRetrace` trong `drawing.js`) để khoảng cách gạch luôn đúng theo bề rộng bút thật.

## 7. Dữ liệu trên đĩa và biến môi trường
| Thứ | Ở đâu | Ghi chú |
|---|---|---|
Gốc dữ liệu = `data/` (tự tạo khi cần, không lên Git); đổi bằng `EXTRUXY_DATA_DIR`. Giao diện không cho đổi đường dẫn.

| Thứ | Ở đâu (trong gốc) | Ghi chú |
|---|---|---|
| Hồ sơ phần mềm | `profile.json` | Z bút, tốc độ bút, bước jog tối đa |
| Sao lưu YAML mạch | `config_backups/` | tạo trước mỗi lần "Lưu vào mạch" |
| Cài đặt bản thảo | `draw_settings.json` | số bản tối đa, dung lượng tối đa |
| Bản thảo | `drafts/` | mỗi bản một thư mục: `meta.json`, `draw[-<n>-<màu>].gcode`, `preview.svg` |
| Macro | `macros/` | mỗi macro một tệp `m_<mã>.json` |
| Điểm dừng tác vụ | `resume.json` | G-code đã làm sạch + số dòng đã nhận; xóa khi tác vụ chạy trọn |
| Nhật ký hệ thống | bộ nhớ | **không ghi tệp** (đã quyết định bỏ, xem DECISIONS S5) |

Biến môi trường (đều tùy chọn):
| Biến | Tác dụng |
|---|---|
| `EXTRUXY_DATA_DIR` | thư mục gốc dữ liệu (mặc định `data`) |
| `EXTRUXY_ALLOW_MOTION=1` | mở khóa chuyển động cố định (máy thật mặc định chỉ đọc) |
| `EXTRUXY_UNLOCK_MINUTES` | tự khóa lại sau chừng này phút (mặc định 15; 0 = tắt) |
| `EXTRUXY_UNLOCK_PIN` | đòi PIN khi mở khóa chuyển động |
| `EXTRUXY_NO_UNLOCK=1` | cấm mở khóa từ giao diện |
| `EXTRUXY_ALLOWED_HOSTS` | danh sách Host được gọi API (mặc định chỉ cục bộ) |
| `EXTRUXY_IDLE_EXIT_MIN` | tự tắt server khi không có yêu cầu nào chừng này phút và không đang chạy tác vụ (`app/idle.py`; mặc định 0 = không tắt; launcher đặt 10). Tab ẩn vẫn gửi `/api/health` mỗi 30 s |
| `EXTRUXY_DRAW_INPROC=1` | xử lý ảnh ngay trong tiến trình server (test, gỡ lỗi) |
| `EXTRUXY_DRAW_TIMEOUT_S` | quá giờ thì dừng xử lý ảnh (600) |
| `EXTRUXY_DRAW_MAX_MB` | trần bộ nhớ ảo của tiến trình xử lý ảnh, chỉ Linux (4096) |

## 8. Các chốt an toàn đã có
- Máy thật chỉ đọc cho tới khi mở khóa chuyển động; lệnh `hold`/`reset`/`jog_cancel` luôn gửi được; lệnh chỉ đọc lấy từ `$CMD` thật (`links/protocol.py`).
- Backend chỉ nhận Host cục bộ và chặn POST từ Origin lạ. **Chưa có đăng nhập** (xem `PLAN_ONLINE.md` trước khi mở ra mạng).
- G-code tệp bị làm sạch (`job.clean_gcode`): bỏ chú thích; từ chối dòng `$...` (cài đặt, Home, jog), ký tự realtime (`? ! ~`, Ctrl-X), ký tự lạ; tối đa 200 000 dòng, 200 ký tự/dòng. G-code do tab vẽ sinh ra cũng phải qua đúng bộ làm sạch này (kiểm trong `service.py`). Bộ làm sạch còn chặn `G10, G28, G30, G38, G53, G55–G59, G92` (đổi gốc / hệ tọa độ, chạy tới chỗ máy tự chọn) và báo một lần tối đa 5 dòng lỗi kèm số dòng; `lib/gcode.js` (`BLOCKED_G`) báo trước ngay lúc nạp và khóa nút Chạy. G54, G91, G20, M0, lệnh lạ không bị chặn (firmware tự báo). G-code của tab vẽ không sinh các lệnh bị chặn.
- Mọi nét phải nằm trong vùng làm việc; `layout.py` chặn khung vượt giấy, `service.py` kiểm lại trước khi ra G-code.
- Hủy an toàn 3 chế độ (reset / soft / hard); trong lúc dừng, backend từ chối job mới, lệnh chuyển động và `resume` (`stopping`). Giao diện khóa điều khiển khi báo cáo trạng thái cũ quá 2 s; tác vụ đang chạy coi là mất phản hồi sau `STATUS_STALE_S` (10 s) và tự Feed Hold.
- Tab vẽ không gọi máy; chỉ một việc xử lý ảnh chạy một lúc; tiến trình xử lý ảnh có giới hạn thời gian/RAM và tự kết thúc khi hủy.

## 9. Định dạng G-code do tab vẽ sinh
Bắt đầu `G90 G21`; có `F` ở lệnh vẽ; bút lên/xuống theo `pen_up_z`/`pen_down_z` (lấy từ hồ sơ máy); mỗi nét kết thúc bút lên; G0 cho di chuyển nhanh; dòng ≤ 200 ký tự. Tránh quá nhiều đoạn rất ngắn (gửi từng dòng chờ `ok` có thể làm máy giật): `optimize.py` nối/đơn giản hóa nét, sóng tự giãn bước để vượt không quá 200 000 dòng.
