# 12 — Tab Beta: in trang PDF (chữ Word, bảng, khung, ảnh)

> Tính năng **tách riêng hoàn toàn** khỏi phần còn lại (xem mục 10 "Cách gỡ"). Tài liệu này giải thích hướng phát triển, thuật toán, thư viện và hằng số, theo cách viết của [06](06_THUAT_TOAN_XU_LY_ANH.md). Quyết định và lý do: [09](09_QUYET_DINH_THIET_KE.md) P47.

**Trạng thái (22/11/2026):** đã làm xong phần mềm và test; **chưa in giấy, chưa đo trên MiniPC**. Số đo ở mục 7 là trên máy phát triển.

## 0. Tóm tắt một đoạn
Bạn xuất tài liệu Word thành PDF, mở tab **Beta PDF**, chọn một trang. Phần mềm **không chụp trang thành ảnh rồi làm mỏng** (đã thử: chữ Times 14 bị đứt nét, mất dấu). Thay vào đó nó **đọc từng ký tự thật trong PDF** (chữ gì, ở đâu, cỡ nào, đậm hay nghiêng) và **viết lại như viết tay**: từng từ một nét liền, nét đều nhau, chỉ khác cỡ chữ, dấu tiếng Việt tự ghép; **đường kẻ bảng và khung** vẽ thẳng từ vector; **ảnh trong trang** đi qua đường tô ảnh của tab Tạo bản vẽ. Kết quả là một bản vẽ như mọi bản vẽ khác: mở ở tab Tạo bản vẽ để đặt giấy, tạo G-code, lưu bản thảo.

## 1. Phương hướng phát triển
| Giai đoạn | Việc | Trạng thái |
|---|---|---|
| **1. Lõi** | đọc PDF → chữ nét đơn có dấu Việt + đường kẻ + ảnh → bản vẽ; tab giao diện; test | ✅ 22/11/2026 |
| **2. In thử và chỉnh** | in trang mẫu (bảng, khung, tiêu đề 18–20, chữ 14–16) bằng bút bi 0,5; chỉnh hằng số mục 8; đo độ đọc được | ⏳ cần bạn in |
| **3. Đo trên MiniPC** | giây, RAM khi trang kín chữ + vài ảnh | ⏳ |
| **4. Nhiều trang** | nút "Tạo tất cả trang": mỗi trang một bản thảo trong danh sách bản thảo | 💡 |
| **5. Chữ khó** | công thức, ký hiệu, chữ xoay: hiện rơi về skeleton từng ký tự hoặc bị bỏ qua | 💡 |
| **6. Khối tô** | ô bảng tô nền, tô màu: hiện bỏ qua (chỉ cảnh báo); có thể tô gạch chéo theo độ sáng nền | 💡 |
| **7. Soạn font riêng** | trang Soạn font trong tab: xuất font vpype ra tệp, chủ dự án sửa từng chữ bằng chuột, nạp thẳng thay vpype (thiếu thì dùng vpype); sau đó bút cảm ứng và biến thể mỗi chữ (mục 11b) | 📋 đã chốt kế hoạch, chưa làm |
| **8. PDF quét** | trang là ảnh (không có chữ thật): hiện chỉ tô như ảnh; có thể thêm nhận dạng chữ (OCR) rồi viết lại | 💡 |

## 2. Cách dùng
1. Trong Word: **Lưu thành PDF** (giữ font Times New Roman và dấu tiếng Việt).
2. Tab **Beta PDF** → chọn tệp → chọn trang (← Trước / Sau →). Bên trái là trang gốc.
3. Chọn cách vẽ chữ (mặc định **Nét đơn**, font **Chữ viết tay nối nét**), bút chữ 0,5, bút ảnh 0,4 → **Tạo nét trang này**. Bên phải hiện nét sẽ vẽ, số nét, độ dài, ước thời gian; hai khung phóng to được (nút − / +, Ctrl + lăn chuột).
4. **Mở ở Tạo bản vẽ →**: đặt tờ giấy, kéo khung, tạo G-code, lưu bản thảo như mọi bản vẽ. Hai lớp (chữ + khung bút bi, ảnh bút tô) ra **hai tệp G-code**, đổi bút giữa hai tệp.
Chỉ quản lý dùng tab này (khách không thấy).

## 3. Dây chuyền
```
PDF ──► reader.py ──► Ký tự (chữ, vị trí, cỡ, đậm, nghiêng)
                 ├──► Đường kẻ (đoạn thẳng, hình chữ nhật, cung)
                 └──► Khung ảnh
Ký tự ─► text.py ─► [nét đơn: viet.py + fontdata.py] hoặc [skeleton] ─► nối nét ─┐
Đường kẻ ─► frame.py ─► gộp, nối, sắp ──────────────────────────────────────────┼─► Lớp 1 (bút chữ)
Khung ảnh ─► images.py ─► drawing.raster (đường tô ảnh sẵn có) ─────────────────► Lớp 2 (bút ảnh)
                                    service.py: ghép lớp, thống kê, lưu vào TASKS (như một bản vẽ đã nạp)
```
Kết quả cùng dạng với `drawing.raster.build_raster` (lớp, khung, thông tin, cảnh báo) nên **phần xem trước, bố trí, G-code, bản thảo dùng lại 100 %**; tab Beta chỉ giao bản vẽ qua sự kiện `extruxy:beta-task` (một đoạn nhận ở `views/drawing.js`).

## 4. Thuật toán từng bước

