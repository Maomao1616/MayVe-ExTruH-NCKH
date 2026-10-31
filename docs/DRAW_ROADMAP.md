# Tab Tạo bản vẽ — thiết kế và hợp đồng API (30/10/2026)

Tài liệu thiết kế của tab Tạo bản vẽ: nguyên tắc, hợp đồng API, bản thảo, dây chuyền ảnh, các quyết định. **Tình trạng và việc còn
lại: `STATUS.md`** (không lặp ở đây). Phần cứng đích: MiniPC i5-3210M (2 nhân/4 luồng, 8 GB); phát triển trên laptop.
Frontend chỉ biết API; thuật toán đổi bên trong không làm đổi giao diện (hợp đồng đã chốt và đã cài đặt đầy đủ).

## 1. Nguyên tắc thiết kế
- **Mọi thứ là tham số**, khai báo MỘT chỗ (`services/drawing/spec.py`), trả cho frontend qua `GET /api/draw/schema`. Form của tab vẽ sinh từ schema, không rải số cứng. Máy yếu chỉ đổi giá trị, không xóa code.
- **Không ghi ảnh gốc ra đĩa.** Ảnh chỉ nằm trong RAM lúc xử lý. Ra đĩa chỉ có *bản thảo* (G-code + ảnh minh họa + meta, mục 5).
- **Một tác vụ nặng tại một thời điểm**, một luồng worker, có tiến trình và hủy. Yêu cầu mới hủy yêu cầu cũ. Song song chỉ nằm trong OpenCV (`cv2.setNumThreads(2)`, hạ còn 1 khi đang chạy máy). Không dùng multiprocessing. Không tự chia ảnh thành ô.
- **Backend không tự đặt số của máy**: vùng làm việc, hành trình Z, tốc độ, Z bút do frontend gửi (từ `MACHINE` / hồ sơ `/api/profile`).
- **Điểm đổi trục duy nhất:** `gcode.to_machine` + `invert_y` (⚠ hướng trục C5).
- Một lần vector hóa → nhiều lần đổi **vị trí / xoay / lật / khổ giấy** mà không vector lại. Riêng **kiểu tô (hatch)** phụ thuộc kích thước thật (khoảng gạch tính bằng mm), nên đổi **kích thước khung** thì phải tạo lại (frontend cảnh báo "mật độ đã đổi").
- **Chi phí vẽ chủ yếu là số lần nhấc bút** (~0,6 s mỗi nét: chờ 0,2 + 0,2 s và 2 lần chạy Z), không phải quãng di chuyển → ưu tiên kiểu vẽ ít nét liền.
- **Đo thực tế (laptop, 8000 nét):** `linesort` 0,85 s / 11,75 m di chuyển; `--two-opt --passes 50` 8,5 s / 8,97 m; `--passes 200` 9,3 s / 8,89 m. ⇒ two-opt **50 lượt**, thời gian tăng theo bình phương số nét ⇒ **vượt ngưỡng số nét (~15 000) thì chỉ sắp xếp thường**. ⚠ chưa đo trên MiniPC.
- RAM không phải nút thắt (ảnh xám 1500 px = 2,25 MB): không cần rải `gc.collect()`, chỉ không giữ mảng lớn sau khi xong.

## 2. Khung chuẩn và bút
- Khung thật (do nhóm vẽ trên mặt bàn): vùng máy **285×318 mm**, gốc O(0,0) góc trên trái, Y xuống; **A6 ⊂ A5 ⊂ A4 cùng neo ở O**. Khớp quy ước `layout.py` (tờ giấy neo ở O, dịch bằng `paper_x/y_mm`).
- `margin_mm` tính từ mép tờ giấy. Khung vẽ nằm trong phần trong lề; ra ngoài → lỗi `box_out_of_paper` (không tự cắt).
- **Bút: 0,2 và 0,4 mm** (`pen_width_mm`: 0.2 / 0.4 / tùy chọn). Độ phân giải xử lý **tự tính** = cạnh dài khung vẽ ÷ độ rộng bút × 1,3 (cạnh dài trong lề A4 = 287 mm: ~930 px với bút 0,4; ~1870 px với bút 0,2), có ô ghi đè (`max_side_px`, trần 2500). Khoảng gạch nhỏ nhất = độ rộng bút; các mức nhạt hơn là bội số của nó.
- `origin` (G54/máy) không vào backend: frontend kiểm lại kể cả WCO khi Chạy.

