# AI_START — FOR AI (tài liệu chỉ dành cho AI, người đọc xem `01_TONG_QUAN.md`)

Đọc tệp này đầu tiên khi nhận dự án. ~2 500 token. Xong thì mở đúng tệp cần, đừng quét cả kho (~380 000 token).

## 1. Dự án
**VMU PlotterPen** (thư mục `ExtruXY`): phần mềm điều khiển máy vẽ bút CoreXY. Mạch **MKS DLC32 V2.1**, firmware **FluidNC v4.1.1** (không sửa), nối USB (CH340, 115200). Vùng làm việc **285 × 318 mm**, Z bút 5 mm (servo, bút hạ bằng trọng lực). Giấy A6 ⊂ A5 ⊂ A4 neo ở O(0,0) góc trên trái, Y xuống. **Hướng trục đã xác nhận đúng 05/11/2026** (`VIEW.flipX/flipY = false`, `invert_y = false`).
Backend **Python 3.12 / FastAPI**; frontend **JS thuần** (không framework, không build). Chạy trên laptop (bản mang đi Windows); kế hoạch MiniPC Ubuntu + Docker + Cloudflare Tunnel. Dữ liệu ở `data/` cùng cấp `backend/`.
Bút: Sakura 0,4 / Uniball 150 trên giấy Ivory 250 g/m² (tranh; từ 11/11/2026 ô "Bút vẽ" chọn theo tên bút và ghi thẳng nét đo trên giấy: đo 12/11/2026: UB-155 0,38, UM-100 0,40, Sakura 0,50 (mặt nhám 0,55: Tùy chọn); `LINE_WIDTH_RATIO` 1,0; giấy thường từng loang ra 0,55), bút bi 0,5 (chữ, Word cỡ 14–16). Mặc định vẽ / di chuyển 8000 mm/min, Z3 / Z0, chờ 0,02 s, hạ bút 2000, nối nét gần bật, vẽ lần lượt từng mức tắt; máy thật đang chạy tối đa 8000 (10000 được ở đoạn dài), gia tốc 3000 (không tăng: sợ gãy ngòi), junction 0,05, SpreadCycle.
Chủ dự án: sinh viên điện tử, **không phải lập trình viên**, đề tài cấp trường, mục tiêu sản phẩm IoT chạy thật, demo **không cần Internet**.

## 2. Tài liệu
| Tệp | Mở khi |
|---|---|
| `docs/11_VIEC_CAN_LAM.md` | biết cái gì xong / chưa kiểm chứng / việc tiếp |
| `docs/AI_CODEMAP.md` | tìm tệp theo vai trò + token, danh sách route (sinh tự động, không sửa tay) |
| `docs/03_CAU_TRUC_PHAN_MEM.md` | tầng frontend / backend, quy tắc phụ thuộc, dữ liệu, biến môi trường |
| `docs/04_TAB_DIEU_KHIEN.md` | sửa điều khiển máy, chạy G-code, dừng an toàn, tiếp tục |
| `docs/05_TAB_TAO_BAN_VE.md` | sửa tab vẽ: luồng, tham số, **hợp đồng API** |
| `docs/06_THUAT_TOAN_XU_LY_ANH.md` | sửa thuật toán ảnh → nét (con số, công thức, thư viện đã loại) |
| `docs/02_PHAN_CUNG_MAY.md` | đụng phần cứng, giao thức, hành vi firmware đã xác nhận |
| `docs/09_QUYET_DINH_THIET_KE.md` | **trước khi đổi một hành vi đã chốt** |
| `docs/07_THU_NGHIEM.md` · `08_TRIEN_KHAI.md` · `10_HUONG_PHAT_TRIEN.md` | thử trên giấy · đóng gói / phân quyền / mạng / MiniPC · ý tưởng để dành |

**Mã khác tài liệu thì mã là sự thật**; sửa tài liệu cho khớp. Tài liệu 01–11 viết cho **người không học code**: giữ văn phong đó khi sửa (lời thường, khối rõ, từ nhỏ đến lớn, bảng).

