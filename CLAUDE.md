# CLAUDE.md — luật làm việc của dự án VMU PlotterPen (ExtruXY)

Máy vẽ bút CoreXY (mạch MKS DLC32 + firmware FluidNC 4.1.1, không sửa firmware). Backend Python 3.12 / FastAPI, frontend JS thuần (không framework, không bước build). Chủ dự án là sinh viên điện tử, **không phải lập trình viên**.

**Việc đầu tiên mỗi phiên:** đọc `docs/AI_START.md` (~2 500 token, là nguồn chi tiết của mọi luật dưới đây), rồi `docs/11_VIEC_CAN_LAM.md` để biết đang làm tới đâu. Tìm tệp cần sửa bằng `docs/AI_CODEMAP.md`, **đừng quét cả kho** (~380 000 token). Các tệp luật này (`CLAUDE.md`, `.clinerules/`) chỉ là bản rút gọn; mâu thuẫn thì `AI_START.md` và mã thắng.

## Cây thư mục: không đổi, không tạo tầng mới
```
docs/        tài liệu 01–11 (người đọc, đánh số) + AI_* (chỉ cho AI)
frontend/    index.html · css/ · locales/{vi,en}.json · js/{core,lib,stores,views}/ · tests/
backend/     app/{api,links,services,auth.py,main.py} · tests/ · tests/draw_test/
tools/       export_context.py · ink_sim.py · make_test_gcode.py · dong_goi.ps1
launcher/    bật / tắt bằng icon (Windows)        data/  (không lên Git) bản thảo, hồ sơ, PIN
```
- Frontend phụ thuộc một chiều: `views → stores → lib`, mọi tầng → `core`. View không import view khác (trừ `control.js → preview.js`). Mỗi phần tử HTML có **một** chủ ghi.
- Chỉ `core/api.js` gọi mạng, chỉ `core/state.js` thăm dò. Frontend không chạm serial.
- Tham số vẽ có **một** nguồn: `backend/app/services/drawing/spec.py`. Thêm tham số = dòng `Param` + ô `index.html` + dòng `FIELDS` trong `views/drawing/params.js` + khóa dịch vi/en.
- Con số của thuật toán là hằng số HOA ở đầu tệp Python, có chú thích tiếng Việt (vd `LINE_WIDTH_RATIO` trong `styles.py`).
- Thêm kiểu tô = hàm `@FILLERS.register("tên")` + `spec.STYLES` + `GROUPERS` (không sửa `registry.py`).

## An toàn máy (không nới nếu chủ dự án chưa yêu cầu rõ)
1. Máy thật mặc định **chỉ đọc**; không tự chạy G-code (người bấm ▶ Chạy; bước bắt buộc Xem trước + tích xác nhận đã ẩn từ 12/11/2026 theo yêu cầu chủ dự án, `REQUIRE_PREVIEW_CONFIRM` ở `views/control.js`). Tab Tạo bản vẽ **không bao giờ gọi máy**. Nút web không phải dừng khẩn cấp.
2. Route API mới mặc định **chỉ quản lý** (`app/auth.py`, `GUEST_ROUTES`); thêm route cho khách = một dòng ở đó **và** sửa `tests/test_auth.py`.
3. **PIN thật không bao giờ vào Git, tài liệu, hay câu trả lời**: nằm ở `data\pin.txt` (gitignored). Chỉ nhắc tên khóa (`admin`, `unlock`).
4. Không bịa số máy: lấy từ `MACHINE` (`core/config.js`), hồ sơ máy, hoặc `docs/02_PHAN_CUNG_MAY.md`; điều chưa đo thì ghi "chưa kiểm chứng".

