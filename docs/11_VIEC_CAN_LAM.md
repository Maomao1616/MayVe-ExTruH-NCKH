# 11 — Tình trạng và việc cần làm

> Sổ làm việc, cập nhật 05/11/2026. Một nơi duy nhất cho "cái gì xong / chưa kiểm chứng / còn phải làm".
> Cỡ việc: **S** vài giờ · **M** nửa đến một ngày · **L** nhiều ngày.

## 1. Tình trạng chung
| Khối | Tính năng | Đã kiểm ngoài máy giả |
|---|---|---|
| Điều khiển, an toàn, hủy | ~95 % | ~65 % |
| Tạo bản vẽ (ảnh, SVG, bản thảo, hàng đợi) | ~92 % | ~50 % |
| Cài đặt, cấu hình máy | ~90 % | ~70 % |
| Phân quyền, bản mang đi | ~85 % | ~60 % |

Test tự động: máy chủ ~397 bài (`python -m pytest` trong `backend`), giao diện 33 bài. Thiếu chủ yếu là **in thật trên giấy** và **thử trên MiniPC**.

Mục tiêu trước mắt cho phần web điều khiển: chốt thông số chuẩn bằng bản in → đo thời gian thật → (nếu có) tab Beta → MiniPC + Docker + Cloudflare. Camera, nút cứng, ESP32 thêm lúc nào cũng được.

