# 02 — Cấu trúc (không đổi cây thư mục, không tạo tầng mới)

```
docs/        tài liệu 01–11 (cho người, đánh số) + AI_* (chỉ cho AI, dòng đầu ghi "FOR AI")
frontend/    index.html · css/ · locales/{vi,en}.json · js/{core,lib,stores,views}/ · tests/
backend/     app/{api,links,services,auth.py,main.py} · tests/ · tests/draw_test/
tools/       export_context.py · ink_sim.py · make_test_gcode.py · dong_goi.ps1
launcher/    bật / tắt bằng icon (Windows)
data/        không lên Git: bản thảo, macro, hồ sơ, sao lưu, PIN
```

## Frontend: phụ thuộc một chiều
`views → stores → lib`, mọi tầng → `core`.
- `views/`: mỗi tab / khối một tệp; là chủ **duy nhất** ghi lên phần tử HTML của khối đó. View không import view khác (trừ `control.js → preview.js`).
- `stores/`: dữ liệu dùng chung giữa view (tệp G-code đang nạp, bản thảo, macro).
- `lib/`: công thức thuần, không đụng giao diện, không gọi mạng (để test được).
- `core/`: gọi máy chủ, thăm dò, dịch chữ, hằng số máy.

## Backend
- `api/` mỏng: chỉ nhận yêu cầu, gọi `services/`, trả kết quả. Logic nằm ở `services/`.
- `links/`: nói chuyện với máy (`serial_link.py` thật, `sim_link.py` máy giả). Không tầng nào khác chạm serial.
- `services/drawing/`: ảnh → nét → G-code. Xử lý ảnh mặc định chạy ở **tiến trình con** (`isolated.py`).

## Một nguồn sự thật
- **Tham số vẽ:** `backend/app/services/drawing/spec.py`. Thêm tham số = dòng `Param` + ô trong `index.html` + dòng `FIELDS` trong `frontend/js/views/drawing/params.js` + khóa dịch vi/en. Không rải số cứng trong frontend.
- **Con số thuật toán:** hằng số VIẾT HOA ở đầu tệp Python, có chú thích tiếng Việt (vd `LINE_WIDTH_RATIO` trong `styles.py`).
- **Kiểu tô mới:** hàm `@FILLERS.register("tên")` trong `styles.py` + thêm vào `spec.STYLES` + `GROUPERS`. Không sửa `registry.py`.
- **Chữ hiển thị:** `frontend/locales/vi.json` và `en.json`, **cùng bộ khóa**; dấu `"` trong tiếng Việt phải thoát. `DrawError.code` ↔ khóa `drawing.error.<code>`. Terminal giữ tiếng Anh.

## Không làm
- Không thêm framework, bước build, hay thư viện nặng khi chưa hỏi (máy đích có thể là MiniPC i5 đời cũ, RAM thấp).
- Không tạo tệp tài liệu mới nếu nội dung thuộc tệp đã có.
- Không đổi `frontend/assets/css/tokens.css` hay giao diện lớn khi chưa hỏi; giữ nguyên CSS chủ dự án sửa tay.
