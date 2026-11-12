# 04 — Tab Điều khiển: nút bấm, luồng lệnh và mã phía sau

> Dành cho người đọc. Phần 1–2 dùng máy hằng ngày. Phần 3–7 giải thích mã đứng sau từng nút, tăng dần độ sâu.
> Thông số máy: [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md). Cấu trúc thư mục: [03_CAU_TRUC_PHAN_MEM.md](03_CAU_TRUC_PHAN_MEM.md).

**Mục lục**
1. Tab này làm gì, không làm gì
2. Các nút và ô
3. Đường đi của một lệnh: từ nút bấm tới động cơ
4. Trạng thái máy: hỏi 10 lần mỗi giây
5. Chạy một tệp G-code
6. Dừng an toàn và tiếp tục từ điểm dừng
7. Các chốt an toàn
8. Tệp mã liên quan

---

## 1. Tab này làm gì, không làm gì

| Làm | Không làm |
|---|---|
| Kết nối máy, xem trạng thái và vị trí, jog, Home, đặt gốc (Zero), nâng hạ bút | Không tạo nét từ ảnh (việc của tab Tạo bản vẽ) |
| Nạp tệp G-code (khung 2D hiện ngay đường chạy + vùng vẽ), chạy, chỉnh tốc độ khi đang chạy, hủy an toàn, tiếp tục từ điểm dừng | Không chạy khi máy chưa nối / chưa mở khóa chuyển động / chưa Idle / tệp có dòng bị cấm. **Không còn bước Xem trước + tích xác nhận** (bỏ từ 12/11/2026, [09](09_QUYET_DINH_THIET_KE.md) C9) |
| Terminal gửi lệnh tay, macro, hàng đợi bản thảo | Nút Reset trên web **không phải dừng khẩn cấp**. Dừng khẩn cấp thật là công tắc cắt nguồn 12 V |

---

## 2. Các nút và ô

| Khối | Nút / ô | Làm gì | Lệnh gửi xuống máy |
|---|---|---|---|
| Đầu trang | Tạm dừng / Tiếp tục | dừng tạm khi đang chạy tệp, chạy tiếp | `!` (Feed Hold) / `~` (Cycle Start) |
| | Hủy jog | dừng lệnh jog đang chạy | byte `0x85` |
| | Reset | dừng mềm (hỏi xác nhận) | byte `0x18` (Ctrl-X) |
| | Mở khóa ($X) | gỡ Alarm | `$X` |
| Trạng thái | ô trạng thái một dòng | Idle / Run / Hold / Alarm / Home, tốc độ thật, bộ đệm | (đọc từ báo cáo `?`) |
| | Mở khóa chuyển động | máy thật mặc định **chỉ đọc**; bấm (kèm PIN nếu đặt) mới cho chạy, tự khóa sau 15 phút không dùng | (không gửi gì, chỉ mở cổng ở máy chủ) |
| Vị trí | Tọa độ X, Y, Z; đèn công tắc X / Y | đèn sáng khi báo cáo có `Pn:X` / `Pn:Y` (đang đè công tắc hành trình) | |
| | Zero X / Y / XY | đặt gốc làm việc tại chỗ bút đang đứng | `G10 L20 P1 X0 Y0` |
| | Home X / Y / tất cả | chạy về công tắc hành trình (hỏi xác nhận). **Tự nâng bút trước** | `$J=G90 G21 Z5 F3000` rồi `$H` / `$HX` / `$HY` |
| Di chuyển | Mũi tên, ô bước | jog theo bước đã chọn (tối đa 50 mm) | `$J=G91 G21 X10 F…` |
| | Nút giữa | về gốc làm việc | `$J=G90 G21 X0 Y0 F…` |
| Bút | Lên / Giữa / Xuống | Z5 / Z1,5 / Z0 (sửa ở Cài đặt → Cấu hình máy, mục App). Z nhấc của G-code (mặc định 3) là giá trị khác, chỉnh ở cùng mục; nhấc của G-code vẫn hiện là "Lên" | `$J=G90 G21 Z5 F3000` |
| Tệp G-code | Chọn tệp → nhìn khung 2D → **▶ Chạy** | nút Xem trước và ô tích xác nhận đang **ẩn** (công tắc `REQUIRE_PREVIEW_CONFIRM` ở đầu `views/control.js`; đặt `true` để hiện lại: lúc đó phải xem trước + tích, đổi tệp là làm lại). Dòng bị cấm hiện đỏ kèm số dòng và lý do, khóa nút Chạy | gửi từng dòng |
| | Hủy tác vụ | hộp thoại: Tiếp tục chạy / **Dừng êm** / **Dừng gấp** | xem mục 6 |
| | −10 −1 100% +1 +10 | ghi đè tốc độ (10–200 %) | byte `0x90`…`0x94` |
| | Lưu vào bản thảo | lưu tệp đang nạp thành một bản thảo để ghim, chạy lại nhanh | |
| | Tiếp tục / Bỏ điểm dừng | chỉ hiện khi có tác vụ dừng giữa chừng | xem mục 6.3 |
| Khung 2D | Phóng / thu, toàn cảnh, xóa vết, phát lại | xem trước **một** tệp đang chọn; khi chạy, vệt bút bám theo đường của tệp | |
| Hàng đợi công việc | Làm mới, Nạp, Ghim, Đẩy ưu tiên, Mở xem | đọc thẳng các bản thảo đã lưu | |
| Terminal | Gửi, Xóa log hiển thị | gửi lệnh tay; giữ tiếng Anh để dễ tra mã lỗi | nguyên văn |
| Dock trái | Macro | lệnh lưu sẵn (thêm / sửa / xóa), lưu ở máy chủ | |
| | Tệp nhanh | các bản thảo đã ghim, bấm để nạp (khung vẽ hiện ngay, rồi bấm Chạy) | |

