# 10 — Hướng phát triển (ý tưởng chưa xếp lịch)

> Dành cho người đọc và người viết báo cáo (phần "hướng phát triển"). Chưa làm. Mọi thời gian là **ước lượng**, phải đo trên MiniPC thật.
> Ký hiệu: ✅ chủ dự án đã đồng ý ý này · 💡 gợi ý · ⚠ chưa kiểm chứng.
> Việc đã xếp lịch và câu hỏi chờ bạn chọn: [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md). Thư viện / thuật toán ảnh có thể thêm: [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 17.

Nguyên tắc chung: **không sửa firmware FluidNC.** Đóng góp của đề tài nằm ở cách ghép dây chuyền, tối ưu cho phần cứng yếu, phần cứng gắn thêm bên ngoài, và **số đo trước / sau**.

---

## 0. Thuật toán ảnh: đã làm xong (12–14/11/2026)
Nguồn: tài liệu tư vấn AI khác (ý tưởng A–F) đối chiếu với mã và số đo in thật. **Triết lý giữ nguyên: ít lần nhấc bút, không râu / nét vụn, chạy được trên CPU MiniPC, không cần mạng.** Mọi việc thêm vào dây chuyền **có sẵn**, không viết lại.

| Ý tưởng | Kết quả | Chi tiết |
|---|---|---|
| Nối nét gần thay vì nhấc bút | ✅ ảnh A5: −55–82 % lần nhấc, −30–50 % thời gian | 09 P18 |
| Ước tính thời gian có gia tốc | ✅ khớp tờ 7.6 (110,9 / 111 s) | 09 P19 |
| Đường cong tông (từ tờ in) | ✅ gạch chéo + xoắn ốc, 75 % | 09 P21 · 06 mục 8.12 |
| XDoG → FDoG cho viền | ✅ viền mắt / mũi rõ, nét liền | 09 P26 |
| Flow field (nét theo dáng) | ✅ kiểu **Theo dáng ảnh**; sửa cửa sổ tròn 14/11 | 09 P28, P30 · 06 mục 8.10 |
| Buffer + cung G2/G3 | ✅ chờ 0, G2/G3 (sai lệch ≤ 0,02 mm); **không** gửi dồn / tăng baud | 09 C10, D10–D12 |
| Đan 3 hướng, lai đan chéo + theo dáng | ✖ thử rồi ẩn | 09 P22, P23, P28 |

**Không làm** (đi ngược triết lý, hoặc chưa cần):
| Ý tưởng | Vì sao bỏ |
|---|---|
| Dithering 2D từng điểm ảnh (Floyd–Steinberg, Atkinson, blue-noise) | quyết định theo từng điểm → đốm, đoạn ngắn → nhiều nhấc bút, nét vụn. "Chuyển mức mềm" so le theo cả dòng gạch nên nét vẫn liền |
| Tối ưu theo hàm chi phí, giữ thứ tự nhạt → đậm, 30–180 s | phạt nhấc bút đã có (nối nét gần); vẽ từng mức nhạt → đậm in thật thấy lâu hơn (đã tắt mặc định); quá lâu cho MiniPC |
| Viết lại dây chuyền thành "PipelineContext" chung | mất phần kiểm tham số của `spec.py`, phải viết lại ~3600 dòng |
| AI dò cạnh / GPU / API ngoài | MiniPC i5-3210M không CUDA; demo phải offline. Xem lại khi có máy mạnh hơn, luôn giữ đường CPU và tắt được |

**Còn mở (ý nhỏ, chỉ làm khi in thấy cần):** tờ tông riêng cho Theo dáng ảnh và UB-155 · nối đầu các đường kề nhau ở Theo dáng (giảm mẩu vụn) · tự đo tờ tông từ ảnh chụp (tìm 3 ô đen, nắn phối cảnh) nếu phải hiệu chỉnh nhiều bút / giấy.

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
| Bút servo | đo thời gian nhấc / hạ thật bằng máy hiện sóng / logic analyzer; thử servo nhanh hơn | `FluidNC RcServo` |
| Driver | TMC2209 StealthChop (êm) và SpreadCycle (khỏe ở tốc độ cao); nguồn 24 V | `TMC2209 standalone SpreadCycle` |
| Camera tự căn giấy | mã ArUco ở góc bàn → tự tìm vị trí giấy, tự đặt Zero; chụp tờ đã vẽ → so với xem trước bằng SSIM + OCR | `OpenCV ArUco homography` |
| Thông báo | MQTT lên bảng theo dõi, bot Telegram báo "vẽ xong / lỗi" | `Telegram bot sendMessage` |
| So đường truyền | độ trễ USB so với Wi-Fi của FluidNC; ghi lý do chọn USB (Wi-Fi vượt qua khóa của phần mềm) | `FluidNC telnet websocket` |

---

## 4. Tính năng phần mềm nhỏ
Thứ tự làm đã chốt 17/11/2026 ở [11](11_VIEC_CAN_LAM.md) mục 4.2: thuật toán → nối mạng → nút cứng + cảm biến → ESP32 cuối. Đã làm: khoanh vùng chủ thể, báo vẽ xong / lỗi. **Không làm:** mã QR địa chỉ, tiếp tục khi mất điện. Còn lại:
- 💡 Vệt bút theo dòng G-code cho cả macro / tiếp tục tác vụ (hiện chỉ cho tệp đang chạy).
- 💡 `.devcontainer/` cho GitHub Codespaces.
- 💡 2-opt trong Web Worker, chỉ khi đo trên MiniPC thấy sắp xếp nét lâu.

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
| 10 | 💡 **Chữ trong SVG: giữ `<text>`, thêm lớp "… hatched" / "… contour"** thay vì đổi hẳn thành path | Họ không phá tệp gốc, chữ vẫn sửa được; đúng hướng mục 1.1–1.2 ở trên (tab PDF, bộ chữ) | để dành cho tab Beta PDF | M |
| 11 | 💡 **Tờ mẫu riêng cho từng kiểu nét** (mọi chữ, số, dấu ở 2 cỡ) | Mình có Tờ thử (thang tông, nhấc bút) nhưng chưa có tờ mẫu theo kiểu nét; họ sinh tờ A3 cho từng kiểu tô | `testsheets.py` | S |

Nguồn từng việc: **1–5** SVGroom · **6–7** Plotterosaurus · **8** vpyposaurus · **9–11** PlotHatcher.

**Đã có rồi, đừng làm lại** (đối chiếu mã 17/11/2026): vẽ như bút thật (đầu tròn, bề rộng bút — `views/drawing/canvas.js:193`) · thời gian có gia tốc, chậm ở góc, nét ngắn, thời gian nhấc / hạ bút (`gcode.py:175-190`) · mỗi lớp tính như một lần chạy riêng (`service.py:77`) · tên lớp + màu bút lấy từ lớp Inkscape (`svg_in.py:69`) · khổ giấy, lề, xoay, canh giữa (`lib/paper.js`) · cảnh báo đã có: `dropped_strokes`, `feed_above_rapid`, `no_page_size` · tối ưu SVG bằng vpype, có số trước / sau (`optimize.py`); riêng ảnh thì chạy ở tiến trình con, ưu tiên thấp (`isolated.py`) · bản xem trước do máy chủ tự dựng từ nét (`/drafts/{id}/preview.svg`), không nhúng SVG gốc vào trang → cùng tinh thần "không cho tệp lạ chạy mã" của vpyposaurus · ảnh khách tự xóa sau 5 ngày, ≤ 6 ảnh / giờ (≈ "giữ 30 tệp gần nhất" của họ) · báo vẽ xong bằng âm báo + tiêu đề tab (≈ webhook `job_complete`) · vùng máy: mình **chặn trước** khi vẽ (`paper_out_of_area`, `box_out_of_paper`), họ chỉ cảnh báo rồi cắt bớt — mình chặt hơn, giữ.

**Không lấy:** thư viện ảnh kiểu Lightroom (sao, cờ, nhãn màu, tag, lọc, tự sang ảnh sau khi chấm) — bản thảo của mình ít, thêm vào chỉ rối; catalog `.svgroom`, liên kết thư mục, tìm tệp bị mất, phím tắt, Copy to Folder — đặc thù macOS, mình không có nhu cầu; 6 tab dây chuyền của vpype Studio (Layers / Occult / Operations / …) — mình có dây chuyền riêng, dựng lại chỉ để giống họ; plugin `vpype-occult` (bỏ nét bị hình khác che) — chỉ có nghĩa với tranh nhiều lớp chồng; `disable_motors_on_complete`, `delete_on_complete`, webhook — chưa cần.

**Để dành cho sau (không phải việc nhỏ):** Plotterosaurus có `/api/v1/*` riêng cho máy khác gọi, xác thực bằng khóa `X-API-Key` tách khỏi giao diện web — đúng thứ sẽ cần khi làm ESP32 (mục 3.2) hoặc cho máy khác điều khiển; hiện mình chưa có, và **thêm khóa API là việc bảo mật phải hỏi trước**. Còn: nút cứng Tạm dừng / Chạy tiếp họ đã làm bằng nút thật trên máy — mình đã có trong danh sách mục 3.1.

---

## 5. Lời khuyên đã kiểm là sai (từ một tư vấn AI khác, 02/11/2026): đừng làm theo
- "`pdftocairo -svg` giữ chữ trong thẻ `<text>`": không có tài liệu xác nhận; có người báo SVG ra không thấy chữ.
- "`vpype-text` tự ép font Hershey tiếng Việt": plugin ngừng phát triển; Hershey không có dấu tiếng Việt.
- "`findContours` trên nét 1 điểm ảnh": ra hai đường bao.
- "`potrace` vector hóa nét mượt": ra nét đôi.
- "`docx2pdf`": cần Word cài sẵn; MiniPC Ubuntu không có.
