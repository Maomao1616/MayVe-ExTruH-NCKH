# KIEM_TRA_VE — cách thử và tinh chỉnh các chế độ vẽ

Dành cho người vận hành máy vẽ (không cần lập trình). Mục tiêu: chốt các con số mặc định (khoảng cách nét, số mức, gamma, preset) **bằng bản in thật**, vì màn hình không cho biết mực loang, giấy thấm, bút khô ra sao.
Ký hiệu: ✅ đã chốt bằng bản in · 🧪 mới thử bằng ảnh mẫu trên máy tính.

## 0. Nguyên tắc
- **Mọi bước đều phải vẽ thật lên giấy.** Khung xem trước trên web chỉ dùng để kiểm tra hình học trước khi vẽ (nét đủ, đúng chỗ, đúng số dải / số bậc, không vượt khổ), đỡ phí giấy. Web **không** cho biết độ đậm thật: trên màn hình nét nào cũng mảnh như nhau, còn trên giấy mực loang, giấy thấm, bút đậm nhạt khác nhau. Các quyết định "dải nào xám vừa", "bậc nào tách rõ" chỉ làm được khi nhìn tờ giấy.
- **Mỗi lần chỉ đổi một thông số.** Cùng loại giấy, cùng cây bút, cùng tốc độ vẽ.
- **Ghi số ngay góc tờ giấy** (bút, khoảng cách, số mức, gamma, preset, ngày) rồi chụp ảnh tờ giấy để so về sau.
- Làm theo thứ tự dưới đây: bước trước chốt con số mà bước sau dùng. Mỗi bút **0,2 / 0,4 / 0,5** làm riêng (cả ba đều có trong ô "Bút vẽ"; với tờ mẫu hiệu chỉnh gửi `pen_width_mm: 0.5` cho bút 0,5).
- Ghi kết quả vào bảng ở mục 6.

## 1. Khoảng cách nét theo bút: tờ mẫu hiệu chỉnh bút
Đã in và lưu lại (ảnh chụp tờ mẫu). Nút tạo tờ mẫu đã bỏ khỏi giao diện; cần in lại thì gọi `POST /api/draw/calibration` (vẫn còn ở backend, `drawing/calibration.py`) qua `http://127.0.0.1:8000/docs`.
Tờ có chữ F (kiểm hướng X/Y), thước 100 mm (kiểm tỷ lệ) và **8 dải gạch** với khoảng cách = bề rộng bút × 0,8 / 1 / 1,25 / 1,5 / 2 / 2,5 / 3 / 4.

**Khoảng cách nét quyết định gì:** phần mềm kẻ các đường cách nhau **2 × bề rộng nét thật**, để **một lớp gạch phủ ~50 %**, nhìn xa thành xám vừa. Vùng tối hơn **không** gạch dày hơn mà được **chồng thêm lớp** xoay góc khác (5 mức: 0 / 1 / 2 / 3 / 4 lớp ≈ 0 / 50 / 75 / 88 / 94 % mực; n lớp phủ 1 − (1 − p)ⁿ). **Bề rộng nét thật khác cỡ ngòi:** đo tờ hiệu chỉnh 03/11/2026, Sakura 0,4 ra ~0,55 mm (mực loang), nên cách cũ 2 × 0,4 = 0,8 mm thực tế phủ ~69 % (hai lớp ~90 %, ba lớp ~97 %): bậc 2 và 3 trông giống nhau, vùng tối lấm tấm trắng. Từ 03/11/2026 công thức là 2 × 1,375 × cỡ bút (bút 0,4 → 1,1 mm) và mặc định 5 mức. **Bề rộng nét còn phụ thuộc tốc độ vẽ và giấy**, nên chốt tốc độ (mục 7) rồi mới in lại tờ hiệu chỉnh. Cách chọn hệ số bằng tờ thật: đứng cách 40–50 cm, dải nào trông như **mảng xám mịn** mà chưa thấy từng sợi thì lấy hệ số đó. Thấy sọc → giảm hệ số; bết mực → tăng.

