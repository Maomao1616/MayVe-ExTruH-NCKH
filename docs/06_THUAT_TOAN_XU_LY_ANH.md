# 06 — Thuật toán xử lý ảnh: từ ảnh chụp đến nét bút

> Dành cho người đọc (chủ dự án, người viết báo cáo, người không học lập trình). Đọc từ trên xuống: mỗi mục dựa vào mục trước.
> Mọi con số trong tài liệu lấy từ mã hiện tại (05/11/2026). Mã nằm ở `backend/app/services/drawing/`.
> Muốn biết nút bấm ở đâu: [05_TAB_TAO_BAN_VE.md](05_TAB_TAO_BAN_VE.md). Muốn biết cách thử trên giấy: [07_THU_NGHIEM.md](07_THU_NGHIEM.md).

**Mục lục**
1. Bài toán: máy vẽ chỉ kẻ được đường, không tô được màu xám
2. Cách tư duy để ra dây chuyền
3. Bức tranh tổng thể (sơ đồ)
4. Bước 1 — Đọc ảnh, cắt, thu nhỏ (`raster_in.py`)
5. Bước 2 — Ảnh xám thành bản đồ độ đậm (`tone.py`)
6. Bước 3 — Chia thành đúng N mức sáng tối (`styles.level_plan`)
7. Bước 4 — Mỗi mức thành một mặt nạ đen/trắng (`hatch.level_mask`)
8. Bước 5 — Mặt nạ thành nét: zigzag, sóng, xoắn ốc (`hatch.py`, `styles.py`)
9. Kiểu Viền: ảnh thành đường nét một lượt (`edges.py`, `trace.py`)
10. Nhiều màu (`palette.py`)
11. Tối ưu nét bằng vpype (`optimize.py`)
12. Đặt lên giấy và ra G-code (`layout.py`, `gcode.py`)
13. Máy biết "cách nhau bao nhiêu" bằng cách nào
14. Kiểm tra thuật toán mà không cần in: bộ mô phỏng mực
15. Thư viện đã dùng: mỗi cái làm gì
16. Thư viện và cách làm đã cân nhắc nhưng KHÔNG dùng, vì sao
17. Thư viện và thuật toán có thể thêm để phát triển
18. Giới hạn đã biết

---

## 1. Bài toán: máy vẽ chỉ kẻ được đường, không tô được màu xám

Máy in phun phun được mực đậm nhạt khác nhau. Máy vẽ thì không. Nó chỉ làm được **một việc**: hạ một cây bút xuống giấy rồi kéo đi, để lại một **đường mực rộng cố định** (bút Sakura 0,4 ra nét rộng khoảng 0,55 mm).

Vậy muốn có vùng "xám nhạt", "xám vừa", "gần đen" thì làm sao? Cách duy nhất: **kẻ nhiều đường song song, đường càng sát nhau thì vùng đó càng đậm.** Đứng xa 40–50 cm, mắt không thấy từng đường mà thấy một mảng xám. Đây là cách các họa sĩ khắc đồng, vẽ ký họa bằng bút kim vẫn làm (gọi là *hatching*, gạch nét).

```
Thưa (xám nhạt)      Vừa (xám)          Dày (gần đen)
─────────────        ─────────────      ═════════════
                     ─────────────      ═════════════
─────────────        ─────────────      ═════════════
                     ─────────────      ═════════════
─────────────        ─────────────      ═════════════
```

Một cách khác hẳn là **vẽ theo đường viền** (như tranh tô màu), không cần sáng tối: chỉ cần biết đâu là đường trong ảnh. Dự án có cả hai: **kiểu tô** (zigzag, sóng, xoắn ốc) và **kiểu viền**.

Từ đó ra ba câu hỏi lớn, cũng là ba phần chính của tài liệu:
1. Ảnh có hàng trăm mức xám, máy chỉ kẻ được vài mật độ: **chia thành mấy mức, chia ở đâu?** (mục 6)
2. Mỗi mức phải kẻ các đường **cách nhau bao nhiêu mm** để ra đúng độ đậm? (mục 6, 13)
3. Làm sao biến một vùng trên ảnh thành **các đường bút liền, ít nhấc bút**? (mục 7, 8, 9)

---

## 2. Cách tư duy để ra dây chuyền

Không có thuật toán nào nghĩ ra một lần là đúng. Dây chuyền của dự án được dựng theo bốn bước lặp lại.

### 2.1 Bắt đầu từ giới hạn vật lý, không bắt đầu từ thư viện
| Giới hạn thật | Hệ quả cho thuật toán |
|---|---|
| Bút ra nét rộng cố định ~0,55 mm | Độ đậm = **mật độ nét**. Mọi khoảng cách phải tính bằng **mm thật**, theo bề rộng nét thật |
| Mỗi lần nhấc + hạ bút mất ~0,25 s (bằng quãng vẽ ~20 mm ở 5000 mm/min) | Ưu tiên **nét dài liền** (zigzag nối đầu đuôi), nối qua khe trắng ngắn, bỏ mẩu quá ngắn |
| Ở góc nhọn máy phải giảm tốc gần về 0 (`junction_deviation` 0,01 mm), bút đứng lâu thì mực loang thành giọt | Chỗ quay đầu dùng **nửa vòng tròn**, không dùng hai góc vuông |
| G-code gửi từng dòng, tối đa 200 000 dòng | Giới hạn số điểm (sóng tự giãn bước), đơn giản hóa nét |
| MiniPC i5 thế hệ 3, vừa điều khiển máy vừa xử lý ảnh | Thu nhỏ ảnh **trước** khi lọc; độ phân giải chỉ đủ cho bút; chạy ở tiến trình riêng ưu tiên thấp |
| Chi tiết nhỏ hơn khoảng cách nét thì bút không vẽ nổi | Bỏ đốm và khe nhỏ hơn khoảng cách nét ngay trên ảnh |

### 2.2 Chia thành trạm, mỗi trạm một việc
Với máy tính, **ảnh chỉ là một bảng số** (mỗi ô một điểm ảnh, 0 = đen, 255 = trắng). Hầu hết hàm xử lý ảnh **nhận một bảng số và trả lại một bảng số cùng cỡ**. Vì vào và ra cùng "dạng", ta nối hàm này sau hàm kia như các trạm trên dây chuyền. Mỗi trạm làm đúng một việc nên dễ thử, dễ thay.

### 2.3 Gọi đúng tên vấn đề, rồi tìm công cụ chuẩn cho tên đó
| Vấn đề nhìn thấy | Tên chuẩn (tiếng Anh, để tra) | Công cụ chuẩn |
|---|---|---|
| Vùng xám phải thành các đường | *hatching, halftoning* | đường quét song song + ngưỡng |
| Nét đen dày ra hai đường song song | cần *centerline* (đường giữa) | *skeletonize* |
| Hai mảng khác màu không có viền | *region boundary* | *Canny edge detection* |
| Đỏ cạnh xanh cùng độ sáng mất viền | xét *màu*, không chỉ sáng tối | hệ màu *Lab* |
| Nét bị đứt từng khúc | *gap closing* | *KD-tree* tìm điểm gần nhất |
| Râu nhỏ ở góc nét dày | *spur pruning* | đi dọc nhánh từ đầu mút |
| Bút nhấc nhiều, đi vòng xa | *path optimization, TSP* | vpype `linesort --two-opt` |

### 2.4 Đo, so, chỉnh
1. Thử trên ảnh mẫu, nhìn kết quả.
2. So sánh có số bằng **bộ mô phỏng mực** (mục 14): sai số tông, tổng chiều dài nét, thời gian ước tính.
3. Chỉ chốt khi **in thật trên giấy**, vì màn hình không cho biết mực loang, giấy thấm.

