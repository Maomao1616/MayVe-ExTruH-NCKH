# 11 — Tình trạng và việc cần làm

> Sổ làm việc, cập nhật 26/11/2026. **Một nơi duy nhất** cho: đã xong · cần thử · làm tiếp (theo thứ tự bạn chốt).
> Cách thử từng bài: [07](07_THU_NGHIEM.md). Lý do từng quyết định: [09](09_QUYET_DINH_THIET_KE.md). Ý tưởng để dành: [10](10_HUONG_PHAT_TRIEN.md).
> Cỡ việc: **S** vài giờ · **M** nửa đến một ngày · **L** nhiều ngày.

## 1. Tình trạng chung

| Khối | Tính năng | Đã kiểm ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95 % | ~70 % |
| Tạo bản vẽ (ảnh, SVG, bản thảo, hàng đợi) | ~95 % | ~60 % (thuật toán đã xem bản thảo, chưa in hết) |
| Cài đặt, cấu hình máy | ~90 % | ~70 % |
| Phân quyền, bản mang đi | ~85 % | ~60 % |

Test tự động (chạy lại 26/11/2026): máy chủ **657** (8 bài tab Beta cần PyMuPDF, thiếu thì tự bỏ qua; `test_joblog` và vài bài chờ thời gian có thể hỏng chập chờn khi máy bận, chạy riêng thì qua), giao diện **72**. Còn thiếu chủ yếu: **in thật** các bản mới (Chất lượng tối đa, Xoắn ốc mới, tách mực, tab Beta) và **thử trên MiniPC**.

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
| **Kiểu nét** | 5 kiểu: Đan chéo (mặc định) · Đường dòng · Sóng điều biên · Xoắn ốc (viết lại 22/11) · Đường bao (tên cũ: [05](05_TAB_TAO_BAN_VE.md) mục 3); ô **Chất lượng tối đa** (`style.unlimited`) cho 3 kiểu tô; vòng **sửa sai tông** 1 lượt; hằng số: [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 19 |
| **5 preset** | Chân dung · Hình vẽ 2D · Phong cảnh · Bản vẽ kỹ thuật · Chất lượng tối đa ([09](09_QUYET_DINH_THIET_KE.md) P14) |
| **Tab Beta PDF** | đọc chữ thật trong PDF, viết lại bằng chữ viết tay nối nét (chữ HOA và số kiểu in), dấu tiếng Việt tự ghép, khung bảng từ vector, hình vẽ nét lấy đường giữa, ảnh chụp đi đường tô ảnh; PDF thật 32 trang chạy hết ([12](12_TAB_BETA_PDF.md)) |
| **Giao diện** | màu nhấn vàng an toàn `#ffd400`; số đo WCAG: viền rõ, viền ô nhập ≥ 3:1, chữ ≥ 12 px (P45); hai khung vẽ giấy ngà + nét đen; âm báo xong / lỗi; **lung linh nhẹ** (24/11, [09](09_QUYET_DINH_THIET_KE.md) P48): khung thả tệp, công tắc ngày / đêm ở Cài đặt, thẻ thông tin, nút chính, thanh trượt 5 ô tông ảnh, thanh bước tiến trình, chữ hướng dẫn viết lại học thuật |
| **Triển khai** | bản mang đi Windows + `Cap nhat.bat`; launcher ưu tiên `backend\.venv` rồi mới `Python\`; demo không cần Internet |
| **Đo đạc** | `tools/do_thoi_gian.py` (giây từng bước, RAM đỉnh, thông tin máy); `ink_real.py` đo được cả Đường dòng, Xoắn ốc; số laptop 22/11 ở [07](07_THU_NGHIEM.md) mục 9 |
| **Giao diện điện thoại + dọn tab Điều khiển (P51, 26/11)** | thanh tab đáy, khối thu gọn bằng mũi tên, nút Mở rộng / Thu gọn, Terminal luôn mở trên máy tính, Hủy tác vụ luôn hiện, số lăn tọa độ, vệt sáng laser; **bỏ nút đổi tốc độ** (backend không còn nhận `feed_*`); máy chủ gửi `Cache-Control: no-cache` cho tệp giao diện ([03](03_CAU_TRUC_PHAN_MEM.md) mục 6.2, [09](09_QUYET_DINH_THIET_KE.md) P51). **Chưa thử trên điện thoại thật** (thanh tab đáy với vùng an toàn iPhone, bàn phím ảo, ô xám sau khi chạm) |
| **Dọn tài liệu (P16, 26/11)** | thêm mục lục đầu [12](12_TAB_BETA_PDF.md); dấu ✅ "Hàng chờ tạo nét" ở [10](10_HUONG_PHAT_TRIEN.md) ghi rõ phần đã làm / chưa làm; [13](13_MANG_VA_TEN_MIEN.md) mục 9 ghi đúng "đã làm 25/11", bỏ câu trùng `Python\`; số test cập nhật 652 / 68. Không sửa mã |

## 4. Việc tiếp


### 4.1 Đã chốt (không hỏi lại)
| Việc | Quyết định |
|---|---|
| Thuật toán vẽ ảnh | **ĐÓNG BĂNG (22/11/2026)**: 5 kiểu (Đan chéo · Đường dòng · Sóng điều biên · Xoắn ốc · Đường bao) + ô **Chất lượng tối đa** cho 3 kiểu tô + 5 preset ([09](09_QUYET_DINH_THIET_KE.md) P40–P42, tên mới ở [05](05_TAB_TAO_BAN_VE.md)). Chỉ chỉnh hằng số theo bản in (nêu số trước / sau); mở lại khi có người bổ sung |
| Đã thử và bỏ hẳn | Khối (SLIC) · Phác chì AI · viền AI · độ sâu làm hướng nét · lai nét cong + đan chéo ([09](09_QUYET_DINH_THIET_KE.md) P28, P35) |
| Máy | gia tốc **2700**, junction **0,02** (tiếng "khực" hết), servo **5,3 V** ([02](02_PHAN_CUNG_MAY.md)) |
| Bút | UM-100 chính; Sakura ghi 0,5; UB-155 dừng |
| Nút bút | `G90 G0 Z…`, Giữa = Z3 (servo giật do xung firmware, bỏ, [02](02_PHAN_CUNG_MAY.md) F16) |
| PIN | **không bắt buộc** khi mở ra ngoài (chủ dự án chọn 24/11/2026; launcher không chặn). Chưa đặt = ai có địa chỉ cũng là quản lý. **Nên đặt trước khi đưa địa chỉ cho người khác** ([13](13_MANG_VA_TEN_MIEN.md) mục 6) |
| Thứ tự | thuật toán ✅ → tách lớp màu ✅ → Tab Beta ✅ lõi → nối mạng (Cloudflare) → nút cứng + cảm biến bút → ESP32 |

### 4.2 Làm tiếp, theo thứ tự
1. **In giấy** (bạn): các bài ở [07](07_THU_NGHIEM.md) mục A (gồm tách mực 3 bút A9). Gửi ảnh, AI chỉnh hằng số. Rồi đo trên **MiniPC** bằng `tools/do_thoi_gian.py` ([07](07_THU_NGHIEM.md) mục 9): số này quyết định có cần viết lại phần chậm (vd bằng Rust) hay không.
2. **Tab Beta**: **in thử** một trang báo cáo (bảng, khung, tiêu đề 18–20, chữ 14–16) bằng bút bi 0,5 (thử cả 0,38–0,40), rồi "tạo tất cả trang" nếu cần. Máy mới phải cài `pymupdf` vào Python launcher dùng (`backend\.venv` trước, rồi `Python\`): `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`. **Sau đó: trang Soạn font** (kế hoạch đã chốt, chưa làm: [12](12_TAB_BETA_PDF.md) mục 11b).
3. **Nối mạng** (**M**, [08](08_TRIEN_KHAI.md) mục E, F): **bước 1 (24/11, chưa có MiniPC): chạy trên laptop**: tên miền + Cloudflare Tunnel + `data\mang.txt`, launcher đã hỗ trợ ([13](13_MANG_VA_TEN_MIEN.md): đã chạy thật 24/11: `plotter.tenmien.com` mở được từ 4G, nút QR trên header; còn đặt PIN, Cloudflare Access, thử thao tác ghi qua tên miền), cần bạn đặt PIN và tạo đường hầm; thử Origin / cookie qua Cloudflare. **Bước 2:** MiniPC → Docker hoặc systemd + USB cố định + IP cố định.
4. **Webcam theo dõi** (**M**, dự định 24/11/2026, làm sau khi hoàn thiện tab Beta; chi tiết ở [09](09_QUYET_DINH_THIET_KE.md) P49): webcam USB cắm vào máy chạy server, xem trực tiếp + timelapse bản vẽ.
5. **Nút cứng + cảm biến bút** (**S** + dây, [10](10_HUONG_PHAT_TRIEN.md) 3.1): `feed_hold_pin`, `cycle_start_pin`, cảm biến bút vào `probe`.
6. **ESP32-S3** (cuối): bảng điều khiển không dây, đo **dòng điện / điện năng** (Wh mỗi bản vẽ) và rung (gia tốc kế); **không đo nhiệt** (chủ dự án 24/11: động cơ chạy tải nhẹ, số đo không có ý nghĩa) (**L**).

### 4.4 Dự định làm tiếp (ghi 24/11/2026, làm từ 25/11)
Bối cảnh: chủ dự án **không có laptop**, mượn máy; có một ổ SSD ngoài sau này gắn MiniPC. Chi tiết quyết định: [13](13_MANG_VA_TEN_MIEN.md) mục 9.
1. **Commit** (khi chủ dự án bảo; chủ dự án tự push): 3 commit: (a) 4 việc code nhỏ (biểu đồ tốc độ thật, nhãn junction, vùng chủ thể ảnh khách, CSS màn hẹp); (b) launcher + tên miền con + máy chủ nhận `.tên-miền`; (c) nút QR + docs 13 + kế hoạch webcam / IoT + sinh lại `AI_CODEMAP`.
2. **Launcher cho máy mượn** (**S–M**): tìm `launcher\cloudflared.exe` và chìa khóa `data\cloudflared\<mã>.json` (chạy bằng `--cred-file`, không cần `config.yml`; máy này giữ cách cũ làm dự phòng); thứ tự tìm Python: `backend\.venv` (thử chạy thật) → `Python\` (**mang theo làm bản chính trên SSD**, chủ dự án chọn 25/11/2026 vì có 2 máy mượn); không được thì báo chạy **`Cai may moi.bat`** (tạo lại `backend\.venv` bằng Python 3.12 của máy, đang chạy được thì không làm gì). **Đã làm 25/11/2026** (đường ống bằng chìa khóa + `cloudflared.exe` đã thử ở máy chính, mở được từ 4G; chưa thử trên máy thứ hai): `launcher/start.ps1`, `stop.ps1`, `launcher/cai_may_moi.ps1`, `Cai may moi.bat`, `.gitignore` (`/launcher/cloudflared.exe`).
3. **Thử** (chủ dự án + AI): chạy đường ống chỉ với chìa khóa `.json` (tạm đổi tên thư mục `.cloudflared` của người dùng để chắc không dựa vào nó); `PYTHONPATH` có đi vào tiến trình con xử lý ảnh không; Git báo "dubious ownership" trên ổ ngoài; máy mượn đủ Python 3.12 x64 và thư viện.
4. **Chuẩn bị SSD** (chủ dự án): exFAT; clone **kho gốc** của mình vào SSD; chép `data\` (**bản duy nhất**: sao lưu định kỳ); đặt `cloudflared.exe`; sau commit + push mới clone.
5. **Hướng dẫn** "Mang theo bằng SSD / máy mượn" từng bước ở docs/13.
6. **Sau đó:** chủ dự án gửi phiếu P15 (kiểm toàn bộ tệp, tệp `export/deepseek/phieu-24-11-p15-kiem-tat-ca.md`, Git bỏ qua) cho DeepSeek → AI kiểm lại báo cáo → **sắp xếp lại docs** và sửa lỗi code theo báo cáo.
Việc xếp sau (đã ghi): đặt PIN + thử đăng nhập qua tên miền, Cloudflare Access, webcam ([09](09_QUYET_DINH_THIET_KE.md) P49), ESP32 đo dòng ([09](09_QUYET_DINH_THIET_KE.md) P50).

### 4.3 Code nhỏ (24/11/2026: làm xong cả 4, chờ bạn xem trên điện thoại)
Biểu đồ tốc độ dùng quãng XY ÷ thời gian (`joblog.py`, cửa sổ 0,4 s; `FS:` trên CoreXY cao giả tới 1,41 lần, 02 F15; đầu lần chạy chưa đủ mẫu thì bỏ) · nhãn ô junction ghi "nên dùng 0,02" · ảnh khách gửi mang theo vùng chủ thể elip / chữ nhật / tự tách (vẽ tay không gửi: quá nặng, giới hạn 8 KB) · ô chọn kiểu nét / màu / preset không tràn màn hình hẹp (chưa xem trên điện thoại thật).

Cần bạn cung cấp: ảnh và số sau mỗi buổi thử; router mini (hoặc 4G) cho demo không mạng; máy hiện sóng / logic analyzer nếu có; **ảnh dây điện thật từ nguồn Mean Well tới MKS và nhánh XL4005** (chọn chỗ đặt cảm biến dòng); **linh kiện IoT** (xem [09](09_QUYET_DINH_THIET_KE.md) P50): webcam USB + cần cổ ngỗng, ESP32 + INA260 + hạ áp 5 V + cầu chì.

## 5. Không làm
Hồ sơ tốc độ (Chữ / Tranh / Đẹp nhất) · gửi dồn lệnh, tăng baud · dithering từng điểm ảnh · tối ưu thứ tự theo hàm chi phí · AI tìm nét / tạo ảnh (thử 18/11 và bỏ, P35) · stipple / TSP · WebSocket · viết lại tô nét bằng JavaScript · tiếp tục khi mất điện.