---

## 3. Đường đi của một lệnh: từ nút bấm tới động cơ

Ví dụ bấm mũi tên phải (jog X +10 mm):

```
[Trình duyệt]
 views/control.js      bấm nút → dựng chuỗi "$J=G91 G21 X10 F3000"
 core/api.js           POST /api/command  {"line": "..."}        ← NƠI DUY NHẤT gọi mạng
        │ HTTP
[Máy chủ Python]
 main.py               kiểm Host / Origin, kiểm vai trò (khách bị chặn ở đây)
 api/machine.py        nhận yêu cầu, gọi MachineService.send_line   ← mỏng, không có logic
 services/machine.py   _send_line: đã kết nối chưa? đang chạy tác vụ không? đang dừng an toàn không?
                       máy thật đã mở khóa chuyển động chưa? → ghi nhật ký → gửi
 links/serial_link.py  ghi "…\n" ra cổng COM (pyserial, 115200 baud)
        │ USB (chip CH340)
[Mạch MKS DLC32 + FluidNC]
 trả "ok" → động cơ chạy → các báo cáo "<Jog|MPos:…>" sau đó cho thấy vị trí mới
        │
 links/protocol.py     classify_line: phân loại dòng nhận về (status / ok / error / ALARM / MSG)
 services/machine.py   _on_line: cập nhật trạng thái, đếm ok, ghi nhật ký
        │
[Trình duyệt]  core/state.js nhận luồng SSE /api/events (dự phòng: hỏi GET /api/status mỗi 100 ms) → views vẽ lại tọa độ
```

Ba quy tắc rút ra từ sơ đồ:
1. **Trình duyệt không bao giờ chạm cổng serial.** Mọi lệnh đi qua máy chủ, máy chủ kiểm lại.
2. **Lớp API mỏng.** `api/*.py` chỉ nhận và trả; mọi quyết định nằm ở `services/`.
3. **Mọi lệnh đi qua một cửa kiểm** (`_send_line`), nên thêm chốt an toàn chỉ cần sửa một chỗ.

**Máy giả (SimLink):** chọn chế độ `sim` ở Cài đặt → Kết nối. `links/sim_link.py` bắt chước FluidNC theo log board thật (trả `ok` sau `ALARM:2`, Reset từ Run ra `ALARM:3`…). Mọi nút chạy được khi chưa có máy.

---

## 4. Trạng thái máy: hỏi 10 lần mỗi giây