## 3. Quy tắc bắt buộc
1. **An toàn máy trước hết.** Máy thật mặc định chỉ đọc (`allow_motion`); không bao giờ tự chạy G-code, luôn qua xem trước + xác nhận; tab vẽ **không bao giờ gọi máy**; nút web không phải dừng khẩn cấp. Không nới các chốt này nếu chưa được yêu cầu rõ.
2. **Frontend không chạm serial.** `core/api.js` là nơi duy nhất gọi mạng, `core/state.js` là nơi duy nhất thăm dò.
3. **Phụ thuộc frontend:** `views → stores → lib`, mọi tầng → `core`. View không import view khác (trừ `control.js` → `preview.js`). Một phần tử HTML chỉ một chủ ghi.
4. **Một nguồn sự thật cho tham số vẽ:** `backend/app/services/drawing/spec.py` (frontend lấy qua `GET /api/draw/schema`). Thêm tham số = dòng `Param` + ô `index.html` + dòng `FIELDS` trong `views/drawing/params.js` + khóa dịch.
5. **Dịch:** mọi chữ qua `frontend/locales/vi.json` và `en.json`, hai tệp cùng khóa. Terminal giữ tiếng Anh. `DrawError.code` ↔ khóa `drawing.error.<code>`.
6. **Test đi cùng mã.** `cd backend && python -m pytest` (~500; `tests/conftest.py` đưa dữ liệu vào thư mục tạm, đặt `EXTRUXY_DRAW_INPROC=1`; `test_old_logs_are_pruned` có thể hết giờ khi chạy chung, chạy riêng thì qua). Frontend: `node --test` kèm từng tệp `frontend/tests/*.mjs` (39). Đổi `layout.py` / `tone.py` / `raster_in.py` thì sinh lại số chuẩn (`python frontend/tests/fixtures/make_image_fixtures.py`) và sửa bản JS (`paper.js`, `imageprep.js`).
7. **Không bịa số máy.** Lấy từ `MACHINE` (`core/config.js`), hồ sơ máy, hoặc `02_PHAN_CUNG_MAY.md`; ghi rõ điều chưa kiểm chứng.
8. **Route API mới mặc định chỉ quản lý** (`app/auth.py`, `GUEST_ROUTES`). Thêm route cho khách = một dòng trong danh sách đó **và** sửa `tests/test_auth.py`. Frontend chỉ ẩn nút (`body.role-guest`), không phải bảo mật.
9. **Thuật toán tô:** đánh giá thay đổi bằng `tools/ink_sim.py` (sai số tông, chiều dài, thời gian) trước khi đề xuất; nêu số trước / sau.
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
Đọc tệp đính kèm (AI_START, 03, 09, 11) rồi xác nhận: 1) các quy tắc an toàn không được nới, 2) cách chạy test, 3) khối nào ở đâu.
Chủ dự án không phải dân lập trình: lời thường, ngắn, tiếng Việt. Khi sửa, chỉ đưa đoạn thay đổi.
Việc hôm nay: <một việc cụ thể>. Cần tệp nào thì nói, tôi gửi đúng tệp đó.
```

## 7. Giữ tài liệu đúng
- Thêm / đổi tệp lớn → `python tools/export_context.py --map`.
- Xong một việc → `11_VIEC_CAN_LAM.md`. Đổi hành vi đã chốt → `09_QUYET_DINH_THIET_KE.md`. Đổi API tab vẽ → `05_TAB_TAO_BAN_VE.md` mục 7 + `spec.py`. Đổi con số thuật toán → `06_THUAT_TOAN_XU_LY_ANH.md`. Số đo máy mới → `02_PHAN_CUNG_MAY.md`.
- **Tệp luật cho AI khác:** `CLAUDE.md` (Claude Code) và thư mục `.clinerules/` (Cline, các tệp 00–04) là bản rút gọn của mục 3–5 của tệp này. Đổi luật ở đây thì sửa cả hai nơi cho khớp; `AI_START.md` là bản gốc.
- Không tạo tệp tài liệu mới nếu nội dung thuộc một tệp đã có. Tệp mới cho người đọc thì đánh số; tệp chỉ cho AI thì đặt tiền tố `AI_` và ghi "FOR AI" ở dòng đầu.
