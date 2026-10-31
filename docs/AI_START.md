# AI_START — đọc tệp này đầu tiên

Dành cho AI (hoặc người) mới nhận dự án. Đọc xong tệp này (~2 000 token) là đủ để biết nên mở gì tiếp, không cần quét cả kho.

## 1. Dự án là gì
**VMU PlotterPen** (thư mục `ExtruXY`): phần mềm điều khiển máy vẽ CoreXY. Máy: bo **MKS DLC32 V2.1**, firmware **FluidNC v4.1.1**, nối USB (CH340); vùng làm việc **285 × 318 mm**, Z bút 5 mm, giấy A6 ⊂ A5 ⊂ A4 đặt ở gốc O(0,0) trên trái, Y hướng xuống. Phần mềm = backend **Python/FastAPI** + frontend **JS thuần** (không framework, không bước build). Hiện chạy trên laptop (bản mang đi Windows: `DONG_GOI.md`); kế hoạch chạy trên MiniPC Ubuntu không màn hình bằng Docker (xem `PLAN_ONLINE.md`). Dữ liệu người dùng ở `data/` cùng cấp `backend/`.

Ba tab: **Điều khiển** (kết nối, jog, Home, chạy G-code, hủy an toàn, terminal, hàng đợi), **Tạo bản vẽ** (SVG/ảnh → nét → bố trí → G-code → bản thảo), **Cài đặt**.

## 2. Thứ tự đọc
| Bước | Tệp | Khi nào |
|---|---|---|
| 1 | `docs/AI_START.md` (tệp này) | luôn |
| 2 | `docs/STATUS.md` | muốn biết cái gì xong / chưa / chưa kiểm chứng |
| 3 | `docs/ARCHITECTURE.md` | cần biết khối nào nằm ở đâu, quy tắc phụ thuộc, biến môi trường |
| 4 | `docs/CODEMAP.md` | tìm tệp theo vai trò + token ước tính (sinh tự động) |
| 5 | `docs/DECISIONS.md` | trước khi đổi một hành vi đã chốt |
| 6 | `docs/MACHINE.md` | đụng vào phần cứng, giao thức, an toàn |
| 7 | `docs/DRAW_ROADMAP.md` | sửa tab Tạo bản vẽ (hợp đồng API, quyết định thiết kế) |
| 8 | `docs/BRIEF.md` | cần hiểu từng nút bấm / luồng người dùng |
| 9 | `docs/PLAN_ONLINE.md` | làm phần phân quyền PIN, giới hạn, MiniPC Ubuntu (Docker), IP, Cloudflare Tunnel |
| 10 | `docs/DONG_GOI.md` | bản mang đi Windows (`Python/` embeddable, `launcher/`), chuyển máy, `Cap nhat.bat` |
| 11 | `docs/KIEM_TRA_VE.md` | tinh chỉnh kiểu tô / nét viền / preset bằng bản in thật |

**Nếu mã khác tài liệu thì mã mới là sự thật**; sửa tài liệu cho khớp.

## 3. Lấy mã mà không tốn token
Đừng dán cả kho (~266 000 token). Dùng `python tools/export_context.py`:
```
python tools/export_context.py --list                     # các gói + token
python tools/export_context.py docs                       # tài liệu cốt lõi
python tools/export_context.py draw-backend --budget 35000
python tools/export_context.py --files backend/app/services/job.py
```
Quy trình chi tiết, bảng "việc nào lấy gói nào", mẹo giảm token: `docs/EXPORT_FOR_AI.md`.

