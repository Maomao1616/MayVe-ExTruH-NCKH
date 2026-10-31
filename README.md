# VMU PlotterPen (ExtruXY) — phần mềm điều khiển máy vẽ

Phần mềm điều khiển máy vẽ CoreXY (vùng làm việc 285 × 318 mm, giấy A6/A5/A4), chạy trên laptop và nối với bo mạch **MKS DLC32 V2.1** chạy firmware **FluidNC v4.1.1** qua cáp USB (CH340). Không sửa firmware; dùng giao thức có sẵn của FluidNC.

- **Tab Điều khiển:** kết nối, trạng thái, jog, Home/Zero, bút lên xuống, nạp + xem trước + chạy G-code, hủy an toàn, tiếp tục tác vụ đã dừng, terminal, macro, tệp nhanh (bản thảo ghim), hàng đợi công việc.
- **Tab Tạo bản vẽ:** nạp SVG hoặc ảnh → tạo nét (zigzag, sóng, xoắn ốc, viền; đơn sắc hoặc 2–4 màu) → bố trí lên giấy → G-code → lưu bản thảo → chuyển sang Điều khiển.
- **Tab Cài đặt:** kết nối, hoạt động, thư mục bản thảo, cấu hình máy (đọc/ghi YAML trên mạch), hồ sơ phần mềm.

```
Trình duyệt (frontend JS thuần) ⇄ HTTP API ⇄ Backend Python (FastAPI) ⇄ SimLink (máy giả)  hoặc  SerialLink → MKS DLC32 → FluidNC
```
Frontend không bao giờ chạm cổng serial; backend là nguồn sự thật. Máy thật **mặc định chỉ đọc** cho tới khi mở khóa chuyển động. Tab Tạo bản vẽ **không bao giờ gọi máy**.

## Cài đặt và chạy
Cần **Python 3.12** (3.15 quá mới, thiếu gói cài sẵn) và **Git**. Windows PowerShell:
```powershell
git clone <địa-chỉ-kho>
cd <thư-mục-kho>\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
uvicorn app.main:app --reload
```
Mở `http://127.0.0.1:8000/`. Máy dùng hằng ngày không cần venv: xem **Bản mang đi** bên dưới.
- PowerShell báo "running scripts is disabled": `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` rồi bật lại venv.
- Linux (Ubuntu): `python3.12 -m venv .venv && source .venv/bin/activate`, các lệnh còn lại giống nhau (**chưa thử trên Ubuntu thật**; xem `docs/PLAN_ONLINE.md`).
- Chưa có board? Chọn chế độ `sim` ở Cài đặt → Kết nối (máy giả bắt chước FluidNC theo log board thật).
- Sau khi cập nhật mã có thêm thư viện: chạy lại `pip install -r requirements.txt`.

## Bản mang đi (máy không cài Python)
```
ExtruXY/
├─ Python/          Python 3.12 embeddable 64-bit + thư viện (chuẩn bị một lần, không lên Git)
├─ backend/  frontend/
├─ launcher/        start.vbs · start.ps1 · stop.vbs · stop.ps1 · tao_bieu_tuong.vbs · cap_nhat.ps1 · icon.ico
├─ data/            bản thảo, macro, sao lưu (tự tạo; cập nhật không đụng tới)
└─ Cap nhat.bat
```
**Chuẩn bị `Python/` (một lần, trên máy của bạn):**
1. Tải *Windows embeddable package (64-bit)* Python 3.12.x ở python.org, giải nén vào `Python/`.
2. Sửa `Python/python312._pth` thành 4 dòng: `python312.zip`, `.`, `..\backend`, `import site`. Dòng `..\backend` bắt buộc: bản embeddable bỏ qua thư mục hiện hành và `PYTHONPATH`, thiếu nó thì tiến trình con xử lý ảnh (`python -m app.services.drawing.isolated`) không chạy.
3. Tải `get-pip.py`, chạy `Python\python.exe get-pip.py`, rồi `Python\python.exe -m pip install -r backend\requirements.txt`.
4. Đóng gói: `powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1 -Kieu daydu` → `export\VMU_PlotterPen_daydu-<ngày>.zip`.

**Máy dùng:** giải nén → bấm đúp `launcher\tao_bieu_tuong.vbs` (một lần, tạo icon *VMU PlotterPen* ngoài Desktop) → bấm icon. Server chạy ẩn, trình duyệt mở `http://<IP LAN>:8000`. **Không cần icon tắt:** đóng hết trang 10 phút thì server tự tắt (đang vẽ thì không); muốn tắt ngay: `launcher\stop.vbs`. Lần đầu Windows hỏi tường lửa cho `python.exe`: chọn *Mạng riêng tư*. Server không lên: xem `data\server-loi.txt`.
- Mở cho máy khác cùng mạng (`0.0.0.0`) mà **chưa có đăng nhập**: chỉ dùng mạng tin cậy và đặt PIN (bỏ `#` dòng `EXTRUXY_UNLOCK_PIN` trong `launcher\start.ps1`).

