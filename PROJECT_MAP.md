# ExtruXY – Bản đồ dự án và lộ trình (29/10/2026)

Đọc một lần để biết: file nào làm gì, dữ liệu đi đường nào, ai được ghi vào đâu, đổi gì thì sửa ở đâu.
Ký hiệu: ✅ người dùng đã áp dụng và thử trên máy giả (SimLink) · 📦 Claude đã đưa bản vá, **chưa xác nhận đã áp dụng** (kiểm bằng `grep` trong mã thật) · ⏳ chưa làm · ⚠ giả định chưa kiểm chứng trên máy thật. **Nếu mã nguồn mới lệch với bảng dưới, mã mới là sự thật.**

## 1. Sơ đồ
```
Máy vẽ (FluidNC, MKS DLC32) ⇄ cáp USB (COM)   hoặc   SimLink (máy giả)
        ⇅
Backend Python (FastAPI): giữ trạng thái, nhật ký, đoán Home, khóa chuyển động,
                          chặn lệnh nguy hiểm, chạy G-code, trình tự dừng an toàn
        ⇅  HTTP /api/...
Trình duyệt: api.js (gọi mạng) → state.js (hỏi backend mỗi 0,4 giây) → các view hiển thị
```
Giao diện chỉ hiển thị; backend là nguồn sự thật. **Không có thẻ SD/flash** (đã bỏ, D9): G-code luôn được gửi từng dòng từ máy tính. Giai đoạn sau, backend chạy trên **mini PC i5 thế hệ 3**.

## 2. Backend (`backend/app/`)
| File | Vai trò |
|---|---|
| `main.py`, `routes.py` | Khởi động, phục vụ trang web, API: `health, ports, connection, connect, disconnect, status, command, realtime, log, jobs, jobs/cancel` (nhận `mode`: `reset`/`soft`/`hard`, `lift_z`, `lift_feed`) 📦, `motion` (`{on, pin}`) 📦 |
| `protocol.py` | Đọc từng dòng máy gửi (trạng thái gồm `Pn`→`pins`, `SD`, `ok`, `error`, `ALARM`); danh sách lệnh chỉ đọc; tên mã lỗi |
| `services/machine.py` | **Bộ não:** kết nối, trạng thái, nhật ký 500 dòng, đoán Home từng trục, chặn lệnh khi khóa hoặc đang chạy tác vụ, **khóa/mở khóa chuyển động** (`set_motion`, tự khóa lại) 📦, **trình tự dừng an toàn** (`cancel_job`, `_stop_sequence`, luồng nền `safe-stop`) 📦, poller trạng thái (mỗi kết nối một cờ dừng) 📦 |
| `services/job.py` | Chạy G-code: làm sạch dòng, gửi từng dòng chờ `ok`, dừng khi lỗi/alarm/timeout (kèm Feed Hold) 📦, hủy |
| `links/sim_link.py`, `serial_link.py`, `base.py` | Máy giả / cổng COM thật / khuôn chung. SimLink viết theo mã nguồn FluidNC (ví dụ Reset từ Hold vẫn `ALARM:3`) |
| `tests/` | `pytest`: giao thức, SimLink, dịch vụ máy, tác vụ, API; **`test_regressions.py` (11 test)** và **`test_motion_unlock.py` (6 test)** 📦. Trong bản sao của Claude toàn bộ 85/85 pass |

## 3. Frontend (`frontend/`)
| File | Vai trò |
|---|---|
| `index.html`, `css/style.css`, `assets/css/tokens.css` | Khung tab, giao diện; **Dock** (`<aside id="dock">`) 📦. Người dùng tự chỉnh CSS lại (29/10) |
| `locales/vi.json`, `en.json` | Mọi chữ hiển thị (hai file phải khớp khóa); khóa `dock.*`, `header.*`, `control.motion.*` 📦 |
| `js/app.js` | Chỉ khởi động: tab, ngôn ngữ, sáng/tối, gọi các hàm vào cửa (`initControl`, `initHeader`, `initDock`, `initTerminal`, `initSettings`) |
| `js/api.js` | Nơi **duy nhất** gọi backend |
| `js/state.js` | Nơi **duy nhất** thăm dò; `isConnected()`, `isStale()` |
| `js/config.js` | Hằng số: kích thước máy, Z bút, tốc độ, `VIEW`, nhịp thăm dò |
| `js/i18n.js`, `gcode.js`, `jobstore.js` | Dịch chữ · đọc G-code (thuần tính toán; có `cleanLine`) · tệp đang nạp (dùng chung) |
| `js/macros.js` 📦 | Dữ liệu macro dùng chung: kiểm tra hợp lệ (hàm thuần) + kho `localStorage`; phát `extruxy:macros-changed` |
| `views/terminal.js` | Terminal và nút Tạm dừng / Tiếp tục / Reset (có hộp xác nhận) / Mở khóa |
| `views/settings.js` | Tab Cài đặt: khối kết nối máy; ⏳ hồ sơ máy (F7) |
| `views/control.js` | Tab Điều khiển: trạng thái, **nút mở khóa chuyển động + thanh CHẠY THẬT** 📦, jog, bút, Zero, Home, khối Tệp G-code, tiến trình, hủy tác vụ (hộp thoại Dừng êm / Dừng gấp 📦); hàng chờ do người dùng thêm; gọi `preview.js` |
| `views/preview.js` | Khung 2D: vùng làm việc, đường G-code, phát lại, vết bút, đầu máy |
| `views/dock.js` 📦 | Dock bên trái: macro (thêm/sửa/xóa/chạy) và chỗ cho "Tệp nhanh" |
| `views/header.js` 📦 | Chỉ báo đầu trang: backend / máy / công việc (chủ ghi duy nhất các phần tử đó) |
| `views/drawing.js` | Tab Tạo bản vẽ: ⏳ (AI khác làm, mục 7) |
| `tests/macros.test.mjs` 📦 | `node --test tests/macros.test.mjs` (5 test) |
| ~~`views/jobs.js`~~ | **Không còn dùng** (đã bỏ tab Công việc) |