| Xem gì | Kết luận |
|---|---|
| Thước đo được đúng 100 mm? | sai thì kiểm `steps_per_mm` trong cấu hình máy trước khi làm tiếp |
| Dải **sát nhất** mà nét chưa nhòe thành mảng / giấy chưa ướt, quăn | mức đậm nhất dùng được |
| Dải trông như **xám vừa** | khoảng cách mặc định (hiện `DEFAULT_SPACING_PEN = 2.0` × `LINE_WIDTH_RATIO = 1.375` × cỡ bút, `backend/app/services/drawing/styles.py`; đo lại nét thật rồi sửa `LINE_WIDTH_RATIO` = nét thật ÷ cỡ ngòi) |
| Dải thưa nhất còn đọc thành "mảng" chứ không thành từng sợi | mức sáng nhất có ý nghĩa |

## 2. Thang đậm nhạt: ảnh thử preset (thang xám)
**Chỉ làm MỘT LẦN cho mỗi cây bút + loại giấy**, để chốt số cho preset. Vẽ hằng ngày **không** phải làm bước này: chỉ nạp ảnh → chọn preset → (nếu cần) chỉnh 1–2 ô.

| Ô trên giao diện | Dùng thế nào khi vẽ hằng ngày |
|---|---|
| Số mức đậm nhạt | preset đã chọn sẵn; muốn nhanh / tương phản mạnh thì giảm, muốn mịn thì tăng |
| Tự cân sáng | để bật, tự kéo ảnh tối / nhạt về vừa |
| Gamma, mức đen, mức trắng | preset đã điền; chỉ chỉnh khi một ảnh cụ thể ra quá đậm hoặc quá nhạt |

**Cách làm (lấy preset làm gốc, tăng giảm quanh nó):**
1. Tab Tạo bản vẽ → Bản thảo đã lưu → bấm **"Ảnh thử preset (thang xám)"**: phần mềm tự nạp ảnh 11 bậc (0, 10 … 100 % đen) + một dải chuyển liền bên dưới.
2. Chọn preset **Chân dung** → chờ tạo nét → **Lưu bản thảo** (tên tự thành "Thang xám · Chân dung") → vẽ.
3. Làm tương tự với **Phong cảnh** và **Cận cảnh / Đồ vật**. Ba tờ là đủ.
4. Nhìn từng tờ, sửa đúng preset đó theo bảng dưới, vẽ lại tờ đó nếu cần.

Ảnh 2D / Hình vẽ và Schematic chỉ vẽ viền: thang xám không nói lên gì (chỉ ra khung), thử bằng một hình vẽ thật (mục 4).

| Thấy gì trên tờ | Sửa trong preset (`frontend/js/views/drawing/presets.js`) |
|---|---|
| Hai bậc kề nhau trông như nhau (bút loang) | giảm `style-levels` 1 bậc |
| Bậc đậm nhất bết mực, giấy ướt | tăng khoảng cách nét (mục 1) hoặc giảm `style-levels` |
| Cả tờ quá đậm, các bậc giữa đã gần đen | tăng `image-gamma` thêm 0,1–0,2 |
| Cả tờ quá nhạt, các bậc nhạt còn trắng trơn | giảm `image-gamma` 0,1–0,2 (không dưới 0,8) |
| Vùng nhạt lộ từng sợi, lổn nhổn | giảm khoảng cách nét (`style-spacing`, mm) |

Vì sao cần: ba kiểu tô chia ảnh thành 3–5 mức (`levels`); mỗi mức thêm **một lượt** nét (zigzag: gạch chéo góc khác; sóng: thêm lượt sóng; xoắn ốc: thêm vòng). "5 mức" trên phần mềm chưa chắc ra 5 bậc phân biệt được trên giấy; in một tờ là biết.

## 3. Từng kiểu tô: soi chỗ nào

| Kiểu | Soi trên giấy | Chỉnh ở đâu |
|---|---|---|
| **Zigzag** | chỗ quay đầu ở mép vùng có đọng mực đậm hơn không; các lớp gạch chéo có tạo vân lạ (moiré) không | ô Góc gạch; khoảng cách nét |
| **Sóng** | sóng kề nhau có chạm nhau không; máy có giật / chậm ở chỗ lượn gấp không | ô Biên độ sóng (mặc định 0,35 × khoảng cách, tối đa 0,5 ×) |
| **Xoắn ốc** | tâm xoắn có bết mực không; có vệt nét chạy ngang vùng sáng không (khe trắng < 3 mm được vẽ nối liền để đỡ nhấc bút) | `BRIDGE_MM = 3.0` trong `backend/app/services/drawing/hatch.py` |
| **Nét viền** | viền mỗi khối có liền không, có thừa vụn (lông, vân gỗ) không, nét dày có ra **một** đường không | ô **Chi tiết viền** (Ít / Vừa / Nhiều); hằng số `edges.py` (mục 4) |
| **Thêm lớp viền** (trên kiểu tô) | viền có lệch so với mảng tô không; có làm bức vẽ rối không | tắt đi, hoặc để Chi tiết viền = Ít |

