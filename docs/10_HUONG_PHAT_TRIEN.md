# 10 — Hướng phát triển (ý tưởng chưa xếp lịch)

> Dành cho người đọc và người viết báo cáo (phần "hướng phát triển"). Chưa làm. Mọi thời gian là **ước lượng**, phải đo trên MiniPC thật.
> Ký hiệu: ✅ chủ dự án đã đồng ý ý này · 💡 gợi ý · ⚠ chưa kiểm chứng.
> Thư viện / thuật toán ảnh có thể thêm: [06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md) mục 17. Việc đã xếp lịch: [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md).

Nguyên tắc chung: **không sửa firmware FluidNC.** Đóng góp của đề tài nằm ở cách ghép dây chuyền, tối ưu cho phần cứng yếu, phần cứng gắn thêm bên ngoài, và **số đo trước / sau**.

---

## 1. Tính năng vẽ mới: chỉ thêm "nguồn nét"
Phần "nét → G-code" dùng chung. Mỗi tính năng mới chỉ là một nguồn nét mới đổ vào đó:
```
PDF từ Word  ──► ảnh từng trang → skeleton ──┐
Câu lệnh     ──► AI tạo ảnh nét ─────────────┼──► NÉT ──► G-code (đã có)
Mẫu chữ tay  ──► bộ chữ riêng → bộ viết chữ ─┘
```
Thứ tự nên làm: tab Beta PDF → bộ chữ + bộ viết chữ → lấy mẫu chữ tay → viết Word bằng chữ tay → AI tạo ảnh.

### 1.1 Tab Beta: in nguyên trang PDF ✅ (khả thi cao, làm trước)
- Tab riêng: nạp PDF, xem trang như bản in, chọn trang, vector hóa trang đó, một preset **"Văn bản"**.
- Người dùng tự "Lưu thành PDF" trong Word (giữ đúng font, dấu tiếng Việt, bố cục). Không đổi Word → PDF trên MiniPC (LibreOffice thiếu font làm chữ xuống dòng khác).
- Kết xuất trang thành ảnh (`pypdfium2` hoặc PyMuPDF) → skeleton (đã có) → mỗi nét chữ một đường giữa.
- Đọc cấu trúc PDF (PyMuPDF `get_text("rawdict")`, `get_drawings()`): đường kẻ bảng vẽ thẳng bằng vector, chữ đậm vẽ 2 đường, ảnh trong trang đi kiểu tô. Lớp chữ (bút bi 0,5) và lớp tranh (Sakura 0,4) thành 2 tệp G-code.

| Chữ cỡ 14–16 | Nét chữ thật | Bút 0,5 vẽ một nét |
|---|---|---|
| Thường (Arial, Times) | ~0,45–0,55 mm | gần y bản in |
| Đậm | ~0,8 mm | hơi mảnh; muốn giống thì 2 đường sát nhau |
| Nét mảnh của Times | ~0,15–0,2 mm | dày bằng nét chính, vẫn dễ đọc |
| Lỗ chữ e, a, o | ~1 mm | còn hở |

**Preset "Văn bản" khác preset ảnh ở 7 điểm:** (1) độ phân giải ~10–12 điểm / mm (`OVERSAMPLE` ~5–6 thay 1,3; chữ "o" cỡ 14 chỉ ~10 điểm ảnh ở độ phân giải ảnh thường); (2) tắt nối khe hở (khe giữa hai chữ chỉ 0,5–0,8 mm); (3) cắt râu (đã có); (4) làm mượt; (5) nét dày > 1,5 × bút thì 2 đường; (6) tỷ lệ 1:1; (7) không khuyên chữ dưới cỡ 8.

Thời gian: trang A4 kín chữ ~2000 ký tự × 2,5 nét ≈ **5000 lần nhấc bút**. Ở ~0,25 s mỗi lần nhấc / hạ (cấu hình hiện tại) + vẽ ≈ **35 phút** ⚠ ước. Thử ngay không cần code: xuất trang PDF ra PNG 300 dpi → tab Tạo bản vẽ → preset Schematic: sẽ thấy đúng hai lỗi (chữ thô, chữ dính), chính là điểm (1) và (2).

