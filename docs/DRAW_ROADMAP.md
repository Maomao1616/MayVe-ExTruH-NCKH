# ExtruXY – Roadmap tab Tạo bản vẽ (28/10/2026)

Ký hiệu: ✅ đã viết + test lõi · ⏳ chưa làm · ⚠ giả định chưa kiểm chứng.
Quy tắc làm song song (chỉ sửa file thuộc tab vẽ, khóa `draw.*` ở cuối hai file ngôn ngữ, router riêng, giao G-code qua `jobstore.setFile`, nhánh Git `draw`) nằm trong hướng dẫn giao tab; tệp này không lặp lại.

## 1. Thiết kế
- **Dây chuyền, mỗi bước một hàm thuần:** nạp ảnh → tiền xử lý → vector hóa → bố trí (mm) → tối ưu → G-code.
- **Tham số khai báo một chỗ** (`services/drawing/spec.py`): mặc định + giới hạn; dùng để kiểm tra đầu vào và trả cho frontend qua `GET /api/draw/schema`. Thêm tham số = sửa một dòng.
- **Kiểu vector hóa là sổ đăng ký** (`registry.py`): thêm kiểu = 1 file + 1 dòng đăng ký + 1 khóa `draw.*`.
- **Dữ liệu trung gian theo lớp** (một lớp = một bút). Mặc định một lớp; tách màu/mức sáng dùng nhiều lớp, **mỗi lớp một tệp G-code**, không dùng `M0` (chưa thử).
- **Backend không tự đặt số của máy:** vùng làm việc, hành trình Z, tốc độ tối đa, Z bút do frontend gửi (lấy từ `MACHINE` trong `frontend/js/core/config.js`).
- **Điểm đổi trục duy nhất:** `gcode.to_machine` + tham số `invert_y` (⚠ hướng trục giả định C5).
- **Thư viện:** vpype 1.15.0 + python-multipart (đã cài, GĐ2); Pillow, opencv-python-headless (GĐ3). Python 3.12.10, numpy 2.5.4, scipy 1.18.1, shapely 2.2.0. Tự viết bộ xuất G-code, không dùng plugin.
- **Dùng vpype qua hai cửa:** `vpype.read_multilayer_svg` (đọc SVG) và `vpype_cli.execute(chuỗi lệnh, Document)` (linemerge → linesimplify → filter → linesort). Chuỗi lệnh dựng bằng hàm thuần `optimize.build_pipeline` nên test được không cần vpype. vpype dùng px CSS (96 px = 1 inch); đổi sang mm ngay khi xuất.
- **Bộ nhớ tạm `store.py`:** giữ 3 bản vẽ đã nạp gần nhất, trả mã `task`; đổi tham số bố trí/G-code chỉ gọi lại `/gcode` với `task`, không nạp lại tệp.
- **Máy yếu:** thu nhỏ ảnh sớm (mặc định cạnh dài ≤ 1500 px ⚠), giới hạn dung lượng/số điểm, tác vụ nặng chạy luồng riêng có tiến trình + hủy, cache theo bước.

## 2. Quy ước bố trí (đã chốt trong code, theo ảnh minh họa của nhóm)
- Vùng máy 285×318 mm, gốc O(0,0) ở góc trên trái, Y xuống (⚠ C5). **Tờ giấy (A6/A5/A4/Letter/tùy chọn, đặt đứng) neo ở gốc O**, có thể dịch bằng `paper_x_mm/paper_y_mm`. Tờ giấy phải nằm trong vùng máy, nếu không → lỗi `paper_out_of_area`.
- `margin_mm` = lề an toàn tính từ mép TỜ GIẤY. Khung vẽ (`width_mm/height_mm`, mặc định lấp đầy phần trong lề) phải nằm trong phần trong lề, nếu không → lỗi `box_out_of_paper` (không tự cắt).
- `center` = căn khung vẽ giữa phần trong lề của tờ giấy; tắt thì dùng `offset_x_mm/offset_y_mm` tính từ góc trong lề.
- `fit=contain` thu ảnh về vừa khung, giữ tỷ lệ, căn nội dung giữa khung; `stretch` kéo giãn kín khung. Lật X/Y lấy tâm là tâm khung. `reverse` đảo thứ tự nét.
- Khổ giấy dựng sẵn (`papers` trong schema) để frontend điền rộng/cao và vẽ khung A6/A5/A4 trên khung 2D.
- `origin` (G54/máy) không vào backend: kiểm vùng ở backend giả định WCO = 0; frontend (D5) vẫn kiểm lại kể cả WCO khi Chạy.
- `lock_ratio` chỉ là việc của giao diện.

