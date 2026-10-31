# Hướng dẫn đọc hiểu code VMU PlotterPen (cho người không biết lập trình)

Tài liệu này **không dạy viết code**. Nó giải thích **nguyên lý**: một chức năng nằm ở đâu, muốn sửa / thêm / bỏ thì động vào chỗ nào, các thư viện xử lý ảnh làm gì và vì sao ghép được với nhau, hiệu ứng giao diện học ở đâu. Đọc xong bạn có thể tự lần ra đúng tệp, đúng đoạn khi cần nhờ người khác (hoặc AI) sửa, và hiểu họ đang làm gì.

Tài liệu kỹ thuật chi tiết hơn nằm trong `docs/` (bắt đầu từ `docs/AI_START.md`).

---

## 1. Bức tranh tổng thể: ba tầng nói chuyện với nhau

Hãy hình dung một **nhà hàng**:

| Nhà hàng | Phần mềm | Nằm ở |
|---|---|---|
| Thực đơn + bàn ghế khách nhìn thấy | **Giao diện**: nút, ô nhập, màu sắc, chữ | `frontend/` (chạy trong trình duyệt) |
| Bồi bàn ghi món, mang món ra | **API**: các "đường gọi" như `/api/draw/import`, `/api/jobs/start` | `frontend/js/core/api.js` ↔ `backend/app/api/` |
| Nhà bếp nấu món | **Máy chủ Python**: xử lý ảnh, sinh G-code, điều khiển máy | `backend/app/services/` |
| Lò nướng | **Máy vẽ** (mạch MKS + FluidNC) qua cáp USB | `backend/app/links/` |

Quy tắc quan trọng: **giao diện không bao giờ tự nói chuyện với máy vẽ**. Mọi thứ đều đi qua máy chủ, máy chủ kiểm tra lại cho an toàn.

Giao diện lại chia làm ba thứ, mỗi thứ một ngôn ngữ:

| Ngôn ngữ | Vai trò | Ví dụ trong dự án |
|---|---|---|
| **HTML** | *bộ xương*: có những nút, ô, khối nào | `frontend/index.html` (cả trang nằm trong một tệp) |
| **CSS** | *quần áo*: màu, cỡ, vị trí, hiệu ứng | `frontend/css/style.css`, `drawing.css`, `polish.css`; màu ở `frontend/assets/css/tokens.css` |
| **JavaScript (JS)** | *cơ bắp*: bấm nút thì làm gì | `frontend/js/…` |

Chữ hiển thị (tiếng Việt / tiếng Anh) **không** viết thẳng trong HTML/JS mà nằm ở `frontend/locales/vi.json` và `en.json`.

---

## 2. Thư mục nào chứa gì

```
ExtruXY/
├─ frontend/                 GIAO DIỆN
│  ├─ index.html             toàn bộ nút, ô, khối của 3 tab
│  ├─ css/                   style.css (nền) → drawing.css (tab vẽ) → polish.css (lớp chỉnh sau cùng, thắng các lớp trước)
│  ├─ assets/css/tokens.css  bảng màu, cỡ chữ, bo góc dùng chung
│  ├─ locales/               vi.json, en.json: mọi chữ hiển thị
│  └─ js/
│     ├─ app.js              điểm khởi động: lần lượt bật từng tab (initControl, initDrawing, …)
│     ├─ core/               nền móng: api.js (gọi máy chủ), state.js (hỏi trạng thái máy liên tục),
│     │                      i18n.js (đổi ngôn ngữ), config.js (số đo máy: vùng 285 × 318 mm, Z bút)
│     ├─ views/              mỗi tab / khối một tệp: control.js, drawing.js, settings.js, drafts.js, terminal.js…
│     │  └─ drawing/         phần con của tab vẽ: params.js (các ô thông số), presets.js, crop.js, canvas.js
│     ├─ stores/             nơi giữ dữ liệu dùng chung (danh sách bản thảo, tệp G-code đang nạp, macro)
│     └─ lib/                công thức thuần, không đụng giao diện (đọc G-code, bố trí giấy, thu nhỏ ảnh)
├─ backend/                  MÁY CHỦ PYTHON
│  ├─ app/main.py            khởi động máy chủ, chặn truy cập lạ
│  ├─ app/api/               "quầy bồi bàn": mỗi tệp một nhóm đường gọi (draw.py, machine.py, config.py, storage.py)
│  ├─ app/services/          "nhà bếp": logic thật
│  │  ├─ machine.py, job.py  điều khiển máy, chạy G-code từng dòng, lọc lệnh nguy hiểm
│  │  └─ drawing/            dây chuyền ảnh → nét → G-code (xem mục 6)
│  ├─ app/links/             nói chuyện với máy: serial_link.py (máy thật), sim_link.py (máy giả để thử)
│  └─ tests/                 kiểm tra tự động (chạy: `python -m pytest`)
├─ launcher/                 bật/tắt phần mềm bằng icon (Windows)
├─ data/                     bản thảo, macro, sao lưu (dữ liệu của bạn, không lên Git)
└─ docs/                     tài liệu kỹ thuật
```

