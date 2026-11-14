# 07 — Thử nghiệm và hiệu chỉnh trên giấy

> Dành cho người vận hành máy (không cần lập trình). Mục tiêu: chốt các con số mặc định (bề rộng nét, khoảng cách, số mức, gamma,
> preset, tốc độ) **bằng bản in thật**, vì màn hình không cho biết mực loang, giấy thấm, bút khô ra sao.
> Ký hiệu: ✅ đã chốt bằng bản in · 🧪 mới thử bằng ảnh mẫu / mô phỏng · ⏳ chưa làm.
> Kết quả thử máy đã có: [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) mục 6.
>
> **Cách dùng:** xem việc cần thử ở [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md) mục 3 → làm theo hướng dẫn bài đó ở tệp này →
> chép **mẫu ở mục 8**, điền số, gửi kèm ảnh. Không cần tự sửa mã hay tài liệu.

## 0. Nguyên tắc
- **Mọi quyết định về độ đậm phải nhìn tờ giấy.** Khung xem trước trên web chỉ để kiểm hình học (đủ nét, đúng chỗ, không vượt khổ).
- **Mỗi lần chỉ đổi một thông số.** Cùng giấy, cùng bút, cùng tốc độ.
- **Ghi số ở góc tờ** (bút, khoảng cách, số mức, gamma, preset, tốc độ, ngày) rồi chụp ảnh.
- Làm theo thứ tự: mục trước chốt con số mục sau dùng. **Mỗi bút làm riêng** (UB-155, UM-100, Sakura 0,4, bút bi 0,5).
- **Từ 11/11/2026 ô "Bút vẽ" ở tab Tạo bản vẽ ghi thẳng bề rộng nét đo trên giấy** (không còn nhân 1,1). Chọn bút theo tên; bút chưa có trong danh sách hoặc vừa đo ra số khác thì chọn **Tùy chọn** và gõ số đo được.

## Kế hoạch tuần sau (từ 16/11/2026; làm từ trên xuống, bước 1–4 quan trọng nhất)
Giấy Ivory, mặt bóng như 13/11. Bút **Sakura 0,5** trừ khi ghi khác. Kết quả 13/11 và lý do từng thay đổi: [09](09_QUYET_DINH_THIET_KE.md) C10, D10–D12, P19–P26.

**Chuẩn bị (một lần):**
1. Tắt phần mềm, mở lại, trình duyệt **Ctrl+F5** (bản mới: G2/G3, chờ 0, đường cong tông, kiểu "Đan chéo + theo dáng", XDoG, Thang tông).
2. Tab Tạo bản vẽ, khối G-code: ô **chờ** gõ **0** (trình duyệt còn nhớ 0,02). Vẽ / di chuyển 8000, Z3, hạ 2000.
3. Terminal gõ `$10` → phải là `$10=3` (để Biểu đồ có hàng đợi).
4. Chọn lại preset sau khi mở (từ 14/11/2026 còn 4 preset: Chân dung, Ảnh 2D, Phong cảnh, Schematic; 09 P29).

| Bước | Làm gì | Ở đâu / chọn gì | Giấy | Ghi lại |
|---|---|---|---|---|
| 1 | **Chân dung kiểu mới** | ảnh em bé, preset **Chân dung** (= Đan chéo + theo dáng, gamma 1), **A6** rồi **A4** | 2 tờ | so với tờ đan chéo 13/11: mắt / mũi / mép mặt có tách khỏi nền không; đường cong có lạc lõng như viền dán không; **có quá đậm không** (đường cong tông làm vùng trung bình đậm hơn → quá đậm thì gamma 1,1–1,2 và báo lại); thời gian thật / ước tính; Terminal có `error` nào không (bản vẽ thật đầu tiên có G2/G3) |
| 2 | **Thêm lớp viền XDoG** | như bước 1, **A4**, tích **"Thêm lớp viền phác họa lên kiểu tô"** | 1 tờ | có che bớt móc chữ U ở vùng sáng không, có rối không; thiếu nét → Chi tiết viền "Nhiều", vụn → "Ít" |
| 3 | **Phác họa ảnh** | preset **Phác họa ảnh** (Nét viền + XDoG), ảnh em bé + ảnh thú, **A5**; nếu còn giấy: cùng ảnh, kiểu Nét viền **bỏ tích** XDoG | 2–3 tờ | XDoG có rõ mắt / mũi / miệng hơn không, có mất viền nào (mũ trắng trên nền sáng: XDoG chỉ nhìn độ sáng) |
| 4 | **Sóng biên độ có lớp đậm** | Cài đặt → Tờ thử → **Thang tông** → tab vẽ: kiểu **Sóng biên độ**, gamma 1, tắt CLAHE / khử nhiễu, **A6**; rồi ảnh phong cảnh tối, preset **Phong cảnh**, **A5** | 2 tờ | ô đậm nhất đã gần đen chưa (bản cũ ~0,71); lớp gạch thẳng ở vùng đậm có làm mất vẻ mượt không (không thích → AI tắt `AM_DARK_LAYER`); máy có rung ở sóng dày không; thời gian / số lần nhấc (Biểu đồ, nay đếm theo Z) |
| 5 | **Kiểm đường cong tông** | **Thang tông**, kiểu **Đan chéo + theo dáng** rồi **Xoắn ốc**, gamma 1, tắt CLAHE / khử nhiễu, Số mức 5, **A6** | 2 tờ | 5 bậc đậm nhạt có cách đều nhau không (16 ô gom thành ~5 bậc là đúng). Chụp như mục 2b, gửi ảnh gốc → AI đo, lệch thì sửa bảng |
| 6 | (nếu còn giờ) **UB-155 đen** | **Thang tông**, kiểu Đan chéo + theo dáng, ô Bút vẽ UB-155 (0,38), **A6** | 1 tờ | như bước 5: đạt thì dùng chung đường cong, lệch thì AI thêm bảng riêng cho bút này |
| 7 | (nếu gặp) **Servo sau Home** | — | — | bút tụt sau Home: Terminal có dòng `pen re-lift not sent` không |