## 3. Định dạng G-code
Dòng đầu `G90 G21`; `F` ở G1 đầu tiên và mỗi khi đổi; ≤ 200 ký tự; không `$`, không G92/G10/G28/G53; bút lên Z=`pen_up_z` (Z5), xuống `pen_down_z` (Z0); mỗi nét kết thúc bút lên; chờ bằng `G4 P<giây>`. Di chuyển không vẽ: `G0` nếu `travel_feed ≥ rapid_feed`, ngược lại `G1` kèm F. Mặc định chỉ G0/G1; cung G2/G3 là tùy chọn ở GĐ6 (đã thử vẽ tròn trên máy thật; khung 2D chưa mô phỏng cung).
Đầu ra được kiểm bằng chính `clean_gcode` của JobRunner (phải giữ nguyên).

## 4. Lộ trình
| GĐ | Nội dung | Tình trạng |
|---|---|---|
| 0 | Khung thư mục, kiểu dữ liệu, sổ đăng ký, tham số + `/api/draw/schema`, `api/draw.py` | ✅ (chờ `pytest` thật) |
| 1 | Bố trí + G-code từ danh sách nét (`POST /api/draw/gcode`, nhiều lớp = nhiều tệp), thống kê, cảnh báo | ✅ (chờ `pytest` thật) |
| 2 | Đọc SVG (nhiều lớp) + tối ưu vpype (gộp nét, đơn giản hóa, lọc nét ngắn, sắp xếp) → demo đầu tiên SVG → Điều khiển → Xem trước/Chạy | ✅ (`POST /api/draw/svg`, `/gcode` nhận `task`; chờ test vpype thật) |
| 3 | Nạp PNG/JPG, EXIF, thu nhỏ sớm, crop/vùng che, auto-levels, tương phản, khử nhiễu, ngưỡng, ảnh xem trước | ⏳ |
| 4 | Vector hóa: đường giữa nét, viền, cạnh (XDoG/Canny) | ⏳ |
| 5 | Tô bóng: hatch song song, cross-hatch nhiều mức, cắt theo vùng | ⏳ |
| 6 | Chất lượng: sàn độ dài đoạn, linesort/reloop, ước tính thời gian, khớp cung G2/G3 (tùy chọn) | ⏳ |
| 7 | Frontend `drawing.js`: tải ảnh, đồng bộ ô thông số, xem trước nét, tiến trình/hủy, "Gửi sang Điều khiển" | ⏳ |
| 8 | Nhiều lớp: tách theo mức sáng và màu chủ đạo, mỗi lớp một kiểu nét, dấu đăng ký | ⏳ |
| 9 | Mở rộng: preset, gợi ý thông số, so sánh trước/sau, chữ → nét đơn (Hershey), stipple/xoắn ốc, xuất SVG, bộ ảnh chuẩn hồi quy | ⏳ |

## 5. Ảnh mẫu → hệ quả
- **Cảnh đêm tương phản cao:** cần auto-levels/gamma trước ngưỡng; đường giữa nét/cạnh; lọc nét ngắn (cửa ô lưới); tách màu có ích.
- **Ảnh chụp người, khổ dọc ~1:2,2:** cần crop; contain + căn giữa; hatch hợp hơn viền.
- **Ảnh CG nền mây, có watermark:** cần crop/vùng che; tách 3 mức sáng (trời không vẽ, mây hatch thưa, nhân vật hatch dày).
Test tự động chỉ dùng ảnh tự tạo bằng Pillow, không đưa ảnh mẫu vào Git.

## 6. Việc chưa kiểm chứng
Tên hàm chính xác của vpype; tốc độ/RAM thực trên máy yếu; ngưỡng 1500 px; hướng trục (C5); `G4 P` tính theo giây trên FluidNC 4.1.1; thời gian ước tính chưa tính gia tốc (D7).

## 7. Luồng thử GĐ2 (qua /docs)
1. `POST /api/draw/svg`: chọn tệp SVG, `options` = `{"svg": {"frame": "page"}}` → nhận `task`.
2. `POST /api/draw/gcode`: gửi `task`, `machine` (work_w 285, work_h 318, z_travel 5, rapid_feed 6000), `layout`, `gcode` (pen_up_z 5, pen_down_z 0) → nhận `files[].gcode`.
3. Dán G-code vào tab Điều khiển (hoặc nạp tệp) để Xem trước → tích xác nhận → Chạy.
`frame`: `content` = co theo hộp bao của nét (mặc định); `page` = giữ lề trang SVG. Tệp thử: `demo_ve_nha.svg` (2 lớp: đen, đỏ).