### 1.2 Bộ chữ + bộ viết chữ
- Định dạng bộ chữ: mỗi ký tự vài biến thể, mỗi biến thể là các nét đo theo chiều cao chữ; kèm phong cách (nghiêng, khoảng cách, độ lượn, lệch ngẫu nhiên).
- Bộ viết chữ: văn bản → xếp dòng trên khổ giấy → chọn biến thể (không lặp liền) → lệch nhẹ → nét → G-code.
- Dấu tiếng Việt ghép theo quy tắc (chữ gốc + 5 dấu thanh; khó nhất là chồng hai dấu ấ ầ ẩ ẫ ậ). Chưa có font nét đơn nào có sẵn dấu tiếng Việt (Hershey không có).

### 1.3 Lấy mẫu chữ tay
- Tờ mẫu có ô kẻ: mỗi ký tự viết 3 lần (~80 ký tự × 3 ≈ 2–3 trang) → hình dáng. Một đoạn văn tự nhiên → đo phong cách chung.
- Tốt nhất: **viết thẳng lên màn hình cảm ứng** trong app (ghi đúng thứ tự nét, sạch, không cần skeleton).
- Chỉ dùng chữ của chính mình hoặc người đã đồng ý; không dùng để nộp thay bài bắt buộc tự viết.

### 1.4 Gõ câu lệnh → AI tạo ảnh → bản vẽ (làm cuối)
- **Không chạy AI tạo ảnh trên MiniPC** (không card đồ họa: vài phút mỗi ảnh, 4–8 GB RAM).
- Gọi dịch vụ trên mạng: nhanh, nhẹ cho MiniPC, nhưng cần Internet, mất phí theo ảnh, phải giới hạn số lần khi mở cho người ngoài.
- Tự thêm vào câu lệnh "tranh nét đen trắng, không tô bóng".

### 1.5 MiniPC có chịu nổi không
| Việc | Tải |
|---|---|
| PDF → ảnh → skeleton | vừa (~16 lần điểm ảnh so với ảnh thường, vẫn trong giới hạn) |
| Bộ viết chữ | rất nhẹ |
| AI tạo ảnh qua mạng | rất nhẹ (tốn phí) |
| AI tạo ảnh tại chỗ | **không nên** |

Giới hạn bảo vệ đã có: ảnh ≤ 40 MB, SVG ≤ 20 MB, ảnh gốc ≤ 60 triệu điểm, ảnh làm việc 400–4000 điểm cạnh dài, mỗi lần xử lý ≤ 600 s, RAM tiến trình ≤ 4 GB (Linux), tổng điểm nét ≤ 2 triệu, 2-opt ≤ 15 000 nét, G-code ≤ 200 000 dòng.

---

## 2. Mở cho nhiều người (sau bản khách + quản lý)
| Ý | Ghi chú |
|---|---|
| Tài khoản "người dùng" ✅ | chỉ tên + mật khẩu, không email; mật khẩu băm bằng `hashlib.scrypt` 💡; form đăng ký không bao giờ tạo quản lý |
| Thư mục riêng theo tài khoản ✅ | người này không xem được của người kia; giữ 3 ngày; mọi route đọc tệp phải kiểm chủ |
| Hàng chờ tạo nét ✅ | tách "nạp ảnh" khỏi "tạo nét" (nút "Tạo nét", đã đưa vào kế hoạch [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md) mục 5 bước 4); một việc một lúc theo thứ tự đến; mỗi người chỉ hủy việc của mình; `idle.py` phải tính việc đang chờ |
| Lưu nét gốc `strokes.json` ✅ | đổi bố trí / G-code mà không vector lại; "dấu vân tay" = băm (ảnh + vùng cắt + tham số vector) để biết nét đã cũ |
| Màu chỉ cho quản lý ✅ | khóa ở máy chủ, không chỉ ẩn ô |
| Cloudflare nâng cao 💡 | Cloudflare Access làm thêm lớp đăng nhập ngoài; giới hạn tần suất theo `CF-Connecting-IP` |

---

## 3. Điện tử và IoT (không sửa firmware)

### 3.1 Dùng chân trống của MKS (chỉ sửa YAML + nối dây)
- `feed_hold_pin` + `cycle_start_pin`: **2 nút cứng Tạm dừng / Chạy tiếp** trên máy, chạy cả khi mất mạng.
- **Cảm biến bút** (công tắc nhỏ hoặc Hall + nam châm trên giá bút) vào `probe` (`gpio.22`): báo cáo có `Pn:P` → phần mềm biết **bút thật sự đã nhấc** (hiện chỉ biết lệnh Z), thêm đèn "Bút" cạnh đèn X / Y, dừng khi bút kẹt. Phần mềm đã đọc `Pn` sẵn.
- ⚠ Dò chân bằng sơ đồ mạch trước ([02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) mục 3, 8).

