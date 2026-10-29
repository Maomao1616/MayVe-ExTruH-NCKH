# ExtruXY – Machine Correct (Sự thật máy thật)

**Board**: MKS DLC32 V2.1 · **Firmware**: FluidNC v4.1.1 (esp32-wifi) · **Config**: ConfigNCKH-16.yaml
**Trạng thái test**: Đã test tay không motor/servo (29/10/2026). Chưa test với motor/servo thực tế.

---

## A. Sự thật đã xác nhận (✅)

### A1. Kích thước và Settings
- `$130=285`, `$131=318`, `$132=5` (khớp YAML).
- `$100=80`, `$101=80`, `$102=100` (khớp giả định).
- `$110=6000`, `$111=6000`, `$112=3000`.

### A2. Công tắc hành trình
- Cổng X → Pn:X · Cổng Y → Pn:Y. **Không đảo nhãn**.
- Mức `:high` đúng (giữ = kích). Không cần sửa YAML.

### A3. Trạng thái Boot và $X
- Boot lên → firmware tự vào `Alarm` (do `must_home: true`). G-code bị chặn (error:9).
- Gửi `$X` → về `Idle` → **mọi lệnh G-code đều chạy được** (kể cả X/Y khi chưa Home thực).
- *Hệ quả*: `must_home` chỉ chặn lúc boot. Sau `$X`, UI cần cảnh báo người dùng nếu chạy G-code vượt hành trình mà chưa Home.

### A4. Soft limit — Thứ tự phản hồi
Gửi `g0 x1000` → firmware trả `ok` **trước**, `ALARM:2` **sau**. Backend đã xử lý đúng.

### A5. Feed Hold và Jog
- Đang chạy G-code (Run) → `!` → Hold:1 → Hold:0 (~100ms). Resume được bằng `~`.
- Đang chạy Jog (`$J`) → `!` → **Hủy jog ngay lập tức**, về Idle tại chỗ. KHÔNG resume được.

### A6. Reset và Hủy tác vụ
- Reset từ Run → `ALARM:3` (Abort Cycle).
- Reset từ Hold → Có thể ra `ALARM:3` hoặc về thẳng `Idle` (tùy thời điểm gửi).
- Đã triển khai 3 chế độ Hủy: `reset` (cũ), `soft` (chạy nốt buffer), `hard` (Hold -> Reset -> $X -> Nâng bút).

### A7. Rút cáp USB
- Máy chạy nốt các block trong buffer planner (vài giây) rồi dừng.
- Cắm lại: Backend báo `lost_reason: PermissionError(13)`. Cần nối lại, máy về Idle, không cần reset board.

### A8. Báo cáo trạng thái
- Đủ trường: `MPos`, `WPos`, `WCO`, `Bf`, `F`, `Pn`.
- Dòng `[MSG:Homed:XY]` xuất hiện sau khi Home xong.

### A9. Hold / Jog / Reset (kiểm lại 29/10/2026, sau khi sửa backend)
- Reset khi Hold: về `Idle`, không alarm. Reset ở Alarm khi chưa Home: ra `ALARM:14`.
- `$J` rồi `!`: hủy hẳn, `~` không chạy tiếp được.
- Chạm công tắc hành trình (ALARM:1): **phải Reset trước, rồi mới `$X`** được. Backend đã xử lý (`_unlock_alarm`).
- Chế độ chỉ đọc: `$$ $E $A $Limits $SS $G` đọc được, `$X` gửi được, `?` `!` `~` gõ ở terminal hoạt động.

### A10. Hủy tác vụ trên máy thật (không servo)
- **Dừng êm:** chờ Idle mới → `$J=G90 G21 Z5 F3000` → `pen lift confirmed (Z5)`. Không alarm.
- **Dừng gấp:** Hold → Reset → Idle mới (không alarm) → nâng bút → `pen lift confirmed`. Dừng khi đang Hold cũng không lỗi.
- Trong lúc đang dừng an toàn, nút/lệnh chuyển động bị chặn (`stopping`).
- Rút cáp khi đang chạy: job báo `failed` kèm `PermissionError(13)`, kết nối bị khóa lại về chỉ đọc.
- Z5/Z0 lấy theo WebUI FluidNC: gửi cùng tọa độ thì đúng, không cần đo thêm.