## 2. Đã xong gần đây
- [x] 14/11 (4): **Theo dáng ảnh áp được đậm nhạt**: sửa cửa sổ kiểm tra chỗ có đường (vuông → tròn; trước đó đường chéo không dày hơn ~1,4 mm), `FLOW_TEST_RATIO` 0,5 → 0,85, thêm đường cong tông. Còn: nhiều mẩu nét ngắn ở vùng tối (526 → 894 nét); chưa đo tờ tông riêng cho theo dáng.
- [x] 14/11 (3): **4 preset** (09 P29): Chân dung = sóng biến thiên, không viền, mức đen 20, tương phản 1,3, góc 135°; Ảnh 2D = gạch chéo + viền; Phong cảnh, Schematic giữ; bỏ Cận cảnh, Phác họa. Ô **Tương phản** mới ở tiền xử lý (cả xem trước trong trình duyệt). Sóng biến thiên: ô **"Phủ đều đường ở vùng sáng"** (bật ở Chân dung): da mặt kín đường, hết vệt trắng do bớt đường.
- [x] 14/11 (2): **tách đan chéo / theo dáng** (09 P28): giao diện có "Gạch chéo" và "Theo dáng ảnh" riêng, bỏ kiểu lai; preset Chân dung = Gạch chéo + lớp viền FDoG; Sóng biến thiên để trắng vùng sáng dưới 0,10 (hết đường thẳng giữa mặt). Thử bỏ chữ U ở mép (hàng rào mỏng, góc bo, lấn mức) rồi quay lại vì nét kém đẹp (09 P28).
- [x] 14/11: **nét gọn hơn** (09 P27): đan chéo bỏ "râu" (dải đậm hẹp < 1,5 × khoảng cách nét, mẩu gạch < 1,5 mm, nối chéo); dưới độ phủ 0,2 để **giấy trắng hẳn**; **"Đan chéo + theo dáng" = đan chéo + MỘT đường viền cong bao khối làm hàng rào** (dòng gạch dừng ở viền, tóc không lan vào mặt; bỏ 2–3 đường theo dáng song song); khối đậm (tròng mắt) lấy vành; nét viền **làm mượt 0,8 mm**, bỏ nét < 4 mm; XDoG đổi sang **FDoG** (làm mượt dọc hướng nét 4 mm). Ảnh chân dung A4 bút 0,4: đan chéo + theo dáng 1196 → 868 nét, 20,6 → 16,2 phút, mực 92,7 → 76,9 m.
- [x] 13/11 (4): **XDoG** (09 P26): ô tích "Dùng XDoG" ở kiểu Nét viền; lớp viền phủ lên kiểu tô luôn XDoG; preset **"Phác họa ảnh"**; hằng số chỉnh trên ảnh mèo + em bé (σ 0,7 mm).
- [x] 13/11 (3): gọn giao diện (09 P25): ẩn zigzag + sóng thường (ô Kiểu tô còn 5 kiểu, mặc định đan chéo + theo dáng); `styles.py` chia mục A nền / B kiểu đang hiện / C kiểu ẩn; Tờ thử: nhấc bút chờ 0 / 0,02, gộp Thang xám + Tờ tông thành **Thang tông** (ảnh 16 ô nạp vào tab vẽ), chỉ còn 7.2 + 7.5; preset Cận cảnh gamma 1.
- [x] 13/11 (2): theo tờ tông + chân dung in 13/11: **đường cong tông** cho đan chéo và xoắn ốc (75 %, 09 P21); kiểu **"Đan chéo + theo dáng"** làm mặc định Chân dung, gamma 1 (09 P22); **bỏ "Đan 3 hướng" và "Theo dáng ảnh" thuần** khỏi danh sách kiểu tô, mã giữ lại (P23); **sóng biên độ thêm lớp gạch ở vùng rất đậm** (P24, có công tắc); Biểu đồ **đếm nhấc bút theo Z** (P19); `tools/ink_sim.py` thêm cột "sai mắt".
- [x] 13/11 (1): theo tờ nhấc bút + tờ 7.6 in sáng 13/11: **chờ mặc định 0** (09 C10); **nét cong ghi bằng G2/G3** (`drawing/arcs.py`, sai lệch ≤ 0,02 mm; 09 D12; ảnh mẫu A5 bớt 6–25 % dòng); **ước tính thời gian** tính giới hạn ~125 dòng/giây + 0,025 s mỗi lần nhấc + 0,025 s mỗi G4 (tờ 7.6: ước 110,9 s / thật 111 s, bản cũ 32 s; tờ nhấc bút 18,0 / 17 s, bản cũ 22,5). **Không làm** gửi dồn lệnh / tăng baud: mô phỏng cho thấy bản vẽ thật không bị chậm vì giới hạn dòng (09 D10, D11).
- [x] 12/11 (9): kiểu tô **"Theo dáng ảnh (thử nghiệm)"** (flow field bản thô, `flow.py`): nét uốn dọc theo dáng ảnh, độ đậm liền. Ảnh mẫu A5: nhấc bút và thời gian ước tính ít hơn đan chéo 40–56 %, sai tông mô phỏng còn kém đan chéo (0,056 / 0,042). Chưa in. Hướng dẫn thử: [07](07_THU_NGHIEM.md) "Kế hoạch ngày 13/11".
- [x] 12/11 (8): thêm **tờ thử 7.6 "Đoạn ngắn / cung G2"** (Cài đặt → Tờ thử; `testgcode.arc_test`): 5 vòng tròn R10, đoạn G1 1 / 0,5 / 0,25 / 0,1 mm rồi cung G2, để xem bộ đệm cạn ở đoạn ngắn và máy có chạy G2 mượt không (trước đây chỉ có ô trống "G2 / G3" ở mục 8 bảng ghi, chưa có tờ thử). Cách đọc + bài bộ đệm khi chờ 0: [07](07_THU_NGHIEM.md) mục 6. Sửa kèm: `tools/make_test_gcode.py` in tiếng Việt lỗi trên console Windows.
- [x] 12/11 (7): tờ hiệu chỉnh tông thêm kiểu **Sóng biên độ** và **Xoắn ốc** (Cài đặt → Tờ thử; sóng chạy đúng hàm tô thật, xoắn ốc cắt bỏ phần ra ngoài ô). Chủ dự án vẽ 3 tờ Sakura 0,5: đan 3 hướng, sóng biên độ, xoắn ốc; zigzag / gạch chéo mượn đường cong đan 3. Cần: chụp ảnh gốc gửi lại ([07](07_THU_NGHIEM.md) mục 2b).
- [x] 12/11 (6): **ẩn biểu đồ "Độ cao bút Z"** trong khung Biểu đồ của tab Điều khiển (đọc không ra gì; số lần nhấc / % thời gian vẽ đã có ở bảng tóm tắt; Z đo là Z lệnh nên không bắt được servo tụt). Công tắc `SHOW_PEN_CHART` ở đầu `views/jobchart.js` (đặt `true` là có lại). Còn tốc độ thật + hàng đợi.
- [x] 12/11 (5): sửa **Cài đặt → Tờ thử: khối "Tờ hiệu chỉnh tông" hiện chữ của khối "Thang xám"** (hai khối dùng trùng khóa dịch `sheet.tone.title` / `.help`, khóa sau đè khóa trước). Khối tông đổi sang khóa `sheet.tonecal.*`. Thêm `frontend/tests/locales.test.mjs` (không trùng khóa, vi / en cùng khóa, mọi `data-i18n` trong index.html có bản dịch).
- [x] 12/11 (4): **ẩn nút "Xem trước" + ô tích "Tôi đã xem trước đường chạy và vùng vẽ"** ở tab Điều khiển (chủ dự án thấy không cần): nạp tệp là khung vẽ hiện ngay, nút ▶ Chạy chỉ còn cần máy nối + đã mở khóa chuyển động + Idle + tệp không lỗi. Công tắc `REQUIRE_PREVIEW_CONFIRM` ở đầu `views/control.js` (đặt `true` là có lại). Ghi ở [09](09_QUYET_DINH_THIET_KE.md) C9. Ô "Tôi đã kiểm tra kích thước, vị trí và vùng làm việc" ở tab Tạo bản vẽ (trước khi ra G-code cuối) giữ nguyên.
- [x] 12/11 (3): sửa **tab Điều khiển đơ khi chạy tác vụ** (laptop yếu, tệp lớn): mỗi lần máy báo vị trí (10 lần/giây) khung xem trước vẽ lại cả tệp (3 lượt × hàng chục nghìn đoạn, có nét đứt). Nay lớp nền, phần đã vẽ xong và phần phát lại nằm trong khung ẩn, mỗi lần chỉ vẽ thêm đoạn mới (`views/preview.js`). Chưa đo trong trình duyệt thật.
- [x] 12/11 (2): kiểu tô **Đan 3 hướng (60°)**; **tờ hiệu chỉnh tông** (16 ô độ phủ × 3 kiểu gạch, Cài đặt → Tờ thử); lộ trình thuật toán ảnh chi tiết ở [10_HUONG_PHAT_TRIEN.md](10_HUONG_PHAT_TRIEN.md) mục 0 (đường cong tông, XDoG, flow field, G2/G3; bỏ dithering 2D và tối ưu theo chi phí).
- [x] 12/11: theo kết quả in thật: **nối nét gần** thay vì nhấc bút (ô "Nối nét gần", mặc định bật; ảnh mẫu A5 bớt 55–82 % lần nhấc, nhanh 30–50 %); **ước tính thời gian có gia tốc** + 0,15 s mỗi lần nhấc (khớp tỷ lệ 1,7–1,9); mặc định vẽ / di chuyển **8000**, chờ **0,02**; "Vẽ lần lượt từng mức" mặc định **tắt**; preset bỏ nét viền, Chân dung → **đan chéo**, Phong cảnh → **sóng biên độ**; bút UB-155 **0,38**, UM-100 **0,40**, Sakura **0,50**; Home xong tự nhích Z để servo giữ bút lên; nút 7.5 hết lỗi "cần 1–8 giá trị"; tờ nhấc bút có ô chờ 0.
- [x] 11/11 (2): **chuyển mức mềm** (mặc định bật, ô "Chuyển mức mềm"), kiểu **Gạch chéo chồng lớp** và **Sóng biến thiên (tông liền)** ([06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md) mục 8.7–8.9). Mới thử bằng mô phỏng mực, **chưa in**.
- [x] 11/11: đổi sang giấy Ivory + Sakura / Uniball 150: nét giả định **0,44 mm** (`LINE_WIDTH_RATIO` 1,1, trước 1,375 = 0,55); tờ hiệu chỉnh có dải 0,40 / 0,45 / 0,50. Tờ nhấc bút chờ 0,02 / 0,05 / 0,1. Bài 7.2 / 7.3 / 7.4 dùng chung ô tốc độ thử (mặc định 7000–10000, trần 20000), chờ = ô chờ tab Tạo bản vẽ; 7.2 mỗi tốc độ một cặp dấu +, 7.3 mỗi tốc độ một hàng. Tốc độ tối đa của máy đọc từ mạch (max_rate X/Y) thay cho số cứng 6000 (hết cảnh báo "cao hơn tốc độ tối đa" sai); ô tốc độ không còn bị chặn ở 6000. Nút "Lưu vào mạch" bấm được cả khi chỉ đổi bằng terminal.
- [x] 11/11 (tối): ô **"Bút vẽ"** chọn theo tên bút (Uniball UB-155 đỏ / đen, UM-100, Sakura Pigma Micron 0,4, bút bi 0,5) + **Tùy chọn** để gõ nét đo được; số trong ô là **bề rộng nét trên giấy** (`LINE_WIDTH_RATIO` 1,1 → 1,0). Số mỗi bút đang là ước tính: 0,30 / 0,30 / 0,45 / 0,50 ⏳ đo ngày 12/11. Bản thảo / tùy chọn đã lưu với giá trị cũ (0,2 / 0,4 / 0,5) tự quay về Sakura.
- [x] 09/11: khổ giấy "Cả vùng máy"; tách Z (điều khiển Z5, G-code Z3); đổi PIN quản lý trên giao diện; biểu đồ số liệu chạy máy (nút [Đường vẽ / Biểu đồ] trong Khung nhìn 2D, ghi `data/job_logs/`); máy giả hiểu `$10`. **Chưa thử trên máy thật** (xem mục 3).
- [x] 05/11: hướng trục X / Y trên giấy **đúng** (chủ dự án xác nhận).
- [x] 03–04/11: thuật toán tô mới (mỗi mức một dải, khoảng cách theo nét thật, quay đầu nửa vòng tròn, xoắn ốc nối khe), viền cắt râu + khép vòng + làm phẳng màu, bộ mô phỏng mực `tools/ink_sim.py`.
- [x] 03/11: Z nhấc 3, vẽ 5000, chờ 0,05 s, hạ bút 2000; Home tự nâng bút; khoảng cách nét theo nét thật 0,55 mm; bài thử 7.5.
- [x] 02/11: đăng nhập PIN (khách chỉ xem), đèn công tắc X / Y, trạng thái 10 lần / giây, vệt bút bám G-code, ô tốc độ hạ bút, bút 0,5, công cụ sinh G-code thử tốc độ.

