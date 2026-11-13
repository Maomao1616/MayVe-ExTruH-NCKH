# 05 — Tab Tạo bản vẽ: nút bấm, luồng dữ liệu và mã phía sau

> Dành cho người đọc. Phần 1–3 dùng hằng ngày. Phần 4–8 giải thích mã đứng sau, tăng dần độ sâu.
> Thuật toán ảnh → nét chi tiết từng bước: [06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md).

**Mục lục**
1. Tab này làm gì, không làm gì
2. Các nút và ô
3. Bộ thông số dựng sẵn (preset) và chọn kiểu nét
4. Luồng dữ liệu: từ chọn tệp tới bản thảo
5. Ba nhóm việc: nặng, nhẹ, rất nhẹ
6. Tham số: khai báo một chỗ
7. Hợp đồng API
8. Bản thảo trên đĩa
9. Tệp mã liên quan

---

## 1. Tab này làm gì, không làm gì

| Làm | Không làm |
|---|---|
| Nạp ảnh (PNG / JPG / WEBP) hoặc SVG → tạo nét → đặt lên giấy A6 / A5 / A4 → ra G-code → lưu **bản thảo** | **Không bao giờ gọi máy vẽ.** Muốn vẽ phải sang tab Điều khiển, nhìn khung vẽ rồi bấm Chạy |

Hai tab chỉ nối với nhau qua **bản thảo trên đĩa** (G-code + ảnh minh họa + thông tin). Không có đường tắt nào khác.

---

## 2. Các nút và ô

| Nút / ô | Làm gì |
|---|---|
| **Chọn tệp** | **ảnh**: chỉ hiện ảnh (cắt và chỉnh sáng / tối chạy ngay trong trình duyệt, máy chủ chưa làm gì); canvas trống cho tới khi bấm **Tạo nét**. **SVG**: nhẹ nên tạo nét ngay. Chọn tệp khác thì xóa nét của tệp trước |
| **Gửi ảnh** (khách) | thay cho Tạo nét khi chưa đăng nhập: gửi ảnh + thông số cho chủ máy (xem 08 B4). Quản lý mở ảnh khách ở hộp thư "Ảnh khách gửi" |
| **Tạo nét** | (chỉ ảnh) chạy xử lý ở máy chủ, nền, có thanh tiến trình. Sau lần đầu nút đổi tên thành **Tạo lại nét**. Khách (không đăng nhập) không bấm được |
| **Hủy** (cạnh thanh tiến trình) | dừng việc tạo nét đang chạy |
| **Bộ thông số dựng sẵn** | Chân dung / Phong cảnh / Cận cảnh – Đồ vật / Ảnh 2D – Hình vẽ / Schematic: điền sẵn tiền xử lý + kiểu nét rồi tạo lại nét. Sửa tay ô nào thì về "Tùy chỉnh" |
| **Tạo lại nét** | chạy lại sau khi đổi thông số tạo nét (tiền xử lý, kiểu nét, bút, màu) |
| Ảnh gốc → **✂ Cắt ảnh** | kéo vùng, co giãn góc / cạnh, khóa tỷ lệ (tự do / theo khung giấy / 1:1 / 4:3 / 3:4 / 16:9). Áp dụng: chưa tạo nét thì chỉ nhớ vùng cắt (gửi lúc bấm Tạo nét); đã tạo nét thì tạo lại như tệp mới. Đổi bộ thông số dựng sẵn cũng vậy |
| Hộp **Xem ảnh sau chỉnh sáng** | xem ngay ảnh sau mức đen / trắng / gamma / đảo (chạy trong trình duyệt, không có CLAHE / khử nhiễu) |
| Khung vẽ trên giấy | kéo = dời; 8 tay nắm = co giãn; hít vào lề và tâm; phím mũi tên dời (Shift = 10 mm); Shift + cuộn = thu phóng; nhấp đúp = đặt lại |
| Xoay 90° / Xem toàn bộ | xoay khung; về toàn cảnh |
| Khổ giấy, lề, rộng / cao, căn giữa, lật, đảo thứ tự | bố trí; đổi là G-code tự tính lại sau 0,4 s. Khổ "Cả vùng máy" = hành trình máy, mặc định 285 × 318 mm (lề chỉnh ở ô Lề an toàn, mặc định 5) |
| Tốc độ vẽ / di chuyển / nâng bút / **hạ bút**, Z bút, thời gian chờ | tham số G-code (mặc định 8000 / 8000 / 3000 / 2000 mm/min, Z3 / Z0 (ô Z nhấc lấy mặc định từ Cài đặt → "Z nhấc khi sinh G-code", không phải Z bút lên của điều khiển), chờ 0 s (từ 13/11/2026); nét cong ghi bằng G2/G3) |
| **Lưu bản thảo** | ghi G-code + ảnh minh họa + thông tin vào thư mục bản thảo |
| **Chuyển sang Điều khiển** | cần tích "Tôi đã kiểm tra…". Tự lưu bản thảo (không tạo trùng) rồi nạp vào tab Điều khiển. **Không tự chạy** |
| Danh sách bản thảo | ☰ kéo đổi thứ tự (trong cùng nhóm ghim / không ghim), ✎ đổi tên tại chỗ, Mở xem, Nạp (theo lớp màu), Ghim, Xóa (bấm hai lần) |
| **Thang tông** (ở **Cài đặt → Tờ thử / hiệu chỉnh**, nút "Mở ảnh thang tông ở tab Tạo bản vẽ"; từ 13/11/2026 thay "Thang xám" + "Tờ hiệu chỉnh tông") | nạp ảnh 16 ô xám 0 → 90 % + 3 ô mốc đen + chữ F; chọn bút / kiểu tô / preset ở tab này rồi vẽ, để thử preset và đo tông ([07_THU_NGHIEM.md](07_THU_NGHIEM.md) mục 2, 2b) |