### A11. Sửa cấu hình qua USB (Cài đặt → Cấu hình máy, 29/10/2026)
- Cú pháp đã thử: `$Config/Filename` → `ConfigNCKH-16.yaml`; `$CD` in YAML đang chạy;
  `$/axes/x/max_rate_mm_per_min[=v]` đọc/ghi (ghi chỉ trong RAM); `$LocalFS/List`, `$LocalFS/Show=/<tệp>`;
  `$CD=/localfs/<tệp>` ghi YAML đang chạy ra tệp. Bộ nhớ trống ~60 KB.
- Đọc từ máy: giá trị khớp ConfigNCKH-16. Áp dụng (X 5500): máy đổi tạm, hàng hiện dấu ●.
- Lưu vào mạch: ghi đè YAML thành công, bản gốc được sao lưu về `backend/data/config_backups/`.
- Tắt nguồn, bật lại: giá trị đã lưu vẫn còn.
- `$CD=` viết lại tệp theo dạng chuẩn (mất chú thích `#`, `engine: I2S_STREAM` thành `engine: I2S`); máy vẫn khởi động và chạy bình thường.
- Thanh bút 3 nấc (Z5 / Z2.5 / Z0): chạy đúng, nấc sáng khớp vị trí.

---

## B. Chưa test / Làm tiếp
- B1: Xác nhận thời gian Home chính xác (X, Y, XY).
- B2: Hướng X+/Y+ thực tế trên giấy (dự kiến X+ đi trái, Y+ đi xuống).
- B3: Z bút lên/xuống thực tế (Servo GPIO 32).
- B4: Cung G2/G3 trên máy thật.






# ExtruXY – Machine Correct (sự thật máy thật)

**Board**: MKS DLC32 V2.1
**Firmware**: FluidNC v4.1.1
**Config**: ConfigNCKH-16.yaml (nạp ngày ___)
**Port**: COM_ (Windows) / /dev/ttyUSB_ (Linux)
**Baud**: 115200
**Ngày test**: ___

Ký hiệu: ✅ đã verify · ⚠ chưa verify · ❓ firmware trả khác dự kiến

---
Test 1 — Mở khóa UI:
- Banner chỉ đọc: [Có ]
- Mở khóa qua UI: [OK ]
- Tự khóa sau ngắt: [Ngắt kết nối thì ko khóa về chỉ đọc]
- Tự khóa sau timeout: [OK ]
- Kết luận: cơ chế hướng C [Chưa có vấn đề nghiêm trọng]

Test 2 — Công tắc:
- Giữ công tắc cổng X → Pn: [X]
- Giữ công tắc cổng Y → Pn: [Y]
- Mức logic: [:high đúng]
- Kết luận nhãn X/Y YAML: [không đảo]

Test 3 — G0 Z3 khi chưa Home:
- Chưa mở khóa (#X - Vẫn alarm từ lúc bật): error 9: G-code bị khóa khi đang Alarm hoặc Jog 
- Đã mở khóa: Phản hồi: [ok]
- Kết luận M5: [dùng jog / dùng được G0]

Test 4a — Hold → Reset:
- Hold:1 → Hold:0: 
 G1 X200 F600
ok
~ Idle  MPos 0.000,0.000,3.000  WPos 0.000,0.000,3.000  F0
~ Run  MPos 12.500,0.000,3.000  WPos 12.500,0.000,3.000  F849
~ Run  MPos 25.225,0.000,3.000  WPos 25.225,0.000,3.000  F849
~ Run  MPos 38.138,0.000,3.000  WPos 38.138,0.000,3.000  F849
> !
ok
~ Hold:0  MPos 40.487,0.000,3.000  WPos 40.487,0.000,3.000  F0
~ Hold:0  MPos 40.487,0.000,3.000  WPos 40.487,0.000,3.000  F0
~ Hold:0  MPos 40.487,0.000,3.000  WPos 40.487,0.000,3.000  F0
~ Hold:0  MPos 40.487,0.000,3.000  WPos 40.487,0.000,3.000  F0

- Reset khi Hold:0: [Ko lỗi]
- Sau $X, jog Z5: [chạy]
- Kết luận D4:

Test 4b — Reset thẳng:
- Reset khi Run: [ALARM:3]
- So với 4a: [! là dừng hẳn luôn rất nhanh => ko có lỗi]

Test 5 — Jog trong Hold:
- Phản hồi: [Hủy luôn jog - Về lại Idle bth]

Test 6 — Streaming:
- Số dòng trong tệp: [1500]
- Thời gian chạy: 
zigzag_F3000_1500lines.gcode · Đang chạy
4%
Dòng lệnh: 69 / 1507
Còn lại: 18:43

- Có nhảy Run/Idle không:  Không]
- Kết luận D10: [OK ]

