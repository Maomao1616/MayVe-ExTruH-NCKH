# CODEMAP — bản đồ mã nguồn (SINH TỰ ĐỘNG)

Không sửa tay: chạy `python tools/export_context.py --map` để tạo lại. Cột token là ước tính (ký tự ÷ 3,2) để
chọn đọc tệp nào; dòng mô tả lấy từ chú thích đầu tệp. Muốn đọc nhanh: xem bản đồ này, rồi chỉ lấy gói cần
(`python tools/export_context.py --list`). Toàn bộ dự án ~254,718 token nếu đọc hết.

## API backend (đọc từ `backend/app/api/*.py`)

| Phương thức | Đường dẫn | Tệp |
|---|---|---|
| GET | `/api/machine/config` | config.py |
| POST | `/api/machine/config` | config.py |
| POST | `/api/machine/config/save` | config.py |
| GET | `/api/machine/config/backups` | config.py |
| GET | `/api/machine/config/backups/{name}` | config.py |
| GET | `/api/profile` | config.py |
| PUT | `/api/profile` | config.py |
| GET | `/api/draw/schema` | draw.py |
| POST | `/api/draw/import` | draw.py |
| POST | `/api/draw/svg` | draw.py |
| GET | `/api/draw/tasks/{token}` | draw.py |
| POST | `/api/draw/tasks/{token}/cancel` | draw.py |
| DELETE | `/api/draw/tasks/{token}` | draw.py |
| GET | `/api/draw/tasks/{token}/preview` | draw.py |
| POST | `/api/draw/gcode` | draw.py |
| POST | `/api/draw/drafts` | draw.py |
| GET | `/api/draw/drafts` | draw.py |
| GET | `/api/draw/drafts/{draft_id}` | draw.py |
| GET | `/api/draw/drafts/{draft_id}/gcode/{layer_file}` | draw.py |
| GET | `/api/draw/drafts/{draft_id}/preview.svg` | draw.py |
| PATCH | `/api/draw/drafts/{draft_id}` | draw.py |
| DELETE | `/api/draw/drafts/{draft_id}` | draw.py |
| GET | `/api/draw/settings` | draw.py |
| PUT | `/api/draw/settings` | draw.py |
| POST | `/api/motion` | machine.py |
| GET | `/api/health` | machine.py |
| GET | `/api/ports` | machine.py |
| GET | `/api/connection` | machine.py |
| POST | `/api/connect` | machine.py |
| POST | `/api/disconnect` | machine.py |
| GET | `/api/status` | machine.py |
| POST | `/api/command` | machine.py |
| POST | `/api/realtime` | machine.py |
| GET | `/api/log` | machine.py |
| POST | `/api/jobs` | machine.py |
| POST | `/api/jobs/cancel` | machine.py |

## Tệp theo thư mục

### `./`

| Tệp | Token | Vai trò |
|---|---|---|
| `README.md` | ~1,468 |  |

### `backend/app/`

| Tệp | Token | Vai trò |
|---|---|---|
| `main.py` | ~1,007 |  |

### `backend/app/api/`

| Tệp | Token | Vai trò |
|---|---|---|
| `__init__.py` | ~84 | Các router HTTP. Thêm router mới: tạo file trong api/ rồi thêm vào ROUTERS. |
| `config.py` | ~654 | API cấu hình máy (YAML trên mạch, services/machine_config.py) và hồ sơ phần mềm |
| `draw.py` | ~2,759 | API tab Tạo bản vẽ. Mỏng: mọi logic nằm trong services/drawing. Không gọi máy trực tiếp (A4). |
| `machine.py` | ~925 | API điều khiển máy: kết nối, trạng thái, lệnh, tác vụ, mở khóa. Mỏng: logic ở MachineService. |

### `backend/app/links/`

| Tệp | Token | Vai trò |
|---|---|---|
| `base.py` | ~756 | Giao diện chung cho mọi kiểu kết nối tới bộ điều khiển (máy thật hoặc mô phỏng). |
| `protocol.py` | ~2,810 | Phân tích các dòng phản hồi của FluidNC v4.1.1. |
| `serial_link.py` | ~1,058 | SerialLink: kết nối FluidNC thật qua USB/serial (CH340). |
| `sim_link.py` | ~7,793 | SimLink: máy FluidNC giả để phát triển khi chưa có board. |