## 3. Thử trên máy thật (không cần code)
Cách làm từng bài ở [07_THU_NGHIEM.md](07_THU_NGHIEM.md); làm xong chép mẫu ở 07 mục 8, điền số, gửi kèm ảnh.
- [ ] **(14/11) Nét gọn (09 P27):** khởi động lại phần mềm, xem bản thảo Chân dung ("Đan chéo + theo dáng") và Nét viền tích XDoG. Nhìn: gạch còn lan qua viền không, mắt / mũi có khung không, má / nền sáng có quá trống không, viền có liền và mềm không. Trống quá → báo AI hạ `HATCH_WHITE`; mất chi tiết → hạ `HATCH_THIN_SPACINGS` / `FDOG_ALONG_MM`; viền thiếu → Chi tiết viền "Nhiều".
- [ ] **(13/11) Chân dung kiểu mới** (khởi động lại phần mềm, chọn lại preset Chân dung để lấy "Đan chéo + theo dáng" và gamma 1): ảnh em bé A6 + A4, so với tờ đan chéo hôm 13/11. Nhìn: mắt / mũi / mép mặt có tách khỏi nền không, đường theo dáng có lạc lõng như viền dán lên không, đậm nhạt có quá đậm không (đường cong tông làm vùng trung bình đậm hơn). Quá đậm → tăng gamma 1,1–1,2 hoặc báo AI hạ `TONE_CURVE_STRENGTH`; đường theo dáng quá nhiều / ít → báo AI chỉnh `HYB_EDGE_LO / HI`, `HYB_FLOW_SHARE`.
- [ ] **(13/11) XDoG:** (a) preset "Phác họa ảnh" với ảnh em bé + ảnh thú, A5; so với kiểu Nét viền tắt XDoG. (b) Chân dung tích thêm "Thêm lớp viền": có che bớt móc chữ U vùng sáng không, có rối không. Nếu thiếu nét → Chi tiết viền "Nhiều"; vụn → "Ít".
- [ ] **(13/11) Sóng biên độ, chỉnh trên máy thật:** in lại tờ tông kiểu Sóng biên độ (nay có lớp gạch vùng đậm) + một ảnh phong cảnh tối. Ghi: ô 90 % có đen chưa, lớp gạch thẳng có làm mất vẻ mượt không, máy có rung ở sóng dày không (khung đã chắc hơn), thời gian / số lần nhấc. Không thích lớp gạch → `AM_DARK_LAYER = False` (`styles.py`). Muốn sóng dày hơn (khung đỡ rung): thử `AM_SPACING_LINES` 4 → 3 (mô phỏng: ô 90 % 0,78 → 0,81 khi chưa có lớp gạch).
- [ ] **(tùy chọn) Tờ tông cho UB-155 đen:** đường cong tông hiện đo bằng Sakura 0,5 mặt bóng, dùng chung cho mọi bút. Muốn chính xác cho Uniball: 1 tờ tông kiểu Gạch chéo, bề rộng nét = số ở ô Bút vẽ (0,38), cùng mặt giấy; gửi ảnh → AI thêm bảng riêng theo bút. Không dùng mực đỏ để đo tông.