Ví dụ thật: ý "chia 5 mức đều nhau" nghe hợp lý nhưng mô phỏng cho sai số **tệ nhất** (0,147). Cách hiện tại (mục 6) cho 0,071 và nét ngắn hơn 45 %.

---

## 3. Bức tranh tổng thể

```
                         ┌──────────────────── Trình duyệt ────────────────────┐
Ảnh gốc (JPG/PNG/WEBP) ─►│ cắt vùng, thu nhỏ về đúng cỡ cần (lib/imageprep.js) │─► gửi lên máy chủ
                         └─────────────────────────────────────────────────────┘
Máy chủ (tiến trình con ưu tiên thấp, isolated.py):
 (1) raster_in  đọc ảnh, xoay theo EXIF, cắt, thu nhỏ        → ảnh xám (+ ảnh màu nếu cần)
 (2) tone       tự cân sáng, mức đen/trắng, gamma, CLAHE     → BẢN ĐỒ ĐỘ ĐẬM 0..1
 (3) styles     chọn kiểu:
      ├─ TÔ (zigzag / sóng / xoắn ốc)
      │    level_plan  chia N mức, mỗi mức một khoảng cách nét
      │    level_mask  mỗi mức → mặt nạ đen/trắng đã làm sạch
      │    scan_runs / spiral_runs  đường quét cắt theo mặt nạ
      │    serpentine  nối thành nét liền, quay đầu nửa vòng tròn
      ├─ VIỀN (outline)
      │    edges  nét mực + ranh giới mảng + nối khe + cắt râu → đường mảnh 1 điểm ảnh
      │    trace  đường mảnh → đồ thị → nét liền, làm mượt, bớt điểm
      └─ (tùy chọn) thêm lớp viền lên kiểu tô
 (3b) palette   nhiều màu: chia 2–4 màu, mỗi màu tô riêng một lớp
 (4) optimize   vpype nối nét sát nhau, bớt điểm, bỏ nét ngắn, sắp thứ tự
Sau đó (máy chủ, nhẹ):
 (5) layout     đặt lên tờ giấy (lề, tỷ lệ, xoay, lật)
 (6) gcode      G0 tới đầu nét → hạ bút → G1 qua từng điểm → nhấc bút
```

Tệp điều phối cả dây chuyền: `raster.py` (hàm `build_raster`). SVG đi đường riêng ngắn hơn: `svg_in.py` (vpype đọc SVG thành nét) rồi nhập vào bước (4).

---

## 4. Bước 1 — Đọc ảnh, cắt, thu nhỏ (`raster_in.py`)

**Thứ tự đã chốt:** xoay theo EXIF → cắt → thu nhỏ → (sau đó mới) lọc sắc độ và tạo nét.

Vì sao thu nhỏ **trước** khi lọc: chi phí mọi phép lọc tỷ lệ với số điểm ảnh. Ảnh điện thoại 4000×3000 = 12 triệu điểm. Nếu lọc trước, máy làm việc gấp 10–20 lần mà kết quả gần như không khác, vì bút không vẽ nổi chi tiết nhỏ hơn bề rộng nét.

### 4.1 Cỡ ảnh làm việc
```
cạnh dài (điểm ảnh) = cạnh dài khung vẽ (mm) ÷ bề rộng bút (mm) × 1,3     (kẹp 400 … 4000)
```
Ví dụ khung A4 trong lề (287 mm), bút 0,4: 287 ÷ 0,4 × 1,3 ≈ **933 điểm ảnh** → mỗi điểm ảnh ≈ **0,31 mm**.

- Hệ số 1,3 (`OVERSAMPLE`) = "mỗi bề rộng bút có 1,3 điểm ảnh": đủ để ranh giới các vùng không răng cưa.
- Ảnh gốc nhỏ hơn cỡ cần: chỉ phóng nhẹ (bicubic) tới tối đa 720 điểm (`UPSCALE_TO_PX`). Phóng nhiều hơn không thêm chi tiết.
- Độ phân giải chỉ ảnh hưởng **thời gian xử lý**. Thời gian **vẽ** do tổng chiều dài nét và số lần nhấc bút quyết định.

### 4.2 Các bước nhỏ
| Việc | Hàm thư viện | Vì sao |
|---|---|---|
| Mở ảnh, chặn ảnh > 60 triệu điểm | `PIL.Image.open`, `Image.MAX_IMAGE_PIXELS` | chống "bom giải nén" làm tràn RAM |
| Giải mã JPEG nhỏ ngay từ đầu | `Image.draft` | ảnh 12 MP chỉ giải mã ở cỡ cần, rẻ RAM |
| Xoay theo hướng chụp | `ImageOps.exif_transpose` | ảnh điện thoại thường lưu nằm ngang kèm cờ xoay |
| Nền trong suốt thành trắng | `Image.alpha_composite` | PNG sticker có nền trong suốt |
| Cắt vùng (tỷ lệ 0..1 của ảnh gốc) | `Image.crop` | người dùng kéo vùng cắt trên web |
| Thu nhỏ | `Image.resize` với `BOX` (thu nhiều), `LANCZOS` (thu vừa), `BICUBIC` (phóng) | mỗi cách hợp một trường hợp: `BOX` lấy trung bình vùng, không gây nhiễu |
| Ra ảnh xám (và ảnh màu nếu cần viền / nhiều màu) | `convert("L")`, `convert("RGB")` | |

**Kích thước thật (mm):** ảnh đã cắt được đặt gọn trong khung vẽ, giữ tỷ lệ. Từ đó biết mỗi điểm ảnh bao nhiêu mm. Đây là gốc của mọi phép tính "cách nhau bao nhiêu mm" ở sau.

Trình duyệt làm trước một phần (`frontend/js/lib/imageprep.js`): thu nhỏ ảnh về đúng cỡ trên trước khi gửi, nên ảnh 3600×4800 gửi lên chỉ còn ~650×866. Công thức trùng với Python và có test đối chiếu. Máy chủ vẫn tự làm lại được nếu trình duyệt không làm.

---

## 5. Bước 2 — Ảnh xám thành bản đồ độ đậm (`tone.py`)

**Đầu vào:** ảnh xám, mỗi điểm 0 (đen) … 255 (trắng).
**Đầu ra:** *bản đồ độ đậm*, mỗi điểm một số thực **0 … 1**, với **1 = cần nhiều mực nhất**. Đảo chiều so với ảnh xám vì ta quan tâm "mực", không quan tâm "ánh sáng".

| # | Bước | Công thức / hàm | Ô trên giao diện |
|---|---|---|---|
| 1 | Khử nhiễu hạt (tùy chọn, chậm) | `cv2.fastNlMeansDenoising(h=7)` | Khử nhiễu |
| 2 | Tự cân sáng | lấy điểm sáng ở phần trăm 1 và 99 (`np.percentile`), kéo giãn ra 0..255. Ảnh gần một màu (chênh < 16) thì bỏ qua để khỏi khuếch đại nhiễu | Tự cân sáng |
| 3 | Mức đen / trắng | `x = (ảnh − đen) / (trắng − đen)`, kẹp 0..1 | Mức đen, Mức trắng |
| 4 | Gamma | `x = x^(1/gamma)`. Gamma > 1 làm sáng vùng giữa | Gamma |
| 5 | Cân bằng sáng cục bộ (tùy chọn) | `cv2.createCLAHE(clipLimit=2, tileGridSize=8×8)`: cân bằng từng ô nhỏ, chỗ tối sáng lên mà chỗ sáng không cháy | CLAHE |
| 6 | Đảo thành độ đậm | `độ đậm = 1 − x` (ô Đảo sáng tối thì đảo lại lần nữa) | Đảo sáng/tối |

