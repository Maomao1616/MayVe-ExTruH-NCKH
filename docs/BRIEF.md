# ExtruXY — Tóm tắt cấu trúc và nút chức năng

Một trình điều khiển máy vẽ chạy trên laptop: nạp ảnh/SVG → tạo nét → G-code → gửi cho máy (MKS DLC32 + FluidNC). Không có Docker, tunnel hay AI ngôn ngữ trong phạm vi này.
Tài liệu chi tiết: `PROJECT_MAP.md` (bản đồ file), `DRAW_ROADMAP.md` (tab vẽ), `MACHINE.md` (sự thật máy thật), `DECISIONS.md` (quyết định).

## 1. Ba khối lớn

```
Trình duyệt (frontend, JS thuần)  ⇄  FastAPI (backend)  ⇄  USB serial  ⇄  FluidNC
   tab Điều khiển · Tạo bản vẽ · Cài đặt        api/ → services/ → links/
```

| Khối | Việc của nó | Không làm |
|---|---|---|
| **Điều khiển** | Kết nối, trạng thái, jog, Home/Zero, bút lên/xuống, nạp + xem trước + chạy G-code, hủy an toàn, terminal, Hàng đợi | Không tạo nét |
| **Tạo bản vẽ** | Ảnh/SVG → nét → bố trí trên giấy → G-code → lưu bản thảo | **Không bao giờ gọi máy**. Muốn vẽ phải sang Điều khiển |
| **Cài đặt** | Giao diện, cổng kết nối, thư mục bản thảo, hồ sơ máy, cấu hình máy (đọc/ghi YAML qua USB) | |

Luồng nối hai tab: Tạo bản vẽ → **bản thảo trên đĩa** (G-code + ảnh minh họa + meta) → Điều khiển đọc từ đó. Không có đường tắt nào khác.

## 2. Backend

| Thư mục | Nội dung |
|---|---|
| `app/links/` | Nói chuyện với máy: serial thật, máy giả `SimLink` để phát triển, bộ đọc giao thức |
| `app/services/machine.py`, `job.py` | Trạng thái máy, gửi lệnh, chạy G-code từng dòng chờ `ok`, hủy 3 chế độ (Reset / Dừng êm / Dừng gấp), chặn lệnh xen vào lúc đang dừng |
| `app/services/drawing/` | Toàn bộ phần vẽ (mục 3) |
| `app/api/` | Mỏng: nhận request, gọi service. `api/draw.py` là cửa của tab vẽ |

Quy tắc an toàn đã có: máy thật mặc định **chỉ đọc** (phải "Mở khóa chuyển động"); G-code bị lọc (`$`, `G92`, `G10`, `G28`, `G53` bị chặn); tối đa 200 000 dòng/tệp; mọi nét phải nằm trong vùng làm việc 285 × 318 mm; xem trước + tích xác nhận trước khi chạy.

## 3. Dây chuyền tab Tạo bản vẽ (`services/drawing/`)

```
SVG  ── svg_in ───────────────────────────────┐
Ảnh  ── raster_in → tone → styles/hatch ──────┤→ optimize (vpype) → bộ nhớ tạm (store)
                  └→ palette (2–4 màu)         │         ↓
                  └→ edges + trace (viền)      │   layout (khổ giấy, lề, xoay, lật)
                                               │         ↓
                                               │   gcode → drafts (lưu đĩa)
```