**Cập nhật (chỉ thay `backend/`, `frontend/`, `launcher/`):** trên máy bạn `powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1` → `export\VMU_PlotterPen_capnhat-<ngày>.zip` (vài trăm KB). Ở máy dùng: chép file zip vào cạnh `Cap nhat.bat` → bấm đúp. Nó tắt server, thay mã, giữ `Python/` + `data/`, cất bản cũ và file zip vào `_ban_cu/`; `requirements.txt` đổi thì tự `pip install` (cần Internet).

## Kiểm tra
| Việc | Lệnh |
|---|---|
| Test backend (~326 test) | trong `backend`, đã bật venv: `python -m pytest` |
| Test frontend | từ thư mục gốc: `node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs frontend/tests/gcode.test.mjs` |
| Thử API bằng tay | `http://127.0.0.1:8000/docs` |

## Máy thật: dùng thế nào cho an toàn
- Cắm USB, chọn cổng ở Cài đặt → Kết nối. Ở chế độ chỉ đọc bạn chỉ xem được trạng thái và gửi lệnh đọc thông tin.
- Muốn máy chuyển động: bấm **Mở khóa chuyển động** (tự khóa lại sau 15 phút; có thể đặt PIN). Chỉ mở khi có người đứng cạnh, tay gần công tắc nguồn.
- Nút Reset/Dừng trên web **không phải dừng khẩn cấp**. Dừng khẩn cấp thật là công tắc cắt nguồn 12 V ở máy.
- Backend chỉ nhận yêu cầu từ máy chạy nó (`localhost`) và **chưa có đăng nhập**. Đừng mở ra mạng trước khi làm xong phân quyền (`docs/PLAN_ONLINE.md`).

## Tài liệu
| Tệp | Để làm gì |
|---|---|
| [docs/AI_START.md](docs/AI_START.md) | **Đọc đầu tiên** (dành cho AI/người mới): tóm tắt, quy tắc bắt buộc, bẫy đã gặp |
| [docs/STATUS.md](docs/STATUS.md) | Cái gì xong / chưa / chưa kiểm chứng / còn lại |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Kiến trúc, bản đồ khối, luồng dữ liệu, biến môi trường, chốt an toàn |
| [docs/CODEMAP.md](docs/CODEMAP.md) | Bản đồ mã nguồn sinh tự động (route API, vai trò + token từng tệp) |
| [docs/BRIEF.md](docs/BRIEF.md) | Giải thích khối chức năng và từng nút bấm |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Sổ quyết định (chọn gì, vì sao, mức chắc) |
| [docs/MACHINE.md](docs/MACHINE.md) | Sự thật máy thật đã xác nhận |
| [docs/DRAW_ROADMAP.md](docs/DRAW_ROADMAP.md) | Hợp đồng API và quyết định thiết kế tab Tạo bản vẽ |
| [docs/PLAN_ONLINE.md](docs/PLAN_ONLINE.md) | Kế hoạch MiniPC Ubuntu, phân quyền PIN, giới hạn, tunnel |
| [docs/EXPORT_FOR_AI.md](docs/EXPORT_FOR_AI.md) | Cách xuất mã cho AI tiết kiệm token (`tools/export_context.py`) |

## Cấu trúc thư mục
```
backend/app/{api,services,links}   HTTP mỏng → logic → kết nối máy (serial thật / máy giả)
backend/app/services/drawing/      Dây chuyền tab Tạo bản vẽ (ảnh/SVG → nét → G-code → bản thảo)
backend/tests/                     pytest (draw_test/ cho tab vẽ)
frontend/{index.html,css,js,locales,assets/css/tokens.css,tests}
launcher/                          Bật/tắt server chạy ẩn, tạo icon Desktop, cập nhật (bản mang đi)
tools/export_context.py            Xuất mã gọn cho AI + sinh docs/CODEMAP.md
tools/dong_goi.ps1                 Đóng gói zip bản cập nhật / bản đầy đủ (vào export/)
docs/                              Tài liệu (bảng trên)
samples/                           G-code mẫu
```
Dữ liệu riêng của từng máy nằm ở `data/`, không lên Git, tự tạo khi cần: `drafts/` (bản thảo), `config_backups/` (sao lưu cấu hình), `macros/`, cùng `profile.json`, `resume.json`. Xem được trong Cài đặt → Lưu trữ dữ liệu; đổi gốc bằng biến môi trường `EXTRUXY_DATA_DIR`.

## Làm việc với Git
Trước khi làm: `git pull`. Xong một việc nhỏ: `git add .`, `git commit -m "mô tả ngắn"`, `git push`. Mỗi commit một việc; không đẩy mật khẩu, token, `.venv`, `data/`.
