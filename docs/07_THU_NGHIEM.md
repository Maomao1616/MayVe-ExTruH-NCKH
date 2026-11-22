# 07 — Thử nghiệm và hiệu chỉnh trên giấy

> Dành cho người vận hành máy (không cần lập trình). Mục tiêu: chốt con số mặc định **bằng bản in thật**, vì màn hình không cho biết mực loang, giấy thấm, bút khô ra sao.
> **Cách dùng:** làm theo danh sách ngay dưới (từ trên xuống) → chép **mẫu ở mục 8**, điền số, gửi kèm ảnh. Không cần tự sửa mã hay tài liệu; AI đọc ảnh và số rồi chỉnh.
> Ký hiệu: ✅ đã chốt · ⏳ chưa làm. Kết quả thử máy đã có: [02](02_PHAN_CUNG_MAY.md) mục 6. Việc cần làm khác: [11](11_VIEC_CAN_LAM.md).

## 0. Nguyên tắc
- **Mọi quyết định về độ đậm phải nhìn tờ giấy.** Khung xem trước chỉ để kiểm hình học (đủ nét, đúng chỗ, không vượt khổ).
- Mỗi lần **đổi một thông số**. Cùng giấy, cùng bút, cùng tốc độ. Ghi số ở góc tờ (bút, kiểu, khổ, ngày) rồi chụp.
- Ô "Bút vẽ" ghi thẳng **bề rộng nét đo trên giấy**; bút chưa có trong danh sách thì chọn **Tùy chọn** và gõ số đo.
- Bút đỏ chỉ dùng đo bề rộng nét, loang, đọng mực; **không dùng đánh giá độ đậm** (đỏ trông nhạt hơn đen).

### Đổi gì thì phải đo lại gì
Hằng số thuật toán (`FLOW_*`, `HATCH_*`, `AM_*`, `REFINE_*`) **không** đổi theo bút hay giấy; chỉ đổi khi một bài dưới đây bảo.

| Bạn đổi | Làm lại | Ghi kết quả vào | Không đụng |
|---|---|---|---|
| **Bút** (loại, cỡ) | tờ hiệu chỉnh bút (mục 1) + tờ tông A4 | ô **Bút vẽ**; `spec.PENS` | `LINE_WIDTH_RATIO` (giữ 1,0) |
| **Giấy** (bóng ↔ nhám, hãng) | mục 1 + A4 | bảng bút / giấy ở [02](02_PHAN_CUNG_MAY.md); `TONE_CURVES` nếu A4 lệch | hằng thuật toán |
| **Tốc độ vẽ** | bài 7.4 (mục 6) | `draw_feed` | `LINE_WIDTH_RATIO`, `MAX_COVERAGE` |
| **Z nhấc / chờ / hạ bút** | bài 7.1 (mục 6) | `spec.py` (`pen_up_z`, chờ, hạ) | hằng tô |
| **Gia tốc / junction** | bài 7.3 (mục 6) | cấu hình máy → Lưu vào mạch | hằng tô |
| **Kiểu ảnh đặc thù** (chữ, sơ đồ, đen trắng gắt) | chỉnh gamma / tương phản trên giao diện; chưa vừa mới báo AI | ô tương ứng trên tab Tạo bản vẽ | hằng tô |
| **Sửa sai tông** (số lượt) | A5 | ô **Sửa sai tông** | `TONE_CURVES` |

## Danh sách cần thử (làm từ trên xuống)

**Chuẩn bị (một lần):** (1) tắt phần mềm, mở lại, trình duyệt **Ctrl+F5**; (2) tab Tạo bản vẽ, khối G-code: vẽ / di chuyển **8000**, Z nâng 3 / hạ 0, hạ bút 2000, chờ **0**; (3) Terminal gõ `$10` phải ra `$10=3` (không thì gõ `$10=3`); (4) Cài đặt → Cấu hình máy: gia tốc X / Y **2700**, `junction_deviation` **0,02** (chốt 22/11/2026) → Áp dụng → **Lưu vào mạch** (bạn bấm; phần mềm đã ước tính theo 2700 / 0,02); (5) bật nguồn, nối, **mở khóa chuyển động**; (6) chọn lại preset sau khi mở. Giấy Ivory mặt bóng, bút **Sakura 0,5** trừ khi ghi khác.

