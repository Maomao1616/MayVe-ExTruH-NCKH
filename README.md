# VMU PlotterPen (ExtruXY) — phần mềm điều khiển máy vẽ

Máy vẽ bút CoreXY tự làm (vùng làm việc 285 × 318 mm, giấy A6 / A5 / A4) và phần mềm điều khiển chạy trên trình duyệt. Máy dùng mạch **MKS DLC32 V2.1** với firmware **FluidNC v4.1.1** (không sửa firmware), nối với máy tính qua cáp USB.

- **Tab Điều khiển:** kết nối, trạng thái, jog, Home / Zero, nâng hạ bút, nạp + xem trước + chạy G-code, hủy an toàn, tiếp tục tác vụ đã dừng, terminal, macro, hàng đợi.
- **Tab Tạo bản vẽ:** ảnh hoặc SVG → nét (zigzag, sóng, xoắn ốc, viền; 1–4 màu) → đặt lên giấy → G-code → bản thảo → sang Điều khiển.
- **Tab Cài đặt:** kết nối, giao diện, cấu hình máy (đọc / ghi YAML trên mạch), hồ sơ bút, dữ liệu.

```
Trình duyệt (JS thuần) ⇄ HTTP API ⇄ máy chủ Python (FastAPI) ⇄ máy giả (SimLink)  hoặc  USB → MKS DLC32 → FluidNC
```
Giao diện không bao giờ chạm cổng USB; máy chủ là nguồn sự thật. Máy thật **mặc định chỉ đọc** cho tới khi mở khóa chuyển động. Tab Tạo bản vẽ **không bao giờ gọi máy**.

## Tài liệu
Bắt đầu từ **[docs/01_TONG_QUAN.md](docs/01_TONG_QUAN.md)**. Tài liệu đánh số từ nhỏ đến lớn, viết cho cả người không học lập trình:

| # | Tệp | Nội dung |
|---|---|---|
| 01 | [Tổng quan](docs/01_TONG_QUAN.md) | dự án là gì, hệ thống, các tab, từ điển, bản đồ tài liệu |
| 02 | [Phần cứng và thông số máy](docs/02_PHAN_CUNG_MAY.md) | linh kiện, cấu hình FluidNC, hành vi firmware, kết quả thử máy |
| 03 | [Cấu trúc phần mềm](docs/03_CAU_TRUC_PHAN_MEM.md) | cây thư mục, frontend, backend, dữ liệu, cách tìm / sửa mã, kiểm tra |
| 04 | [Tab Điều khiển](docs/04_TAB_DIEU_KHIEN.md) | nút, luồng lệnh, gửi G-code, dừng an toàn, tiếp tục |
| 05 | [Tab Tạo bản vẽ](docs/05_TAB_TAO_BAN_VE.md) | nút, preset, luồng dữ liệu, tham số, API, bản thảo |
| 06 | [Thuật toán xử lý ảnh](docs/06_THUAT_TOAN_XU_LY_ANH.md) | ảnh → nét chi tiết từng bước, thư viện dùng / không dùng / có thể thêm |
| 07 | [Thử nghiệm](docs/07_THU_NGHIEM.md) | cách thử trên giấy, bài thử tốc độ, bảng kết quả |
| 08 | [Triển khai](docs/08_TRIEN_KHAI.md) | bản mang đi Windows, phân quyền, mạng / demo, MiniPC, Cloudflare |
| 09 | [Quyết định thiết kế](docs/09_QUYET_DINH_THIET_KE.md) | chọn gì, vì sao |
| 10 | [Hướng phát triển](docs/10_HUONG_PHAT_TRIEN.md) | ý tưởng để dành |
| 11 | [Việc cần làm](docs/11_VIEC_CAN_LAM.md) | tình trạng, việc tiếp theo |
| AI | [AI_START](docs/AI_START.md), [AI_CODEMAP](docs/AI_CODEMAP.md) | chỉ dành cho AI |

## Cài đặt và chạy (máy phát triển)
Cần **Python 3.12** (3.15 quá mới, thiếu gói) và **Git**. Windows PowerShell:
```powershell
git clone <địa-chỉ-kho>
cd <thư-mục-kho>\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
uvicorn app.main:app --reload
```
Mở `http://127.0.0.1:8000/`. Chưa có máy: Cài đặt → Kết nối → chế độ `sim` (máy giả).
- PowerShell báo "running scripts is disabled": `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Linux: `python3.12 -m venv .venv && source .venv/bin/activate`, còn lại giống nhau (chưa thử trên Ubuntu thật).
- Máy không cài Python: dùng **bản mang đi** (thư mục `Python/` + `launcher/`, bấm icon), xem [08_TRIEN_KHAI.md](docs/08_TRIEN_KHAI.md) phần A.

## Kiểm tra
| Việc | Lệnh |
|---|---|
| Test máy chủ (~397) | trong `backend`, đã bật venv: `python -m pytest` |
| Test giao diện (33) | từ thư mục gốc: `node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs frontend/tests/gcode.test.mjs` |
| Thử API bằng tay | `http://127.0.0.1:8000/docs` |

## Dùng máy thật an toàn
- Cắm USB, chọn cổng ở Cài đặt → Kết nối. Chế độ chỉ đọc chỉ xem trạng thái và gửi lệnh đọc.
- Muốn máy chạy: **Mở khóa chuyển động** (tự khóa sau 15 phút). Chỉ mở khi có người đứng cạnh, tay gần công tắc nguồn.
- Nút Reset / Dừng trên web **không phải dừng khẩn cấp**. Dừng khẩn cấp thật là công tắc cắt nguồn 12 V.
- **Hai vai trò**: khách (không đăng nhập) chỉ xem; quản lý nhập PIN. Chưa đặt PIN thì ai vào cũng là quản lý: khi cho máy khác vào mạng, đặt PIN quản lý và PIN mở khóa trong `data\pin.txt` ([08_TRIEN_KHAI.md](docs/08_TRIEN_KHAI.md) phần A4, B).
- Tắt Wi-Fi của mạch MKS trước khi cho người khác vào mạng (WebUI FluidNC vượt qua mọi khóa của phần mềm).

## Thư mục
```
backend/app/{api,services,links}   HTTP mỏng → logic → kết nối máy (USB thật / máy giả)
backend/app/services/drawing/      dây chuyền tab Tạo bản vẽ
backend/tests/                     pytest (draw_test/ cho tab vẽ)
frontend/                          index.html, css, js, locales, tests
launcher/  Cap nhat.bat            bản mang đi Windows
tools/                             export_context.py (xuất mã cho AI, sinh AI_CODEMAP) · dong_goi.ps1 · make_test_gcode.py · ink_sim.py
docs/                              tài liệu (bảng trên)
data/                              (không lên Git) bản thảo, macro, sao lưu, hồ sơ, PIN
```

## Git
Trước khi làm: `git pull`. Xong một việc: `git add .`, `git commit -m "mô tả ngắn"`, `git push`. Không đẩy mật khẩu, PIN, `.venv`, `data/`.