Ví dụ: một điểm xám 191 trong ảnh đã cân sáng, gamma 1 → x = 191/255 = 0,75 → **độ đậm 0,25** (xám nhạt).

Kết quả vẫn là **số liên tục**, chưa chia mức. Việc chia mức nằm ở bước sau.

---

## 6. Bước 3 — Chia thành đúng N mức sáng tối (`styles.level_plan`)

Đây là trả lời câu hỏi "tách ảnh xám nhiều bậc thành đúng 5 mức thế nào".

### 6.1 Công thức độ phủ
Kẻ các nét rộng `w` cách nhau `s` (tính từ tâm nét này tới tâm nét kia). Trên mỗi đoạn dài `s` có `w` là mực, phần còn lại là giấy:
```
độ phủ = w ÷ s          ⇔         s = w ÷ độ phủ
```
Với `w` = 0,55 mm: cách 1,1 mm phủ 50 %; cách 0,61 mm phủ 90 %; cách 2,44 mm phủ 22,5 %.

`w` lấy từ bề rộng nét **đo thật**: `w = LINE_WIDTH_RATIO × số trong ô "Bút vẽ"`. 03/11/2026 Sakura 0,4 trên giấy thường ra 0,55 mm (1,375, các bảng số trong mục này tính theo số đó). 11/11/2026 giấy Ivory: 1,1 → w = 0,44 mm. **Cùng ngày (tối): `LINE_WIDTH_RATIO = 1,0`, ô "Bút vẽ" chọn theo tên bút và mang sẵn nét đo trên giấy** (UB-155 / UM-100 0,30 · Sakura 0,45 · bút bi 0,50, ước tính chờ đo). Sakura 0,45: 4 mức cách 2,0 / 1,0 / 0,67 / 0,50 mm; nét 0,30: 1,33 / 0,67 / 0,44 / 0,33 mm (nhiều đường hơn ~50 %, vẽ lâu hơn tương ứng).

### 6.2 Chia mức
"N mức" gồm cả **mức 0 = giấy trắng (không vẽ)**. Với N = 5 thì có 4 mức có mực. Độ phủ mục tiêu **tăng đều** từ 0 tới 90 % (`MAX_COVERAGE = 0.9`). Không lên 100 % vì nét quá sát sẽ nhòe thành một mảng ướt, giấy quăn.

```
độ phủ bậc k = 0,9 × k ÷ (N − 1)          k = 0, 1, …, N−1
ranh giới giữa bậc k−1 và k = trung bình hai độ phủ đó
khoảng cách nét bậc k = w ÷ độ phủ bậc k
```

**Bảng cho N = 5, bút 0,4 (w = 0,55 mm):**

| Bậc | Độ phủ mục tiêu | Khoảng cách nét | Điểm ảnh có độ đậm trong khoảng này thì nhận bậc |
|---|---|---|---|
| 0 | 0 % | không vẽ | dưới 0,1125 |
| 1 | 22,5 % | 2,44 mm | 0,1125 … 0,3375 |
| 2 | 45 % | 1,22 mm | 0,3375 … 0,5625 |
| 3 | 67,5 % | 0,81 mm | 0,5625 … 0,7875 |
| 4 | 90 % | 0,61 mm | từ 0,7875 trở lên |

Vì sao ranh giới nằm **giữa** hai độ phủ: mỗi điểm ảnh nhận bậc có độ phủ **gần độ đậm của nó nhất**. Ví dụ điểm có độ đậm 0,30: gần 22,5 % (lệch 0,075) hơn 45 % (lệch 0,15), nên nhận bậc 1.

**Ô "Khoảng cách nét" trên giao diện:** để trống thì khoảng tham chiếu = 2 × w = 1,1 mm. Gõ số khác (vd 1,3) thì **mọi** khoảng cách trong bảng nhân cùng tỷ lệ (1,3 ÷ 1,1), tức cả bức vẽ nhạt hơn đều. Hàm nhận tham số `scale` cho việc này.

### 6.3 Vì sao chọn cách này (đã so bằng mô phỏng, mục 14)
| Cách | Sai số tông | Tổng chiều dài nét |
|---|---|---|
| Cũ: chồng 3–4 lớp gạch xoay góc, cách 0,8 mm | 0,174 | 4211 mm |
| Thử: 5 ngưỡng chia đều 0,2 / 0,4 / … | 0,147 (tệ nhất) | |
| **Hiện tại: mỗi bậc một dải, một lượt, khoảng cách riêng** | **0,071** | **2331 mm (−45 %)** |

Mỗi chỗ trên giấy **chỉ bị gạch một lượt**, nên ít nét hơn hẳn mà tông lại đúng hơn.

---

## 7. Bước 4 — Mỗi mức thành một mặt nạ đen/trắng (`hatch.level_mask`)

*Mặt nạ* = một bảng cùng cỡ ảnh, mỗi ô chỉ có **Có** (vẽ) hoặc **Không**. Đây chính là "ảnh bin" (nhị phân) đã được làm đẹp.

### 7.1 Tạo mặt nạ "đậm ≥ ngưỡng t" (chạy một lần cho mỗi ranh giới)
| # | Bước | Hàm | Con số (bút 0,4, điểm ảnh 0,31 mm) | Để làm gì |
|---|---|---|---|---|
| 1 | Làm mờ nhẹ | `cv2.GaussianBlur`, σ = 0,35 × 1,1 mm | σ ≈ 1,25 điểm ảnh | ranh giới vùng không lổn nhổn từng điểm |
| 2 | So ngưỡng | `độ đậm ≥ t` (numpy) | | ra bảng Có/Không |
| 3 | Đóng (giãn rồi co) | `cv2.morphologyEx(MORPH_CLOSE)`, nhân hình elip | elip ~5 điểm ≈ 1,5 mm | **bịt khe hẹp** hơn khoảng cách nét (bút không chui vào được) |
| 4 | Mở (co rồi giãn) | `cv2.morphologyEx(MORPH_OPEN)`, cùng nhân | | **xóa đốm nhỏ** hơn khoảng cách nét (bút không vẽ nổi) |

Hình minh họa phép "mở" xóa đốm:
```
trước        co lại        giãn lại (= sau)
· · ■ · ·    · · · · ·     · · · · ·      đốm 1 ô biến mất
■ ■ ■ ■ ■    · ■ ■ ■ ·     ■ ■ ■ ■ ■      mảng lớn giữ nguyên hình
■ ■ ■ ■ ■    · ■ ■ ■ ·     ■ ■ ■ ■ ■
```

Mọi ngưỡng dùng **cùng một cỡ làm mờ** (theo khoảng tham chiếu 1,1 mm), nên các mặt nạ lồng nhau gọn: chỗ đậm ≥ 0,79 thì cũng nằm trong chỗ đậm ≥ 0,56.

### 7.2 Lấy riêng từng dải
```
dải bậc k = (đậm ≥ ranh giới dưới) VÀ KHÔNG (đậm ≥ ranh giới trên)
dải bậc cao nhất = (đậm ≥ ranh giới dưới)
```
Các dải **không chồng nhau**. Hàm `styles._passes` trả lần lượt (mặt nạ dải, góc gạch, khoảng cách nét).

---

## 8. Bước 5 — Mặt nạ thành nét: zigzag, sóng, xoắn ốc, gạch chéo, sóng biến thiên

### 8.1 Đường quét song song (`hatch.scan_runs`), nền của zigzag và sóng
Ý tưởng: kẻ các đường thẳng song song cách nhau `s` mm phủ cả ảnh, rồi **chỉ giữ phần đường nằm trong vùng Có của mặt nạ**.

