# ExtruXY – Tóm tắt backend (v0.2.0, đọc từ mã nguồn thật)

Mọi cấu trúc dữ liệu dưới đây lấy trực tiếp từ `routes.py`, `services/machine.py`, `protocol.py`, `links/sim_link.py`. Frontend dùng đúng tên trường này, **không đoán**.

## 1. Kiến trúc

```
Trình duyệt ──HTTP /api/*──> FastAPI (routes.py, mỏng)
                                  │
                           MachineService (singleton `machine`, giữ khóa RLock)
                                  │ listener / write
                       BaseLink ──┬── SimLink (giả FluidNC, luồng nền)
                                  └── SerialLink (pyserial, máy thật)
```

- `main.py` gắn router, trả lỗi dạng `{"error":{"code","message"}}` cho `ServiceError`, và phục vụ thư mục `frontend/` ở `/`.
- Một kết nối tại một thời điểm. Poller nền gửi `?` mỗi 0,25 s (`POLL_S`).
- Bật chuyển động trên máy thật bằng biến môi trường `EXTRUXY_ALLOW_MOTION=1`. Mặc định máy thật chỉ đọc.

## 2. API

| Phương thức | Đường dẫn | Vào | Ra |
|---|---|---|---|
| GET | `/api/health` | – | `{ok, service, version}` |
| GET | `/api/ports` | – | `{ports:[...]}` (lỗi `pyserial_missing` nếu thiếu) |
| GET | `/api/connection` | – | `connection` (mục 3) |
| POST | `/api/connect` | `{mode:"sim"\|"serial", port?, baud=115200 (9600–2000000), sim_speed=1 (0–100]}` | `connection` |
| POST | `/api/disconnect` | – | `connection` |
| GET | `/api/status` | – | snapshot (mục 3) |
| POST | `/api/command` | `{line}` (1–200 ký tự, đúng một dòng) | `{sent}` |
| POST | `/api/realtime` | `{action: status\|hold\|resume\|reset\|jog_cancel}` | `{sent}` |
| GET | `/api/log?since=N` | – | `{entries:[...], last_seq}` |

`/api/command` **không trả về `ok`/`error` của máy**. Kết quả lệnh chỉ thấy qua log (dòng `rx`) và `last_error`/`last_alarm`.

## 3. Cấu trúc dữ liệu

`GET /api/status` (snapshot):

```json
{
  "connection": { "connected": true, "mode": "sim", "port": null, "baud": null,
                  "lost_reason": null, "motion_unlocked": true },
  "machine": { "state": "Idle", "substate": null,
               "mpos": [0,0,0], "wpos": [0,0,0], "wco": null,
               "planner_free": 15, "rx_free": 128,
               "feed": 0, "spindle": 0, "sd": null, "pins": null },
  "homed_guess": false,
  "last_alarm": { "code": 14, "name": "Unhomed", "at": 1761350000.1 },
  "last_error": { "code": 15, "name": "TravelExceeded", "at": 1761350001.2 },
  "banner": "Grbl 3.9 [FluidNC v4.1.1 (sim)]",
  "updated_at": 1761350002.3
}
```

Quy ước quan trọng:
- `motion_unlocked` nằm trong `status.connection`, **không** nằm ở gốc. Sim luôn `true`; máy thật `true` chỉ khi có `EXTRUXY_ALLOW_MOTION=1`.
- Trạng thái máy ở `status.machine.state` (`Idle, Run, Jog, Hold, Home, Alarm`). `machine` là `null` khi chưa nhận báo cáo trạng thái nào (chưa kết nối hoặc vừa kết nối).
- `substate` chỉ có khi FluidNC gửi dạng `Hold:0` / `Hold:1`.
- `mpos`, `wpos`, `wco` là mảng 3 số (X, Y, Z) hoặc `null`. Service tự suy `wpos` từ `mpos − wco` khi đã biết WCO.
- `updated_at` là **giây epoch (float)** lúc backend nhận báo cáo trạng thái gần nhất, `null` nếu chưa có. Các trường này chỉ bị xóa khi kết nối lần mới, không xóa khi ngắt. Frontend phải kiểm tra connection.connected trước khi tin machine
- `last_alarm` / `last_error` **không tự xóa** khi alarm hết hoặc sau `$X`. Frontend chỉ coi alarm là đang hoạt động khi `machine.state === "Alarm"`.
- `homed_guess` chỉ là **đoán**: bật khi thấy `Home`→`Idle` hoặc nhận `ok` sau `$H`; tắt khi nhận alarm thuộc nhóm làm mất gốc {1,3,6,7,8,9,12,13,14,16}.
- `name` của alarm/error là `null` nếu mã chưa nằm trong bảng của `protocol.py` (ERROR_NAMES hiện chỉ có 8 mã: 3, 8, 9, 10, 11, 15, 16, 20). Frontend phải dịch theo `code`.

`GET /api/log?since=N`:

```json
{ "entries": [ { "seq": 12, "t": 1761350002.3, "dir": "tx", "source": "terminal", "text": "$I" } ],
  "last_seq": 12 }
```

