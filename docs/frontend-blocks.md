# Bản đồ khối giao diện (frontend)

Tài liệu này nối **nút/khối trên giao diện** với **lệnh gửi xuống máy** và **API backend**. Dùng chung cho người làm giao diện và người làm backend.

## Quy tắc quan trọng

- Có thể đổi **vị trí, kích thước, màu** của khối thoải mái. **Không đổi `id` và các thuộc tính `data-*`**, vì JavaScript sẽ gắn vào đó.
- Thêm hoặc bớt một khối thì phải sửa HTML và JS. Đổi chỗ khối chỉ cần sửa CSS.
- Mọi thứ chỉnh nhanh nằm ở **bảng biến đầu file `css/style.css`** (mục 1B).

## Bảng biến chỉnh bố cục (đầu `style.css`, mục 1B)

| Biến | Tác dụng | Mặc định |
|---|---|---|
| `--page-width` | Chiều rộng tối đa của trang | 1600px |
| `--font-size-base` | Cỡ chữ chính | 14px |
| `--layout-gap` | Khoảng cách giữa các khối | 20px |
| `--panel-padding` | Lề bên trong mỗi khối | 18px |
| `--control-height` | Chiều cao nút và ô nhập | 38px |
| `--sidebar-width` | Chiều rộng cột trái tab Điều khiển | 360px |
| `--canvas-height` | Chiều cao khung vẽ 2D (cố định) | 520px |
| `--canvas-aspect` | Tỉ lệ vùng làm việc X / Y | 285 / 318 |
| `--terminal-height` | Chiều cao ô log terminal | 180px |
| `--progress-max-width` | Chiều rộng tối đa tiến trình cạnh tiêu đề | 480px |
| `--jog-button-size` | Kích thước nút jog X/Y | 54px |
| `--icon-button-size` | Kích thước nút Zero/Home từng trục | 32px |
| `--accent-text` (bảng màu) | Màu chữ/biểu tượng nhấn (thay cho `--accent` quá tối) | #00ffff |

## Nút ở tab Điều khiển và lệnh tương ứng

Lệnh gửi qua `POST /api/command` (một dòng) hoặc `POST /api/realtime`.

| Nút | `id` | Lệnh | Ghi chú |
|---|---|---|---|
| Zero X / Y | `zero-x-btn`, `zero-y-btn` | `G10 L20 P1 X0` / `G10 L20 P1 Y0` | Đặt gốc làm việc (G54) tại vị trí hiện tại. Không làm máy chuyển động. |
| Zero tất cả | `zero-all-btn` | `G10 L20 P1 X0 Y0` | |
| Home X / Y | `home-x-btn`, `home-y-btn` | `$HX` / `$HY` | Chạy về công tắc hành trình của trục đó. Có trong FluidNC v4.1.1. |
| Home tất cả | `home-btn` | `$H` | |
| Mở khóa | `unlock-btn` | `$X` | Chỉ khi máy báo Alarm. |
| Jog X/Y | `[data-jog-axis]` | `$J=G91 G21 X{±bước} F{tốc độ}` | Bước từ `jog-distance`, tốc độ từ `jog-feed`. Hướng: ↑ là Y−, ↓ là Y+ (gốc ở góc trái phía xa). |
| XY 0 | `jog-center-btn` | `$J=G90 G21 X0 Y0 F{tốc độ}` | Về gốc làm việc. Chưa kiểm chứng jog dùng hệ tọa độ nào, cần thử trên máy thật. |
| Bút lên | `pen-up-btn` | `$J=G90 G21 Z5 F3000` | Z5 là bút lên (lấy từ cấu hình). |
| Bút xuống | `pen-down-btn` | `$J=G90 G21 Z0 F3000` | Z0 là bút xuống. |
| Hủy jog | `jog-cancel-btn` | realtime `jog_cancel` | |
| Tạm dừng | `pause-btn` | realtime `hold` | Luôn bật khi đã kết nối. |
| Tiếp tục | `resume-btn` | realtime `resume` | |
| Reset | `reset-btn` | realtime `reset` | Dừng mềm, **không phải dừng khẩn cấp**. Máy mất vị trí, phải Home lại. |
| Chạy | `run-job-btn` | (chưa có) | Chỉ bật khi đã tick `run-confirm`. Cần backend. |

Lưu ý kỹ thuật (đã đối chiếu source FluidNC v4.1.1):
- Cấu hình có `must_home: true`: **G-code chuyển động trước khi Home sinh `ALARM:14`**, còn **jog thì được**.
- Trục Z là servo nâng bút, **không có Home** (`homing cycle: 0`), nên không có nút Zero/Home cho Z.

## Khối chưa có backend (đang để khóa)

Tệp G-code (nạp, danh sách SD/Flash, dung lượng, Chạy), tiến trình tác vụ, Dừng tác vụ, hàng đợi và lịch sử (tab Công việc), tiền xử lý ảnh / vector hóa / tạo G-code (tab Tạo bản vẽ), đọc cấu hình máy (tab Cài đặt), lưu macro phía backend.

## Khối đã có dữ liệu từ backend

| Khối | API |
|---|---|
| Vị trí, trạng thái, feed, planner, RX | `GET /api/status` |
| Alarm / lỗi gần nhất, đã Home (ước đoán) | `GET /api/status` (`last_alarm`, `last_error`, `homed_guess`) |
| Chế độ chỉ đọc | `GET /api/connection` (`motion_unlocked`) |
| Danh sách cổng COM | `GET /api/ports` |
| Terminal, nhật ký | `POST /api/command`, `GET /api/log?since=N` |