1. **Xoay hệ trục** theo góc gạch (mặc định 45°): `d = (cos a, sin a)` là hướng dọc đường, `n = (−sin a, cos a)` là hướng vuông góc. Điểm (x, y) có tọa độ mới `u = (x, y)·d` (dọc đường) và `v = (x, y)·n` (đường thứ mấy).
2. **Đặt các đường** ở `v = vmin + i × s`. Khoảng cách `s` được áp ở đây, **bằng mm**.
3. **Lấy mẫu dọc mỗi đường** mỗi 0,7 điểm ảnh (~0,22 mm). Đổi mỗi mẫu về (x, y) mm rồi về ô ảnh, tra mặt nạ (`_lookup`). Làm cả lô cùng lúc bằng numpy (tối đa 2 triệu mẫu một lượt để giới hạn RAM).
4. **Tìm đoạn Có liên tiếp** (`_runs`) bằng mẹo hiệu số: đệm 0 hai đầu, `np.diff` ra +1 ở đầu đoạn, −1 ở cuối đoạn.
   ```
   mẫu:   0 0 1 1 1 1 0 0 1 1 0
   diff:    0 +1 0 0 0 −1 0 +1 0 −1
   →  đoạn 1: mẫu 2…5        đoạn 2: mẫu 8…9
   ```
5. **Bỏ đoạn ngắn hơn 0,3 mm** (`MIN_RUN_MM`): bút không vẽ nổi.

Kết quả: mỗi đường một danh sách đoạn `(u đầu, u cuối)`.

### 8.2 Nối thành zigzag (`hatch.serpentine`)
Nếu mỗi đoạn là một nét riêng, bút phải nhấc hạ hàng nghìn lần. Nên nối như đi cày ruộng:
- Đường chẵn đi trái sang phải, đường lẻ đi phải sang trái.
- Với mỗi đoạn trên đường mới, tìm đoạn của đường trước có **điểm cuối gần điểm đầu đoạn này nhất**, trong giới hạn `max(2,5 × s, 0,8 mm)` (vd s = 1,22 → 3,05 mm). Có thì **nối vào cùng một nét**. Xa hơn thì tách nét mới, vì đường nối sẽ cắt ngang vùng trắng.
- **Chỗ quay đầu là nửa vòng tròn** bán kính `s/2`, 7 điểm (`TURN_POINTS`), khi hai đầu gần thẳng hàng (lệch ≤ 0,7 × bán kính) và hai đoạn đủ dài. Ngược lại thì nối bằng một đoạn chéo ngắn.

Vì sao nửa vòng tròn: ở góc vuông FluidNC phải giảm tốc gần về 0 (với `junction_deviation` 0,01 mm còn khoảng 7 mm/s). Bút đứng lâu ở mép vùng, mực loang thành giọt (thấy rõ trên ảnh thử 03/11). Nửa vòng 7 điểm có mỗi chỗ rẽ ~30°, máy giữ được khoảng 24 mm/s.
```
cũ (góc vuông):  ──────┐        mới (nửa vòng):  ──────╮
                       │                                 )
                 ──────┘                          ──────╯
```

### 8.3 Sóng (`styles.wave`)
Vẫn là đường quét và nối như trên, nhưng mỗi đoạn thẳng được thay bằng đường sin (`hatch.sine_shape`):
```
v' = v + biên độ × sin(2π × u ÷ bước sóng)
biên độ  = 0,18 × s   (tối đa 0,5 × s để hai sóng kề không chạm)
bước sóng = lớn nhất trong { 6 × biên độ ; 6 × cỡ bút ; mức cần để không vượt 100 000 điểm }
mỗi bước sóng lấy 5 điểm
```
Ví dụ s = 1,22 mm: biên độ 0,22 mm, bước sóng = max(1,32; 2,4; …) = 2,4 mm.
Pha sóng tính theo `u` (không theo từng đoạn) nên các sóng kề nhau song song. Ảnh quá đậm thì bước sóng tự dài ra, sóng thưa hơn, nhưng G-code luôn hợp lệ.
Biên độ 0,18 (cũ 0,35) chọn bằng mô phỏng: sai số 0,123 → 0,090.

### 8.4 Xoắn ốc (`hatch.spiral_runs`)
Không kẻ đường thẳng mà dùng **xoắn ốc Archimedes** từ tâm ảnh ra ngoài; khoảng cách giữa hai vòng chính là `s`.
```
bán kính  r = s × θ ÷ 2π              (θ tăng 2π thì r tăng đúng s)
chiều dài cung từ tâm ≈ s × θ² ÷ 4π   ⇒   θ = √(4π × L ÷ s)
```
Lấy mẫu đều theo chiều dài: mẫu thứ k ở `L = k × bước`, nên các mẫu cách đều nhau trên đường.
Sau đó tra mặt nạ, lấy đoạn Có như 8.1, rồi:
- **nối qua khe trắng** ngắn hơn `max(3 mm, 6 × s)` (đỡ một lần nhấc bút),
- **bỏ mẩu** ngắn hơn `max(0,3 mm, 4 × s)` (gần như không thấy).

Mô phỏng: sai số 0,106 → 0,058. Nhưng mỗi bậc cắt xoắn ốc thành nhiều mẩu, nên thời gian vẽ khoảng **gấp đôi zigzag**; preset Cận cảnh vì vậy dùng 4 mức.

### 8.5 Thêm lớp viền lên kiểu tô
Bật "Thêm lớp viền" thì sau khi tô xong, phần mềm chạy thêm kiểu Viền (mục 9) và vẽ lớp viền **sau cùng** để nét rõ.

### 8.6 Thêm kiểu tô mới
Một hàm có dòng `@FILLERS.register("tên")` trong `styles.py` + thêm tên vào `spec.py` (`kind`) + `GROUPERS` nếu muốn vẽ lần lượt từng mức. Không phải sửa chỗ khác (`registry.py`).

### 8.7 Chuyển mức mềm (`soft_levels`, mặc định bật từ 11/11/2026)
**Vấn đề:** chia N mức thì giữa hai mức có một đường ranh giới: một bên gạch thưa, một bên gạch dày, và mọi dòng gạch quay đầu thẳng hàng trên ranh giới đó (máy chậm lại ở chỗ quay đầu, mực đậm hơn) nên lộ thành **đường viền mảng**. Đây đúng là vệt mảng thấy trên tranh con mèo 11/11.

**Cách làm (ordered dithering theo dòng):** dòng gạch thứ i dùng ngưỡng lệch `δ[i mod 8]`, 8 giá trị trải đều trong ±0,9 × nửa bước độ phủ, xếp theo thứ tự đảo bit (0, 4, 2, 6, 1, 5, 3, 7) để hai dòng kề nhau luôn lệch xa nhau (`hatch.dither_offsets`). Mỗi dải có 8 mặt nạ, dòng i tra mặt nạ i mod 8.
Ở chỗ giáp ranh, tỷ lệ dòng của mức nhạt còn lại giảm dần từ 1 về 0, tỷ lệ dòng của mức đậm tăng dần từ 0 lên 1: độ phủ nội suy **tuyến tính** giữa hai mức thay vì nhảy bậc. Phía giáp giấy trắng chỉ lệch một nửa (`SOFT_WHITE`) để vùng gần trắng không có dòng lẻ tẻ.

