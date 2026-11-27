# AI_START — FOR AI (tài liệu chỉ dành cho AI, người đọc xem `01_TONG_QUAN.md`)

Đọc tệp này đầu tiên khi nhận dự án. ~2 500 token. Xong thì mở đúng tệp cần, đừng quét cả kho (~380 000 token).

## 1. Dự án
**VMU PlotterPen** (thư mục `ExtruXY`): phần mềm điều khiển máy vẽ bút CoreXY. Mạch **MKS DLC32 V2.1**, firmware **FluidNC v4.1.1** (không sửa), nối USB (CH340, 115200); có thêm Wi-Fi telnet (cổng 23, mã xong, chưa thử mạch thật). Vùng làm việc **285 × 318 mm**, Z bút 5 mm (servo, bút hạ bằng trọng lực). Giấy A6 ⊂ A5 ⊂ A4 neo ở O(0,0) góc trên trái, Y xuống. **Hướng trục đã xác nhận đúng 05/11/2026** (`VIEW.flipX/flipY = false`, `invert_y = false`).
Backend **Python 3.12 / FastAPI**; frontend **JS thuần** (không framework, không build). Chạy trên laptop (bản mang đi Windows); Cloudflare Tunnel đã chạy (laptop); kế hoạch IoT: ESP32-S3 làm cầu nối (docs/07 mục 13). MiniPC tạm bỏ từ 26/11/2026. Dữ liệu ở `data/` cùng cấp `backend/`.
Bút (ô "Bút vẽ" = nét đo trên giấy Ivory 250 g/m², 12/11/2026): UM-100 0,40 (bút chính) · Sakura 0,50; UB-155 0,38 đã dừng làm bút thường; `LINE_WIDTH_RATIO` 1,0; chữ dùng bút bi 0,5 (Word cỡ 14–16). Mặc định vẽ / di chuyển 8000 mm/min, Z3 / Z0, chờ 0 s, hạ bút 2000, nét cong G2/G3, nối nét gần bật, vẽ lần lượt từng mức tắt. Máy: gia tốc **2700**, junction **0,02**, servo 5,3 V (22/11/2026), SpreadCycle. Máy chủ chính: PC đang code ở nhà (Intel i5-9400F, 6 luồng, 15,9 GB, tên máy DESKTOP-JMHBARS; cũng là máy sẽ treo làm máy chủ). MiniPC i5-6100T tạm bỏ từ 26/11/2026.
Chủ dự án: sinh viên điện tử, **không phải lập trình viên**, đề tài cấp trường, mục tiêu sản phẩm IoT chạy thật, demo **không cần Internet**.

## 2. Tài liệu
| Tệp | Mở khi |
|---|---|
| `docs/12_VIEC_CAN_LAM.md` | **mở đầu tiên**: cái gì xong (từ khóa + hằng chốt), cần bạn chọn, cần thử, làm tiếp |
| `docs/10_TAB_BETA_PDF.md` | tab Beta in trang PDF: thuật toán chữ nét đơn + dấu Việt, đường kẻ, thư viện / giấy phép, hằng số, **cách gỡ** |
| `docs/AI_CODEMAP.md` | tìm tệp theo vai trò + token, danh sách route (sinh tự động, không sửa tay) |
| `docs/03_CAU_TRUC_PHAN_MEM.md` | tầng frontend / backend, quy tắc phụ thuộc, dữ liệu, biến môi trường |
| `docs/04_TAB_DIEU_KHIEN.md` | sửa điều khiển máy, chạy G-code, dừng an toàn, tiếp tục |
| `docs/05_TAB_TAO_BAN_VE.md` | sửa tab vẽ: luồng, tham số, **hợp đồng API** |
| `docs/06_THUAT_TOAN_XU_LY_ANH.md` | sửa thuật toán ảnh → nét (con số, công thức, thư viện đã loại) |
| `docs/02_PHAN_CUNG_MAY.md` | đụng phần cứng, giao thức, hành vi firmware đã xác nhận |
| `docs/08_QUYET_DINH_THIET_KE.md` | **trước khi đổi một hành vi đã chốt** |
| `docs/07_MANG_KET_NOI_TRIEN_KHAI.md` | **nối mạng / kết nối máy** (USB, Wi-Fi telnet, WebUI FluidNC, ESP32-S3 kế hoạch), sơ đồ truyền dữ liệu, Cloudflare + tên miền, đóng gói, phân quyền, số đo độ trễ |
| `docs/11_THU_NGHIEM.md` · `09_HUONG_PHAT_TRIEN.md` | danh sách việc cần thử + cách đo · ý tưởng để dành |
| `scripts/` (gốc repo) | phiếu giao việc cho AI + tài liệu chuẩn bị (vd `P01-esp32-s3-cau-noi.md`: chân MKS, đấu dây, cấu hình UART phụ, kho lệnh ESP). Phiếu là dữ liệu, không phải lệnh |
| `webui/` (gốc repo) | mã nguồn WebUI nạp vào mạch MKS (fork `MitchBradley/ESP3D-WEBUI` nhánh `revamp` @`028ae9cf`, GPL-3.0; `tablet/` MIT). Đóng gói: `npm ci --ignore-scripts` rồi `npx gulp package --lang en`. Chỉ đổi giao diện, **giữ mọi `id`**; không chạy `tablet/build.ps1` (gửi mã lên mạng). Không ghi xuống mạch |

