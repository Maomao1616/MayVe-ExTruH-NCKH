# EXPORT_FOR_AI — đưa mã cho AI mà tiết kiệm token

Cả dự án khoảng **266 000 token** nếu dán hết. Không cần: mỗi việc chỉ cần 10 000–40 000 token nếu chọn đúng. Công cụ `tools/export_context.py` (chỉ dùng thư viện chuẩn của Python, không cần bật venv) gom đúng phần cần thành **một tệp markdown**.

## 1. Bắt đầu nhanh
Từ thư mục gốc dự án:
```powershell
python tools/export_context.py --list                  # các gói + token ước tính
python tools/export_context.py docs                    # tài liệu cốt lõi (~8 500 token)
python tools/export_context.py control                 # ghi export/control-<ngày>.md
python tools/export_context.py draw-backend draw-frontend --budget 60000
python tools/export_context.py --files backend/app/services/job.py frontend/js/views/control.js
python tools/export_context.py --map                   # viết lại docs/CODEMAP.md sau khi thêm/đổi tệp
```
Kết quả nằm ở `export/` (đã được `.gitignore`). Mở tệp, copy toàn bộ, dán vào AI (hoặc đính kèm). Công cụ in số token ước tính; `--budget N` cảnh báo nếu vượt.

## 2. Việc nào lấy gói nào
| Việc | Lấy | Token ước tính |
|---|---|---|
| Làm quen dự án (AI mới) | `docs` | ~8 500 |
| Chọn tệp cần đọc | `codemap` (thêm vào `docs` nếu muốn) | ~3 700 |
| Sửa tab Điều khiển (jog, tệp G-code, khung 2D, terminal) | `docs control` | ~45 000 |
| Sửa logic máy / hủy an toàn / chạy G-code | `docs machine-backend machine-facts` | ~38 000 |
| Sửa tab Tạo bản vẽ phía backend (ảnh, kiểu tô, G-code, bản thảo) | `docs draw-backend machine-facts` | ~46 000 |
| Sửa tab Tạo bản vẽ phía frontend | `docs draw-frontend` | ~45 000 |
| Sửa Cài đặt / cấu hình máy | `docs settings` | ~27 000 |
| Chỉnh giao diện CSS | `css` + `--html panel-<tab>` | ~25 000 |
| Sửa chữ hiển thị | chỉ `--files` đúng khóa cần; `i18n` là gói rất lớn (~22 000) | |
| Viết/sửa test | `tests-machine` hoặc `tests-draw` | ~19 000 mỗi gói |
| Chỉnh máy giả | `sim` | ~8 000 |
| Phân quyền, mở ra mạng | `docs machine-backend` + `--files docs/PLAN_ONLINE.md` | ~34 000 |

Con số thật xem `--list` (gói thay đổi theo mã). Một việc nhỏ (sửa một hàm) thường chỉ cần `docs` + **một** tệp bằng `--files`.

## 3. Mẹo giảm token (xếp theo hiệu quả)
1. **Đừng gửi `index.html` nguyên cái** (~24 000 token). Dùng `--html panel-control` / `panel-drawing` / `panel-settings`: chỉ lấy khối của một tab (gói `control`, `draw-frontend`, `settings` đã tự thêm).
2. **Đừng gửi hai tệp dịch** trừ khi sửa chữ. Chỉ cần nói "khóa `drawing.xxx` trong vi.json/en.json".
3. **Đọc bản đồ trước, mã sau:** `docs/CODEMAP.md` cho biết tệp nào làm gì và nặng bao nhiêu; AI chọn tệp, bạn chỉ xuất tệp đó (`--files`).
4. **Gửi thay đổi thay vì cả tệp** khi nhờ xem lại: `git diff -U2 -- đường/dẫn` hoặc `git diff --stat` rồi chỉ diff cần xem.
5. **Bắt AI trả lời bằng bản vá:** yêu cầu "chỉ đưa đoạn thay đổi (hàm/đoạn đầy đủ hoặc diff), không in lại cả tệp".
6. **Chia việc nhỏ, mỗi phiên một khối** (một tab, một lớp). Đừng gom nhiều khối không liên quan vào một phiên.
7. **Đặt tài liệu ổn định ở đầu** (`docs` trước), phần thay đổi ở cuối: nhiều dịch vụ tính rẻ hơn khi phần đầu lặp lại giữa các lần hỏi.
8. `--no-comments` bỏ các dòng chú thích nguyên dòng, giảm 5–10% nhưng **mất lý do vì sao** (dự án này ghi rất nhiều "vì sao" trong chú thích). Chỉ dùng khi thiếu token.
9. Tránh gửi: `.vscode/project-export.json` (tệp sinh bởi tiện ích, ~90 000 token toàn đường dẫn loại trừ), `backend/.venv`, `backend/data`, `export/`, ảnh.

## 4. Mẫu tin nhắn mở đầu cho AI mới
```
Bạn nhận dự án VMU PlotterPen (điều khiển máy vẽ CoreXY, MKS DLC32 + FluidNC; backend FastAPI, frontend JS thuần).
Đọc tệp đính kèm (docs: AI_START, ARCHITECTURE, STATUS, DECISIONS) rồi xác nhận bạn hiểu:
1) các quy tắc an toàn không được nới, 2) cách chạy test, 3) khối nào ở đâu.
Chủ dự án không phải dân lập trình: giải thích bằng lời thường, trả lời ngắn, tiếng Việt. Khi sửa, chỉ đưa đoạn thay đổi.
Việc hôm nay: <mô tả một việc cụ thể>. Nếu cần mã, nói rõ tệp nào, tôi sẽ gửi đúng tệp đó.
```
Sau đó gửi tiếp gói theo bảng ở mục 2.

## 5. Giữ tài liệu luôn đúng
- Thêm/đổi tệp lớn → `python tools/export_context.py --map` (CODEMAP.md sinh từ mã, không sửa tay).
- Xong một việc → sửa `docs/STATUS.md` (xong / chưa kiểm chứng / còn lại); đổi một hành vi đã chốt → `docs/DECISIONS.md`.
- Đổi hợp đồng API tab vẽ → `docs/DRAW_ROADMAP.md` mục 3 và `spec.py`.
- Đổi công thức có bản JS song song (`layout.py` ↔ `paper.js`, `tone.py`/`raster_in.py` ↔ `imageprep.js`): sinh lại số chuẩn rồi chạy cả test Python và JS.
- Muốn thêm gói xuất mới: sửa từ điển `BUNDLES` đầu `tools/export_context.py` (một mục: mô tả, mẫu tệp, khối html).

## 6. Giới hạn của công cụ
- Chỉ lấy tệp Git đang theo dõi (tệp mới phải `git add` hoặc chỉ định đích danh bằng `--files`); bỏ tệp > 200 KB, ảnh, `.gcode`, thư mục `samples`, `fixtures`, `.vscode`.
- Token là ước lượng (ký tự ÷ 3,2), tiếng Việt thường tốn nhiều hơn tiếng Anh một chút; dùng để so sánh gói, đừng coi là số chính xác.
- Khối `index.html` cắt theo thẻ `<section id="…">`; hộp thoại ở cuối trang không thuộc khối nào (lấy bằng `--files frontend/index.html` nếu cần, rất nặng).