| Ai | Làm gì | Nhịp |
|---|---|---|
| Máy chủ (`MachineService._poll_loop`) | gửi byte `?` xuống máy | 0,1 s (`POLL_S`) |
| FluidNC | trả một dòng `<Idle\|MPos:10.000,20.000,3.000\|Bf:15,127\|FS:0,0\|Pn:X\|WCO:…>` | mỗi lần hỏi |
| `protocol.py` | tách trạng thái, MPos / WPos, WCO, bộ đệm `Bf`, tốc độ `FS`, công tắc `Pn`, ghi đè `Ov` | |
| `_update_status` | đổi MPos ↔ WPos bằng WCO (WPos = MPos − WCO), tăng số thứ tự báo cáo, ghi giờ | |
| Máy chủ (`api/events.py`) | **đẩy** qua một kết nối SSE `GET /api/events?since=`: sự kiện `status` (nội dung như `/api/status`) khi đổi, ít nhất mỗi 2 s; sự kiện `log` (chỉ quản lý) khi có dòng nhật ký mới | nhìn 10 lần/giây |
| Trình duyệt (`core/state.js`) | nhận SSE; **dự phòng** khi SSE im quá 5 s / chưa nối được / tab ẩn: `GET /api/status` | 100 ms |
| | dự phòng: `GET /api/log?since=` (terminal) | 300 ms–1 s (Cài đặt → Hoạt động) |

- **MPos** = vị trí theo máy (tính từ công tắc hành trình). **WPos** = vị trí làm việc (tính từ gốc Zero). **WCO** = độ lệch giữa hai cái.
- **Số thứ tự báo cáo** (`_status_seq`) tăng mãi. Khi cần chờ "máy đã dừng chưa", mã chỉ tin báo cáo có số lớn hơn mốc lấy **trước** khi gửi lệnh (`_wait_state`). Nhờ vậy không nhầm báo cáo cũ còn nằm trong bộ nhớ.
- **Đoán đã Home:** FluidNC không có trường "đã Home". Máy chủ đoán theo ba tín hiệu: dòng `[MSG:Homed:XY]`, trạng thái Home → Idle, hoặc `ok` sau `$H`. Phải đủ cả X và Y mới coi là đã Home. Alarm làm mất Home (danh sách `_LOSE_HOME`).
- **SSE (từ 09/11/2026):** SSE khỏe thì giao diện **không gọi `/api/status` hay `/api/log` nữa** (đo trên Chrome: 0 lần gọi trong 6 giây, trước đó ~60). Máy chủ tắt thì tự quay về hỏi lặp, bật lại thì SSE tự nối lại (since mới nên không lặp dòng nhật ký). Tab bị ẩn thì đóng SSE (bản đóng gói vẫn tự tắt khi không còn trang nào). Qua Cloudflare Tunnel: máy chủ gửi lại trạng thái mỗi 2 s nên kết nối không bị cắt vì im lặng; tối đa 40 kết nối cùng lúc. Lệnh điều khiển vẫn là HTTP POST. Trình duyệt chỉ mở tối đa 6 kết nối tới một địa chỉ: mở quá 6 tab cùng lúc thì tab mới có thể treo.
- **Dữ liệu cũ:** báo cáo cũ hơn 2 s thì giao diện khóa nút điều khiển (`POLL.staleMs`).

---

## 5. Chạy một tệp G-code

### 5.1 Trước khi chạy: kiểm tệp ở hai nơi
| Nơi | Hàm | Kiểm gì |
|---|---|---|
| Trình duyệt, lúc nạp | `lib/gcode.js` `parseGcode`, `cleanLine` | đọc tệp thành các đoạn để vẽ khung 2D; báo trước dòng bị cấm (`BLOCKED_G`), ra ngoài vùng máy (`outOfRange`), chưa Home |
| Máy chủ, lúc chạy | `services/job.py` `clean_gcode` | bỏ chú thích `( )` và `;`, bỏ dòng trống; **từ chối** dòng `$…` (cài đặt, Home, jog), ký tự tức thời `? ! ~`, ký tự lạ, dòng > 200 ký tự, và các lệnh `G10, G28, G30, G38, G53, G55–G59, G92` (đổi gốc / chạy tới chỗ máy tự chọn). Báo một lần tối đa 5 dòng lỗi kèm số dòng. Tối đa 200 000 dòng |

Hai nơi giữ **cùng một danh sách**. Trình duyệt báo sớm cho tiện; máy chủ kiểm lại vì không tin dữ liệu từ trình duyệt.

Điều kiện bắt đầu (`MachineService.start_job`): đã kết nối, không đang dừng an toàn, đã mở khóa chuyển động (máy thật), máy đang **Idle**.

### 5.2 Gửi từng dòng, chờ `ok` (`JobRunner._run`)
```
với mỗi dòng:
    ghi dòng xuống máy
    chờ "ok" hoặc "error"  (tối đa 120 s; đang Hold thì không tính giờ)
    "ok"    → dòng tiếp
    "error" → dừng cấp lệnh + Feed Hold (không để máy chạy tiếp một mình)
hết dòng: chờ 2 báo cáo Idle MỚI liên tiếp → xong
```

