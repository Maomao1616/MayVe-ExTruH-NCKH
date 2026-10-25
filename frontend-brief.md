# ExtruXY – Chỉ dẫn viết JavaScript frontend (bàn giao cho AI khác)

Đọc kèm `project-handoff.md`, `docs/frontend-blocks.md` và `backend-summary.md` (cấu trúc dữ liệu thật của API). File này chỉ nói **phần còn lại phải làm và làm theo thứ tự nào**.

## 0. Hiện trạng (đã xong, đừng làm lại)

- HTML/CSS bốn tab, i18n (`i18n.js`, `vi.json`, `en.json`), chuyển tab bằng JS (`app.js`).
- `js/api.js`: **duy nhất** nơi gọi `fetch`, đã có 9 endpoint, lỗi chuẩn hóa thành `ApiError(code)`.
- `js/config.js`: hằng số máy, ngưỡng thăm dò. Mọi giả định chưa kiểm chứng ghi ở đây.
- `i18n.js` đã sửa để hiểu cú pháp `data-i18n="[title]khóa; khóa"`. Không quay lại bản cũ.

Còn rỗng: `state.js`, `views/control.js`, `views/settings.js`, `views/jobs.js`, `views/drawing.js`.

## 1. Quy tắc cứng (vi phạm là bị trả lại)

1. Không framework, không npm, không bước build. ES modules thuần.
2. `fetch` chỉ nằm trong `api.js`. Cần endpoint mới thì ghi vào `docs/api-requests.md`, **không tự bịa**, không sửa `backend/`.
3. Không đổi `id` và `data-*` đã có. Thêm/bớt khối phải báo rõ.
4. Không viết chữ cứng trong JS. Mọi chữ hiển thị đi qua `t('khóa')`, thêm khóa vào **cả** `vi.json` và `en.json`.
5. Không giả lập dữ liệu trông như thật. Mất backend hoặc `status.updated_at` (giây epoch) không đổi sau `POLL.staleMs` thì khóa điều khiển và hiện cảnh báo.
6. Không có chữ "E-STOP" / "Dừng khẩn cấp". Reset là dừng mềm.
7. Không tự động làm máy chuyển động. Mọi lệnh chuyển động do người bấm.
8. Hằng số máy lấy từ `config.js`, không rải số cứng.
9. Không ngầm nâng cấp: mọi thay đổi ngoài chỉ dẫn phải nêu rõ.

## 2. Thứ tự làm (mỗi bước xong phải chạy được với chế độ `sim` rồi mới sang bước sau)

### Bước 1 – `state.js` (bộ não dùng chung)
- Lưu: `connection`, `status` (snapshot), `log[]`, `lastOkAt`, `backendOnline`.
- Vòng thăm dò `/api/status` (mỗi `POLL.statusMs`) và `/api/log?since=last_seq` (mỗi `POLL.logMs`). Dùng `setTimeout` nối tiếp (không `setInterval`) để không chồng yêu cầu.
- Tạm dừng thăm dò khi `document.hidden`; tiếp tục khi quay lại.
- Cơ chế đăng ký: `subscribe(fn)` / `emit()`; các view chỉ đọc state, không tự gọi API thăm dò.
- Tính sẵn các cờ dẫn xuất: `isConnected`, `isStale`, `canMove` (= `status.connection.connected` && `status.connection.motion_unlocked` && không stale), `canStop` (đã kết nối, luôn bật).
- isStale chỉ tính khi connected là true. Khi đã ngắt kết nối, machine là dữ liệu cũ nên chỉ hiển thị mờ, không dùng để bật điều khiển

### Bước 2 – Header, thanh an toàn, cảnh báo
- Cập nhật `backend-status`, `machine-state`, `job-status`, dải cảnh báo `system-alert` (mất backend, dữ liệu cũ, chế độ chỉ đọc).
- Tạm dừng / Tiếp tục / Reset luôn bật khi đã kết nối (realtime `hold|resume|reset`).

### Bước 3 – Tab Cài đặt: kết nối
- Chọn Sim/Serial, đổ cổng COM từ `/api/ports`, Kết nối / Ngắt.
- Lưu ngôn ngữ và sáng/tối vào `localStorage`, nạp lại khi tải trang.

### Bước 4 – Tab Điều khiển
- Vị trí (MPos/WPos), feed, planner/RX, Alarm/lỗi, "đã Home (ước đoán)".
- Bật/tắt nút theo bảng ở mục 3. Jog, bút lên/xuống, Zero, Home, Mở khóa, Hủy jog, XY 0 đúng bảng lệnh trong `docs/frontend-blocks.md`.
- Terminal: gửi một dòng qua `/api/command`, hiển thị log tx/rx/sys.
- Khung 2D: vẽ vùng làm việc theo `MACHINE.travelX/Y` và vị trí đầu bút (chỉ đọc từ `status`). Hướng trục là **giả định** (gốc trái-xa, Y tăng về phía người dùng), ghi trong `config.js`.