### `backend/app/services/`

| Tệp | Token | Vai trò |
|---|---|---|
| `job.py` | ~3,624 | JobRunner: chạy một tệp G-code bằng cách gửi TỪNG DÒNG và chờ `ok`/`error` của firmware. |
| `machine.py` | ~13,306 | MachineService: quản lý kết nối, trạng thái máy và nhật ký. |
| `machine_config.py` | ~3,299 | Đọc / sửa / lưu cấu hình FluidNC qua cổng serial. |
| `profile.py` | ~719 | Hồ sơ phần mềm: thông số chỉ phần mềm dùng (không nằm trong YAML của mạch). |

### `backend/app/services/drawing/`

| Tệp | Token | Vai trò |
|---|---|---|
| `__init__.py` | ~319 | Tab Tạo bản vẽ: ảnh/SVG -> đường nét -> G-code. Không gọi máy. |
| `drafts.py` | ~3,156 | Bản thảo trên đĩa: G-code từng lớp + ảnh minh họa + meta.json, mỗi bản một thư mục con. |
| `edges.py` | ~268 | Bắt nét viền bằng hiệu hai Gaussian (DoG, lõi của XDoG): nét đen nơi vùng tối hơn xung quanh. |
| `errors.py` | ~108 | Lỗi của tab Tạo bản vẽ. `code` ổn định để frontend dịch (quy ước E3), `message` chỉ để tra cứu. |
| `gcode.py` | ~1,455 | Đường nét (mm, đã bố trí) -> dòng G-code + thống kê. Không gọi máy. |
| `hatch.py` | ~2,408 | Lõi tô bằng nét: bản đồ độ đậm -> mặt nạ từng mức -> đường quét song song / xoắn ốc -> các nét (mm). |
| `isolated.py` | ~2,204 | Chạy việc nặng (ảnh -> nét) trong TIẾN TRÌNH RIÊNG, ưu tiên thấp. |
| `layout.py` | ~1,620 | Bố trí: đặt đường nét vào KHUNG VẼ nằm trong TỜ GIẤY, tờ giấy nằm trong vùng làm việc của máy. |
| `optimize.py` | ~657 | Tối ưu nét bằng vpype: nối nét gần nhau, đơn giản hóa, bỏ nét ngắn, sắp xếp giảm quãng bút nâng. |
| `palette.py` | ~1,124 | Chia 2–4 màu: k-means (OpenCV) trên Lab, ảnh thu nhỏ ~300 px; mỗi màu một vùng, mỗi vùng một lớp bút. |
| `preview.py` | ~409 | Nét xem nháp: rút gọn để vẽ lên canvas (tọa độ NGUỒN, trước bố trí; frontend tự di chuyển/co giãn). |
| `raster.py` | ~1,984 | Dây chuyền ảnh raster -> đường nét: đọc -> chỉnh sắc độ -> tô nét -> tối ưu vpype. |
| `raster_in.py` | ~1,737 | Nạp ảnh raster -> ảnh xám ở độ phân giải làm việc + kích thước thật (mm). |
| `registry.py` | ~379 | Sổ đăng ký: gom các biến thể cùng loại (kiểu vector hóa...). Thêm kiểu mới không sửa chỗ khác. |
| `service.py` | ~1,353 | Ghép các bước: kiểm tra tham số -> bố trí -> G-code (mỗi lớp một tệp) -> kiểm bằng chính bộ làm sạch |
| `shapes.py` | ~174 | Kiểu dữ liệu dùng chung. Tọa độ đường nét: (x, y) tính bằng mm, gốc ở góc trên trái, Y xuống. |
| `spec.py` | ~3,034 | Khai báo tham số MỘT chỗ: tên, kiểu, mặc định, giới hạn. Dùng để kiểm tra đầu vào VÀ để trả cho |
| `store.py` | ~463 | Bộ nhớ tạm các bản vẽ đã nạp (để đổi tham số bố trí/G-code không phải nạp lại ảnh/SVG). |
| `styles.py` | ~1,345 | Kiểu tô: zigzag, sóng, xoắn ốc. Mỗi kiểu nhận Field (độ đậm) -> danh sách nét (mm). |
| `svg_in.py` | ~1,559 | Nạp SVG (nhiều lớp) bằng vpype -> các lớp đường nét tính bằng mm. |
| `tasks.py` | ~1,287 | Tác vụ nền của tab vẽ: MỘT luồng worker tại một thời điểm, có tiến trình và hủy hợp tác. |
| `tone.py` | ~521 | Chỉnh sắc độ: ảnh xám uint8 -> bản đồ độ đậm float32 0..1 (1 = đen nhất, cần nhiều mực nhất). |
| `trace.py` | ~1,249 | Mặt nạ nét -> làm mảnh (skeleton) -> dò thành các nét liền (mm). |