| File | Việc |
|---|---|
| `spec.py` | Khai báo **mọi tham số một chỗ** (mặc định, giới hạn). Backend kiểm tra bằng nó; frontend lấy qua `/schema` |
| `raster_in.py` | Đọc ảnh, xoay EXIF, nền trong suốt → trắng, cắt, thu nhỏ/phóng nhẹ (≤ 720 px) về cỡ làm việc |
| `tone.py` | Tự cân sáng, mức đen/trắng, gamma, CLAHE, khử nhiễu → bản đồ độ đậm |
| `hatch.py`, `styles.py` | Zigzag, sóng, xoắn ốc: độ đậm → đường gạch song song/xoắn ốc, nhiều mức xoay góc |
| `edges.py`, `trace.py` | Viền: hiệu hai Gaussian → làm mảnh → dò thành nét liền (đường giữa) |
| `palette.py` | Chia 2–4 màu (k-means trên Lab), mỗi màu một lớp |
| `raster.py` | Ghép các bước trên, báo tiến trình, trả lớp + số liệu |
| `optimize.py` | vpype: nối nét gần nhau, đơn giản hóa, bỏ nét ngắn, sắp xếp giảm quãng nhấc bút (+2-opt) |
| `layout.py` | Đặt nét vào khung vẽ trong tờ giấy (A6/A5/A4), lề, xoay 0/90/180/270, lật |
| `gcode.py`, `service.py` | Nét → dòng G-code + thống kê + cảnh báo |
| `tasks.py` | **Một luồng worker**: nạp ảnh chạy nền, có tiến trình, hủy được; yêu cầu mới hủy yêu cầu cũ (máy yếu) |
| `isolated.py` | Chạy việc ảnh → nét trong **tiến trình riêng, ưu tiên thấp**: hủy = kết thúc hẳn tiến trình, quá giờ/hết RAM chỉ chết tiến trình con, không làm giật luồng điều khiển máy vẽ. `EXTRUXY_DRAW_INPROC=1` để chạy ngay trong tiến trình (test, gỡ lỗi) |
| `drafts.py` | Lưu/đọc/dọn bản thảo; kiểm tên và đường dẫn |

### Nguyên tắc quan trọng
- **Mọi toạ độ là mm**, gốc trên trái, Y xuống. Khoảng cách gạch tính bằng mm trên khung thật nên mật độ mực đúng với bút.
- **Trình duyệt giúp một phần:** trước khi gửi, `lib/imageprep.js` thu nhỏ ảnh về đúng cỡ backend cần (ảnh 3600×4800 gửi lên chỉ còn ~650×866), và `views/drawing/tonepreview.js` cho xem ảnh sau chỉnh sáng ngay khi kéo ô (không có CLAHE/khử nhiễu). Chỉ là đường nhanh tùy chọn; backend tự làm được và luôn kiểm tra lại.
- **Độ phân giải làm việc** (cạnh dài) = khung ÷ bề rộng bút × 1,3, kẹp 400–4000 px. Ảnh lớn thì thu nhỏ; ảnh nhỏ chỉ phóng nhẹ tới 720 px. Độ phân giải chỉ ảnh hưởng thời gian **xử lý**, thời gian **vẽ** do tổng chiều dài nét và số lần nhấc bút quyết định.
- **Kéo khung lệch quá 12%** so với lúc tạo nét → giao diện tự tạo lại nét theo cỡ mới (đổi ít hơn thì chỉ phóng hình học).
- **Thứ tự xử lý ảnh:** EXIF → cắt → thu nhỏ → lọc sắc độ → bắt nét/tô. Lọc làm sau thu nhỏ để đỡ tốn CPU.
- **Sóng** tự giãn bước sóng nếu ảnh quá đậm để không vượt 200 000 dòng; **xoắn ốc** vẽ liền qua khe trắng < 3 mm để đỡ nhấc bút.

### Cách đọc từng kiểu nét
| Kiểu | Hợp với | Số nét / nhấc bút | Ghi chú |
|---|---|---|---|
| Zigzag | Hầu hết ảnh, chân dung | Ít nhất | Mặc định, ổn định nhất |
| Sóng | Trời, nước, mảng đều | Ít, nhiều điểm | Đường sóng nên G-code dài hơn zigzag |
| Xoắn ốc | Phong cách, thử nghiệm | Nhiều nhất | Nhiều lần nhấc bút ở ảnh nhiều chi tiết |
| Viền | Bản vẽ, mạch điện, scan | Ít | Nét mảnh → một đường giữa; nét dày → hai đường biên |

Đa màu: mỗi màu là **một tệp G-code riêng**, tên lớp = `<số>-<mã màu>` (ví dụ `draw-2-3231a7.gcode`, bản thảo hiện `Bản vẽ · 2-3231a7.gcode`). Vẽ xong tệp nào thì đổi bút rồi nạp tệp kế tiếp; mỗi nút "Nạp …" trong bản thảo có vệt màu bên trái.