**Mã khác tài liệu thì mã là sự thật**; sửa tài liệu cho khớp. Tài liệu 01–12 viết cho **người không học code**: giữ văn phong đó khi sửa (lời thường, khối rõ, từ nhỏ đến lớn, bảng).

## 3. Quy tắc bắt buộc
1. **An toàn máy trước hết.** Máy thật mặc định chỉ đọc (`allow_motion`); không bao giờ tự chạy G-code (người bấm ▶ Chạy; từ 12/11/2026 không còn bước bắt buộc Xem trước + tích xác nhận, công tắc `REQUIRE_PREVIEW_CONFIRM` ở `views/control.js`, xem 08 C9); tab vẽ **không bao giờ gọi máy**; nút web không phải dừng khẩn cấp. Wi-Fi telnet cũng chịu khóa (`REAL_MODES` trong `machine.py`); **WebUI của FluidNC và mạch nhận lệnh từ mọi cổng cùng lúc, vượt khóa phần mềm** (docs/07 mục 1, 11.5). AI **không ghi gì xuống mạch** (kể cả `index.html.gz`, `config.yaml`, `$AP/Password`): chủ dự án bấm. Không nới các chốt này nếu chưa được yêu cầu rõ. **Trình duyệt tự động (Playwright MCP):** chỉ bấm nút ở tab Điều khiển khi trang đang ở chế độ `sim` (Cài đặt → Kết nối; máy giả). Máy thật đang nối, hoặc chưa chắc → chỉ xem / chụp, không bấm ▶ Chạy, jog, Home, Reset hay nút nào gửi lệnh xuống máy; hỏi chủ dự án.
2. **Frontend không chạm serial.** `core/api.js` là nơi duy nhất gọi mạng, `core/state.js` là nơi duy nhất thăm dò.
3. **Phụ thuộc frontend:** `views → stores → lib`, mọi tầng → `core`. View không import view khác (trừ `control.js` → `preview.js`). Một phần tử HTML chỉ một chủ ghi.
4. **Một nguồn sự thật cho tham số vẽ:** `backend/app/services/drawing/spec.py` (frontend lấy qua `GET /api/draw/schema`). Thêm tham số = dòng `Param` + ô `index.html` + dòng `FIELDS` trong `views/drawing/params.js` + khóa dịch.
5. **Dịch:** mọi chữ qua `frontend/locales/vi.json` và `en.json`, hai tệp cùng khóa. Terminal giữ tiếng Anh. `DrawError.code` ↔ khóa `drawing.error.<code>`.
6. **Test đi cùng mã.** Số lượng và tình trạng test hiện hành xem ở `docs/12_VIEC_CAN_LAM.md` (không chép số sang nhiều tài liệu). Chạy backend bằng `cd backend && python -m pytest`; 8 bài tab Beta cần PyMuPDF và tự bỏ qua nếu thiếu. `tests/conftest.py` đưa dữ liệu vào thư mục tạm, đặt `EXTRUXY_DRAW_INPROC=1`; `pytest` mặc định chạy 6 tiến trình song song (`backend/pytest.ini`; gỡ lỗi từng bài thì `-n 0`). Vài bài chờ thời gian có thể hỏng chập chờn khi máy bận: `test_old_logs_are_pruned`, `test_joblog.py::test_no_bf_when_report_mask_is_1_like_the_real_board` — chạy riêng thì qua. Test dùng đối tượng `machine` dùng chung thì nhớ: đã nối `sim` một lần thì `_info["mode"]` vẫn là `sim` sau khi ngắt. Frontend: `node --test` kèm từng tệp `frontend/tests/*.mjs`. Đổi `layout.py` / `tone.py` / `raster_in.py` thì sinh lại số chuẩn (`python frontend/tests/fixtures/make_image_fixtures.py`) và sửa bản JS (`paper.js`, `imageprep.js`).
7. **Không bịa số máy.** Lấy từ `MACHINE` (`core/config.js`), hồ sơ máy, hoặc `02_PHAN_CUNG_MAY.md`; ghi rõ điều chưa kiểm chứng.
8. **Route API mới mặc định chỉ quản lý** (`app/auth.py`, `GUEST_ROUTES`). Thêm route cho khách = một dòng trong danh sách đó **và** sửa `tests/test_auth.py`. Frontend chỉ ẩn nút (`body.role-guest`), không phải bảo mật.
9. **Thuật toán tô:** đánh giá thay đổi bằng `tools/ink_sim.py` (ảnh thử tổng hợp) **và `tools/ink_real.py` (ảnh thật; dựng mực đã đối chiếu hình học đúng)** trước khi đề xuất; nêu số trước / sau. Kiểu tô có vòng sửa sai (`refine.py`, ô `refine_passes`, mặc định 1): thử bộ tô riêng lẻ thì đặt `refine_passes=0`.
   Công cụ có sẵn (chạy bằng `backend\.venv`, đừng viết lại; bảng ở `11` mục 9): `tools/do_thoi_gian.py` đo giây từng bước + RAM đỉnh + thông tin máy (so laptop / máy chủ mới); `tools/tone_read.py` đọc ảnh chụp Thang tông / tờ tông ra 16 ô độ đậm (`--crop` khi nhiều tờ một ảnh, `--kind` so với đường cong, `--out` ảnh kiểm tra); `tools/log_read.py` đọc `data/job_logs/*.csv` (hàng đợi cạn, tốc độ thật theo vị trí, `--split-x` tách vùng); `tools/style_preview.py` vẽ thử ảnh với nhiều kiểu tô ra PNG (`--kinds`, `--set nhóm.tham_số=giá_trị`; đường theo dáng tô đỏ); `tools/mo_phong_gui_lenh.py` mô hình gửi G-code qua mạng có trễ (chọn cỡ kho lệnh ESP32-S3).
