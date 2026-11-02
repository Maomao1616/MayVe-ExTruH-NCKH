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
- Lưu vào mạch: ghi đè YAML thành công, bản gốc được sao lưu về `data/config_backups/`.
- Tắt nguồn, bật lại: giá trị đã lưu vẫn còn.
- `$CD=` viết lại tệp theo dạng chuẩn (mất chú thích `#`, `engine: I2S_STREAM` thành `engine: I2S`); máy vẫn khởi động và chạy bình thường.
- Thanh bút 3 nấc (Z5 / Z2.5 / Z0): chạy đúng, nấc sáng khớp vị trí.

---

## B. Chưa test / Làm tiếp
- B1: Xác nhận thời gian Home chính xác (X, Y, XY).
- B2: Hướng X+/Y+ thực tế trên giấy (dự kiến X+ đi trái, Y+ đi xuống).
- B3: Z bút lên/xuống thực tế (Servo GPIO 32).
- B4: Cung G2/G3 trên máy thật.

---

## C. Phần cứng và cấu hình hiện tại (ghi 02/11/2026)

### C1. Linh kiện (chủ dự án cung cấp, chưa đo lại)
| Phần | Hiện tại | Ghi chú |
|---|---|---|
| Servo bút | **JX PS-1109MG** 9 g, bánh răng kim loại, analog | Theo nơi bán: 4,8–6,0 V; 0,12 s/60° (4,8 V), 0,10 s/60° (6 V); 2,2 / 2,5 kg·cm |
| Nguồn servo | Hạ áp **XL4005** → 5 V, lấy từ nguồn 12 V | Dây âm (GND) của XL4005 phải nối chung với MKS (tín hiệu servo đo so với GND của MKS) |
| Cơ cấu nâng bút | Mẫu **Extruh pen plotter** (Printables 734327): bút **hạ xuống giấy nhờ trọng lực**, servo chỉ **nâng** cụm bút lên | Lực bút lên giấy = trọng lượng cụm bút (không phụ thuộc servo) → muốn nét đậm / chắc hơn thì **thêm khối nặng** cho cụm bút. Thời gian "hạ" = thời gian servo rút về + bút rơi. Hạ chậm = đáp nhẹ, đỡ gãy ngòi |
| Động cơ bước | **NEMA 17 17HS4401** (X, Y) | Tài liệu nhà bán không thống nhất: 1,5–1,7 A mỗi pha, ~40 N·cm. ⚠ Xem nhãn / datasheet đúng lô hàng trước khi tăng dòng |
| Driver | **2 × TMC2209**, Vref **1,2 V**; trên module ghi **R100** (điện trở đo 0,1 Ω), chip in `2539 a327c Germany` | Với R100: Irms ≈ 0,766 × Vref ≈ **0,92 A** (đỉnh ≈ 1,3 A), khoảng 55–60 % dòng định mức → dư an toàn cho máy vẽ nhẹ. Muốn ~1,2 A RMS thì Vref ≈ 1,57 V (công thức Trinamic, dải Vref cho phép 0,2–2,2 V). ⚠ Ghi chú: một số trang tính 0,71 × Vref (cho điện trở 110 mΩ), không đúng với R100 |
| Nguồn tổng | **Mean Well 12 V 6 A** (72 W) | MKS DLC32 nhận 12–24 V |
| Truyền động | Đai **GT2**, puly **20 răng**, vi bước **1/16** | Khớp `$100 = $101 = 80` bước/mm (200 × 16 / 40 mm) |
| Bút vẽ tranh | **Sakura đầu 0,4** | Không dùng 0,2 vì sợ gãy ngòi khi chạy nhanh |
| Bút viết chữ | **Bút bi 0,5** | Nét bi thường mảnh hơn cỡ bi (khoảng một nửa, tùy loại) → ⚠ đo trên tờ hiệu chỉnh |
| Mạch thêm | Có thể mua ESP32-S3 dạng kit | Webcam: chưa có |

### C2. Cấu hình trên mạch (đọc từ bản sao lưu `ConfigNCKH-16.yaml` 29/10/2026)
- Gia tốc X / Y **600 mm/s²**, Z **1000 mm/s²**; `junction_deviation_mm` **0,01**; `planner_blocks` **16**; `arc_tolerance_mm` 0,002; bước `I2S`.
- Servo Z: `gpio.32`, 50 Hz, **1350–1950 µs** (Z 0–5 mm ↔ ~54° nếu servo ~11 µs/độ, ⚠ suy luận).
- Công tắc hành trình: X `gpio.36`, Y `gpio.35`. Mục `control` (dừng, chạy tiếp, macro…) và `probe` đều `NO_PIN`.
- Chân **có thể còn trống** (theo cấu hình chính thức của FluidNC cho DLC32 V2.1): `gpio.34` (đầu Z-limit, chỉ đọc vào), `gpio.22` (đầu probe), `gpio.33` (bản chính thức dùng cho `macro0`). ⚠ Dò lại bằng sơ đồ mạch / đồng hồ trước khi nối.
- **Một chu kỳ nhấc / hạ bút hiện tại** ≈ 0,7 s: `G1 Z` với `pen_feed` 3000 mm/min (≈ 0,15 s cho 5 mm với gia tốc Z 1000) + `G4 P0.2`, làm hai lần (hạ và nhấc).
- Firmware bản `esp32-wifi`: nếu chưa cài Wi-Fi, FluidNC có thể tự phát mạng "FluidNC" (192.168.0.1). Ai vào mạng đó dùng WebUI là **vượt qua mọi khóa của phần mềm**. ⚠ Kiểm `$WiFi/Mode`; khi demo nên tắt hoặc đặt mật khẩu mạnh.