## 4. Nét viền: ảnh thử và hằng số
Thử 3 loại ảnh: (a) hình vẽ / sticker có viền đen (kể cả dán lên ảnh chụp), (b) hình mảng màu phẳng không viền, (c) ảnh chụp thật (chân dung, đồ vật).

| Hằng số (`backend/app/services/drawing/edges.py`) | Ý nghĩa | Khi nào đổi |
|---|---|---|
| `INK_MAX_MM = 4.0` | nét mực dày tới chừng này → một đường giữa; dày hơn → viền hai phía | viền hoạt hình rất dày vẫn ra hai đường → tăng |
| `LIGHT_MAX_MM = 1.2` | vạch sáng mảnh hơn → một đường giữa | |
| `GAP_MM = 1.5` | khe hở được nối | còn đứt → tăng; nối nhầm hai nét khác nhau → giảm |
| `DETAIL` (bảng 3 mức) | ngưỡng Canny, ngưỡng nét mực, mẩu cạnh ngắn nhất | mức Vừa còn vụn trên ảnh chụp → tăng số cuối (mm) của `medium` |

## 5. Preset: thử với ảnh thật
Sau khi chốt mục 1–2, vẽ mỗi preset bằng một ảnh thật đúng loại (khổ A5), ghi: **thời gian vẽ thật**, thời gian phần mềm ước tính (chưa tính gia tốc nên thường ngắn hơn thật), số lần nhấc bút, nhận xét.

| Preset | Kiểu | Ảnh thử nên dùng |
|---|---|---|
| Chân dung | zigzag 5 mức, khử nhiễu, gamma 1,15, viền Ít | ảnh tự chụp, mặt người đủ sáng |
| Phong cảnh | sóng 4 mức, góc 30°, CLAHE, viền Ít | trời mây + nhà, cảnh đêm có đèn, hoàng hôn |
| Cận cảnh / Đồ vật | xoắn ốc 4 mức, gamma 1,25, viền Ít | cốc cà phê, đồ ăn, đồ vật |
| Ảnh 2D / Hình vẽ | nét viền, chi tiết Vừa | sticker, hoạt hình, truyện tranh, ảnh chụp màn hình |
| Schematic / Bản vẽ kỹ thuật | nét viền, mức đen/trắng 60–200 | sơ đồ mạch, bản vẽ scan nền xám |

Sửa số trong `frontend/js/views/drawing/presets.js` (mỗi preset vài dòng, chung một `BASE`). Ảnh đêm / sân khấu vốn tối nên tốn mực và thời gian: thử tăng gamma (1,3–1,5) và bật khử nhiễu.

## 6. Bảng ghi kết quả (điền dần)
| Ngày | Bút | Giấy | Thử gì | Thông số | Thời gian thật / ước tính | Kết luận |
|---|---|---|---|---|---|---|
| | 0,2 | | tờ mẫu hiệu chỉnh | | | |
| | 0,4 | | tờ mẫu hiệu chỉnh | | | |
| | 0,5 | | tờ mẫu hiệu chỉnh | | | |
| | 0,4 | | Thang xám · Chân dung | | | |
| | 0,4 | | Thang xám · Phong cảnh | | | |
| | 0,4 | | Thang xám · Cận cảnh | | | |

Khi đã chốt, cập nhật số mặc định trong mã (đường dẫn ở trên) và đổi 🧪 thành ✅ trong `DRAW_ROADMAP.md` / `STATUS.md`.