### A. In giấy (chỉ còn các bài này; kết quả cũ đã chốt thì bỏ, tra Git)
Tổng quát: bút **UM-100**, giấy Ivory 250 g/m² mặt bóng, A4; ghi ở góc tờ (kiểu, preset, ngày) rồi chụp thẳng góc, đủ sáng, không flash.
| # | Bài | Chọn gì | Nhìn và ghi |
|---|---|---|---|
| A1 | **Mèo** | kiểu **Đường dòng** + tích **Chất lượng tối đa** | mắt, mũi có hiện không (bản 19/11 mất mặt); mực có bết không |
| A2 | **Phong cảnh** | preset **Phong cảnh**, một tờ có và một tờ không tích **Chất lượng tối đa** | nhà gỗ, cây, mây có hiện không; trời có đậm kịt không |
| A3 | **Hình vẽ 2D** | preset **Hình vẽ 2D** (tương phản 1,5 + cân bằng sáng + làm nét), ảnh nhân vật; thử **cả hai**: **Đan chéo** và **Đường dòng** (mỗi kiểu một tờ) | **mắt, mũi, môi** rõ chưa (ưu tiên số 1; chỗ khác chưa hoàn hảo cũng được); nền có vệt "cuộn len" không |
| A4 | **Chân dung ảnh thật** | preset **Chân dung**, **không** tích Chất lượng tối đa (chủ dự án 22/11: bỏ giới hạn trông chia mảng, kém mịn hơn) | mắt, mũi, môi rõ và mịn chưa |
| A5 | **Xoắn ốc mới** | một ảnh bất kỳ, kiểu **Xoắn ốc** | nhận ra hình không (bản cũ chỉ ra vòng tròn); mực bết ở chỗ đậm không |
| A6 | **Bản vẽ kỹ thuật** | preset **Bản vẽ kỹ thuật**, ảnh sơ đồ hoặc đen trắng | nét gạch mảnh, vạch chia, chữ có giữ không |
| A7 | **Tờ tông 3 bản mới** | **Thang tông** (mục 2): Đan chéo + Chất lượng tối đa · Đường dòng + Chất lượng tối đa · Xoắn ốc; A6 mỗi tờ, thấy đủ 3 ô mốc đen | 5 bậc cách đều chưa; ô 0,05–0,35 của đường dòng đã tách tông chưa. Gửi ảnh gốc, AI đo bằng `tools/tone_read.py` |
| A9 | **Tách mực 3 bút** (22/11) | ảnh có màu rõ (bông hoa đỏ, tóc tối): Palette = **Tách mực theo bộ bút**, bộ **Đen + đỏ + xanh navy**, kiểu **Đường dòng** hoặc **Sóng điều biên**, A5; bút: đỏ UB-155, xanh UM-100 (thay navy), đen Micron (hoặc bộ mới: UM-151 đen 0,28 + prussian blue 0,38; nhập nét đo vào ô "Nét bút 1–3"); vẽ đỏ → xanh → đen, đổi bút giữa các tệp G-code | màu có ra đúng không (hoa đỏ, tóc xanh đậm); ba lớp có khớp nhau không (chồng đúng chỗ); bút khác bề rộng nét có làm lớp nào đậm lệch |
| A8 | **Vùng chủ thể** | ảnh có nền rối, khoanh elip, nền còn 50 % | nền thưa đủ để chủ thể nổi; mép vùng không lộ vòng |

### B. Máy (còn 1 bài; B1 bản vẽ G2/G3, B2 servo, B4 tiếng "khực" (hết với gia tốc 2700 / junction 0,02, 22/11), tab Điều khiển mượt đã xong, dồn về [11](11_VIEC_CAN_LAM.md) mục 3 và [02](02_PHAN_CUNG_MAY.md) F16)
| # | Bài | Làm | Nhìn và ghi |
|---|---|---|---|
| B3 | **Tạo nét chậm** (laptop yếu; tab Điều khiển đã mượt 18/11) | tạo nét một ảnh A5 nhiều nét; thuật toán **Tạo nét** còn chậm, nhiều khả năng do máy | **cách lấy thông số** (ghi 4 dòng): (1) tên CPU + RAM laptop (Cài đặt Windows → System → About); (2) số dòng G-code (dòng G-code ở tab Tạo bản vẽ); (3) thời gian từ lúc bấm **Tạo nét** tới lúc xong (đếm giây); (4) nếu còn khựng: F12 → Performance → Record 5 giây khi chạy, chụp màn hình |

### C. Người dùng, mạng
**Cách vào giao diện từ điện thoại khi laptop đã có Wi-Fi:** [08](08_TRIEN_KHAI.md) mục C, khối "Vào giao diện từ điện thoại" (5 bước: nối Wi-Fi **trước**, bấm icon, mở đúng địa chỉ, tường lửa Mạng riêng tư).

