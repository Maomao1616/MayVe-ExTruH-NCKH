# 09 — Quyết định thiết kế: chọn gì, vì sao

> Dành cho người đọc và người viết báo cáo (phần "lý do lựa chọn"). Mỗi dòng: quyết định, lý do, mức chắc chắn.
> Ký hiệu: ✅ đã làm và kiểm (máy thật hoặc test tự động) · 🧪 làm rồi, chưa kiểm trên giấy / môi trường thật · ⏳ đã quyết, chưa làm.
> Trước khi đổi một hành vi trong bảng này, đọc lý do của nó. Mã số (A1, C4…) giữ nguyên để tra lịch sử Git; dòng đã bị thay thế (P22, P23, P38, P39) đã bỏ, tra Git. Số đo chi tiết và hằng số: [06](06_THUAT_TOAN_XU_LY_ANH.md).

## 1. Kiến trúc
| # | Quyết định | Vì sao | |
|---|---|---|---|
| A1 | Máy chủ Python (FastAPI) + giao diện JavaScript thuần | xử lý ảnh hợp Python (OpenCV, scikit-image, vpype); JS thuần không cần bước build, dễ giao cho người khác | ✅ |
| A2 | Giao diện chỉ hiển thị, máy chủ là nguồn sự thật; **giao diện không chạm cổng serial** | tránh đoán sai trạng thái; mọi lệnh được kiểm ở một chỗ | ✅ |
| A3 | Không framework, không bước build | đơn giản, chạy được trên máy yếu, ít phụ thuộc | ✅ |
| A4 | Hai đường nối máy: máy thật (SerialLink) và máy giả (SimLink, bắt chước theo log board thật) | phát triển và test khi chưa có máy | ✅ |
| A5 | Chỉ `api.js` gọi mạng, chỉ `state.js` thăm dò; một phần tử HTML chỉ một tệp ghi | một nơi để sửa, không giật | ✅ |
| A6 | **Lệnh** qua HTTP POST; **trạng thái + terminal** qua **SSE** (đẩy một chiều); **không dùng WebSocket** | qua Internet mỗi lần hỏi lặp tốn một vòng đi–về, SSE nhanh gần gấp đôi; SSE chạy trên HTTP, tự nối lại, dùng được cookie PIN. WebSocket phải tự lo nối lại, kiểm Origin mà lệnh chỉ nhanh thêm 1–2 ms | ✅ SSE (máy giả, 09/11/2026) · ⏳ qua Cloudflare thật |
| A7 | Mỗi tab một tệp view. Bỏ tab Công việc (gộp vào Điều khiển). **Bỏ thẻ SD / Flash** | thực tế chỉ stream từ máy tính; MKS đọc thẻ dễ lỗi | ✅ |
| P1 | Mọi tham số vẽ khai báo **một chỗ** (`spec.py`), giao diện lấy qua `/api/draw/schema` | không rải số cứng; đổi một dòng | ✅ |
| P2 | Tab vẽ **không bao giờ gọi máy**; hai tab chỉ nối qua bản thảo | an toàn | ✅ |

