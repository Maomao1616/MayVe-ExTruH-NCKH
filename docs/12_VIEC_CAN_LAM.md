# 12 — Tình trạng và việc cần làm

> **Dành cho AI đọc đầu phiên** (và chủ dự án). Việc kế tiếp: mục 4.2 (chủ dự án), 4.3 (AI làm ngay được).

> Sổ làm việc, cập nhật 27/11/2026. **Một nơi duy nhất** cho: đã xong · cần thử · làm tiếp (theo thứ tự bạn chốt).
> Cách thử từng bài: [11](11_THU_NGHIEM.md). Lý do từng quyết định: [08](08_QUYET_DINH_THIET_KE.md). Ý tưởng để dành: [09](09_HUONG_PHAT_TRIEN.md).
> Cỡ việc: **S** vài giờ · **M** nửa đến một ngày · **L** nhiều ngày.

## 1. Tình trạng chung

| Khối | Tính năng | Đã kiểm ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95 % | ~70 % |
| Tạo bản vẽ (ảnh, SVG, bản thảo, hàng đợi) | ~95 % | ~60 % (thuật toán đã xem bản thảo, chưa in hết) |
| Cài đặt, cấu hình máy | ~90 % | ~70 % |
| Phân quyền, bản mang đi | ~85 % | ~60 % |
| Kết nối: USB ✅ · Wi-Fi telnet (mã + test) · Cloudflare ✅ · ESP32-S3 (kế hoạch) | USB, Cloudflare ~95 % · Wi-Fi ~80 % · ESP32-S3 0 % | USB, Cloudflare đã chạy thật; **Wi-Fi telnet chưa nối mạch thật** |

Test tự động (chạy lại 27/11/2026, hai lần liền): máy chủ **712** (8 bài tab Beta cần PyMuPDF, thiếu thì tự bỏ qua; `test_joblog` (`test_old_logs_are_pruned`; 27/11 thêm `test_log_is_closed_when_disconnected_midway`: `IndexError` vì danh sách nhật ký rỗng sau khi ngắt, 1 lần trong cả bộ song song, chạy riêng 3/3 qua, **chưa tìm nguyên nhân**) và vài bài chờ thời gian có thể hỏng chập chờn khi máy bận, chạy riêng thì qua), giao diện **72**. `pytest` mặc định chạy song song 6 tiến trình (`backend/pytest.ini`, ~30 giây thay vì ~112 giây; gỡ lỗi từng bài thì `pytest -n 0`); độ phủ đo bằng `pytest --cov=app`: **93 %** (26/11/2026), `machine.py` 94 % sau khi thêm `tests/test_stop_paths.py` (đường dừng an toàn và đường lỗi bằng mạch giả viết tay). Đã rà test bằng Cline (`data/ra-soat-test.md`, 26/11): siết 16 bài chỉ kiểm mã 200 / 400 thành kiểm mã lỗi và nội dung, xóa 1 bài trùng; giữ `test_arcs::test_default_delays_are_zero_so_no_g4` vì nó bảo vệ giá trị MẶC ĐỊNH của thời gian chờ bút. `test_motion_unlock::test_route_motion` hỏng chập chờn do dùng chung đối tượng `machine` (chế độ `sim` được nhớ sau khi ngắt), đã sửa 27/11 để kiểm thẳng cờ `allow_motion`. Chỗ chưa phủ: `serial_link.py` (cổng USB thật, chỉ thử trên máy thật). Còn thiếu chủ yếu: **in thật** các bản mới (Chất lượng tối đa, Xoắn ốc mới, tách mực, tab Beta) và **thử trên máy chủ mới** (cloud / Linux, chưa có).

## 2. Bản đồ việc