**Vì sao gửi từng dòng mà máy vẫn chạy liền:** FluidNC trả `ok` ngay khi dòng **vào hàng đợi chuyển động** (planner, 16 khối), chưa phải khi chạy xong. Hàng đợi đầy thì `ok` bị giữ lại. Vậy hàng đợi luôn đầy mà không cần đếm ký tự bộ đệm. Thử 1500 dòng ở F3000: không nhảy Run / Idle. Chỉ khi đoạn nét **rất ngắn** ở tốc độ rất cao mới có thể "đói lệnh". Muốn biết chắc thì cần ghi số liệu `Bf:` theo thời gian (việc cần làm, [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md)).

**Vì sao cần 2 báo cáo Idle mới:** một báo cáo Idle đơn lẻ có thể được tạo ngay trước khi khối cuối bắt đầu chạy.

**Mất phản hồi:** quá 10 s không có báo cáo trạng thái (`STATUS_STALE_S`) thì tác vụ báo lỗi và gửi Feed Hold.

**Khi đang chạy tác vụ**, terminal chỉ gửi được `? ! ~` và các nút dừng. Lý do: mỗi dòng gửi thêm có một `ok` riêng, làm lệch việc đếm `ok` của tác vụ.

### 5.3 Biểu đồ số liệu chạy máy (`views/jobchart.js`, `services/joblog.py`)
Trong khung "Khung nhìn 2D" có nút chuyển **[Đường vẽ | Biểu đồ]** (chỉ quản lý thấy). Mỗi lần chạy tệp, backend ghi mỗi báo cáo trạng thái (~10 lần/giây) vào `data/job_logs/<giờ>-<số>.csv` + một tệp `.json` tóm tắt; giữ 30 lần gần nhất (và không quá 150 MB).

| Cột CSV | Ý nghĩa |
|---|---|
| `t`, `state` | giây từ lúc bắt đầu, trạng thái máy (Run / Hold / Idle…) |
| `x y z` | tọa độ làm việc |
| `feed` | **tốc độ thật** (`FS:`, mm/phút) |
| `bf_planner`, `bf_rx` | số khối trống trong hàng đợi chuyển động / bộ đệm nhận (`Bf:`) |
| `sent`, `acked` | số dòng đã gửi / đã nhận `ok` |

Giao diện vẽ ba biểu đồ dùng chung trục thời gian: **tốc độ thật**, **hàng đợi** (số khối đang có = tối đa − trống; **0 khi đang chạy = máy đói lệnh**, chấm đỏ) và **độ cao bút Z**. Rê chuột để đọc số từng lúc. Đang chạy thì tự làm mới mỗi 2 giây (đây chỉ là nhịp vẽ lại màn hình; dữ liệu vẫn ghi ~10 lần/giây). **Khung thời gian**: mặc định "Tự động" = đang chạy thì chỉ hiện **1 phút gần nhất** và cuộn theo (không bị thu nhỏ dần), chạy xong thì hiện cả lần chạy; có thể chọn 30 giây / 1 phút / 5 phút / cả lần chạy. Lần chạy đã xong mà chọn khung ngắn thì có **thanh trượt** để xem lại đoạn trước. Bảng tóm tắt luôn tính trên cả lần chạy. Biểu đồ Z có vạch **0 / 1 / 3 / 5 mm** (các mốc nhấc hay dùng). Backend nhớ phần đã đọc nên làm mới không đọc lại cả tệp (`GET /api/joblogs/{id}?window=60&end=…`). Bảng tóm tắt: thời gian thật so với ước tính, số lần nhấc bút (đếm đoạn G0 trong G-code, không đếm từ mẫu vì mẫu thưa hơn một chu kỳ nhấc), % thời gian máy chạy / bút xuống, tốc độ vẽ trung bình, % thời gian đói lệnh. Chọn thêm một lần chạy khác ở ô "So với" thì có cột so sánh và % chênh, tô xanh / đỏ theo tốt hơn / xấu hơn.

**Cần `$10=3`:** máy thật đang để `$10=1` nên không gửi `Bf:`; khi đó biểu đồ hàng đợi trống và có lời nhắc. Mở khóa chuyển động, gõ `$10=3` trong terminal (`$10` để xem), rồi chạy lại. Máy giả mặc định `$10=3`; gõ `$10=1` để giống máy thật.

