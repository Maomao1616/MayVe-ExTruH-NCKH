# 03 — Quy trình làm một việc

1. **Đọc** tài liệu liên quan (bảng ở `00-bat-dau.md`). Đổi hành vi đã chốt: đọc `docs/09_QUYET_DINH_THIET_KE.md` trước.
2. **Sửa mã và test cùng lúc.**
3. **Chạy test:**
   - Backend: `cd backend && python -m pytest` (~500 test). `test_old_logs_are_pruned` có thể hết giờ khi chạy chung; chạy riêng thì qua.
   - Frontend: `node --test frontend/tests/<tên>.test.mjs ...` (Windows: truyền **đường dẫn từng tệp**, không truyền thư mục).
4. **Đo thuật toán tô** bằng `python tools/ink_sim.py` (sai số tông, độ nhảy bậc, chiều dài, thời gian) và nêu số trước / sau. Mô phỏng chỉ để **so sánh**, không đoán độ đậm tuyệt đối trên giấy.
5. Đổi `layout.py` / `tone.py` / `raster_in.py`: sinh lại số chuẩn `python frontend/tests/fixtures/make_image_fixtures.py` và sửa bản JS tương ứng (`paper.js`, `imageprep.js`).
6. **Cập nhật tài liệu đúng chỗ:**

| Đã làm | Sửa |
|---|---|
| Xong một việc / còn việc cần thử | `docs/11_VIEC_CAN_LAM.md` |
| Đổi hành vi đã chốt | `docs/09_QUYET_DINH_THIET_KE.md` |
| Đổi API tab vẽ | `docs/05_TAB_TAO_BAN_VE.md` mục 7 + `spec.py` |
| Đổi con số / thuật toán | `docs/06_THUAT_TOAN_XU_LY_ANH.md` |
| Số đo máy mới | `docs/02_PHAN_CUNG_MAY.md` |
| Kết quả thử trên giấy | `docs/07_THU_NGHIEM.md` mục bảng ghi kết quả |
| Thêm / đổi / xóa tệp lớn | `python tools/export_context.py --map` (sinh lại `docs/AI_CODEMAP.md`, không sửa tay) |

7. **Báo trung thực:** test fail, bước bỏ qua, điều chưa thử trên máy thật / giấy / Ubuntu. Điều chỉ thử bằng mô phỏng thì nói là "mới thử mô phỏng, chưa in".

## Git
- **Chỉ commit khi chủ dự án bảo** ("commit"). **Không `git push`** (chủ dự án tự push).
- Mỗi commit một việc; message **tiếng Việt**, ngắn, nói việc đã làm.
- Không `--no-verify`, không `reset --hard`, không `push --force`.
- Không đưa vào Git: `data/`, `export/`, `Python/`, `.venv/`, `*.gcode` ở gốc.
- Nhiều AI cùng làm: trước khi sửa, chạy `git status` và `git log -5`; đừng ghi đè thay đổi chưa commit của người khác. Việc gối nhau thì làm trên nhánh riêng.

## Bẫy đã gặp
- Dùng Python **3.12** (3.15 thiếu gói).
- Console Windows cp1252 không in được tiếng Việt: script gọi `sys.stdout.reconfigure(encoding="utf-8")`.
- `.html`, `.css`, `.json` có thể là CRLF. Sửa tệp bằng công cụ sửa tệp, không dùng `sed`, heredoc hay `Set-Content` (dễ chèn BOM hoặc trượt chuỗi nhiều dòng). Sau khi thay hàng loạt, đọc lại đoạn đã sửa hoặc chạy test ngay.
- `launcher/*.ps1`, `*.vbs`, `tools/dong_goi.ps1`: **ASCII không dấu** (PowerShell 5.1). Zip ghi tên tệp bằng `/`.
- Backend cũ có thể còn chạy sau khi sửa mã: nhắc chủ dự án khởi động lại phần mềm.
- FastAPI bọc router: liệt kê route bằng `app.openapi()["paths"]`, không dùng `app.routes`.
- Thử launcher / cập nhật trong thư mục tạm, **kiểm cổng 8000 trống trước**.