| # | Bài | Làm | Nhìn và ghi |
|---|---|---|---|
| C1 | **PIN + khách** | `data\pin.txt` dòng `admin=…` bằng PIN khó đoán (chỉ PIN đăng nhập, không cần `unlock=`); vào bằng điện thoại | ra giao diện **khách** (chỉ xem, được Gửi ảnh); đổi PIN trên giao diện, đăng nhập lại bằng điện thoại |
| C2 | **Luồng khách gửi ảnh** | điện thoại (chưa đăng nhập) → tab Tạo bản vẽ → chọn ảnh, cắt, khổ → **Gửi ảnh**; laptop (đăng nhập) → hộp "Ảnh khách gửi" → **Mở** → **Tạo nét** | cắt bằng ngón tay được không; cảnh báo quá 6 ảnh / giờ; ảnh tự xóa sau 5 ngày |
| C3 | **Tờ thử trên giao diện** | Cài đặt → Tờ thử → tạo tờ nhấc bút, nạp ở Điều khiển, chạy, chọn hàng đẹp → **Dùng** | tab Tạo bản vẽ có đổi Z nhấc / chờ / tốc độ hạ |
| C4 | **Tắt Wi-Fi của mạch MKS** | trước khi cho người khác vào mạng | — |
| C5 | **Âm báo xong / lỗi** | chạy một bản vẽ ngắn (hoặc máy giả), chuyển sang tab khác | nghe 3 nốt lên khi xong; tiêu đề tab nhấp nháy; tắt được ở Cài đặt → Hoạt động; lỗi thì 2 nốt trầm |

### D. Bản mang đi, MiniPC
Máy sạch không cài gì (Visual C++ của OpenCV), điện thoại thật, thời gian xử lý ảnh / RAM trên MiniPC, Docker + USB, Cloudflare: [08](08_TRIEN_KHAI.md) mục G.

**Gửi lại (một lần cuối buổi):** ảnh từng tờ (thẳng góc, đủ sáng, không flash; tờ tông thấy đủ 3 ô mốc đen) + bảng: bài · kiểu / preset · khổ · thời gian thật / ước tính · nhận xét. Bài máy: ảnh chụp màn hình Biểu đồ + tải CSV từ Biểu đồ (hoặc nén `data\job_logs`). Có `error` ở Terminal thì chụp lại.

## 1. Bề rộng nét thật: tờ mẫu hiệu chỉnh bút
Tờ có chữ F (kiểm hướng X / Y), thước 100 mm (kiểm tỷ lệ) và **8 dải gạch** cách nhau 0,8 / 1 / 1,125 / 1,25 / 1,5 / 2 / 2,5 / 3 **lần cỡ bút** (nhân số, không phải mm). Tạo ở Cài đặt → **Tờ thử / hiệu chỉnh** → "Tạo tờ hiệu chỉnh bút" (khổ A5 hoặc A6).

| Xem gì | Kết luận |
|---|---|
| Thước đúng 100 mm? | ✅ đúng. Sai thì kiểm `steps_per_mm` trước |
| Dải **sát nhất còn đặc mà chưa ướt / quăn** | khoảng cách ≈ **bề rộng nét thật** |
| Dải trông **xám vừa** (đứng 40–50 cm) | ≈ 2 × bề rộng nét (phủ 50 %) |

✅ Đã chốt (12/11/2026, Ivory 250 g/m², 8000 mm/phút, mặt bóng): **UB-155 0,38 · UM-100 0,40 · Sakura 0,50** (mặt nhám 0,55: chọn Tùy chọn); `LINE_WIDTH_RATIO = 1,0`. Phần mềm suy mọi khoảng cách nét từ số này ([06](06_THUAT_TOAN_XU_LY_ANH.md) mục 6). Bề rộng nét phụ thuộc **tốc độ, bút, giấy**: đổi một trong ba thì đo lại.

## 2. Thang tông (đo độ đậm mắt thấy)
Làm **một lần cho mỗi bút + giấy + kiểu tô**. Kết quả dùng để uốn đường cong tông ([06](06_THUAT_TOAN_XU_LY_ANH.md) mục 8.12).

1. Cài đặt → **Tờ thử / hiệu chỉnh** → khối **Thang tông** → chọn khổ (A6 gọn nhất) → **"Mở ảnh thang tông ở tab Tạo bản vẽ"** (tự chuyển tab, nạp ảnh 16 ô xám + 3 ô mốc đen + chữ F). Ô vẽ ra đã đi qua đường cong tông của kiểu tô, nên đo đúng cái mắt thấy khi vẽ thật.
2. Chọn **bút + kiểu tô**; để đo: **tắt CLAHE / khử nhiễu, gamma 1, tương phản 1, mức đen 0 / trắng 255, Số mức 5**. Tạo nét → Lưu bản thảo → vẽ.
3. Chụp bằng điện thoại: **thẳng góc**, ánh sáng đều (cửa sổ hoặc đèn trần, tránh chiếu một phía), **không flash**, giấy phẳng, thấy đủ 3 ô đen ở góc và chữ F; giấy bóng thì nghiêng nhẹ tránh phản chiếu. Không chỉnh sáng / lọc. Gửi ảnh gốc; chụp nhiều tờ một ảnh vẫn đo được nếu tờ nào cũng thấy đủ 3 ô mốc. Mốc **10 mm**, chữ F nét **6 mm** (19/11/2026; trước 4 mm / 1,5 mm — mốc nhỏ bị bộ lọc bớt râu xoá sạch nên tờ in 18/11 không đo được).
4. 16 ô đọc từ trái sang phải, trên xuống dưới, độ phủ: 0 (giấy) · 5 · 10 · 15 · 20 · 25 · 30 · 35 · 40 · 45 · 50 · 55 · 60 · 70 · 80 · 90 %. Ô nào bết mực / ướt giấy thì ghi.