- [ ] Đặt `data\pin.txt` dòng `admin=…` bằng **PIN khó đoán** (chỉ PIN đăng nhập; không cần `unlock=`); vào bằng điện thoại xem có ra giao diện khách.
- [ ] **Thử các việc mới (09/11/2026)** trên máy thật: (a) nút Bút lên / Home nâng tới Z5; tệp G-code nhấc Z3 vẫn chạy đúng; (b) Cài đặt → PIN quản lý: đổi PIN, đăng nhập lại bằng điện thoại; (c) Điều khiển → Khung 2D → **Biểu đồ**: chạy một tệp thật, xem tốc độ thật, hàng đợi, Z; (d) so sánh hai lần chạy.
- [ ] **Thử luồng khách** (cần đã đặt PIN): mở trang bằng điện thoại (không đăng nhập) → tab Tạo bản vẽ → chọn ảnh, cắt, khổ giấy, bấm **Gửi ảnh**; trên laptop (đăng nhập) mở hộp thư "Ảnh khách gửi" → **Mở** → kiểm thông số → **Tạo nét**. Xem cảnh báo gửi quá 6 ảnh / giờ và ảnh tự xóa sau 5 ngày.
- [ ] **Thử tờ thử mới**: Cài đặt → Tờ thử / hiệu chỉnh → tạo tờ nhấc bút, nạp ở Điều khiển, chạy, chọn hàng đẹp → **Dùng**; kiểm tab Tạo bản vẽ có đổi Z nhấc / chờ / tốc độ hạ.
- [ ] Bật báo bộ đệm: terminal gõ `$10=3` (11/11 đã gõ), rồi gõ `$10` xem máy trả `$10=3`. **Chạy một bản vẽ MỚI** rồi mở Biểu đồ của lần chạy đó: có đường "hàng đợi" = đã có `Bf`. Lần chạy trước khi gõ `$10=3` (vd con mèo) vĩnh viễn không có. Tắt bật máy, gõ lại `$10` xem còn 3 không.
- [ ] **Tờ hiệu chỉnh tông** (07 mục 2b): A6, Sakura 0,5 × 3 kiểu gạch (zigzag, gạch chéo, đan 3 hướng), cùng mặt giấy / tốc độ 8000; chụp thẳng, sáng đều, gửi ảnh gốc → AI dựng đường cong tông.
- [ ] Gửi 2–3 ảnh thật cho XDoG (ảnh em bé, ngược sáng, đèn đêm) và ảnh chân dung động vật cho flow field; gửi nhật ký chạy `data/job_logs` (sau `$10=3`) của một bức sóng biên độ và một bức gạch chéo cho phần buffer / G2-G3.
- [ ] **Kiểm độ mượt tab Điều khiển** (laptop yếu): nạp tệp lớn (ảnh A5 nhiều nét), chạy tác vụ, thử bấm đổi tab / bấm nút khi đang chạy; so với trước. Nếu còn khựng: ghi laptop gì, bao nhiêu dòng G-code, và F12 → Performance ghi 5 giây khi đang chạy.
- [ ] **Sau bản 12/11 (khởi động lại phần mềm trước):** (1) bật mạch → Home → bấm thử jog X/Y: bút có còn tụt không (log có hai dòng `$J=… Z4.5` rồi `Z5` sau `$H`); (2) tờ nhấc bút tick thêm ô **chờ 0**, Z3, hạ 2000: hàng chờ 0 có kéo vệt / hụt đầu nét không; (3) vẽ lại ảnh em bé (Chân dung = đan chéo) A5 Sakura 0,5: so thời gian thật với ước tính mới, soi chỗ nối nét có lộ không (bật / tắt ô "Nối nét gần" nếu cần so); (4) một bức sóng biên độ: thời gian thật / ước tính.
- [ ] Tốc độ tối đa 10000 (đoạn dài): nếu muốn giữ thì Cấu hình máy → Lưu vào mạch; ô Tốc độ di chuyển có thể lên 10000 khi đó.
- [ ] Tắt Wi-Fi của mạch MKS trước khi cho người khác vào mạng.
- [ ] Vẽ lại Phong cảnh với mặc định mới; chụp cận mép khối xem còn giọt mực ở chỗ quay đầu không.
- [ ] Bài 7.1 (đo thời gian một chu kỳ nhấc bút), 7.3 (gia tốc), 7.5 (vệt kéo), mỗi bài một tờ.
- [ ] Thời gian Home, Z nâng / hạ thật. Bản vẽ thật đầu tiên có cung G2/G3 do phần mềm sinh (từ 13/11): chạy hết không báo lỗi, nét cong mượt.
- [ ] Đèn X / Y sáng đúng khi tay đè công tắc.
- [ ] DIP3 (nối chân vị trí MS3 của driver): xem chữ in dưới module TMC2209 là **SPREAD** hay **PDN_UART**. Thử nghe: tắt nguồn → gạt → chạy G0; ồn hẳn lên = SpreadCycle. Nếu là SPREAD thì chạy 7.2b ở SpreadCycle (hai trục cùng chế độ).
- [ ] Tiếp tục từ điểm dừng trên máy thật: hủy giữa chừng → Home → Tiếp tục, so nét chồng.
- [ ] Đo thời gian vẽ thật so với ước tính; ghi vào [07_THU_NGHIEM.md](07_THU_NGHIEM.md) mục 7.

