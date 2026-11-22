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

### A. In giấy
Thuật toán đã tạm ổn. **Chân dung bỏ khỏi danh sách**: bạn tự chỉnh thông số khi xem bản nháp trên khung vẽ; chỉ gửi ảnh khi cần AI chỉnh hằng số bên trong.
| # | Bài | Chọn gì | Giấy | Nhìn và ghi |
|---|---|---|---|---|
| A1 | **Ảnh 2D** + **Nét viền** | ảnh hoạt hình, preset Ảnh 2D; rồi kiểu Nét viền (tích / bỏ tích "Dùng FDoG"), A5 | A4 + A5 | mắt / mũi có khung không; má và nền sáng có **trống quá** không (→ hạ `HATCH_WHITE`); viền có liền, mềm không; thiếu nét → Chi tiết viền "Nhiều", vụn → "Ít" |
| A2 | **Phong cảnh** | ảnh phong cảnh tối + ảnh trời mây, preset Phong cảnh | A5 | ô đậm nhất đã gần đen chưa; lớp gạch thẳng ở vùng đậm có làm mất vẻ mượt không (không thích → AI tắt `AM_DARK_LAYER`); máy có rung ở sóng dày không (→ `AM_SPACING_LINES` 4 → 3); **chụp cận mép khối** xem còn giọt mực ở chỗ quay đầu không |
| A3 | **Vùng chủ thể** | ảnh có nền rối (rèm, nước), khoanh elip quanh người, nền còn 50 % rồi thử 30 % | A5 | nền thưa đủ để chủ thể nổi chưa; mép vùng có lộ thành vòng không; thời gian / mực bớt bao nhiêu |
| A4 | **Tờ tông** (đường cong tông) | **Thang tông** (mục 2): kiểu **Gạch chéo** rồi **Xoắn ốc**; tùy chọn: bút UB-155 0,38 | A6 | 5 bậc đậm nhạt cách đều chưa (16 ô gom thành ~5 bậc là đúng); gửi ảnh gốc, AI đo bằng `tools/tone_read.py` |
| A5 | **Sửa sai tông** (mới 17/11) | một ảnh chân dung, cùng preset Chân dung, ô **Sửa sai tông** = **0** rồi **1** (rồi 2 nếu muốn), cùng khổ | A5 ×2 | so hai tờ cạnh nhau: tờ 1 lượt có đúng đậm nhạt hơn không (vùng giữa, da), có đậm lên quá không; nét có rối hơn không; thời gian thật (dự tính +4–8 %). Thấy đậm quá: hạ gamma hoặc để 0 |
| A7 | **Tờ tông cho 3 bản mới** (22/11) | **Thang tông**: (1) Gạch chéo + ô **Bỏ giới hạn** · (2) Theo dáng + **Bỏ giới hạn** · (3) **Xoắn ốc** viết lại — bút UM-100, A6 mỗi tờ | A6 ×3 | 5 bậc đậm nhạt cách đều chưa; ô 0,05–0,35 của theo dáng **đã tách tông** chưa (19/11 dính một mức ~0,3); xoắn ốc mới có ra mảng đậm nhạt theo độ đậm không. Gửi ảnh gốc, AI đo bằng `tools/tone_read.py` |
| A8 | **Chế độ Bỏ giới hạn trên 4 ảnh** (22/11) | 2D (mặt, tai, tay) · mèo (lông, mắt) · phong cảnh (nhà gỗ, mây, cây) · chân dung — preset **Siêu chi tiết**, A4 | A4 ×4 | chi tiết nhỏ còn không; mực có bết / loang ở chỗ gạch dày; **thời gian thật** so với ước tính (2D 977 nét / 20,2 phút · mèo 849 / 9,2 · phong cảnh 1 041 / 29,3) |
| A6 | **Theo dáng ảnh** (⏳ **chờ ảnh thật**, làm cuối) | ảnh người + ảnh thú (lông rõ), kiểu Theo dáng ảnh | A4 | đã chỉnh 17/11 theo nhận xét: nền tối thưa bớt (`FLOW_MAX_COVER` 0,9 → 0,85), vùng sáng dày thêm (`FLOW_MAX_SEP_LINES` 5 → 4,5, `FLOW_WHITE` 0,1 → 0,08); nét chạy theo tầm nhìn trung bình đã ổn. Khi có ảnh thật: vùng tối còn **đặc** / **vụn**, vùng sáng đủ nét chưa (→ báo AI chỉnh) |

