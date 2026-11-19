# 11 — Tình trạng và việc cần làm

> Sổ làm việc, cập nhật 17/11/2026. **Một nơi duy nhất** cho: đã xong · cần thử · làm tiếp (theo thứ tự bạn chốt).
> Cách thử từng bài: [07](07_THU_NGHIEM.md). Lý do từng quyết định: [09](09_QUYET_DINH_THIET_KE.md). Ý tưởng để dành: [10](10_HUONG_PHAT_TRIEN.md).
> Cỡ việc: **S** vài giờ · **M** nửa đến một ngày · **L** nhiều ngày.

## 1. Tình trạng chung

| Khối | Tính năng | Đã kiểm ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95 % | ~70 % |
| Tạo bản vẽ (ảnh, SVG, bản thảo, hàng đợi) | ~95 % | ~60 % (thuật toán đã xem bản thảo, chưa in hết) |
| Cài đặt, cấu hình máy | ~90 % | ~70 % |
| Phân quyền, bản mang đi | ~85 % | ~60 % |

Test tự động: máy chủ **564**, giao diện **58** (đều qua 18/11/2026). Còn thiếu chủ yếu: **in thật** các kiểu mới và **thử trên MiniPC**.

## 2. Bản đồ việc

```
 ĐÃ XONG (mục 3)                 LÀM TIẾP, THEO THỨ TỰ (mục 4.2)                              CUỐI
 ───────────────                 ───────────────────────────────                              ─────
 máy + G-code chuẩn ──┐
 thuật toán vẽ ổn ────┼─► 1. THUẬT TOÁN: in thử A → chốt hằng ─► (tab Beta PDF?) ─┐
 vùng chủ thể, âm báo ┘                                                              │
                                  2. NỐI MẠNG: MiniPC + Docker + Cloudflare ◄───────┘
 an toàn / phân quyền ─────────► 3. NÚT CỨNG + CẢM BIẾN BÚT (YAML + dây) ───────────► 4. ESP32 (IoT)
```

## 3. Đã xong (chỉ từ khóa và hằng đã chốt; lý do ở 09)

