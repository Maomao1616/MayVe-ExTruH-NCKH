# VMU PlotterPen (ExtruXY) — phần mềm điều khiển máy vẽ

Máy vẽ bút CoreXY tự làm (vùng làm việc 285 × 318 mm, giấy A6 / A5 / A4) và phần mềm điều khiển chạy trên trình duyệt. Máy dùng mạch **MKS DLC32 V2.1** với firmware **FluidNC v4.1.1** (không sửa firmware), nối với máy tính qua cáp USB.

- **Tab Điều khiển:** kết nối, trạng thái, jog, Home / Zero, nâng hạ bút, nạp tệp G-code (khung 2D hiện ngay), chạy, hủy an toàn, tiếp tục tác vụ đã dừng, âm báo khi xong / lỗi, terminal, macro, hàng đợi.
- **Tab Tạo bản vẽ:** ảnh hoặc SVG → nét (gạch chéo, theo dáng ảnh, sóng biến thiên, xoắn ốc, nét viền; 4 preset; khoanh vùng chủ thể; vòng sửa sai tông; 1–4 màu) → đặt lên giấy → G-code → bản thảo → sang Điều khiển.
- **Tab Cài đặt:** kết nối, giao diện, cấu hình máy (đọc / ghi YAML trên mạch), hồ sơ bút, tờ thử / hiệu chỉnh, PIN quản lý, dữ liệu.

```
Trình duyệt (JS thuần) ⇄ HTTP API ⇄ máy chủ Python (FastAPI) ⇄ máy giả (SimLink)  hoặc  USB → MKS DLC32 → FluidNC
```
Giao diện không bao giờ chạm cổng USB; máy chủ là nguồn sự thật. Máy thật **mặc định chỉ đọc** cho tới khi mở khóa chuyển động. Tab Tạo bản vẽ **không bao giờ gọi máy**.

## Phần cứng: khung, mạch, firmware
Khung in 3D ghép từ ba mẫu công khai (ý tưởng chung của **pittance**; giấy phép từng mẫu theo trang Printables):