## 3. Hợp đồng API (CHỐT TRƯỚC KHI LÀM FRONTEND)
Mọi lỗi có dạng `{"error": {"code", "message"}}`; frontend dịch theo `code` (khóa `drawing.error.<code>`). Tọa độ nét: **mm, gốc trên trái, Y xuống**.

| Route | Việc | Trả về |
|---|---|---|
| `GET /api/draw/schema` | tham số các nhóm, khổ giấy, bút, kiểu tô, giới hạn | `{papers, pens, params{nhóm:[...]}, styles, limits}` |
| `POST /api/draw/import` | multipart `file` + `options` JSON; tự nhận SVG / ảnh. `/svg` giữ làm bí danh | `202 {task, state}` |
| `GET /api/draw/tasks/{id}` | trạng thái (frontend hỏi mỗi 0,5 s) | `{state: queued\|running\|done\|failed\|cancelled, step, progress 0..1, message, source?, warnings?, error?}` |
| `POST /api/draw/tasks/{id}/cancel` | hủy hợp tác (đặt cờ, các bước kiểm tra) | `{ok}` |
| `DELETE /api/draw/tasks/{id}` | bỏ khỏi bộ nhớ tạm | `{ok}` |
| `GET /api/draw/tasks/{id}/preview` | nét **rút gọn** để vẽ nháp (sai số ~0,3 mm, ≤ 100 000 điểm), **tọa độ nguồn trước bố trí** | `{bounds, layers:[{id,color,strokes}]}` |
| `POST /api/draw/gcode` | tính G-code + số liệu từ `task` (không lưu) | `{files[], paper, box, warnings}` (như hiện nay) |
| `POST /api/draw/drafts` | tạo G-code rồi **lưu bản thảo** | `{draft}` |
| `GET /api/draw/drafts` | danh sách (ghim trước, rồi theo thời gian tạo) | `{drafts[]}` |
| `GET /api/draw/drafts/{id}` · `/gcode/{layer}` · `/preview.svg` | meta · G-code · ảnh minh họa | |
| `PATCH /api/draw/drafts/{id}` | `{name?, pinned?, priority?}` | `{draft}` |
| `DELETE /api/draw/drafts/{id}` | xóa | `{ok}` |
| `GET/PUT /api/draw/settings` | hạn mức bản thảo (`max_count`, `max_mb`); `folder` chỉ để xem, cố định | `{settings, limits, folder}` |
| `POST /api/draw/drafts/import-gcode` | multipart `file` (G-code) + `work_w`, `work_h` → một bản thảo (không qua ảnh/SVG) | `{draft, warnings}` |
| `POST /api/draw/calibration` | `{machine, gcode, pen_width_mm, paper_x_mm?, paper_y_mm?}` → tờ mẫu hiệu chỉnh bút thành bản thảo (giao diện không còn nút) | `{draft, warnings}` |
| `POST /api/draw/drafts/reorder` | `{ids: [...]}` thứ tự mới (một nhóm ghim / không ghim); bản đầu ưu tiên cao nhất | `{drafts}` |