**Kết quả in giấy 18/11/2026** (chủ dự án báo bằng ảnh, chưa có số; chưa đổi hằng nào):
| Bài | Đã in | Nhận xét của chủ dự án (và điều tôi thấy trên ảnh) |
|---|---|---|
| A4 tờ tông | Thang tông, **UB-155**, A5 | nét không đủ đậm vì cụm bút **thiếu lực tì** ngòi, "có lẽ không chuẩn lắm"; số đo tông từ tờ này kém tin cậy; UB-155 **dừng ở đây** |
| A1 Ảnh 2D | hoạt hình (Tom), kiểu 2D | chưa nhận xét |
| A5 Sửa sai tông | chân dung, bút **UM-100**: trái = **1 lượt**, phải = **2 lượt + nét viền** | **Chốt (chủ dự án): 1 lượt, không viền tốt hơn**; viền gây rối ở ảnh nhiều góc nét, lượt 2 làm đậm hơn bình thường (mặc định giữ 1 lượt, preset Chân dung giữ không viền). Bản phải đậm và rõ nét mặt hơn; trên ảnh, đường viền ở áo / cổ nhìn **rối như vết nứt** (chưa kiểm là do viền hay do 2 lượt). Nhật ký chạy (CSV, ~901 s) là của bản phải; trong đó hàng đợi **cạn hai lần** (~2 s ở giây 117, ~13 s ở giây 527–540: máy bò chậm, bút còn hạ), nguyên nhân chưa rõ (máy tính / mạng gửi chậm) |
| A6 Theo dáng ảnh | mèo, **Theo dáng ảnh** + 2 lượt + elip tập trung | chưa nhận xét |
| A3 Vùng chủ thể | ảnh hoa, **Xoắn ốc**, nền ngoài vùng **50 %** | "cũng được": phần bên phải mờ đi chấp nhận được |
| A2 Phong cảnh | **Sakura nhập 0,4** (đo thật là **0,5**, 02) | nét đậm, chưa rõ; **phân vùng** (các mảng sáng / tối) cần cải thiện. Đậm hơn dự kiến một phần vì khoảng cách nét tính theo 0,4 trong khi nét thật 0,5 |

### B. Máy (còn 2 bài; B1 bản vẽ G2/G3, B2 servo, tab Điều khiển mượt đã xong 18/11, dồn về [11](11_VIEC_CAN_LAM.md) mục 3 và [02](02_PHAN_CUNG_MAY.md) F16)
| # | Bài | Làm | Nhìn và ghi |
|---|---|---|---|
| B3 | **Tạo nét chậm** (laptop yếu; tab Điều khiển đã mượt 18/11) | tạo nét một ảnh A5 nhiều nét; thuật toán **Tạo nét** còn chậm, nhiều khả năng do máy | **cách lấy thông số** (ghi 4 dòng): (1) tên CPU + RAM laptop (Cài đặt Windows → System → About); (2) số dòng G-code (dòng G-code ở tab Tạo bản vẽ); (3) thời gian từ lúc bấm **Tạo nét** tới lúc xong (đếm giây); (4) nếu còn khựng: F12 → Performance → Record 5 giây khi chạy, chụp màn hình |
| B4 | **Tiếng "khực" ở góc trái** (18/11/2026, **đang tạm hoãn**, chờ xem kết quả vẽ) | xảy ra sau khi chỉnh đai; chỉ với **zigzag / đan chéo** (nét 45°); sóng, theo dáng, xoắn ốc êm hoặc kêu nhỏ. Gia tốc 2800 + junction 0,01 thì bớt kêu. Đã loại: nguồn 23 V, TMC có quạt nhiệt ổn, đẩy tay tắt nguồn mượt, hai đai căng đều, tốc độ 10000 đã dùng từ trước. Vì sao nghi 45°: CoreXY có motor kéo `x+y` và `x−y`; nét 45° thì **một motor làm hết**, nhanh 1,41×, gia tốc 2× (giới hạn gia tốc theo trục X/Y của FluidNC), motor kia đứng yên; zigzag / đan chéo ~90 % chiều dài ở hướng đó, sóng 26 %, flow 11 %, xoắn ốc 21 % (mô hình, chưa đo máy thật). Thử, mỗi bài đổi một thứ: **(1)** chạy bài kêu nhưng **nhấc bút cao**; **(2)** giữ 10000, hạ gia tốc 1500; **(3)** khối nét 45° ở 4 góc + giữa giấy; **(4)** nét chỉ ↗ rồi chỉ ↖ ở góc trái (mỗi hướng một motor); áp ống giấy cuộn vào thân motor trái / phải để nghe, tay xa đai. Kiểm: vít puly dưới lực, vít chân motor, dây / xích / cần công tắc gần góc trái | kêu theo **vị trí** (cơ khí ở đó) hay theo **hướng nét** (motor / đai bên đó) hay theo **gia tốc** (đảo chiều gấp); có mất bước không (về điểm xuất phát, dấu trùng khít). Nếu kết luận là tải: cân nhắc cho phần mềm hạ tốc độ nét gần 45° hoặc đổi góc tô mặc định (cần chốt với chủ dự án, đổi hành vi) |

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
