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
| Bút vẽ tranh | **Sakura 0,4**, thử thêm **Uniball 150**; giấy **Ivory 250 g/m²** (từ 11/11/2026) | giấy thường: nét ~0,55 mm (mực loang, đo 03/11/2026). Giấy Ivory, 8000 mm/min (tờ hiệu chỉnh 12/11/2026): Sakura **0,45–0,5** mặt láng, **0,5–0,55** mặt nhám (phần mềm dùng 0,50); UB-155 **0,35–0,4** (dùng 0,38); UM-100 **~0,4** |
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
| Bút lên / giữa / xuống (điều khiển tay) | **Z5 / Z1,5 / Z0** (từ 09/11/2026: nút Bút lên, Home tự nâng, hủy tác vụ nâng bút, jog dùng Z5 cho chắc) | Cài đặt → Cấu hình máy, mục App; mặc định ở `services/profile.py`, `frontend/js/core/config.js` |
| Z nhấc khi **sinh G-code** | **Z3** (chỉnh 3 / 2 / 1,5 theo bản vẽ) | cùng mục App, ô "Z nhấc khi sinh G-code"; tab Tạo bản vẽ lấy làm mặc định cho ô Z |
| Tốc độ nâng bút / hạ bút | 3000 / **2000** mm/min (hạ chậm hơn, đỡ nảy) | tab Tạo bản vẽ; `spec.py` |
| Chờ sau nâng / sau hạ | **0 s** / 0 s (từ 13/11/2026, [09](09_QUYET_DINH_THIET_KE.md) C10; trước 0,02 và 0,05) | tab Tạo bản vẽ; `spec.py` |
| Tốc độ vẽ / di chuyển | **8000** / 8000 mm/min (từ 12/11/2026) | tab Tạo bản vẽ |
| Nét cong trong G-code | cung **G2/G3** (từ 13/11/2026, [09](09_QUYET_DINH_THIET_KE.md) D12) | `drawing/arcs.py`, công tắc `USE_ARCS` ở `drawing/gcode.py` |
| Bề rộng nét thật ÷ số trong ô "Bút vẽ" | **1,0** (từ 11/11/2026 ô đó ghi thẳng nét đo trên giấy của từng bút; trước là 1,1 và 1,375) | `LINE_WIDTH_RATIO` trong `styles.py`; số từng bút ở `index.html` ô `draw-pen-width` + `spec.PENS` |
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
| F10 | Sửa cấu hình qua USB: `$Config/Filename`, `$CD` (**chỉ in** YAML đang chạy, không ghi gì), `$/axes/x/max_rate_mm_per_min[=v]` (ghi vào RAM), `$LocalFS/List`, `$CD=/localfs/<tệp>` (ghi YAML đang chạy ra tệp, = nút "Lưu vào mạch" nhưng không sao lưu). Mục không có ô trên giao diện (vd `$/axes/x/motor0/pulloff_mm=1.5`, `$/axes/x/homing/cycle=2`, `$/axes/x/homing/settle_ms=100`; đường dẫn = vị trí trong tệp YAML, chữ thường) đổi bằng terminal rồi bấm "Lưu vào mạch" (từ 11/11/2026 nút luôn bấm được sau khi đọc cấu hình). `$10` (= `$Report/Status`) không nằm trong YAML: lưu ngay vào bộ nhớ riêng (NVS) khi gõ. Bộ nhớ trống ~60 KB. Tắt bật nguồn giá trị vẫn còn. `$CD=` viết lại tệp dạng chuẩn (mất chú thích `#`) nhưng máy chạy bình thường | Cài đặt → Cấu hình máy |
| F11 | Dừng êm: chờ Idle → `$J=G90 G21 Z… F…` → xác nhận Z. Dừng gấp: Hold → Reset → Idle → nâng bút. Không alarm | [04_TAB_DIEU_KHIEN.md](04_TAB_DIEU_KHIEN.md) mục 6 |
| F12 | Gửi từng dòng chờ `ok`: 1500 dòng ở F3000 không nhảy Run / Idle | cách gửi hiện tại là đủ |
| F13 | (13/11/2026) Gửi từng dòng chờ `ok` qua USB 115200 đạt **~125 dòng/giây** (124–130, mọi độ dài đoạn); hàng đợi chuyển động **15 khối**; `G4` bắt máy chạy hết hàng đợi rồi mới chờ | ước tính thời gian tính giới hạn này (`EST_LINES_PER_S`, `EST_DWELL_FLUSH_S`); nét cong ghi bằng G2/G3 |
| F14 | (13/11/2026) **G2/G3 chạy đúng và đủ tốc** (vòng R10 ở 8000: 5,7 s, hàng đợi đầy) | `drawing/arcs.py` |
| F15 | (13/11/2026) Tốc độ báo trong `FS:` (biểu đồ Tốc độ thật) **cao hơn thật tới 1,41 lần** tùy hướng chạy (máy CoreXY: vòng G2 thật ~7 900 mm/phút, biểu đồ 10 000–11 300; đường ngang G0 10 000 báo 14 142) | đọc tốc độ thật bằng quãng đường ÷ thời gian, không đọc số trên biểu đồ ⏳ sửa biểu đồ |
| F16 | (13/11/2026) Servo sau Home: bấm Home bút nhảy lên Z5, Home xong có lúc **tụt về chỗ cũ** hoặc giật rồi đứng ở Z5 | không ảnh hưởng nhiều (chủ dự án); lần sau tụt thì xem Terminal có `pen re-lift not sent` ⏳ |

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
| 11/11/2026 | ảnh con mèo (preset Chân dung), Pigma 0,4, giấy thường: tối đa 8000, gia tốc 3000, junction 0,05, Z3, SpreadCycle | chạy êm, không thấy mất bước. Nền lộ ranh giới các mức đậm nhạt; đọng mực cuối nét (nghi bút + giấy, thử lại bằng Ivory + Uniball 150) |
| 12/11/2026 | tờ hiệu chỉnh A6 (UB-155, UM-100, Sakura), nhấc bút, 7.2 / 7.3 / 7.4 ở 7000–10000, thang xám A6 các kiểu, ảnh thật | vẽ **8000** ổn, đoạn dài lên được **10000**; gia tốc **3000** ổn (không tăng: sợ gãy ngòi); Z nhấc **3** đẹp (2,5 / 2 gần như không khác, dễ không nhấc khỏi giấy); chờ **0,02 s** chưa thấy lỗi. Thời gian thật = 1,7–1,9 × ước tính cũ; buffer tụt về 0 ở mỗi lần nhấc bút. ⚠ Servo: bật mạch xong phải bấm Bút lên một lần, không thì lệnh đầu tiên làm bút tụt về giữa; sau Home thỉnh thoảng tụt (~1250 µs) → phần mềm tự nhích Z xuống 0,5 rồi lên lại sau mỗi lần Home (`machine._relift_pen_after_home`) ⏳ kiểm trên máy |
| 13/11/2026 | tờ nhấc bút (chờ 0 / 0,02 × Z3 × hạ 2000), tờ 7.6 đoạn ngắn / cung G2 ở 8000, Sakura 0,5, Ivory | **chờ 0 dùng được** (nét đủ, hàng đợi đầy suốt; chờ 0,02 hàng đợi tụt về 0 mỗi lần nhấc), cả tờ thật 17 s. 7.6: đoạn 1 / 0,5 / 0,25 / 0,1 mm mất 6,0 / 11,6 / 23,3 / 60,7 s (~125 dòng/giây), **G2 5,7 s**; trên giấy 5 vòng như nhau. Thật ÷ ước tính cũ = 3,46 (tờ 7.6) → sửa ước tính (nay 110,9 s so với thật 111 s). Servo sau Home: xem F16 |