---

## 3. Tìm code: đi ngược từ thứ bạn nhìn thấy

Không cần đọc cả dự án. **Bắt đầu từ chữ trên màn hình**, lần theo từng "tên" một. Mỗi bước là một lần tìm kiếm trong VS Code: **Ctrl+Shift+F** (tìm trong mọi tệp).

**Ví dụ: muốn biết ô "Chi tiết viền" hoạt động thế nào.**

| Bước | Tìm | Ra | Hiểu được gì |
|---|---|---|---|
| 1 | `Chi tiết viền` | `vi.json`: `"drawing.style.outlineDetail": "Chi tiết viền"` | tên khóa của chữ |
| 2 | `drawing.style.outlineDetail` | `index.html`: `<select id="style-outline-detail" …>` | ô này có **id** là `style-outline-detail` |
| 3 | `style-outline-detail` | `js/views/drawing/params.js`: `["style-outline-detail", "style", "outline_detail", "str"]` | ô này gửi lên máy chủ tham số tên `outline_detail` |
| 4 | `outline_detail` (trong `backend`) | `spec.py` (định nghĩa: 3 lựa chọn low/medium/high) và `styles.py` → `edges.py` (nơi dùng thật) | đây là nơi thuật toán đọc giá trị |

Mọi chức năng đều theo một chuỗi như vậy:

```
Chữ trên màn hình → khóa trong vi.json → id trong index.html → tệp JS dùng id đó
→ hàm trong api.js gọi đường /api/… → tệp trong backend/app/api/ → hàm trong backend/app/services/
```

Phím tắt VS Code giúp đi nhanh:

| Phím | Tác dụng |
|---|---|
| **Ctrl+Shift+F** | tìm chữ trong cả dự án (công cụ chính) |
| **Ctrl+P** | gõ tên tệp để mở nhanh |
| **F12** (đặt con trỏ lên tên hàm) | nhảy tới nơi hàm đó được viết |
| **Shift+F12** | liệt kê mọi nơi đang dùng hàm / biến đó |
| **Ctrl+Shift+O** | danh sách hàm trong tệp đang mở |
| **Ctrl+F** | tìm trong tệp đang mở |

Mẹo: tên trong dự án **nhất quán**: id HTML viết gạch ngang (`style-outline-detail`), tham số Python viết gạch dưới (`outline_detail`), khóa chữ viết chấm (`drawing.style.outlineDetail`). Biết một tên là đoán được tên ở tầng khác.

---

## 4. Sửa: dùng cái gì, sửa ở đâu

| Muốn sửa | Sửa ở | Ghi chú |
|---|---|---|
| Chữ hiển thị | `frontend/locales/vi.json` **và** `en.json` | hai tệp phải có cùng khóa |
| Màu | `frontend/assets/css/tokens.css` | ví dụ `--highlight` là màu cam nhấn |
| Cỡ, khoảng cách, bố cục, giao diện điện thoại | `frontend/css/polish.css` | tệp nạp sau cùng nên thắng các tệp trước; phần điện thoại nằm trong khối `@media (max-width: 760px)` |
| Một con số của thuật toán | **hằng số viết HOA ở đầu tệp Python**, có chú thích tiếng Việt | ví dụ `INK_MAX_MM = 4.0` trong `edges.py`, `BRIDGE_MM = 3.0` trong `hatch.py` |
| Giới hạn / giá trị mặc định của ô thông số vẽ | `backend/app/services/drawing/spec.py` | mỗi dòng `Param(...)` là một tham số: tên, kiểu, mặc định, nhỏ nhất, lớn nhất |
| Bộ thông số dựng sẵn | `frontend/js/views/drawing/presets.js` | chỉ là dữ liệu, không có logic |
| Số đo máy (vùng vẽ, Z bút) | Cài đặt → Cấu hình máy trên giao diện (lưu ở `data/profile.json`) | không cần sửa code |