## Cách làm một việc
1. Đọc đúng tài liệu liên quan (bảng ở `AI_START.md` mục 2). **Trước khi đổi hành vi đã chốt: đọc `docs/09_QUYET_DINH_THIET_KE.md`.**
2. Sửa mã **và test cùng lúc**. Chạy: `cd backend && python -m pytest` (~500 test; riêng `test_old_logs_are_pruned` có thể hết giờ khi chạy chung, chạy riêng thì qua) và `node --test <các tệp trong frontend/tests/*.mjs>` (Windows: truyền **đường dẫn tệp**, không truyền thư mục).
3. Đổi thuật toán tô: đo bằng `python tools/ink_sim.py`, nêu số trước / sau. Đổi `layout.py` / `tone.py` / `raster_in.py`: sinh lại số chuẩn (`python frontend/tests/fixtures/make_image_fixtures.py`) và sửa bản JS.
4. Cập nhật tài liệu đúng chỗ: xong việc → `11`; đổi hành vi đã chốt → `09`; API tab vẽ → `05` mục 7 + `spec.py`; con số thuật toán → `06`; số đo máy → `02`; thêm / đổi tệp lớn → `python tools/export_context.py --map`. **Không tạo tệp tài liệu mới** nếu nội dung thuộc tệp đã có.
5. Chữ hiển thị: mọi chuỗi qua `frontend/locales/vi.json` và `en.json` (cùng khóa; `"` trong tiếng Việt phải thoát). `DrawError.code` ↔ khóa `drawing.error.<code>`. Terminal giữ tiếng Anh.
6. Báo trung thực: test fail, bước bỏ qua, điều chưa thử trên máy thật / giấy / Ubuntu.

## Git
- **Chỉ commit khi chủ dự án bảo** ("commit"). Không `git push` (chủ dự án tự push). Mỗi commit một việc, message tiếng Việt, kết thúc bằng dòng `Co-Authored-By` của AI đang làm.
- Không dùng `--no-verify`, không `reset --hard` / `push --force`.
- Không tự đổi `frontend/assets/css/tokens.css` hay giao diện lớn khi chưa hỏi; giữ nguyên CSS chủ dự án sửa tay.
- Không đưa vào Git: `data/`, `export/`, `Python/`, `.venv/`, `*.gcode` ở gốc.

## Giao tiếp với chủ dự án
- **Tiếng Việt, lời thường trước, kỹ thuật sau.** Thư viện / cơ chế mới phải giải thích. Ngắn, thẳng, dùng bảng khi so sánh. Chỉ đưa đoạn thay đổi, không dán lại cả tệp.
- Tài liệu 01–11 viết cho người không học code: giữ văn phong (lời thường, khối rõ, từ nhỏ đến lớn, bảng).
- Báo kèm: lỗi / tối ưu tìm thấy trong lúc làm, tiến độ, và những bài thử còn phải làm.
- Chủ dự án thử trên giấy rồi gửi ảnh và số; AI sửa mã và tài liệu theo đó. Nêu số trước / sau khi đề xuất đổi.
- Thông số bút hiện tại (từ 11/11/2026): Sakura 0,4 / Uniball 150, giấy Ivory 250 g/m², ô "Bút vẽ" chọn theo tên bút, ghi thẳng nét đo trên giấy (đo 12/11/2026: UB-155 0,38, UM-100 0,40, Sakura 0,50; `LINE_WIDTH_RATIO` = 1,0); vẽ 8000, gia tốc 3000, Z3, chờ 0,02; chữ dùng bút bi 0,5, Word cỡ 14–16.

## Bẫy đã gặp (chi tiết ở `AI_START.md` mục 5)
- Python **3.12** (3.15 thiếu gói). Console Windows cp1252 không in được tiếng Việt: script gọi `sys.stdout.reconfigure(encoding="utf-8")`.
- `.html/.css/.json` có thể là CRLF; sửa tệp bằng công cụ sửa tệp (Edit/Write), không dùng `sed` / heredoc / PowerShell `Set-Content` (dễ chèn BOM hoặc làm trượt chuỗi).
- `launcher/*.ps1`, `*.vbs`, `tools/dong_goi.ps1`: **ASCII không dấu**.
- Backend cũ có thể còn chạy sau khi sửa mã: nhắc chủ dự án khởi động lại phần mềm.
- Xử lý ảnh chạy ở tiến trình con (`isolated.py`); test đường đó ở `tests/draw_test/test_isolated.py`.