**Nối nét:** các dòng kết thúc so le nên `serpentine` (chỉ nối dòng kề nhau) vỡ thành từng đoạn (thử: 15 → 171 nét). Kiểu mềm dùng `hatch.join_rows`: nối sang dòng cách 1–8 dòng nếu hai đầu lệch ≤ max(2,5 × s, 0,8 mm) và vòng quay đầu cao ≤ 2 mm (`SOFT_TURN_MM`). Vòng quay đầu cắt bớt hai đầu dòng để đỉnh vòng nằm giữa hai đầu cũ (`_trim_turn`), không lòi ra ngoài.

**Đo (mô phỏng, nét 0,44 mm):** dải chuyển liền: sai tông 0,082 → 0,051, bậc lớn nhất 0,099 → 0,049. Ảnh mèo A5: nhấc bút 496 → 648, thời gian (có gia tốc 3000) 5,7 → 6,3 phút. Tắt ô "Chuyển mức mềm" để quay về cách cũ.

### 8.8 Gạch chéo chồng lớp (`crosshatch`)
Độ phủ mong muốn T tách thành hai lớp a (góc gạch) và b (góc + 90°) sao cho `1 − (1 − a)(1 − b) = T` (`styles.cross_split`): T ≤ 0,45 chỉ lớp a (= T); trên đó a tăng nửa phần, b gánh phần còn lại. T = 0,9: a ≈ b ≈ 0,68, tức mỗi hướng cách ~0,65 mm thay vì một hướng cách 0,49 mm (ít ướt giấy). Mỗi lớp là một lượt zigzag đủ mức (mềm nếu bật); vẽ hết lớp a rồi mới lớp b (mực lớp dưới có thời gian khô). Tốn hơn zigzag ~20 % chiều dài ở ảnh nhiều mảng đậm.

### 8.9 Sóng biến thiên (`wave_am`): tông liền, không chia mức
Các đường sóng **song song**, cách nhau `s0 = 4 × nét thật` (bút 0,4: 1,76 mm), bước sóng **cố định** `λ = 2 × nét thật` (0,88 mm), cùng pha (pha tính từ cùng một gốc) nên không bao giờ cắt nhau. Chỉ biên độ đổi theo độ đậm:
- Đường sóng `v = A·sin(2πu/λ)` dài gấp `F(k)` lần đường thẳng, `k = 2πA/λ` (bảng tra `hatch._F_TAB`). Nét rộng w cách s0 phủ `w·F/s0`. Muốn độ phủ c: `F = c·s0/w` → tra ngược ra k → A. Biên độ tối đa 0,45 × s0 cho độ phủ ~0,9.
- Sáng hơn mức một lưới đường thẳng phủ được (w/s0 = 25 %) thì bớt đường: còn 1/2 (dòng chẵn), rồi 1/4 (dòng chia hết cho 4); mỗi đường xuất hiện ở ngưỡng lệch so le ±35 % nên không thành ranh giới. Dưới 0,6 × w/(4 s0) để trắng.
- Chỉ nối hai đường khi thật sự quay đầu và hai đầu lệch ≤ s0 (thường ở mép ảnh); nối chỗ khác ra móc chữ U / Z lạc lõng. Bỏ đoạn ngắn hơn 3 × s0.
- Lần thử đầu cho bước sóng đổi theo độ đậm: các đường lệch pha cắt nhau thành lưới rối, đã bỏ.

**Đo:** dải chuyển liền: sai tông 0,027, bậc 0,012 (zigzag cũ 0,082 / 0,099). Ảnh mèo A5: 105 nét, 5,4 phút có gia tốc (nhanh nhất vì gần như không nhấc bút) nhưng **16 000 dòng G-code** (zigzag 8 000): nhiều đoạn ngắn 0,2 mm. Ở 8000 mm/phút có thể vượt sức gửi lệnh từng dòng qua USB: xem đường "hàng đợi" ở Biểu đồ (cần `$10=3`); nếu hàng đợi cạn thì hạ tốc độ cho kiểu này.

---

## 9. Kiểu Viền: ảnh thành đường nét một lượt (`edges.py`, `trace.py`)

Kiểu này **không dùng mức sáng tối**. Nó tìm "đâu là đường trong ảnh" rồi cho bút đi đúng đường đó, **một lượt**.

### 9.1 Ba lớp đường, gộp lại
| Lớp | Tìm gì | Cách làm | Hàm |
|---|---|---|---|
| A. Nét mực | nét đậm hẹp ≤ 4 mm: viền hoạt hình, chữ, chấm mắt | *top-hat* trên độ đậm: giữ phần "nhô lên" hẹp hơn 4 mm so với nền, bỏ mảng to. Thêm vạch **sáng** mảnh ≤ 1,2 mm trên nền tối (thanh giường, dây sáng) | `cv2.morphologyEx(MORPH_TOPHAT)`, `connectedComponentsWithStats` (bỏ cục nhỏ) |
| B. Ranh giới mảng | hai vùng khác sáng tối **hoặc khác màu** mà không có nét đen | ảnh màu: làm phẳng vùng cùng màu (`pyrMeanShiftFiltering`, bán kính 7 điểm, khoảng màu 22) → làm mịn giữ mép (`bilateralFilter` hai lần) → `Canny`. Chạy thêm Canny trên hai kênh màu **a** (xanh lá–đỏ) và **b** (xanh dương–vàng) của hệ màu Lab | `cv2.Canny`, `cv2.cvtColor(RGB2LAB)` |
| C. Chấm đậm | mắt, nút: làm mảnh thì gần như mất | chấm có bán kính ≥ 2 điểm mà đường giữa ngắn hơn 5 × bán kính → vẽ **vòng viền** quanh chấm | `distanceTransform`, `findContours` |

Lớp B bỏ phần nằm sát nét mực (Canny cho hai mép của một nét mực, mà lớp A đã có đường giữa), và bỏ mẩu cạnh ngắn hơn 1,5 / 2,5 / 4 mm (theo mức chi tiết) để mất nhiễu lông, vân gỗ.

**Mức chi tiết** (ô "Chi tiết viền", bảng `DETAIL`):
| Mức | Canny thấp / cao | Ngưỡng nét mực | Cạnh ngắn nhất | Cắt râu tối đa | Hợp với |
|---|---|---|---|---|---|
| Ít (`low`) | 30 / 80 | 0,22 | 4 mm | 2,4 mm | ảnh chụp nhiều kết cấu |
| Vừa (`medium`) | 18 / 50 | 0,16 | 2,5 mm | 1,6 mm | hình 2D, sticker |
| Nhiều (`high`) | 10 / 30 | 0,11 | 1,5 mm | 1,0 mm | hình vẽ nét nhạt |

### 9.2 Làm mảnh: lấy đường giữa (`skimage.morphology.skeletonize`)
Bào mòn nét từ hai mép vào, mỗi lượt một lớp điểm ảnh, đến khi chỉ còn **1 điểm ảnh** mà không làm đứt nét. Kết quả là **đường giữa** (skeleton).
```
nét dày 5 điểm:     sau khi làm mảnh:
■■■■■■■■■■          ··········
■■■■■■■■■■          ··········
■■■■■■■■■■    →     ■■■■■■■■■■     ← bút đi đúng đường này, một lượt
■■■■■■■■■■          ··········
■■■■■■■■■■          ··········
```
Vì sao không dò đường bao (`findContours`, potrace): dò bao cho **hai đường** ở hai mép nét, bút sẽ vẽ hai lần và nét dày gấp đôi.