### Bước 5 – Macro
- `js/macros.js` riêng, lưu `localStorage`, giao diện đủ đơn giản để sau đổi sang backend mà không sửa view.

### Bước 6 – Giữ khóa
Tệp G-code, tác vụ, hàng đợi, thẻ SD, lịch sử, toàn bộ tab Tạo bản vẽ, đọc cấu hình máy: **giữ khóa** và hiện "Chưa có backend". Không viết logic giả.

## 3. Điều khiển theo `status.machine.state`

`status.machine` là `null` khi chưa nhận báo cáo nào: coi như chưa sẵn sàng. `last_alarm` và `last_error` không tự xóa, chỉ hiện alarm khi `state === "Alarm"`. Cấu trúc đầy đủ xem `backend-summary.md`.

| `state` | Cho phép |
|---|---|
| (chưa kết nối) | Chỉ Kết nối |
| `Idle` | Jog, Home, Zero, bút, gửi lệnh (nếu `canMove`) |
| `Run` | Chỉ Tạm dừng và Reset; khóa jog |
| `Jog` | Hủy jog, Tạm dừng, Reset |
| `Hold` | Tiếp tục, Reset |
| `Home` | Chỉ Reset |
| `Alarm` | Hiện `last_alarm`; chỉ Mở khóa, Home, Reset |

Khi `status.connection.motion_unlocked` là `false` (máy thật chỉ đọc): khóa Home/Jog/Bút/Chạy và hiện dải "Chế độ chỉ đọc". Lệnh `hold`/`reset` vẫn gửi được.
Alarm hay gặp: 1 công tắc cứng, 2 giới hạn mềm, 3 bị hủy, **14 chưa Home**. Jog chạy được khi chưa Home, G-code chuyển động thì không.

## 4. Mã lỗi → khóa i18n (dịch ở frontend, không hiện thẳng `message`)

| `ApiError.code` | Khóa gợi ý | Ý nghĩa |
|---|---|---|
| `backend_unreachable` | `error.backendUnreachable` | Không gọi được backend |
| `already_connected` | `error.alreadyConnected` | 409 |
| `not_connected` | `error.notConnected` | 409 |
| `bad_request` | `error.badRequest` | 400 |
| `motion_locked` | `error.motionLocked` | 403, máy thật đang chỉ đọc |
| `link_error` | `error.linkError` | 502 |
| `pyserial_missing` | `error.pyserialMissing` | 500 |
| `validation_error` | `error.validation` | 422 |
| `http_error` | `error.http` | khác |

Lỗi FluidNC dạng `error:N` và `ALARM:N` cũng đi qua bảng dịch (`last_error.code`, `last_alarm`), không hiện số trần.

## 5. Kiểm tra chấp nhận (chế độ sim, người dùng chạy thật và báo lại)

1. Kết nối sim: Idle, 0,0,0, báo "chưa Home".
2. Gõ `G0 X10`: vào Alarm, giao diện báo Unhomed (ALARM:14).
3. Mở khóa, jog X +10 chạy được.
4. Home: trạng thái Home khoảng 1,5 giây rồi Idle.
5. Jog +999: `error:15`, giao diện báo lỗi dễ hiểu.
6. Chạy chậm rồi Tạm dừng / Tiếp tục.
7. Reset khi đang chạy: Alarm mã 3.
8. Ngắt kết nối: khóa mọi điều khiển.
9. Tắt backend: hiện cảnh báo mất kết nối, khóa điều khiển.
10. Đổi ngôn ngữ và sáng/tối, tải lại vẫn giữ.

Thêm: không có lỗi đỏ trong Console (F12); không tràn ngang ở 1280 px và 1024 px.

## 6. Cách nộp bài

- Nén `frontend/` (kèm `docs/`), nêu file đã tạo/sửa, nội dung đổi, cách kiểm tra.
- Dán lỗi Console nếu có. Ghi rõ điều **chưa kiểm chứng**.
- Mỗi bước một commit nhỏ.

## 7. Việc còn treo (chờ nhóm chốt, đừng tự quyết)

- Ý nghĩa nút **Dừng tác vụ** khi có hàng đợi (hủy tác vụ, không phải Tạm dừng).
- Phím tắt jog: mặc định **tắt**.
- Hướng trục, Z0/Z5, `XY 0` dùng hệ tọa độ nào: chờ thử máy thật.
- `--canvas-aspect` trong CSS cần khớp hành trình thực (nhóm tự sửa số, X 285 / Y 318).
