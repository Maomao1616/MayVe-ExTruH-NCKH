# P01 — ESP32-S3 làm cầu nối máy chủ ↔ mạch MKS (chuẩn bị)

> Tạo 27/11/2026. Trạng thái: ⏳ **đã chuẩn bị** (đọc sơ đồ mạch, đọc mã FluidNC, mô phỏng trễ). **Chưa mua mạch, chưa có dòng mã ESP nào, chưa ghi gì xuống MKS.**
> Quyết định gốc: `docs/08_QUYET_DINH_THIET_KE.md` P52. Tài liệu chính: `docs/07_MANG_KET_NOI_TRIEN_KHAI.md` mục 4 (số đo trễ), mục 13 (thiết kế).

## 1. Mục tiêu
Máy chủ (PC nhà, sau này server cloud) chạy phần mềm như hiện nay. Quanh máy vẽ chỉ có **một ESP32-S3 N16R8**: tự gọi ra tên miền (WebSocket bảo mật) qua Cloudflare, nhận G-code theo gói, giữ trong kho, tự gửi từng dòng xuống MKS qua dây UART. USB, Wi-Fi telnet và điểm phát dự phòng của MKS **giữ nguyên** (thêm một phương pháp, không thay). Nút dừng cứng nối **thẳng MKS**, không qua ESP.

## 2. Phần cứng (chủ dự án báo 27/11/2026 + đọc sơ đồ `MKS DLC32 V2.1_003 SCH.pdf`)
**Đang dùng** (chủ dự án): 2 khe driver X, Y; chân **S của cổng TTL** (= `gpio.32`, nhãn `LC` trên sơ đồ trang 2: servo bút, khớp `output_pin: gpio.32` trong cấu hình); 2 cổng endstop X, Y (`gpio.36`, `gpio.35`). Driver chạy qua I2S (`gpio.16, 17, 21`). Còn lại trống. Cấu hình máy (bản sao 29/10 trong `data/config_backups`) để trống `spi`, `sdcard`, `control`.
**Nguồn ESP32-S3:** mạch hạ áp **Mini560 5 V** riêng (chủ dự án đã đặt). Bắt buộc **nối chung GND** với MKS. **Không** nối 5 V / 3V3 giữa hai mạch.

### 2.1 Chân còn trống có ra đầu cắm (đọc sơ đồ, CHƯA đo bằng đồng hồ)
| Đầu cắm (chân) | Nhãn sơ đồ | GPIO của MKS | Đặc điểm (sơ đồ) | Đề xuất |
|---|---|---|---|---|
| **EXP2 (6)** | LCD_MOSI | **IO23** | nối thẳng ESP32 | **TX của MKS** → RX của ESP32-S3 |
| **EXP2 (1)** | LCD_MISO | **IO19** | nối thẳng ESP32 | **RX của MKS** ← TX của ESP32-S3 |
| **EXP2 (9)** | GND | | | **GND chung** |
| EXP2 (2) | LCD_SCK | IO18 | nối thẳng ESP32 | dự phòng: nút Chạy tiếp (`gpio.18:low:pu`) |
| EXP2 (8) | RESET | EN | nối chân reset ESP32 | **KHÔNG đụng** (chạm GND là reset mạch) |
| EXP2 (10) | +3V3 | | nguồn 3,3 V của MKS | không dùng (ESP32-S3 có nguồn riêng) |
| EXP1 (8) | LCD_RS | IO33 | trông như nối thẳng (chưa chắc) | dự phòng |
| EXP1 (3, 4, 5, 7) | LCD_EN / RST / TOUCH_CS / CS | IO5 / 27 / 26 / 25 | đi qua IC đệm một chiều U7, U8 (chỉ **ra**) | **không** dùng làm RX; IO5 là chân khởi động |
| EXP1 (1) | BEEPER | — | ra từ IC dịch 74HC595 (QH), không phải GPIO | không dùng |
| EXP1 (10) | +5V | | | không dùng |
| J2 "I2C" (3, 4) | I2C_SDA / I2C_SCL | IO0 / IO4 | nối thẳng; **IO0 là chân khởi động** (kéo lên R4) | phương án UART thứ hai nếu EXP2 hỏng; tránh để IO0 bị kéo xuống lúc bật nguồn |
| J11 (Z-endstop) | Z- | **IO34** | **chỉ vào**; kéo lên 3V3 (R20) + lọc RC (R23, C19) | **nút Tạm dừng**: `feed_hold_pin: gpio.34:low` (nút nối chân tín hiệu với GND) |
| J12 (Probe) | Probe | IO22 | kéo lên (R24) + điện trở nối tiếp + diode kẹp | **cảm biến bút** (kế hoạch, docs/09 mục 3.1); hoặc nút Chạy tiếp nếu chưa làm cảm biến |

