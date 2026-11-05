# 02 — Phần cứng và thông số máy

> Dành cho người đọc. Một nơi cho mọi con số của máy thật: linh kiện, cấu hình FluidNC, hành vi firmware đã kiểm, kết quả thử.
> Ký hiệu: ✅ đã xác nhận trên máy thật · ⚠ chưa đo / suy luận · ⏳ còn phải thử.
> Đổi một con số ở đây thì đổi cả chỗ tương ứng trong mã (cột "Trong phần mềm").

## 1. Sơ đồ khối phần cứng

```
Nguồn Mean Well 12 V 6 A ──┬──► MKS DLC32 V2.1 (ESP32, FluidNC v4.1.1) ◄── USB (CH340) ── máy chủ
                           │        ├─ driver TMC2209 #1 ──► động cơ NEMA17 (X)  ┐ khung CoreXY,
                           │        ├─ driver TMC2209 #2 ──► động cơ NEMA17 (Y)  ┘ đai GT2, puly 20 răng
                           │        ├─ gpio.32 (tín hiệu PWM 50 Hz) ──► servo nâng bút
                           │        ├─ gpio.36 ◄── công tắc hành trình X
                           │        └─ gpio.35 ◄── công tắc hành trình Y
                           └──► hạ áp XL4005 → ~6 V ──► nguồn servo (GND nối chung với MKS)
```

## 2. Linh kiện

| Phần | Linh kiện | Ghi chú |
|---|---|---|
| Khung | **CoreXY**, mẫu Extruh pen plotter (Printables 734327) | vùng làm việc **285 × 318 mm**, Z (nâng bút) **5 mm** |
| Cơ cấu bút | bút **hạ xuống giấy nhờ trọng lực**, servo chỉ **nâng** cụm bút | lực bút = trọng lượng cụm bút (muốn nét chắc hơn thì thêm khối nặng). Hạ chậm = đáp nhẹ, đỡ gãy ngòi |
| Servo | **JX PS-1109MG** 9 g, bánh răng kim loại, analog | 4,8–6 V; 0,12 s/60° ở 4,8 V, 0,10 s/60° ở 6 V (theo nơi bán) |
| Nguồn servo | hạ áp **XL4005**, đặt **~6 V** | GND phải nối chung với MKS. Nên có tụ 470–1000 µF sát servo |
| Động cơ | 2 × **NEMA17 17HS4401** | ~1,5–1,7 A mỗi pha (nhà bán ghi không thống nhất ⚠) |
| Driver | 2 × **TMC2209**, điện trở đo **R100** (0,1 Ω), Vref **1,4 V** | Irms ≈ 0,766 × Vref ≈ **1,07 A** (đỉnh ≈ 1,5 A). Dải Vref cho phép 0,2–2,2 V |
| Truyền động | đai **GT2**, puly **20 răng**, vi bước **1/16** | 200 bước × 16 ÷ (20 răng × 2 mm) = **80 bước/mm** |
| Nguồn tổng | **Mean Well 12 V 6 A** (72 W) | MKS nhận 12–24 V |
| Bút vẽ tranh | **Sakura 0,4** | nét thật **~0,55 mm** (mực loang, đo 03/11/2026) |
| Bút viết chữ | **bút bi 0,5** | nét bi thường mảnh hơn cỡ bi ⚠ cần đo |
| Thêm được | ESP32-S3 (kit) | chưa có webcam |

## 3. Cấu hình FluidNC đang dùng

Tệp cấu hình trên mạch: `ConfigNCKH-16.yaml`. Sửa được ngay trên giao diện: Cài đặt → Cấu hình máy → Áp dụng (chỉ trong RAM) → Lưu vào mạch (sao lưu bản cũ về `data/config_backups/` trước).