Test 8 — Rút cáp:
- Chạy nốt hết lệnh
- UI backend báo lost_reason: 
# Connection lost: motion locked
# Mất kết nối serial: GetOverlappedResult failed (PermissionError(13, 'Access is denied.', None, 5))
# Connected (serial)

- Sau khi cắm lại + nối lại, state: [/ Idle / home chưa xác nhận ...]
- Có cần reset board không: [Không - vì có lẽ nếu là streaming thì nốt mấy dòng gocde lỡ nạp là nó dừng ]


## 1. Banner và Firmware

### $I:
[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]
[OPT:PHS]
[CLUSTER:16]
[MSG:Machine: MAYVE]
[MSG:Mode=STA:SSID=OppoFindX9S:Status=Connected:IP=10.148.147.227:MAC=1C-C3-AB-8E-7F-4C]
ok



### $$ (settings đầy đủ):
$13=0
$20=1
$21=1
$22=1
$23=7
$30=0
$32=0
$100=80.000
$101=80.000
$102=100.000
$110=6000.000
$111=6000.000
$112=3000.000
$120=600.000
$121=600.000
$122=1000.000
$130=285.000
$131=318.000
$132=5.000
$10=1


### $CMD (danh sách lệnh)
$ESPNow/Unpair or $EU
$ESPNow/List or $EL
$ESPNow/Cancel or $EC
$ESPNow/Pair or $EP
$HTTP/Settings/Load or $HSL
$HTTP/Command or $HCMD
$Notification/Send or $ESP600 =message
$Notification/Setup or $ESP610 =TYPE=NONE|PUSHOVER|EMAIL|LINE T1=token1 T2=token2 TS=settings
$Sta/Setup or $ESP103 =IP=ipaddress MSK=netmask GW=gateway
$System/IP or $ESP111
$Firmware/Info or $ESP800
$wifi/status
$WiFi/ListAPs or $ESP410
$WebUI/Help or $ESP
$WebUI/Help or $ESP0
$WebUI/List or $ESP400
$WebUI/Set or $ESP401 =P=position T=type V=value
$System/Control or $ESP444 =RESTART
$System/Stats or $ESP420
$GCode/Modes or $G
$Jog or $J
$GRBL/Show or $GS
$Report/Inches or $13
$Report/Interval or $RI
$Uart/Passthrough or $UP
$Crash/Test or $CRASH
$Backtrace/Show or $BS
$Startup/Show or $SS
$Heap/Show or $Heap
$Alarm/Send or $SA
$Settings/Restore or $RST
$Build/Info or $I
$System/Sleep or $SLP
$Log/Verbose or $LV
$Log/Debug or $LD
$Log/Info or $LI
$Log/Warn or $LW
$Log/Error or $LE
$Log/Msg or $LM
$Msg/Channel or $MC
$Msg/Uart1 or $MU1
$Msg/Uart0 or $MU0
$Home/W or $HW
$Home/V or $HV
$Home/U or $HU
$Home/C or $HC
$Home/B or $HB
$Home/A or $HA
$Home/Z or $HZ
$Home/Y or $HY
$Home/X or $HX
$Home or $H
$Parameters/List or $PL
$Macros/Run or $RM
$Motors/Init or $MI
$Motor/Enable or $ME
$Motor/Disable or $MD
$GCode/Offsets or $#
$Settings/Stats or $V
$Settings/Erase or $NVX
$Alarm/Disable or $X
$GCode/BlockMode or $GB
$GCode/Check or $C
$Errors/List or $E
$Alarms/List or $A
$Commands/List or $CMD
$Settings/ListChanged or $SC
$Settings/List or $S
$Limits/Show or $Limits
$GrblNames/List or $L
$GrblSettings/List or $$
$State or $T
$Help or $
$Config/Dump or $CD
$Channel/Info or $CI
$GPIO/Read or $GR
$GPIO/Off or $G-
$GPIO/On or $G+
$GPIO/Output or $GO
$GPIO/Input or $GI
$GPIO/Dump or $GD
$Bye =RESTART
$Xmodem/Send or $XS
$Xmodem/Receive or $XR
$Files/ListGCode =path
$SD/Status or $ESP200
$SD/ListJSON =path
$SD/List or $ESP210
$SD/Rename =path
$SD/Delete or $ESP215 =file_or_directory_path
$SD/Run or $ESP220 =path
$SD/Show or $ESP221 =path
$File/ShowHash =path
$File/ShowSome =path
$File/SendJSON =path
$LocalFS/Hashes
$LocalFS/Migrate =path
$LocalFS/Restore =path
$LocalFS/Backup =path
$LocalFS/Rename =path
$LocalFS/Delete =path
$LocalFS/ListJSON =path
$LocalFS/List =path
$LocalFS/Run or $ESP700 =path
$LocalFS/Show =path
$LocalFS/Format or $ESP710 =FORMAT
$LocalFS/Size or $ESP720
ok