Số liệu kèm từ giao diện khi bấm Chạy: ước tính thời gian, quãng vẽ / di chuyển, số đoạn G0 (`client` trong `POST /api/jobs`). API: `GET /api/joblogs`, `GET /api/joblogs/{id}`, `GET /api/joblogs/{id}/csv`, `DELETE /api/joblogs/{id}` (đều cần quản lý). Mỗi lần chạy tự lưu trên **máy chủ** (kể cả lần bị ngắt kết nối giữa chừng, trạng thái "ngắt kết nối" / "mất kết nối"); lần chạy dưới 3 mẫu (bấm Chạy rồi ngắt ngay) bị bỏ. **Tải CSV** chỉ chép một bản về máy đang dùng (thư mục Tải xuống của trình duyệt), bản gốc vẫn ở `data/job_logs/`; **So với** là so sánh hai lần chạy trên màn hình; **Xóa** xóa hẳn khỏi máy chủ, có hộp xác nhận riêng của app. Lỗi ghi đĩa chỉ tắt nhật ký của lần chạy đó, không bao giờ làm hỏng việc gửi lệnh.

### 5.4 Khung 2D bám theo bút (`views/preview.js`, `lib/gcode.js` `trackProgress`)
Máy chỉ có thể đang ở trong vài chục dòng trước dòng đã nhận `ok` (planner 16 khối + bộ đệm nhận). Khung 2D tìm đoạn gần vị trí máy nhất trong khoảng từ (dòng đã nhận − 64) tới dòng đã nhận, không lùi so với lần trước. Nhờ vậy hỏi thưa hay mô phỏng chạy nhanh vẫn không mất dấu, cung tròn không bị gãy.

---

## 6. Dừng an toàn và tiếp tục từ điểm dừng

### 6.1 Ba chế độ hủy (`MachineService.cancel_job`)
| Chế độ | Trình tự | Khi nào dùng |
|---|---|---|
| **Dừng êm** (`soft`, mặc định) | ngừng gửi dòng mới → chờ máy chạy hết hàng đợi (tối đa 120 s) → xác nhận Idle mới → nâng bút → chờ báo cáo xác nhận Z đã tới | dừng bình thường, giữ được Home |
| **Dừng gấp** (`hard`) | Feed Hold `!` → chờ Hold xong (3 s) → Reset `0x18` → nếu Alarm: `$X` (nếu firmware đòi Reset trước thì Reset rồi `$X` lại) → xác nhận Idle mới → nâng bút → xác nhận Z | cần dừng ngay |
| `reset` | Reset ngay, không nâng bút | hành vi cũ |

- Dừng êm gặp Hold / Door / Alarm, hết giờ, hoặc nâng bút thất bại → tự chuyển sang dừng gấp.
- **Chỉ báo "đã nâng bút" khi báo cáo trạng thái xác nhận Z đã tới** (sai số 0,05 mm), không chỉ là "lệnh đã gửi". Không xác nhận được thì nhật ký ghi rõ "The pen may still be DOWN".
- Trong lúc dừng, máy chủ giữ một **thẻ dừng** (`_stop_token`). Mọi lệnh chuyển động, tác vụ mới, tiếp tục đều bị từ chối (`stopping`). Chỉ luồng dừng có đúng thẻ mới được gửi lệnh. Mất kết nối giữa chừng thì thẻ bị hủy và nhật ký báo "safe stop abandoned".
- Trình tự chạy ở luồng nền, nên giao diện không bị đứng.

### 6.2 Home tự nâng bút (`_lift_pen_before_home`)
Bút hạ bằng trọng lực, quên nâng mà bấm Home thì bút kéo một vệt chéo qua giấy (đã gặp 03/11/2026). Nên khi gửi `$H`, `$HX`, `$HY` mà máy đang Idle, máy chủ gửi trước `$J=G90 G21 Z3 F3000`, chờ Z tới thêm 0,3 s (servo quay chậm hơn trục Z ảo), rồi mới Home. Nâng bút lỗi thì vẫn Home (chỉ ghi nhật ký).

### 6.3 Tiếp tục từ điểm dừng (`services/resume.py`)
Khi tác vụ kết thúc không trọn (hủy, lỗi, mất kết nối), `JobRunner` ghi vào `data/resume.json`: tệp đã làm sạch, số dòng máy đã nhận, gốc làm việc (WCO) lúc đó. Chạy trọn thì xóa.