## 4. Chưa kiểm chứng (cần máy hoặc môi trường thật)
| Việc | Cách kiểm |
|---|---|
| Khoảng cách nét / số mức / gamma từng preset | thang xám + ảnh thật ([07_THU_NGHIEM.md](07_THU_NGHIEM.md)) |
| Quay đầu nửa vòng tròn có hết giọt mực | chụp cận |
| `G4 P` tính bằng giây trên FluidNC 4.1.1 | đo |
| Thời gian ước tính (bản 13/11: gia tốc + 0,025 s / lần nhấc + 0,025 s / G4 + giới hạn 125 dòng/giây; khớp tờ 7.6 và tờ nhấc bút) | so thời gian thật / ước tính trên các bức chân dung, sóng biên độ. Ngày 12/11 bản vẽ thật = 1,7–1,9 × ước tính cũ; bản mới có thể ước **thấp** hơn thật nếu phần chậm đó không do nhấc bút |
| Biên lùi 64 dòng khi tiếp tục có đủ | hủy bản vẽ dài, tiếp tục |
| Xử lý ảnh trên MiniPC i5-3210M; giới hạn RAM trên Ubuntu | `info.timings`, `htop` |
| Chia màu với ảnh có màu rất nhỏ | ảnh nhiều màu nền sáng |
| Giao diện trên điện thoại thật (cắt ảnh bằng ngón tay, hộp "Tác vụ đã dừng") | điện thoại |
| Bản mang đi trên máy sạch (Visual C++ của OpenCV) | máy bạn bè |