### Kết luận
- Version: ___
- Firmware có hỗ trợ $HX/$HY: [Có ]
- Firmware có hỗ trợ $SD/List: [Không dùng]

---

## 2. Vật lý trục (chỉ khi có motor)

### 2.1 Hướng trục (C5) — ⚠/✅
- Jog X+ → đầu bút đi: [trái - tại WebUI đã test +X là sang trái tức firmware đã đúng, phần mềm nhảy cùng kiểu webui]
- Jog Y+ → đầu bút đi:  xuống - như trên]
- Cấu hình hiện tại giả định: X+ = sang phải, Y+ = đi xuống
- **Kết luận**: VIEW.flipX = [false / true], VIEW.flipY = [false / true] - ko hiểu

### 2.2 Home
- Home X → chạy về: [phải]
- Home Y → chạy về: [trên] - giống tọa độ webui là đc
- Tọa độ sau Home: MPos = [0, 0, 0] 
- Thời gian Home X: ___ giây - chưa xác thực
- Thời gian Home Y: ___ giây

### 2.3 Hành trình thực (mm)
- X: min = ___, max = ___
- Y: min = ___, max = ___
- Z: min = ___, max = ___

### 2.4 steps_per_mm
- X: ___ (giả định 80)
- Y: ___ (giả định 80)
- Z: ___ (giả định 100 — servo nên không áp dụng)
-Firmware cài ban đầu đã chuẩn
---

## 3. Bút và servo (C4) — ⚠/✅

- Z khi bút **lên**: 5 (giả định 5)
- Z khi bút **xuống**: 0 (giả định 0)
- Z trung gian (bút chạm giấy nhẹ):
- Servo gpio.32 min_pulse_us/max_pulse_us: 1350 / 1950 (theo YAML, theo yaml là chuẩn)

## 4. Giao thức và trạng thái

### 4.1 Báo cáo trạng thái thô (10 mẫu)

| # | Trạng thái | Nguyên văn |
|---|---|---|
| 1 | Idle sau boot | 
Grbl 4.1 [FluidNC v4.1.1 (esp32-wifi) '$' for help]
[MSG:INFO: ALARM: Unhomed]
ALARM:14
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0


| 2 | Idle sau Home | `<Idle\|MPos:0.000,0.000,0.000\|WCO:...>` |