**Gửi lại:** ảnh từng tờ (thẳng góc, đủ sáng, không flash; tờ Thang tông thấy đủ 3 ô mốc đen) + bảng: bước · kiểu / preset · khổ · thời gian thật / ước tính · số lần nhấc · nhận xét. Có `error` ở Terminal thì chụp lại.

## Kế hoạch ngày 13/11/2026 (làm từ trên xuống; hết giờ thì dừng ở đâu cũng được, bước 1–5 quan trọng nhất)
Giấy Ivory 250 g/m², cùng một mặt giấy cho cả ngày (mặt đã chọn 12/11). Bút **Sakura 0,5** cho mọi tờ đo tông và so kiểu tô.

**Chuẩn bị (một lần, ~5 phút):**
1. Tắt phần mềm, mở lại (bản mới có tờ 7.6, tờ tông mới, kiểu "Theo dáng ảnh"). Mở trình duyệt, bấm **Ctrl+F5**.
2. Bật nguồn máy, nối, **mở khóa chuyển động**.
3. Terminal gõ `$10` → phải trả `$10=3`. Nếu không: gõ `$10=3` rồi gõ lại `$10`. Không có số này thì Biểu đồ không có đường "hàng đợi".
4. Tab Tạo bản vẽ, khối G-code: vẽ **8000**, di chuyển 8000, Z nâng 3 / hạ 0, hạ bút 2000, chờ **0,02** (sau bước 2 đổi thành **0**, xem kết quả dưới bảng). Ô **Bút vẽ** = **Sakura (0,5)**.
5. Từ 12/11 **không còn** nút Xem trước + ô tích ở tab Điều khiển: nạp bản thảo xong nhìn khung vẽ rồi bấm **▶ Chạy**.

| Bước | Làm gì | Ở đâu / chọn gì | Giấy | Ghi lại |
|---|---|---|---|---|
| 1 | **Servo sau khi bật nguồn / Home** | Bật nguồn mạch → nối → bấm **Home** → bấm một lệnh bất kỳ (jog nhỏ). Làm lại 3 lần. Lần cuối: chạy xong một tờ bất kỳ rồi Home | không | sau Home phần mềm tự nhích bút xuống 0,5 mm rồi lên lại (để servo giữ chặt): có thấy nhích không; bút có tự tụt về giữa không; nếu có: lúc nào (sau bật nguồn / sau Home / sau tác vụ), Terminal có dòng "pen re-lift not sent" không |
| 2 | **Bộ đệm khi chờ nhấc bút = 0** | Cài đặt → Tờ thử → **Tờ nhấc bút**: tích chờ **0** và **0,02** (bỏ tích mức khác), Z nhấc chỉ **3**, hạ chỉ **2000** → 2 hàng. Tạo → tab Điều khiển nạp → Chạy. Xong: khung 2D bấm **Biểu đồ**, chọn lần chạy vừa xong | 1 tờ | hàng chờ 0: đầu nét có hụt / loang không, có kéo vệt không; Biểu đồ "hàng đợi": tụt về 0 ở hàng nào (chụp màn hình); thời gian cả tờ |
| 3 | **7.6 Đoạn ngắn / cung G2** | Cài đặt → Tờ thử → Bộ thử máy → nút **7.6 Đoạn ngắn / cung G2** (dùng tốc độ vẽ 8000 đang đặt) → nạp → Chạy | 1 tờ | Biểu đồ: tốc độ thật và hàng đợi **từng vòng** (5 vòng từ trái sang: đoạn 1 / 0,5 / 0,25 / 0,1 mm, rồi cung G2), vòng nào có chấm đỏ (cạn); trên giấy: vòng nào có cạnh góc, rung, vệt đậm; máy có kêu khác thường ở vòng nào |
| 4 | **3 tờ hiệu chỉnh tông** | Cài đặt → Tờ thử → **Tờ hiệu chỉnh tông**: Bề rộng nét **0,5**, khổ **A6**, Kiểu gạch lần lượt **Đan 3 hướng**, **Sóng biên độ**, **Xoắn ốc** (3 bản thảo) | 3 tờ A6 | ô nào bắt đầu bết mực / ướt giấy. Chụp theo mục 2b (thẳng góc, ánh sáng đều, không flash, thấy đủ 3 ô đen + chữ F) |
| 5 | **So 3 kiểu tô chân dung** | Tab Tạo bản vẽ: ảnh em bé (hoặc một ảnh người rõ mặt), preset **Chân dung**, khổ **A6**. Tạo nét → Lưu bản thảo. Rồi **chỉ đổi ô Kiểu tô**: **Đan 3 hướng (60°)** → Lưu; **Theo dáng ảnh (thử nghiệm)** → Lưu. Vẽ cả 3 | 3 tờ A6 | mỗi tờ: thời gian thật / ước tính (số ở tab Điều khiển), số lần nhấc bút (Biểu đồ → bảng tóm tắt), tờ nào giống ảnh nhất, tờ nào có "hồn" nhất, chỗ nào quá đậm / quá nhạt, nét nối gần có để lại vệt không |
| 6 | **Theo dáng ảnh với ảnh thú** | ảnh chân dung chó / mèo (lông rõ), preset Chân dung, Kiểu tô **Theo dáng ảnh**, A6 | 1 tờ | nét có chạy theo lông không, chỗ nào rối / quằn quại, chỗ nào trống, so nhanh với Đan chéo nếu còn giấy |
| 7 | (nếu còn giờ) **Sóng biên độ, đo thời gian** | ảnh phong cảnh, preset **Phong cảnh**, A6 | 1 tờ | thời gian thật / ước tính; Biểu đồ hàng đợi có cạn giữa nét không |

**Kết quả bước 1–3 (13/11/2026):** servo sau Home có lúc tụt về chỗ cũ hoặc giật rồi đứng ở Z5, không ảnh hưởng nhiều ([02](02_PHAN_CUNG_MAY.md) F16). Bước 2: chờ 0 dùng được → mặc định 0. Bước 3: G2 nhanh và đủ tốc, đoạn ngắn G1 chậm vì giới hạn ~125 dòng/giây → phần mềm từ nay ghi nét cong bằng G2/G3 (chi tiết ở mục 6, bài 7.6). Khởi động lại phần mềm để dùng bản mới; ô chờ ở tab Tạo bản vẽ trình duyệt còn nhớ 0,02, gõ **0** một lần. Thời gian thật / ước tính ở bước 5–7 nay so được (ước tính mới tính cả giới hạn dòng/giây).