### 4.1 Đọc trang (`reader.py`, PyMuPDF)
- Tọa độ đổi sang **mm, gốc ở góc trên trái, Y xuống** (như phần còn lại của dự án). 1 pt = 25,4 / 72 = 0,3528 mm.
- **Ký tự:** `page.get_text("rawdict")` cho từng ký tự: mã chữ, hộp (x0, x1), đường cơ sở (y của điểm gốc), cỡ chữ, cờ đậm / nghiêng (cờ font hoặc tên font có Bold / Italic / Oblique). Ligature (ﬁ, ﬂ…) tách thành các chữ thường, chia đều bề rộng. Chữ **xoay** (hướng dòng không ngang) bị bỏ qua và đếm.
- **Đường kẻ:** `page.get_drawings()`; mỗi hình thành đoạn thẳng:
  - đoạn `l` → đoạn thẳng; cung Bézier `c` → 10 đoạn thẳng; hình tứ giác `qu` → viền đóng;
  - hình chữ nhật có **viền** → 4 cạnh; hình chữ nhật **tô đặc mỏng hơn 2 pt** (cách Word và trình duyệt vẽ viền bảng) → **một đường tại tâm**, bề dày ghi lại;
  - hình tô đặc lớn (nền ô, khối màu) → **không vẽ**, chỉ đếm và cảnh báo; màu gần trắng bỏ qua.
- **Ảnh:** `page.get_image_info()` lấy khung (bỏ khung nhỏ hơn 4 pt²).
- Giới hạn bảo vệ: PDF ≤ 40 MB, ≤ 500 trang; PDF có mật khẩu bị từ chối.

### 4.2 Font nét đơn (`fontdata.py`)
- Nguồn: font **Hershey** có sẵn trong gói vpype (`timesr` / `timesrb` / `timesi` / `timesib` = giống Times; `futural` / `futuram` = nét đơn kiểu sans). Dữ liệu: ASCII 32–127, mỗi ký tự là các đường gấp khúc, y hướng xuống, đường cơ sở y = 9; **chiều cao chữ hoa 21, chữ thường 14, chân chữ sâu 7** (đơn vị Hershey). Đổi y thành "so với đường cơ sở" để ghép dấu dễ.
- **Đổi sang mm:** cỡ chữ (em) = 21 / 0,662 ≈ **31,7 đơn vị**, vì chữ hoa của Times New Roman cao 0,662 em. Vậy 1 đơn vị = cỡ chữ / 31,7; chữ 14 pt (4,94 mm) → 0,156 mm mỗi đơn vị.
- Ba họ font (tham số `font`):
  - **`script`** (mặc định): chữ viết tay nối nét (Hershey `cursive`). Mỗi chữ cái chủ yếu là **một nét liền**, vào ở mép trái và ra ở mép phải ngang cùng độ cao (y = 4), nên đặt sát nhau là **nối liền cả từ** (mục 4.4b). **Chỉ một kiểu**: bỏ đậm, nghiêng của Word, chỉ khác cỡ chữ. **Chữ HOA và chữ SỐ viết kiểu in** như chữ tiếng Anh (chữ hoa viết tay của font này trông lệch): lấy từ họ `simplex`, co `PRINT_SCALE` 0,9, **đứng riêng, không nối** (`Glyph.solo`). Chữ thường chỉ cao 9 (Times 14) nên co giãn `FAMILY_SCALE` 0,85 ngang × 1,1 dọc (1,0 × 1,45 chồng dòng, 0,8 × 1,0 nhỏ).
  - **`simplex`**: chữ rời, một nét cho mỗi đường, ít nét; chữ nghiêng làm bằng cách xô ngang 0,2.
  - **`times`**: giống Times nhưng nhiều nét kép nên đặc, gấp đôi số nét (mục 7).
  Chiều cao chữ thường / hoa / chữ có đuôi (`fontdata.metrics`) **đo từ chính glyph x, H, d của họ font** (Times và simplex: 14, 21, 21; script: 9,9, 18,9 (chữ hoa in), 23,1), nên dấu tiếng Việt đặt đúng chỗ ở mọi họ font.
- Font Hershey **không có chữ tiếng Việt** (kiểm: "Giới thiệu đề tài" chỉ còn 45 nét thay vì 64, chữ có dấu bị rụng hết).

### 4.3 Ghép chữ tiếng Việt (`viet.py`)
Mỗi chữ như ấ, ặ, ữ, Đ dựng từ **chữ gốc + dấu phụ + dấu thanh**:
- Tách bằng chuẩn Unicode NFD: chữ gốc ASCII + dấu **mũ** (â ê ô), **trăng** (ă), **râu** (ơ ư) + dấu thanh **sắc, huyền, hỏi, ngã, nặng**. `đ`, `Đ` không tách được nên xử lý riêng (gạch ngang qua chữ d).
- **Vị trí** (đơn vị Hershey, `top` = đỉnh chữ: −14 chữ thường, −21 chữ hoa):

| Thành phần | Tâm đặt tại | Ghi chú |
|---|---|---|
| dấu mũ, trăng | giữa chữ, cao hơn đỉnh 3,2 | |
| dấu thanh thường (a, e, o…) | sắc lệch phải 0,8, huyền lệch trái 0,8, cao 3,8 (hỏi 4,8, ngã 4,0) | |
| dấu thanh **trên dấu mũ** (ấ ầ ẩ ẫ) | sắc lệch phải 3,6, huyền lệch trái 3,6, cao 6,2 (hỏi 7,4, ngã 7,2) | giống cách viết tay |
| dấu thanh **trên dấu trăng** (ắ ằ ẳ ẵ) | gần giữa, cao 6,6–7,4 | |
| dấu nặng | giữa chữ, thấp hơn chân 3,2 | ạ ậ ặ… |
| râu (ơ ư) | nối từ mép phải đỉnh chữ, lên phải | dấu thanh vẫn ở giữa chữ |
| gạch đ | ngang thân d ở độ cao −16,5; gạch Đ ở giữa chiều cao chữ hoa | |