> $H
~ Home  MPos -38.763,0.000,0.000  WPos -38.763,0.000,0.000  F2000
~ Home  MPos -61.438,-12.762,0.000  WPos -61.438,-12.762,0.000  F1414  Pn:Y
[MSG:Homed:XY]
ok
~ Home  MPos -66.500,-19.825,0.000  WPos -66.500,-19.825,0.000  F0
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
$X

~ Idle  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0


| 3 | Jog X+ | `<Jog\|MPos:...>` |
> $J=G91 G21 X50 F500
ok
~ Jog  MPos 0.150,0.000,0.000  WPos 0.150,0.000,0.000  F707
~ Jog  MPos 8.788,0.000,0.000  WPos 8.788,0.000,0.000  F707
~ Jog  MPos 19.450,0.000,0.000  WPos 19.450,0.000,0.000  F707

| 4 | Run | `<Run\|MPos:...\|F:...>` |

# Job started: zigzag_F3000_1500lines.gcode (1507 lines)
~ Run  MPos 34.513,0.000,5.000  WPos 34.513,0.000,5.000  F8485
~ Run  MPos 11.006,0.044,0.000  WPos 11.006,0.044,0.000  F4243
~ Run  MPos 27.388,0.287,0.000  WPos 27.388,0.287,0.000  F4243
~ Run  MPos 21.094,0.481,0.000  WPos 21.094,0.481,0.000  F42

| 5 | Hold:1 
| 6 | Hold:0 

> [realtime] hold
~ Hold:1  MPos 22.062,0.087,0.000  WPos 22.062,0.087,0.000  F3228
~ Hold:0  MPos 28.300,0.113,0.000  WPos 28.300,0.113,0.000  F0
~ Hold:0  MPos 28.300,0.113,0.000  WPos 28.300,0.113,0.000  F0

~ Hold:0  MPos 28.300,0.113,0.000  WPos 28.300,0.113,0.000  F0
~ Hold:0  MPos 28.300,0.113,0.000  WPos 28.300,0.113,0.000  F0

> [Dừng êm nhưng có vẻ ko êm lắm]
~ Run  MPos 2.412,0.413,0.000  WPos 2.412,0.413,0.000  F4243
Job cancelled. The machine is in Alarm: unlock, then lift the pen.
> [realtime] reset
[MSG:INFO: ALARM: Abort Cycle]
ALARM:3
Grbl 4.1 [FluidNC v4.1.1 (esp32-wifi) '$' for help]
~ Alarm  MPos 41.406,0.569,0.000  WPos 41.406,0.569,0.000  F0
~ Alarm  MPos 41.406,0.569,0.000  WPos 41.406,0.569,0.000  F0

==> Mở khóa $X để về idle, chưa nâng bút. Cũng như bấm nút dừng khẩn cấp ko đc
==> Có vẻ do claude mới chỉ giúp tôi đổi html, app và api chứ chưa đổi backend machine với route 



### 4.2 Các trường có/không có trong báo cáo
- [x] MPos
- [x] WPos
- [x] WCO
- [x] Bf (planner, rx)
- [x] FS / F
- [x] Pn
- [x] SD (nếu có)
- [ ] Khác: ___


[MSG:Homed:XY]
~ Idle  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
[MSG:INFO: ALARM: Hard Limit]
ALARM:1
[MSG:ERR: Reset to continue]
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0  Pn:XY
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
> $X
ok
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
> [realtime] reset
[MSG:INFO: ALARM: Unhomed]
ALARM:14
Grbl 4.1 [FluidNC v4.1.1 (esp32-wifi) '$' for help]
~ Alarm  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
> $X
[MSG:INFO: Caution: Unlocked]
ok
~ Idle  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0


### 4.3 Phản hồi các lệnh đặc biệt
- `G10 L20 P1 X0` → [nguyên văn]