### `backend/tests/`

| Tệp | Token | Vai trò |
|---|---|---|
| `test_board_paths.py` | ~2,038 | Mọi nút và mọi dòng terminal phải tới được board; hành vi theo log MKS DLC32 thật |
| `test_job.py` | ~1,682 | Tác vụ G-code: làm sạch dòng, chạy từng dòng chờ ok, lỗi, hủy, chặn lệnh khác. |
| `test_machine_config.py` | ~2,408 | Đọc / sửa / lưu cấu hình FluidNC (machine_config.py) và hồ sơ phần mềm (profile.py). |
| `test_machine_service.py` | ~1,413 |  |
| `test_motion_unlock.py` | ~855 |  |
| `test_protocol.py` | ~562 |  |
| `test_regressions.py` | ~2,227 | Hồi quy cho các lỗi đã gặp ở Giai đoạn "xác thực" (28/10/2026). |
| `test_routes.py` | ~1,723 | Kiểm tra lớp HTTP: đường dẫn, mã trạng thái, hình dạng JSON mà frontend dựa vào. |
| `test_safe_stop.py` | ~2,897 | Hồi quy cho đợt tối ưu backend 29/10/2026 (cac_van_de_can_toi_uu_backend.txt). |
| `test_sim_link.py` | ~3,718 | SimLink phải khớp hành vi đã thấy trên board thật (MACHINE.md, 29/10/2026). |

### `backend/tests/draw_test/`

| Tệp | Token | Vai trò |
|---|---|---|
| `test_draw_contract.py` | ~3,346 | Hợp đồng API của tab vẽ: nạp nền + tiến trình + hủy, nét nháp, bản thảo trên đĩa, xoay. |
| `test_draw_gcode.py` | ~1,424 |  |
| `test_draw_layout.py` | ~1,439 |  |
| `test_draw_optimize.py` | ~526 |  |
| `test_draw_registry.py` | ~196 |  |
| `test_draw_routes.py` | ~1,212 | Lớp HTTP của tab vẽ. Cần fastapi/httpx (chạy ở máy bạn). |
| `test_draw_service.py` | ~1,027 |  |
| `test_draw_spec.py` | ~822 |  |
| `test_draw_store.py` | ~332 |  |
| `test_draw_svg_in.py` | ~1,556 |  |
| `test_hatch.py` | ~1,562 |  |
| `test_isolated.py` | ~1,131 | Xử lý ảnh trong tiến trình riêng: kết quả như chạy thẳng, hủy / quá giờ / sập đều gọn. |
| `test_palette.py` | ~743 |  |
| `test_raster_in.py` | ~1,282 |  |

### `backend/tools/`

| Tệp | Token | Vai trò |
|---|---|---|
| `probe_vpype.py` | ~153 |  |

### `docs/`

| Tệp | Token | Vai trò |
|---|---|---|
| `BRIEF.md` | ~2,627 |  |
| `DECISIONS.md` | ~2,062 |  |
| `DRAW_ROADMAP.md` | ~4,497 |  |
| `MACHINE.md` | ~1,189 |  |
| `PLAN_ONLINE.md` | ~1,493 |  |

### `frontend/`

| Tệp | Token | Vai trò |
|---|---|---|
| `index.html` | ~23,754 |  |

### `frontend/assets/css/`

| Tệp | Token | Vai trò |
|---|---|---|
| `tokens.css` | ~902 | 1. BANG MAU - SUA CAC BIEN NAY DE DOI MAU - TOI |

### `frontend/css/`

| Tệp | Token | Vai trò |
|---|---|---|
| `drawing.css` | ~2,556 | 9. TAB TAO BAN VE |
| `polish.css` | ~4,198 | POLISH: lop tinh chinh giao dien |
| `style.css` | ~13,036 |  |