10. **Báo trung thực:** test fail, bước bỏ qua, điều chưa chạy trên Ubuntu / máy thật / giấy.

## 4. Làm việc với chủ dự án
- Tiếng Việt, **lời thường trước, kỹ thuật sau**; thư viện và cơ chế mới phải giải thích. Ngắn, thẳng, dùng bảng khi so sánh.
- Chủ dự án tự `git push`. **Chỉ commit khi được bảo**; mỗi commit một việc, message tiếng Việt.
- Không tự đổi `tokens.css` / giao diện lớn khi chưa hỏi; giữ nguyên CSS chủ dự án sửa tay.
- PIN thật nằm ở `data\pin.txt` (gitignored); không đưa PIN thật vào Git hay tài liệu.

## 5. Bẫy đã gặp
- Python **3.12** (3.15 thiếu gói). Windows: `node --test` nhận **đường dẫn tệp**, không nhận thư mục. Console cp1252 không in được tiếng Việt: script gọi `sys.stdout.reconfigure(encoding="utf-8")`.
- `.html`, `.css`, `.json` có thể là CRLF: thay chuỗi nhiều dòng bằng script dễ trượt; giữ kiểu xuống dòng.
- Dấu `"` trong chuỗi tiếng Việt của JSON locale phải thoát.
- Xử lý ảnh mặc định chạy ở **tiến trình con** (`isolated.py`); test đường đó ở `tests/draw_test/test_isolated.py`.
- FastAPI bọc router: liệt kê route bằng `app.openapi()["paths"]`, không dùng `app.routes`.
- `launcher/*.ps1`, `*.vbs`, `tools/dong_goi.ps1`: **ASCII không dấu** (PowerShell 5.1). Zip ghi tên tệp bằng `/`. Bản embeddable cần `..\backend` trong `python312._pth`.
- Thử launcher / cập nhật trong thư mục tạm, **kiểm cổng 8000 trống trước** (`stop.ps1` tắt mọi thứ nghe 8000).
- `str.replace` hàng loạt trên tệp Python có thể trượt im lặng: đọc lại đoạn đã sửa hoặc chạy test ngay.
- **Chỉnh thuật toán vẽ (rút từ 14/11/2026):** (1) đổi tông / mật độ → chạy `python tools/ink_sim.py` TRƯỚC khi báo xong, không chỉ nhìn ảnh thật (đường cong tông cho theo dáng trông ổn trên ảnh nhưng ink_sim báo đậm quá, đã phải gỡ); (2) tách nguyên nhân bằng dữ liệu giả đơn giản (ô phẳng mỗi ô một độ đậm) trước khi soi ảnh thật (lỗi cửa sổ vuông ở `flow.busy` lộ ngay ở ô phẳng); (3) so trước / sau với mã đã commit: `git archive <commit> backend/app tools | tar -x -C <thư mục tạm>` rồi chạy ở đó (`git stash` không đổi gì khi mã đã commit); (4) thử biến thể bằng script nháp đè hằng số (monkeypatch) trong thư mục tạm, chỉ sửa mã khi đã chọn; (5) phải nới ngưỡng test cho qua = dấu hiệu nghi thay đổi, không phải nghi test; (6) không gợi ý chỉnh ô cho chủ dự án khi chưa chạy thử; (7) xem ảnh so sánh: cắt đúng vùng, kích thước thật, ảnh ghép thu nhỏ không thấy gì.
- Đường dẫn Windows trong chuỗi Python / `sed`: `\r`, `\n`, `\t` thành ký tự điều khiển (đã làm `data\ra-soat-test.md` thành chữ có ký tự CR lạc trong tài liệu); viết `/` hoặc nhân đôi `\\`.
- Số tài liệu đổi 27/11/2026 (07 mạng + kết nối + triển khai gộp; 08 quyết định; 09 hướng; 10 Beta; 11 thử nghiệm; 12 việc cần làm): ghi chú cũ ở Git / bản ghi nhớ có thể còn số cũ.
- Sửa tay `locales/*.json`: kiểm `json.load` ngay sau khi sửa. Python Windows không thấy `/tmp` của Git Bash: ghi script vào thư mục tạm của phiên.