Đa số việc tinh chỉnh chỉ là **đổi con số**, không đổi logic. Đổi một số → chạy lại → xem kết quả → không ưng thì đổi về.

---

## 5. Thêm và bỏ: mọi thứ đều nối với nhau bằng TÊN

### 5.1 Thêm một ô thông số vẽ mới (ví dụ thật: ô "Chi tiết viền")
Phải chạm **5 chỗ**, vì một ô đi qua cả ba tầng:

| # | Tệp | Thêm gì |
|---|---|---|
| 1 | `backend/app/services/drawing/spec.py` | một dòng `Param("outline_detail", "choice", "medium", choices=(...))` vào đúng nhóm (`STYLE`) |
| 2 | Tệp Python dùng nó (`styles.py` / `edges.py`) | đọc `style.outline_detail` |
| 3 | `frontend/index.html` | `<label>` + `<select id="style-outline-detail">` đặt cạnh các ô cùng nhóm |
| 4 | `frontend/js/views/drawing/params.js` | một dòng trong bảng `FIELDS`: id ô ↔ nhóm ↔ tên tham số ↔ kiểu |
| 5 | `vi.json` + `en.json` | khóa chữ cho nhãn, các lựa chọn, dòng gợi ý |

### 5.2 Thêm một nút
1. `index.html`: thẻ `<button id="ten-nut" data-i18n="khoa.chu">` đặt trong khối muốn nút hiện.
2. Tệp JS của tab đó: một dòng `$("ten-nut")?.addEventListener("click", hamXuLy)` trong hàm `init…` của tab, và viết `hamXuLy`.
3. Nếu nút cần máy chủ làm gì: thêm hàm gọi vào `frontend/js/core/api.js`, thêm đường `@router.post(...)` vào `backend/app/api/…py`, viết logic trong `backend/app/services/…`.
4. Khóa chữ ở `vi.json`, `en.json`. Kiểu dáng ở `polish.css` nếu cần.

### 5.3 Bỏ một chức năng: tìm hết các "sợi dây" của nó
Một chức năng để lại **nhiều tên** ở nhiều tầng. Bỏ thiếu một chỗ là lỗi (nút ma, chữ thừa, gọi vào hàm không còn). Cách làm:

1. Bắt đầu từ **id** trong `index.html` → tìm id đó → ra đoạn JS gắn sự kiện.
2. Trong đoạn JS, ghi lại **mọi tên** nó dùng: hàm xử lý, hàm trong `api.js`, khóa chữ.
3. **Tìm từng tên một** (Ctrl+Shift+F). Tên nào chỉ còn dùng cho chức năng này thì bỏ; tên còn nơi khác dùng thì **giữ**.
4. Bỏ theo chiều ngược: HTML → JS → `api.js` → khóa chữ (cả hai tệp) → tài liệu. Phần máy chủ có thể giữ lại nếu sau này còn cần.
5. Chạy kiểm tra (mục 9).

Ví dụ thật: bỏ nút "Tạo tờ mẫu hiệu chỉnh bút" = bỏ nút trong `index.html` + dòng gắn sự kiện và hàm `createCalibration` trong `drawing.js` + `drawCalibration` trong `api.js` + 3 khóa chữ `drawing.calibration.*` ở hai tệp ngôn ngữ; **giữ** đường `POST /api/draw/calibration` ở máy chủ để in lại khi cần.

---

## 6. Thư viện xử lý ảnh: mỗi thứ làm gì, vì sao ghép được

### 6.1 Nguyên lý ghép: dây chuyền, mỗi trạm một việc
Với máy tính, **ảnh chỉ là một bảng số**: mỗi ô là một điểm ảnh, số càng lớn càng sáng (0 = đen, 255 = trắng). Hầu hết hàm xử lý ảnh **nhận một bảng số và trả lại một bảng số cùng cỡ**. Vì vào và ra cùng một "dạng", ta nối hàm này vào sau hàm kia như các trạm trên dây chuyền, miễn là mỗi trạm làm đúng một việc rõ ràng.

Dây chuyền "ảnh → nét vẽ" của mọi phần mềm máy vẽ đều có 5 trạm:

```
Ảnh màu
 → (1) Làm sạch, chỉnh sáng tối       [bảng số xám, đã chỉnh]
 → (2) Tìm chỗ cần vẽ (cạnh, vùng)     [bảng "mức độ cạnh" / "độ đậm"]
 → (3) Chốt có / không                  [bảng đen-trắng: 1 = vẽ, 0 = bỏ]
 → (4) Biến điểm ảnh thành đường        [danh sách đường nét, mỗi đường là dãy toạ độ mm]
 → (5) Gọn đường, sắp thứ tự            [ít điểm hơn, ít lần nhấc bút]
 → G-code cho máy vẽ
```

Cách chọn hàm cho từng trạm: **gọi tên đúng vấn đề bằng thuật ngữ chuẩn, rồi tìm công cụ chuẩn cho thuật ngữ đó**. Ví dụ khi làm lại nét viền:

| Vấn đề nhìn thấy | Tên thuật ngữ | Công cụ chuẩn |
|---|---|---|
| Nét đen dày ra hai đường song song | cần *đường giữa* (centerline) của nét | *top-hat* để lấy nét, *skeletonize* để làm mảnh |
| Gấu trắng trên nền xám không có viền | *ranh giới vùng* (region boundary) | *Canny edge detection* |
| Đỏ cạnh xanh lá cùng độ sáng bị mất viền | cần xét *màu*, không chỉ sáng tối | đổi sang hệ màu *Lab*, chạy Canny trên kênh màu |
| Nét bị đứt từng khúc | *nối khe hở* (gap closing) | tìm điểm gần nhất bằng *KD-tree* rồi kẻ nối |

Sau đó **thử trên vài ảnh mẫu, nhìn kết quả, chỉnh con số**, lặp lại. Không ai nghĩ ra thuật toán một lần là đúng.

### 6.2 Các thư viện và hàm hay gặp (nghĩa bằng lời thường)

| Thư viện | Là gì | Dùng ở |
|---|---|---|
| **NumPy** | làm việc với bảng số rất nhanh (cộng, so sánh cả bảng một lúc) | khắp nơi |
| **Pillow (PIL)** | đọc / lưu tệp ảnh, xoay ảnh theo hướng chụp (EXIF) | `raster_in.py` |
| **OpenCV (`cv2`)** | hộp đồ nghề xử lý ảnh lớn nhất: lọc, bắt cạnh, tìm đường bao | `tone.py`, `edges.py`, `hatch.py`, `trace.py` |
| **scikit-image (`skimage`)** | thêm các phép ảnh khoa học, ở đây dùng *làm mảnh* | `trace.py`, `edges.py` |
| **SciPy** | toán khoa học, ở đây dùng *tìm điểm gần nhất* | `edges.py` |
| **vpype** | thư viện chuyên cho máy vẽ: gộp nét, bỏ nét vụn, sắp thứ tự để ít nhấc bút | `optimize.py`, `svg_in.py` |
| **FastAPI + uvicorn** | dựng máy chủ và các đường `/api/…` | `backend/app/main.py`, `app/api/` |
| **pydantic** | kiểm dữ liệu gửi lên có đúng kiểu, đúng khoảng không | `app/api/*.py` |
| **pyserial** | nói chuyện qua cổng USB / COM với mạch máy vẽ | `links/serial_link.py` |

| Hàm | Nghĩa đơn giản | Trạm |
|---|---|---|
| `cv2.cvtColor` | đổi hệ màu (màu → xám, RGB → Lab) | 1 |
| `cv2.fastNlMeansDenoising` | khử nhiễu hạt (ảnh chụp thiếu sáng) | 1 |
| `cv2.createCLAHE` | cân bằng sáng **từng vùng nhỏ** (chỗ tối sáng lên mà chỗ sáng không cháy) | 1 |
| `cv2.GaussianBlur` | làm mờ đều (bớt chi tiết vụn) | 1–3 |
| `cv2.bilateralFilter` | làm mờ **nhưng giữ mép** (mịn mảng mà không nhòe ranh giới) | 1 |
| `cv2.Canny` | tìm **cạnh**: nơi độ sáng đổi đột ngột, ra đường mảnh 1 điểm ảnh | 2 |
| `cv2.morphologyEx(… TOPHAT)` | giữ lại những thứ **hẹp hơn một cỡ cho trước** (nét mực, chấm), bỏ mảng to | 2 |
| `cv2.morphologyEx(… CLOSE / OPEN)` | lấp lỗ nhỏ / xóa đốm nhỏ trên bảng đen-trắng | 3 |
| so sánh `bảng >= ngưỡng` | chốt điểm nào đủ đậm thì vẽ (*threshold*) | 3 |
| `cv2.connectedComponentsWithStats` | đếm và đo từng "cục" liền nhau (để bỏ cục quá nhỏ) | 3 |
| `cv2.distanceTransform` | mỗi điểm cách mép bao xa (biết nét dày bao nhiêu) | 3–4 |
| `skimage.morphology.skeletonize` | gọt nét dày thành **đường giữa** 1 điểm ảnh | 4 |
| `cv2.findContours` | đi vòng theo **đường bao** của một vùng | 4 |
| `cv2.approxPolyDP` | bỏ bớt điểm thừa trên đường mà hình dạng gần như không đổi (thuật toán Douglas–Peucker) | 5 |
| `scipy.spatial.cKDTree` | tra nhanh "điểm nào gần điểm này nhất" | 4–5 |
| vpype `linemerge`, `linesimplify`, `filter`, `linesort` | nối các nét đầu-đuôi gần nhau, bớt điểm thừa, bỏ nét quá ngắn, sắp thứ tự cho bút đi ít nhất (`--two-opt`: thử đảo đoạn để quãng nhấc bút ngắn hơn) | 5 |