Không dùng chân endstop / probe làm UART: có tụ lọc RC làm méo cạnh xung ở 115200 baud.

### 2.2 Đấu dây đề xuất (chưa đấu)
```
ESP32-S3 TX  ──► EXP2 chân 1 (IO19, RX của MKS)
ESP32-S3 RX  ◄── EXP2 chân 6 (IO23, TX của MKS)
ESP32-S3 GND ─── EXP2 chân 9 (GND)  ── GND của Mini560
Mini560 5V   ──► chân 5V của ESP32-S3       (không nối gì sang 5V / 3V3 của MKS)
Nút Tạm dừng: J11 chân tín hiệu (IO34) ── nút ── GND của J11
```
Chân UART phía ESP32-S3: đề xuất **GPIO17 (TX), GPIO18 (RX)** (mặc định UART1 của nhiều thư viện, chưa kiểm cho bo cụ thể). ESP32-S3 định tuyến UART qua ma trận GPIO nên đổi được; **tránh** GPIO0, 3, 45, 46 (khởi động), 19, 20 (USB), 26–37 (flash / PSRAM octal của bản N16R8). Kiểm sơ đồ bo ESP32-S3 thật trước khi đấu.

### 2.3 Cấu hình MKS cần thêm (đề xuất; **chủ dự án tự ghi xuống mạch**, sao lưu trước)
Khóa đã kiểm trong mã FluidNC ở `D:\FluidNC-4.1.1` (`Uart.cpp`, `UartChannel.h`, `Control.cpp`, `MachineConfig.cpp` dòng 60–61), chưa thử trên mạch:
```yaml
uart1:
  txd_pin: gpio.23
  rxd_pin: gpio.19
  baud: 115200          # mặc định 115200; mode mặc định 8N1
uart_channel1:
  uart_num: 1           # report_interval_ms mặc định tắt: máy chủ tự hỏi `?` như hiện nay
control:
  feed_hold_pin: gpio.34:low
  # cycle_start_pin: gpio.18:low:pu   (nếu dùng nút Chạy tiếp)
```
Cổng phụ vào cùng danh sách kênh với USB (`UartChannel.cpp` dòng 36): nhận G-code và ký tự tức thời như USB. **Mạch nhận lệnh từ mọi cổng cùng lúc** (USB, telnet, WebUI, UART phụ): đang vẽ qua ESP thì không bấm WebUI.

## 3. Phần mềm: hướng đã chốt (chủ dự án 27/11: "ESP giữ dữ liệu, tải dần")
**Số đo:** qua Cloudflare mỗi lượt ~0,13 s, có lần 1,16 s (docs/07 mục 4). **Mô phỏng** (`tools/mo_phong_gui_lenh.py`, mô hình, không phải số đo):

| Cách gửi (3000 dòng nét 0,5 mm, lý tưởng 11,2 s) | Trễ đo được | 4G giật (0,3 s, vọt 3 s, 8 %) |
|---|---|---|
| A. Từng dòng chờ `ok` qua mạng | 570 s, khựng mọi dòng | 1 888 s |
| B. Đếm ký tự qua mạng | 48 s, khựng 2 300 lần | 159 s |
| C. Kho ESP 5000 dòng, gói 1000, nạp trước 2000 | ~11,9 s, 0 khựng | 11,8–14,9 s, **0 khựng** (5 hạt) |