## 7. Thử tốc độ (sau khi chốt nét ở mục 1–2)
Mục đích: vẽ nhanh hơn mà nét không xấu đi, máy không mất bước. Số hiện tại và lý do từng thông số: `FUTURE_UPGRADE_BETA.md` mục 21.1.
- **Thông số máy** (gia tốc, `junction_deviation_mm`, tốc độ tối đa): Cài đặt → Cấu hình máy → **Áp dụng**. Chỉ đổi trong RAM, tắt máy là mất. Chốt được rồi mới **Lưu vào mạch** (phần mềm tự sao lưu bản cũ).
- **Thông số G-code** (thời gian chờ, tốc độ vẽ / di chuyển / bút): ô ở tab Tạo bản vẽ. **Z bút lên / xuống**: Cài đặt → Cấu hình máy (mục App).
- Mỗi lần đổi **một** thông số, cùng bản vẽ, ghi thời gian thật.
- **Tệp G-code thử có sẵn:** `python tools/make_test_gcode.py` ghi 10 tệp vào `export\test-gcode\` (không lên Git): `7.1-cho-0.20s / 0.10s / 0.05s`, `7.1-nhac-Z2 / Z1.5-cho-0.10s`, `7.2-mat-buoc`, `7.3-gia-toc-rang-cua`, `7.4-toc-do-ve` (3000 / 4000 / 5000 / 6000), `7.5-keo-vet-cho-0.05s / 0.10s`. Nạp ở tab Điều khiển → Xem trước → Chạy. **Mỗi bài một tờ giấy mới** (7.3 và 7.4 vẽ cùng chỗ, chồng lên là không đọc được). Mặc định Z 3 / 0, nâng 3000, hạ 2000, vẽ 5000; hồ sơ khác thì `--up`, `--down`, `--down-feed`, `--draw-feed`. 7.1: thời gian thật ÷ 100 gạch ≈ một chu kỳ nhấc + hạ + chờ.
- **Hạ chậm, nhấc nhanh** (bút hạ bằng trọng lực): ô "Tốc độ hạ bút" ở tab Tạo bản vẽ (trống = như nâng bút). Mặc định 2000 (từ 03/11/2026); thử 600–1500 nếu bút còn nảy hoặc loang mực đầu nét, trong khi giữ tốc độ nâng bút ở hồ sơ máy (Cài đặt → Cấu hình máy).

| # | Bài thử | Cách làm | Nhìn gì |
|---|---|---|---|
| 7.1 | **Chi phí nhấc bút** | Một bản vẽ nhiều nét rất ngắn (100–200 gạch 2 mm; nhờ AI tạo sẵn tệp G-code). Thời gian thật ÷ số nét = một chu kỳ nhấc / hạ. Lần lượt đổi: thời gian chờ 0,2 → 0,1 → 0,05 s; Z nhấc 5 → 3 → 2; điện áp servo 5 → 6 V | Bút có kéo vệt khi di chuyển (nhấc chưa kịp)? Đầu nét có hụt (hạ chưa kịp chạm)? Bút có nảy? |
| 7.2 | **Mất bước** | Vẽ một dấu + nhỏ ở góc giấy → chạy bản vẽ hoặc di chuyển nhanh nhiều lần → quay về vẽ lại dấu + | Hai dấu trùng khít = không mất bước. Lệch = giảm gia tốc / tốc độ hoặc tăng dòng động cơ |
| 7.3 | **Gia tốc + góc** | Cùng một đoạn chữ ở gia tốc 600 / 1000 / 1500 / 2000 mm/s², rồi `junction_deviation_mm` 0,01 / 0,03 | Thời gian; gợn sóng ngay sau góc chữ (dấu hiệu rung); làm lại 7.2 |
| 7.4 | **Tốc độ vẽ của từng bút** | Dải đường thẳng ở 3000 / 4000 / 5000 / 6000 mm/min, mỗi bút một tờ. Chụp cận (macro) và **đo bề rộng nét ở từng tốc độ** | Tốc độ cao nhất mà nét chưa nhạt / đứt; bề rộng nét thật ở tốc độ đó (số cho `LINE_WIDTH_RATIO`) |
| 7.5 | **Vệt kéo khi di chuyển xa** | Chấm hai chấm cách 240 mm, chạy G0 qua lại 5 lần, mỗi lần một mức chờ nâng (0,05 / 0,1 s); đổi Z nhấc bằng `--up` (3 / 4 / 5). Dán giấy phẳng bằng băng keo | Có vệt mảnh nối hai chấm = bút chưa rời giấy. Hết vệt ở Z / chờ nào thì dùng mức đó |

| Ngày | Bài | Bút | Thông số đổi | Thời gian thật | Số nét | Kết luận |
|---|---|---|---|---|---|---|
| | 7.1 | | thời gian chờ 0,2 → 0,1 | | | |
| | 7.2 | | gia tốc 1500 | | | |
