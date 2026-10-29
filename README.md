# ExtruXY – Phần mềm điều khiển máy vẽ

Phần mềm điều khiển riêng cho máy vẽ CoreXY (ExtruXY, vùng vẽ khoảng A4), chạy trên laptop và nối với bo mạch **MKS DLC32 V2.1** chạy firmware **FluidNC v4.1.1** qua cáp USB (chip CH340).

Mục tiêu trước mắt là một phần mềm **chạy ổn định trên laptop**. Hosting công khai, IoT, AI và sửa firmware là các giai đoạn sau.

## 1. Hướng đi

```
Trình duyệt (frontend)  ⇄  HTTP API / WebSocket  ⇄  Backend Python (FastAPI)
                                                          │
                                         ┌────────────────┴───────────────┐
                                      SimLink                         SerialLink
                                  (máy giả, để phát triển)      (USB/CH340 → MKS DLC32 → FluidNC → máy vẽ)
```

- **Backend** giữ kết nối với máy, đọc trạng thái, gửi lệnh, ghi nhật ký, kiểm tra an toàn. Sau này thêm hàng đợi tác vụ và xử lý ảnh → G-code.
- **Frontend** (HTML/CSS/JavaScript thuần) chỉ nói chuyện với backend qua API. **Frontend không bao giờ truy cập cổng serial trực tiếp.**
- **SimLink** và **SerialLink** có cùng giao diện (`BaseLink`). Nhờ vậy giao diện làm xong với máy giả vẫn chạy được khi nối máy thật.
- Giữ nguyên firmware FluidNC. Ưu tiên dùng giao thức có sẵn trước khi nghĩ tới sửa firmware.

Giao diện dự kiến có bốn khu vực: **Điều khiển**, **Trạng thái**, **Ảnh và đường vẽ**, **Cài đặt**.

## 2. Trạng thái hiện tại

| Hạng mục | Tình trạng |
|---|---|
| Môi trường (Python 3.12, venv, Git/GitHub) | Xong |
| Backend FastAPI + API cơ bản | Xong, có 28 test tự động chạy qua |
| SimLink (máy giả bắt chước FluidNC) | Xong, **chỉ là xấp xỉ** (xem mục 6) |
| SerialLink (máy thật) | Đã viết, **chưa thử trên board thật** |
| Thử board thật ở chế độ chỉ đọc | Chưa làm |
| Frontend | Chưa bắt đầu |
| Jog, Home, gửi G-code, SD, xử lý ảnh | Chưa làm |

Lớp API nằm trong `backend/app/api/` (có test tự động; thử tay bằng trang `/docs`). Cây thư mục và vai trò từng file: xem [docs/PROJECT_MAP.md](docs/PROJECT_MAP.md).

## 3. Cài đặt và chạy

Cần: **Python 3.12** và **Git**. Python 3.15 quá mới, nhiều thư viện (đặc biệt xử lý ảnh sau này) chưa có gói cài sẵn nên dễ lỗi cài đặt.

Windows PowerShell:

```powershell
git clone <địa-chỉ-kho-GitHub>
cd <thư-mục-kho>\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
uvicorn app.main:app --reload
```

- Nếu PowerShell báo "running scripts is disabled", chạy `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` rồi kích hoạt lại venv.
- Linux/macOS (chưa được thử): `python3.12 -m venv .venv`, `source .venv/bin/activate`, các lệnh còn lại giống nhau.
- Sau khi server chạy, mở `http://127.0.0.1:8000/docs` để thử API. Tắt server bằng Ctrl+C.
- `python -m pytest` phải báo **28 passed**. Muốn làm việc mà **không cần board**, chỉ dùng chế độ `sim`.

## 4. API hiện có

| API | Công dụng |
|---|---|
| `GET /api/health` | Kiểm tra backend sống |
| `GET /api/ports` | Liệt kê cổng COM |
| `POST /api/connect` | Kết nối: `{"mode": "sim"}` hoặc `{"mode": "serial", "port": "COM3"}` |
| `POST /api/disconnect` | Ngắt kết nối |
| `GET /api/connection` | Thông tin kết nối |
| `GET /api/status` | Trạng thái máy, vị trí, alarm/lỗi gần nhất |
| `POST /api/command` | Gửi một dòng lệnh (terminal) |
| `POST /api/realtime` | Gửi lệnh tức thời: `status`, `hold`, `resume`, `reset`, `jog_cancel` |
| `GET /api/log?since=N` | Nhật ký lệnh và phản hồi |