- **ì í ỉ ĩ** bỏ chấm của i (nét nằm hẳn trên đỉnh chữ), dấu thanh thay chỗ; **ị** giữ chấm trên, thêm chấm dưới.
- Chữ nghiêng: mọi dấu xô theo cùng độ nghiêng 0,2.
- Hình dấu (đa tuyến nhỏ): sắc `/`, huyền `\`, hỏi `?` nhỏ (đuôi cong), ngã `~` (một chu kỳ sin), mũ `^`, trăng `⌣`, nặng một chấm ngắn 0,8.
- Kiểm: 146 chữ cái tiếng Việt (73 thường + 73 hoa) × 2 họ font × 4 kiểu (thường, đậm, nghiêng, đậm nghiêng) đều dựng được (test `test_viet_glyphs.py`); đã xem ảnh bảng chữ ở cả thường lẫn hoa.

### 4.4 Đặt chữ theo từ (`text.py`, `word_strokes`)
Dàn trang (xuống dòng, căn đều, kerning) **do Word làm sẵn**; ta chỉ vẽ lại chữ **vào đúng khoảng mà PDF cho**, đặt **theo từng từ** (co từng chữ cái theo ô Times thì chữ rộng chữ hẹp, nhìn run):
1. Cắt dòng thành từ bằng dấu cách (dấu cách không có nét). Cỡ: `đơn vị = cỡ chữ PDF / 31,7`.
2. Trong một từ, chữ cái cách nhau **theo bề rộng tự nhiên của font nét đơn** (nhịp đều).
3. Cả từ co hoặc giãn **đều một hệ số** `s = bề rộng từ trong PDF / bề rộng tự nhiên`, kẹp trong `WORD_FIT_MIN` 0,55 … `WORD_FIT_MAX` 1,25. Từ bắt đầu đúng chỗ ký tự đầu, kết thúc đúng chỗ ký tự cuối nên dòng căn đều hai bên vẫn đúng.
4. Đường cơ sở và cỡ lấy theo **từng ký tự** (chỉ số trên, dưới vẫn đúng chỗ). Râu ơ ư làm ô chữ rộng thêm `HORN_EXTRA` 2,0.
5. Ký tự font không có tách riêng (vẽ theo hình gốc), phần còn lại của từ vẫn đặt theo từ.
6. Gạch dài (– — −) đứng riêng thì kéo giãn kín ô (`glyph_strokes`). Ngoặc cong, dấu ba chấm, nhân, chia… đổi về ASCII (`CHAR_MAP`).

### 4.4b Nối chữ thành một nét (chỉ họ `script`; `text._connected_word`)
Yêu cầu chủ dự án: "chỉ cần đúng chữ và đọc được; rung, nguệch ngoạc không sao; nếu được thì **nối nét thành một từ như viết tay**, nét đều, chỉ khác cỡ chữ".
1. Mỗi glyph tách thành **thân** và **nét phụ** (`_split_body`): thân = nét dài nhất cộng các nét nối tiếp nó (đầu / cuối chạm nhau, ≤ `BODY_TOL` 1,6).
2. **Nét phụ của chữ cái sát thân** (vòm của n, m, h; đuôi của d, g, p, q; gạch ngang của t; **râu ơ ư và gạch đ**) có một đầu cách thân ≤ `ATTACH_TOL` 6,5 (và dài ≥ `ATTACH_MIN_LEN` 5,0; râu và gạch đ luôn thử nối) thì **nối vào thân bằng một chuyến đi ra rồi quay lại** tại điểm chạm: bút không nhấc, đầu và cuối thân giữ nguyên để còn nối sang chữ kế, mực chồng đúng lên nét cũ nên không thấy. Đo: font `cursive` có hầu hết nét phụ bắt đầu cách thân 0–6 đơn vị, còn chấm của i, j dài 3,9.
3. Các thân trong cùng một từ nối đuôi nhau thành **một nét** (đoạn thẳng nối khi đuôi và đầu cách ≤ `CONNECT_UNITS` 10 đơn vị Hershey).
4. **Nét phụ còn lại viết sau khi xong cả từ**: chấm của i, j; dấu mũ, trăng, sắc, huyền, hỏi, ngã, nặng; như người viết tay. Chấm dài dưới `DOT_MIN` 0,5 được kéo thành đoạn ngắn để bút chạm giấy.
Kết quả: trung bình **2,8 nét mỗi từ** (937 từ trên 3 trang; 1–3 nét chiếm 3/4, từ có nhiều dấu như "thiết", "điện" 5–7 nét) thay vì một nét mỗi chữ cái.

### 4.5 Dòng, đoạn, nối nét, thứ tự
- **Gom dòng:** ký tự có đường cơ sở lệch nhau không quá 0,45 × cỡ chữ cùng một dòng; dòng từ trên xuống, trong dòng từ trái sang phải.
- **Cắt đoạn:** khoảng trống rộng hơn 1,5 × cỡ chữ cắt dòng thành các đoạn (để không gộp các ô bảng, chỉ dùng cho kiểu skeleton).
- **Nối nét** (`pathing.join`): đầu một nét cách đuôi nét trước không quá `join_mm` (0,25 mm) thì nối liền (có đảo chiều nếu đầu kia gần hơn), **giảm số lần nhấc bút**.
- Thứ tự: đường kẻ trước (sắp theo láng giềng gần nhất), rồi chữ **theo từng dòng**, giống người viết.

### 4.6 Kiểu skeleton và ký tự dự phòng
- Dùng cho kiểu "Giữ hình chữ gốc", chữ từ `mixed_min_pt` (17 pt) trở lên ở kiểu hỗn hợp, và **ký tự font không có** (vd ², công thức): kết xuất vùng chữ ở `skeleton_dpi` (600) → mực là điểm xám < `skeleton_threshold` (190) → `skimage.skeletonize` → dò nét bằng `drawing/trace.py` (cùng mã với phần nét viền của tab Tạo bản vẽ, đã có cắt râu và làm mượt) → bỏ nét ngắn hơn 0,3 mm.
- Vùng cắt quanh đường cơ sở: lên 0,95 em, xuống 0,32 em, thêm lề 0,4 mm; chọn hẹp để không dính viền bảng.
- Nhược điểm đã đo: chữ Times 14 bị **đứt nét mảnh, sinh râu ở chân chữ, mất dấu ơ ư, dấu thanh dính** (tăng lên 900 dpi không khá hơn), nên không phải kiểu chính.

### 4.7 Đường kẻ (`frame.py`)
1. Tách mọi hình thành **cạnh**; cạnh ngắn dưới 0,05 mm bỏ.
2. Cạnh dày hơn **1,5 × bút** (`thick_double`): thay bằng **hai đường song song** lệch ±(bề dày − bút)/2, tối đa 1 mm (cách "chữ đậm vẽ hai đường").
3. **Gộp:** cạnh ngang / dọc (lệch trục < 0,25 mm) cùng đường (cách nhau < 0,3 mm), chồng hoặc nối tiếp nhau (hở < 0,3 mm) thành một đường dài. Mỗi cạnh chung của hai ô bị vẽ hai lần trong PDF nên bước này bắt buộc.
4. **Nối thành nét liền:** các cạnh gặp nhau (cách < 0,35 mm) nối đuôi, ở ngã ba / ngã tư **ưu tiên đi thẳng**, chỗ rẽ vuông dựng **đúng giao điểm** đường ngang và đường dọc (góc vuông sắc). Quá 3000 cạnh thì bỏ bước này.
5. Sắp thứ tự láng giềng gần nhất (có đảo chiều).

### 4.8 Ảnh trong trang (`images.py`)
Mỗi khung ảnh (≥ 3 mm mỗi cạnh) được **nhận diện** rồi đi một trong hai đường (`image_kind` = `auto`, mặc định):

| Loại ảnh | Nhận diện (`classify`, thử ở 100 dpi) | Cách vẽ | Lớp |
|---|---|---|---|
| **Hình vẽ nét**: sơ đồ khối, mạch điện, đồ thị, công thức hoặc ký hiệu Hy Lạp lưu dạng ảnh | ≥ **70 %** điểm ảnh gần trắng (> 200) **và** ≤ **20 %** điểm xám trung gian (64–192) | lấy **đường giữa nét** như chữ: kết xuất khung ở `skeleton_dpi` → làm mịn Gauss 0,25 mm → nhị phân → skeleton → dò nét (`text.skeleton_strokes`) | cùng bút và cùng tệp G-code với chữ (`lineart_with_text` = bật); tắt thì thành lớp ảnh |
| **Ảnh chụp, ảnh nhiều tông** | còn lại | cắt từ trang ở `image_dpi` (150), chạy `drawing.raster.build_raster` với kiểu Đan chéo (hoặc kiểu đã chọn), bút ảnh, trong đúng khung; nét tịnh tiến về vị trí trên trang | lớp ảnh riêng (bút tô, tệp G-code riêng) |

**Vì sao phải nhận diện:** lần đầu thử PDF thật 32 trang, **sơ đồ và mạch điện gần như mất hết** (kiểu tô theo độ tối, mà hình nét đen trên nền trắng gần như không có vùng tối), trang 7 ảnh mất 10 s. Có đường lấy nét: hiện đủ, < 1 s. Ngưỡng đo trên PDF này: sơ đồ trắng 0,82–0,96 / xám 0,03–0,11; ký hiệu 6 mm trắng 0,75–0,84 / xám 0,11–0,16. Ép kiểu bằng `image_kind` (`lineart`, `crosshatch`, `flow`, `wave_am`, `spiral`, `outline`) khi nhận diện sai.
**Chạy ngay trong tiến trình hiện tại** (không tách tiến trình con như tab Tạo bản vẽ), nên giữ `image_dpi ≤ 300`; nhận diện và lấy nét hình vẽ không tốn đáng kể.

### 4.9 Đóng gói (`service.py`)
- **Lớp 1** `1-141414` "Chữ và đường kẻ" (bút bi), **lớp 2** `2-067a4e` "Ảnh" (bút tô). Mã lớp có màu như các lớp khác, nên tên tệp G-code tách theo lớp.
- Khung = cả trang (mm). Thông tin có thêm `beta` (số ký tự đã vẽ bằng nét đơn / skeleton / dự phòng, số dòng, số nét đường kẻ, số khung ảnh) và `timings` (read, style, optimize).
- Trang không có gì để vẽ → lỗi `empty_drawing`; quá điểm tối đa → `too_many_points`.

## 5. Thư viện và giấy phép
| Thư viện | Dùng ở | Giấy phép | Ghi chú |
|---|---|---|---|
| **PyMuPDF** (`pymupdf==2.1`) | `reader.py` (đọc ký tự, đường kẻ, ảnh, kết xuất) | **AGPL-3.0** hoặc thương mại (Artifex) | Chọn vì đọc được **cấu trúc** (chữ, cỡ, font, hình chữ nhật) rất nhanh (0,01 s / trang). Đề tài nghiên cứu nên dùng được. **Không phải tư vấn pháp lý:** nếu sau này đóng gói bán, hoặc mở dịch vụ qua mạng cho người ngoài, cần xem lại điều khoản AGPL; khi đó chỉ phải viết lại `reader.py` (mục 10). |
| vpype (1.15.0) | `fontdata.py` (chỉ lấy dữ liệu font Hershey) | **MIT** (đã kiểm trong gói đang cài; báo cáo tra cứu ngoài ghi GPL là **sai**) | đã có sẵn trong dự án |
| scikit-image, OpenCV, NumPy | skeleton, cắt / kết xuất | BSD / Apache / BSD | đã có sẵn |
| pypdfium2 | không dùng | Apache-2.0 / BSD-3 | đã thử 22/11: kết xuất nhanh (0,02 s) nhưng đọc cấu trúc kém hơn; giữ làm phương án thay PyMuPDF |

Cài đặt: `requirements.txt` có `pymupdf`; **phải cài vào đúng Python mà `launcher\start.ps1` chạy** (ưu tiên `backend\.venv`, nếu không có mới `Python\python.exe` mang theo): `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`; `Cap nhat.bat` tự cài khi tệp này đổi (cần Internet). Thiếu thư viện thì tab báo rõ ("chạy `pip install pymupdf`"), phần mềm vẫn chạy bình thường.

## 6. Quyết định và lý do
Ở [09](09_QUYET_DINH_THIET_KE.md) P47. Tóm tắt: viết lại bằng font nét đơn vì skeleton làm mất dấu và đứt nét (mục 7); đặt chữ theo từ cho nhịp đều; đường kẻ từ vector cho thẳng và ít nhấc bút; hai lớp vì hai bút; giao bản vẽ qua sự kiện để không import view khác; tách riêng để dễ gỡ (mục 10).

## 7. Số đo (trang mẫu: tiêu đề 20 / 18, chữ 14, bảng 3×3, khung, thử dấu; ~510 ký tự; máy phát triển)
| Cách | Số nét (≈ lần nhấc bút) | Độ dài vẽ | Ước thời gian vẽ* | Giây dựng nét | Chất lượng |
|---|---|---|---|---|---|
| skeleton 300 dpi (thử trước khi làm) | 1429 | 4,4 m | 7 phút | ~0,5 | **kém**: đứt nét, mất dấu |
| Nét đơn, font Times | 2530 | 8,2 m | 12 phút | ~1,0 | đọc rõ, hơi đặc |
| **Nét đơn, chữ viết tay nối nét (mặc định)** | **578** | 7,0 m | **4 phút** | ~2 | đọc rõ khi phóng to, như viết tay, nét đều |
| Nét đơn, chữ rời gọn (`simplex`) | 1152 | 5,6 m | 6 phút | ~0,9 | đọc rõ, nhịp đều, hơi "máy" |
| Hỗn hợp (chữ ≥ 17 pt skeleton) | 1204 | 5,1 m | 6 phút | ~1,0 | tiêu đề giữ hình gốc |
\* 0,25 s mỗi lần nhấc / hạ + 8000 mm/phút (cả đường di chuyển); ước, không phải đo bằng máy.
**Chưa đo trên MiniPC i5-6100T; chưa in giấy.**

### 7b. PDF thật: "Đáp án đo lường" (32 trang, Times New Roman, có sơ đồ, mạch điện, công thức; máy phát triển)
| Việc | Kết quả |
|---|---|
| Chạy đủ 32 trang | **không lỗi trang nào**; mỗi trang 0,0–1,0 s (sau khi thêm đường hình vẽ nét; trước đó trang nhiều ảnh mất 10 s) |
| Số nét mỗi trang | chữ viết tay nối nét (mặc định): **184–1081**; chữ rời gọn: 365–2593 (trang kín chữ ~1700–2500) |
| Ước thời gian vẽ mỗi trang | chữ viết tay nối nét: **1–7 phút, cả 32 trang ước ~2,4 giờ**; chữ rời gọn: 2–13 phút, ~4–5 giờ (0,25 s mỗi lần nhấc / hạ + 8000 mm/phút; chưa tính đổi bút) |
| Ký tự font không có (rơi về skeleton) | 0–60 mỗi trang; nhiều nhất ở trang công thức (Hy Lạp, √, ∫, Σ…) |
| Ảnh | sơ đồ khối, mạch điện, công thức dạng ảnh, ký hiệu Hy Lạp 6 mm đều vẽ được (hình nét); xem ảnh so sánh trang 2 và 11 |
| Chưa tốt | ký hiệu toán (∫, √, Σ, Hy Lạp) vẽ bằng skeleton; chữ nhỏ trong hình đứt nét; công thức nhiều tầng chưa kiểm kỹ trên giấy |
Nhận xét về độ đậm: chữ 12–13 pt bằng bút 0,5 ra khá **đặc** (x-height ~2,2 mm, nét 0,5 mm). Nên thử bút 0,38–0,40 cho chữ thân bài; con số chính xác phải xem trên giấy.

## 8. Hằng số (đặt đầu mỗi tệp, có chú thích tiếng Việt)
| Hằng số | Giá trị | Tệp | Ý nghĩa |
|---|---|---|---|
| `TIMES_CAP_RATIO` | 0,662 | fontdata | chiều cao chữ hoa / cỡ chữ của Times New Roman |
| `SLANT` / `SIMPLEX_SLANT` | 0,2 | viet / fontdata | độ nghiêng chữ nghiêng và dấu |
| `MARK_LEVEL1` | 3,2 | viet | tâm dấu mũ / trăng cách đỉnh chữ |
| `TONE_PLAIN` / `TONE_CIRC` / `TONE_BREVE` | bảng mục 4.3 | viet | vị trí dấu thanh |
| `DOT_BELOW` | 3,2 | viet | dấu nặng dưới chân |
| `HORN`, `D_BAR` | xem mã | viet | râu ơ ư, gạch đ |
| `FAMILY_SCALE` (script) | 0,85 × 1,1 | fontdata | co giãn ngang × dọc font viết tay |
| `CONNECT_UNITS`, `BODY_TOL`, `ATTACH_TOL`, `ATTACH_MIN_LEN`, `DOT_MIN` | 10 · 1,6 · 6,5 · 5,0 · 0,5 | text | nối chữ thành một nét (mục 4.4b) |
| `WORD_FIT_MIN`, `WORD_FIT_MAX` | 0,55 · 1,25 | text | từ co / giãn đều tối đa so với nhịp tự nhiên |
| `FIT_MIN` | 0,55 | text | co ngang tối đa của chữ đứng riêng (gạch dài) |
| `HORN_EXTRA` | 2,0 | viet | râu làm ô chữ rộng thêm |
| `LINE_TOL` | 0,45 | text | dung sai cùng dòng (× cỡ chữ) |
| `RUN_GAP_EM` | 1,5 | text | khoảng trống cắt đoạn |
| `SKEL_*` | 0,4 · 0,95 · 0,32 · 0,3 | text | lề, vùng cắt, bỏ nét ngắn của skeleton |
| `JOIN_MM` / `join_mm` | 0,25 | pathing / tham số | nối nét hở dưới mức này |
| `THIN_RECT_PT` | 2,0 | reader | hình chữ nhật mỏng hơn là đường kẻ |
| `THICK_FACTOR`, `MAX_OFFSET_MM` | 1,5 · 1,0 | frame | khi nào vẽ hai đường, lệch tối đa |
| `AXIS_TOL_MM`, `SAME_LINE_MM`, `TOUCH_MM`, `JOIN_TOL_MM` | 0,25 · 0,3 · 0,3 · 0,35 | frame | gộp và nối đường kẻ |
| `MAX_EDGES_TO_CHAIN` | 3000 | frame | quá mức này bỏ bước nối |
| `MIN_SIDE_MM` | 3,0 | images | khung ảnh nhỏ hơn bỏ qua |
| `LINEART_WHITE`, `LINEART_MID`, `PROBE_DPI` | 0,70 · 0,20 · 100 | images | ngưỡng nhận diện hình vẽ nét, độ phân giải thử |
| `LINEART_BLUR_MM`, `BLUR_THRESHOLD_DROP` | 0,25 · 20 | images / text | làm mịn ảnh hình vẽ nét trước khi lấy nét (thử 0 / 0,25 / 0,45 mm: 156 / 115 / 41 nét, mức 0,45 mất nét mảnh) |
| `MAX_PDF_BYTES`, `MAX_PAGES` | 40 MB · 500 | reader | giới hạn bảo vệ |

Tham số người dùng (`options.py`, một nơi, có đơn vị): `page`, `text_mode` (`single` / `skeleton` / `mixed`), `font` (`script` mặc định / `simplex` / `times`), `mixed_min_pt` 17, `pen_mm` 0,5, `frame`, `thick_double`, `images`, `image_kind` (`auto` mặc định, `lineart`, hoặc một kiểu tô), `lineart_with_text` (bật), `image_pen_mm` 0,4, `image_dpi` 150, `skeleton_dpi` 600, `skeleton_threshold` 190, `join_mm` 0,25, `glyph_fit` 0,92.

## 9. API (chỉ quản lý)
| Phương thức, đường dẫn | Việc |
|---|---|
| `POST /api/beta/pdf/upload` | tải PDF một lần → `{doc, name, pages, sizes}` (giữ 2 tệp gần nhất trong RAM) |
| `GET /api/beta/pdf/schema` | khai báo tham số |
| `GET /api/beta/pdf/{doc}/page/{n}/preview.png?dpi=` | ảnh trang gốc |
| `POST /api/beta/pdf/import` | `{doc, options}` → 202 `{task}`; theo dõi bằng `GET /api/draw/tasks/{task}` (cùng cơ chế nền, hủy được); kết quả dùng được với `/api/draw/preview`, `/api/draw/gcode`, bản thảo |
Mã lỗi mới: `pdf_engine_missing`, `bad_pdf`, `pdf_encrypted`, `too_many_pages`, `unknown_pdf`. Cảnh báo mới: `beta_page_rotated`, `beta_rotated_text`, `beta_filled_areas`, `beta_missing_chars`, `beta_fallback_chars`, `beta_image_skipped` (khóa dịch `drawing.error.*` / `drawing.warning.*`).

## 10. Cách gỡ (hoặc thay phần đọc PDF)
**Gỡ hẳn tính năng** (phần còn lại không bị ảnh hưởng):
1. Xóa `backend/app/services/beta_pdf/`, `backend/app/api/beta_pdf.py`, `backend/tests/beta_pdf/`.
2. `backend/app/api/__init__.py`: bỏ dòng import `beta_pdf_router` và tên trong `ROUTERS`.
3. `frontend/`: xóa `js/views/beta/`, `css/beta.css`, `tests/beta.test.mjs`; trong `index.html` xóa khối `BETA:TAB`, khối `BETA:START … BETA:END` và dòng `<link>` có chú thích BETA; trong `js/app.js` bỏ `import { initBeta }` và `initBeta();`; trong `js/core/api.js` bỏ ba hàm `betaPdf*`; trong `js/views/drawing.js` bỏ khối `extruxy:beta-task`.
4. `locales/vi.json`, `en.json`: xóa các khóa `nav.beta`, `beta.*`, `drawing.error.pdf_*` / `too_many_pages` / `unknown_pdf`, `drawing.warning.beta_*` (nằm liền một khối cuối tệp).
5. `backend/requirements.txt`: bỏ `pymupdf`. Xóa tài liệu này và các dòng nhắc trong 01, 09, 10, 11, AI_START.
**Chỉ thay PyMuPDF:** viết lại `reader.py` (giữ `PdfDoc`, `Char`, `Segment`, `ImageBox`, `PageContent`, `read_page`, `render_gray`, `render_png`, `page_sizes`); phần còn lại không đổi.
**Gộp vào dự án chính:** phần cần chạm vào chỉ có 4 chỗ nhỏ ở bước 2–3 (đã đánh dấu BETA).

## 11. Giới hạn đã biết
- Chữ xoay / dọc: bỏ qua. Trang xoay (`/Rotate`): cảnh báo, chữ có thể lệch.
- Công thức toán, ký hiệu, chữ ngoài Latin: rơi về skeleton từng ký tự (nhìn được nhưng không đẹp), xem cảnh báo `beta_fallback_chars`.
- Khối tô nền, tô màu, bóng: không vẽ (cảnh báo `beta_filled_areas`).
- Chữ trắng trên nền tối: màu gần trắng bị coi là không có mực ở đường kẻ; ở chữ nét đơn vẫn vẽ như chữ thường.
- Ảnh chụp trong trang chạy trong tiến trình chính (không tách tiến trình con): ảnh lớn có thể làm giật máy.
- Hình vẽ nét lấy đường giữa nét nên mũi tên đặc thành một nét. **Chữ nhỏ nằm trong hình** (nhãn sơ đồ) chỉ cao ~10 điểm ảnh nên skeleton ra nét nguệch ngoạc; muốn đẹp phải nhận dạng chữ (OCR) rồi viết lại: chưa làm (mục 1, giai đoạn 8).
- Mỗi lần chỉ nạp **một trang**; chưa có "tạo tất cả trang".
- Font Hershey chỉ có kiểu Times / sans / viết tay; font lạ vẫn được vẽ bằng kiểu gần nhất. Họ viết tay bỏ đậm, nghiêng; tiêu đề chỉ khác cỡ.
- Chữ viết tay nhìn **đặc ở khung xem trước nhỏ** vì nét 0,5 mm chỉ còn 1–2 điểm ảnh (dùng zoom); chữ thường chỉ cao ~1,7 mm nên với bút 0,5 vòng của e, l có thể kín: thử bút 0,38–0,40.
- Chưa in giấy: độ đọc được của chữ 14 pt với bút 0,5 phải xem trên giấy.

## 11b. Soạn font riêng trong ứng dụng (kế hoạch ĐÃ CHỐT 22/11/2026, **chưa làm**)

### Quyết định của chủ dự án
| Việc | Chốt |
|---|---|
| Soạn ở đâu | **ngay trong tab Beta** (trang "Soạn font"), không cần phần mềm ngoài; vẫn có nút xuất / nhập tệp để sao lưu, chia sẻ, gộp vào dự án |
| Dụng cụ | **chuột** trước; **bút cảm ứng** sau khi mở được web từ xa (Cloudflare, [08](08_TRIEN_KHAI.md) mục F) |
| Phạm vi | **một bộ font** trước; **biến thể** mỗi chữ (2–3 bản, xen kẽ để các chữ giống nhau không y hệt) làm sau |
| Quy trình | xuất font vpype ra tệp → chủ dự án sửa trong trang Soạn font → bộ xếp chữ **nạp thẳng tệp đó** |
| Khi chưa có tệp, hoặc thiếu một chữ | **vẫn lấy thẳng từ vpype** (không bao giờ lỗi vì thiếu font riêng) |
| Nguồn | ghi **đầy đủ** nguồn gốc, và **ghi cả chỗ đã sửa** (mục dưới) |
| Tên font | chưa đặt; đề nghị "Chữ tay VMU" (đổi được) |

### Font single-line gồm những gì (để hiểu cái sẽ sửa)
Font thường (Times) lưu **hình đặc** của chữ (vành ngoài khép kín); bút bi vẽ theo vành đó ra hai đường. Font **single-line** lưu **đường mà đầu bút đi qua**, như cách viết tay; độ dày nét do bút quyết định nên không có đậm / nhạt.
| Thành phần | Ý nghĩa | Ví dụ chữ "o" của font hiện tại |
|---|---|---|
| **Nét** | một lần hạ bút = danh sách điểm (x, y) nối nhau | 1 nét, vài chục điểm |
| **Thứ tự và hướng nét** | bút đi từ đâu trước; quan trọng khi nối chữ | bắt đầu ở đỉnh, đi vòng, kết thúc bên phải |
| **Đường mốc** | đường cơ sở, chiều cao chữ thường, chữ hoa, chữ có đuôi; mọi tọa độ tính theo đó | chữ thường cao 9 đơn vị (trước co giãn 0,85 × 1,1) |
| **Ô chữ** | mép trái `lt`, mép phải `rt` = chữ rộng bao nhiêu | từ −6 đến 8 |
| **Điểm vào và ra** | đầu và cuối nét; chữ kế tiếp bắt đầu đúng độ cao đó thì nối liền | điểm ra (8, 4) |
| **Nét phụ** | chấm của i, gạch ngang của t; viết sau cả từ | |
| **Dấu** | các nét nhỏ (mũ, trăng, sắc, huyền, hỏi, ngã, nặng); vị trí tính theo chiều cao chữ, râu ơ ư và gạch đ tính theo quy tắc | |
| **Biến thể** (sau) | nhiều bản mỗi chữ | chưa có |

### Tệp font (kế hoạch định dạng)
`data/fonts/<tên>.json` (không lên Git, như bản thảo):
- `format`, `name`, ngày tạo;
- `sources`: nguồn gốc và giấy phép (mục dưới);
- `glyphs`: mỗi ký tự ASCII in được (33–126): `lt`, `rt`, `strokes` (danh sách nét, mỗi nét là điểm [x, y], y so với đường cơ sở, âm = phía trên), `solo` (chữ in đứng riêng: chữ hoa và số), `origin` (`vpype` hoặc `edited`), ngày sửa;
- `marks`: hình các dấu (mũ, trăng, sắc, huyền, hỏi, ngã, nặng) quanh tâm (0, 0);
- `log`: nhật ký sửa (chữ nào, lúc nào, sửa hay trả về chữ gốc).
Chữ có dấu tiếng Việt **không lưu riêng**: vẫn ghép từ chữ gốc + dấu (mục 4.3) nên sửa chữ gốc và hình dấu là đủ cho mọi chữ.
Giới hạn bảo vệ: tối đa 12 nét mỗi chữ, 300 điểm mỗi chữ, tọa độ trong ±60, `rt` > `lt`.

### Nạp và dự phòng
- Thêm họ font `mine` ("Chữ tay VMU") vào `fontdata.FAMILIES`, chạy như `script` (nối nét, chữ hoa và số kiểu in).
- Mỗi ký tự: có trong tệp thì dùng; **không có tệp hoặc thiếu ký tự thì lấy thẳng vpype `script`**.
- Tệp đổi (theo giờ sửa) thì tự nạp lại, không cần khởi động lại; ô chọn font ở tab Beta có thêm lựa chọn này.

### Trang Soạn font (giao diện, chuột)
- **Chọn chữ:** lưới a–z, A–Z, 0–9, dấu câu, và các dấu; chữ đã sửa có đánh dấu. Chữ có dấu tiếng Việt không có nút riêng (ghép từ chữ gốc).
- **Khung phóng to** có đường mốc (cơ sở, chữ thường, chữ hoa, đuôi), hai mép ô chữ kéo được, mỗi nét hiện thứ tự, điểm đầu (xanh) và điểm cuối (đỏ).
- **Công cụ:** kéo điểm · thêm điểm · xóa điểm · **vẽ lại nét** bằng chuột (tự làm gọn bớt điểm thừa) · đảo chiều nét · xóa nét · hoàn tác / làm lại.
- **Câu thử** bên cạnh, cập nhật ngay khi sửa, xem chữ nối nét và dấu đúng chỗ.
- **Trả về chữ gốc** (quay lại chữ vpype cho riêng chữ đó); **Lưu**.
- Chỉ quản lý dùng (route mới mặc định chỉ quản lý).
- Bút cảm ứng, viết cả chữ bằng ngón tay: để sau, cùng khung này (sự kiện con trỏ đã dùng chung chuột và bút).

### Ghi nguồn
1. **Đầu tệp font** (`sources`): gói vpype (giấy phép MIT, © Antoine Beyeler & Contributors) và bộ chữ **Hershey** mà vpype dùng, kèm: bản vpype đã dùng (1.15.0), mã chuyển bộ chữ lấy từ dự án `axi` của Michael Fogleman (MIT; vpype ghi ở đầu `text.py`).
2. **Nhật ký sửa** theo từng chữ: chữ nào đã sửa, ngày, hành động; chữ không có trong nhật ký là còn nguyên từ vpype.
3. **Trang Soạn font** có mục "Nguồn và giấy phép"; tài liệu này và `README` của tính năng ghi lại.
**Việc phải làm trước khi viết tệp font (chưa xong):** tìm **nguyên văn** thông báo của bộ chữ Hershey. Đã kiểm 22/11/2026: gói vpype 1.15.0 chỉ ghi nguồn `axi` ở đầu `text.py`, còn `LICENSE_THIRD_PARTY` của vpype **không nhắc Hershey hay axi**; theo trí nhớ của AI, điều kiện của Hershey là dùng tự do nhưng phải kèm lời ghi nguồn (Dr. A. V. Hershey; định dạng dữ liệu của James Hurt), **chưa kiểm chứng nguyên văn**. Cần tra bản gốc (hoặc dự án `axi`) rồi chép đúng, không diễn đạt lại thành "giấy phép".

### Các bước làm
| Bước | Việc | Kiểm chứng |
|---|---|---|
| 0 | tra nguyên văn thông báo Hershey và nguồn `axi`; chốt chữ ghi nguồn | có trích dẫn nguyên văn trong tệp và docs |
| 1 | `customfont.py`: định dạng tệp, **xuất font từ vpype** (cả hình dấu), kiểm hợp lệ, lưu an toàn (ghi tạm rồi đổi tên, giữ bản trước), nhật ký | test: xuất rồi nạp lại ra đúng glyph vpype; tệp sai bị từ chối |
| 2 | họ font `mine` trong `fontdata` / `viet`; dự phòng vpype theo từng ký tự | test: không có tệp thì kết quả **giống hệt** `script`; sửa một chữ thì chỉ chữ đó đổi; thiếu một chữ vẫn chạy |
| 3 | API `/api/beta/font/…`: tạo từ vpype, xem, lưu / trả về từng chữ và từng dấu, xuất, nhập, xem thử câu | test API, quyền chỉ quản lý |
| 4 | trang Soạn font (chuột), câu thử, nhật ký, mục nguồn | thử bằng trình duyệt thật; test hàm thuần (làm gọn nét, thêm / xóa điểm, hoàn tác) |
| 5 | nút xuất / nhập tệp font | thử qua lại hai máy |
| Sau | biến thể mỗi chữ; bút cảm ứng và viết cả chữ bằng ngón tay (sau khi có web từ xa) | |

### Rủi ro và việc chưa quyết
- Hình dấu và vị trí dấu chưa kiểm hết trên giấy; trang Soạn font giúp chủ dự án tự sửa.
- Sửa một chữ cái có thể làm chỗ nối với chữ kế bên bị lệch: câu thử phải hiện rõ chỗ nối (điểm vào / ra).
- Nhiều người cùng sửa một tệp trên nhiều máy: chưa tính (một tệp, ghi đè bằng bản mới nhất; có bản trước đó).
- Tên font chưa đặt.

## 12. Test
- `backend/tests/beta_pdf/test_viet_glyphs.py`: đủ 146 chữ Việt, vị trí dấu, ì / ị, đ, râu, chữ nghiêng, kích thước font.
- `test_layout_pieces.py`: tham số, nối nét, sắp nét, đường kẻ (gộp, góc vuông, lưới, hai đường), xếp chữ (căn ô, co ngang, cỡ, dòng, đoạn), skeleton và hỗn hợp bằng bộ kết xuất giả.
- `test_service_and_api.py` (cần PyMuPDF, thiếu thì bỏ qua): PDF thật tạo trong test (chữ, bảng, ảnh, nhiều trang): đọc, dựng lớp, lưu bản vẽ, tạo G-code qua `/api/draw/gcode`, tải / xem / nạp qua API, các lỗi.
- `frontend/tests/beta.test.mjs`: tùy chọn gửi backend, số trang, đường SVG, tổng hợp số liệu; `locales.test.mjs` kiểm khóa dịch.
- Thử bằng trình duyệt thật: tải PDF mẫu, tạo nét, mở ở tab Tạo bản vẽ, tạo G-code; PDF thật 32 trang (mục 7b).