**Kết quả bước 5–6 (13/11/2026):** em bé A6 (UB-155): đan 3 không đẹp bằng đan chéo; theo dáng nhanh hơn hẳn nhưng ở A6 gần như không ra nét. Thêm hai bức A4 (Sakura, chờ 0): mèo theo dáng 6:21 (ước 7:16), ra hình nhưng quá "nghệ thuật"; em bé đan chéo gamma 1, 13:21 (ước 14:10), đủ đậm nhạt nhưng cứng, mắt / mũi khó phân biệt khi nhìn gần. Hàng đợi đầy suốt, đói lệnh 0 %. → kiểu "Đan chéo + theo dáng" làm mặc định Chân dung ([09](09_QUYET_DINH_THIET_KE.md) P22).

**Về kiểu "Theo dáng ảnh (thử nghiệm)":** nét uốn dọc theo dáng ảnh thay vì gạch chéo cố định, độ đậm liền (không có ô Số mức). Trên ảnh mẫu A5 nó nhấc bút ít hơn đan chéo 40–56 % và nhanh hơn khoảng một nửa, nhưng dùng ít mực hơn nên **có thể nhạt hơn**; chưa có lớp đan thứ hai cho vùng rất đậm. Đây là bản thô để xem nét uốn trông thế nào trên giấy, chưa phải bản cuối. Ô **Góc** vẫn dùng: là hướng nét ở chỗ phẳng không rõ hướng (trán, nền trơn).

**Gửi lại (một lần cuối ngày, theo thứ tự bước):**
1. Bước 1: một dòng "servo: ổn / tụt lúc …".
2. Bước 2, 3: ảnh chụp màn hình Biểu đồ mỗi lần chạy + ảnh giấy chụp cận + thư mục `data\job_logs` (nén lại) hoặc tải CSV từ Biểu đồ.
3. Bước 4: 3 ảnh gốc tờ tông (không chỉnh, không cắt).
4. Bước 5, 6, 7: ảnh từng tờ (cùng góc, cùng ánh sáng) + bảng: kiểu tô · thời gian thật · ước tính · nhấc bút · nhận xét.
5. Thêm nếu có: 2–3 ảnh gốc cho XDoG (em bé, ngược sáng, ảnh tối) và 1–2 ảnh 2D (hình vẽ chụp lại bằng điện thoại, có chỗ tối chỗ sáng).

## Kế hoạch ngày 12/11/2026 (đã làm; giữ để tra cứu)
Giấy Ivory 250 g/m², khổ A6 cho tờ hiệu chỉnh (đỡ tốn mực, tốn giấy). **Bút đỏ không dùng để đánh giá độ đậm** (đỏ trông nhạt hơn đen); chỉ dùng để đo bề rộng nét, loang, đọng mực.

**Chuẩn bị (một lần):**
1. Tab Tạo bản vẽ, khối G-code: tốc độ vẽ **8000**, Z nâng 3 / hạ 0, hạ bút 2000, chờ 0,05 s.
2. Kẹp giấy phẳng, **mặt láng lên trên** trước.
3. Dừng gấp làm bút tụt về giữa (lỗi 11/11, chưa rõ nguyên nhân): nếu gặp lại, ghi lúc đó máy đang làm gì và bấm "Bút lên" bút có lên lại không.

| Bước | Bút | Làm gì (Cài đặt → Tờ thử / hiệu chỉnh) | Ghi lại |
|---|---|---|---|
| 1 | UB-155 đỏ, **mặt láng** | Tờ hiệu chỉnh bút, A6, **cỡ nét đoán 0,3** (dải 0,24 / 0,30 / 0,34 / 0,38 / 0,45 / 0,60 / 0,75 / 0,90 mm) | dải sát nhất còn đặc mà chưa ướt (mm); thước đúng 80 mm? nét có đứt / đọng cuối nét? |
| 2 | UB-155 đỏ, **mặt nhám** | như bước 1, lật giấy | như bước 1 → chọn mặt đẹp hơn, các bước sau dùng mặt đó |
| 3 | UB-155 đỏ | Bài **7.4** tốc độ vẽ, ô "Tốc độ thử" 7000, 8000, 9000, 10000 (trước đó: Cấu hình máy → tốc độ tối đa X, Y = **10000** → **Áp dụng**, chỉ RAM) | tốc độ cao nhất mà nét còn đều, chưa nhạt / đứt. Nếu chốt tốc độ khác 8000 thì làm lại bước 1 ở tốc độ đó (bề rộng nét đổi theo tốc độ) |
| 4 | UB-155 đỏ | Tờ **nhấc bút** (chờ 0,02 / 0,05 / 0,1 × Z 1 / 3 / 5 × hạ 1000 / 2000) | hàng đẹp nhất (đầu nét không hụt, cuối nét không đọng, không kéo vệt) → bấm **Dùng** |
| 5 | UM-100 xanh | Tờ hiệu chỉnh bút, A6, cỡ nét đoán **0,3**, mặt đã chọn ở bước 2 | dải sát nhất còn đặc (mm) |
| 6 | Sakura 0,4 | Tờ hiệu chỉnh bút, A6, cỡ nét đoán **0,4** (dải 0,32 / 0,40 / 0,45 / 0,50 …), làm **cả hai mặt** giấy | dải sát nhất còn đặc mỗi mặt; mặt nào nét đều, không đứt |
| 7 | Sakura 0,4 | Bài **7.2** mất bước rồi **7.3** gia tốc + góc (ô "Tốc độ thử" 7000–10000, max_rate 10000 đã Áp dụng ở bước 3); xong chạm thử động cơ, driver | 7.2: cặp dấu + nào tách đôi; 7.3: hàng nào gợn sau góc / giọt mực ở góc; động cơ nóng tay không |
| 8 | Sakura 0,4 | Tab Tạo bản vẽ: ô **Bút vẽ** = Sakura (hoặc Tùy chọn + số đo ở bước 6), ảnh con mèo, preset Chân dung, **A6**, vẽ 4 tờ: Zigzag tắt "Chuyển mức mềm" · Zigzag bật · Đan chéo · Sóng mật độ | tờ nào đẹp nhất, ranh giới mức còn lộ không, chỗ nào loang / bết |

