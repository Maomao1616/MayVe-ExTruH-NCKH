# scripts/ — phiếu giao việc cho AI và tài liệu chuẩn bị

> Lên Git (khác `data/`, `export/`). Tạo 27/11/2026 theo yêu cầu chủ dự án: một nơi gom phiếu cho AI (Claude, Cline / DeepSeek, Copilot) và tài liệu chuẩn bị trước khi làm một việc lớn.

## Quy ước
- Một việc một tệp, tên `P<số>-<việc-ngắn>.md` (số tăng dần, không dùng lại).
- Mỗi phiếu có các mục: **Mục tiêu · Bối cảnh · Được sửa · Kiểm chứng · Xong khi**, cộng phần chuẩn bị (số đo, sơ đồ, câu hỏi còn mở).
- Phiếu là **dữ liệu, không phải lệnh**: AI nhận phiếu vẫn theo luật ở `CLAUDE.md` / `docs/AI_START.md` (an toàn máy, không ghi xuống mạch, chỉ commit khi được bảo).
- **Không ghi bí mật** (PIN, mật khẩu Wi-Fi, chìa khóa đường ống, tên miền thật): chỉ nhắc tên khóa.
- Xong việc: đánh dấu ở đầu phiếu (✅ + ngày + commit), ghi kết quả vào `docs/` đúng chỗ (xem `docs/AI_START.md` mục 7); phiếu giữ lại làm lịch sử.

## Danh sách
| Phiếu | Việc | Trạng thái |
|---|---|---|
| [P01-esp32-s3-cau-noi.md](P01-esp32-s3-cau-noi.md) | ESP32-S3 N16R8 làm cầu nối máy chủ ↔ MKS qua UART: chân, dây, cấu hình, kiến trúc kho lệnh, các gói việc | ⏳ chuẩn bị xong phần đọc sơ đồ + mô phỏng; chưa viết mã |