## 5. Code tiếp, xếp theo ưu tiên
- [ ] (14/11, chủ dự án đồng ý, chưa gấp) **Khoanh vùng chủ thể cho Chân dung**: kéo elip / chữ nhật trên khung Cắt ảnh; ngoài vùng gạch nhạt đi hoặc chỉ viền. Nền vẫn vẽ (giữ đúng kiểu ảnh), chỉ nhạt hơn để chủ thể nổi.
Kế hoạch chốt 09/11/2026: làm lần lượt **bước 1 → 6** (không cần in giấy để kiểm), rồi tới các việc cần máy / dây / in thật.

| Bước | Việc | Cỡ | Chi tiết |
|---|---|---|---|
| 1a ✅ | Đổi nhãn "Độ lệch góc (junction)" thành "Độ bo góc khi qua góc (junction)" | S | xong 09/11/2026 (chưa thêm dòng gợi ý 0,02–0,1) |
| 1b ✅ | Dọn: bỏ nhắc `project-export.json` trong `AI_START.md`, `.gitignore` thêm `*.gcode` ở gốc | S | tệp đã không còn dùng |
| 1c ✅ | **Tách Z**: "Z bút lên (điều khiển)" = **5** cho nút Bút lên, Home tự nâng, hủy tác vụ nâng bút, jog; "Z nhấc khi sinh G-code" = **3** (chỉnh 3 / 2 / 1,5 theo bản vẽ). Khung 2D đoán bút lên bằng "Z > Z xuống + 0,5" thay vì ngưỡng giữa | S–M | điều khiển tay nhấc cao cho chắc, chỉ G-code nhấc thấp cho nhanh (09 C4) |
| 1d ✅ | **Đổi PIN đăng nhập** trên giao diện (Cài đặt): nhập PIN cũ + mới hai lần → ghi `data/pin.txt`, áp dụng ngay, đăng xuất phiên khác. Máy chủ tự đọc `pin.txt` (không chỉ qua launcher) để dùng được trên MiniPC. PIN có chữ được, dài tuỳ ý, tránh dấu tiếng Việt / khoảng trắng, nên ≥ 6 ký tự | S | PIN mở khóa chuyển động **không dùng** (không ghi `unlock=`) |
| 2 ✅ | **Biểu đồ số liệu chạy máy**: mỗi báo cáo `?` khi chạy tệp ghi một dòng `data/job_logs/*.csv` (giờ, trạng thái, X Y Z, `FS:`, `Bf:`, số dòng đã nhận; giữ ~30 lần). Trong "Khung nhìn 2D" tab Điều khiển thêm nút chuyển **[Đường vẽ / Biểu đồ]**: tốc độ thật so với tốc độ đặt, bộ đệm (đói lệnh), Z; số tổng (thời gian thật / ước tính, % vẽ / di chuyển / nhấc bút); so sánh hai lần chạy; tải CSV. Tự vẽ bằng canvas (không thư viện ngoài, O8). Máy giả chỉ báo `Bf` khi `$10` có bit 2 (như máy thật); thiếu `Bf` thì nhắc gõ `$10=3` | M | mọi số đo sau dựa vào đây; quyết bước 7 (baud) |
| 3 ✅ | **Mục "Tờ thử / hiệu chỉnh"** trong Cài đặt → Cấu hình máy, mỗi nút tạo một bản thảo: tờ hiệu chỉnh bút (đưa nút trở lại), **tờ nhấc bút mới** (mỗi hàng một tổ hợp Z nhấc / chờ / tốc độ hạ; **Z nhấc dùng các mốc 1 / 3 / 5 mm** theo thói quen, thêm 1,5 / 2 nếu cần, đầu hàng có số chấm = số hàng; bảng hàng → thông số; nút "Dùng hàng N" ghi vào Z G-code / chờ / tốc độ hạ; thời gian thật từng hàng lấy từ biểu đồ), bộ thử 7.2 / 7.3 / 7.4 / 7.5 (từ `tools/make_test_gcode.py`). Thang xám vẫn ở tab vẽ | S–M | khỏi chạy lệnh tay; chọn mức nhấc bút bằng mắt |
| 4 ✅ | **Nạp ảnh chưa tạo nét**: nạp chỉ hiện ảnh xám, cắt + chỉnh tông trên trình duyệt, bấm **"Tạo nét"** mới chạy máy chủ. Sau lần đầu, kéo khung lệch > 12 % vẫn tự tạo lại | S–M | MiniPC không tạo nét cho lần chỉnh dở; khớp luồng khách (09 P9 / O7) |
| 5 ✅ | **SSE** cho trạng thái + terminal (lệnh giữ HTTP): luồng SSE nhìn số thứ tự trạng thái ~20 lần/s, ping ~20 s chống Cloudflare cắt; **giữ hỏi lặp làm dự phòng** (SSE hỏng thì tự quay về). Lưu ý trình duyệt chỉ mở 6 kết nối / địa chỉ | M | người xem qua Cloudflare đỡ trễ, đỡ tải (09 A6) |
| 6 ✅ | **Khách gửi ảnh**: khách cắt, chọn khổ / xoay / kích thước, chỉnh tông (thêm thanh Sáng / Tương phản quy về điểm đen / trắng + gamma), chọn preset / kiểu tô "mong muốn"; chỉ xem trước **ảnh xám** (không có mô phỏng G-code). Nút "Gửi ảnh" thay "Tạo nét" → ảnh thu nhỏ ~1000 px + thông số + tên / ghi chú vào `data/customer/`, giới hạn dung lượng / số ảnh mỗi giờ / tổng; **tự xóa sau 5 ngày** (chỉnh 3–5 trong Cài đặt → Dữ liệu). Quản lý: danh sách, mở là tab vẽ tự điền thông số, xóa. Bản thảo (SVG, G-code, JSON) giữ như cũ | M–L | hết cảnh gửi ảnh qua lại ([08_TRIEN_KHAI.md](08_TRIEN_KHAI.md) B4; 09 S9) |