| Thông số | Giá trị | Ghi chú |
|---|---|---|
| Bước / mm X, Y, Z (`$100 $101 $102`) | 80 / 80 / 100 | thước 100 mm vẽ ra đúng 100 mm ✅ |
| Hành trình (`$130 $131 $132`) | 285 / 318 / 5 mm | |
| Tốc độ tối đa X, Y (`$110 $111`) | 6000 mm/min; Z 3000 | |
| Gia tốc X / Y / Z | **2000 / 2000 / 3000 mm/s²** | nâng từ 600 / 600 / 1000 ngày 03/11/2026 |
| `junction_deviation_mm` | 0,01 | nhỏ → qua góc nhọn phải giảm tốc mạnh (vì vậy zigzag quay đầu bằng nửa vòng tròn) |
| `planner_blocks` | 16 | hàng đợi chuyển động |
| `arc_tolerance_mm` | 0,002 | |
| Servo Z | `gpio.32`, 50 Hz, xung 1350–1950 µs | Z 0–5 mm ↔ ~54° ⚠ suy luận |
| Công tắc hành trình | X `gpio.36`, Y `gpio.35`, mức `:high` (giữ = kích) | ✅ không đảo nhãn |
| `must_home` | true | khởi động lên Alarm (mục 5) |
| Chân có thể còn trống | `gpio.34` (đầu Z-limit, chỉ đọc), `gpio.22` (đầu probe), `gpio.33` | ⚠ dò lại sơ đồ mạch trước khi nối |
| Wi-Fi của mạch (bản `esp32-wifi`) | có thể tự phát mạng "FluidNC" (192.168.0.1) | ⚠ ai vào WebUI là **vượt qua mọi khóa của phần mềm**. Kiểm `$WiFi/Mode`, tắt hoặc đặt mật khẩu mạnh trước demo |

## 4. Thông số phần mềm dùng cho máy này

| Thông số | Giá trị | Trong phần mềm |
|---|---|---|
| Bút lên / giữa / xuống | **Z3 / Z1,5 / Z0** (từ 03/11/2026; trước đó Z5 / Z2,5) | Cài đặt → Cấu hình máy, mục App; mặc định ở `services/profile.py`, `frontend/js/core/config.js` |
| Tốc độ nâng bút / hạ bút | 3000 / **2000** mm/min (hạ chậm hơn, đỡ nảy) | tab Tạo bản vẽ; `spec.py` |
| Chờ sau nâng / sau hạ | **0,05 s** / 0,05 s | tab Tạo bản vẽ |
| Tốc độ vẽ / di chuyển | **5000** / 6000 mm/min | tab Tạo bản vẽ |
| Bề rộng nét thật ÷ cỡ ngòi | **1,375** | `LINE_WIDTH_RATIO` trong `styles.py` |
| Gốc giấy | góc trên trái O(0,0), Y hướng xuống; A6 ⊂ A5 ⊂ A4 cùng neo ở O | `layout.py` |
| Hướng trục X / Y | ✅ **đúng** (chủ dự án xác nhận 05/11/2026) với `VIEW.flipX = flipY = false`, `invert_y = false` | `core/config.js`, `gcode.to_machine` |

## 5. Hành vi firmware đã xác nhận trên máy thật ✅

| # | Hành vi | Phần mềm xử lý thế nào |
|---|---|---|
| F1 | Khởi động lên **Alarm** (do `must_home`), G-code bị chặn (error:9). Gửi `$X` → Idle → **mọi G-code chạy được kể cả chưa Home** | giao diện cảnh báo khi chạy tệp mà chưa Home |
| F2 | Gửi `g0 x1000` (vượt hành trình): firmware trả `ok` **trước**, `ALARM:2` **sau** | máy chủ coi Alarm đến sau là lỗi của tác vụ |
| F3 | Đang chạy tệp gửi `!` → Hold (~100 ms), `~` chạy tiếp được | nút Tạm dừng / Tiếp tục |
| F4 | Đang jog gửi `!` → **hủy jog ngay**, về Idle, `~` không chạy tiếp | nút Hủy jog riêng |
| F5 | Reset khi đang chạy → `ALARM:3`. Reset khi Hold → Idle (không alarm) hoặc `ALARM:3` tùy thời điểm. Reset khi Alarm chưa Home → `ALARM:14` | dừng gấp xử lý cả ba |
| F6 | Chạm công tắc (`ALARM:1`): **phải Reset trước rồi mới `$X`** được | `_unlock_alarm` |
| F7 | Rút cáp khi đang chạy: máy chạy nốt bộ đệm (vài giây) rồi dừng. Cắm lại báo `PermissionError(13)`, nối lại là được, không cần reset mạch | tác vụ báo `failed`, khóa lại về chỉ đọc, ghi điểm dừng |
| F8 | Báo cáo trạng thái có đủ `MPos, WPos, WCO, Bf, F, Pn`; dòng `[MSG:Homed:XY]` sau khi Home xong | đoán Home, đèn công tắc |
| F9 | Chế độ chỉ đọc: `$$ $E $A $Limits $SS $G` đọc được; `$X`, `? ! ~` gửi được | danh sách lệnh chỉ đọc theo `$CMD` thật |
| F10 | Sửa cấu hình qua USB: `$Config/Filename`, `$CD` (in YAML đang chạy), `$/axes/x/max_rate_mm_per_min[=v]` (ghi vào RAM), `$LocalFS/List`, `$CD=/localfs/<tệp>` (ghi ra tệp). Bộ nhớ trống ~60 KB. Tắt bật nguồn giá trị vẫn còn. `$CD=` viết lại tệp dạng chuẩn (mất chú thích `#`) nhưng máy chạy bình thường | Cài đặt → Cấu hình máy |
| F11 | Dừng êm: chờ Idle → `$J=G90 G21 Z… F…` → xác nhận Z. Dừng gấp: Hold → Reset → Idle → nâng bút. Không alarm | [04_TAB_DIEU_KHIEN.md](04_TAB_DIEU_KHIEN.md) mục 6 |
| F12 | Gửi từng dòng chờ `ok`: 1500 dòng ở F3000 không nhảy Run / Idle | cách gửi hiện tại là đủ |