| Nhóm | Đã chốt |
|---|---|
| **Máy và G-code** | vẽ / di chuyển **8000**, gia tốc **3000**, junction **0,03** (máy đang chạy **2800 / 0,01** từ 18/11/2026, [07](07_THU_NGHIEM.md) B4 chưa kết luận); Z nhấc **3**, hạ **2000**, chờ **0**; nút bút gửi `G90 G0 Z…`: Lên **Z5** · Giữa **Z3** · Xuống **Z0**; nét cong **G2/G3** (sai lệch ≤ 0,02 mm); giữ **115200 baud**, gửi từng dòng chờ `ok` (~125 dòng/giây); ước tính thời gian: +0,025 s mỗi lần nhấc; `$10=3` cho biểu đồ hàng đợi |
| **Máy đã thử xong** (17/11) | mất bước ở 7000–10000 ổn · tốc độ tối đa **10000** · TMC2209 đã bật **SpreadCycle** (DIP3, giữ) · Home, Z, đèn X / Y đúng · **Tiếp tục từ điểm dừng** đúng · Biểu đồ có đường hàng đợi · tab Điều khiển mượt hơn (Tạo nét còn chậm là do laptop) |
| **Máy đã thử xong** (18/11) | bản vẽ thật có **G2/G3** chạy tốt · tab Điều khiển mượt · servo giật khi bấm nút bút liên tục (xung, firmware; thôi, ghi 02 F16) |
| **Bút, giấy** | ô "Bút vẽ" = **nét đo trên giấy**: UB-155 **0,38** · UM-100 **0,40** · Sakura **0,50** · bút bi 0,5; `LINE_WIDTH_RATIO` **1,0**; giấy Ivory 250 g/m² mặt bóng |
| **An toàn** | máy mặc định chỉ đọc; khóa chuyển động tự khóa sau 15 phút; Home tự nâng bút; hủy 3 chế độ; tiếp tục từ điểm dừng (lùi 64 dòng); bỏ bước Xem trước bắt buộc (`REQUIRE_PREVIEW_CONFIRM`); PIN quản lý đổi được trên giao diện |
| **Phân quyền, khách** | khách xem + **Gửi ảnh** (tự xóa 5 ngày, ≤ 6 ảnh / giờ); quản lý mở ảnh khách → Tạo nét; SSE cho trạng thái |
| **Tạo bản vẽ** | nạp ảnh → cắt / chỉnh tông → **Tạo nét**; **vùng chủ thể** (elip / chữ nhật, ngoài vùng giữ 50 % độ đậm, mép mờ 8 %); SVG; bản thảo + hàng đợi; 2–4 màu; Tờ thử (Thang tông, nhấc bút, 7.2, 7.5); Biểu đồ số liệu chạy máy (tốc độ, hàng đợi, nhấc bút) |
| **Kiểu nét (7)** | **Gạch chéo** (mặc định) · **Đan chéo siêu chi tiết** · **Theo dáng ảnh** · **Theo dáng siêu chi tiết** · **Sóng biến thiên** · **Xoắn ốc** · **Nét viền**; tờ thử vẫn chạy kiểu ẩn (zigzag, sóng thường, đan 3 hướng) |
| **Hằng kiểu nét** | độ phủ tối đa **0,9**; trắng hẳn dưới **0,2** (sóng: **0,10**); bỏ mẩu gạch < **5 mm** (19/11/2026; trước 6 mm), dải hẹp < **1,5 ×** khoảng cách nét; đường cong tông **75 %**; sóng: khoảng cách **4 ×** nét, bước sóng **2 ×**, phủ đều bật ở Chân dung; theo dáng: `FLOW_TEST_RATIO` **0,7**, cửa sổ tròn, phủ tối đa **0,85**, khoảng cách lớn nhất **4,5 ×** nét; viền: **FDoG** dọc nét 4 mm, làm mượt **0,8 mm**, nối khe **3 mm**, bỏ nét < **6 mm** (19/11/2026; trước 1,5 mm / 8 mm) |
| **5 preset** | **Chân dung** = sóng biến thiên, góc 135°, không viền, mức đen 20, tương phản 1,3, phủ đều · **Ảnh 2D** = gạch chéo 5 mức + lớp viền + khử nhiễu · **Phong cảnh** = sóng, góc 30°, tương phản 1,4, mức đen 15, làm nét 1,5, không CLAHE, không viền · **Schematic** = viền, đen 60 / trắng 200 · **Siêu chi tiết** (19/11/2026) = đan chéo bỏ lọc râu, 8 mức, cách nét 0,9 × bút, sửa sai 2 lượt |
| **Báo xong / lỗi** | âm báo WebAudio (xong: 3 nốt lên; lỗi: nốt trầm lặp; hủy: im) + tiêu đề tab nhấp nháy khi tab ẩn; công tắc ở Cài đặt → Hoạt động; không cần Internet |
| **Sửa sai tông** (17/11) | vòng phản hồi `refine.py`: tô → dựng mực → so → chỉnh mục tiêu → tô lại; mặc định **1 lượt**, gạch chéo / sóng / xoắn ốc; sai số −40…−58 %, mực và thời gian +4…8 % ([06](06_THUAT_TOAN_XU_LY_ANH.md) 8.13, 09 P34) |
| **Giao diện** (17/11) | màu nhấn **vàng an toàn** `#ffd400` (nền sáng `#8a6d00`) thay cyan, ở `tokens.css`; hai khung vẽ (Tạo bản vẽ và xem trước ở Điều khiển) là **giấy ngà + nét đen** như bản in ở cả hai giao diện (khung giấy / lề vàng đậm `--paper-guide`); nhóm Tối ưu nét có nút **Về mặc định** và ô bị xóa trống tự trả về mặc định; dòng G-code ở tab Tạo bản vẽ ghi cả **số cung G2/G3** |
| **Dọn mã** (17/11) | xóa kiểu lai `crosshatch_flow`, `HYB_*`, `edge_band`, `ink_cover`, hàng rào viền; `ink_sim` ra đúng số cũ cho mọi kiểu đang bật |
| **Triển khai** | bản mang đi Windows + `Cap nhat.bat`; demo không cần Internet (giao diện không tải gì từ ngoài) |
| **Tờ tông, bớt râu** (19/11) | `HATCH_MIN_RUN_MM` 6 → **5** mm (4 mm làm hỏng bài test mức mềm: 24,2 % < 25 %); tờ thang tông mốc 4 → **10** mm, chữ F nét 1,5 → **6** mm (`calibration.TONE_MARK`, `loadToneRamp`); test khoá `test_tone_sheet_marks_and_f_survive_the_hatch_filter` |
| **Siêu chi tiết** (19/11) | kiểu `crosshatch_detail` (bỏ hết lọc bớt râu: 0,5 mm / không mở mặt nạ / trắng 0,02) + preset: 8 mức, cách nét 0,9 × bút, sửa sai 2 lượt, không đơn giản hoá; `levels` mở 3–8; tạo nét 30 phút riêng kiểu (`DETAIL_TIMEOUT_S`) |
| **Flow siêu chi tiết + viền liền** (19/11) | kiểu `flow_detail` (`FLOW_DETAIL`: bước 0,25 · sep 1,05–3,0 · phủ 0,95 · trắng 0,02 · test 0,55 · min len 0,6 · dài ≤ 80 mm); Nét viền: `GAP_MM` 1,5 → **3,0**, `OUTLINE_MIN_LEN_MM` 8 → **6**; test `test_flow_detail_is_denser_and_restores_the_flow_constants` |