```
 ĐÃ XONG (mục 3)                 LÀM TIẾP, THEO THỨ TỰ (mục 4.2)                              CUỐI
 ───────────────                 ───────────────────────────────                              ─────
 máy + G-code chuẩn ──┐
 thuật toán (đóng băng)┼─► 1. IN THỬ (11 mục A) → chốt hằng; đo máy chủ mới (11 mục 9) ─┐
 tách mực, tab Beta ──┘   (Soạn font: kế hoạch ở 10 mục 11b, chưa làm)            │
                                  2. NỐI MẠNG: Cloudflare ✅ → Wi-Fi telnet ◄─────────┘
 an toàn / phân quyền ─────────► 3. ESP32-S3 CẦU NỐI + NÚT CỨNG (YAML + dây) ──► 4. CAM, CẢM BIẾN BÚT
```

## 3. Đã xong (chỉ từ khóa và hằng đã chốt; lý do ở 08, số ở 06)

| Nhóm | Đã chốt |
|---|---|
| **Máy và G-code** | vẽ / di chuyển **8000**, gia tốc **2700**, junction **0,02**, servo **5,3 V** (22/11/2026); Z nhấc **3**, hạ **2000**, chờ **0**; nút bút `G90 G0 Z…`: Lên **Z5** · Giữa **Z3** · Xuống **Z0**; nét cong **G2/G3**; **115200 baud**, gửi từng dòng chờ `ok`; `$10=3` cho biểu đồ hàng đợi |
| **Máy đã thử xong** | mất bước ở 7000–10000 ổn · tốc độ tối đa **10000** · TMC2209 **SpreadCycle** · Home, Z, đèn X / Y đúng · tiếp tục từ điểm dừng đúng · G2/G3 trên bản vẽ thật · tab Điều khiển mượt · tiếng "khực" hết với 2700 / 0,02 |
| **Bút, giấy** | ô "Bút vẽ" = **nét đo trên giấy**: UB-155 **0,38** · UM-100 **0,40** · Sakura **0,50** · bút bi 0,5; giấy Ivory 250 g/m² mặt bóng |
| **An toàn, phân quyền** | máy mặc định chỉ đọc; khóa chuyển động tự khóa sau 15 phút; Home tự nâng bút; hủy 3 chế độ; tiếp tục từ điểm dừng; PIN quản lý đổi được; khách xem + **Gửi ảnh** (tự xóa 5 ngày, ≤ 6 ảnh / giờ); SSE cho trạng thái |
| **Tạo bản vẽ** | nạp ảnh → cắt / chỉnh tông → **Tạo nét**; **vùng chủ thể** elip / chữ nhật / **Tự động** / **Vẽ tay**; SVG; bản thảo + hàng đợi; 2–4 màu và **tách mực theo bộ bút** (đen–đỏ–navy hoặc CMYK, ô Độ nổi màu); zoom khung vẽ; Tờ thử; Biểu đồ số liệu chạy máy |
| **Kiểu nét** | 5 kiểu: Đan chéo (mặc định) · Đường dòng · Sóng điều biên · Xoắn ốc (viết lại 22/11) · Đường bao (tên cũ: [05](05_TAB_TAO_BAN_VE.md) mục 3); ô **Chất lượng tối đa** (`style.unlimited`) cho 3 kiểu tô; vòng **sửa sai tông** 1 lượt; hằng số: [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 19 |
| **5 preset** | Chân dung · Hình vẽ 2D · Phong cảnh · Bản vẽ kỹ thuật · Chất lượng tối đa ([08](08_QUYET_DINH_THIET_KE.md) P14) |
| **Tab Beta PDF** | đọc chữ thật trong PDF, viết lại bằng chữ viết tay nối nét (chữ HOA và số kiểu in), dấu tiếng Việt tự ghép, khung bảng từ vector, hình vẽ nét lấy đường giữa, ảnh chụp đi đường tô ảnh; PDF thật 32 trang chạy hết ([10](10_TAB_BETA_PDF.md)) |
| **Giao diện** | màu nhấn vàng an toàn `#ffd400`; số đo WCAG: viền rõ, viền ô nhập ≥ 3:1, chữ ≥ 12 px (P45); hai khung vẽ giấy ngà + nét đen; âm báo xong / lỗi; **lung linh nhẹ** (24/11, [08](08_QUYET_DINH_THIET_KE.md) P48): khung thả tệp, công tắc ngày / đêm ở Cài đặt, thẻ thông tin, nút chính, thanh trượt 5 ô tông ảnh, thanh bước tiến trình, chữ hướng dẫn viết lại học thuật |
| **Triển khai, mạng** | bản mang đi Windows + `Cap nhat.bat`; launcher ưu tiên `backend\.venv` rồi mới `Python\`; demo không cần Internet; **Cloudflare Tunnel + tên miền chạy thật** (24–25/11; bạn cùng dự án chạy được bằng `data` + `cloudflared.exe`, 27/11); nút QR; launcher chép `cloudflared.exe` sang thư mục tạm và báo hộp thoại khi đường ống sập; **Wi-Fi telnet** (`links/telnet_link.py`, 26/11, 10 bài test với mạch giả, **chưa nối mạch thật**): [07](07_MANG_KET_NOI_TRIEN_KHAI.md) |
| **Đo đạc** | `tools/do_thoi_gian.py` (giây từng bước, RAM đỉnh, thông tin máy); `ink_real.py` đo được cả Đường dòng, Xoắn ốc; số laptop 22/11 ở [11](11_THU_NGHIEM.md) mục 9 |
| **Giao diện điện thoại + dọn tab Điều khiển (P51, 26/11)** | thanh tab đáy, khối thu gọn bằng mũi tên, nút Mở rộng / Thu gọn, Terminal luôn mở trên máy tính, Hủy tác vụ luôn hiện, số lăn tọa độ, vệt sáng laser; **bỏ nút đổi tốc độ** (backend không còn nhận `feed_*`); máy chủ gửi `Cache-Control: no-cache` cho tệp giao diện ([03](03_CAU_TRUC_PHAN_MEM.md) mục 6.2, [08](08_QUYET_DINH_THIET_KE.md) P51). **Chưa thử trên điện thoại thật** (thanh tab đáy với vùng an toàn iPhone, bàn phím ảo, ô xám sau khi chạm) |
| **Gộp tài liệu mạng (27/11/2026)** | Triển khai + Mạng và tên miền + phiếu Wi-Fi gộp thành [07](07_MANG_KET_NOI_TRIEN_KHAI.md) (15 mục: sơ đồ, phương án nối, quy chuẩn, số đo Cloudflare, Wi-Fi, WebUI, ESP32-S3); tài liệu đánh lại số 01–12; thêm P52 vào [08](08_QUYET_DINH_THIET_KE.md); 09 thêm mục 3.4; `AI_CODEMAP` sinh lại |
| **Test đường dừng an toàn + tăng tốc (26/11)** | `tests/test_stop_paths.py` 39 bài (mạch giả viết tay); siết 16 bài yếu; `pytest` chạy 6 tiến trình ~30 s (thay vì ~112 s); `machine.py` phủ 94 % |

## 4. Việc tiếp

### 4.1 Đã chốt (không hỏi lại)
| Việc | Quyết định |
|---|---|
| Thuật toán vẽ ảnh | **ĐÓNG BĂNG (22/11/2026)**: 5 kiểu (Đan chéo · Đường dòng · Sóng điều biên · Xoắn ốc · Đường bao) + ô **Chất lượng tối đa** cho 3 kiểu tô + 5 preset ([08](08_QUYET_DINH_THIET_KE.md) P40–P42, tên mới ở [05](05_TAB_TAO_BAN_VE.md)). Chỉ chỉnh hằng số theo bản in (nêu số trước / sau); mở lại khi có người bổ sung |
| Đã thử và bỏ hẳn | Khối (SLIC) · Phác chì AI · viền AI · độ sâu làm hướng nét · lai nét cong + đan chéo ([08](08_QUYET_DINH_THIET_KE.md) P28, P35) |
| Máy | gia tốc **2700**, junction **0,02** (tiếng "khực" hết), servo **5,3 V** ([02](02_PHAN_CUNG_MAY.md)) |
| Bút | UM-100 chính; Sakura ghi 0,5; UB-155 dừng |
| Nút bút | `G90 G0 Z…`, Giữa = Z3 (servo giật do xung firmware, bỏ, [02](02_PHAN_CUNG_MAY.md) F16) |
| PIN | **không bắt buộc** khi mở ra ngoài (chủ dự án chọn 24/11/2026; launcher không chặn). Chưa đặt = ai có địa chỉ cũng là quản lý. **Nên đặt trước khi đưa địa chỉ cho người khác** ([07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 9.6) |
| Kết nối (26–27/11) | Wi-Fi telnet là **thêm** lựa chọn, giữ USB; **không sửa firmware FluidNC**; **ESP32-S3 N16R8 làm cầu nối** + nút dừng cứng nối thẳng MKS ([08](08_QUYET_DINH_THIET_KE.md) P52); **tạm bỏ MiniPC / Pi**; WebUI: chỉ **đổi giao diện, giữ chức năng** (cách A trước, B sau, [07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 12.4) |
| Thứ tự lộ trình | thuật toán ✅ → tách lớp màu ✅ → Tab Beta ✅ lõi → Cloudflare ✅ (laptop) → Wi-Fi telnet (chưa thử mạch) → **ESP32-S3 cầu nối + nút cứng** → cam cố định → cảm biến bút → cam trên bút |

### 4.2 Việc của chủ dự án (cần tay, giấy, mạch thật)
Thứ tự theo ích lợi. Mỗi việc ghi nơi chi tiết.
1. **In giấy** (**L**): bài A1–A9 ([11](11_THU_NGHIEM.md) mục A, đã gợi ý gộp 13 → 12 tờ, theo bút). Gửi ảnh + mẫu mục 8. AI chỉnh hằng số theo số đo. Chặn việc chốt hằng thuật toán.
2. **Thử giao diện trên điện thoại thật** (**S**): thanh tab đáy với vùng an toàn iPhone, bàn phím ảo, ô xám sau khi chạm, nút Hủy tác vụ, Terminal, khối Cảnh báo ([08](08_QUYET_DINH_THIET_KE.md) P51). Khởi động lại phần mềm, tải lại cứng; nếu vẫn lỗi gửi ảnh.
3. **Kiểm mạch qua Wi-Fi** (**S**, chỉ đọc): `$I`, `$WiFi/Mode`, `$Telnet/Enable`, `$Telnet/Port`, `$WiFi/PsMode`, `$System/IP`; đổi `$AP/Password` (ghi xuống mạch = người bấm); nối thử bằng phần mềm **chỉ xem trạng thái** ([07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 11.6, bài C4, C6).
4. **Đặt PIN** trước khi đưa địa chỉ cho ai (`data\pin.txt`, dòng `admin=`; bài C1); cân nhắc Cloudflare Access.
5. ✅ **Đo `do_thoi_gian.py` trên máy chủ** (27/11): máy đang code = máy treo = i5-9400F 6 luồng 15,9 GB; số khớp 22/11 (±6 %), [11](11_THU_NGHIEM.md) mục 9.2. Khi chọn server cloud: RAM đỉnh thêm ≤ 55 MB mỗi lần tạo nét (ảnh thử A5).
6. **Tab Beta**: in thử một trang báo cáo (bảng, khung, tiêu đề 18–20, chữ 14–16, bút bi 0,5 và thử 0,38–0,40); máy mới phải cài `pymupdf` vào Python mà launcher dùng. Sau đó **Soạn font** (kế hoạch [10](10_TAB_BETA_PDF.md) mục 11b, chưa làm).
7. **Mua ESP32-S3 N16R8** và đọc sơ đồ cùng AI (chỉ khi mục 4.3 việc 2 và 3 xong: có số tốc độ qua độ trễ và biết chân trống): xem [07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 13.
8. **Chuẩn bị bản mang đi / máy thứ hai** (**S**): chưa thử trên máy thứ hai: `PYTHONPATH` vào tiến trình con xử lý ảnh, Git "dubious ownership" trên ổ ngoài, máy mượn đủ Python 3.12 x64. Cách làm [07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 10.
9. **Webcam** (**M**, [08](08_QUYET_DINH_THIET_KE.md) P49): cam cố định trên khung trước; cam trên bút để cuối; khi máy chủ ở xa thì chưa chốt ESP32-CAM hay webcam + máy nhỏ ([07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 13.4). Cảm biến (đo dòng INA260, rung ADXL345) tạm hoãn; **không đo nhiệt** (P50).

### 4.3 Việc AI làm được ngay, không cần mạch thật (xin chủ dự án bảo mới làm)
| # | Việc | Cỡ | Kiểm chứng | Cần hỏi trước? |
|---|---|---|---|---|
| 1 | `tools/do_duong_truyen.py`: 500 lần `$G` qua USB / `--host`, in dòng/giây và thời gian đi–về (trung vị / 95 % / lớn nhất); thử với máy giả | S | chạy với `sim`; có test | không |
| 2 | ✅ 27/11 **Mô hình trễ** `tools/mo_phong_gui_lenh.py`: chốt kho ESP ≥ 5000 dòng, gói ~1000, nạp trước ~2000 (0 khựng kể cả 4G giật); gửi từng dòng qua mạng chậm ~50 lần | M | `tests/test_mo_phong_gui_lenh.py` | xong (chưa đụng `JobRunner`) |
| 3 | ✅ 27/11 Đọc sơ đồ MKS: UART phụ = **EXP2 IO23 (TX) / IO19 (RX) / GND**, nút Tạm dừng = **J11 IO34**; nguồn ESP32-S3 = Mini560 5 V riêng ([phiếu P01](../scripts/P01-esp32-s3-cau-noi.md)) | S | bảng chân (chưa đo bằng đồng hồ) | xong |
| 4 | WebUI **cách B** (đổi 27/11): ✅ mã nguồn ở `webui/` (fork nhánh `revamp`), ✅ đóng gói thử được (121 KB). Còn: sửa `www/sub/*.html` + `www/css/*.css` cho khối dễ nhìn như web mình, ẩn spindle / laser / A B C / macro rỗng, **giữ mọi `id`**; xem trước bằng Playwright (không có mạch) | M | ảnh chụp xem trước; kích thước ≤ chỗ trống trên mạch; số `id` và hàm không đổi so với bản gốc | **có**: kiểu giao diện (mẫu `mauchu.css`?), tên tệp thành phẩm ở gốc repo |
| 5 | ✅ 27/11 Dọn 3 điểm thấp của telnet: lọc đủ chuỗi điều khiển telnet (`TelnetFilter`, giữ trạng thái qua các lần đọc), ghi lỗi / quá hạn thì báo mất kết nối **ngay** (một lần), bỏ kiểm baud khi không phải USB | S | `tests/test_telnet_link.py` 23 bài; kiểm đột biến | xong |
| 6 | Mã **ESP32-S3** + kiểu kết nối `esp` ở backend: các gói việc 5–8 trong [phiếu P01](../scripts/P01-esp32-s3-cau-noi.md) | L | mạch giả có trễ trước, mạch thật sau | **có** (cấu trúc mới, đụng an toàn) |

### 4.4 Cần chủ dự án cung cấp
Ảnh và số sau mỗi buổi thử; router mini hoặc 4G cho demo không mạng; máy hiện sóng / logic analyzer nếu có; **ảnh dây điện thật từ nguồn Mean Well tới MKS và nhánh XL4005** (chọn chỗ đặt cảm biến dòng); linh kiện IoT ([08](08_QUYET_DINH_THIET_KE.md) P50): webcam, ESP32 + INA260 + hạ áp 5 V + cầu chì.

## 5. Không làm
Hồ sơ tốc độ (Chữ / Tranh / Đẹp nhất) · gửi dồn lệnh qua USB, tăng baud (với ESP32-S3 thì **kho lệnh nằm ở ESP**, khác chuyện này: P52) · dithering từng điểm ảnh · tối ưu thứ tự theo hàm chi phí · AI tìm nét / tạo ảnh (thử 18/11 và bỏ, P35) · stipple / TSP · WebSocket giữa giao diện và máy chủ (vẫn HTTP + SSE; WebSocket chỉ cho ESP32-S3 ↔ máy chủ, P52) · viết lại tô nét bằng JavaScript · tiếp tục khi mất điện.