> $J=G91 G21 X-50 F3000
ok
~ Jog  MPos 31.600,0.000,0.000  WPos -19.400,0.000,0.000  F4243
~ Idle  MPos 1.000,0.000,0.000  WPos -50.000,0.000,0.000  F0
> G10 L20 P1 X0 Y0
ok
~ Idle  MPos 1.000,0.000,0.000  WPos -50.000,0.000,0.000  F0
> G10 L20 P1 X0 Y0
ok
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
> G10 L20 P1 X0 Y0
ok
~ Idle  MPos 1.000,0.000,0.000  WPos 0.000,0.000,0.000  F0
> $J=G91 G21 X-1 F3000
ok
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
> G10 L20 P1 X0G10 L20 P1 X0
[MSG:ERR: Bad GCode: G10 L20 P1 X0G10 L20 P1 X0]
error:24
[MSG:ERR: Gcode axis command conflict]
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
> G10 L20 P1 X0
ok
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos -1.000,0.000,0.000  F0
~ Idle  MPos 0.000,0.000,0.000  WPos 0.000,0.000,0.000  F0

- `???` (dòng vô nghĩa) → [error:X / ok]

> ???`
[MSG:ERR: Bad GCode: `]
error:1
[MSG:ERR: Expected GCodecommand letter]

error:3
[MSG:ERR: Invalid $ statement]

- `g0 x1000` → [error:X / ok / ALARM:X] 

> g0 x1000
[MSG:INFO: Soft limit exceeded on X axis: target 1000.000 mm, limit [-0.013, 285.013] mm]
[MSG:INFO: Commanded mpos: X1000.000 Y0.000 Z0.000]
[MSG:INFO: GCode line: g0 x1000]
ok
[MSG:INFO: ALARM: Soft Limit]
ALARM:2


---

## 5. Danh mục ALARM / Error thực tế

| Mã | Kích hoạt bằng cách | Nguyên văn firmware | Ý nghĩa thực |
|---|---|---|---|
| ALARM:1 | __ (chạm cứng) | `ALARM:1` | Hard limit |
| ALARM:2 | __ (chạy quá giới hạn mềm) | `ALARM:2` | Soft limit |
| ALARM:3 | __ (Reset khi đang chạy) | `ALARM:3` | Abort |
| ALARM:6 | __ | `ALARM:6` | Homing fail reset |
| ALARM:8 | __ | `ALARM:8` | Homing fail pulloff |
| ALARM:9 | __ | `ALARM:9` | Homing fail approach |
| ALARM:14 | __ (G0 khi chưa Home) | `ALARM:14` | Unhomed |
| error:1 | __ | `error:1` | ❓ cần giải thích |
| error:2 | __ | `error:2` | Bad number |
| error:3 | __ | `error:3` | Invalid $ |
| error:9 | __ | `error:9` | SystemGcLock |
| error:15 | __ | `error:15` | Travel exceeded |
| error:16 | __ | `error:16` | Invalid jog |
| error:20 | __ | `error:20` | Unsupported G |
| error:22 | __ | `error:22` | Missing feed |

---
$E
0: No error
1: Expected GCodecommand letter
2: Bad GCode number format
3: Invalid $ statement
4: Negative value
5: Setting disabled
6: Step pulse too short
7: Failed to read settings
8: Command requires idle state
9: GCode cannot be executed in lock or alarm state
10: Soft limit error
11: Line too long
12: Max step rate exceeded
13: Check door
14: Line too long
15: Max travel exceeded during jog
16: Invalid jog command
17: Laser mode requires PWM output
18: No Homing/Cycle defined in settings
19: Single axis homing not allowed
20: Unsupported GCode command
21: Gcode modal group violation
22: Gcode undefined feed rate
23: Gcode command value not integer
24: Gcode axis command conflict
25: Gcode word repeated
26: Gcode no axis words
27: Gcode invalid line number
28: Gcode value word missing
29: Gcode unsupported coordinate system
30: Gcode G53 invalid motion mode
31: Gcode extra axis words
32: Gcode no axis words in plane
33: Gcode invalid target
34: Gcode arc radius error
35: Gcode no offsets in plane
36: Gcode unused words
37: Gcode G43 dynamic axis error
38: Gcode max value exceeded
39: P param max exceeded
40: Check startup pins
60: Failed to mount device
61: Read failed
62: Failed to open directory
63: Directory not found
64: File empty
65: File not found
66: Failed to open file
67: Device is busy
68: Failed to delete directory
69: Failed to delete file
70: Failed to rename file
80: Number out of range for setting
81: Invalid value for setting
82: Failed to create file
83: Failed to format filesystem
90: Failed to send message
100: Failed to store setting
101: Failed to get setting status
110: Authentication failed!
111: End of line
112: End of file
113: System Reset
114: No Data
115: Deferred
120: Another interface is busy
130: Jog Cancelled
150: Bad Pin Specification
151: Bad Runtime Config Setting
152: Configuration is invalid. Check boot messages for ERR's.
160: File Upload Failed
161: File Download Failed
162: Read-only setting
170: Expression Divide By Zero
171: Expression Invalid Argument
173: Expression Unknown Operator
174: Expression Argument Out of Range
175: Expression Syntax Error
176: Flow Control Syntax Error
177: Flow Control Not Executing Macro
178: Flow Control Out of Memory
179: Flow Control Stack Overflow
180: Parameter Assignment Failed
181: Gcode invalid word value
ok