### 6.3 Dây chuyền trong dự án, trạm nào ở tệp nào
Tất cả nằm trong `backend/app/services/drawing/`:

| Trạm | Tệp | Việc |
|---|---|---|
| Đọc ảnh | `raster_in.py` | đọc, xoay theo EXIF, **cắt** (crop), thu nhỏ về độ phân giải làm việc |
| 1 | `tone.py` | khử nhiễu → tự cân sáng → mức đen / trắng / gamma → CLAHE → (đảo) |
| 2–3, kiểu tô | `hatch.py`, `styles.py` | chia ảnh thành vài mức đậm; mỗi mức kẻ một lượt zigzag / sóng / xoắn ốc |
| 2–4, nét viền | `edges.py` → `trace.py` | nét mực (top-hat) + ranh giới vùng (Canny) + nối khe → làm mảnh → dò thành đường |
| Đa màu | `palette.py` | gom màu ảnh thành 2–4 màu (`cv2.kmeans` trên hệ màu Lab), mỗi màu một lớp bút |
| 5 | `optimize.py` | vpype gộp và sắp nét |
| Bố trí giấy | `layout.py` | đặt bản vẽ lên tờ giấy, xoay, lật, kiểm không vượt vùng máy |
| G-code | `gcode.py` | đổi đường nét thành lệnh máy (`G0`, `G1`, nâng / hạ bút) |
| Điều phối | `raster.py`, `service.py` | gọi các trạm theo đúng thứ tự |

Xử lý ảnh chạy ở **một chương trình con riêng** (`isolated.py`) để ảnh nặng không làm máy vẽ giật, và hủy được ngay.

---

## 7. Hiệu ứng động của giao diện (CSS + JS): là gì, học ở đâu

| Hiệu ứng trong dự án | Kỹ thuật | Từ khóa để tra |
|---|---|---|
| Khối mở / thu gọn có trượt mềm | thẻ `<details>` + `::details-content` + `transition` + `interpolate-size` | *CSS details animation* |
| Nút sáng lên khi rê chuột | `:hover` + `transition` | *CSS transition* |
| Dòng bản thảo trôi khi kéo, dòng khác trượt nhường chỗ | `transform: translateY(...)` + `transition`; JS dùng *Pointer Events* và `requestAnimationFrame` | *pointer events drag and drop*, *FLIP animation* |
| Hiện chữ từ từ | `@keyframes` + `animation` | *CSS keyframes* |
| Điện thoại khác bố cục máy tính | `@media (max-width: …)` | *responsive design media query* |
| Đổi thứ tự khối trên điện thoại mà không sửa HTML | `display: contents` + `order` | *CSS order*, *display contents* |
| Xếp hàng / cột | `display: flex`, `display: grid` | *CSS flexbox*, *CSS grid* |
| Một chỗ đổi màu cả trang, sáng / tối | biến CSS `--ten-bien` trong `tokens.css`, `color-mix()` | *CSS custom properties* |
| Tắt hiệu ứng cho người không thích chuyển động | `@media (prefers-reduced-motion: reduce)` | *prefers-reduced-motion* |
| Bật / tắt trạng thái | JS `element.classList.toggle("ten-lop")`, CSS định nghĩa `.ten-lop` | *classList* |

Nơi tham khảo (miễn phí, có ví dụ chạy được ngay trên trang):