**Quy ước:** mỗi tab một file view với một hàm vào cửa; mỗi khối là một hàm riêng bên trong; khối quá lớn mới tách file nhưng vẫn do hàm vào cửa gọi. **Một phần tử HTML chỉ một chủ ghi** (kiểm: `grep -n "<id>" js/*.js js/views/*.js`). Các view không import lẫn nhau, dùng chung qua `state.js`, `jobstore.js`, `macros.js`, hoặc sự kiện `extruxy:message` (báo ra terminal; terminal giữ tiếng Anh).

**Còn là rác sau khi bỏ SD/Công việc (xóa khi an toàn):** khối Thẻ SD/Flash ở Cài đặt; khối "Macro nhanh" ở tab Điều khiển và panel Macro ở Cài đặt (id `macro-list`, `add-macro-btn`, `macro-empty-state`); `initRunModeSwitch` và nút tải lên trong khối G-code; khóa dịch `control.macro.*`, `settings.macro.*`, khóa SD (để lại cũng không hại).

## 4. Đổi X thì sửa ở đâu
| Muốn đổi | Sửa ở |
|---|---|
| Kích thước máy, Z bút lên/xuống, tốc độ bút | `config.js` (`MACHINE`); ⏳ sẽ chỉnh được ở Cài đặt (F7) |
| Khung 2D ngược chiều | `config.js` (`VIEW.flipX/flipY`) |
| Nhịp thăm dò, ngưỡng "dữ liệu cũ" | `config.js` (`POLL`) |
| Một dòng chữ | `vi.json` và `en.json` (cùng khóa) |
| Dòng trạng thái trong terminal (tần suất, `Pn`, `WPos`, giờ) | `terminal.js` (`STATUS_ECHO`, `SHOW_TIME`) |
| Màu, hiệu ứng, Dock | `style.css`, `tokens.css` |
| Mở/khóa chuyển động | Nút giao diện; biến môi trường: `EXTRUXY_ALLOW_MOTION=1` (mở cố định), `EXTRUXY_UNLOCK_MINUTES` (mặc định 15; 0 tắt tự khóa), `EXTRUXY_UNLOCK_PIN`, `EXTRUXY_NO_UNLOCK=1` |
| Kiểm tra/lưu macro, nơi lưu macro | `macros.js` (`validateMacro`, `readAll`/`writeAll`) |
| Điều kiện bật nút macro | `dock.js` (`whyNotRunnable`) |
| Hành vi máy giả | `sim_link.py` |
| Lệnh nào là "chỉ đọc" | `protocol.py` |
| Giới hạn tác vụ G-code, timeout | `job.py` |
| Trình tự Dừng êm / Dừng gấp | `machine.py` (`_stop_sequence`) |

## 5. Chạy và thử (PowerShell, trong `backend`, đã bật venv)
* Chạy: `uvicorn app.main:app --reload` (đang sửa code) hoặc bấm đúp `chay-server.bat` (bật venv, mở trình duyệt, không `--reload`) → `http://127.0.0.1:8000/`.
* Test backend: `pytest`. Test macro: `node --test tests/macros.test.mjs` (trong `frontend`).
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
| **Chỉ được sửa** | `views/drawing.js`, file mới trong `backend/app/services/drawing/` và `routes_draw.py`, khóa `draw.*` ở **cuối** hai file ngôn ngữ, phần HTML của panel Tạo bản vẽ, test mới |
| **Không được sửa** | `machine.py`, `job.py`, `protocol.py`, `state.js`, `control.js`, `terminal.js`, `dock.js`, `header.js`. `api.js` chỉ được **thêm** hàm `draw*` ở cuối. Cần đổi chỗ khác thì hỏi chủ dự án |
| **Backend** | Router riêng, gắn vào `main.py` bằng một dòng. Đầu vào ảnh, đầu ra G-code dạng văn bản + thống kê. **Không gọi máy trực tiếp** |
| **Giao nhận G-code** | Đưa vào `jobstore.setFile(...)` để tab Điều khiển xem trước, tích xác nhận, chạy. Không tự chạy |
| **Định dạng G-code** | Theo `gcode.js`/`job.py`: bắt đầu `G90 G21`; có `F` (tránh cảnh báo thiếu tốc độ); dòng ≤ 200 ký tự; không `$`, không `G92/G10/G28/G53`; bút lên/xuống theo `penUpZ/penDownZ` trong `config.js` (⚠); mỗi nét kết thúc bút lên. **Tránh quá nhiều đoạn rất ngắn** (xem D10: gửi từng dòng chờ `ok` có thể làm máy giật) — gộp/đơn giản hóa nét |
| **Vùng vẽ** | Lấy từ `MACHINE` trong `config.js` (285 × 318 mm), không tự đặt số riêng |
| **Git** | Nhánh riêng `draw`, commit nhỏ, kéo từ nhánh chính mỗi ngày. Hai file ngôn ngữ là chỗ dễ xung đột nhất → chỉ thêm khóa ở cuối |
| **Quy ước chung** | A1–A8 và F4: không framework, không build, giải thích bằng lời thường, mỗi phần mới có test, ghi rõ chưa kiểm chứng gì |
| **Hạ tầng** | Xử lý ảnh chạy trên máy cá nhân/mini PC (cần Python 3.12 + vpype, Pillow, numpy, opencv); không dùng Raspberry Pi/hosting chia sẻ |