## 4. Tab Tạo bản vẽ — nút và ô

| Nút / ô | Làm gì |
|---|---|
| **Chọn tệp** | Nạp PNG/JPG/WEBP/SVG, tạo nét ngay (nền, có thanh tiến trình) |
| **Hủy** (cạnh thanh tiến trình) | Dừng việc tạo nét đang chạy |
| **Bộ thông số dựng sẵn** | Chân dung / Phong cảnh / Mạch điện–Bản vẽ: điền sẵn tiền xử lý và kiểu nét rồi tạo lại nét. Sửa tay ô nào thì về "Tùy chỉnh" |
| **Tạo lại nét** | Chạy lại sau khi đổi thông số tạo nét (tiền xử lý, kiểu nét, bút, màu). Đổi xong giao diện báo "cần tạo lại" |
| Khung vẽ trên giấy | Kéo = dời; 8 tay nắm = co giãn; hít lề và tâm; phím mũi tên dời (Shift = 10 mm); **Shift + cuộn** = thu phóng; nhấp đúp = đặt lại |
| **Xoay 90° / Xem toàn bộ** | Xoay khung; về toàn cảnh |
| Ô khổ giấy, lề, rộng/cao, căn giữa, lật, đảo thứ tự | Bố trí; đổi là G-code tự tính lại (chờ 0,4 s) |
| Ô tốc độ, Z bút, thời gian chờ | Tham số G-code; tự tính lại. Gõ dở giá trị ngoài khoảng thì chưa báo lỗi |
| **Tạo lại** (cạnh ô xác nhận) | Tính lại G-code ngay |
| **Lưu bản thảo** | Ghi G-code + ảnh minh họa + meta vào thư mục bản thảo. Không chuyển tab |
| **Chuyển sang Điều khiển** | Cần tích "Tôi đã kiểm tra…". **Tự lưu bản thảo** (nếu chưa lưu cùng thông số thì không tạo trùng) rồi nạp vào tab Điều khiển và chuyển sang đó. Không tự chạy |
| Danh sách bản thảo | Mở xem, Nạp (theo lớp màu), Ghim, Đẩy lên đầu, Xóa (bấm hai lần) |

Dòng trạng thái sau khi tạo nét ghi tổng thời gian; rê chuột vào để xem thời gian từng bước. Ô "Ảnh gốc" dưới canvas có hộp tích **Xem ảnh sau chỉnh sáng** (xem trước độ sáng/gamma/đảo ngay khi chỉnh).

Bảng số liệu ở đầu tab: kích thước, số nét, số lần nhấc bút, độ dài vẽ/di chuyển, thời gian ước tính (chưa tính gia tốc nên chỉ để tham khảo), có nằm trong vùng làm việc không.

## 5. Tab Điều khiển — nút

| Nhóm | Nút | Làm gì |
|---|---|---|
| Đầu trang | Tạm dừng / Tiếp tục | Feed Hold / Cycle Start |
| | Hủy jog | Dừng một lệnh jog đang chạy |
| | Reset | Dừng mềm (hỏi xác nhận); không phải dừng khẩn cấp |
| Vị trí | Zero X/Y/XY, Home X/Y/tất cả | Đặt gốc làm việc; về công tắc hành trình (hỏi xác nhận) |
| Di chuyển | Mũi tên, nút giữa | Jog theo bước; về gốc làm việc |
| Bút | Lên / giữa / xuống | Theo hồ sơ máy (Z 5 / Z 0) |
| Tệp G-code | **Xem trước** → tích xác nhận → **▶ Chạy** | Phải xem trước trước khi chạy; đổi tệp là phải xem trước lại |
| | Hủy tác vụ | Hộp thoại: Tiếp tục chạy / **Dừng êm** (chờ hết bộ đệm) / **Dừng gấp** (Feed Hold → Reset → nâng bút) |
| | −10 −1 100% +1 +10 | Chỉnh tốc độ chạy (feed override) |
| Trạng thái | Mở khóa ($X) | Gỡ Alarm |
| Khung nhìn 2D | Phóng/thu, toàn cảnh, xóa vết, phát lại | Chỉ xem trước **một** G-code đang được chọn |
| Hàng đợi công việc | Làm mới, Nạp, Ghim, Đẩy ưu tiên, Mở xem | Đọc thẳng các bản thảo đã lưu |
| Terminal | Gửi, Xóa log hiển thị | Gửi lệnh tay |
| Dock bên trái | Macro | Lệnh lưu sẵn (thêm/sửa/xóa) |

