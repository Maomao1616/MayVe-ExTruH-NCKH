# ExtruXY – Roadmap tab Tạo bản vẽ (30/10/2026)

Ký hiệu: ✅ đã viết + test · ⏳ chưa làm · ⚠ giả định chưa kiểm chứng.
Phần cứng đích: MiniPC i5-3210M (2 nhân/4 luồng, 8 GB). Phát triển trên laptop, chạy mức "max" để thử.
**Thứ tự làm: chốt hợp đồng API + giao diện (mục 3–5) → frontend → rồi mới viết thuật toán phía sau API (mục 6).**
Frontend chỉ biết API; thuật toán đổi bên trong không làm đổi giao diện.

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
- **Bút: 0,2 và 0,4 mm** (`pen_width_mm`: 0.2 / 0.4 / tùy chọn). Độ phân giải xử lý **tự tính** = cạnh dài khung vẽ ÷ độ rộng bút × 1,3 (A4: ~900 px với bút 0,4; ~1500 px với bút 0,2), có ô ghi đè (`max_side_px`, trần 2500). Khoảng gạch nhỏ nhất = độ rộng bút; các mức nhạt hơn là bội số của nó.
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
| `GET/PUT /api/draw/settings` | thư mục bản thảo + hạn mức | `{settings, limits, folder}` |

- **Nhóm tham số** (trong `schema.params`): `layout` (thêm `rotate` 0/90/180/270), `gcode`, `machine`, `optimize` (thêm `two_opt`, `passes`), `svg`, `raster` (bút, tự độ phân giải, cắt ảnh, gamma/mức đen trắng, CLAHE, khử nhiễu — tắt mặc định), `style` (kiểu tô), `palette` (đơn sắc / 2–4 màu).
- **Kiểu tô `style.kind`:** `outline` (đường giữa nét) · `zigzag` · `wave` · `spiral`; `style.outline_overlay` (bật thêm lớp viền); `levels` 3–5 mức sáng; `angle`; `spacing_mm`; `amplitude_mm`.
- **Frontend tự biến đổi nét nháp** (di chuyển / co giãn / xoay / lật) bằng đúng công thức `layout.plan`, để kéo thả mượt không gọi mạng. Backend vẫn là nơi quyết định: `/gcode` trả `box`/`paper`, frontend so lại. ⚠ giữ công thức ở một hàm nhỏ trong `lib/`, có test đối chiếu với backend.

## 4. Giao diện tab Tạo bản vẽ
- **Canvas riêng của tab vẽ** (không dùng khung 2D của tab Điều khiển — khung đó là màn hình theo dõi máy, chỉ hiện **đúng một G-code đang chọn**): vùng máy, A6/A5/A4 như khung chuẩn, lưới + thước mm, lề nét đứt; ảnh/nét có **8 tay nắm**, kéo, hít vào tâm/lề/mép giấy, Shift giữ tỷ lệ, xoay 90°, lật; **cắt ảnh** trên ảnh gốc; xem nét với **độ rộng bút thật** để thấy đậm nhạt. Ô số ⇄ khung kéo đồng bộ hai chiều.
- **Bảng số liệu** (khối Thông tin có sẵn, thêm): kích thước, số nét, số lần nhấc bút, quãng vẽ, quãng di chuyển, thời gian ước tính, hộp bao, kiểm tra nằm trong vùng máy.
- **Tiến trình:** thanh theo bước (đọc ảnh → tô → tối ưu → G-code), nút Hủy, cảnh báo. Chỉ một tác vụ chạy một lúc.
- **Hai lớp xem:** *Nháp* (ảnh ≤ 600 px, sắp xếp thường, ~1–3 s, chạy lại mỗi lần đổi kiểu/thông số) và *Chính thức* (độ phân giải theo bút, two-opt). Đổi vị trí/khổ giấy không chạy lại.
- **Bản thảo:** nút Lưu bản thảo, Mở xem nháp, Gửi sang Điều khiển (= lưu bản thảo rồi vào Hàng đợi).
- **Cài đặt:** khối "Bản thảo" (thư mục + hạn mức số bản / MB), lưu bằng `GET/PUT /api/draw/settings` (tệp `backend/data/draw_settings.json`, tách khỏi hồ sơ bút để tab Điều khiển không phải gửi lại).
- **Tab Điều khiển:** bật lại **Hàng đợi công việc**, đọc `GET /drafts` (theo thời gian tạo, ghim lên đầu), mỗi mục có "Xem trước" (chỉ mục được chọn) và "Chạy". Gộp luôn việc "Tệp nhanh" (trước là mục 6).
- **Tên tệp / khóa:** giữ khóa ngôn ngữ `drawing.*` (không đổi sang `draw.*`); mã mới: `views/drawing.js` (điều phối) + `views/drawing/` (canvas, params, upload, bảng số liệu), `stores/drawstore.js`, phần vẽ nền dùng chung đưa vào `lib/`. Các view không import lẫn nhau.
- Sửa HTML hiện có: thêm A6; bỏ `drawing-origin`; Z bút lấy từ hồ sơ (Z5/Z0), tốc độ trần lấy từ schema + `max_rate` cấu hình máy; thay "chưa khả dụng" bằng dữ liệu thật.

