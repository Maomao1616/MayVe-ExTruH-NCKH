# BỐI CẢNH DỰ ÁN CHO AI ASSISTANT MỚI

Chào bạn, tôi là người phát triển dự án **ExtruXY** (Máy vẽ CNC/Plotter dùng MKS DLC32 + FluidNC). Tôi không phải dân chuyên code, nên tôi cần bạn giải thích bằng lời thường trước khi đưa code, và chỉ đưa các đoạn code nhỏ để tôi dán vào file (không tạo lại toàn bộ file trừ khi tôi yêu cầu).

## 1. TÌNH TRẠNG HIỆN TẠI (Đã xong)
- **Backend & Frontend Core**: Đã ổn định, test pass. 
- **Đã dọn dẹp**: Bỏ hoàn toàn tính năng Thẻ SD/Flash và tab Jobs (gộp vào Control).
- **An toàn**: Đã làm xong tính năng Hủy tác vụ 3 chế độ (Reset / Dừng êm / Dừng gấp). Nút Tạm dừng (Run) và Hủy Jog đã được tách riêng.
- **Máy thật**: Đã test các lệnh cơ bản (Home, Jog, Streaming) thành công trên MKS DLC32 (không motor). Xem file `MACHINE.md` để biết chi tiết.

## 2. BƯỚC TIẾP THEO (Giai đoạn B: Tab Tạo Bản Vẽ)
- **Mục tiêu**: Nạp file ảnh (SVG trước, PNG/JPG sau) -> Xử lý -> Sinh G-code -> Đẩy sang tab Control để chạy.
- **Backend**: Đã có skeleton trong `services/drawing/`. Đã có API `/api/draw/gcode`. 
- **Cần làm ngay**: Viết `loader.py` để đọc file SVG, thêm endpoint nhận file, và làm frontend `views/drawing.js`.

## 3. QUY TẮC CỐT LÕI
- **Code**: Vanilla JS (ES6), Python (FastAPI). Không dùng framework nặng.
- **Giao tiếp**: Trả lời ngắn gọn, đi thẳng vào vấn đề. Dùng bảng biểu nếu cần.
- **Giới hạn**: Nếu sửa lỗi, chỉ đưa đoạn code cần thay. Hỏi lại tôi nếu cần rõ ngữ cảnh.

## 4. TÀI LIỆU ĐÍNH KÈM (Tôi đã có sẵn trong Project)
- `DECISIONS.md`: Các quyết định kiến trúc.
- `MACHINE.md`: Sự thật về phần cứng.
- `PROJECT_MAP.md`: Bản đồ file.
- `DRAW_ROADMAP.md`: Lộ trình làm tab Vẽ.

---
*(Hết phần bàn giao. Bạn hãy chào tôi và xác nhận đã hiểu, sau đó chúng ta sẽ bắt tay vào việc tạo `loader.py` cho SVG)*