- `dir`: `tx` (ta gửi), `rx` (máy trả), `sys` (hệ thống).
- `source`: `terminal`, `realtime`, `device`, `system`.
- `seq` tăng liên tục, **không reset khi kết nối lại**. Bộ đệm giữ 500 dòng gần nhất. Báo cáo trạng thái `<...>` **không** vào log.
- Frontend lưu `last_seq` và gọi `?since=last_seq`.

Lỗi: `{"error":{"code","message"}}` kèm mã HTTP. Riêng kiểm tra dữ liệu của Pydantic trả `{"detail":[...]}` (422), `api.js` đã đổi thành `validation_error`.

| `code` | HTTP | Khi nào |
|---|---|---|
| `already_connected` | 409 | Đang kết nối mà gọi connect |
| `not_connected` | 409 | Gửi lệnh/realtime khi chưa kết nối |
| `bad_request` | 400 | Thiếu port ở serial, lệnh rỗng hoặc nhiều dòng |
| `motion_locked` | 403 | Máy thật chỉ đọc, lệnh không nằm trong danh sách đọc |
| `link_error` | 502 | Mở/ghi cổng lỗi |
| `pyserial_missing` | 500 | Chưa cài pyserial |

Máy thật chỉ đọc cho phép: `$I, $CMD, $$, $#, $G, $CD, $SD/STATUS, $FILES/LISTGCODE` và các lệnh bắt đầu bằng `$SD/LIST`, `$LOCALFS/LIST`, `$LOCALFS/SHOW=`. Realtime (`hold/resume/reset/jog_cancel/status`) **không bị chặn** ở chế độ chỉ đọc.

## 4. SimLink – hành vi frontend có thể dựa vào

- Giới hạn mặc định `travel=(285, 310, 5)`, bật `must_home`. Rapid X/Y 6000, Z 3000 mm/phút. Planner 15, RX 128.
- Mới kết nối: `Idle`, vị trí 0,0,0, chưa Home.
- G-code có trục khi chưa Home → `[MSG:INFO: Unhomed axes: XY]` + `ALARM:14`, state `Alarm`, xóa hàng đợi.
- G-code ngoài hành trình → `ALARM:2`. Jog ngoài hành trình → `error:15`. Jog thiếu `F` hoặc trục → `error:16`.
- Khi `Alarm`: G-code và jog trả `error:9`. Chỉ `$X` (về `Idle`) và `$H` (cho phép từ `Idle`/`Alarm`) hoạt động.
- `$H`: state `Home` 1,5 giây, rồi đặt X,Y = 0, `Idle`, phát `ok`. Z không đổi.
- `G2/G3` → `error:20`. `$` lạ → `error:3`. `$H` khi đang chạy → `error:8`.
- `!` đưa `Run/Jog` → `Hold:1` rồi `Hold:0` sau 0,2 s. `~` tiếp tục.
- `reset` (Ctrl-X) khi `Run/Jog/Hold` → `ALARM:3`; khi `Home` → `ALARM:6`; khi `Idle` chỉ in banner.
- `jog_cancel` chỉ có tác dụng khi `Jog`. Chuyển động tốc độ không đổi (không mô phỏng gia tốc). `sim_speed` tăng tốc thời gian mô phỏng.
- Điểm chưa chắc (cần đối chiếu bằng log máy thật): thời điểm `ok` của một số lệnh, phản hồi sau `ALARM:14`.

## 5. Vấn đề đã phát hiện ở backend

1. **SimLink còn Y = 310**, trong khi `ConfigNCKH-14.yaml` ghi Y 318. Cần đổi `travel=(285.0, 318.0, 5.0)` và chú thích đầu file (đang ghi "configNCKH-13").
2. **`requirements.txt` và `requirements-dev.txt` mã hóa UTF-16 (có BOM)**. `pip` thường đọc được, nhưng nên chuyển UTF-8 cho an toàn (công cụ khác có thể lỗi).
3. **Chưa chạy được bộ test trong môi trường của mình** (không có `pytest`, không có mạng). Tình trạng test thật bạn phải chạy `pytest` phía bạn và báo lại.
4. `reset` không xóa cờ chờ `ok` của `$H` (`_homing_pending`). Sau reset giữa lúc đang Home, một `ok` đến muộn có thể làm `homed_guess` bật sai. Khả năng thấp, nhưng nên sửa.
5. `last_alarm` / `last_error` không tự hết hạn (đã nêu ở mục 3). Chọn một: để frontend xử lý theo `state`, hoặc backend xóa sau `$X`/reset.
6. `ok` của lệnh không được gắn với lệnh nào (chưa có hàng đợi lệnh). Đây là điều kiện bắt buộc cho việc gửi G-code từng dòng.
7. Bảng `ERROR_NAMES` còn ít mã. Mã khác trả `name: null`.

## 6. Việc backend tiếp theo (đề xuất, chờ bạn chọn)

- **A. Dọn nhanh (khoảng 1 buổi):** sửa các mục 1, 2, 4; thêm test cho `routes.py` (đã có test cho protocol, sim_link, machine service, chưa có test lớp API).
- **B. Thử máy thật chỉ đọc:** chạy `SerialLink` với `$I`, `$$`, `?` trên board thật; đối chiếu `protocol.py` và SimLink với log thật.
- **C. Gửi G-code từng dòng:** hàng đợi tác vụ chờ `ok`/`error`, có tạm dừng, dừng, kiểm tra vùng vẽ trước khi gửi.
