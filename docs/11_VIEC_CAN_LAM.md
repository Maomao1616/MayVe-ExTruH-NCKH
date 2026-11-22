# 11 — Tình trạng và việc cần làm

> Sổ làm việc, cập nhật 22/11/2026. **Một nơi duy nhất** cho: đã xong · cần thử · làm tiếp (theo thứ tự bạn chốt).
> Cách thử từng bài: [07](07_THU_NGHIEM.md). Lý do từng quyết định: [09](09_QUYET_DINH_THIET_KE.md). Ý tưởng để dành: [10](10_HUONG_PHAT_TRIEN.md).
> Cỡ việc: **S** vài giờ · **M** nửa đến một ngày · **L** nhiều ngày.

## 1. Tình trạng chung

| Khối | Tính năng | Đã kiểm ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95 % | ~70 % |
| Tạo bản vẽ (ảnh, SVG, bản thảo, hàng đợi) | ~95 % | ~60 % (thuật toán đã xem bản thảo, chưa in hết) |
| Cài đặt, cấu hình máy | ~90 % | ~70 % |
| Phân quyền, bản mang đi | ~85 % | ~60 % |

Test tự động: máy chủ **635** (8 bài tab Beta cần PyMuPDF, thiếu thì tự bỏ qua), giao diện **68** (qua 22/11/2026). Còn thiếu chủ yếu: **in thật** các bản mới (Chất lượng tối đa, Xoắn ốc mới, tách mực, tab Beta) và **thử trên MiniPC**.

## 2. Bản đồ việc

```
 ĐÃ XONG (mục 3)                 LÀM TIẾP, THEO THỨ TỰ (mục 4.2)                              CUỐI
 ───────────────                 ───────────────────────────────                              ─────
 máy + G-code chuẩn ──┐
 thuật toán (đóng băng)┼─► 1. IN THỬ (07 mục A) → chốt hằng; đo MiniPC (07 mục 9) ─┐
 tách mực, tab Beta ──┘   (Soạn font: kế hoạch ở 12 mục 11b, chưa làm)            │
                                  2. NỐI MẠNG: MiniPC + Docker + Cloudflare ◄───────┘
 an toàn / phân quyền ─────────► 3. NÚT CỨNG + CẢM BIẾN BÚT (YAML + dây) ───────────► 4. ESP32 (IoT)
```

## 3. Đã xong (chỉ từ khóa và hằng đã chốt; lý do ở 09, số ở 06)