## 4. Quy tắc bắt buộc (không thương lượng)
1. **An toàn máy trước hết.** Máy thật mặc định chỉ đọc (`motion_locked`); không bao giờ tự chạy G-code, luôn qua xem trước + người dùng xác nhận; tab Tạo bản vẽ **không bao giờ gọi máy**, chỉ ghi bản thảo; nút web không phải dừng khẩn cấp. Đừng nới các chốt này nếu chưa có yêu cầu rõ.
2. **Frontend không chạm cổng serial.** Chỉ backend giữ serial. Frontend chỉ gọi API (`core/api.js` là nơi duy nhất gọi mạng, `core/state.js` là nơi duy nhất thăm dò).
3. **Chiều phụ thuộc frontend:** `views → stores → lib`, mọi tầng → `core`. View không import view khác. Một phần tử HTML chỉ một nơi ghi.
4. **Một nguồn sự thật cho tham số vẽ:** `backend/app/services/drawing/spec.py` (frontend lấy qua `GET /api/draw/schema`). Đổi tham số = sửa đúng một dòng ở đó + ô tương ứng trong `index.html`/`params.js` + khóa dịch.
5. **Dịch:** mọi chữ qua `frontend/locales/vi.json` và `en.json`, hai tệp phải khớp khóa. Terminal giữ tiếng Anh. Mã lỗi backend `DrawError.code` ↔ khóa `drawing.error.<code>`.
6. **Test đi cùng mã.** Backend: `cd backend && python -m pytest` (~361 test; `tests/conftest.py` đưa mọi dữ liệu vào thư mục tạm). Frontend: `node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs frontend/tests/gcode.test.mjs`. Công thức bố trí và độ sáng có bản JS song song, được test đối chiếu số với Python; nếu đổi `layout.py` / `tone.py` / `raster_in.py` thì sinh lại số chuẩn (`python frontend/tests/fixtures/make_image_fixtures.py`) và sửa bản JS.
7. **Không bịa số máy.** Giới hạn phần cứng lấy từ `MACHINE` (`core/config.js`) hoặc hồ sơ máy; ghi rõ điều gì **chưa kiểm chứng** trên máy thật.
8. **Báo trung thực:** test nào fail, bước nào bỏ qua, điều gì chưa chạy thử trên Ubuntu/máy thật.

## 5. Quy ước làm việc với chủ dự án
- Chủ dự án không phải dân lập trình: **giải thích bằng lời thường** trước khi đưa chi tiết kỹ thuật; thư viện và cơ chế mới phải giải thích rõ.
- Trả lời ngắn gọn, đi thẳng vào việc, dùng bảng khi so sánh. Tiếng Việt.
- Chủ dự án tự `git push`. Chỉ commit khi được bảo; mỗi commit một việc, tiếng Việt.
- Không tự đổi `tokens.css`/giao diện lớn mà chưa hỏi; phần CSS chủ dự án đã sửa tay thì giữ nguyên.

## 6. Bẫy đã gặp (tiết kiệm thời gian)
- Python **3.12** (3.15 quá mới, thiếu gói cài sẵn). Windows: `node --test` nhận **đường dẫn tệp**, không nhận thư mục.
- Tệp `.html`, `.css`, `.json` có thể là CRLF: khi sửa bằng script phải giữ kiểu xuống dòng; một lần thay chuỗi nhiều dòng trượt vì CRLF.
- Số liệu tiếng Việt trong JSON locale: dấu `"` phải thoát, đừng dán trực tiếp.
- Chế độ mặc định xử lý ảnh chạy ở **tiến trình con** (`isolated.py`); test đặt `EXTRUXY_DRAW_INPROC=1` trong `conftest.py`. Muốn test đường tiến trình con dùng `tests/draw_test/test_isolated.py`.
- Trên Windows, dừng server thử bằng cách tắt tiến trình đang nghe cổng, kiểm bằng `curl` thấy mã 000.
- FastAPI bọc router; liệt kê route bằng `app.openapi()["paths"]`, không dùng `app.routes`.
- `launcher/*.ps1`, `*.vbs`, `tools/dong_goi.ps1`: viết **ASCII không dấu** (PowerShell 5.1 đọc UTF-8 không BOM sai). Zip phải ghi tên tệp bằng `/` (`Compress-Archive` 5.1 ghi `\`). Bản embeddable cần `..\backend` trong `python312._pth`.
- Chạy thử launcher/cập nhật: làm trong thư mục tạm, **kiểm cổng 8000 trống trước** (`stop.ps1` tắt mọi thứ đang nghe 8000).
- `.vscode/project-export.json` là tệp sinh bởi tiện ích VS Code (liệt kê hàng nghìn đường dẫn loại trừ), **đừng đưa cho AI**.