### 9.3 Sửa lỗi sau khi làm mảnh
1. **Nối khe hở** (`bridge`): mỗi đầu mút ước lượng hướng đi ra (trung bình các điểm nét trong bán kính 5 điểm ảnh). Nhìn thẳng ra phía trước trong góc 55°, gặp điểm nét khác trong ~1,5 mm (`GAP_MM`) thì kẻ đoạn nối. Tìm điểm gần nhanh bằng **KD-tree** (`scipy.spatial.cKDTree`: cây chia không gian, tra "điểm nào gần đây nhất" mà không phải so với mọi điểm).
2. **Cắt râu** (`prune_spurs`): làm mảnh nét dày luôn đẻ ra nhánh cụt ngắn ở góc (đỉnh chữ A, đáy chữ V). Cách nhận ra: đếm **số lần chuyển từ trắng sang đen khi đi một vòng 8 ô quanh một điểm** (`_crossing_number`):
   ```
   1 = đầu mút        2 = giữa nét (kể cả bậc thang)        ≥ 3 = ngã ba
   ```
   Từ mỗi đầu mút đi dọc nét. Gặp ngã ba trước khi đi quá giới hạn thì đoạn vừa đi là râu và bị xóa. Giới hạn = min(mức theo chi tiết, 1,6 × bán kính nét lớn nhất dọc nhánh + 2 điểm). Nhờ vậy nét mảnh (mạch in, chữ nhỏ, dấu ơ ư) không bị cắt nhầm, vì nhánh ngắn của nét mảnh là nét thật. Đoạn rời không có ngã ba thì giữ nguyên.

### 9.4 Dò thành nét liền (`trace.py`)
| # | Bước | Cách làm |
|---|---|---|
| 1 | Đồ thị | mỗi điểm đường giữa là một nút, nối với điểm lân cận 8 hướng |
| 2 | Đi nét | bắt đầu từ các đầu mút (sau đó tới các vòng kín). Tại ngã rẽ chọn hướng **thẳng nhất** (tích vô hướng với hướng đang đi lớn nhất). Nhánh còn lại thành nét mới, bắt đầu từ chính điểm rẽ nên không hở |
| 3 | Khép vòng | hai đầu một nét cách nhau ≤ 2 điểm ảnh thì nối lại (chữ o, số 0, hình tròn không hở) |
| 4 | Làm mượt | trung bình trọng số (1, 2, 1) ÷ 4 trên ba điểm liền, chạy 2 lượt, giữ hai đầu: bỏ bậc thang của lưới điểm ảnh |
| 5 | Bớt điểm | `cv2.approxPolyDP` (thuật toán Douglas–Peucker, dung sai 0,6 điểm ảnh ≈ 0,18 mm): bỏ điểm thừa trên đoạn gần thẳng |
| 6 | Đổi sang mm | `(điểm + 0,5) × mm mỗi điểm ảnh`; bỏ nét ngắn hơn max(1 mm, 3 × cỡ bút) |

---

## 10. Nhiều màu (`palette.py`)

Chọn "2–4 màu" thì mỗi màu là một lớp riêng, một tệp G-code riêng, vẽ xong thì đổi bút.
1. Đổi ảnh sang hệ màu **Lab** (L = sáng tối; a, b = màu), nhân hai kênh màu × 2,2 để phân biệt màu rõ hơn sáng tối.
2. Thu nhỏ về ~300 điểm, lặp lại các điểm rực màu 4 lần (để đèn màu nhỏ vẫn có cụm riêng).
3. **k-means** (`cv2.kmeans`, cố định hạt ngẫu nhiên nên chạy lại ra cùng kết quả): gom các điểm thành k nhóm màu.
4. Gán mỗi điểm ảnh vào màu gần nhất, lọc trung vị 5 ô (`cv2.medianBlur`) để bỏ đốm lẻ. Màu sáng nhất (L > 80) bị bỏ, coi là giấy.
5. Mỗi màu: độ đậm = độ đậm ảnh + 0,35, chỉ trong vùng màu đó (để màu sáng vẫn có ít nhất một lượt gạch). Mỗi màu gạch một góc khác nhau (lệch 180° ÷ số màu) cho dễ phân biệt.

Đây là phần thử nghiệm: màu chiếm diện tích rất nhỏ vẫn có thể bị gộp.

---

## 11. Tối ưu nét bằng vpype (`optimize.py`)

vpype là thư viện chuyên cho máy vẽ. Phần mềm gọi một chuỗi lệnh:
| Lệnh | Mặc định | Làm gì |
|---|---|---|
| `linemerge --tolerance` | 0,1 mm | nối hai nét có đầu–đuôi cách nhau ≤ 0,1 mm thành một |
| `linesimplify --tolerance` | 0,05 mm | bỏ điểm thừa |
| `filter --min-length` | 0,5 mm | bỏ nét quá ngắn |
| `linesort --two-opt --passes 50` | bật | sắp thứ tự nét cho quãng bút **nhấc lên di chuyển** ngắn nhất. *2-opt*: thử đảo ngược từng đoạn trong thứ tự, giữ lại nếu quãng đi ngắn hơn |

**Thứ tự vẽ giữa các mức (`group_levels`, 09/11/2026).** `linesort` chỉ biết rút ngắn quãng bay nên trộn mọi mức đậm nhạt lẫn nhau: bút vẽ dở mảng này đã nhảy sang mảng khác, và cú nhảy xa dồn ở cuối (nét lẻ bị bỏ lại). Mặc định giờ mỗi **mức** là một lớp vpype riêng (vpype sắp xếp từng lớp độc lập) rồi ghép lại **nhạt → đậm, viền cuối** (`raster._optimize`, `styles.fill_groups`). Đo (ảnh nhiều chi tiết, xoắn ốc, 1071 nét): tổng quãng nhấc bút **1344 mm → 3947 mm** (thêm khoảng 2,6 m ≈ 20–30 s ở 6000–8000 mm/min), số nét không đổi; ảnh chuyển sắc: đổi mức **3 lần** (lý tưởng) thay vì 111 lần. Số lần nhấc bút gần như không đổi. Tắt ô "Vẽ lần lượt từng mức" để quay về cách cũ (quãng bay ngắn nhất, thứ tự lộn xộn). Chưa biết thứ tự nào tốt hơn cho mực: chờ ảnh in thật.

Đo trên laptop (8000 nét): sắp thường 0,85 s → 11,75 m di chuyển; 2-opt 50 lượt 8,5 s → 8,97 m (−24 %); 200 lượt không hơn đáng kể. 2-opt chậm theo bình phương số nét, nên quá 15 000 nét thì chỉ sắp thường.

---

## 12. Đặt lên giấy và ra G-code (`layout.py`, `gcode.py`)

**Bố trí** (`layout.plan`): tờ giấy neo ở góc trên trái máy O(0,0), Y hướng xuống. Trừ lề → khung vẽ (lấp đầy hoặc theo kích thước người dùng) → co giãn giữ tỷ lệ → căn giữa → xoay 0/90/180/270 → lật → đảo thứ tự nét (tùy chọn). Mọi lớp màu dùng **chung một** phép đặt nên khớp nhau. Khung ra ngoài giấy thì báo lỗi, không tự cắt. Trình duyệt có bản JS trùng công thức (`lib/paper.js`) để kéo thả mượt, có test đối chiếu.

**G-code** (`gcode.build_gcode`):
```
G90 G21                  ; tọa độ tuyệt đối, đơn vị mm
G1 Z3 F3000              ; nhấc bút
G4 P0.05                 ; chờ servo
G0 X12.4 Y30.1           ; chạy nhanh tới đầu nét 1
G1 Z0 F2000              ; hạ bút (chậm hơn, đỡ nảy)
G4 P0.05
G1 X13.0 Y30.6 F5000     ; vẽ qua từng điểm
G1 X13.7 Y31.0
…
G1 Z3 F3000              ; nhấc bút, sang nét 2 …
```
`F` chỉ ghi khi đổi. Điểm trùng liền nhau bị bỏ. Ước tính thời gian = quãng vẽ ÷ tốc độ vẽ + quãng di chuyển ÷ tốc độ di chuyển + thời gian nâng/hạ Z + chờ (chưa tính gia tốc nên thường ngắn hơn thật).