## 2. Điều khiển máy và an toàn
| # | Quyết định | Vì sao | |
|---|---|---|---|
| C1 | Jog, bút, Zero chỉ khi Idle; Home khi Idle / Alarm | an toàn | ✅ |
| C2 | Jog dùng `$J=…` | chạy được khi chưa Home, hủy được ngay | ✅ |
| C3 | Zero dùng `G10 L20 P1` | chuẩn FluidNC | ✅ |
| C4 | Bút 3 nấc (nút tay) **Z5 / Z3 / Z0** = Lên / Giữa / Xuống, gửi `G90 G0 Z…` (không dùng `$J=`: nghi làm servo giật, P33). Điều khiển tay (Bút lên, Home, hủy, jog) nhấc **Z5**; G-code sinh ra nhấc thấp (mặc định Z3). Khung 2D coi bút xuống khi Z ≤ Z xuống + 0,5 mm | nhấc 3 mm đủ khỏi giấy, nhanh hơn; điều khiển tay hiếm khi cần nhanh nên nhấc cao cho chắc | 🧪 chưa thử lâu trên giấy cong · ✅ tách (máy giả) |
| C5 | Gốc (0,0) trên trái, Y xuống; không lật khung 2D, không đảo trục Y | ✅ chủ dự án xác nhận hướng trục đúng 05/11/2026 | ✅ |
| C6 | Nút Tạm dừng chỉ cho tác vụ; nút Hủy jog riêng | đúng bản chất firmware (Hold hủy jog, không resume được) | ✅ |
| C7 | Cấu hình máy một panel: "Máy" (YAML trên mạch: Áp dụng vào RAM, Lưu vào mạch sau khi sao lưu) và "App" (hồ sơ phần mềm). Không cho sửa chân GPIO, kinematics | chỉnh thông số không cần WebUI / Wi-Fi | ✅ |
| C8 | **Home tự nâng bút trước** (03/11/2026) | bút hạ bằng trọng lực, quên nâng thì kéo vệt chéo qua giấy | ✅ |
| C9 | **Bỏ bước bắt buộc "Xem trước" + ô tích xác nhận** trước nút ▶ Chạy (12/11/2026, chủ dự án). Nút Chạy vẫn cần: máy nối và dữ liệu mới, đã mở khóa chuyển động, máy Idle, tệp không có dòng bị cấm / ngoài hành trình. Công tắc `REQUIRE_PREVIEW_CONFIRM` ở đầu `views/control.js` (`true` là có lại) | nạp tệp là khung 2D hiện ngay đường chạy + vùng làm việc; chống chạy nhầm do khóa chuyển động (mặc định chỉ đọc, tự khóa sau 15 phút) và Idle đảm nhận | ✅ (ẩn) · ⏳ chủ dự án dùng thử |
| C10 | **Chờ sau nâng / hạ bút mặc định 0** (13/11/2026); ô chờ vẫn gõ được (`spec.py` `delay_up_s` / `delay_down_s`) | tờ nhấc bút 13/11: chờ 0 nét đủ, không hụt đầu nét, hàng đợi máy đầy suốt; chờ 0,02 làm hàng đợi tụt về 0 mỗi lần nhấc, chậm ~0,08 s mỗi lần | ✅ |
| D4 | Hủy 3 chế độ: `soft` (mặc định: chạy hết bộ đệm, nâng bút), `hard` (Hold → Reset → `$X` → nâng bút), `reset`. Chỉ báo "đã nâng bút" khi báo cáo xác nhận Z | giữ được Home khi có thể; không báo an toàn giả | ✅ |
| D10 | Gửi từng dòng, chờ `ok` (**giữ**, 13/11/2026); **không làm "gửi dồn"** | đo tờ 7.6: chỉ ~125 dòng/giây (~8 ms mỗi dòng), chuỗi đoạn < 1 mm ở 8000 bị chậm; nhưng mô phỏng trên bản vẽ thật (khớp số đo trong 4 %) chậm thêm **~0 %** vì đoạn ngắn đi từng cụm xen nét dài, bộ đệm 15 khối nạp lại kịp. Gửi dồn làm dừng / lỗi / tiếp tục phức tạp hơn mà gần như không lợi | ✅ |
| D11 | Giữ **115200 baud** (chốt 13/11/2026) | chỗ chậm là chờ `ok`, không phải tốc độ dây (truyền chữ ~2 ms trong ~8 ms mỗi dòng); đổi baud phải đổi cả YAML lẫn app, đặt sai thì khó nối lại | ✅ |
| D12 | **Gộp nét thành cung G2/G3 + đoạn G1 dài** (13/11/2026, chủ dự án chọn sau tờ 7.6); sai lệch ≤ 0,02 mm (`arcs.py`); tắt bằng `USE_ARCS = False` ở `gcode.py` | tờ 7.6: vòng tròn bằng G2 chạy 5,7 s đủ tốc; cùng vòng bằng G1 đoạn 0,1 mm 60,7 s; trên giấy không khác. Ảnh mẫu bớt 6–25 % số dòng | ✅ máy giả · ⏳ in thật |
| M6 | Sau `$X` máy chạy được G-code kể cả chưa Home → giao diện cảnh báo | sự thật firmware | ✅ |
| S7 | Bộ làm sạch G-code chặn `$…`, ký tự tức thời, `G10 G28 G30 G38 G53 G55–G59 G92`; báo một lần tối đa 5 dòng kèm số dòng. Giao diện giữ cùng danh sách | các lệnh đó đổi gốc / hệ tọa độ → bản vẽ lệch khỏi giấy; danh sách ngắn để tệp thường không bị từ chối oan | ✅ |
| P11 | Tiếp tục từ điểm dừng: lùi 64 dòng rồi lùi tới đầu nét gần nhất, dựng lại trạng thái, kiểm gốc Zero | `ok` chỉ là "đã vào hàng đợi"; vẽ chồng vô hại, bỏ sót thì mất nét | ✅ máy giả · 🧪 máy thật |
| O2 | Hai vai trò khách / quản lý bằng PIN; máy chủ **chặn mặc định**; vẫn giữ lớp mở khóa chuyển động (**không đặt PIN** cho lớp này, PIN chỉ dùng để đăng nhập, 09/11/2026) | đề tài cấp trường: khách chỉ xem / gửi ảnh, không cần tài khoản, hàng chờ | ✅ (gửi ảnh ✅ 09/11/2026) |