AI đọc ảnh bằng `tools/tone_read.py` ra bảng *độ phủ → độ đậm nhìn thấy*. Với 5 mức, 16 ô gộp thành **5 bậc trên giấy** (giấy trắng + 4 mật độ 22 / 45 / 68 / 90 %); hai ô kề ra cùng mật độ là đúng thiết kế.

| Thấy gì trên tờ | Sửa trong `frontend/js/views/drawing/presets.js` hoặc `styles.py` |
|---|---|
| Hai mật độ kề nhau trông như nhau | giảm `style-levels` 1 bậc |
| Bậc đậm nhất bết mực, giấy ướt | giảm `MAX_COVERAGE` (0,9) hoặc tăng `style-spacing` |
| Cả tờ quá đậm / quá nhạt | `image-gamma` ±0,1–0,2 (không dưới 0,8) |
| Vùng nhạt lộ từng sợi | giảm `style-spacing` (trống = 2 × nét thật) |
| Tông giữa lệch | gửi ảnh, AI cập nhật bảng ở `styles.TONE_CURVES` |

✅ Đã đo 13/11/2026 (Sakura 0,5, mặt bóng; bảng ở 06 mục 8.12): vùng giữa trông nhạt hơn độ phủ → đường cong tông 75 % cho Gạch chéo và Xoắn ốc. Chưa đo cho Theo dáng ảnh và UB-155.

**Tờ tông in 19/11/2026 bằng UM-100** (bút xanh, chủ dự án coi là chuẩn; ảnh `D:\OneDrive\Live-Work\IMG20261119174516.jpg`). Tờ có 4 phần: trên-trái **đan chéo thường** · dưới-trái **đan chéo bỏ giới hạn** · trên-phải **theo dáng bỏ giới hạn** · dưới-phải **xoắn ốc**. Mốc ở phần gạch / xoắn ốc là ô gạch thưa, `tone_read.py` chỉ bắt được mốc ở phần theo dáng → đo bằng cách chỉ tay 3 mốc, **sai số ±0,05** (chụp nghiêng, vết mực).

| Phần | Kết luận |
|---|---|
| Đan chéo thường | ô 0,15 → 0,9 tăng đều gần thẳng; ô 0–0,1 để trắng đúng thiết kế → **đường cong tông hiện tại đúng, không chỉnh** |
| Đan chéo bỏ giới hạn | tăng dần nhưng lổn nhổn; viền gạch đứt ở mép mỗi ô (do làm mờ mặt nạ ở mép) |
| Theo dáng bỏ giới hạn | ô 0,05–0,35 cùng độ đậm (~0,3) → do đường thưa nhất 3 × nét, **đã sửa** (`FLOW_UNLIMITED`: 8 × nét); chưa in lại |
| Xoắn ốc | ảnh xoay, đo lệch → **không dùng số**; xoắn ốc đã viết lại nên `TONE_CURVES["spiral"]` cũ hết ý nghĩa với bản mới; cần in lại |

**Cần in lại (22/11/2026):** (1) tờ tông cho **3 bản mới**: gạch chéo bỏ giới hạn · theo dáng bỏ giới hạn · xoắn ốc viết lại; (2) **4 ảnh mẫu** bằng chế độ Bỏ giới hạn (xem A8).

## 3. Từng kiểu tô: soi chỗ nào
| Kiểu | Soi trên giấy | Chỉnh ở đâu |
|---|---|---|
| Gạch chéo | râu ở mép mảng; má / nền sáng trống quá; móc chữ U ở mảng sáng hẹp (còn, đã thử bỏ không được, 09 P28) | `HATCH_WHITE` 0,2 · `HATCH_THIN_SPACINGS` 1,5 · `HATCH_MIN_RUN_MM` 5 (`styles.py`) |
| Theo dáng ảnh | vùng tối vụn hay đặc; nét chạy theo lông | `FLOW_TEST_RATIO` 0,7 · `FLOW_MIN_LEN_SEPS` 3 · `FLOW_MAX_COVER` 0,85 · `FLOW_MAX_SEP_LINES` 4,5 (`flow.py`) |
| Sóng biến thiên | vệt trắng ở da; rung ở sóng dày; ô 90 % đen chưa | ô "Phủ đều đường ở vùng sáng" · `AM_DARK_LAYER` · `AM_SPACING_LINES` |
| Xoắn ốc | tâm xoắn bết mực; vệt nối ngang vùng sáng | `SPIRAL_BRIDGE_PITCHES` (`hatch.py`) |
| Nét viền | liền, thừa vụn, nét dày ra **một** đường | ô Chi tiết viền; mục 4 |