Lỗi trả về dạng ổn định `{"error": {"code": "...", "message": "..."}}` để frontend tự quyết định cách hiển thị.

## 5. Máy thật: chế độ chỉ đọc mặc định

- Với `mode: sim`, mọi lệnh đều được phép.
- Với `mode: serial`, khi chưa mở khóa, backend **chỉ cho lệnh đọc thông tin** (danh sách lấy từ `$CMD` của board thật: `$I`, `$$`, `$G`, `$E`, `$A`, `$CD`, `$Limits`, `$SS`, ... cả tên ngắn lẫn tên dài) và `$X` (mở Alarm, không làm máy chạy). Các lệnh còn lại (`$H`, jog, G-code) bị từ chối với mã `motion_locked`. Firmware vẫn là lớp chặn cuối (soft limit, `error:9` khi Alarm).
- Lệnh dừng (`hold`, `reset`, `jog_cancel`) **luôn** gửi được. Gõ `?`, `!`, `~` một mình trong terminal được gửi như ký tự tức thời, **kể cả khi đang chạy tác vụ**. Các dòng khác bị chặn trong lúc chạy tác vụ (`job_running`), vì mỗi dòng sinh thêm một `ok` làm lệch việc đếm `ok` của tác vụ.
- `SimLink` đã hiệu chỉnh theo log board thật ([docs/MACHINE.md](docs/MACHINE.md)): bật lên ở `ALARM:14`, `$X` xong chạy được G-code kể cả khi chưa Home, `!` khi Jog thì hủy jog, Reset tại Hold:0 không alarm, soft limit trả `ok` trước `ALARM:2`, ALARM:1 phải Reset trước `$X`.
- Để mở khóa chuyển động (chỉ khi máy đã sẵn sàng, có người đứng cạnh, tay gần công tắc nguồn):
  ```powershell
  $env:EXTRUXY_ALLOW_MOTION = "1"
  uvicorn app.main:app --reload
  ```
- Backend chỉ nhận yêu cầu có Host cục bộ (`localhost`, `127.0.0.1`, `[::1]`) và chặn POST đến từ trang web khác (Origin lạ), để một trang web bất kỳ đang mở trong trình duyệt không gửi được lệnh tới máy. **Không có đăng nhập**: muốn dùng qua mạng LAN thì phải đặt `$env:EXTRUXY_ALLOWED_HOSTS = "192.168.1.20,localhost"` (địa chỉ của máy chạy backend), chạy `uvicorn ... --host 0.0.0.0`, và hiểu rằng **mọi máy trong mạng đều điều khiển được máy vẽ**.
- Trong lúc Dừng êm/Dừng gấp đang chạy (`/api/status` → `"stopping": true`), backend từ chối job mới, lệnh chuyển động và `resume` (mã `stopping`). Lệnh `hold`/`reset`/`jog_cancel` vẫn luôn được phép. Nhật ký phân biệt rõ: *pen lift sent* (đã gửi), *rejected by firmware* (bị từ chối), *pen lift confirmed* (báo cáo trạng thái xác nhận Z đã tới đích).

## 6. Vì sao làm như vậy (các bước quan trọng)