## 7. Còn phải thử ⏳

- Thời gian Home (X, Y, XY).
- Bản vẽ thật có cung G2/G3 do phần mềm sinh (từ 13/11/2026): chạy hết không báo lỗi, so thời gian thật với ước tính.
- `G4 P` tính bằng giây trên FluidNC 4.1.1 (đang giả định giây; từ 13/11 mặc định không còn G4).
- Servo sau Home (F16): khi bút tụt, Terminal có dòng `pen re-lift not sent` không.
- Z3 có đủ trên giấy cong không (bài 7.5).
- Bề rộng nét ở 5000 mm/min, đường cong tông bằng thang xám in thật.

## 8. Ghi chú điện tử cho người nối dây

- Thêm ESP32 thì dùng **hạ áp 5 V riêng** cho mạch logic: servo giật dòng có thể làm ESP32 khởi động lại.
- Muốn chạy nhanh hơn: tăng dần Vref (1,4 → 1,57 V ≈ 1,2 A RMS) kèm bài thử mất bước, có tản nhiệt TMC2209, đo nhiệt.
- Nguồn 24 V cho mô-men tốt hơn ở tốc độ cao (MKS nhận 12–24 V, XL4005 nhận tới ~32 V) ⚠ kiểm các thiết bị 12 V khác.
- Chân `gpio.34–39` chỉ đọc vào, không có điện trở kéo lên bên trong → cần kéo lên ngoài.
- Dừng khẩn cấp thật = **nút cắt nguồn 12 V**, không qua phần mềm (FluidNC không hỗ trợ nút E-Stop trực tiếp).
