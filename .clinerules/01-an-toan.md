# 01 — An toàn (không nới nếu chủ dự án chưa yêu cầu rõ)

1. Máy thật mặc định **chỉ đọc** (`allow_motion`). Không bao giờ tự chạy G-code: luôn xem trước + xác nhận.
2. Tab Tạo bản vẽ **không bao giờ gọi máy**. Nút web không phải dừng khẩn cấp (đừng viết chữ gợi ý ngược lại).
3. Frontend **không chạm serial**. Chỉ `frontend/js/core/api.js` gọi mạng; chỉ `frontend/js/core/state.js` thăm dò trạng thái.
4. Route API mới mặc định **chỉ quản lý**. Thêm route cho khách = một dòng trong `GUEST_ROUTES` (`backend/app/auth.py`) **và** sửa `backend/tests/test_auth.py`. Ẩn nút bằng `body.role-guest` chỉ là giao diện, không phải bảo mật.
5. **PIN thật không bao giờ vào Git, tài liệu hay câu trả lời.** PIN nằm ở `data\pin.txt` (gitignored). Chỉ nhắc tên khóa (`admin`, `unlock`), không in giá trị.
6. Không bịa số máy. Lấy từ `MACHINE` (`frontend/js/core/config.js`), hồ sơ máy hoặc `docs/02_PHAN_CUNG_MAY.md`. Điều chưa đo thì ghi "chưa kiểm chứng".
7. Không sửa cấu hình mạch ngoài các mục đã cho phép trong `backend/app/services/machine_config.py` (`FIELDS`): chân GPIO, kinematics, stepping sai có thể làm mạch không khởi động.
8. Không tự chạy lệnh làm máy chuyển động, tắt cổng 8000 (`launcher/stop.ps1` tắt mọi thứ đang nghe 8000), hay xóa `data/`.