- **`options` của `/import`:** khóa `svg`, `optimize`, `raster`, `style`, `palette`, `layout`. Với ảnh, `layout` chỉ là **hộp tham chiếu**: `paper`/`margin_mm` cho phần trong lề, hoặc `width_mm`/`height_mm` (kích thước khung thật, theo hướng ảnh gốc) để khoảng cách gạch tính đúng theo mm. Kết quả `source.timings` = giây từng bước; `source.layers[].color` = mã màu (đa màu); id lớp đa màu dạng `<số>-<mãmàu>`.
- **Nhóm tham số** (trong `schema.params`): `layout` (thêm `rotate` 0/90/180/270), `gcode`, `machine`, `optimize` (thêm `two_opt`, `passes`), `svg`, `raster` (bút, tự độ phân giải, cắt ảnh, gamma/mức đen trắng, CLAHE, khử nhiễu — tắt mặc định), `style` (kiểu tô), `palette` (đơn sắc / 2–4 màu).
- **Kiểu tô `style.kind`:** `outline` (viền khối + nét mực) · `zigzag` · `wave` · `spiral`; `style.outline_overlay` (bật thêm lớp viền); `style.outline_detail` `low`/`medium`/`high` (mức chi tiết viền); `levels` 3–5 mức sáng; `angle`; `spacing_mm`; `amplitude_mm`.
- **Frontend tự biến đổi nét nháp** (di chuyển / co giãn / xoay / lật) bằng đúng công thức `layout.plan`, để kéo thả mượt không gọi mạng. Backend vẫn là nơi quyết định: `/gcode` trả `box`/`paper`, frontend so lại. ⚠ giữ công thức ở một hàm nhỏ trong `lib/`, có test đối chiếu với backend.

## 4. Giao diện tab Tạo bản vẽ
- **Canvas riêng của tab vẽ** (không dùng khung 2D của tab Điều khiển — khung đó là màn hình theo dõi máy, chỉ hiện **đúng một G-code đang chọn**): vùng máy, A6/A5/A4 như khung chuẩn, lưới + thước mm, lề nét đứt; ảnh/nét có **8 tay nắm**, kéo, hít vào tâm/lề/mép giấy, Shift giữ tỷ lệ, xoay 90°, lật; **cắt ảnh** trên ảnh gốc; xem nét với **độ rộng bút thật** để thấy đậm nhạt. Ô số ⇄ khung kéo đồng bộ hai chiều.
- **Bảng số liệu** (khối Thông tin có sẵn, thêm): kích thước, số nét, số lần nhấc bút, quãng vẽ, quãng di chuyển, thời gian ước tính, hộp bao, kiểm tra nằm trong vùng máy.
- **Tiến trình:** thanh theo bước (đọc ảnh → tô → tối ưu → G-code), nút Hủy, cảnh báo. Chỉ một tác vụ chạy một lúc.
- **Hai lớp xem:** *Nháp* (ảnh ≤ 600 px, sắp xếp thường, ~1–3 s, chạy lại mỗi lần đổi kiểu/thông số) và *Chính thức* (độ phân giải theo bút, two-opt). Đổi vị trí/khổ giấy không chạy lại.
- **Bản thảo:** nút Lưu bản thảo, Mở xem nháp, Gửi sang Điều khiển (= lưu bản thảo rồi vào Hàng đợi).
- **Cài đặt:** khối "Bản thảo" (hạn mức số bản / MB; thư mục cố định), lưu bằng `GET/PUT /api/draw/settings` (tệp `data/draw_settings.json`, tách khỏi hồ sơ bút để tab Điều khiển không phải gửi lại).
- **Tab Điều khiển:** bật lại **Hàng đợi công việc**, đọc `GET /drafts` (theo thời gian tạo, ghim lên đầu), mỗi mục có "Xem trước" (chỉ mục được chọn) và "Chạy". Gộp luôn việc "Tệp nhanh" (trước là mục 6).
- **Tên tệp / khóa:** giữ khóa ngôn ngữ `drawing.*` (không đổi sang `draw.*`); mã mới: `views/drawing.js` (điều phối) + `views/drawing/` (canvas, params, upload, bảng số liệu), `stores/drawstore.js`, phần vẽ nền dùng chung đưa vào `lib/`. Các view không import lẫn nhau.
- Sửa HTML hiện có: thêm A6; bỏ `drawing-origin`; Z bút lấy từ hồ sơ (Z5/Z0), tốc độ trần lấy từ schema + `max_rate` cấu hình máy; thay "chưa khả dụng" bằng dữ liệu thật.