## 4. Nét viền: ảnh thử và hằng số
Thử 3 loại ảnh: (a) hình vẽ / sticker có viền đen, (b) mảng màu phẳng không viền, (c) ảnh chụp thật.

| Hằng số | Ý nghĩa | Khi nào đổi |
|---|---|---|
| `INK_MAX_MM` 4,0 (`edges.py`) | nét mực dày tới chừng này → một đường giữa | viền hoạt hình rất dày vẫn ra hai đường → tăng |
| `GAP_MM` 3,0 | khe hở được nối (19/11/2026: 1,5 → 3,0, chủ dự án muốn nét liền hơn) | còn đứt → tăng; nối nhầm hai nét → giảm |
| `SPUR_MM` 2,4 / 1,6 / 1,0 | râu ngắn hơn chừng này bị cắt | còn râu ở góc chữ → tăng; mất chân linh kiện ngắn → giảm |
| `FDOG_ALONG_MM` 4,0 | làm mượt **dọc** hướng nét (FDoG) | nét đứt → tăng; góc gắt bị tròn → giảm (0 = XDoG thường) |
| `SMOOTH_MM` 0,8 (`trace.py`) | làm mượt đường theo chiều dài | còn run → tăng |
| `OUTLINE_MIN_LEN_MM` 6,0 (`styles.py`) | bỏ nét viền ngắn hơn (19/11/2026: 8 → 6 mm, cùng GAP 1,5 → 3,0) | còn gạch vụn → tăng; mất chi tiết nhỏ → giảm |

## 5. Preset với ảnh thật
Vẽ mỗi preset bằng một ảnh đúng loại (A5), ghi thời gian thật / ước tính, số lần nhấc bút, nhận xét.

| Preset | Ảnh thử |
|---|---|
| Chân dung | ảnh người thật, mặt đủ sáng |
| Ảnh 2D | hoạt hình, truyện tranh, hình vẽ, ảnh chụp màn hình |
| Phong cảnh | trời mây + nhà, cảnh đêm có đèn, hoàng hôn |
| Schematic | sơ đồ mạch, bản vẽ scan nền xám, mạch in đơn giản |

Ảnh đêm vốn tối nên tốn mực và thời gian: thử tăng gamma (1,3–1,5) và bật khử nhiễu. Ảnh nhỏ (< ~1000 px) ra nét thô: dùng ảnh gốc, hoặc **Cắt ảnh** sát chủ thể.