**Chốt (mô hình, đo lại khi có mạch):**
- ESP giữ **kho ≥ 5000 dòng** (~100 KB, để trong PSRAM 8 MB); máy chủ gửi **gói ~1000 dòng**; ESP **nạp trước ~2000 dòng** (hoặc cả bài nếu ngắn hơn) rồi mới bắt đầu.
- ESP gửi xuống MKS theo **đếm ký tự tại chỗ** (tổng byte chưa có `ok` ≤ bộ đệm nhận của MKS; mặc định kênh 256 byte, cổng UART phụ **chưa kiểm**: thử từ 128 byte cho an toàn).
- **Máy chủ quyết định, ESP thực hiện:** máy chủ giữ PIN, khóa chuyển động, nhật ký, quyết định chạy / dừng / chạy tiếp; ESP báo về số dòng đã được `ok` để máy chủ biết vị trí (dùng cho "Tiếp tục từ điểm dừng").
- **Ký tự tức thời** (`?` `!` `~` Ctrl-X) máy chủ gửi thì ESP chuyển **ngay**, không xếp sau kho. Ctrl-X: ESP **xóa kho**.
- **Mất kết nối với máy chủ quá N giây khi đang vẽ: ESP tự gửi `!`** (tạm dừng) xuống MKS. N đề xuất 2 s (chưa chốt; ngắn hơn thì dừng oan khi mạng giật).
- Giữ kết nối liên tục (mở mới mất ~1,75 s, đo 27/11).

### 3.1 Giao thức máy chủ ↔ ESP (bản nháp, để bàn)
| Hướng | Tin | Nội dung |
|---|---|---|
| ESP → máy chủ | `hello` | mã thiết bị, chìa khóa (bí mật riêng, ở `data/`, không lên Git), phiên bản mã ESP, cỡ kho |
| máy chủ → ESP | `chunk` | mã tác vụ, số thứ tự dòng đầu, danh sách dòng |
| ESP → máy chủ | `ack` | mã tác vụ, đã `ok` tới dòng nào, kho còn trống bao nhiêu |
| máy chủ → ESP | `rt` | một ký tự tức thời (chuyển ngay) |
| ESP → máy chủ | `rx` | dòng mạch trả lời (`<...>` trạng thái, `ok`, `error:`, `ALARM:`, `[MSG:]`), chuyển nguyên văn để backend dùng lại `links/protocol.py` |
| máy chủ → ESP | `abort` | xóa kho, không gửi thêm |

Backend thêm một kiểu kết nối mới (vd `links/esp_link.py`, `kind="esp"`) cùng giao diện `BaseLink`, và một đường nhận WebSocket cho thiết bị (xác thực bằng chìa khóa thiết bị, **không** mở cho khách). `REAL_MODES` phải gồm `"esp"` (khóa chuyển động áp như USB).

### 3.2 Trạng thái lên điện thoại: trễ bao nhiêu, ai hỏi `?` (27/11, ước tính, chưa đo)
Hiện nay máy chủ hỏi `?` 10 lần/giây (`POLL_S = 0.1`, `backend/app/services/machine.py:79`). Từ 27/11 luồng SSE (`backend/app/api/events.py`) **đẩy ngay** khi có trạng thái / nhật ký mới (máy đánh thức luồng; trước đó chờ nhịp nhìn 0,1 s). Đo trên máy giả, PC i5-9400F: chờ trong máy chủ trước **32 ms** trung bình (lớn nhất 94), sau **1,3 ms** (lớn nhất 16 = bước đồng hồ Windows).

| Đường | Trạng thái tới điện thoại chậm (sau khi đẩy ngay) | Ghi chú |
|---|---|---|
| USB, máy chủ cạnh máy vẽ (hiện nay) | ~0,05–0,15 s | nhịp hỏi `?` 0,1 s là chính |
| Qua ESP, máy chủ ở nhà | ~0,15–0,3 s; lúc mạng vọt ~1 s | thêm 2 lượt Cloudflare (ESP → nhà, nhà → điện thoại) |
| Lệnh bấm trên web (jog, Tạm dừng) qua ESP | thêm ~0,15–0,2 s | vì thế **nút cứng nối thẳng MKS là bắt buộc** |

Ai hỏi trạng thái (chọn khi làm gói 5–6):

| Cách | Làm sao | Được | Mất |
|---|---|---|---|
| a. Máy chủ hỏi `?` qua mạng (như USB) | `rt "?"` mỗi 0,1 s | không đổi backend | mỗi `?` đi một lượt Internet; mạng giật thì trạng thái giật theo |
| b. **ESP tự hỏi `?` tại chỗ** (đề xuất) | ESP gửi `?` xuống UART mỗi 0,1 s, chuyển `<...>` lên máy chủ qua `rx` | trạng thái đều dù chiều xuống nghẽn; backend chỉ cần bỏ vòng hỏi khi `kind="esp"` | ESP phải lọc trùng nếu máy chủ cũng gửi `?` |
| c. MKS tự báo | `uart_channel1: report_interval_ms: 100` | ESP không cần hỏi | xem dưới |