## 6. Xuất mã cho AI khác mà tiết kiệm token (`tools/export_context.py`, chỉ dùng thư viện chuẩn)
```
python tools/export_context.py --list                      # các gói + token ước tính
python tools/export_context.py docs                        # tài liệu cốt lõi cho AI
python tools/export_context.py draw-backend --budget 35000
python tools/export_context.py --files backend/app/services/job.py
python tools/export_context.py control --html panel-control   # thêm đúng một khối index.html
python tools/export_context.py --map                       # viết lại docs/AI_CODEMAP.md sau khi thêm / đổi tệp
```
Kết quả ở `export/` (gitignored). Chỉ lấy tệp Git đang theo dõi; bỏ tệp > 200 KB, ảnh, `.gcode`, `samples`, `fixtures`, `.vscode`. Token ≈ ký tự ÷ 3,2 (để so sánh).

| Việc | Gói | Token ~ |
|---|---|---|
| Làm quen | `docs` | ~12 000 |
| Chọn tệp cần đọc | `codemap` | ~5 000 |
| Tab Điều khiển (giao diện) | `docs control` | ~55 000 |
| Logic máy, hủy an toàn, chạy G-code | `docs machine-backend machine-facts` | ~45 000 |
| Thuật toán / tab vẽ backend | `docs algorithm draw-backend` (chỉ đọc thuật toán: `algorithm` ~15 000) | ~66 000 |
| Tab vẽ frontend | `docs draw-frontend` | ~57 000 |
| Cài đặt / cấu hình máy | `docs settings` | ~31 000 |
| CSS | `css` + `--html panel-<tab>` | ~29 000+ |
| Test | `tests-machine` hoặc `tests-draw` | ~26 000–29 000 mỗi gói |