## 6. Bài thử máy (sau khi chốt nét)
Mục đích: vẽ nhanh hơn mà nét không xấu, máy không mất bước. **Mỗi bài một tờ giấy mới.**
- **Thông số máy** (gia tốc, `junction_deviation`, tốc độ tối đa): Cài đặt → Cấu hình máy → **Áp dụng** (chỉ RAM; chốt rồi mới **Lưu vào mạch**). Firmware tự chặn mọi lệnh ở `max_rate_mm_per_min`: muốn thử 10000 thì nâng tốc độ tối đa X, Y trước.
- **Thông số G-code** (chờ, tốc độ vẽ / di chuyển / bút): tab Tạo bản vẽ. **Z bút**: Cài đặt → Cấu hình máy, mục App.
- **Tạo tờ thử:** Cài đặt → **Tờ thử / hiệu chỉnh** (thành bản thảo trong Hàng đợi): tờ hiệu chỉnh bút, **tờ nhấc bút** (chờ 0 / 0,02 × Z3 × hạ 2000 = 2 hàng; hàng k có k chấm ở đầu; "Dùng hàng N" ghi vào Z G-code / chờ / tốc độ hạ), **7.2** (tốc độ thử mặc định 8000), **7.5**. Bài 7.1 chính là tờ nhấc bút; 7.3, 7.4, 7.6 đã xong nên bỏ nút, tạo bằng `python tools/make_test_gcode.py` (ghi vào `export\test-gcode\`, không lên Git).
- Ô **"Tốc độ hạ bút"** (mặc định 2000): hạ chậm, nhấc nhanh (bút hạ bằng trọng lực); thử 600–1500 nếu bút còn nảy hoặc loang đầu nét.

| # | Bài | Cách làm | Nhìn gì | Tình trạng |
|---|---|---|---|---|
| 7.1 | Chi phí nhấc bút | 100 gạch 2 mm; thời gian thật ÷ 100 = một chu kỳ; đổi chờ, Z nhấc | kéo vệt, hụt đầu nét, bút nảy | ✅ chờ **0**, Z**3**, hạ **2000** |
| 7.2 | Mất bước | vẽ dấu + ở góc → chạy nhanh nhiều lần → vẽ lại dấu +; **7.2b**: mỗi tốc độ một cặp dấu, 10 vòng G1 (~1,3 m) giữa hai lần vẽ | hai dấu trùng khít = không mất bước | ✅ 6000 (03/11); 7000–10000 đạt (17/11) |
| 7.3 | Gia tốc + góc | răng cưa bước 2 mm, mỗi tốc độ một hàng; đổi gia tốc / junction rồi chạy lại | gợn sóng sau góc; giọt mực ở góc | ✅ gia tốc **3000** (không tăng thêm, để giữ ngòi bút và linh kiện); junction **0,03** (17/11, nhẹ máy; bút xịn, giấy mượt ít đọng mực) |
| 7.4 | Tốc độ vẽ từng bút | dải đường thẳng 7000 / 8000 / 9000 / 10000, chụp cận đo bề rộng nét | tốc độ cao nhất mà nét chưa nhạt / đứt | ✅ **8000** (10000 được ở đoạn dài) |
| 7.5 | Vệt kéo khi đi xa | hai chấm cách 240 mm, G0 qua lại 5 lần, mỗi lần một mức chờ; đổi Z 3 / 4 / 5; giấy phẳng | vệt mảnh nối hai chấm = bút chưa rời giấy | bỏ 17/11 (không cần) |
| 7.6 | Đoạn ngắn và cung G2 | 5 vòng tròn R10 chồng 12 lần: G1 đoạn 1 / 0,5 / 0,25 / 0,1 mm rồi G2; mở Biểu đồ xem hàng đợi từng vòng | tốc độ thật tụt không; hàng đợi cạn (chấm đỏ) | ✅ 13/11: G1 6,0 / 11,6 / 23,3 / 60,7 s, **G2 5,7 s** → dùng G2/G3 (09 D12) |

**Đọc bộ đệm khi chờ 0:** chờ 0,02 thì mỗi lần nhấc có `G4` nên hàng đợi tụt về 0; chờ 0 không có `G4` thì hàng đợi phải **không tụt** tại chỗ nhấc (✅ 13/11: đầy suốt; mặc định 0). Cần đã gõ `$10=3`.

## 7. Ghi kết quả
Kết quả chốt ghi ở [02](02_PHAN_CUNG_MAY.md) mục 6 (máy) và sửa số mặc định trong mã (cột "Chỉnh ở đâu"); đánh dấu xong ở [11](11_VIEC_CAN_LAM.md). Bảng ghi từng buổi (03/11 → 13/11) nằm ở 02 mục 6, không lặp ở đây.

## 8. Mẫu gửi kết quả
Chép khối dưới, điền sau dấu `:`, bỏ trống chỗ không đo được. Gửi kèm **ảnh cả tờ** (chụp thẳng, đủ sáng) và **ảnh cận** nếu bài cần. Đặt thước kẻ cạnh chỗ chụp cận để đọc bề rộng nét.
```
Ngày / Bút / Giấy (loại, mặt bóng-nhám):
Bài (mã ở danh sách trên):
Có đổi gì so với mặc định (Z, chờ, tốc độ, gia tốc):
Kiểu tô / preset / khổ:
Thời gian thật / ước tính / số lần nhấc bút:
Nhận xét bằng mắt (đậm nhạt, râu, loang, đọng mực ở chỗ quay đầu):
Máy: kêu lạ / rung / nóng tay (động cơ X Y, driver) / mất bước (lệch mm, hướng):
Terminal có `error` không:
```
Bài tông (A5): thêm *bút · giấy · tốc độ · kiểu gạch · ô nào bắt đầu bết mực*. Bài bề rộng nét (mục 1, 7.4): thêm *dải sát nhất còn đặc (mm)*, *bề rộng nét đo ảnh cận ở từng tốc độ*, *tốc độ nào bắt đầu nhạt / đứt*.

## 9. Đo trên máy tính (không cần in giấy)

> Dùng khi cần biết **máy tính nào chậm ở bước nào** — nhất là lúc quyết định có phải viết lại phần tô nét hay không.
> Số đo ở đây **không nói gì về độ đẹp trên giấy**; muốn chốt tông thì vẫn phải in (mục A).

### 9.1 Bộ công cụ đo có sẵn (7 cái + 1 công cụ dò thư viện)
Chạy bằng Python của phần mềm: `cd backend` rồi `.\.venv\Scripts\python.exe ..\tools\<tên>.py` (máy chạy bằng `Python\` mang theo thì dùng Python đó).

| Công cụ | Đo gì | Cần gì để chạy | Ngày 22/11/2026 |
|---|---|---|---|
| `ink_sim.py` | Sai tông / chiều dài nét / thời gian của từng kiểu tô trên ảnh thử tổng hợp (80 × 50 mm) | không cần gì | ✅ chạy được, số ở 9.3 |
| `ink_real.py` | Như trên nhưng trên **ảnh thật**, so 0 / 1 / 2 / 3 lượt sửa sai | một ảnh | ✅ chạy được (ảnh mẫu `skimage`), số ở 9.3 |
| `tone_read.py` | Đọc ảnh chụp **tờ Thang tông** ra 16 ô độ đậm (mục 2) | ảnh chụp tờ tông | ⏳ chưa có ảnh tờ tông mới; mới kiểm chạy `--help` |
| `log_read.py` | Đọc `data/job_logs/<id>.csv`: hàng đợi cạn lúc nào, tốc độ thật | tệp CSV (chỉ có sau khi vẽ thật) | ⏳ `data/job_logs` hiện chỉ có 4 tệp `.json`, **chưa có CSV** nên chưa chạy |
| `style_preview.py` | Vẽ thử một ảnh với nhiều kiểu ra PNG + số nét, thời gian | một ảnh (hoặc `astronaut` / `cat`) | ✅ chạy được, ghi `export/preview/` |
| `make_test_gcode.py` | Sinh 11 tệp G-code cho các bài thử máy (mục 6) | không cần gì | ✅ chạy được, ghi `export/test-gcode/` |
| `export_context.py` | Xuất mã / tài liệu gọn cho AI, sinh lại `docs/AI_CODEMAP.md` | không cần gì | ✅ chạy được (`--list`, `--map`) |
| `probe_vpype.py` | In phiên bản `vpype` + các gói hình học (dò lỗi cài đặt) | không cần gì | ✅ đã chuyển từ `backend/tools/` sang `tools/`, chạy được |

### 9.2 Đo thời gian + RAM đỉnh: `tools/do_thoi_gian.py` (mới 22/11/2026)
```powershell
cd backend
.\.venv\Scripts\python.exe ..\tools\do_thoi_gian.py --label laptop        # ảnh thử tổng hợp, khổ A5, 5 kiểu
.\.venv\Scripts\python.exe ..\tools\do_thoi_gian.py --image ..\data\anh.jpg --paper a4 --label mini-pc
.\.venv\Scripts\python.exe ..\tools\do_thoi_gian.py --styles crosshatch,flow --refine 0
```
- In một bảng ra màn hình và ghi **2 tệp** vào `export\` (không lên Git): `do-thoi-gian-<tên máy>-<ngày>.md` (đọc bằng mắt) và `.json` (đưa cho AI).
- Đo: giây của **từng bước** (đọc ảnh · chỉnh tông · tô nét · tối ưu nét), giây **sinh G-code**, số nét, chiều dài nét, số dòng G-code, **RAM đỉnh** (mức tăng so với RAM nền), thông tin máy (CPU, số luồng, RAM, hệ điều hành, phiên bản Python và các gói).
- Nghĩa các cột: **Tạo nét** = tổng thời gian từ lúc bấm nút tới lúc có nét; cột **Tô** thường chiếm gần hết. **Vẽ ước tính** là thời gian máy vẽ, không phải thời gian tính.
- Lúc dùng thật, bước ảnh → nét chạy ở **tiến trình con** (`isolated.py`) nên cộng thêm thời gian khởi động (đo riêng, ~0,35 s trên laptop).
- Công cụ **nạp sẵn thư viện `vpype`** trước khi đo (lần đầu nạp ~0,7 s), nên kiểu đầu bảng không bị đội thời gian; hai máy đo cùng cách thì so được.

**Số laptop 22/11/2026** (Intel i5-9400F, 6 luồng, 15,9 GB, ảnh thử 1000 × 1400, A5, bút 0,5, sửa sai 1 lượt):

| Kiểu | Tạo nét | Đọc | Tông | Tô | Tối ưu | G-code | Số nét | Dài | Dòng G-code | RAM đỉnh thêm |
|---|---|---|---|---|---|---|---|---|---|---|
| Gạch chéo (`crosshatch`) | 0,83 s | 0,04 | 0,00 | 0,33 | 0,46 | 0,16 s | 396 | 39,2 m | 3 859 | +24 MB |
| Theo dáng (`flow`) | 2,31 s | 0,02 | 0,00 | 1,84 | 0,44 | 0,39 s | 201 | 23,9 m | 6 519 | +24 MB |
| Sóng biến thiên (`wave_am`) | 0,49 s | 0,02 | 0,00 | 0,32 | 0,15 | 1,43 s | 173 | 34,6 m | 24 651 | +44 MB |
| Xoắn ốc (`spiral`) | 0,12 s | 0,02 | 0,00 | 0,05 | 0,05 | 0,96 s | 47 | 25,3 m | 16 108 | +55 MB |
| Nét viền (`outline`) | 0,34 s | 0,02 | 0,00 | 0,31 | 0,01 | 0,00 s | 9 | 0,5 m | 91 | +55 MB |

Đọc: **Theo dáng là kiểu tạo nét chậm nhất** (1,84 s ở bước tô). Ở **Sóng / Xoắn ốc**, *sinh G-code* tốn hơn cả *tạo nét* vì hai kiểu này ra rất nhiều dòng (16 000–25 000 dòng). RAM đỉnh cộng dồn qua các kiểu nên số ở dòng dưới là **cận trên** của kiểu đó; chạy lại cùng máy thì số dao động khoảng ±10 %.

### 9.3 Số mô phỏng hôm 22/11 và chỗ lệch so với tài liệu
`ink_sim.py` (ảnh thử tổng hợp; "sai số" = lệch độ phủ trung bình, nhỏ là đúng tông):

| Kiểu (ink_sim) | Sai số | Sai mắt | Bậc | Dài (mm) | Số nét | Phút |
|---|---|---|---|---|---|---|
| Gạch chéo mềm | 0,030 | 0,077 | 0,041 | 3 050 | 111 | 1,07 |
| Theo dáng | 0,028 | 0,091 | 0,085 | 2 388 | 52 | 0,69 |
| Sóng biến thiên | 0,049 | 0,120 | 0,019 | 2 482 | 34 | 0,64 |
| Xoắn ốc (bản mới) | 0,060 | 0,060 | 0,052 | 2 341 | 10 | 0,51 |
| Sóng mềm (kiểu ẩn) | 0,027 | 0,092 | 0,048 | 2 674 | 128 | 1,07 |

`ink_real.py` trên ảnh thật (`skimage`: `retina` 1411 px, `astronaut` 512 px, `chelsea` 300 px; A4 trừ lề, bút 0,5):

| Ảnh · kiểu | Sửa sai 0 | Sửa sai 1 | Dài nét | Nhận xét |
|---|---|---|---|---|
| retina · Gạch chéo | 0,068 | **0,043** | 47,2 → 50,3 m | 1 lượt bớt 37 % sai số |
| chelsea · Gạch chéo | 0,136 | **0,063** | 21,1 → 27,1 m | ảnh nhỏ (300 px) nên nét thô, sai số cao |
| retina · Sóng biến thiên | 0,047 | **0,034** | 42,4 → 44,4 m | |
| chelsea · Sóng biến thiên | 0,056 | **0,028** | 21,0 → 23,4 m | |
| retina · Theo dáng | 0,057 | (không áp) | 32,1 m | kiểu này không có vòng sửa sai |
| retina · Xoắn ốc | 0,100 | (không áp) | 34,5 m | bản viết lại 22/11, **chưa có số chuẩn** |
| retina · Nét viền | — | — | 1,1 m · 24 nét | kiểu Viền **không vẽ theo độ đậm** nên không đo tông |

**Chỗ lệch hơn 10 % so với số trong [06](06_THUAT_TOAN_XU_LY_ANH.md)** (số tài liệu ghi 14–17/11, mã đã đổi 18–22/11 nên chưa rõ do đâu):

| Số tài liệu | Nay | Lệch |
|---|---|---|
| Sóng biến thiên sai tông **0,027**, bậc **0,012** (06 mục 8.9) | 0,049 / 0,019 | **+81 % / +58 %** (tệ hơn) |
| Theo dáng "sai mắt" **0,043** (06 mục 8.10) | 0,091 | **+112 %** (tệ hơn) |
| Gạch chéo sai tông **0,071** (06 mục 6.3, trước khi có chuyển mức mềm) | 0,030 | −58 % (tốt hơn) |
| Sóng mềm / zigzag mềm **0,051** (06 mục 8.7) | 0,027 / 0,066 | −47 % / **+30 %** |

Ghi chú: **kiểu Viền và Xoắn ốc bản mới chưa có số chuẩn** để so. Trong `ink_sim`, dòng "+ sửa sai" nhắm độ phủ **đã qua đường cong tông** nên sai số so với độ đậm ảnh gốc có thể **tăng** dù nét đúng hơn — muốn thấy vòng sửa sai có ích thì đọc `ink_real`.

### 9.4 Gửi lại số sau khi đo
1. Chạy đúng một lệnh ở 9.2 trên **laptop** và trên **MiniPC** (cùng ảnh, cùng `--paper`).
2. Gửi **2 tệp** của mỗi máy (`export\do-thoi-gian-*.md` và `.json`) — trong đó đã có CPU, RAM, thời gian từng bước, RAM đỉnh.
3. Nếu định thử lại một kiểu tô: chạy thêm `ink_sim.py` trước và sau khi sửa, gửi **cả hai bảng** (nêu số trước / sau).
