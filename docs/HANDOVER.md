# BỐI CẢNH DỰ ÁN CHO AI ASSISTANT MỚI

Chào bạn, tôi là người phát triển dự án **ExtruXY** (Máy vẽ CNC/Plotter dùng MKS DLC32 + FluidNC). Tôi không phải dân chuyên code, nên tôi cần bạn giải thích bằng lời thường trước khi đưa code, và chỉ đưa các đoạn code nhỏ để tôi dán vào file (không tạo lại toàn bộ file trừ khi tôi yêu cầu).

## 1. TÌNH TRẠNG HIỆN TẠI (Đã xong)
- **Backend & Frontend Core**: ổn định, test pass (xem `BRIEF.md` mục "Chạy và kiểm tra").
- **An toàn**: Hủy tác vụ 3 chế độ (Reset / Dừng êm / Dừng gấp), Tạm dừng và Hủy Jog tách riêng.
- **Máy thật**: đã thử Home, Jog, Streaming trên MKS DLC32 (không motor). Xem `MACHINE.md`.
- **Tab Tạo bản vẽ**: nạp SVG hoặc ảnh (PNG/JPG/WEBP) → nét (zigzag, sóng, xoắn ốc, viền; đơn sắc hoặc 2–4 màu; preset) → bố trí trên giấy A6/A5/A4 → G-code → bản thảo → Hàng đợi ở tab Điều khiển. Giải thích khối chức năng và nút bấm ở `BRIEF.md`.

## 2. VIỆC CÒN LẠI
- Thử ảnh thật trên máy thật: hiệu chỉnh khoảng cách gạch theo bút 0,2 / 0,4, ngưỡng viền, preset (`views/drawing/presets.js`).
- Chưa kiểm chứng trên máy thật: hướng trục, Z bút, thời gian ước tính (chưa tính gia tốc), `G4 P` tính bằng giây.
- Ghi nhận chưa làm: nhật ký ghi ra tệp (giữ 3 ngày), tiếp tục từ dòng N, test cho `lib/gcode.js`. Danh sách đầy đủ ở `BRIEF.md`.

## 3. QUY TẮC CỐT LÕI
- **Code**: Vanilla JS (ES6), Python (FastAPI). Không dùng framework nặng.
- **Giao tiếp**: Trả lời ngắn gọn, đi thẳng vào vấn đề. Dùng bảng biểu nếu cần.
- **Giới hạn**: Nếu sửa lỗi, chỉ đưa đoạn code cần thay. Hỏi lại tôi nếu cần rõ ngữ cảnh.

## 4. TÀI LIỆU ĐÍNH KÈM (Tôi đã có sẵn trong Project)
- `DECISIONS.md`: Các quyết định kiến trúc.
- `MACHINE.md`: Sự thật về phần cứng.
- `PROJECT_MAP.md`: Bản đồ file.
- `DRAW_ROADMAP.md`: Lộ trình làm tab Vẽ.
- `BRIEF.md`: Tóm tắt cấu trúc và nút chức năng (đọc đầu tiên).
- `PLAN_ONLINE.md`: Kế hoạch MiniPC Ubuntu, phân quyền PIN, tunnel.

---
*(Hết phần bàn giao. Bạn hãy chào tôi, xác nhận đã hiểu, rồi hỏi tôi muốn làm việc nào trong mục 2.)*