| Nguồn | Dùng khi |
|---|---|
| **MDN Web Docs** (`developer.mozilla.org`, có tiếng Việt một phần) | tra nghĩa chính xác của mọi thẻ HTML, thuộc tính CSS, hàm JS |
| **web.dev** (Google) | bài hướng dẫn hiệu ứng, bố cục, tốc độ |
| **CSS-Tricks**: "A Complete Guide to Flexbox", "A Complete Guide to CSS Grid" | hiểu flex / grid bằng hình vẽ |
| **caniuse.com** | xem trình duyệt nào hỗ trợ một tính năng mới |
| Công cụ **F12** trong Chrome / Edge (DevTools) | bấm vào một phần tử trên trang, xem nó đang ăn CSS nào, sửa thử trực tiếp (không lưu) |

---

## 8. Học thuật toán ảnh ở đâu

| Nguồn | Có gì |
|---|---|
| **OpenCV Python Tutorials** (`docs.opencv.org`, mục *OpenCV-Python Tutorials*) | từng phép (làm mờ, ngưỡng, hình thái học, Canny, đường bao) có ảnh trước / sau và code |
| **scikit-image Gallery** (`scikit-image.org`, mục *Examples*) | mỗi ví dụ một trang: skeletonize, bộ lọc, phân vùng |
| **vpype docs** (`vpype.readthedocs.io`) | các lệnh tối ưu nét cho máy vẽ |
| **awesome-plotters** (GitHub: `beardicus/awesome-plotters`) | danh sách công cụ, thuật toán, dự án mẫu của cộng đồng máy vẽ |
| **FluidNC wiki** (`wiki.fluidnc.com`) | lệnh và cấu hình firmware máy vẽ |

Cách tìm hiệu quả: gõ **tiếng Anh**, **cụ thể theo một trạm**, kèm tên thư viện. Ví dụ "opencv skeleton thick line centerline python" ra kết quả tốt hơn nhiều so với "chuyển ảnh thành nét vẽ".

---

## 9. Sửa xong thì kiểm tra thế nào

| Kiểm | Cách | Báo gì |
|---|---|---|
| Kiểm tra tự động máy chủ | trong `backend`: `python -m pytest` | số bài đạt / hỏng; hỏng nghĩa là có thứ khác bị ảnh hưởng |
| Kiểm tra tự động giao diện | ở thư mục gốc: `node --test frontend/tests/paper.test.mjs frontend/tests/imageprep.test.mjs frontend/tests/gcode.test.mjs` | như trên |
| Xem giao diện | khởi động lại máy chủ, trình duyệt **Ctrl+F5** (tải lại không dùng bản cũ); **F12 → Console** xem có dòng đỏ báo lỗi JS không | lỗi chữ, nút không chạy |
| Lưới an toàn | Git: sửa hỏng thì `git checkout -- <tệp>` quay về bản đã commit; `git diff` xem mình đã đổi gì | |

---

## 10. Từ điển nhanh

| Từ | Nghĩa |
|---|---|
| **id** | tên riêng của một phần tử trên trang (`id="run-job-btn"`), JS dùng để tìm đúng nút đó |
| **class** | nhãn dán chung cho nhiều phần tử để CSS tô cùng kiểu (`class="primary-button"`) |
| **hàm (function)** | một đoạn việc có tên, gọi tên là chạy (`refreshDrafts()`) |
| **biến / hằng số** | ô nhớ có tên; hằng số viết HOA là con số cố định để chỉnh (`GAP_MM = 1.5`) |
| **sự kiện (event)** | điều xảy ra trên trang: bấm (`click`), gõ (`input`), kéo (`pointermove`) |
| **API / route** | một "đường gọi" máy chủ, ví dụ `POST /api/draw/drafts/reorder` |
| **JSON** | dạng chữ để gửi dữ liệu qua lại, như `{"name": "Bản vẽ", "pinned": true}` |
| **import** | một tệp mượn hàm của tệp khác; dòng `import` ở đầu tệp cho biết nó phụ thuộc vào đâu |
| **mặt nạ (mask)** | bảng đen-trắng: điểm nào được vẽ / bị bỏ |
| **skeleton** | đường giữa 1 điểm ảnh của một nét dày |
| **G-code** | ngôn ngữ lệnh của máy CNC / máy vẽ: `G0` chạy không vẽ, `G1` chạy có vẽ, `Z` nâng hạ bút |
| **commit** | một lần "chụp lại" toàn bộ mã trong Git, có thể quay về bất cứ lúc nào |