| Phần | Nguồn |
|---|---|
| Khung CoreXY (mẫu gốc) | [extruH pen plotter](https://www.printables.com/model/734327-extruh-pen-plotter) |
| Cụm gá bút + servo cho micro servo | [Pen bracket update](https://www.printables.com/model/1323373-penbracket-update) |
| Chi tiết phụ, đi dây gọn | [ExtruXY GRBL — remix](https://www.printables.com/model/1526086-extruxy-grbl-grbl-remix-of-extruxy-remix-of-extruh) |
| Cách lắp ráp (video) | [Playlist YouTube](https://youtube.com/playlist?list=PLQQNsxNs4rQY3_Fx0UpvSxl-MGIwFmLt1) |

| Linh kiện | Đang dùng | Ghi chú |
|---|---|---|
| Nguồn tổng | **12 V 6 A** (Mean Well) | chọn 12 V cho gọn, rẻ; **khuyến khích 24 V nếu mua được** (khoẻ hơn, chạy nhanh hơn). Mạch nhận 12–24 V, nhưng đổi nguồn thì phải chỉnh lại dòng driver |
| Mạch điều khiển | **MKS DLC32 V2.1** (ESP32) | sơ đồ và tệp phần cứng: [MKS-DLC32 V2.1_003](https://github.com/makerbase-mks/MKS-DLC32/tree/fcedc0ebb0e73e4e45024685bd0464f60a8fc355/MKS-DLC32-main/hardware/MKS%20DLC32%20V2.1_003) |
| Firmware | **FluidNC v4.1.1** | [bản phát hành](https://github.com/bdring/FluidNC/releases/tag/v4.1.1) · [kho mã](https://github.com/bdring/FluidNC) (GPL-3.0). **Không sửa firmware**, chỉ nạp và ghi tệp cấu hình YAML |
| Servo nâng bút | **JX PS-1109MG** 9 g, bánh răng kim loại, analog | **cấp nguồn 6 V riêng** (hạ áp XL4005 từ 12 V, GND nối chung với mạch); dùng chung nguồn với mạch thì servo giật và mạch dễ reset |
| Động cơ, driver | 2 × NEMA17 17HS4401, 2 × TMC2209 | dòng, Vref, bước/mm, chân, cấu hình: [02_PHAN_CUNG_MAY.md](docs/02_PHAN_CUNG_MAY.md) |

Bản dựng 3D của mình theo đúng ba mẫu trên: khung chữ H (hai thanh ray + đai GT2), cụm bút treo trên thanh ngang, khay đựng mạch và bút đặt ở góc tờ giấy.

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
| 07 | [Thử nghiệm](docs/07_THU_NGHIEM.md) | danh sách bài thử trên giấy, cách đo bề rộng nét / tông, mẫu gửi kết quả |
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
| Test máy chủ | trong `backend`, đã bật venv: `python -m pytest` |
| Test giao diện | từ thư mục gốc, truyền **đường dẫn từng tệp** (PowerShell không hiểu `{a,b}`): `node --test frontend/tests/chart.test.mjs frontend/tests/gcode.test.mjs frontend/tests/imageprep.test.mjs frontend/tests/locales.test.mjs frontend/tests/notify.test.mjs frontend/tests/paper.test.mjs frontend/tests/preview.test.mjs frontend/tests/subject.test.mjs` |
| Thử API bằng tay | `http://127.0.0.1:8000/docs` |

- `python -m pytest` chạy cả bộ; `test_old_logs_are_pruned` (`backend/tests/test_joblog.py:76`) đôi khi hết giờ khi chạy chung — chạy riêng thì qua: `python -m pytest tests/test_joblog.py -k pruned`.
- Chỉ chạy phần tab vẽ: `python -m pytest tests/draw_test`.

## Dùng máy thật an toàn
- Cắm USB, chọn cổng ở Cài đặt → Kết nối. Chế độ chỉ đọc chỉ xem trạng thái và gửi lệnh đọc.
- Muốn máy chạy: **Mở khóa chuyển động** (tự khóa sau 15 phút). Chỉ mở khi có người đứng cạnh, tay gần công tắc nguồn.
- Nút Reset / Dừng trên web **không phải dừng khẩn cấp**. Dừng khẩn cấp thật là công tắc cắt nguồn 12 V.
- **Hai vai trò**: khách (không đăng nhập) chỉ xem, được **Gửi ảnh**; quản lý nhập PIN. Chưa đặt PIN thì ai vào cũng là quản lý: khi cho máy khác vào mạng, đặt PIN quản lý trong `data\pin.txt` (dòng `admin=…`; dòng `unlock=` **không dùng**) — hoặc đổi ngay trong Cài đặt → PIN quản lý. Xem [08_TRIEN_KHAI.md](docs/08_TRIEN_KHAI.md) phần A4, B.
- Tắt Wi-Fi của mạch MKS trước khi cho người khác vào mạng (WebUI FluidNC vượt qua mọi khóa của phần mềm).

## Thư mục
```
backend/app/{api,services,links}   HTTP mỏng → logic → kết nối máy (USB thật / máy giả)
backend/app/services/drawing/      dây chuyền tab Tạo bản vẽ
backend/tests/                     pytest (draw_test/ cho tab vẽ)
frontend/                          index.html, css, js, locales, tests
launcher/  Cap nhat.bat            bản mang đi Windows
tools/                             export_context.py (xuất mã cho AI, sinh AI_CODEMAP) · dong_goi.ps1 · make_test_gcode.py
                                   ink_sim.py (mô phỏng mực) · ink_real.py (đo tông trên ảnh thật) · tone_read.py · log_read.py · style_preview.py
docs/                              tài liệu (bảng trên)
data/                              (không lên Git) bản thảo, macro, sao lưu, hồ sơ, PIN
```

## Ghi công: ý tưởng, thư viện, giấy phép
**Giao diện:** tab Điều khiển tham khảo cách bố trí của [AxioCNC](https://github.com/rsteckler/AxioCNC) (giao diện web điều khiển CNC, dựng trên cncjs) — **chỉ lấy ý tưởng, không dùng mã**. Ý tưởng tính năng: 4 repo của [Tonino-RB](https://github.com/Tonino-RB) — [SVGroom](https://github.com/Tonino-RB/SVGroom) · [Plotterosaurus](https://github.com/Tonino-RB/Plotterosaurus) · [PlotHatcher](https://github.com/Tonino-RB/PlotHatcher) · [vpyposaurus](https://github.com/Tonino-RB/vpyposaurus); việc cụ thể và giấy phép từng repo ở [10_HUONG_PHAT_TRIEN.md](docs/10_HUONG_PHAT_TRIEN.md) mục 4.1. Kho này **không chứa dòng mã nào của họ**.

**Thư viện dùng trực tiếp** (giấy phép đọc từ gói đã cài, `pip` metadata ngày 17/11/2026):

| Thư viện | Giấy phép | Dùng cho |
|---|---|---|
| FastAPI · Starlette · Uvicorn · Pydantic | MIT · BSD-3 · BSD-3 · MIT | máy chủ HTTP, API, kiểm dữ liệu vào |
| NumPy | BSD-3 | mọi phép trên ảnh và tọa độ |
| OpenCV (`opencv-python-headless`) | Apache-2.0 | làm mờ, Canny, hình thái học, CLAHE, k-means, Douglas–Peucker |
| scikit-image | BSD-3 | `skeletonize` — gọt nét dày thành đường giữa |
| SciPy | BSD-3 | `cKDTree` (tìm điểm gần nhất), `gaussian_filter1d` |
| Pillow | MIT-CMU | đọc / ghi ảnh, xoay theo EXIF |
| Shapely | BSD-3 | rút gọn nét cho bản xem nháp |
| vpype (kèm `vpype_cli`) | MIT | đọc SVG, nối nét, bớt điểm, sắp thứ tự nét (2-opt) |
| pyserial | BSD | nói chuyện với cổng USB |
| PyYAML | MIT | đọc / ghi cấu hình FluidNC |
| python-multipart | Apache-2.0 | nhận tệp tải lên |

**Phần giao diện không dùng thư viện ngoài** (JS thuần, không CDN) → không có giấy phép bên thứ ba nào trong trình duyệt.

Phụ thuộc kéo theo, mã dự án **không gọi trực tiếp**: `networkx`, `svgelements`, `svgwrite`, `imageio`, `websockets`, `asteval`, `multiprocess`, `pyphen`, `pnoise`… (do vpype / FastAPI kéo vào). ⚠ `pyphen` (GPL-2.1+ / LGPL-2.1+ / MPL-1.1) và `pnoise` (LGPL-2.1) là hai gói ràng buộc mạnh nhất — dùng nội bộ thì không sao, **bán sản phẩm thì phải xem lại**.

**Thuật toán: cái nào mượn, cái nào tự viết** (bảng hàm thư viện đầy đủ ở [06_THUAT_TOAN_XU_LY_ANH.md](docs/06_THUAT_TOAN_XU_LY_ANH.md) mục 15):

| Thuật toán / ý tưởng | Lấy từ đâu | Trong mã |
|---|---|---|
| Sắp thứ tự nét cho quãng nhấc bút ngắn nhất (2-opt) | vpype `linesort --two-opt` | `optimize.py` |
| Làm mảnh nét thành đường giữa | `skimage.morphology.skeletonize` | `edges.py` |
| CLAHE, Canny, hình thái học, Douglas–Peucker | OpenCV | `tone.py`, `edges.py`, `trace.py` |
| XDoG / FDoG (DoG có ngưỡng mềm + trung bình dọc hướng nét) | ý tưởng từ tài liệu công khai, **tự viết** | `edges.py` |
| Nối chuỗi điểm thành cung `G2/G3` | **tự viết**, sai lệch ≤ 0,02 mm | `arcs.py` |
| 5 kiểu tô, thang tông, vòng sửa sai, khoanh vùng chủ thể | **tự viết**, số đo ở tài liệu 06 | `styles.py`, `tone.py`, `hatch.py` |
| Ước tính thời gian vẽ (gia tốc, qua góc, nhấc bút) | **tự viết**; cách đối chiếu với phần mềm AxiDraw học từ SVGroom | `gcode.py` |

## Git
Trước khi làm: `git pull`. Xong một việc: `git add .`, `git commit -m "mô tả ngắn"`, `git push`. Không đẩy mật khẩu, PIN, `.venv`, `data/`.