## 4. Việc tiếp


### 4.1 Đã chốt 17/11/2026 (bạn trả lời, không hỏi lại)
| Câu | Quyết định |
|---|---|
| Dọn mã chết | ✅ đã xóa (giữ nguyên mọi kiểu đang bật) |
| Chưa đặt PIN | **để nguyên** (ai vào cũng là quản lý; chỉ khi mở ra ngoài mới bắt buộc đặt PIN) |
| Thứ tự | **thuật toán → nối mạng (Cloudflare) → nút cứng + cảm biến bút → ESP32 cuối cùng** |
| Khoanh vùng chủ thể | ✅ đã làm: ngoài vùng gạch **nhạt đi** (09 P31) |
| Bài thử A, B (17/11) | Chân dung bỏ (tự chỉnh khi xem bản nháp); Theo dáng ảnh **chờ ảnh thật**, làm cuối; các bài máy đã đạt dồn về mục 3; mất điện rồi chạy tiếp: **không cần, ghi lại sau nếu muốn** |
| Junction | **0,03** (nhẹ máy; bút xịn, giấy mượt ít đọng mực) — máy đang chạy 0,01 từ 18/11/2026, [07](07_THU_NGHIEM.md) B4 chưa kết luận |
| Nút bút | gửi `G90 G0 Z…` thay `$J=`, Giữa = **Z3** (servo giật do xung firmware, chốt 18/11, [02](02_PHAN_CUNG_MAY.md) F16) |
| Báo "vẽ xong / lỗi" | ✅ đã làm: âm báo + tiêu đề tab (09 P32) |
| Mã QR địa chỉ | **không làm** |
| Tiếp tục khi mất điện | **chưa cần**, ghi lại sau nếu muốn |
| **Thuật toán vẽ ảnh (18/11, cập nhật 19/11)** | Giữ vững 5 kiểu vẽ gốc + bổ sung 2 biến thể chi tiết cao: `crosshatch_detail` và `flow_detail` ([09](09_QUYET_DINH_THIET_KE.md) P38, P39); nâng cấp Nét viền (nối khe 3 mm, bỏ nét < 6 mm). **Không thêm kiểu vẽ hay AI mới**; chỉ chỉnh hằng số theo kết quả in giấy (nêu số trước / sau). Mở lại khi có người khác bổ sung |
| Preset (18/11, cập nhật 19/11) | **Chân dung** = sóng biến thiên, 1 lượt sửa sai, không viền · **Phong cảnh** = sóng, góc 30°, tương phản 1,4, mức đen 15, làm nét 1,5, không CLAHE, không viền · **Ảnh 2D** = gạch chéo + viền FDoG + khử nhiễu · **Schematic** = viền · **Siêu chi tiết** = đan chéo bỏ lọc râu, 8 mức, sửa sai 2 lượt |
| Đã thử và bỏ hẳn (18/11) | kiểu Khối (SLIC) · Phác chì bằng AI (U²-Net Portrait, Informative Drawings) · viền do AI vẽ · độ sâu (Depth Anything) làm hướng nét · lai nét cong + đan chéo ([09](09_QUYET_DINH_THIET_KE.md) P28, P35; [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 17). Gói `onnxruntime` đã gỡ |
| Bút (18/11) | UM-100 là bút chính; Sakura phải ghi **0,5**; UB-155 dừng; nút Servo giật = giới hạn xung firmware, bỏ |
| So với phần mềm khác (18/11) | chủ dự án **tự test riêng DrawingBotV3** (và Plotcaster) cùng ảnh, cùng bút để so; **không chặn** việc khác |

### 4.2 Làm tiếp, theo thứ tự
1. **Thuật toán: ĐÃ CHỐT (xem 4.1), chỉ còn đo.** (a) **In giấy 4 tờ** rồi chỉnh hằng số nếu lệch: Phong cảnh (sóng + làm nét 1,5) · chân dung · ảnh 2D · tĩnh vật; (b) đo Tạo nét và vẽ thật trên **MiniPC** (RAM, giây); (c) *tùy chọn*: so DrawingBotV3 / Plotcaster bằng cùng 3 ảnh, bạn chấm "nét nào đẹp hơn" (tôi chỉ giúp số nét, thời gian). **S**
   **Tab Beta in PDF (chữ Word)** ([10](10_HUONG_PHAT_TRIEN.md) mục 1.1, **L**): sau mạng; bạn muốn đưa lên trước thì báo.
2. **Nối mạng** ([08](08_TRIEN_KHAI.md) mục E, F): MiniPC (đo xử lý ảnh, RAM) → Docker + USB cố định (udev) + IP cố định → Cloudflare Tunnel; **chỉ mở ra ngoài khi đã đặt PIN**; thử Origin / cookie qua Cloudflare. **M**
3. **Nút cứng + cảm biến bút** (YAML + dây; 10 mục 3.1): `feed_hold_pin` + `cycle_start_pin` cho Tạm dừng / Chạy tiếp chạy cả khi mất mạng; cảm biến bút vào `probe` để biết bút thật đã nhấc, thêm đèn "Bút". **S + dây**
4. **ESP32-S3** (cuối cùng, chọn 1–2): bảng điều khiển không dây, đo điện năng, đo nhiệt, camera. **L**
5. *(tùy chọn, chưa làm — chờ bạn)* **Sóng biến thiên siêu chi tiết** (`wave_am_detail`): sóng không chia mức nên "Số mức 8" vô tác dụng; muốn chi tiết phải nới 5 hằng số `AM_*`. Đã đo thử trên ảnh mèo A4 bút 0,5: khoảng cách đường 4,0 → **2,8 × nét**, biên độ 0,45 → **0,50**, bước sóng 2,0 → **2,5**, bỏ mẩu ngắn 3,0 → **1,0 mm**, ngưỡng trắng 1,6 → **0,6**, bật Phủ đều vùng sáng → **592 nét / 21,2 m / 3,1 phút** (hiện tại 125 nét / 21,5 m / 2,8 phút). Cần: khối `WAVE_DETAIL` (`styles.py`) + `spec` + ô chọn + khoá dịch + test khoá + tài liệu. **S–M**


### 4.3 Cần thử (chi tiết và cách làm: [07](07_THU_NGHIEM.md) danh sách đầu tệp)
| Nhóm | Gồm |
|---|---|
| **A. In giấy** | Ảnh 2D + Nét viền · Phong cảnh (sóng + làm nét) · chân dung · tĩnh vật · tờ tông · **vùng chủ thể trên một ảnh có nền rối** · (cuối, chờ ảnh thật) Theo dáng ảnh |
| **B. Máy** | ghi thông số laptop và thời gian Tạo nét · **tiếng "khực" ở góc trái** khi vẽ nét 45° (B4, tạm hoãn 18/11) |
| **C. Người dùng, mạng** | cách vào web từ điện thoại ([08](08_TRIEN_KHAI.md) mục C) · PIN + giao diện khách · luồng khách gửi ảnh · tắt Wi-Fi mạch MKS · **âm báo xong / lỗi nghe được trên máy bạn** |
| **D. Bản mang đi, MiniPC** | máy sạch · điện thoại thật · Docker, USB, Cloudflare ([08](08_TRIEN_KHAI.md) mục G) |

### 4.4 Code nhỏ (không cần hỏi)
1. **Biểu đồ**: tốc độ trong `FS:` cao hơn thật tới 1,41 lần trên CoreXY (02 F15); hiện tốc độ thật = quãng ÷ thời gian. **S**
2. Mặc định `style.kind` ở `spec.py` đang là `zigzag` còn giao diện là Gạch chéo: đổi cho khớp. **S**
3. Dòng gợi ý "0,02–0,1; lớn hơn = qua góc nhanh hơn" dưới ô junction trong Cấu hình máy: ghi thêm "đang dùng 0,03". **S**
4. Vùng chủ thể chưa đi theo **ảnh khách gửi** (khách chưa khoanh được): thêm vào `customerSnapshot` nếu cần. **S**

Cần bạn cung cấp: ảnh và số sau mỗi buổi thử; router mini (hoặc 4G) cho demo không mạng; máy hiện sóng / logic analyzer nếu có.

## 5. Không làm
Hồ sơ tốc độ (Chữ / Tranh / Đẹp nhất) · gửi dồn lệnh, tăng baud · dithering từng điểm ảnh · tối ưu thứ tự theo hàm chi phí · AI tạo ảnh trên MiniPC (AI tìm viền / phác chì: đã thử 18/11 và bỏ hẳn, MiniPC i5-6100T 12–16 GB, thử ở việc 4.2 1c) · stipple / TSP · WebSocket · viết lại tô nét bằng JavaScript.