## 3. Tạo bản vẽ và xử lý ảnh
| # | Quyết định | Vì sao | |
|---|---|---|---|
| P3 | Ảnh → nét chạy ở **tiến trình con ưu tiên thấp**; hủy = kết thúc tiến trình; trần 600 s (Bỏ giới hạn 1 800 s), 4 GB (Linux) | MiniPC yếu vừa điều khiển vừa xử lý; ảnh lạ không làm sập server | ✅ (RAM trên Ubuntu 🧪) |
| P4 | Thứ tự: EXIF → cắt → thu nhỏ → lọc sắc độ → tạo nét | chi phí tỷ lệ số điểm ảnh | ✅ |
| P5 | Cỡ làm việc = khung ÷ bút × 1,3 (400–4000 điểm); ảnh nhỏ chỉ phóng tới 720; kéo khung lệch > 12 % thì tạo lại nét | khoảng cách nét đúng theo mm thật; thêm điểm ảnh không thêm chi tiết | ✅ |
| P6 | 5 kiểu trên giao diện: **Gạch chéo** (mặc định) · **Theo dáng ảnh** · **Sóng biến thiên** · **Xoắn ốc** · **Nét viền**; thêm lớp viền tùy chọn. Kiểu ẩn (mã giữ): zigzag, sóng thường, đan 3 hướng | ít nhấc bút; không vượt 200 000 dòng | ✅ · 🧪 in giấy |
| P15 | **Mỗi mức đậm nhạt = một dải, một lượt gạch, khoảng cách riêng** (độ phủ 0 → 90 % chia đều, s = nét thật ÷ độ phủ); 5 mức mặc định | mô phỏng: sai số 0,174 → 0,071, nét ngắn hơn 45 % so với chồng lớp | ✅ mô phỏng · 🧪 in giấy |
| P16 | Zigzag / sóng quay đầu bằng **nửa vòng tròn** | góc vuông ép máy chậm gần 0, mực đọng thành giọt | 🧪 |
| P17 | **Vẽ lần lượt từng mức** (nhạt → đậm, viền cuối): có ô, **mặc định tắt** từ 12/11/2026 | in thật thấy nhấc bút nhiều, lâu hơn; quãng bay ≈ × 3 | ✅ |
| P18 | **Nối nét gần** thay vì nhấc bút (`optimize.bridge`, mặc định bật): đầu nét sau ≤ 4 × bề rộng nét và đoạn nối nằm trong vùng đậm ≥ 0,2; không dùng cho viền / nhiều màu | 55–80 % lần nhấc chỉ bay ≤ 2–3 mm; ảnh mẫu A5 bớt 55–82 % lần nhấc, nhanh 30–50 %, mực +3 % | ✅ mô phỏng · 🧪 in giấy |
| P19 | **Ước tính thời gian có gia tốc** (hình thang, gia tốc 2700, junction 0,02 như máy; + 0,025 s mỗi lần nhấc, + 0,025 s mỗi G4, tối đa 125 dòng/giây); backend và `lib/gcode.js` cùng công thức; số lần nhấc đếm theo Z | cách cũ (quãng ÷ tốc độ) ngắn hơn thật 1,7–1,9 lần; nay tờ 7.6 ước 110,9 / thật 111 s, A4 thật ÷ ước 0,87–0,94 | ✅ |
| P20 | **Khung xem trước vẽ theo lớp, lưu sẵn** (`preview.js`): mỗi lần có vị trí máy chỉ dán lại + vẽ thêm đoạn mới | vẽ lại cả tệp 10 lần/giây làm tab Điều khiển đơ trên laptop yếu | ✅ test · ⏳ đo trên máy yếu |
| P13 | Viền: top-hat (nét mực ≤ 4 mm → đường giữa) + Canny trên ảnh làm phẳng màu (mean shift, kênh a / b Lab) + vòng viền chấm + nối khe ≤ 3 mm + cắt râu theo bề dày nét + khép vòng. Thay DoG cũ | DoG cho hai đường song song ở nét dày, mất viền mảng không có nét đen | ✅ ảnh mẫu · 🧪 in giấy |
| P21 | **Đường cong tông** cho gạch chéo (đo trên tờ tông, áp **75 %**, `TONE_CURVE_STRENGTH`); Theo dáng và Xoắn ốc **không** áp | tờ tông 13/11: phủ 50 % chỉ trông 0,39; áp đủ thì dải chuyển liền đậm quá, 0,75 cân hai bên. Bảng đo cho một bút + một mặt giấy | ✅ mô phỏng · ⏳ in lại |
| P24 | **Sóng biến thiên thêm lớp gạch thẳng ở vùng rất đậm** (`AM_DARK_LAYER`) | ô 90 % chỉ trông 0,71 (sườn sóng đè nhau); có lớp bù 0,89. Đổi lại ảnh tối nhấc bút nhiều hơn | ✅ mô phỏng · ⏳ in thử |
| P26 | **FDoG cho lớp ranh giới mảng**: lớp viền phủ lên kiểu tô luôn dùng; kiểu Nét viền bật bằng ô (`style.outline_xdog`); khối đậm dày > 2 mm chỉ lấy vành | ra mắt / mũi / miệng rõ hơn Canny, ít vụn, viền mắt khép. Hạn chế: chỉ nhìn độ sáng, bỏ sót ranh giới hai màu cùng độ sáng nên ảnh 2D vẫn Canny | ✅ mô phỏng · ⏳ in thật |
| P27 | **Nét gọn** (chủ dự án: "chi tiết đậm hẹp mất đi trông gọn hơn"): gạch bỏ dải đậm hẹp < 1,5 × khoảng cách nét, mẩu gạch < **5 mm** (P37), chỉ nối bằng vòng quay đầu; độ phủ < 0,2 để trắng hẳn. Nét viền làm mượt 0,8 mm | ảnh chân dung A4: 1120 → 867 nét, 19,4 → 16,2 phút. Bỏ dải < 2,5 × làm mất mũi, mắt nên chọn 1,5 | ✅ mô phỏng · ⏳ in thật |
| P28 | **Đan chéo và theo dáng là hai kiểu riêng**; bản lai đã **xóa mã** 17/11/2026. Đã thử rồi bỏ (chủ dự án: "nét không còn đẹp nữa"): hàng rào viền, quay đầu góc bo, kéo mức nhạt lấn mức đậm, rải đều khe sáng | bản lai làm khối rối, lệch tông; đan chéo + lớp viền đẹp nhất. Chữ U ở mảng sáng hẹp trong tóc còn lại | ✅ |
| P29 | **Ô Tương phản** (`raster.contrast`, 0,5–3, sau gamma). Sóng biến thiên: lưới thưa nhất chỉ có từ độ phủ 0,10; ô **"Phủ đều đường ở vùng sáng"** (`style.am_fill`, bật ở Chân dung) | ở tông da sóng bớt đường nên có vệt trắng 3,2 mm trên mặt; phủ đều thì da kín đường, đậm hơn ảnh chút | ✅ · ⏳ in thật |
| P30 | **Theo dáng ảnh áp được đậm nhạt**: kiểm "đã có đường chưa" bằng cửa sổ **tròn** (không vuông), `FLOW_TEST_RATIO` 0,7; không đường cong tông | cửa sổ vuông làm ô phẳng 0,4 / 0,6 / 0,9 ra cùng số nét; cửa sổ tròn cho khoảng cách khớp yêu cầu. Thêm đường cong tông làm đậm quá | ✅ mô phỏng · ⏳ in thật |
| P31 | **Vùng chủ thể**: ngoài vùng độ đậm × `subject_outside` (mặc định 0,5), mép mờ ± 8 %; vùng tính theo ảnh **gốc** nên đổi vùng cắt không lệch. Hình: elip, chữ nhật, Tự động, Vẽ tay (P46) | nền vẫn vẽ nhưng nhạt, chủ thể nổi; ảnh cô gái A4: 11,4 → 8,6 phút, mực 27,7 → 20,9 m | ✅ · ⏳ in thật |
| P32 | **Báo vẽ xong / lỗi**: âm báo WebAudio (không tệp, chạy offline) + tiêu đề tab nhấp nháy khi tab ẩn; hủy do người bấm thì im; công tắc ở Cài đặt → Hoạt động | người đứng xa máy biết bản vẽ xong hoặc hỏng; không Internet nên không dùng Telegram | ✅ test · ⏳ nghe thử |
| P33 | **Nút bút gửi `G90 G0 Z…`** (không `$J=`), Giữa = Z3; màu nhấn vàng an toàn `#ffd400`; hai khung vẽ là giấy ngà `#cfcbbd` + nét đen như bản in; nét "đã vẽ" xanh lá đậm; nhóm Tối ưu nét có nút **Về mặc định** | nghi servo tụt do `$J=`; khung vẽ giống bản in để nhìn ra khối đậm nhạt; chủ dự án chọn bộ màu A trong 3 bộ | ✅ test · ⏳ servo trên máy (07 B2) |
| P34 | **Vòng sửa sai** (`refine.py`, chủ dự án yêu cầu): tô → dựng ảnh mực đúng bề rộng bút → làm mờ 2 mm → so với độ phủ định vẽ → trừ 0,8 × sai số khỏi mục tiêu → tô lại; 1 lượt mặc định (0–3). Áp cho Gạch chéo, Sóng biến thiên; không cho Theo dáng (3 lượt không đổi mực), Xoắn ốc, Nét viền | các kiểu tô vẽ ít mực hơn định 5–8 %, một chiều; một vòng phản hồi sửa chung cho mọi kiểu. 1 lượt: sai số −40…−58 %, mực và thời gian +4…8 %. Bộ dựng mực đối chiếu diện tích hợp nét (shapely) 0,97–1,00 × | ✅ test + 3 ảnh thật · ⏳ in thật (07 A5) |
| P35 | **Thử AI cho nét vẽ rồi bỏ hẳn** (18/11/2026, chủ dự án): Informative Drawings, U²-Net Portrait, Depth Anything V2 Small (ONNX, CPU). Đã xóa mã, mô hình, gói `onnxruntime` | ảnh chì phải ép thành nét thì mất kết cấu; độ sâu làm hướng nét không hơn hướng lấy từ ảnh; mô hình đẹp hơn thì quá nặng cho MiniPC i5-6100T | ✅ bỏ |
| P36 | **Chốt thuật toán vẽ ảnh** (18/11/2026, chủ dự án): 5 kiểu + preset + vòng sửa sai + làm nét; sau đó thêm Bỏ giới hạn (P40), Xoắn ốc mới (P41), tách mực (P44). **Không thêm kiểu vẽ hay mô hình AI mới**; chỉ chỉnh hằng số theo kết quả in (nêu số trước / sau) | đã thử và bỏ: Khối (SLIC), Phác chì AI, viền AI, độ sâu làm hướng nét; việc còn lại là đo trên giấy và MiniPC | ✅ chốt · ⏳ in giấy |
| P37 | **Bớt râu 5 mm** (`HATCH_MIN_RUN_MM`); tờ thang tông: mốc đen 10 mm, chữ F nét 6 mm, có test khóa | 6 mm xóa sạch mốc và chữ F (không đo được bằng `tone_read.py`); 4 mm làm bậc mức mềm hỏng ngưỡng test | ✅ test · ⏳ in tờ tông mới |
| P40 | **Ô Bỏ giới hạn** (`style.unlimited`, giao diện ghi "Chất lượng tối đa"; 22/11/2026, thay hai kiểu "siêu chi tiết" 19/11) cho Gạch chéo · Theo dáng · Sóng biến thiên: 8 mức, sửa sai ≥ 2, giữ nét nhỏ, tạo nét tối đa 30 phút; mỗi kiểu một bộ hằng riêng (06 mục 8.8). Preset **Siêu chi tiết** = Gạch chéo + ô này. Tên kiểu cũ vẫn mở bản thảo cũ | chủ dự án: DrawingBotV3 đẹp vì không giới hạn thời gian và nhấc bút → thêm một ô, giữ kiểu nhanh làm mặc định. A4: 2D 11,5 → 20,2 phút; mèo 7,4 → 9,2; phong cảnh 25,2 → 29,3 (nhà gỗ, cây hiện ra) | ✅ test · ⏳ in thật |
| P41 | **Xoắn ốc viết lại** (22/11/2026): **một** xoắn, bước 5,5 × nét, sóng dọc đường xoắn có biên độ theo độ đậm | bản cũ (mỗi mức một xoắn đồng tâm) chỉ ra vòng tròn, không nhận ra hình; bước 3,2 × cho cả ảnh xám đều | ✅ test · ⏳ in giấy |
| P42 | **Nét viền riêng bỏ nét < 2,5 mm** (lớp viền phủ kiểu tô giữ 6 mm); preset **Schematic** bật FDoG + chi tiết Nhiều | bản vẽ kỹ thuật: 6 mm mất vạch chia, nét chữ (38 → 73 nét); ảnh scan nhiễu: Canny mất nét gạch mảnh, FDoG giữ đủ | ✅ test · ⏳ in |
| P43 | **Máy chốt gia tốc 2700, junction 0,02, servo 5,3 V** (22/11/2026); ước tính thời gian sửa theo | chủ dự án: "an toàn cho máy, đỡ rung lắc, không chậm hơn quá nhiều"; servo 5,3 V ổn định hơn 5,9 V (chưa đo gợn áp) | ✅ · ⏳ in giấy |
| P44 | **Tách mực theo bộ bút** (`palette.mode = inks`): `kdn` đen · đỏ · navy (mặc định) hoặc `cmyk`; mỗi bút một lớp, nhạt trước, đen sau cùng; ô **Độ nổi màu** (`ink_boost`, mặc định 0,5) bớt đen lấn ở chỗ tối | k-means chia VÙNG nên chỗ tím phải chọn một màu; tách mực cho mỗi bút tô cả chỗ nó góp màu, như in offset. `kdn` vì đã có bút đỏ và xanh, ít đổi bút nhất; ảnh Reze boost 0,5: đen 66 % → 34 % lượng mực | ✅ test · ⏳ in giấy |
| P45 | **Chỉnh giao diện theo số đo WCAG** (22/11/2026, báo cáo DeepSeek, chủ dự án duyệt): viền và nền khối rõ hơn, thêm `--border-control` (viền ô nhập ≥ 3:1), chữ tối thiểu 12 px, tiêu đề khối gọn, header điện thoại thấp hơn. Chỉ đổi CSS, màu ở `tokens.css` | số đo cho thấy viền và chữ nhỏ khó đọc; đảo ngược dễ; không thêm thư viện (demo offline) | ✅ đo lại · ⏳ chủ dự án xem bằng mắt |
| P46 | **Chủ thể Tự động (GrabCut) và Vẽ tay** (đa giác tô thêm / tô bớt / hoàn tác, gửi `subject_poly`) | chủ dự án: "bỏ vẽ nền ít thôi chứ vẽ toàn đen ngốn thời gian"; elip / chữ nhật không ôm tóc, tay; GrabCut nhẹ (0,5–1,5 s, không thêm thư viện), vẽ tay để chỉnh khi máy tách lệch | ✅ test + chuột thật · ⏳ in giấy · ⏳ đo MiniPC |
| P47 | **Tab Beta in trang PDF** (22/11/2026, chủ dự án: "bung hết cỡ", "để riêng để dễ xóa sửa gộp"): đọc chữ thật trong PDF (PyMuPDF), **viết lại bằng font Hershey nét đơn**, mặc định **chữ viết tay nối nét** (`script`; chữ HOA và SỐ kiểu in), dấu tiếng Việt tự ghép; khung bảng vẽ từ vector; hình vẽ nét lấy đường giữa, ảnh chụp đi đường tô ảnh. Tách riêng để gỡ ([12](12_TAB_BETA_PDF.md) mục 10) | kết xuất ảnh rồi skeleton làm chữ 14 pt đứt nét, mất dấu; nét đơn đọc rõ và ít nét. Chủ dự án chỉ cần đọc được, muốn chữ nối như viết tay, nét đều, chỉ khác cỡ. PyMuPDF AGPL: ổn cho nghiên cứu, gói gọn trong `reader.py` | ✅ test + trình duyệt + PDF thật 32 trang · ⏳ in giấy · ⏳ đo MiniPC |
| P14 | **Preset**: **Chân dung** = sóng biến thiên 135°, không viền, mức đen 20, tương phản 1,5, CLAHE, làm nét 1,5, phủ đều · **Hình vẽ 2D** = gạch chéo 5 mức + lớp viền + khử nhiễu, tương phản 1,5, CLAHE, làm nét 1,5 · **Phong cảnh** = sóng 30°, tương phản 1,4, mức đen 15, làm nét 1,5, không CLAHE, không viền · **Schematic** = Nét viền FDoG chi tiết Nhiều, đen 60 / trắng 200 · **Siêu chi tiết** = Gạch chéo + Bỏ giới hạn + sửa sai 2 | chủ dự án: tiền xử lý không đặc thù thì tự chỉnh. Chân dung không viền vì viền bắt vệt bóng mềm thành nét cứng; ảnh hoạt hình gạch chéo + viền đẹp nhất | ✅ bản thảo · ⏳ in thật |
| P25 | **Gọn giao diện**: ẩn kiểu phụ (`spec.UI_STYLES`, test kiểm khớp `index.html`); Cài đặt → Tờ thử gộp còn tờ nhấc bút, **Thang tông** (16 ô), bài thử máy 7.2 và 7.5 | chủ dự án: gia tốc, tốc độ, G2 đã chốt, giữ tuổi thọ linh kiện | ✅ |
| P7 | Nhiều màu 2–4: k-means trên Lab có nhấn sắc độ; mỗi màu một tệp G-code | để thử; đổi bút giữa các tệp | ✅ |
| P8 | Trình duyệt thu nhỏ ảnh và xem trước độ sáng; máy chủ luôn tự làm được và kiểm lại | gửi nhẹ; không tin dữ liệu từ trình duyệt | ✅ |
| P9 | Không có nút "Tạo nháp", "Tạo G-code"; nạp ảnh chỉ hiện ảnh xám, bấm **"Tạo nét"** mới tạo nét (khách thấy "Gửi ảnh") | cắt / chỉnh tông xong mới tốn máy chủ | ✅ |
| P10 | Cắt ảnh ngay trên web, gửi tỷ lệ vùng cắt cho máy chủ | tiện hơn chỉnh ảnh trước khi gửi | ✅ |
| P12 | Tờ mẫu hiệu chỉnh bút do máy chủ tạo thành bản thảo thường | đi cùng đường xem trước | ✅ |
| O3 | Không viết lại tô nét / skeleton bằng JS | không nhanh hơn, thêm lỗi | ✅ |