$A
0: None
1: Hard Limit
2: Soft Limit
3: Abort Cycle
4: Probe Fail Initial
5: Probe Fail Contact
6: Homing Fail Reset
7: Homing Fail Door
8: Homing Fail Pulloff
9: Homing Fail Approach
10: Spindle Control
11: Input Pin Initially On
12: Ambiguous Switch
13: Hard Stop
14: Unhomed
15: Init
16: Expander Reset
17: GCode Error
18: Probe Hard Limit


## 6. Hành vi runtime

### 6.1 Hold → Reset (D4)
- Hold từ Run: `Hold:1` sau ___ giây → `Hold:0` sau ___ giây
- Reset từ Hold:0: `ALARM:X`
- Reset thẳng từ Run: `ALARM:X`
- Sau Reset: cần `$X` mới jog được → [đúng / sai]

### 6.2 Jog trong Hold
- `$J=...` khi Hold:0 → [ok / error:X]

### 6.3 Rút cáp USB (1 lần)
- Máy chạy nốt queue: [có / không, dừng sau ___ giây]
- Backend báo `lost_reason`: ___
- Sau cắm lại: state = ___, cần [reset board / chỉ cần $X / chỉ cần Home lại]

### 6.4 Streaming
- Tệp test: ___ dòng
- Tốc độ gửi: ___ dòng/giây
- State có nhảy Run/Idle không: [có / không]
- Kết luận D10: ___

---

## 7. Việc phải sửa sau khi có kết quả

Sau khi điền đủ mục 1-6, cập nhật:

- [x] `backend/app/links/sim_link.py`: travel, Z, protocol khớp dữ liệu thật
- [x] `frontend/js/core/config.js`: Z bút và hành trình giờ lấy từ Cài đặt → Cấu hình máy (`VIEW.flipX/flipY` vẫn trong config.js)
- [ ] `frontend/css/style.css`: `--canvas-aspect` (nếu hành trình thay đổi)
- [ ] `DECISIONS.md`: C3, C4, C5, D4, D5, D10 đổi ⚠ → ✅ và ghi giá trị thật
- [ ] `docs/frontend-blocks.md`: cập nhật lệnh bút, hành trình
- [x] `backend/app/links/protocol.py`: bổ sung tên error/alarm mới theo `$E` / `$A`
- [ ] `locales/vi.json`, `en.json`: bổ sung khóa alarm/error mới (nếu thiếu)

---

## 8. Ghi chú tự do

[Ghi lại bất cứ điều gì bất thường, không khớp với giả định, hoặc muốn nhắc phiên sau]

Clarify 1: Tức lf bấm dừng lại trên bảng header, hay bấm ! khi đang jog thì sẽ hủy luôn. 
Có sự khác biệt giữa jog và chạy g90, tức nếu chạy G0 X100 chả hạn thì có thể dừng về hold và tiếp tục nhưng jog thì nó sẽ dừng hẳn và về idle, ko cho tiếp tục, dừng tại x y lúc bấm dừng luôn

Clarify 2: Nếu chỉ là 1 dòng code thì sẽ chạy hết cả dòng code, chưa thử với cả 1 tệp