Cách c, đọc mã FluidNC 4.1.1 (`UartChannel.h:68-79`, `Channel.cpp:242-300`): mặc định 0 (tắt); nhỏ nhất **50 ms**; ngoài nhịp đều còn báo **ngay** khi đổi trạng thái, đổi chân, bắt đầu / hết tác vụ; lúc đứng yên chỉ báo khi có thay đổi; **tự gửi thêm dòng `[GC:...]`** (chế độ G-code) khi đổi, nên ESP / `links/protocol.py` phải chịu được dòng không ai hỏi; bật mục này thì mạch **lặp lời chào đến khi thiết bị trả lời**, ESP phải đáp. Cách c ghi vào cấu hình mạch (chủ dự án ghi), nên thử b trước; c để dành nếu muốn ESP nhẹ hơn.

## 4. Các gói việc (theo thứ tự; mỗi gói hỏi chủ dự án trước khi làm)
| # | Gói | Ai | Kiểm chứng | Trạng thái |
|---|---|---|---|---|
| 1 | Đọc sơ đồ, chọn chân (mục 2) | Claude | bảng chân | ✅ 27/11 (chưa đo) |
| 2 | Mô phỏng trễ, chốt kho / gói / nạp trước (mục 3) | Claude | `tools/mo_phong_gui_lenh.py` + `tests/test_mo_phong_gui_lenh.py` | ✅ 27/11 (mô hình) |
| 3 | Đo bằng đồng hồ: IO19, IO23 không dính tụ / điện trở lạ; J11 đủ kéo lên | chủ dự án | ảnh + số | ⏳ |
| 4 | Mua ESP32-S3 N16R8; chụp sơ đồ chân bo mua về | chủ dự án | ảnh | ⏳ |
| 5 | Mạch giả ESP trong máy chủ (giả lập kho + UART) + `links/esp_link.py` + đường WebSocket thiết bị + test | Claude | pytest với mạch giả có trễ; khóa chuyển động áp cho `esp` | ⏳ **phải hỏi** (cấu trúc mới, đụng an toàn) |
| 6 | Mã ESP32-S3 (Arduino / ESP-IDF, chưa chọn): Wi-Fi + trang cài Wi-Fi, WebSocket TLS, kho trong PSRAM, đếm ký tự UART, tự `!` khi mất máy chủ | Claude viết, chủ dự án nạp | thử với MKS **không lắp bút / nhấc bút**, chạy tệp 7.6 | ⏳ |
| 7 | Thêm `uart1` / `uart_channel1` / `control` vào cấu hình MKS | chủ dự án ghi xuống mạch | `$CD` in ra có mục mới; `$I` ổn | ⏳ |
| 8 | Đo thật: số dòng/giây, khựng (Biểu đồ + `log_read.py`), rút mạng giữa bản vẽ | chủ dự án | bài C7–C9 ở `docs/11` | ⏳ |

## 5. Xong khi
- Một bản vẽ thật chạy qua ESP32-S3 từ máy chủ ở xa, **không khựng** khi mạng thường, và **tự tạm dừng** khi rút mạng; "Tiếp tục từ điểm dừng" chạy được.
- Nút Tạm dừng cứng dừng máy dù mất mạng.
- USB và Wi-Fi telnet vẫn chạy như cũ; toàn bộ test qua.

## 6. Câu hỏi còn mở
- Thư viện ESP: Arduino (dễ đọc) hay ESP-IDF (chặt hơn)? Đề xuất Arduino + thư viện WebSocket có TLS.
- N (giây mất máy chủ thì tự `!`) và cỡ bộ đệm UART phụ của MKS: chốt sau khi đo.
- Ai hỏi trạng thái `?`: ESP tự hỏi tại chỗ (đề xuất) hay MKS tự báo `report_interval_ms` (mục 3.2). Chốt khi làm gói 5–6.
- Cloudflare Access chặn thiết bị không đăng nhập: dùng "service token" cho ESP hay đường riêng không qua Access.