| Nhóm | Đã chốt |
|---|---|
| **Máy và G-code** | vẽ / di chuyển **8000**, gia tốc **2700**, junction **0,02**, servo **5,3 V** (22/11/2026); Z nhấc **3**, hạ **2000**, chờ **0**; nút bút `G90 G0 Z…`: Lên **Z5** · Giữa **Z3** · Xuống **Z0**; nét cong **G2/G3**; **115200 baud**, gửi từng dòng chờ `ok`; `$10=3` cho biểu đồ hàng đợi |
| **Máy đã thử xong** | mất bước ở 7000–10000 ổn · tốc độ tối đa **10000** · TMC2209 **SpreadCycle** · Home, Z, đèn X / Y đúng · tiếp tục từ điểm dừng đúng · G2/G3 trên bản vẽ thật · tab Điều khiển mượt · tiếng "khực" hết với 2700 / 0,02 |
| **Bút, giấy** | ô "Bút vẽ" = **nét đo trên giấy**: UB-155 **0,38** · UM-100 **0,40** · Sakura **0,50** · bút bi 0,5; giấy Ivory 250 g/m² mặt bóng |
| **An toàn, phân quyền** | máy mặc định chỉ đọc; khóa chuyển động tự khóa sau 15 phút; Home tự nâng bút; hủy 3 chế độ; tiếp tục từ điểm dừng; PIN quản lý đổi được; khách xem + **Gửi ảnh** (tự xóa 5 ngày, ≤ 6 ảnh / giờ); SSE cho trạng thái |
| **Tạo bản vẽ** | nạp ảnh → cắt / chỉnh tông → **Tạo nét**; **vùng chủ thể** elip / chữ nhật / **Tự động** / **Vẽ tay**; SVG; bản thảo + hàng đợi; 2–4 màu và **tách mực theo bộ bút** (đen–đỏ–navy hoặc CMYK, ô Độ nổi màu); zoom khung vẽ; Tờ thử; Biểu đồ số liệu chạy máy |
| **Kiểu nét** | 5 kiểu: Gạch chéo (mặc định) · Theo dáng · Sóng biến thiên · Xoắn ốc (viết lại 22/11) · Nét viền; ô **Chất lượng tối đa** (`style.unlimited`) cho 3 kiểu tô; vòng **sửa sai tông** 1 lượt; hằng số: [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 19 |
| **5 preset** | Chân dung · Hình vẽ 2D · Phong cảnh · Bản vẽ kỹ thuật (Schematic) · Chất lượng tối đa ([09](09_QUYET_DINH_THIET_KE.md) P14) |
| **Tab Beta PDF** | đọc chữ thật trong PDF, viết lại bằng chữ viết tay nối nét (chữ HOA và số kiểu in), dấu tiếng Việt tự ghép, khung bảng từ vector, hình vẽ nét lấy đường giữa, ảnh chụp đi đường tô ảnh; PDF thật 32 trang chạy hết ([12](12_TAB_BETA_PDF.md)) |
| **Giao diện** | màu nhấn vàng an toàn `#ffd400`; số đo WCAG: viền rõ, viền ô nhập ≥ 3:1, chữ ≥ 12 px (P45); hai khung vẽ giấy ngà + nét đen; âm báo xong / lỗi |
| **Triển khai** | bản mang đi Windows + `Cap nhat.bat`; launcher ưu tiên `backend\.venv` rồi mới `Python\`; demo không cần Internet |
| **Đo đạc** | `tools/do_thoi_gian.py` (giây từng bước, RAM đỉnh, thông tin máy); `ink_real.py` đo được cả Theo dáng, Xoắn ốc; số laptop 22/11 ở [07](07_THU_NGHIEM.md) mục 9 |

## 4. Việc tiếp


### 4.1 Đã chốt (không hỏi lại)
| Việc | Quyết định |
|---|---|
| Thuật toán vẽ ảnh | **ĐÓNG BĂNG (22/11/2026)**: 5 kiểu (Đan chéo · Đường dòng · Sóng điều biên · Xoắn ốc · Đường bao) + ô **Chất lượng tối đa** cho 3 kiểu tô + 5 preset ([09](09_QUYET_DINH_THIET_KE.md) P40–P42, tên mới ở [05](05_TAB_TAO_BAN_VE.md)). Chỉ chỉnh hằng số theo bản in (nêu số trước / sau); mở lại khi có người bổ sung |
| Đã thử và bỏ hẳn | Khối (SLIC) · Phác chì AI · viền AI · độ sâu làm hướng nét · lai nét cong + đan chéo ([09](09_QUYET_DINH_THIET_KE.md) P28, P35) |
| Máy | gia tốc **2700**, junction **0,02** (tiếng "khực" hết), servo **5,3 V** ([02](02_PHAN_CUNG_MAY.md)) |
| Bút | UM-100 chính; Sakura ghi 0,5; UB-155 dừng |
| Nút bút | `G90 G0 Z…`, Giữa = Z3 (servo giật do xung firmware, bỏ, [02](02_PHAN_CUNG_MAY.md) F16) |
| PIN | chưa đặt thì để nguyên; **phải đặt trước khi mở ra ngoài** |
| Thứ tự | thuật toán ✅ → tách lớp màu ✅ → Tab Beta ✅ lõi → nối mạng (Cloudflare) → nút cứng + cảm biến bút → ESP32 |

### 4.2 Làm tiếp, theo thứ tự
1. **In giấy** (bạn): các bài ở [07](07_THU_NGHIEM.md) mục A (gồm tách mực 3 bút A9). Gửi ảnh, AI chỉnh hằng số. Rồi đo trên **MiniPC** bằng `tools/do_thoi_gian.py` ([07](07_THU_NGHIEM.md) mục 9): số này quyết định có cần viết lại phần chậm (vd bằng Rust) hay không.
2. **Tab Beta**: **in thử** một trang báo cáo (bảng, khung, tiêu đề 18–20, chữ 14–16) bằng bút bi 0,5 (thử cả 0,38–0,40), rồi "tạo tất cả trang" nếu cần. Máy mới phải cài `pymupdf` vào Python launcher dùng (`backend\.venv` trước, rồi `Python\`): `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`. **Sau đó: trang Soạn font** (kế hoạch đã chốt, chưa làm: [12](12_TAB_BETA_PDF.md) mục 11b).
3. **Nối mạng** (**M**, [08](08_TRIEN_KHAI.md) mục E, F): MiniPC → Docker + USB cố định + IP cố định → Cloudflare Tunnel; chỉ mở ra ngoài khi đã đặt PIN; thử Origin / cookie qua Cloudflare.
4. **Nút cứng + cảm biến bút** (**S** + dây, [10](10_HUONG_PHAT_TRIEN.md) 3.1): `feed_hold_pin`, `cycle_start_pin`, cảm biến bút vào `probe`.
5. **ESP32-S3** (cuối): bảng điều khiển không dây, đo điện năng / nhiệt, camera (**L**).

### 4.3 Code nhỏ (không cần hỏi)
1. **Biểu đồ**: tốc độ trong `FS:` cao hơn thật tới 1,41 lần trên CoreXY (02 F15); hiện tốc độ thật = quãng ÷ thời gian. **S**
2. Dòng gợi ý dưới ô junction trong Cấu hình máy: ghi thêm "đang dùng 0,02". **S**
3. Vùng chủ thể chưa đi theo **ảnh khách gửi**: thêm vào `customerSnapshot` nếu cần. **S**
4. Cỡ chữ ô tên kiểu trên điện thoại (tên mới dài hơn). **S**

Cần bạn cung cấp: ảnh và số sau mỗi buổi thử; router mini (hoặc 4G) cho demo không mạng; máy hiện sóng / logic analyzer nếu có.

## 5. Không làm
Hồ sơ tốc độ (Chữ / Tranh / Đẹp nhất) · gửi dồn lệnh, tăng baud · dithering từng điểm ảnh · tối ưu thứ tự theo hàm chi phí · AI tìm nét / tạo ảnh (thử 18/11 và bỏ, P35) · stipple / TSP · WebSocket · viết lại tô nét bằng JavaScript · mã QR địa chỉ · tiếp tục khi mất điện.