### 3.2 ESP32-S3: các nút mạng riêng (không đụng MKS)
| Nút | Làm gì | Từ khóa |
|---|---|---|
| Bảng điều khiển không dây | OLED / TFT + 3 nút + còi + LED: trạng thái, % tiến độ, tạm dừng / chạy tiếp qua API (cần "mã thiết bị"). Nút an toàn vẫn phải nối dây | `ESP32-S3 OLED HTTP client` |
| Đo điện năng | INA226 trên dây 12 V → Wh mỗi bản vẽ | `INA226 ESP32` |
| Nhiệt độ | DS18B20 trên driver / động cơ → cảnh báo | `DS18B20 ESP32` |
| Camera xem trực tiếp | ESP32-S3 + OV2640, MJPEG 640×480 ⚠ đo khung/s | `ESP32-S3 CameraWebServer` |
| Giao tiếp | MQTT (Mosquitto chạy trên MiniPC, không cần Internet) hoặc HTTP | `paho-mqtt`, `PubSubClient` |

ESP32 dùng hạ áp 5 V riêng (servo giật dòng làm ESP32 khởi động lại).

### 3.3 Hướng nghiên cứu khác
| Hướng | Làm gì | Từ khóa |
|---|---|---|
| Cách gửi G-code | so "gửi một dòng chờ `ok`" với "đếm ký tự" (lấp bộ đệm nhận); vẽ biểu đồ `Bf:` theo thời gian để thấy chỗ "đói lệnh". Rủi ro an toàn: dòng lỗi vẫn nằm trong bộ đệm | `grbl character counting streaming` |
| Tinh chỉnh cấu hình | gia tốc, `junction_deviation`, vi bước → bảng thời gian vẽ / chất lượng nét | `grbl junction deviation` |
| Bút servo | đo thời gian nhấc / hạ thật bằng máy hiện sóng / logic analyzer; thử servo nhanh hơn | `FluidNC RcServo` |
| Driver | TMC2209 StealthChop (êm) và SpreadCycle (khỏe ở tốc độ cao); nguồn 24 V | `TMC2209 standalone SpreadCycle` |
| Camera tự căn giấy | mã ArUco ở góc bàn → tự tìm vị trí giấy, tự đặt Zero; chụp tờ đã vẽ → so với xem trước bằng SSIM + OCR | `OpenCV ArUco homography` |
| Thông báo | MQTT lên bảng theo dõi, bot Telegram báo "vẽ xong / lỗi" | `Telegram bot sendMessage` |
| So đường truyền | độ trễ USB so với Wi-Fi của FluidNC; ghi lý do chọn USB (Wi-Fi vượt qua khóa của phần mềm) | `FluidNC telnet websocket` |

---

## 4. Tính năng phần mềm nhỏ
- 💡 Vệt bút theo dòng G-code cho cả macro / tiếp tục tác vụ (hiện chỉ cho tệp đang chạy).
- 💡 `.devcontainer/` cho GitHub Codespaces.
- 💡 Đổi PIN quản lý ngay trên giao diện; mã QR địa chỉ LAN trên giao diện.
- 💡 2-opt trong Web Worker, chỉ khi đo trên MiniPC thấy sắp xếp nét lâu.
- 💡 Thời gian ước tính có tính gia tốc (cần số liệu máy thật).
- 💡 Ghi mốc tiến độ định kỳ để tiếp tục được cả khi mất điện / tắt server giữa chừng.

---

## 5. Lời khuyên đã kiểm là sai (từ một tư vấn AI khác, 02/11/2026): đừng làm theo
- "`pdftocairo -svg` giữ chữ trong thẻ `<text>`": không có tài liệu xác nhận; có người báo SVG ra không thấy chữ.
- "`vpype-text` tự ép font Hershey tiếng Việt": plugin ngừng phát triển; Hershey không có dấu tiếng Việt.
- "`findContours` trên nét 1 điểm ảnh": ra hai đường bao.
- "`potrace` vector hóa nét mượt": ra nét đôi.
- "`docx2pdf`": cần Word cài sẵn; MiniPC Ubuntu không có.