## 4. Dữ liệu
| # | Quyết định | Vì sao | |
|---|---|---|---|
| S1 | Một thư mục dữ liệu `data/`, ba thư mục con cố định; **không có ô nhập đường dẫn** trên giao diện | người lạ không trỏ được máy chủ ghi ra chỗ khác | ✅ |
| S2 | Macro lưu ở máy chủ | mọi trình duyệt thấy cùng bộ, sao lưu cùng dữ liệu | ✅ |
| S3 | Xem thư mục dữ liệu qua giao diện, chỉ đọc + tải về | MiniPC không màn hình | ✅ |
| S4 | Tệp nhanh = bản thảo đã ghim | | ✅ |
| S10 | **Số liệu chạy máy** ghi ra `data/job_logs/*.csv` (tốc độ thật, hàng đợi `Bf:`, Z), giữ 30 lần / 150 MB; lỗi đĩa chỉ tắt nhật ký. Biểu đồ tự vẽ bằng canvas trong Khung nhìn 2D | cần số đo thật để quyết định baud, hệ số ước tính; không thư viện ngoài (demo offline) | ✅ máy giả · ⏳ máy thật (`$10=3`) |
| S5 | Không ghi nhật ký hệ thống ra tệp | log dài, khó đọc; điểm dừng + sao lưu đã đủ phục hồi | ✅ |
| S6 | Nhập G-code có sẵn = một tệp một bản thảo, qua cùng bộ làm sạch | chạy lại, ghim tệp từ phần mềm khác | ✅ |
| S8 | `data/` nằm ở gốc dự án | cập nhật chỉ thay `backend/` + `frontend/` | ✅ |
| S9 | Ảnh gốc không ghi ra đĩa. **Ngoại lệ:** ảnh khách tự bấm "Gửi ảnh" lưu ở `data/customer/` (đã thu nhỏ), tự xóa sau 5 ngày (chỉnh 3–5); bản thảo giữ như cũ | riêng tư, đỡ dung lượng; quản lý cần ảnh khách để tạo nét sau | ✅ · ✅ ảnh khách (máy giả, 09/11/2026) |