## 6. Kết quả thử máy

| Ngày | Thử | Kết quả |
|---|---|---|
| 29/10/2026 | thử tay không động cơ | các hành vi F1–F11 |
| 03/11/2026 | **mất bước**: G0 liên tục 6000 mm/min ~20 phút, gia tốc 2000 / 3000, Vref 1,4 V | dấu + vẽ lại trùng khít ✅. Driver ~50 °C, động cơ ấm nhẹ |
| 03/11/2026 | tốc độ vẽ 6000 mm/min | đường thẳng vẫn đậm, đủ nét (ảnh chụp xa) ⚠ chưa đo bề rộng theo tốc độ |
| 03/11/2026 | chờ hạ bút 0,05 s | đầu nét không hụt ✅ |
| 03/11/2026 | **bề rộng nét** Sakura 0,4 | **~0,55 mm**: dải cách 0,5 mm đặc hẳn, 0,6 mm gần đặc, 0,8 mm còn thấy sợi. Đo ở tốc độ vẽ cũ 3000 ⏳ đo lại ở 5000 |
| 03/11/2026 | vệt kéo khi di chuyển xa | vệt mảnh cong từ góc giấy, đuôi + chấm mực cuối nét, chưa rõ nguyên nhân ⏳ bài 7.5. Đường chéo trên tờ mất bước là do bấm Home khi bút chưa nâng (đã sửa: Home tự nâng bút) |
| 03/11/2026 | ảnh Phong cảnh | lỗ trắng ở khối trái (xem trước cũng có, nhiều khả năng do ảnh); giọt mực lồi ở mép dưới khối (đã đổi quay đầu sang nửa vòng tròn ⏳ chụp lại) |
| 05/11/2026 | hướng trục X / Y | ✅ đúng |

## 7. Còn phải thử ⏳

- Thời gian Home (X, Y, XY).
- Cung `G2 / G3` trên máy thật (phần mềm hiện chỉ sinh `G0 / G1`).
- `G4 P` tính bằng giây trên FluidNC 4.1.1 (đang giả định giây).
- Z3 có đủ trên giấy cong không (bài 7.5).
- Bề rộng nét ở 5000 mm/min, đường cong tông bằng thang xám in thật.

## 8. Ghi chú điện tử cho người nối dây

- Thêm ESP32 thì dùng **hạ áp 5 V riêng** cho mạch logic: servo giật dòng có thể làm ESP32 khởi động lại.
- Muốn chạy nhanh hơn: tăng dần Vref (1,4 → 1,57 V ≈ 1,2 A RMS) kèm bài thử mất bước, có tản nhiệt TMC2209, đo nhiệt.
- Nguồn 24 V cho mô-men tốt hơn ở tốc độ cao (MKS nhận 12–24 V, XL4005 nhận tới ~32 V) ⚠ kiểm các thiết bị 12 V khác.
- Chân `gpio.34–39` chỉ đọc vào, không có điện trở kéo lên bên trong → cần kéo lên ngoài.
- Dừng khẩn cấp thật = **nút cắt nguồn 12 V**, không qua phần mềm (FluidNC không hỗ trợ nút E-Stop trực tiếp).
