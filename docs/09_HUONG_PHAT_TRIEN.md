# 09 — Hướng phát triển (ý tưởng chưa xếp lịch)

> Dành cho người đọc và người viết báo cáo (phần "hướng phát triển"). Chưa làm. Mọi thời gian là **ước lượng**, phải đo trên máy chủ thật.
> Ký hiệu: ✅ chủ dự án đã đồng ý ý này · 💡 gợi ý · ⚠ chưa kiểm chứng.
> Việc đã xếp lịch và câu hỏi chờ bạn chọn: [12_VIEC_CAN_LAM.md](12_VIEC_CAN_LAM.md). Thư viện / thuật toán ảnh có thể thêm: [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 17.

Nguyên tắc chung: **không sửa firmware FluidNC.** Đóng góp của đề tài nằm ở cách ghép dây chuyền, tối ưu cho phần cứng yếu, phần cứng gắn thêm bên ngoài, và **số đo trước / sau**.

---

## 0. Thuật toán ảnh: đã xong và đóng băng
Các ý tưởng tư vấn (nối nét gần, ước tính có gia tốc, đường cong tông, FDoG, flow field, G2/G3, tách mực) **đã làm**; lý do và số đo ở [08](08_QUYET_DINH_THIET_KE.md) (P18–P47) và [06](06_THUAT_TOAN_XU_LY_ANH.md). Triết lý giữ nguyên: **ít nhấc bút, không nét vụn, chạy được trên CPU MiniPC, không cần mạng.**

**Không làm:** dithering 2D từng điểm ảnh (đốm, nhiều nhấc bút; "chuyển mức mềm" đã so le theo dòng) · tối ưu theo hàm chi phí 30–180 s (quá lâu cho máy chủ yếu) · viết lại dây chuyền thành "PipelineContext" chung (mất phần kiểm tham số của `spec.py`) · AI / GPU / API ngoài (MiniPC không CUDA, demo offline; đã thử và bỏ, P35).

**Còn mở (chỉ làm khi in thấy cần):** tờ tông riêng cho Theo dáng ảnh và UB-155 · nối đầu các đường kề nhau ở Theo dáng.

---

## 1. Tính năng vẽ mới: chỉ thêm "nguồn nét"
Phần "nét → G-code" dùng chung; mỗi tính năng mới chỉ là một nguồn nét đổ vào đó.

| Nguồn nét | Trạng thái |
|---|---|
| **PDF từ Word** (tab Beta) | ✅ lõi xong 22/11/2026: đọc ký tự thật rồi viết lại bằng font nét đơn, dấu tiếng Việt tự ghép ([10](10_TAB_BETA_PDF.md)). Cách "kết xuất ảnh rồi skeleton" đã thử và không chọn (chữ 14 pt đứt nét, mất dấu) |
| **Soạn font riêng** (chữ tay của chủ dự án) | 📋 kế hoạch đã chốt, chưa làm: xuất font vpype → sửa bằng chuột trong tab Beta → nạp thẳng; sau đó bút cảm ứng và biến thể mỗi chữ ([10](10_TAB_BETA_PDF.md) mục 11b). Chỉ dùng chữ của chính mình hoặc người đã đồng ý |
| **Nhận dạng chữ (OCR)** cho PDF quét và chữ trong hình | 💡 ([10](10_TAB_BETA_PDF.md) mục 1) |
| **Câu lệnh → AI tạo ảnh** (làm cuối) | 💡 không chạy tại chỗ (máy chủ không GPU); gọi dịch vụ ngoài thì cần Internet, tốn phí, phải giới hạn số lần |

Giới hạn bảo vệ đã có: ảnh ≤ 40 MB, SVG ≤ 20 MB, PDF ≤ 40 MB / 500 trang, ảnh gốc ≤ 60 triệu điểm, ảnh làm việc 400–4000 điểm cạnh dài, mỗi lần xử lý ≤ 600 s, RAM tiến trình ≤ 4 GB (Linux), tổng điểm nét ≤ 2 triệu, 2-opt ≤ 15 000 nét, G-code ≤ 200 000 dòng.

---

## 2. Mở cho nhiều người (sau bản khách + quản lý)
| Ý | Ghi chú |
|---|---|
| Tài khoản "người dùng" ✅ | chỉ tên + mật khẩu, không email; mật khẩu băm bằng `hashlib.scrypt` 💡; form đăng ký không bao giờ tạo quản lý |
| Thư mục riêng theo tài khoản ✅ | người này không xem được của người kia; giữ 3 ngày; mọi route đọc tệp phải kiểm chủ |
| Hàng chờ tạo nét ✅ | **đã đồng ý, làm một phần**: nút "Tạo nét" đã tách nạp ảnh khỏi tạo nét; **chưa làm**: hàng chờ theo thứ tự đến (hiện việc mới **hủy** việc đang chờ, `drawing/tasks.py:68-70`), hủy theo người (`tasks.py:106-107` không kiểm chủ), `idle.py` đếm việc đang chờ (`backend/app/idle.py` chỉ tự tắt server khi hết trang mở; đang chạy thì chỉ xét việc G-code) |
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
| **Đo dòng điện / điện năng** (chọn 24/11/2026) | INA260 (hoặc INA226 + điện trở đo) **mắc nối tiếp** vào dây + 12 V giữa nguồn Mean Well và MKS (mắc song song chỉ đo được điện áp); ESP32 đọc qua I2C rồi gửi lên server → Wh mỗi bản vẽ, công suất cùng biểu đồ tốc độ. Dự phòng dễ hơn: ổ cắm đo điện thông minh. Chi tiết ở [08](08_QUYET_DINH_THIET_KE.md) P50 | `INA260 ESP32` |
| ~~Nhiệt độ~~ | **Bỏ** (24/11/2026): động cơ chạy tải nhẹ, số đo không có ý nghĩa | |
| Camera xem trực tiếp | Dự định 24/11: webcam USB cắm máy chủ thay vì ESP32-CAM ([08](08_QUYET_DINH_THIET_KE.md) P49). **27/11:** nếu máy chủ ở xa máy vẽ (mục 3.4) thì webcam USB không cắm được vào máy chủ; chưa chốt giữa ESP32-CAM (rẻ, chỉ để xem, ảnh mờ, cần nguồn riêng) và webcam + máy nhỏ cạnh máy vẽ | |
| Giao tiếp | MQTT (Mosquitto chạy trên máy chủ, không cần Internet) hoặc HTTP | `paho-mqtt`, `PubSubClient` |

ESP32 dùng hạ áp 5 V riêng (servo giật dòng làm ESP32 khởi động lại).

### 3.3 Hướng nghiên cứu khác
| Hướng | Làm gì | Từ khóa |
|---|---|---|
| Bút servo | đo thời gian nhấc / hạ thật bằng máy hiện sóng / logic analyzer; thử servo nhanh hơn | `FluidNC RcServo` |
| Driver | TMC2209 StealthChop (êm) và SpreadCycle (khỏe ở tốc độ cao); nguồn 24 V | `TMC2209 standalone SpreadCycle` |
| Camera tự căn giấy | mã ArUco ở góc bàn → tự tìm vị trí giấy, tự đặt Zero; chụp tờ đã vẽ → so với xem trước bằng SSIM + OCR | `OpenCV ArUco homography` |
| Thông báo | MQTT lên bảng theo dõi, bot Telegram báo "vẽ xong / lỗi" | `Telegram bot sendMessage` |
| So đường truyền | độ trễ USB so với Wi-Fi telnet (mã đã có, chưa đo; tool `do_duong_truyen.py` chưa viết: [07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 11.6). Phần mềm điều khiển qua Wi-Fi vẫn chịu PIN và khóa; chỉ **WebUI của FluidNC** vượt khóa | `FluidNC telnet websocket` |

### 3.4 Nối mạng và IoT từ xa (chốt hướng 27/11/2026, chưa làm; chi tiết [07](07_MANG_KET_NOI_TRIEN_KHAI.md) mục 11–13)
| Hướng | Làm gì | Từ khóa |
|---|---|---|
| **ESP32-S3 làm cầu nối** (✅ chủ dự án chọn, [08](08_QUYET_DINH_THIET_KE.md) P52) | Máy chủ ở PC nhà hoặc server cloud; quanh máy vẽ chỉ một ESP32-S3 N16R8 tự gọi ra tên miền (WebSocket) và nối dây UART vào cổng phụ của MKS (`uart_channel` trong `config.yaml`). ESP giữ kho lệnh, tự gửi từng dòng tại chỗ (số đo: qua Cloudflare ~0,13 s mỗi lượt, có lần 1,16 s). Giữ USB, telnet, điểm phát dự phòng | `FluidNC uart_channel`, `ESP32 WebSocket client TLS` |
| Nút dừng cứng | `feed_hold_pin` (tạm dừng), `cycle_start_pin` (chạy tiếp), tùy chọn `estop_pin` (dừng gấp, báo động nghiêm trọng) nối thẳng MKS; ESP tự gửi `!` khi mất kết nối với máy chủ | `FluidNC control pins` |
| Đổi giao diện WebUI của FluidNC, giữ chức năng | Cách A: chèn CSS vào `index.html.gz` (màu, nút to, hạn chế sắp lại khối); cách B: build lại từ mã nguồn ESP3D-WEBUI để sắp khối giống tab Điều khiển. Hoặc trang cứu hộ riêng ≤ 30 KB. Chủ dự án tự tải lên mạch | `ESP3D-WEBUI`, `index.html.gz` |
| Máy chủ trên cloud | Backend chưa từng chạy Linux; đo RAM đỉnh bằng `tools/do_thoi_gian.py` trước khi chọn gói | |
| Máy nhỏ cạnh máy vẽ (Pi, MiniPC) | ⏸ tạm bỏ 26/11: chủ dự án chỉ cần một con gửi lệnh; cân nhắc lại nếu cần webcam USB hoặc xử lý ảnh tại chỗ | |

---

## 4. Tính năng phần mềm nhỏ
Thứ tự làm ở [12](12_VIEC_CAN_LAM.md) mục 4.2. Còn lại:
- 💡 Vệt bút theo dòng G-code cho cả macro / tiếp tục tác vụ (hiện chỉ cho tệp đang chạy).
- 💡 `.devcontainer/` cho GitHub Codespaces.
- 💡 2-opt trong Web Worker, chỉ khi đo trên máy chủ thấy sắp xếp nét lâu.

### 4.1 Tham khảo từ 4 repo của Tonino-RB (17/11/2026, chưa làm)

Nguồn: 4 repo cùng một tác giả, đều làm về máy vẽ bút — `SVGroom` (app macOS duyệt và cắt chọn tệp SVG), `Plotterosaurus` (máy chủ vẽ tự dựng cho AxiDraw, chạy trên Raspberry Pi, giao diện web), `PlotHatcher` (biến chữ trong SVG thành nét vẽ được), `vpyposaurus` (giao diện web cho vpype). Giấy phép: SVGroom **PolyForm Noncommercial** (học được, bán thì không) · Plotterosaurus và PlotHatcher **MIT** (dùng lại được, phải giữ bản quyền) · vpyposaurus **chưa thấy tệp giấy phép** (muốn dùng mã phải hỏi tác giả). Cả bốn viết bằng Swift / Python + vpype, không phải JS thuần → **lấy ý tưởng, không chép mã**; riêng vpyposaurus cùng kiểu kiến trúc với mình (FastAPI + HTML/CSS/JS không phụ thuộc) nên đọc cách họ tổ chức được.

| # | Việc | Vì sao đáng làm | Chạm vào | Cỡ |
|---|---|---|---|---|
| 1 | 💡 Cảnh báo khi SVG có **chữ** (`<text`), **ảnh nhúng** (`<image`) hoặc nét **ngoài khổ giấy** | Hiện chữ biến mất im lặng (vpype chỉ đọc đường nét), chỉ báo khi SVG không còn nét nào | `services/drawing/svg_in.py` + khóa `drawing.warning.text_not_path`, `image_ignored`, `off_page_content` (vi + en) | S |
| 2 | 💡 Hiện **"ước tính / thật"** cạnh nhau trong nhật ký chạy | `joblog.py` đã lưu `elapsed_s` (thật) và `est_seconds` (ước) mà chưa ai so → có số để chỉnh `EST_ACCEL_MM_S2`, `EST_LINES_PER_S`. Cách họ làm: đối chiếu mô hình với phần mềm AxiDraw, sai 0,5–1 % | `services/joblog.py` + danh sách nhật ký chạy | S |
| 3 | 💡 **So sánh 2 bản thảo cạnh nhau** cùng tỉ lệ + bảng số (thời gian, quãng bút, số lần nhấc, số nét) | Đúng vòng A/B đang làm (tông, 0 vs 1 lượt, UB-155 vs Sakura); hiện phải in 2 tờ rồi mắt so | `views/drafts.js` + khối xem trước | M |
| 4 | 💡 **Ẩn / hiện từng lớp màu**, thời gian tính lại theo | Trả lời ngay "bỏ màu đỏ thì nhanh hơn bao nhiêu", không cần in | `views/drawing/*`, `spec.py` (bỏ lớp trước khi dựng G-code) | M |
| 5 | 💡 Thêm khổ giấy A3, B5, Legal, Tabloid vào ô Khổ giấy | Rẻ, chỉ thêm hằng số | `lib/paper.js`, `spec.py`, `index.html` | S |
| 6 | 💡 **Nhắc đổi bút giữa các lớp màu, và bỏ nhắc khi lớp kế dùng đúng bút đó** (so màu + bề rộng nét) | `05` mục ghi "vẽ xong tệp nào thì đổi bút rồi nạp tệp kế" — làm tay nên dễ nạp tệp kế khi chưa đổi bút. Họ có `pause_between_layers` + `skip_same_pen_pause` | `views/drafts.js` (Nạp theo lớp), `stores/jobstore.js` | S |
| 7 | 💡 **Chia lớp theo "bút" = màu + bề rộng nét** cho SVG không có layer (Illustrator / Figma) | Họ cho chọn `layer_mode`: layer Inkscape · nhóm gốc · theo bút. Mình chỉ theo layer Inkscape (`svg_in.py:58`) | `svg_in.py` + `spec.py` | M |
| 8 | 💡 **"Cái gì đã đổi" từng bước tối ưu SVG** (mỗi bước: số nét, quãng nhấc trước / sau) | Mình chỉ có tổng trước / sau (`svg_in.py:135`); họ chạy vpype từng bước và báo từng bước một | `optimize.py` (chạy `execute` theo từng bước) + khối xem trước | S |
| 9 | 💡 **Tô kín mảng đặc của SVG bằng gạch** (giữ đường bao, tô phần trong) | SVG có hình tô đặc hiện chỉ ra đường bao rỗng ⚠ (vpype đọc hình học, bỏ phần tô — **chưa thử** với tệp tô đặc). Họ tô bằng 6 kiểu: xoắn ốc, đồng tâm, đường thẳng, đan, zigzag, theo dáng chữ | `styles.py` (dùng lại kiểu tô) + `svg_in.py` (phải biết hình kín) | M–L |
| 10 | 💡 **Chữ trong SVG: giữ `<text>`, thêm lớp "… hatched" / "… contour"** thay vì đổi hẳn thành path | Họ không phá tệp gốc, chữ vẫn sửa được; có thể dùng lại bộ xếp chữ của tab Beta | `svg_in.py` + `beta_pdf/text.py` | M |
| 11 | 💡 **Tờ mẫu riêng cho từng kiểu nét** (mọi chữ, số, dấu ở 2 cỡ) | Mình có Tờ thử (thang tông, nhấc bút) nhưng chưa có tờ mẫu theo kiểu nét; họ sinh tờ A3 cho từng kiểu tô | `testsheets.py` | S |

Nguồn từng việc: **1–5** SVGroom · **6–7** Plotterosaurus · **8** vpyposaurus · **9–11** PlotHatcher.

**Đã có rồi, đừng làm lại** (đối chiếu mã 17/11/2026): vẽ như bút thật trên khung xem trước · thời gian có gia tốc, góc, nhấc / hạ bút · mỗi lớp tính như một lần chạy · tên lớp + màu từ lớp Inkscape · khổ giấy, lề, xoay, canh giữa · tối ưu SVG có số trước / sau · xem trước dựng từ nét (không nhúng SVG gốc) · ảnh khách tự xóa · báo vẽ xong · chặn trước khi vẽ ra ngoài vùng máy (họ chỉ cảnh báo rồi cắt).

**Không lấy:** thư viện ảnh kiểu Lightroom, catalog / phím tắt đặc thù macOS, 6 tab dây chuyền của vpype Studio, plugin `vpype-occult`, webhook, tự tắt động cơ / xóa tệp khi xong.

**Để dành:** API riêng `/api/v1/*` cho máy khác gọi, xác thực bằng khóa `X-API-Key` (sẽ cần khi làm ESP32, mục 3.2); **thêm khóa API là việc bảo mật phải hỏi trước**.

---

## 5. Lời khuyên đã kiểm là sai (từ một tư vấn AI khác, 02/11/2026): đừng làm theo
- "`pdftocairo -svg` giữ chữ trong thẻ `<text>`": không có tài liệu xác nhận; có người báo SVG ra không thấy chữ.
- "`vpype-text` tự ép font Hershey tiếng Việt": plugin ngừng phát triển; Hershey không có dấu tiếng Việt (tab Beta tự ghép dấu).
- "`findContours` trên nét 1 điểm ảnh": ra hai đường bao.
- "`potrace` vector hóa nét mượt": ra nét đôi.
- "`docx2pdf`": cần Word cài sẵn; máy Ubuntu không có.