---

## 13. Máy biết "cách nhau bao nhiêu" bằng cách nào

**Máy không biết gì về khoảng cách nét.** FluidNC chỉ nhận danh sách tọa độ mm và chạy tới đó. Mọi thứ đã tính xong trong phần mềm:

```
Cỡ bút 0,4 mm   × 1,375 (đo thật)          → bề rộng nét w = 0,55 mm
độ phủ mục tiêu (vd bậc 2 = 45 %)          → s = 0,55 ÷ 0,45 = 1,22 mm
đường quét thứ i                           → v = vmin + i × 1,22 mm  (tọa độ mm trên bản vẽ)
điểm ảnh ↔ mm                              → x_mm = cột × (bề rộng ảnh mm ÷ số cột)
bố trí lên giấy                            → cộng vị trí khung, nhân tỷ lệ
G-code (G21 = mm)                          → G1 X63.41 Y20.55 F5000
FluidNC ($100 = 80 bước/mm)                → 1 mm = 80 bước động cơ (độ phân giải 0,0125 mm)
```
Hai đường kề nhau cách nhau 1,22 mm vì **tọa độ trong G-code cách nhau đúng 1,22 mm**.

Vì khoảng cách gắn với mm thật, **kéo khung to/nhỏ hơn 12 %** so với lúc tạo nét thì giao diện tự tạo lại nét (nếu chỉ phóng hình học, nét sẽ thưa ra hoặc dày đặc so với bút).

**Con số dễ sai nhất là w = 0,55 mm**: phụ thuộc bút, giấy, tốc độ vẽ, độ loang. Đổi bút hay giấy thì đo lại (tờ hiệu chỉnh, [07_THU_NGHIEM.md](07_THU_NGHIEM.md) mục 1) và sửa số của bút đó trong ô "Bút vẽ" (`index.html` + `spec.PENS`), hoặc chọn Tùy chọn và gõ số đo; mọi khoảng cách tự cập nhật.

---

## 14. Kiểm tra thuật toán mà không cần in: bộ mô phỏng mực

`tools/ink_sim.py` (chạy: `cd backend` rồi `.venv\Scripts\python.exe ..\tools\ink_sim.py`):
1. Dựng ảnh thử 80 × 50 mm: một dải chuyển liền trắng → đen và một đốm tròn mềm.
2. Chạy từng kiểu tô, **vẽ lại các nét** với bề rộng thật 0,55 mm ở 20 điểm/mm (`cv2.polylines`).
3. Làm mờ cả ảnh mực và ảnh mục tiêu ~2 mm (`GaussianBlur`), giống mắt nhìn từ xa.
4. In: **sai số trung bình** (nhỏ = đúng tông), tổng chiều dài nét, số nét, thời gian ước tính. Ghi ảnh mô phỏng vào `export/ink-sim/`.

Giới hạn: chỉ đo tông ở cỡ ~2 mm, không đo vẻ đẹp hay độ sắc. Coi mực không loang thêm khi hai nét chồng nhau. Dùng để **so sánh các thuật toán với nhau**, không đoán được độ đậm tuyệt đối trên giấy.

---

## 15. Thư viện đã dùng: mỗi cái làm gì

| Thư viện | Là gì (lời thường) | Dùng cho | Tệp |
|---|---|---|---|
| **NumPy** | làm toán trên cả bảng số một lúc, rất nhanh | mọi phép trên ảnh và tọa độ: so ngưỡng, tra mặt nạ, tìm đoạn | khắp nơi |
| **Pillow (PIL)** | đọc / ghi tệp ảnh | mở ảnh, xoay EXIF, cắt, thu nhỏ | `raster_in.py` |
| **OpenCV** (`opencv-python-headless`) | hộp đồ nghề xử lý ảnh lớn nhất | làm mờ, hình thái học, Canny, mean shift, Lab, k-means, Douglas–Peucker, khoảng cách tới mép | `tone`, `hatch`, `edges`, `trace`, `palette` |
| **scikit-image** | các phép ảnh khoa học | `skeletonize` (làm mảnh), `remove_small_objects` | `edges.py`, `trace.py` |
| **SciPy** | toán khoa học | `cKDTree` (tìm điểm gần nhất khi nối khe) | `edges.py` |
| **vpype** | thư viện chuyên cho máy vẽ | đọc SVG, nối nét, bớt điểm, bỏ nét ngắn, sắp thứ tự (2-opt) | `svg_in.py`, `optimize.py` |
| **Shapely** | hình học vector | rút gọn nét xem nháp gửi cho trình duyệt | `preview.py` |

Các gói khác trong `requirements.txt` (`networkx`, `svgelements`, `pnoise`, `pyphen`…) là phụ thuộc kéo theo của vpype, mã của dự án không gọi trực tiếp.

**Các hàm OpenCV / scikit-image, nghĩa bằng lời thường:**
| Hàm | Nghĩa | Ở bước |
|---|---|---|
| `cv2.cvtColor` | đổi hệ màu (RGB → xám, RGB → Lab) | 5, 9, 10 |
| `cv2.fastNlMeansDenoising` | khử nhiễu hạt (ảnh thiếu sáng) | 5 |
| `cv2.createCLAHE` | cân bằng sáng **từng ô nhỏ** | 5 |
| `cv2.GaussianBlur` | làm mờ đều | 7, 14 |
| `cv2.bilateralFilter` | làm mờ **nhưng giữ mép** | 9 |
| `cv2.pyrMeanShiftFiltering` | làm phẳng vùng cùng màu (da, trời thành mảng đều) | 9 |
| `cv2.Canny` | tìm **cạnh**: nơi độ sáng đổi đột ngột, ra đường mảnh 1 điểm | 9 |
| `cv2.morphologyEx(TOPHAT)` | giữ thứ **hẹp hơn một cỡ** cho trước (nét mực, chấm) | 9 |
| `cv2.morphologyEx(CLOSE / OPEN)` | bịt khe nhỏ / xóa đốm nhỏ trên mặt nạ | 7 |
| `cv2.connectedComponentsWithStats` | đếm và đo từng cục liền nhau | 9 |
| `cv2.distanceTransform` | mỗi điểm cách mép bao xa (biết nét dày bao nhiêu) | 9 |
| `cv2.findContours` | đi vòng theo đường bao một vùng (chỉ dùng cho vòng viền chấm) | 9 |
| `cv2.approxPolyDP` | bỏ điểm thừa mà hình gần như không đổi (Douglas–Peucker) | 9 |
| `cv2.kmeans` | gom điểm thành k nhóm giống nhau | 10 |
| `cv2.medianBlur` | lọc trung vị, bỏ đốm lẻ | 10 |
| `skimage.morphology.skeletonize` | gọt nét dày thành đường giữa 1 điểm | 9 |
| `scipy.spatial.cKDTree` | tra nhanh "điểm nào gần nhất" | 9 |

---

## 16. Thư viện và cách làm đã cân nhắc nhưng KHÔNG dùng, vì sao