## 5. Triển khai
| # | Quyết định | Vì sao | |
|---|---|---|---|
| O4 | Bản mang đi Windows = Python embeddable + launcher; một icon bật, tự tắt sau 10 phút không có trang | bạn bè chạy được không cần cài Python; không phải nhớ tắt | ✅ |
| O5 | Cập nhật = zip chỉ mã (~0,3 MB) + `Cap nhat.bat` giữ `Python/` và `data/` | khỏi gửi lại ~450 MB | ✅ |
| O1 | MiniPC chạy cả máy chủ và giao diện; một địa chỉ qua Cloudflare Tunnel; không dùng host chia sẻ | host chỉ chứa tệp tĩnh, không giảm tải; cổng USB phải ở MiniPC | ⏳ |
| O6 | MiniPC chạy bằng Docker (venv + systemd dự phòng); IP cố định bằng giữ chỗ DHCP | image gói sẵn thư viện hệ thống; không lộ IP nhà | ⏳ |
| O7 | Quản lý dùng tab vẽ như hiện tại (việc mới hủy việc cũ), một việc tạo nét một lúc. Tách "nạp ảnh" và "tạo nét" bằng nút (P9) | chỉ một người tạo nét | ✅ · ✅ nút Tạo nét |
| O9 | **Người ở xa (khác mạng) vẫn vào web và điều khiển được** qua Cloudflare Tunnel, phải đăng nhập PIN quản lý (chưa đăng nhập thì chỉ xem / gửi ảnh). Mạng nội bộ là đường tạm khi chưa cài Cloudflare, sau giữ làm dự phòng (chủ dự án, 22/11/2026). Dừng khẩn thật = **nút cứng** | cần demo cho người ở xa, laptop khác mạng vẫn điều khiển được; PIN + chặn mặc định (O2) là lớp bảo vệ; nút cứng không phụ thuộc mạng / trình duyệt / backend | ⏳ |
| O8 | Demo **không cần Internet**: giao diện không tải gì từ ngoài; tự phát Wi-Fi | buổi trình diễn có thể không có mạng | ✅ |

## 6. Giao diện và tài liệu
| # | Quyết định | Vì sao | |
|---|---|---|---|
| B1 | Terminal giữ tiếng Anh | dễ tra mã lỗi | ✅ |
| B2 | Lỗi / alarm dịch theo mã; Alarm không mã hiện "Alarm (chưa rõ mã)" | | ✅ |
| B5 | Tên VMU PlotterPen; màu chỉ sửa ở `tokens.css`; `polish.css` nạp sau cùng | một nơi đổi màu, dễ hoàn nguyên | ✅ |
| X1 | Tài liệu đánh số 01–12 cho người đọc (từ nhỏ đến lớn), tệp `AI_*` cho AI; bản đồ mã sinh tự động | đỡ phân cấp; người không học code đọc được; AI khỏi quét cả kho | ✅ |