Sau đó (cần đo, dây hoặc in thật):

| # | Việc | Cỡ | Vì sao |
|---|---|---|---|
| 7 ✖ | ~~Nâng baud + gửi dồn nhiều dòng~~ **không làm** (13/11/2026) | — | đo: máy nhận ~125 dòng/giây do chờ `ok`, không do baud; mô phỏng: bản vẽ thật không chậm vì giới hạn này; nét cong đã ghi bằng G2/G3 (09 D10–D12) |
| 8 | Đường cong tông từ thang xám in thật | S | tông giữa đúng với mắt (cần tờ in trước) |
| 9 | Tab Beta in PDF: preset "Văn bản", đường kẻ vector, hai bút | L | mục tiêu chữ viết ([10_HUONG_PHAT_TRIEN.md](10_HUONG_PHAT_TRIEN.md) 1.1) |
| 10 | Cảm biến bút + hai nút cứng Tạm dừng / Chạy tiếp (YAML + dây, đèn "Bút") | S + dây | an toàn, dừng khẩn không phụ thuộc mạng (09 O9) |
| 11 | ESP32-S3: bảng điều khiển không dây, đo điện năng, đo nhiệt (chọn 1–2) | L | phần IoT trình diễn được |
| 12 | Tự hiệu chỉnh bằng ảnh chụp tờ mẫu (ArUco) | M | khỏi đo tay bề rộng nét |
| 13 | Mã QR địa chỉ, `.devcontainer/` | S | chưa vội |