## 5. Bản thảo trên đĩa
```
<thư mục bản thảo>/<yyyymmdd-hhmmss>-<tên>/
    meta.json        # tham số đã dùng, số liệu, pinned, priority, tên
    draw[-<n>-<mãmàu>].gcode   # nhiều màu: draw-1-181b1b.gcode, draw-2-3231a7.gcode ...
    preview.svg      # ảnh minh họa
```
- Tên thư mục kiểm bằng regex; thư mục gốc kiểm đường dẫn (chặn `..`, chỉ ghi trong thư mục đã cấu hình). Ghi nguyên tử.
- Tự dọn khi vượt hạn mức: xóa bản **cũ nhất không ghim**.
- Mỗi bản thảo vài trăm KB; Docker/ổ 256 GB không đáng lo.

## 6. Backend phía sau API (đã cài đặt)
| Khối | Việc | Thư viện |
|---|---|---|
| `worker.py` | một luồng, hàng 1, tiến trình, hủy hợp tác | stdlib |
| `raster_in.py` | đọc, `Image.draft`, EXIF, thu nhỏ theo bút, xám | Pillow |
| `tone.py` | gamma, mức đen trắng, CLAHE, khử nhiễu (tùy chọn) | OpenCV |
| `edges.py` | Viền: top-hat (nét mực ≤ 4 mm, vạch sáng ≤ 1,2 mm → đường giữa) + Canny trên ảnh bilateral (xám + kênh màu a/b Lab) cho ranh giới mảng + vòng viền chấm đậm + nối khe hở ≤ 1,5 mm theo hướng đầu mút | OpenCV, scipy (cKDTree), scikit-image (skeletonize) |
| `trace.py` | skeletonize → đồ thị → nét; làm mượt 1–2 vòng sau khi `approxPolyDP` | scikit-image + numpy |
| `styles/` | `zigzag`, `wave`, `spiral`, `outline` (đăng ký trong `VECTORIZERS`) | numpy, OpenCV (`findContours` cho viền mảng đặc) |
| `palette.py` | 2–4 màu: `cv2.kmeans` trên Lab, ảnh ~300 px; mỗi màu một lớp, mỗi lớp một góc hatch | OpenCV |
| `optimize.py` | merge → simplify → filter → sort (+ two-opt 50 lượt, có ngưỡng số nét) | vpype |
| `drafts.py` | lưu/đọc/dọn bản thảo | stdlib |

- **Thêm 3 gói:** Pillow, opencv-python-headless, scikit-image (≈ +100–130 MB ước tính ⚠). **Bỏ:** scikit-learn, potrace, sknw, numba (potrace dò biên mảng đặc → bút vẽ hai đường song song; skeleton cho đường giữa nét, một lượt bút).
- **Kiểu tô — thứ tự ưu tiên:** (1) zigzag nhiều mức, (2) sóng, (3) xoắn ốc, (4) nét viền (`edges.py`), nhập vào chân dung bằng `outline_overlay`. **Bỏ:** stipple (mỗi chấm một lần nhấc bút), TSP art. **Để sau:** hatch theo hướng khối (flow field), đường đồng mức (khác hẳn zigzag/sóng/xoắn ốc nhưng tốn công; chỉ làm khi viền + 4 kiểu hiện có không đủ).
- Docker (nếu dùng): image ~0,7–1 GB. **Rủi ro là cổng USB**, không phải dung lượng: Linux dùng `--device=/dev/ttyUSB0`; Windows cần `usbipd` → trên Windows chạy trực tiếp.

### Thứ tự xử lý ảnh (đã chốt)
EXIF + `Image.draft` → **crop** → **thu nhỏ** về độ phân giải làm việc (không phóng to) → xám → khử nhiễu → mức đen/trắng/gamma → CLAHE → làm nét → ngưỡng / XDoG → skeleton (đi nét). Các bước lọc làm SAU thu nhỏ (chi phí tỉ lệ số điểm ảnh; làm nét trước thu nhỏ bị mất và khuếch đại nhiễu); crop và EXIF mới làm trước. Hệ số × 1,3 (`oversample`) chỉ tốn thời gian XỬ LÝ; thời gian VẼ do khoảng cách gạch (mm), số mức, số lần nhấc bút quyết định.