Bấm **Tiếp tục**:
1. Lùi **64 dòng** so với dòng đã nhận (`RESUME_MARGIN`), vì `ok` chỉ có nghĩa "đã vào hàng đợi", dừng gấp làm mất phần đang chờ.
2. Lùi tiếp tới dòng gần nhất mà **bút đang nhấc** (đầu một nét).
3. Đọc lại phần đã chạy để biết đơn vị, tốc độ F, vị trí; dựng vài dòng mở đầu: `G90 G21`, nâng bút, `G0` tới đầu nét, đặt lại `F`.
4. Gốc Zero đã đổi so với lúc dừng → hỏi lại (bản vẽ sẽ lệch).
5. Từ chối nếu phần đã chạy dùng `G91, G92, G10, G28, G30, G53, G55–G59, M3, M4` (không đoán được trạng thái).

Vẽ chồng một đoạn ngắn thì vô hại; bỏ sót thì mất nét. Nên chọn lùi, không chọn tiến.

---

## 7. Các chốt an toàn

| Chốt | Ở đâu |
|---|---|
| Máy thật mặc định **chỉ đọc**: chỉ gửi được lệnh đọc (`$I $$ $G $E`…) và `$X` cho tới khi mở khóa chuyển động; tự khóa lại sau 15 phút không dùng, khi ngắt kết nối, khi đăng xuất | `MachineService.set_motion`, `_check_relock`; danh sách lệnh chỉ đọc lấy theo `$CMD` thật ở `links/protocol.py` |
| Hold / Reset / Hủy jog luôn gửi được | `_send_realtime` |
| Khách (chưa đăng nhập) không gọi được route điều khiển nào; route mới mặc định bị chặn | `app/auth.py` (`GUEST_ROUTES`), middleware ở `main.py` |
| Tệp G-code không được đổi cài đặt, gốc, hệ tọa độ | `job.clean_gcode` (+ `lib/gcode.js`) |
| Dòng bị máy báo lỗi → Feed Hold | `JobRunner._run` |
| Mất báo cáo > 10 s khi chạy → Feed Hold; > 2 s → giao diện khóa nút | `STATUS_STALE_S`, `POLL.staleMs` |
| Chỉ nhận Host cục bộ / được phép; chặn POST từ trang khác | `main.py`, `EXTRUXY_ALLOWED_HOSTS` |
| Wi-Fi của mạch MKS (WebUI FluidNC) **vượt qua mọi khóa của phần mềm** | tắt hoặc đặt mật khẩu mạnh trước demo ([02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md)) |

---

## 8. Tệp mã liên quan

| Tệp | Vai trò |
|---|---|
| `frontend/js/views/control.js` | tab Điều khiển: trạng thái, mở khóa, jog, thanh bút 3 nấc, Zero, Home, tệp G-code, ghi đè tốc độ, tiến trình, hủy |
| `frontend/js/views/preview.js` | khung 2D, vệt bút, đèn X / Y |
| `frontend/js/views/jobchart.js` · `lib/chart.js` · `css/jobchart.css` | biểu đồ số liệu chạy máy (vẽ canvas · tính vạch trục, bảng so sánh) |
| `frontend/js/views/terminal.js` | terminal và các nút an toàn ở đầu trang |
| `frontend/js/views/dock.js` · `stores/macros.js` | macro và tệp nhanh |
| `frontend/js/views/drafts.js` · `stores/draftstore.js` | hàng đợi công việc (bản thảo) |
| `frontend/js/lib/gcode.js` | đọc G-code, cảnh báo, bám tiến trình |
| `frontend/js/core/state.js` · `core/api.js` | thăm dò trạng thái · gọi máy chủ |
| `backend/app/api/machine.py` | các route `/api/connect`, `/status`, `/command`, `/realtime`, `/jobs`… |
| `backend/app/services/machine.py` | **bộ não**: kết nối, trạng thái, nhật ký, đoán Home, khóa chuyển động, dừng an toàn |
| `backend/app/services/job.py` | làm sạch và chạy tệp G-code |
| `backend/app/services/resume.py` | điểm dừng và tiếp tục |
| `backend/app/services/joblog.py` | ghi / đọc / tóm tắt số liệu từng lần chạy (`data/job_logs/`) |
| `backend/app/links/protocol.py` · `serial_link.py` · `sim_link.py` | đọc dòng FluidNC · cổng COM thật · máy giả |