**Gửi lại:** ảnh chụp cận từng tờ (thẳng góc, đủ sáng) + bảng ngắn: bút · mặt giấy · tốc độ · dải còn đặc (mm) · hàng nhấc bút chọn · ghi chú. AI sẽ sửa bề rộng nét trong danh sách bút (`index.html` ô `draw-pen-width` + `spec.PENS`) theo số đo. Tắt máy thì max_rate quay về số trong mạch; muốn giữ 10000 thì bấm **Lưu vào mạch** sau khi bước 7 không mất bước.
- Tệp G-code thử có sẵn: `python tools/make_test_gcode.py` ghi vào `export\test-gcode\` (không lên Git). Nạp ở tab Điều khiển → Xem trước → Chạy. **Mỗi bài một tờ giấy mới.**

## 1. Bề rộng nét thật: tờ mẫu hiệu chỉnh bút
Tờ có chữ F (kiểm hướng X / Y), thước 100 mm (kiểm tỷ lệ) và **8 dải gạch** có khoảng cách dòng bằng 0,8 / 1 / 1,125 / 1,25 / 1,5 / 2 / 2,5 / 3 **lần cỡ bút** (số nhân, không phải mm; bút 0,4 mm thì 0,32 / 0,40 / 0,45 / 0,50 / 0,60 / 0,80 / 1,00 / 1,20 mm; từ 11/11/2026 dày quanh 0,4–0,5 để tách nét 0,40 với 0,45). Tạo tờ này ở Cài đặt → **Tờ thử / hiệu chỉnh** → "Tạo tờ hiệu chỉnh bút" (chọn khổ **A5** hoặc **A6**; A6 gọn hơn: dải rộng 95 mm, thước 80 mm, vừa lề 5 mm của A6) (hoặc gọi `POST /api/draw/calibration`, gửi `pen_width_mm`).

| Xem gì | Kết luận |
|---|---|
| Thước đúng 100 mm? | ✅ đúng. Sai thì kiểm `steps_per_mm` trước khi làm tiếp |
| Dải **sát nhất còn đặc mà chưa ướt / quăn** | khoảng cách ≈ bề rộng nét thật |
| Dải trông **xám vừa** (đứng 40–50 cm, chưa thấy từng sợi) | ≈ 2 × bề rộng nét (phủ 50 %) |
| Dải thưa nhất còn đọc thành mảng | mức sáng nhất có ý nghĩa |

✅ 03/11/2026, Sakura 0,4, tốc độ 3000: dải 0,5 mm đặc, 0,6 mm gần đặc, 0,8 mm còn sợi → nét thật **~0,55 mm** → `LINE_WIDTH_RATIO = 1.375` (`backend/app/services/drawing/styles.py`). Phần mềm tự suy ra mọi khoảng cách nét từ con số này ([06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md) mục 6).
🔁 11/11/2026: đổi sang giấy **Ivory 250 g/m²** (ít loang) + Sakura 0,4 / **Uniball 150** (~0,35–0,45 mm khi vẽ nhanh) → tạm đặt `LINE_WIDTH_RATIO = 1.1` (nét **0,44 mm** với bút 0,4; dải đậm nhất cách 0,49 mm). Ảnh vẽ ra **nhiều nét hơn ~25 %** so với khi còn 0,55 (lâu hơn tương ứng).
🔁 11/11/2026 (tối): bỏ cách nhân hệ số. `LINE_WIDTH_RATIO = 1.0`, ô **"Bút vẽ"** chọn theo tên bút, mỗi bút mang sẵn bề rộng nét **đo trên giấy**: UB-155 0,30 · UM-100 0,30 · Sakura 0,4 0,45 · bút bi 0,5 0,50 (ba số đầu là ước tính ⏳). Ô "Cỡ nét đoán trước" của tờ hiệu chỉnh chỉ để đặt các dải quanh số đoán.
⏳ Bề rộng nét **phụ thuộc tốc độ, bút, giấy**: in tờ này trên Ivory ở tốc độ vẽ đang dùng (8000) cho từng bút (kế hoạch 12/11 ở trên) → dải sát nhất còn đặc = bề rộng nét → sửa số của bút đó trong danh sách (hoặc chọn Tùy chọn và gõ).

## 2. Thang đậm nhạt: ảnh thử preset (thang tông)
Chỉ làm **một lần cho mỗi bút + loại giấy**, để chốt số cho preset.

1. Cài đặt → **Tờ thử / hiệu chỉnh** → khối **Thang tông** → chọn khổ giấy (A6 / A5 / A4, hoặc giữ khổ đang chọn) → **"Mở ảnh thang tông ở tab Tạo bản vẽ"** (tự chuyển sang tab vẽ, đặt khổ giấy rồi nạp; sau đó bấm Tạo nét): nạp ảnh 16 ô xám 0 → 90 % đen + 3 ô mốc đen + chữ F (từ 13/11/2026 thay ảnh thang xám 11 bậc).
2. Chọn preset **Chân dung** → chờ tạo nét → **Lưu bản thảo** (tên tự thành "Thang tông · Chân dung") → vẽ.
3. Làm tương tự với **Phong cảnh** và **Cận cảnh**. Ba tờ là đủ (Ảnh 2D và Schematic chỉ vẽ viền, thang xám không nói lên gì).
4. Nhìn từng tờ, sửa đúng preset đó theo bảng dưới.

Cần biết: với 5 mức, 11 bậc ảnh được gộp thành **5 bậc trên giấy** (giấy trắng + 4 mật độ: 22 / 45 / 68 / 90 % mực). Hai bậc ảnh kề nhau ra cùng mật độ là đúng thiết kế.

| Thấy gì trên tờ | Sửa trong `frontend/js/views/drawing/presets.js` |
|---|---|
| Hai mật độ kề nhau trông như nhau | giảm `style-levels` 1 bậc |
| Bậc đậm nhất bết mực, giấy ướt | giảm `MAX_COVERAGE` (0,9 trong `styles.py`) hoặc tăng `style-spacing` |
| Cả tờ quá đậm, các bậc giữa gần đen | tăng `image-gamma` 0,1–0,2 |
| Cả tờ quá nhạt | giảm `image-gamma` 0,1–0,2 (không dưới 0,8) |
| Vùng nhạt lộ từng sợi, lổn nhổn | giảm `style-spacing` (mm; trống = 2 × nét thật = 0,88 với bút 0,4) |
| Tông giữa lệch so với dải chuyển liền | ghi lại độ đậm nhìn thấy từng bậc → dùng làm **đường cong tông** ([10_HUONG_PHAT_TRIEN.md](10_HUONG_PHAT_TRIEN.md)) |

## 2b. Tờ hiệu chỉnh tông (đường cong tông theo bút + giấy)
**Từ 13/11/2026:** tờ tông không còn khối riêng trong Cài đặt: dùng **Thang tông** (mục 2) ở tab Tạo bản vẽ, chọn bút + kiểu tô ở đó (kết quả đã qua đường cong tông, tức đo đúng cái mắt thấy khi vẽ thật). Để đo: tắt CLAHE / khử nhiễu, gamma 1, Số mức 5; chụp như bước 4 dưới. Các bước 1–3 dưới là cách cũ (route `POST /api/draw/calibration` sheet = "tone" vẫn còn).
Làm **một lần cho mỗi bút + loại giấy + tốc độ**. Kết quả dùng để chia các mức đậm nhạt cho đều theo mắt (kế hoạch ở [10_HUONG_PHAT_TRIEN.md](10_HUONG_PHAT_TRIEN.md) mục 0.3).

1. Cài đặt → **Tờ thử / hiệu chỉnh** → khối **Tờ hiệu chỉnh tông**: nhập **bề rộng nét** đúng số ở ô Bút vẽ (Sakura 0,50), chọn **khổ A6**, chọn kiểu gạch, bấm **Tạo**.
2. Làm **3 tờ** cho Sakura 0,5 (chủ dự án chốt 12/11/2026): **Đan 3 hướng**, **Sóng biên độ**, **Xoắn ốc**. Zigzag và Gạch chéo **không làm riêng**: dùng tạm đường cong của đan 3 hướng (đan 3 là bản nâng cấp của hai kiểu đó, chênh đậm nhạt chút ít không sao); nhìn bản vẽ thật thấy lệch rõ mới làm thêm (nút vẫn còn trong khối). Cùng mặt giấy, cùng tốc độ 8000, Z3, chờ 0,02 như khi vẽ thật. Sóng biên độ chạy đúng hàm tô thật trên ô đậm đều nên ô nhạt có thể trống / thưa; xoắn ốc tròn nên bốn góc mỗi ô để trống, đo ở giữa ô.
3. Nạp ở tab Điều khiển (khung vẽ hiện ngay) → Chạy.
4. Chụp bằng điện thoại: **thẳng góc**, ánh sáng đều (cửa sổ hoặc đèn trần, tránh đèn chiếu một phía), không chụp có flash, giấy phẳng, thấy đủ 3 ô đen ở góc và chữ F. Mặt giấy láng hay bóng: nghiêng nhẹ để không phản chiếu đèn. Không chỉnh sáng / lọc ảnh. Gửi ảnh gốc.
5. Tờ có 16 ô, đọc từ trái sang phải, trên xuống dưới: độ phủ 0 (giấy trắng) · 5 · 10 · 15 · 20 · 25 · 30 · 35 · 40 · 45 · 50 · 55 · 60 · 70 · 80 · 90 %. Dải đậm nhất bết mực hay ướt giấy thì ghi chú ô nào.

**Gửi lại:** ảnh từng tờ + một dòng: bút · giấy (láng / nhám) · tốc độ · kiểu gạch · ô nào bắt đầu bết mực. AI đọc độ xám từng ô bằng `tools/tone_read.py` (13/11/2026) và dựng bảng *độ phủ → độ đậm nhìn thấy* cho bút đó.

**Kết quả 13/11/2026:** 4 tờ (đan chéo, đan 3, xoắn ốc, sóng biên độ), Sakura 0,5, **mặt bóng** Ivory, 8000, chụp chung một ảnh. Bảng độ đậm mắt thấy và cách áp ở [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 8.12: vùng trung bình trông nhạt hơn độ phủ, đan 3 ≈ đan chéo, xoắn ốc chạm trần từ 70 %, sóng biên độ ô 90 % chỉ 0,71. → đường cong tông cho đan chéo + xoắn ốc, bỏ đan 3, thêm lớp đậm cho sóng biên độ ([09](09_QUYET_DINH_THIET_KE.md) P21–P24). Công cụ đọc ảnh tờ tông hiện là script tạm của AI (chưa đưa vào `tools/`). Chụp nhiều tờ một ảnh vẫn đo được, miễn mỗi tờ thấy đủ 3 ô mốc.

## 3. Từng kiểu tô: soi chỗ nào
| Kiểu | Soi trên giấy | Chỉnh ở đâu |
|---|---|---|
| Zigzag | chỗ quay đầu ở mép vùng còn đọng mực không (đã đổi sang nửa vòng tròn 03/11) | ô Góc gạch, Khoảng cách nét |
| Sóng | sóng kề nhau có chạm nhau không; máy có giật ở chỗ lượn không | ô Biên độ sóng (trống = 0,18 × khoảng cách, tối đa 0,5 ×) |
| Xoắn ốc | tâm xoắn có bết mực không; vệt nối ngang vùng sáng (khe trắng < 6 × bước xoắn được vẽ liền) | `SPIRAL_BRIDGE_PITCHES` trong `hatch.py` |
| Viền | viền khối có liền không, thừa vụn không, nét dày ra **một** đường không | ô Chi tiết viền (Ít / Vừa / Nhiều); hằng số `edges.py` (mục 4) |
| Thêm lớp viền | viền có lệch so với mảng tô, có làm rối không | tắt, hoặc Chi tiết viền = Ít |

## 4. Nét viền: ảnh thử và hằng số
Thử 3 loại ảnh: (a) hình vẽ / sticker có viền đen, (b) hình mảng màu phẳng không viền, (c) ảnh chụp thật.

| Hằng số (`edges.py`) | Ý nghĩa | Khi nào đổi |
|---|---|---|
| `INK_MAX_MM = 4.0` | nét mực dày tới chừng này → một đường giữa | viền hoạt hình rất dày vẫn ra hai đường → tăng |
| `LIGHT_MAX_MM = 1.2` | vạch sáng mảnh hơn → một đường giữa | |
| `GAP_MM = 1.5` | khe hở được nối | còn đứt → tăng; nối nhầm hai nét → giảm |
| `SPUR_MM` (2,4 / 1,6 / 1,0) | râu ngắn hơn chừng này bị cắt | còn râu ở góc chữ → tăng; mất chân linh kiện ngắn → giảm |
| `DETAIL` | ngưỡng Canny, ngưỡng nét mực, mẩu cạnh ngắn nhất | mức Vừa còn vụn trên ảnh chụp → tăng số cuối (mm) của `medium` |

## 5. Preset với ảnh thật
Sau mục 1–2, vẽ mỗi preset bằng một ảnh thật đúng loại (A5). Ghi: thời gian vẽ thật, thời gian ước tính, số lần nhấc bút, nhận xét.

| Preset | Ảnh thử nên dùng |
|---|---|
| Chân dung | ảnh tự chụp, mặt đủ sáng |
| Phong cảnh | trời mây + nhà, cảnh đêm có đèn, hoàng hôn |
| Cận cảnh / Đồ vật | cốc cà phê, đồ ăn |
| Ảnh 2D / Hình vẽ | sticker, hoạt hình, ảnh chụp màn hình |
| Schematic | sơ đồ mạch, bản vẽ scan nền xám, mạch in đơn giản |

Ảnh đêm vốn tối nên tốn mực và thời gian: thử tăng gamma (1,3–1,5) và bật khử nhiễu.

## 6. Bài thử tốc độ (sau khi chốt nét)
Mục đích: vẽ nhanh hơn mà nét không xấu, máy không mất bước.
- **Thông số máy** (gia tốc, `junction_deviation_mm`, tốc độ tối đa): Cài đặt → Cấu hình máy → Áp dụng (chỉ RAM). Chốt được rồi mới Lưu vào mạch.
- **Thông số G-code** (chờ, tốc độ vẽ / di chuyển / bút): tab Tạo bản vẽ. **Z bút**: Cài đặt → Cấu hình máy, mục App.
- **Tạo tờ thử bằng giao diện (từ 09/11/2026):** Cài đặt → **Tờ thử / hiệu chỉnh**. Nút **Tạo tờ nhấc bút** (chọn Z nhấc 1 / 1,5 / 2 / 3 / 5, chờ, tốc độ hạ; mỗi hàng một tổ hợp, hàng k có k chấm ở đầu) cho ra bảng hàng ↔ thông số; chạy tờ trên giấy, chọn hàng đẹp nhất, bấm **Dùng** thì Z nhấc ghi vào hồ sơ và chờ / tốc độ hạ vào ô tab Tạo bản vẽ. Có sẵn cả nút tờ hiệu chỉnh bút và bài 7.2 / 7.3 / 7.4 / 7.5; tất cả thành bản thảo trong Hàng đợi (tab Điều khiển).
- **Từ 11/11/2026:** tờ nhấc bút mặc định chờ **0,02 / 0,05 / 0,1 s** (× Z 1 / 3 / 5 × hạ 1000 / 2000 = 18 hàng). Bài 7.2 / 7.3 / 7.4 dùng chung ô **"Tốc độ thử"** (mặc định **7000, 8000, 9000, 10000**, tối đa 8 số, trần 20000; không còn chặn theo tốc độ tối đa của máy) và chờ = ô chờ ở tab Tạo bản vẽ. **Firmware vẫn tự chặn mọi lệnh ở `max_rate_mm_per_min`**: muốn thử 10000 thật thì Cài đặt → Cấu hình máy → tốc độ tối đa X, Y = 10000 → **Áp dụng** (chỉ RAM, tắt máy là mất) trước khi chạy.
- **Từ 13/11/2026:** tờ nhấc bút chỉ còn ô chờ **0 / 0,02** (mặc định tích cả hai, Z3, hạ 2000 → 2 hàng). Bộ thử máy trên giao diện chỉ còn **7.2** (tốc độ thử mặc định 8000) và **7.5** (chờ 0 / 0,02); 7.3 / 7.4 / 7.6 đã xong nên bỏ nút (tạo bằng API / `tools/make_test_gcode.py` vẫn được, mặc định vẽ 8000).
- Tệp có sẵn (hoặc sinh tay bằng `tools/make_test_gcode.py`): `7.1-cho-0.20s / 0.10s / 0.05s`, `7.1-nhac-Z2 / Z1.5`, `7.2-mat-buoc`, `7.3-gia-toc-rang-cua`, `7.4-toc-do-ve` (3000 / 4000 / 5000 / 6000), `7.5-keo-vet-cho-0.05s / 0.10s`. Mặc định Z 3 / 0, nâng 3000, hạ 2000, vẽ 5000; đổi bằng `--up`, `--down`, `--down-feed`, `--draw-feed`.

| # | Bài | Cách làm | Nhìn gì | Tình trạng |
|---|---|---|---|---|
| 7.1 | Chi phí nhấc bút | 100 gạch 2 mm; thời gian thật ÷ 100 = một chu kỳ nhấc + hạ + chờ. Đổi chờ 0,2 → 0,1 → 0,05 s; Z nhấc 3 → 2 → 1,5 | bút kéo vệt khi di chuyển (nhấc chưa kịp)? đầu nét hụt (hạ chưa chạm)? bút nảy? | ✅ chờ 0,05 s đủ nét; ⏳ đo thời gian chính xác |
| 7.2 | Mất bước | vẽ dấu + ở góc → chạy nhanh nhiều lần → vẽ lại dấu + | hai dấu trùng khít = không mất bước | ✅ 03/11 (6000 mm/min, gia tốc 2000, ~20 phút). ⏳ lặp lại ở mức mới (7.2b) |
| 7.2b | Mất bước ở mức mới | **(từ 11/11 trong giao diện)** mỗi tốc độ một cặp dấu + xếp hàng ngang từ trái sang (cột k có k chấm bên dưới); giữa hai lần vẽ dấu, bút nâng chạy G1 đúng tốc độ đó 10 vòng (~1,3 m / vòng) khắp vùng; cuối bài vẽ lại dấu đầu tiên lần nữa. Gia tốc 3000, SpreadCycle; chạm thử nhiệt động cơ + driver | cặp nào tách đôi = mất bước ở tốc độ đó; dấu đầu lệch ở lần cuối = tổng lệch cả bài | ⏳ 7000 / 8000 / 9000 / 10000 |
| 7.3 | Gia tốc + góc | **(từ 11/11)** răng cưa bước 2 mm, **mỗi tốc độ một hàng** từ trên xuống (hàng k có k chấm đầu hàng); đổi gia tốc / `junction_deviation` ở Cấu hình máy rồi chạy lại trên tờ mới | gợn sóng sau góc; giọt mực ở góc; thời gian từng lần (Biểu đồ). Đang dùng gia tốc 3000, junction 0,05 | ⏳ 7000–10000 |
| 7.4 | Tốc độ vẽ từng bút | dải đường thẳng, mặc định 7000 / 8000 / 9000 / 10000, mỗi bút một tờ, **chụp cận đo bề rộng nét** | tốc độ cao nhất mà nét chưa nhạt / đứt; bề rộng nét ở đó (→ số của bút trong ô "Bút vẽ") | 🧪 6000 vẫn đậm (ảnh xa); 8000 vẽ con mèo OK (11/11); ⏳ đo |
| 7.5 | Vệt kéo khi đi xa | hai chấm cách 240 mm, G0 qua lại 5 lần, mỗi lần một mức chờ nâng; đổi Z nhấc 3 / 4 / 5. Dán giấy phẳng | vệt mảnh nối hai chấm = bút chưa rời giấy | ⏳ |
| 7.6 | Đoạn ngắn và cung G2 | **(từ 12/11, nút "7.6 Đoạn ngắn / cung G2")** 5 vòng tròn bán kính 10 mm xếp một hàng, vẽ lần lượt từ trái sang phải: đoạn thẳng G1 dài **1 / 0,5 / 0,25 / 0,1 mm**, rồi **cung G2** (2 dòng mỗi lượt). Mỗi vòng vẽ chồng 12 lần (~6 s) ở tốc độ vẽ đang đặt (8000). Giấy mới. Chạy xong mở **Biểu đồ** của lần chạy đó | từng vòng: tốc độ thật có tụt không, hàng đợi (Bf) có cạn về 0 giữa vòng không (chấm đỏ), thời gian thật mỗi vòng; trên giấy: vòng nào có cạnh góc / rung / vệt đậm chỗ nối | ✅ 13/11/2026: đoạn 1 / 0,5 / 0,25 / 0,1 mm mất **6,0 / 11,6 / 23,3 / 60,7 s**, **G2 5,7 s** (đủ tốc 8000, hàng đợi đầy 15). Mọi vòng G1 đều chỉ ~125 dòng/giây: chậm do gửi một dòng chờ `ok` (~8 ms), **không phải** do baud (dự đoán cũ "~480 dòng/giây" sai: chỉ tính thời gian truyền chữ). Trên giấy 5 vòng như nhau. → dùng G2/G3 ([09](09_QUYET_DINH_THIET_KE.md) D12), giữ 115200 và cách gửi (D10, D11) |

**Kết quả 13/11/2026 (bài chờ 0):** hàng 1 (chờ 0) nét đủ, đầu nét không hụt; hàng đợi **đầy suốt** cả hàng. Hàng 2 (chờ 0,02) hàng đợi tụt về 0 ở mỗi lần nhấc, ~8 s so với ~6,3 s (20 gạch). Cả tờ thật 17 s. → mặc định chờ **0** ([09](09_QUYET_DINH_THIET_KE.md) C10). Lưu ý: hàng k có k chấm ở đầu hàng, các mức chờ xếp tăng dần (hàng 1 = mức nhỏ nhất).

**Đọc bộ đệm khi chờ nhấc bút = 0 (bài ngày 13/11):** chạy tờ nhấc bút có hàng chờ 0 (ô "0" trong tờ nhấc bút, tạo lại tờ) và hàng chờ 0,02; mở Biểu đồ, xem **hàng đợi lệnh trong máy**. Chờ 0,02 thì mỗi lần nhấc bút có G4 nên hàng đợi tụt về 0; chờ 0 không có G4 thì hàng đợi phải **không tụt** tại chỗ nhấc. Ghi lại: hàng đợi có còn tụt không, thời gian cả tờ, nét đầu sau khi hạ có hụt / loang không. Biểu đồ Độ cao bút Z đã ẩn (không cần để đọc bài này); rê chuột vẫn thấy Z. Cần đã gõ `$10=3` ở Terminal (mục 3 của docs/11).

**Gửi lại sau bài 7.6 và bài chờ 0:** ảnh Biểu đồ từng lần chạy (chụp màn hình), thư mục `data/job_logs` của các lần chạy đó (hoặc tải CSV), ảnh giấy chụp cận từng vòng tròn.

**Mức đang nhắm tới (đề xuất 06/11/2026, chưa thử):** tốc độ tối đa X/Y 8000 mm/min (nguồn 12 V, không nên quá 10000), gia tốc X/Y 2500 (3000 là của Z), `junction_deviation` 0,05, Vref giữ 1,4. G0 chạy tới 8000; tốc độ vẽ chốt theo 7.4 (khoảng 5000–7000). Theo công thức góc cua, 0,02 → 0,05 → 0,1 chỉ nhanh thêm ~1–2 % với ảnh tô, ~7–8 % mỗi bậc với chữ nhiều góc vuông đoạn ngắn. Thứ tự thử: 7.2b trước, rồi 7.3.

**Hạ chậm, nhấc nhanh** (bút hạ bằng trọng lực): ô "Tốc độ hạ bút" (mặc định 2000). Thử 600–1500 nếu bút còn nảy hoặc loang mực đầu nét.

## 7. Bảng ghi kết quả (điền dần)
| Ngày | Bút | Giấy | Thử gì | Thông số | Thời gian thật / ước tính | Kết luận |
|---|---|---|---|---|---|---|
| 03/11/2026 | 0,4 | | tờ mẫu hiệu chỉnh | vẽ 3000 | | nét ~0,55 mm |
| 03/11/2026 | | | 7.2 mất bước | G0 6000, gia tốc X/Y 2000 (Z 3000), Vref 1,4 V | ~20 phút | không mất bước |
| 11/11/2026 | Pigma 0,4 | thường | ảnh con mèo, preset Chân dung | max 8000, gia tốc 3000, junction 0,05, Z3, chờ 0,05, SpreadCycle | | máy chạy êm, không thấy mất bước; nền lộ ranh giới các mức (5 mức); đọng mực cuối nét (nghi bút + giấy) |
| 12/11/2026 | UB-155 đỏ, UM-100, Sakura 0,4 | Ivory 250 | tờ hiệu chỉnh A6, nhấc bút, 7.2 / 7.3 / 7.4, thang xám A6, ảnh thật | vẽ 8000, Z3 / Z0, chờ 0,02, hạ 2000, gia tốc 3000 | 1,7–1,9 | nét: Sakura 0,45–0,5 láng / 0,5–0,55 nhám, UB-155 0,35–0,4, UM-100 ~0,4; 8000 ổn, 10000 được ở đoạn dài; Z3 đẹp; chờ 0,02 ổn. Preset: đan chéo đẹp nhất cho chân dung, sóng biên độ chuyển tông mượt nhất, xoắn ốc nhấc bút nhiều, zigzag / sóng thường ít dùng; vẽ lần lượt từng mức và nét viền nên tắt |
| | | | 7.2b mất bước mức mới | G0 8000, gia tốc X/Y 2500, Vref 1,4 V | 10–20 phút | |
| | | | 7.3 góc cua | junction 0,02 / 0,05 / 0,1 ở 8000, gia tốc 2500 | | |
| | 0,4 | | tờ mẫu hiệu chỉnh | vẽ 5000 | | |
| | 0,5 | | tờ mẫu hiệu chỉnh | | | |
| | 0,4 | | Thang xám · Chân dung | | | |
| | 0,4 | | Thang xám · Phong cảnh | | | |
| | 0,4 | | Thang xám · Cận cảnh | | | |
| | | | 7.4 bề rộng nét theo tốc độ | 3000 / 4000 / 5000 / 6000 | | |
| | | | 7.5 vệt kéo | Z 3 / 4 / 5, chờ 0,05 / 0,1 | | |

Khi đã chốt: sửa số mặc định trong mã (đường dẫn ở trên), ghi kết quả vào [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) mục 6, đánh dấu xong ở [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md).

## 8. Mẫu gửi kết quả
Chép đúng khối của bài vừa làm, điền sau dấu `:`, bỏ trống chỗ không đo được. Gửi kèm **ảnh cả tờ** (chụp thẳng, đủ sáng) và **ảnh cận** nếu bài yêu cầu.
Mẹo: đặt thước kẻ hoặc tờ có thước 100 mm cạnh chỗ chụp cận để đọc được bề rộng nét.

**Phần chung (mọi bài)**
```
Ngày:
Bút (0,4 Sakura / 0,5 bi / khác):
Giấy (loại, định lượng nếu biết):
Bài:
Có đổi gì so với mặc định không (Z, chờ, tốc độ, gia tốc):
```

**Mục 1 / 7.4: bề rộng nét**
```
Tốc độ vẽ:
Dải sát nhất còn đặc mà chưa ướt (mm):
Dải trông xám vừa khi đứng xa 40-50 cm (mm):
Bề rộng một nét đo bằng ảnh cận (mm) ở 3000 / 4000 / 5000 / 6000:
Tốc độ nào nét bắt đầu nhạt / đứt:
```

**Mục 2: thang xám (mỗi preset một khối)**
```
Preset (Chân dung / Phong cảnh / Cận cảnh):
Đếm được mấy mật độ khác nhau trên giấy (tối đa 5 kể cả giấy trắng):
Cặp bậc trông giống nhau (vd 20% và 30%):
Bậc đậm nhất: đặc đẹp / bết mực / giấy quăn:
Cả tờ: quá đậm / vừa / quá nhạt:
Vùng nhạt có lộ từng sợi không:
So với dải chuyển liền: đoạn nào lệch (sáng hơn / tối hơn):
Thời gian vẽ thật / ước tính:
```

**Mục 3–5: kiểu tô, viền, preset với ảnh thật**
```
Preset / kiểu tô:
Ảnh dùng (tả ngắn hoặc gửi kèm):
Chỗ quay đầu ở mép khối còn giọt mực không (ảnh cận):
Viền: liền / đứt / thừa vụn / nét đôi:
Thời gian vẽ thật / ước tính:
Số lần nhấc bút (nếu giao diện có hiện):
Nhận xét bằng mắt:
```

**7.1: chi phí nhấc bút**
```
Chờ (s) / Z nhấc:
Thời gian chạy cả tệp 100 gạch (giây, bấm đồng hồ):
Có kéo vệt / hụt đầu nét / bút nảy không:
```

**7.3: gia tốc và góc**
```
Gia tốc X / Y:
junction 0,02 / 0,05 / 0,1 (Cài đặt -> Cấu hình máy -> "Độ lệch góc"):
Tốc độ vẽ:
Thời gian chạy:
Giọt mực ở góc: không / ít / nhiều:
Gợn sóng sau góc chữ: không / ít / rõ:
Máy có kêu lạ, rung mạnh không:
```

**7.2b: mất bước ở mức mới**
```
Tốc độ G0 / gia tốc X / Y:
Thời gian chạy (phút):
Hai dấu + trùng khít không (lệch bao nhiêu mm, hướng nào):
Nhiệt động cơ X / Y, driver (ấm / nóng tay / không chạm được):
Máy có kêu lạ, rung mạnh không:
```

**7.5: vệt kéo khi đi xa**
```
Z nhấc / chờ:
Có vệt mảnh nối hai chấm không (lần nào):
Giấy có phẳng không:
```

**Khác (Home, G2 / G3, đèn X / Y, tiếp tục sau khi dừng)**
```
Việc:
Làm thế nào:
Kết quả / thời gian:
Có gì bất thường:
```