Bảng số liệu đầu tab: kích thước, số nét, số lần nhấc bút, độ dài vẽ / di chuyển, thời gian ước tính (có gia tốc, thời gian nhấc bút và giới hạn ~125 dòng/giây; [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 12), có nằm trong vùng máy không. Rê chuột vào dòng trạng thái để xem thời gian xử lý từng bước.

---

## 3. Bộ thông số dựng sẵn (preset) và chọn kiểu nét

| Preset | Kiểu | Thông số đặc biệt | Hợp với |
|---|---|---|---|
| Chân dung | **đan chéo + theo dáng** 5 mức | khử nhiễu, gamma 1 | ảnh tự chụp, mặt người đủ sáng |
| Phong cảnh | sóng biên độ, góc 30° | CLAHE | trời mây, nhà, cảnh đêm, hoàng hôn |
| Cận cảnh / Đồ vật | xoắn ốc **4 mức** | gamma 1 | cốc, đồ ăn, đồ vật |
| **Phác họa ảnh** (13/11/2026) | viền, chi tiết Vừa, **XDoG** | khử nhiễu | ảnh chụp chỉ muốn nét viền (người, thú, đồ vật) |
| Ảnh 2D / Hình vẽ | viền, chi tiết Vừa | | sticker, hoạt hình, truyện tranh |
| Schematic | viền, chi tiết Vừa | mức đen 60 / trắng 200 (cắt nền xám) | sơ đồ mạch, bản vẽ scan, mạch in đơn giản |

Preset chỉ là dữ liệu (`frontend/js/views/drawing/presets.js`): mỗi preset ghi đè vài ô của một bộ chung `BASE`.

Danh sách kiểu nét từ 13/11/2026 (`spec.UI_STYLES`; zigzag, sóng thường, đan 3 hướng, theo dáng thuần đã ẩn, mã vẫn giữ, [09](09_QUYET_DINH_THIET_KE.md) P23, P25):

| Kiểu nét | Số nét / nhấc bút | Ghi chú |
|---|---|---|
| Đan chéo + theo dáng | như gạch chéo (+1–5 %) | **mặc định**; đường cong ôm viền mắt / mũi / mặt, đan chéo gánh tông |
| Gạch chéo chồng lớp | vừa | tông nhạt một hướng, đậm thêm hướng vuông góc |
| Sóng biên độ | ít nhất | tông liền, mượt; vùng rất đậm thêm lớp gạch thẳng |
| Xoắn ốc | nhiều nhất | đậm nhanh, ô rất đậm có vệt chữ thập |
| Viền | ít | nét mực ≤ 4 mm → một đường giữa; mảng → viền quanh mảng. Ô tích **"Dùng XDoG"** (chỉ hiện ở kiểu này): viền ảnh chụp rõ hơn. Ô "Thêm lớp viền" trên kiểu tô khác luôn dùng XDoG |

Đan chéo, xoắn ốc, kiểu lai có **đường cong tông** đo trên giấy thật (Sakura 0,5, mặt bóng Ivory; [06](06_THUAT_TOAN_XU_LY_ANH.md) 8.12): không cần chỉnh gamma để bù vùng trung bình.

**Nhiều màu (2–4):** mỗi màu một tệp G-code riêng, tên có mã màu (vd `draw-2-3231a7.gcode`). Vẽ xong tệp nào thì đổi bút rồi nạp tệp kế. Kiểu Viền luôn đơn sắc.

---

## 4. Luồng dữ liệu: từ chọn tệp tới bản thảo

```
[Trình duyệt: views/drawing.js]
 acceptFile            kiểm đuôi tệp, cỡ (ảnh ≤ 40 MB, SVG ≤ 20 MB)
 startImport           lib/imageprep.js thu nhỏ ảnh về đúng cỡ cần (theo khung và bút)
                       params.importOptions(): gom các ô thành JSON
                       POST /api/draw/import  (multipart: file + options)  → nhận mã tác vụ
 poll                  GET /api/draw/tasks/{id} mỗi 0,35 s → thanh tiến trình
        │
[Máy chủ]
 api/draw.py           nhận tệp, kiểm vai trò, giao cho tasks.py
 tasks.py              MỘT luồng worker; yêu cầu mới hủy yêu cầu cũ (máy yếu)
 isolated.py           chạy raster.build_raster trong TIẾN TRÌNH CON ưu tiên thấp
                       (hủy = kết thúc hẳn tiến trình; quá 600 s hoặc quá 4 GB RAM thì dừng)
 raster.build_raster   đọc → sắc độ → tạo nét → vpype tối ưu        (06_THUAT_TOAN_XU_LY_ANH.md)
 store.TASKS           giữ nét trong RAM (3 bản gần nhất) để đổi bố trí không phải làm lại
        │
[Trình duyệt]
 finishImport          GET /api/draw/tasks/{id}/preview: nét RÚT GỌN (≤ 100 000 điểm), tọa độ gốc
 canvas.js             vẽ nét lên tờ giấy; kéo / co giãn / xoay ngay trên trình duyệt
                       bằng lib/paper.js (bản JS của layout.py, không gọi mạng)
 scheduleGcode         sau 0,4 s yên: POST /api/draw/gcode → bố trí + G-code + số liệu (chưa lưu)
 saveDraft             POST /api/draw/drafts → lưu bản thảo lên đĩa
 sendToControl         lưu bản thảo → draftstore.loadIntoControl → jobstore.setFile → sang tab Điều khiển
```

**Kéo khung lệch quá 12 %** so với cỡ lúc tạo nét thì giao diện tự tạo lại nét sau 0,8 s (`scheduleRetrace`). Lý do: khoảng cách nét tính bằng mm thật. Nếu chỉ phóng hình học, nét sẽ thưa ra hoặc dày đặc lại so với bề rộng bút. Đổi dưới 12 % thì chỉ phóng hình học. SVG không bị ảnh hưởng.

**Gõ dở một ô số** (vd gõ "4" trên đường tới "4000"): giao diện bỏ qua giá trị ngoài khoảng đang gõ dở, không báo lỗi chớp nháy (`onParamChange`).

---

## 5. Ba nhóm việc: nặng, nhẹ, rất nhẹ

| Nhóm | Việc | Chạy ở | Khi nào chạy lại |
|---|---|---|---|
| **Nặng** | ảnh → nét (đọc, sắc độ, tô / viền, chia màu, vpype) | tiến trình con trên máy chủ | đổi ảnh, vùng cắt, tiền xử lý, kiểu nét, bút, số màu, hoặc kéo khung lệch > 12 % |
| **Nhẹ** | bố trí + G-code + số liệu | máy chủ (vài trăm ms) | đổi giấy, lề, vị trí, xoay, lật, tốc độ, Z |
| **Rất nhẹ** | kéo / co giãn khung, xem trước độ sáng, thu nhỏ ảnh trước khi gửi | trình duyệt | mỗi lần kéo |

Vì sao tách: MiniPC yếu phải vừa điều khiển máy vừa xử lý ảnh. Một lần tạo nét dùng lại được cho nhiều lần đổi vị trí. Tiến trình con ưu tiên thấp nên ảnh nặng không làm giật luồng gửi G-code.

Đo trên laptop (ảnh 1200×1600, A4): zigzag 0,1–0,7 s, sóng 0,4–1,5 s, xoắn ốc 0,4–1,6 s. ⚠ Chưa đo trên MiniPC i5-3210M.

---

## 6. Tham số: khai báo một chỗ

Mọi tham số vẽ khai báo **một lần** ở `backend/app/services/drawing/spec.py`: tên, kiểu, mặc định, nhỏ nhất, lớn nhất. Máy chủ dùng nó để kiểm đầu vào; trình duyệt lấy qua `GET /api/draw/schema` để đặt giới hạn cho ô.

| Nhóm | Ví dụ tham số |
|---|---|
| `layout` | khổ giấy, lề (5 mm), rộng / cao khung, căn giữa, lật, đảo thứ tự, xoay 0/90/180/270 |
| `gcode` | tốc độ vẽ 5000, di chuyển 6000, nâng bút 3000, hạ bút (trống = như nâng), chờ 0,05 / 0,05 s, độ chính xác 3 chữ số |
| `machine` | vùng máy 285 × 318, hành trình Z, tốc độ G0, `invert_y` (tắt) |
| `optimize` | nối nét 0,1 mm, bớt điểm 0,05 mm, bỏ nét < 0,5 mm, sắp xếp, 2-opt 50 lượt, **`group_levels`** (vẽ lần lượt từng mức đậm nhạt; mặc định **tắt** từ 12/11/2026), **`bridge`** (mặc định bật: ảnh tô đơn sắc, nối nét gần ≤ 4 × bề rộng nét trong vùng đậm thay vì nhấc bút) |
| `svg` | sai số chia đường cong 0,1 mm, khung theo nội dung hay theo trang |
| `raster` | bút (`pen_width_mm` = bề rộng nét đo trên giấy; giao diện chọn theo tên bút: UB-155 0,38, UM-100 0,40, Sakura 0,50, bút bi 0,50, hoặc Tùy chọn; đo 12/11/2026), độ phân giải tự tính, vùng cắt, gamma, mức đen / trắng, tự cân sáng, CLAHE, khử nhiễu |
| `style` | kiểu (`spec.STYLES`; giao diện hiện `spec.UI_STYLES`), thêm viền, chi tiết viền, số mức (3–5), góc (45°), khoảng cách nét, biên độ sóng, đảo |
| `palette` | đơn sắc / nhiều màu, số màu (2–4), bỏ nền |

**Thêm một ô mới** phải chạm 5 chỗ: dòng `Param(...)` trong `spec.py` → tệp Python dùng nó → ô trong `index.html` → một dòng trong bảng `FIELDS` của `views/drawing/params.js` → khóa chữ trong `vi.json` và `en.json` ([03_CAU_TRUC_PHAN_MEM.md](03_CAU_TRUC_PHAN_MEM.md) mục 6).

---

## 7. Hợp đồng API

Mọi lỗi có dạng `{"error": {"code", "message"}}`. Trình duyệt dịch theo `code` (khóa `drawing.error.<code>`). Tọa độ nét luôn là **mm, gốc trên trái, Y xuống**.

| Route | Việc | Trả về |
|---|---|---|
| `POST /api/customer` (khách) · `GET /api/customer` · `GET /api/customer/{id}/image` · `POST …/seen` · `DELETE …` (quản lý) | ảnh khách gửi, xem [08_TRIEN_KHAI.md](08_TRIEN_KHAI.md) B4 | `{item}` / `{items, days}` |
| `POST /api/draw/testsheet` | tờ thử máy thành bản thảo (`kind` = lift / lost / accel / speed / drag, kèm `options`); tờ nhấc bút trả thêm `rows` (hàng N ↔ Z nhấc, chờ, tốc độ hạ) | `{draft, rows?, warnings}` |
| `GET /api/draw/schema` | tham số các nhóm, khổ giấy, bút, kiểu tô, giới hạn | `{papers, pens, params, styles, limits}` |
| `POST /api/draw/import` | multipart `file` + `options` JSON; tự nhận SVG / ảnh (`/svg` là bí danh cũ) | `202 {task, state}` |
| `GET /api/draw/tasks/{id}` | trạng thái tác vụ | `{state, step, progress 0..1, message, source?, warnings?, error?}` |
| `POST /api/draw/tasks/{id}/cancel` · `DELETE …` | hủy · bỏ khỏi bộ nhớ | `{ok}` |
| `GET /api/draw/tasks/{id}/preview` | nét rút gọn, tọa độ gốc trước bố trí | `{bounds, layers:[{id, color, strokes}]}` |
| `POST /api/draw/gcode` | bố trí + G-code + số liệu (không lưu) | `{files[], paper, box, warnings}` |
| `POST /api/draw/drafts` | tạo G-code rồi lưu bản thảo | `{draft}` |
| `GET /api/draw/drafts` · `/{id}` · `/{id}/gcode/{tệp}` · `/{id}/preview.svg` | danh sách · thông tin · G-code · ảnh minh họa | |
| `PATCH /api/draw/drafts/{id}` | `{name?, pinned?, priority?}` | `{draft}` |
| `POST /api/draw/drafts/reorder` | `{ids: [...]}` thứ tự mới | `{drafts}` |
| `DELETE /api/draw/drafts/{id}` | xóa | `{ok}` |
| `POST /api/draw/drafts/import-gcode` | tệp G-code có sẵn → một bản thảo | `{draft, warnings}` |
| `POST /api/draw/calibration` | tờ mẫu hiệu chỉnh bút thành bản thảo (giao diện không còn nút) | `{draft, warnings}` |
| `GET / PUT /api/draw/settings` | hạn mức bản thảo (số bản, MB) | `{settings, limits, folder}` |

Khóa `options` của `/import`: `svg`, `optimize`, `raster`, `style`, `palette`, `layout`. Với ảnh, `layout` chỉ là **hộp tham chiếu** (khung vẽ thật `width_mm` / `height_mm`, hoặc phần trong lề tờ giấy) để tính khoảng cách nét theo mm.

**Thử tay không qua giao diện:** mở `http://127.0.0.1:8000/docs`, gọi `/api/draw/import` với một SVG và `options = {"svg": {"frame": "page"}}`, hỏi `/tasks/{id}` tới khi `done`, rồi gọi `/api/draw/gcode` với `{"task", "machine": {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000}, "gcode": {"pen_up_z": 3, "pen_down_z": 0}}`.

---

## 8. Bản thảo trên đĩa

```
data/drafts/<yyyymmdd-hhmmss>-<tên>/
    meta.json                   tham số đã dùng, số liệu, ghim, ưu tiên, tên
    draw.gcode                  (đơn sắc)   hoặc   draw-1-181b1b.gcode, draw-2-3231a7.gcode … (nhiều màu)
    preview.svg                 ảnh minh họa
```
- Ảnh gốc **không bao giờ ghi ra đĩa**; chỉ nằm trong RAM lúc xử lý.
- Tên thư mục kiểm bằng biểu thức chính quy, chặn `..`, chỉ ghi trong thư mục đã định. Ghi nguyên tử (ghi tệp tạm rồi đổi tên).
- Vượt hạn mức (số bản hoặc MB, Cài đặt → Bản thảo): xóa bản **cũ nhất không ghim**.
- Mỗi bản vài trăm KB.

---

## 9. Tệp mã liên quan

| Tệp | Vai trò |
|---|---|
| `frontend/js/views/drawing.js` | điều phối tab: nạp tệp, hỏi tiến trình, tạo lại nét, G-code, lưu, chuyển tab |
| `frontend/js/views/drawing/params.js` | các ô ⇄ JSON gửi máy chủ (bảng `FIELDS`), ẩn / hiện ô theo kiểu nét |
| `frontend/js/views/drawing/canvas.js` | canvas tờ giấy: lưới, thước mm, lề, nét với độ rộng bút thật, 8 tay nắm, hít lề |
| `frontend/js/views/drawing/crop.js` · `tonepreview.js` · `presets.js` | cắt ảnh · xem trước độ sáng · bộ thông số dựng sẵn |
| `frontend/js/lib/paper.js` · `imageprep.js` | bố trí (bản JS của `layout.py`) · thu nhỏ ảnh + công thức độ sáng (khớp `raster_in.py` / `tone.py`); cả hai có test đối chiếu với Python |
| `frontend/js/views/drafts.js` · `stores/draftstore.js` | danh sách bản thảo (dùng chung với Hàng đợi ở tab Điều khiển) |
| `backend/app/api/draw.py` | các route `/api/draw/*` (mỏng) |
| `backend/app/services/drawing/` | dây chuyền: `spec` (tham số), `tasks` + `isolated` (chạy nền), `raster_in` → `tone` → `styles` / `hatch` / `edges` / `trace` / `palette` → `optimize` → `layout` → `gcode`; `svg_in` (SVG), `store` (bộ nhớ tạm), `preview` (nét rút gọn), `drafts` (bản thảo), `service` (ghép bố trí + G-code + kiểm bằng `clean_gcode`), `gcode_import`, `calibration` |