### Độ phân giải và phóng to / thu nhỏ khung (đã làm)
- Khung vẽ thật (frontend gửi `layout.width_mm/height_mm`, theo hướng ảnh gốc) là hộp tham chiếu; thiếu thì lấy phần trong lề của tờ giấy. Khoảng cách gạch tính theo mm trên khung đó nên mật độ mực đúng theo bút ở kích thước thật.
- Cỡ làm việc (cạnh dài) = khung ÷ bút × 1,3, kẹp 400–4000 px, nháp = một nửa. Ảnh lớn thì thu nhỏ; ảnh nhỏ chỉ phóng nhẹ (bicubic) tới tối đa `UPSCALE_TO_PX = 720` để viền vùng đậm nhạt mịn, không phóng hơn (thêm điểm ảnh không thêm chi tiết).
- Kéo khung lệch quá 12% so với cỡ lúc tạo nét → frontend tự tạo lại nét sau 0,8 s (`scheduleRetrace` trong `views/drawing.js`), giữ nguyên khung đã kéo. Nếu không, chỉ phóng hình học sẽ làm gạch thưa ra / dày đặc so với bề rộng bút. Đổi dưới 12% chỉ phóng hình học. SVG không bị ảnh hưởng.
- Kích thước đo thử (ảnh 1200×1600, A4 trong lề, i5 máy dev): zigzag ~0,1–0,7 s, sóng ~0,4–1,5 s, xoắn ốc ~0,4–1,6 s. Thời gian trên MiniPC i5-3210M chưa đo.
- Viền (`edges.py`, đổi 31/10/2026 thay DoG): nét mực dày tới 4 mm (viền hoạt hình, chữ) → **một** đường giữa; mảng đậm rộng hơn → viền hai phía; chấm đậm (mắt) → vòng viền; ranh giới hai mảng khác sáng tối hoặc **khác màu cùng độ sáng** cũng có viền (cần ảnh màu: `raster.py` nạp màu khi có viền, `Field.rgb`); khe hở ≤ 1,5 mm được nối. `outline_detail`: `low` cho ảnh chụp (bỏ kết cấu lông, vân gỗ), `high` cho hình vẽ nét nhạt. Đa màu bỏ qua khi kiểu là viền (cảnh báo `palette_ignored`). Thử trên ảnh mẫu (gấu hoạt hình dán ảnh giường bệnh, sticker mảng màu, chân dung, cốc cà phê, mèo); 🧪 chưa in giấy.