### `frontend/js/`

| Tệp | Token | Vai trò |
|---|---|---|
| `app.js` | ~1,965 |  |

### `frontend/js/core/`

| Tệp | Token | Vai trò |
|---|---|---|
| `api.js` | ~1,306 | DUY NHẤT nơi gọi fetch. Chỉ dùng các endpoint có trong backend v0.2.0. |
| `config.js` | ~466 | Hằng số máy và giao diện. Mọi giả định chưa kiểm chứng ghi ở đây để sửa một chỗ. |
| `i18n.js` | ~439 |  |
| `state.js` | ~1,778 | NƠI DUY NHẤT nhận dữ liệu từ backend. Không đụng vào DOM. |

### `frontend/js/lib/`

| Tệp | Token | Vai trò |
|---|---|---|
| `drafts.js` | ~424 | định dạng thông tin bản thảo (meta.json do backend trả). THUẦN (không DOM, không mạng). |
| `gcode.js` | ~3,413 | đọc G-code thành các đoạn đường để xem trước. THUẦN (không DOM, không mạng). |
| `imageprep.js` | ~2,045 | chuẩn bị ảnh ngay trong trình duyệt TRƯỚC khi gửi, và xem trước độ sáng. |
| `paper.js` | ~1,502 | bố trí bản vẽ trên tờ giấy. THUẦN (không DOM, không mạng). |

### `frontend/js/stores/`

| Tệp | Token | Vai trò |
|---|---|---|
| `draftstore.js` | ~681 | danh sách bản thảo (GET /api/draw/drafts), dùng chung cho tab Tạo bản vẽ và Hàng đợi |
| `jobstore.js` | ~253 | tệp G-code đang nạp ở trình duyệt. control.js ghi, preview.js đọc. |
| `macros.js` | ~1,136 | dữ liệu macro dùng chung (Dock đọc/ghi, không import view nào). |

### `frontend/js/views/`

| Tệp | Token | Vai trò |
|---|---|---|
| `control.js` | ~8,103 | Tab Điều khiển. |
| `dock.js` | ~1,931 | khối tiện ích bên trái, luôn có mặt ở mọi tab. |
| `drafts.js` | ~2,145 | danh sách bản thảo ở HAI nơi (cùng dữ liệu từ stores/draftstore.js): |
| `drawing.js` | ~7,454 | Tab Tạo bản vẽ: điều phối. Luồng (docs/DRAW_ROADMAP.md mục 3–4): |
| `header.js` | ~1,706 | chỉ báo ở đầu trang: backend / máy / công việc, ô trạng thái trên |
| `preview.js` | ~5,907 | Khung nhìn 2D. Chủ sở hữu của #preview-canvas và thanh phát lại. |
| `settings.js` | ~10,260 | Tab Cài đặt. Một hàm vào cửa, mỗi khối trên giao diện một hàm: |
| `terminal.js` | ~3,698 | CHỦ SỞ HỮU DUY NHẤT của #terminal-output và các nút an toàn. |

### `frontend/js/views/drawing/`

| Tệp | Token | Vai trò |
|---|---|---|
| `canvas.js` | ~5,385 | canvas khung vẽ: tờ giấy (A6/A5/A4 như khung dán thật trên bàn), lề, nét xem nháp |
| `params.js` | ~4,195 | các ô thông số của tab Tạo bản vẽ <-> dữ liệu gửi backend. |
| `presets.js` | ~533 | bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu). |
| `tonepreview.js` | ~943 | khung "ảnh gốc" của tab Tạo bản vẽ: xem ảnh gốc hoặc ảnh SAU chỉnh sáng |

### `frontend/locales/`

| Tệp | Token | Vai trò |
|---|---|---|
| `en.json` | ~11,437 |  |
| `vi.json` | ~11,131 |  |

### `frontend/tests/`

| Tệp | Token | Vai trò |
|---|---|---|
| `imageprep.test.mjs` | ~752 | Đối chiếu lib/imageprep.js với backend: node --test frontend/tests/imageprep.test.mjs |
| `paper.test.mjs` | ~1,895 | Đối chiếu lib/paper.js với backend (layout.py). Sinh bởi script từ chính backend — chạy: node --test frontend/ |