| Thứ | Làm được gì | Vì sao không dùng |
|---|---|---|
| **potrace** | vector hóa ảnh đen trắng rất mượt | dò **đường bao** mảng đặc → nét dày thành hai đường song song, bút vẽ hai lần |
| `cv2.findContours` để dò nét | dò đường bao | cùng lý do: nét 1 điểm ảnh ra **hai** đường bao. Dùng dò theo đồ thị (`trace.py`) |
| **sknw** (skeleton → đồ thị) | như `trace.py` | thêm một gói chỉ cho việc tự viết được trong ~80 dòng |
| **numba** (tăng tốc Python) | chạy vòng lặp nhanh | nặng, khó cài trên bản mang đi; numpy đã đủ nhanh |
| **scikit-learn** (k-means) | phân cụm | OpenCV đã có `kmeans`; đỡ ~30 MB |
| Viền kiểu **DoG** (hiệu hai ảnh mờ, bản đầu) | tìm nét nhanh | nét dày ra hai đường, mất viền mảng không có nét đen, đứt nét, ăn mép tối cạnh vạch sáng. Thay bằng top-hat + Canny + skeleton (31/10/2026) |
| **Chồng nhiều lớp gạch xoay góc** (bản đầu) | tô đậm bằng nhiều lớp | tông sai (bậc 2 giống bậc 3), nét dài gấp đôi (mục 6.3) |
| **5 ngưỡng chia đều** | đơn giản | sai số tệ nhất trong các cách thử (0,147) |
| **Sóng điều biến** (biên độ theo độ đậm, một lượt) | đẹp mắt, một lượt | sai số 0,19–0,22, kém xa cách hiện tại |
| **Stipple / TSP art** (chấm điểm, đường đi qua mọi chấm) | tranh chấm đẹp | mỗi chấm một lần nhấc bút → hàng chục nghìn lần nhấc, vẽ hàng giờ |
| Chia ảnh thành ô xử lý song song | nhanh hơn trên máy nhiều nhân | MiniPC 2 nhân còn phải điều khiển máy; OpenCV đã tự dùng 2 luồng |
| Viết lại tô nét / skeleton bằng JavaScript | đỡ tải máy chủ | không nhanh hơn, thêm lỗi, hai bản phải giữ khớp nhau |
| `vpype-text`, font Hershey | viết chữ nét đơn | plugin ngừng phát triển, Hershey không có dấu tiếng Việt |
| `pdftocairo -svg`, `docx2pdf`, LibreOffice | đổi Word/PDF | chữ có thể mất (SVG), cần Word cài sẵn, thiếu font làm chữ xuống dòng khác. Người dùng tự "Lưu thành PDF" trong Word |
| Chạy AI tạo ảnh / AI tìm nét trên MiniPC | tranh nét sạch hơn | không card đồ họa: vài phút mỗi ảnh, 4–8 GB RAM, làm giật máy vẽ |

---

## 17. Thư viện và thuật toán có thể thêm để phát triển

Xếp theo mức nặng cho MiniPC. Từ khóa tiếng Anh để tự tra.

### 17.1 Nhẹ (chỉ numpy / scipy, gần như không thêm RAM)
| Hướng | Thư viện / cách | Được gì | Từ khóa |
|---|---|---|---|
| Đường cong tông theo bút thật | `scipy.interpolate` trên số đo thang xám in thật | tông giữa đúng với mắt nhìn (hiện coi độ phủ tỷ lệ thẳng với độ đậm) | `tone reproduction curve`, `halftone calibration` |
| Làm mượt nét viền tốt hơn | `scipy.signal.savgol_filter`, `splprep`, Chaikin | cong trơn hơn trung bình 3 điểm | `Savitzky-Golay polyline smoothing` |
| Tỉa râu theo đồ thị | `skan` | phân tích nhánh chính xác hơn | `skan skeleton branch` |
| Đo bề dày nét chữ | `skimage.morphology.medial_axis` | tự phát hiện chữ đậm → vẽ 2 đường | `medial axis stroke width` |
| Tách chữ khỏi nền giấy quét | `skimage.filters.threshold_sauvola` | ngưỡng thích nghi từng vùng | `Sauvola binarization` |
| Xóa đoạn vẽ chồng | plugin `deduplicate` của vpype | bớt nét trùng | `vpype deduplicate` |
| Gộp đoạn thẳng thành cung tròn | ArcWelder (G2/G3) | ít dòng G-code hơn. ⚠ cung chưa thử trên máy thật | `ArcWelder arc fitting` |

### 17.2 Vừa
| Hướng | Thư viện / cách | Được gì | Từ khóa |
|---|---|---|---|
| Tab Beta in trang PDF | `pypdfium2` (giấy phép thoáng) hoặc PyMuPDF | trang PDF → ảnh 600 dpi → skeleton; chữ 14 pt đi được | `pypdfium2 render page` |
| Đọc cấu trúc PDF | PyMuPDF `get_text("rawdict")`, `get_drawings()` | đường kẻ bảng vẽ thẳng bằng vector, chữ đi skeleton, ảnh đi kiểu tô | `PyMuPDF get_drawings` |
| Viền kiểu nét vẽ tay | XDoG / FDoG (tự viết bằng OpenCV) | nét mềm hơn Canny | `XDoG extended difference of gaussians` |
| Phân vùng siêu điểm ảnh | `skimage.segmentation.slic`, `felzenszwalb` | mảng màu sạch hơn mean shift | `SLIC superpixels` |
| Tô theo hướng khối | flow field, đường đồng mức | nét uốn theo hình (khác hẳn zigzag) | `flow field hatching`, `contour hatching` |
| Tự hiệu chỉnh bằng ảnh chụp | `cv2.aruco` + `cv2.findHomography` | chụp tờ mẫu bằng điện thoại → tự đo bề rộng nét, độ phủ từng dải → tự sửa `LINE_WIDTH_RATIO` | `OpenCV ArUco homography` |
| Đo chất lượng | SSIM (`skimage.metrics.structural_similarity`), OCR `pytesseract` (gói `vie`) | số liệu "giống bản gốc bao nhiêu %" cho báo cáo | `SSIM`, `character error rate` |

### 17.3 Nặng (laptop, hoặc chỉ chạy khi máy vẽ rảnh)
| Hướng | Mô hình | Ghi chú |
|---|---|---|
| AI tìm viền nhẹ | TEED (~58 nghìn tham số), PiDiNet, HED qua `cv2.dnn` / onnxruntime | viền ảnh chụp sạch hơn Canny |
| AI ảnh chụp → tranh nét | Informative Drawings (ONNX ~8,6 MB, MIT) | ⚠ đo tốc độ trên i5-3210M trước |
| AI hoạt hình → nét | Anime2Sketch | chỉ có PyTorch ~218 MB, phải tự chuyển ONNX |
| Đường giữa từ vector | Inkscape đổi chữ thành đường → `centerline` (Voronoi, Shapely) | chính xác, không phụ thuộc độ phân giải |

---

## 18. Giới hạn đã biết

- **Ảnh chụp màu** ở kiểu Viền ra **bản phác** nhận ra được hình, nét hơi đứt, không phải tranh tô màu sạch. Muốn sạch hơn cần AI tìm viền (17.3).
- **Chữ nhỏ** (14 pt, cao ~2 mm) đi qua đường ảnh này bị nát (mỗi điểm ảnh ~0,3 mm). Chữ phải đi dây chuyền riêng (tab Beta PDF, 17.2).
- **Mạch in đơn giản** (vết, pad, chân linh kiện, nét ≥ 1,5 mm) đi được bằng preset Schematic.
- Độ phủ được coi là **tỷ lệ thẳng** với độ đậm cảm nhận. Mắt người không tuyến tính, nên tông giữa có thể lệch. Thang xám in thật sẽ cho biết cần uốn đường cong tông ra sao.
- Bề rộng nét 0,55 mm đo ở tốc độ vẽ cũ (3000 mm/min). Cần đo lại ở 5000.