### Quyết định sau lần thử đầu với ảnh thật (30/10/2026)
- **Giao diện gọn:** bỏ nút "Tạo nháp" và "Tạo G-code". Nạp tệp là tạo nét ngay ở độ phân giải đủ dùng; G-code tự tính lại sau mỗi lần đổi thông số (debounce 0,4 s). Còn nút **Tạo lại nét** (khi đổi thông số tạo nét) và **Tạo lại** (tính lại G-code).
- **Bộ thông số dựng sẵn** (`views/drawing/presets.js`, chỉ là dữ liệu, chung một `BASE`): Chân dung (zigzag 5 mức + khử nhiễu + viền Ít), Phong cảnh (sóng + CLAHE + viền Ít; dùng cả cho cảnh đêm, hoàng hôn), Cận cảnh / Đồ vật (xoắn ốc + viền Ít), Ảnh 2D / Hình vẽ (viền Vừa), Schematic / Bản vẽ kỹ thuật (viền, mức 60–200). Bỏ các preset trùng thông số (đêm, hoàng hôn, sân khấu, truyện tranh). Cách thử và chỉnh: `KIEM_TRA_VE.md`. 🧪 chưa in giấy. Chỉnh tay bất kỳ ô nào thì quay về "Tùy chỉnh". Chỉnh số trong file preset khi đã thử ảnh thật.
- **Đa màu:** `palette.split` phân cụm 2–4 màu trên Lab (nhấn sắc độ, lặp pixel rực để màu nhỏ như đèn màu vẫn có cụm). Mỗi màu một lớp, một tệp G-code, tên lớp = `<số>-<mãmàu hex>` nên tên tệp tự mang mã màu; đổi bút giữa các tệp. Màu chiếm diện tích rất nhỏ vẫn có thể bị gộp (ảnh đêm toàn nền tối).
- **Sóng bị vượt 200 000 dòng:** sóng lấy mẫu 5 điểm/chu kỳ, bước sóng tự dài ra nếu tổng nét làm vượt `WAVE_POINT_BUDGET` (100 000 điểm) → ảnh đậm vẫn ra G-code hợp lệ, sóng thưa hơn.
- **Xoắn ốc nhiều lần nhấc bút:** khe trắng ngắn hơn `BRIDGE_MM` (3 mm) trên đường xoắn ốc được vẽ liền (đỡ ~50% số nét ở ảnh thử).
- **Chớp "thông số không hợp lệ":** gõ "4" trên đường tới "4000" nhỏ hơn mức tối thiểu 10 nên backend báo lỗi; frontend nay bỏ qua giá trị ngoài khoảng đang gõ dở (`views/drawing.js`, `onParamChange`).
- **Cắt ảnh:** đã có trên giao diện (khung ảnh gốc → ✂ Cắt ảnh), gửi `crop_*` cho backend; xem DECISIONS P10.

### Xử lý ảnh trong tiến trình riêng và chuẩn bị ảnh ở trình duyệt (30/10/2026)
- `isolated.run_import` chạy `raster.build_raster` ở tiến trình con (ưu tiên thấp, 2 luồng toán học, RAM trần 4 GB trên Linux, quá giờ 600 s). Cha nhận tiến trình qua pipe, kết thúc con khi hủy. Kết quả giống hệt chạy trong tiến trình (có test so khớp).
- `info.timings` = giây từng bước; giao diện hiện tổng và chi tiết khi rê chuột.
- Trình duyệt thu nhỏ ảnh về đúng `work_side_px` (công thức trong `lib/imageprep.js`, test đối chiếu số với Python), chỉ thu nhỏ, lỗi thì gửi ảnh gốc. Backend bỏ qua chênh 1 điểm ảnh do làm tròn.
- Xem trước độ sáng ở trình duyệt khớp `tone.py` (không CLAHE/khử nhiễu), sai lệch tối đa 1 mức xám.

## 7. Tình trạng, việc chưa kiểm chứng
Xem `STATUS.md` (mục 2 đã xong, mục 3 chưa kiểm chứng, mục 4 còn lại). Điểm riêng của tab vẽ: tốc độ thật trên MiniPC (two-opt, skeleton, NLM), hướng trục, `G4 P` tính bằng giây trên FluidNC 4.1.1, thời gian ước tính chưa tính gia tốc, mức đậm nhạt thật của từng cặp bút 0,2/0,4 với từng khoảng gạch (cần vẽ thử mẫu).

## 8. Kiểm thử luồng SVG bằng tay (không qua giao diện)
1. `POST /api/draw/import`: multipart `file` = SVG, `options` = `{"svg": {"frame": "page"}}` → nhận `task` (tác vụ nền; hỏi `GET /api/draw/tasks/{task}` tới khi `done`).
2. `POST /api/draw/gcode`: `{"task", "machine": {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000}, "layout": {...}, "gcode": {"pen_up_z": 5, "pen_down_z": 0}}` → `files[].gcode`.
3. Thử tay tại `http://127.0.0.1:8000/docs`. Trong giao diện: dùng tab Tạo bản vẽ → Chuyển sang Điều khiển → Xem trước → tích xác nhận → Chạy.