## 5. Bản thảo trên đĩa
```
<thư mục bản thảo>/<yyyymmdd-hhmmss>-<tên>/
    meta.json        # tham số đã dùng, số liệu, pinned, priority, tên
    draw[-<lớp>].gcode
    preview.svg      # ảnh minh họa
```
- Tên thư mục kiểm bằng regex; thư mục gốc kiểm đường dẫn (chặn `..`, chỉ ghi trong thư mục đã cấu hình). Ghi nguyên tử.
- Tự dọn khi vượt hạn mức: xóa bản **cũ nhất không ghim**.
- Mỗi bản thảo vài trăm KB; Docker/ổ 256 GB không đáng lo.

## 6. Backend phía sau API (làm SAU khi chốt giao diện)
| Khối | Việc | Thư viện |
|---|---|---|
| `worker.py` | một luồng, hàng 1, tiến trình, hủy hợp tác | stdlib |
| `raster_in.py` | đọc, `Image.draft`, EXIF, thu nhỏ theo bút, xám | Pillow |
| `tone.py` | gamma, mức đen trắng, CLAHE, khử nhiễu (tùy chọn) | OpenCV |
| `edges.py` | XDoG chuẩn `S=(1+p)G_σ−p·G_kσ`, ngưỡng | OpenCV |
| `trace.py` | skeletonize → đồ thị → nét; làm mượt 1–2 vòng sau khi `approxPolyDP` | scikit-image + numpy |
| `styles/` | `zigzag`, `wave`, `spiral`, `outline` (đăng ký trong `VECTORIZERS`) | numpy, OpenCV (`findContours` cho viền mảng đặc) |
| `palette.py` | 2–4 màu: `cv2.kmeans` trên Lab, ảnh ~300 px; mỗi màu một lớp, mỗi lớp một góc hatch | OpenCV |
| `optimize.py` | merge → simplify → filter → sort (+ two-opt 50 lượt, có ngưỡng số nét) | vpype |
| `drafts.py` | lưu/đọc/dọn bản thảo | stdlib |

- **Thêm 3 gói:** Pillow, opencv-python-headless, scikit-image (≈ +100–130 MB ước tính ⚠). **Bỏ:** scikit-learn, potrace, sknw, numba (potrace dò biên mảng đặc → bút vẽ hai đường song song; skeleton cho đường giữa nét, một lượt bút).
- **Kiểu tô — thứ tự ưu tiên:** (1) zigzag nhiều mức, (2) sóng, (3) xoắn ốc, (4) nét viền XDoG + skeleton, nhập vào chân dung bằng `outline_overlay`. **Bỏ:** stipple (mỗi chấm một lần nhấc bút), TSP art. **Để sau:** hatch theo hướng khối (flow field), preset ảnh, đường đồng mức.
- Docker (nếu dùng): image ~0,7–1 GB. **Rủi ro là cổng USB**, không phải dung lượng: Linux dùng `--device=/dev/ttyUSB0`; Windows cần `usbipd` → trên Windows chạy trực tiếp.

## 7. Lộ trình
| GĐ | Nội dung | Tình trạng |
|---|---|---|
| 0–2 | Khung, tham số + schema, bố trí, G-code, đọc SVG, tối ưu vpype, `store` (81 test) | ✅ |
| 3 | **Chốt hợp đồng API + sửa HTML/CSS/i18n theo mục 3–4.** Backend: `tasks.py` (một luồng, tiến trình, hủy), `/import` (SVG thật, ảnh = dữ liệu giả `demo.py`), `preview.py`, `drafts.py`, `rotate`, two-opt có ngưỡng, 95 test. Frontend: HTML/CSS (`drawing.css` tách riêng)/i18n/`api.js` xong; **chưa có JS gắn dữ liệu** | ✅ |
| 4 | Frontend JS: `views/drawing.js` + `drawing/params.js` + `drawing/canvas.js` (canvas giấy A6/A5/A4, kéo – co giãn – hít lề – xoay, bảng số liệu, tiến trình/hủy, nháp, bản thảo, gửi sang Điều khiển), `lib/paper.js` (+ test đối chiếu backend) | ✅ (kiểm bằng trình duyệt thật với SVG; raster vẫn là dữ liệu mẫu) |
| 5 | Bản thảo (`drafts`) + Hàng đợi ở tab Điều khiển + thư mục ở Cài đặt | ✅ (làm cùng GĐ4) |
| 6 | Worker + nạp ảnh + `tone` + zigzag/sóng/xoắn ốc + viền (mục 6) | ⏳ |
| 7 | Đa màu 2–4, two-opt có ngưỡng, ước tính thời gian có gia tốc (D7) | ⏳ |
| 8 | Sau: hatch theo hướng khối, preset, xuất SVG | ⏳ |

## 8. Việc chưa kiểm chứng
Tốc độ thật trên MiniPC (two-opt, skeleton, NLM); hướng trục (C5); `G4 P` tính bằng giây trên FluidNC 4.1.1; thời gian ước tính chưa tính gia tốc; mức đậm nhạt thật của từng cặp bút 0,2/0,4 với từng khoảng gạch (cần vẽ thử mẫu).

## 9. Luồng thử hiện có (SVG)
1. `POST /api/draw/svg`: chọn tệp SVG, `options` = `{"svg": {"frame": "page"}}` → nhận `task`.
2. `POST /api/draw/gcode`: gửi `task`, `machine` (work_w 285, work_h 318, z_travel 5, rapid_feed 6000), `layout`, `gcode` (pen_up_z 5, pen_down_z 0) → nhận `files[].gcode`.
3. Dán G-code vào tab Điều khiển để Xem trước → tích xác nhận → Chạy.