1. **Python 3.12 và môi trường ảo (`.venv`).** Mỗi dự án có bộ thư viện riêng, đúng phiên bản ghi trong `requirements.txt`, nên máy của mọi người chạy giống nhau. Thư mục `.venv` không đưa lên Git (đã có trong `.gitignore`); người khác tự tạo lại bằng lệnh ở mục 3.
2. **Tách `SimLink` và `SerialLink`.** Phát triển giao diện và logic không cần cắm máy, nên không rủi ro cho phần cứng và nhiều người làm song song được. Đổi từ máy giả sang máy thật chỉ là đổi tham số `mode`.
3. **`SimLink` chỉ là xấp xỉ.** Hành vi dựa trên việc đọc source FluidNC v4.1.1, nhưng một số điểm chưa kiểm chứng: thời điểm gửi `ok`, phản hồi sau `ALARM:14`, và chuyển động dùng vận tốc không đổi (không có gia tốc). Phải **đối chiếu với log thật** từ board rồi chỉnh `SimLink` cho khớp, vì không sửa thì giao diện sẽ được xây trên những giả định sai.
4. **Chế độ chỉ đọc.** Lần đầu nối board thật, ta chỉ hỏi thông tin (phiên bản, cấu hình, danh sách lệnh) để chắc kết nối và bộ phân tích đúng, trước khi cho máy chuyển động. Sai lầm ở bước này không làm hỏng gì.
5. **Tắt DTR/RTS khi mở cổng.** Với mạch ESP32 qua CH340, hai tín hiệu này có thể làm board khởi động lại mỗi lần mở cổng. `SerialLink` tắt chúng trước khi mở. Vẫn có thể thấy banner khởi động, và đó là điều cần ghi lại ở lần thử đầu.
6. **Phân biệt các thao tác dừng.** `hold` (`!`) chỉ tạm dừng chuyển động và có thể `resume`. `reset` (Ctrl-X) dừng hẳn, mất vị trí nên phải home lại. Tắt motor khác với dừng chuyển động. **Nút "dừng" trên web không phải dừng khẩn cấp**: dừng khẩn cấp thật là công tắc cắt nguồn 12 V ở máy.
7. **`must_home: true` và `homed_guess`.** Firmware từ chối chuyển động G-code cho tới khi chạy `$H` (báo `ALARM:14`), nhưng jog vẫn được. FluidNC không có trường báo "đã home", nên backend chỉ **đoán** (`homed_guess`) qua trạng thái `Home` rồi `Idle` và `ok` sau `$H`. Đây là suy đoán, không tuyệt đối.
8. **`check_limits` khác `soft_limits`.** `check_limits` chỉ kiểm tra công tắc hành trình lúc bật nguồn hoặc reset. Giới hạn hành trình mềm là `soft_limits` của từng trục. Hai thứ này khác nhau.
9. **Frontend không chạm serial.** Chỉ backend giữ cổng serial; nếu không, hai chương trình tranh nhau cổng và không kiểm soát được lệnh gửi xuống máy.
10. **Không tự chạy G-code.** Ảnh → G-code luôn phải qua bước xem trước và người dùng xác nhận.

## 7. Lộ trình

| Giai đoạn | Nội dung | Tiến độ |
|---|---|---|
| A | Môi trường, repo | Xong |
| B | Backend cơ bản, simulator, test | Xong (SimLink cần hiệu chỉnh) |
| C | Frontend nền, bốn khu vực, WebSocket trạng thái | Tiếp theo |
| D | Máy thật: USB/CH340, đọc giao thức FluidNC, xử lý timeout/mất kết nối | Chờ thử board |
| E | Jog, Home, Terminal, Macro, khung xem đường đi, tác vụ, SD | Chưa |
| F | Ảnh (JPG/PNG/SVG) → vector → G-code, xem trước, kiểm tra vùng vẽ, xác nhận | Chưa |
| G | Cấu hình máy, lịch sử tác vụ, nhật ký, hoàn thiện | Chưa |
| H | AI/OCR, Linux/thiết bị nhỏ, host công khai, firmware tải G-code từ host | Chưa |

## 8. Cấu hình máy nền

File YAML nền: `configNCKH-13.yaml` (CoreXY, 80 steps/mm, X 285 mm, Y 310 mm, tối đa 6000 mm/phút, gia tốc 600 mm/s², servo bút ở GPIO32, `must_home: true`). Các thông số này là cấu hình đã thống nhất, **chưa phải mọi thứ đã được kiểm chứng trên máy thật** (homing, giới hạn hành trình, chiều trục, bước/mm, servo). Không tự ý đổi cấu hình nền khi chưa thảo luận.

## 9. Làm việc nhóm với Git

- Trước khi làm: `git pull`. Sau khi xong một việc nhỏ: `git add .`, `git commit -m "mô tả ngắn"`, `git push`.
- Mỗi commit một việc. Không đẩy file mật khẩu, token, thư mục `.venv`.
- Khi có từ hai người cùng sửa: dùng nhánh ngắn theo từng tính năng (ví dụ `feat/jog-panel`) và Pull Request nhỏ vào `main`. (Đây là đề xuất, nhóm sẽ chốt.)
- Người làm giao diện chủ yếu sửa `frontend/`, người làm backend chủ yếu sửa `backend/`. Hợp đồng API (mục 4) phải thống nhất trước khi đổi.