Mẹo: đừng gửi cả `index.html` (~28 000 token), dùng `--html`; đừng gửi hai tệp dịch trừ khi sửa chữ; gửi `git diff` thay vì cả tệp khi nhờ xem lại; bắt AI trả lời bằng bản vá; mỗi phiên một khối. `--no-comments` giảm 5–10 % nhưng **mất lý do "vì sao"** (dự án ghi nhiều lý do trong chú thích). Thêm gói mới: sửa `BUNDLES` đầu `tools/export_context.py`.

Mẫu tin nhắn mở đầu cho AI mới:
```
Bạn nhận dự án VMU PlotterPen (máy vẽ CoreXY, MKS DLC32 + FluidNC; backend FastAPI, frontend JS thuần).
Đọc tệp đính kèm (AI_START, 03, 08, 12) rồi xác nhận: 1) các quy tắc an toàn không được nới, 2) cách chạy test, 3) khối nào ở đâu.
Chủ dự án không phải dân lập trình: lời thường, ngắn, tiếng Việt. Khi sửa, chỉ đưa đoạn thay đổi.
Việc hôm nay: <một việc cụ thể>. Cần tệp nào thì nói, tôi gửi đúng tệp đó.
```

## 7. Giữ tài liệu đúng
- Thêm / đổi tệp lớn → `python tools/export_context.py --map`.
- **Việc chưa làm chỉ có hai danh sách:** cần thử → `11` (đầu tệp); cần chọn / cần code → `12` mục 4. Việc đã xong chỉ ghi **từ khóa + hằng đã chốt** ở `12` mục 3 (đừng kể lại quá trình, lịch sử số nằm ở Git); quyết định bị thay thì sửa dòng cũ hoặc bỏ dòng đó ở `08` (mã số không dùng lại), thử rồi bỏ thì ghi một dòng ở `08`. Tên trên giao diện khác tên trong tài liệu (vd "Bỏ giới hạn" = ô "Chất lượng tối đa"): bảng ở `05` mục 3.
- Xong một việc → `12_VIEC_CAN_LAM.md`. Đổi hành vi đã chốt → `08_QUYET_DINH_THIET_KE.md`. Đổi API tab vẽ → `05_TAB_TAO_BAN_VE.md` mục 7 + `spec.py`. Đổi con số thuật toán → `06_THUAT_TOAN_XU_LY_ANH.md`. Số đo máy mới → `02_PHAN_CUNG_MAY.md`.
- **Tệp luật cho AI khác:** `CLAUDE.md` (Claude Code) và thư mục `.clinerules/` (Cline, các tệp 00–04) là bản rút gọn của mục 3–5 của tệp này. Đổi luật ở đây thì sửa cả hai nơi cho khớp; `AI_START.md` là bản gốc.
- Không tạo tệp tài liệu mới nếu nội dung thuộc một tệp đã có. Tệp mới cho người đọc thì đánh số; tệp chỉ cho AI thì đặt tiền tố `AI_` và ghi "FOR AI" ở dòng đầu.