**Việc nhỏ còn sót:** thêm dòng gợi ý "0,02–0,1; lớn hơn = qua góc nhanh hơn" dưới ô junction trong Cấu hình máy (bước 1a mới đổi nhãn). Chỉ có `$10` trên máy giả; máy thật bật `$10=3` bằng tay (mục 3).

**Không làm:** hồ sơ tốc độ (Chữ / Tranh / Đẹp nhất). Mặc định luôn chạy nhanh nhất có thể và nhấc bút thấp nhất đủ dùng; khi cần thì chỉnh tay.

## 6. Khi có MiniPC
- [ ] Đo thời gian xử lý ảnh, RAM, máy có giật không.
- [ ] Docker + quyền cổng USB + tên cổng cố định (udev), IP cố định.
- [ ] Thử Origin / cookie qua Cloudflare Tunnel; chỉ mở ra ngoài khi đã đặt PIN.

## 7. Cần bạn cung cấp / quyết
- Ảnh tờ hiệu chỉnh, thang xám và số đo sau mỗi buổi thử.
- Chưa đặt PIN quản lý thì cho ai vào cũng là quản lý (đang vậy) hay chặn hẳn khi mở ra ngoài.
- Hướng ưu tiên tiếp: chữ PDF, IoT (ESP32), hay tốc độ / chất lượng nét.
- Thiết bị demo không mạng: router mini (hoặc 4G), in sẵn mã QR.
- Dụng cụ đo có sẵn: máy hiện sóng, logic analyzer?