## 6. Cài đặt
- **Kết nối:** chọn cổng, Kết nối / Ngắt kết nối. **Giao diện chung:** ngôn ngữ. **Hoạt động:** tùy chọn hành vi.
- **Bản thảo:** thư mục lưu (mặc định `data/drafts`, có thể đổi sang ổ khác), số bản tối đa, dung lượng tối đa. Vượt hạn mức thì xóa bản **cũ nhất không ghim**.
- **Hồ sơ máy:** vùng làm việc, Z bút. **Cấu hình máy:** đọc/ghi YAML trên mạch (có sao lưu, hoàn tác).

## 7. Cấu trúc frontend

`index.html` + `css/` + `locales/{vi,en}.json` + `js/`:
- `core/` (api, config, i18n, state) ← `lib/` (hàm thuần: gcode, paper, drafts) ← `stores/` (dữ liệu dùng chung) ← `views/` (từng tab). Các view **không import lẫn nhau**.
- Mỗi phần tử HTML chỉ có **một nơi ghi** (quy ước để khỏi giẫm chân).
- `lib/paper.js` là bản JS của `layout.py`, có test đối chiếu số với backend (`frontend/tests/paper.test.mjs`).
- Mọi chữ hiển thị qua `locales/*.json`; thêm khóa phải thêm cả hai file.
- **Giao diện (CSS):** màu nằm ở `assets/css/tokens.css` (sửa ở đó: `--highlight` cam nhấn, `--paper`/`--paper-ink` giấy và mực trên canvas, hai bản tối/sáng). `css/style.css` là nền chung, `css/drawing.css` riêng cho tab vẽ, `css/polish.css` là lớp tinh chỉnh nạp sau cùng (xóa dòng `<link>` của nó để quay về như cũ). Thứ bậc nút: chính = cam đặc, phụ = viền, nguy hiểm = đỏ (chỉ Reset, Dừng gấp, Xóa).

## 8. Chạy và kiểm tra
| Việc | Lệnh |
|---|---|
| Chạy app | Bấm đúp `Bat Khien EXTRUH.bat` (mở `http://127.0.0.1:8000/`) |
| Cài thư viện (lần đầu hoặc sau khi cập nhật) | trong `backend`, bật venv: `pip install -r requirements.txt` |
| Test backend | trong `backend`: `python -m pytest` |
| Test frontend | `node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs` |
| Sinh lại số chuẩn cho test JS (khi đổi `tone.py` / `raster_in.py`) | `python frontend/tests/fixtures/make_image_fixtures.py` (đã bật venv backend) |
| Máy giả | Chọn cổng giả `SimLink` khi chưa có board |

## 9. Chưa kiểm chứng / còn lại
- Máy thật: hướng trục X+/Y+, Z bút, thời gian Home, cung G2/G3, `G4 P` tính bằng giây trên FluidNC 4.1.1.
- **Thử vẽ dải đậm nhạt** với bút 0,2 và 0,4 để chỉnh khoảng cách gạch mặc định (hiện 2 × bề rộng bút) và các preset (`views/drawing/presets.js`).
- Ngưỡng bắt viền cố định (`edges.py`): chỉnh dần theo ảnh thật; chưa có giao diện cắt ảnh (backend đã nhận `crop_*`).
- Thời gian xử lý trên MiniPC i5-3210M chưa đo (máy dev: 0,1–2 s cho ảnh A4).
- Kế hoạch mở cho nhiều người dùng (phân quyền bằng PIN, giới hạn, Ubuntu, tunnel): `PLAN_ONLINE.md`.
- Nhật ký hệ thống chỉ nằm trong bộ nhớ (chưa ghi ra tệp, chưa xoay vòng); chưa có "tiếp tục từ dòng N"; `lib/gcode.js` chưa có test.
