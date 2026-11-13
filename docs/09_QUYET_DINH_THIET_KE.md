# 09 — Quyết định thiết kế: chọn gì, vì sao

> Dành cho người đọc và người viết báo cáo (phần "lý do lựa chọn"). Mỗi dòng: quyết định, lý do, mức chắc chắn.
> Ký hiệu: ✅ đã làm và kiểm (máy thật hoặc test tự động) · 🧪 làm rồi, chưa kiểm trên giấy / môi trường thật · ⏳ đã quyết, chưa làm.
> Trước khi đổi một hành vi trong bảng này, đọc lý do của nó. Mã số (A1, C4…) giữ nguyên để tra lại lịch sử Git.

## 1. Kiến trúc
| # | Quyết định | Vì sao | |
|---|---|---|---|
| A1 | Máy chủ Python (FastAPI) + giao diện JavaScript thuần | xử lý ảnh hợp Python (OpenCV, scikit-image, vpype); JS thuần không cần bước build, dễ giao cho người khác | ✅ |
| A2 | Giao diện chỉ hiển thị, máy chủ là nguồn sự thật; **giao diện không chạm cổng serial** | tránh đoán sai trạng thái; mọi lệnh được kiểm ở một chỗ | ✅ |
| A3 | Không framework, không bước build | đơn giản, chạy được trên máy yếu, ít phụ thuộc | ✅ |
| A4 | Hai đường nối máy: máy thật (SerialLink) và máy giả (SimLink, bắt chước theo log board thật) | phát triển và test khi chưa có máy | ✅ |
| A5 | Chỉ `api.js` gọi mạng, chỉ `state.js` thăm dò; một phần tử HTML chỉ một tệp ghi | một nơi để sửa, không giật | ✅ |
| A6 | Giao tiếp (09/11/2026): **lệnh** giữ HTTP POST; **trạng thái + terminal** sẽ đổi từ hỏi lặp sang **SSE** (đẩy một chiều) khi lên Cloudflare; **không dùng WebSocket** | trên cùng máy / mạng nội bộ hỏi lặp đã đủ (trễ chủ yếu do backend hỏi `?` 10 lần/s, không do HTTP). Qua Internet mỗi lần hỏi tốn một vòng đi–về → SSE nhanh gần gấp đôi, mượt hơn. SSE chạy trên HTTP, tự nối lại, dùng được cookie PIN; WebSocket phải tự lo nối lại, kiểm Origin, nối luồng với async → dễ lỗi mà lệnh chỉ nhanh thêm 1–2 ms | ✅ SSE (máy giả, 09/11/2026) · ⏳ qua Cloudflare thật |
| A7 | Mỗi tab một tệp view. Bỏ tab Công việc (gộp vào Điều khiển). **Bỏ thẻ SD / Flash** | thực tế chỉ stream từ máy tính; MKS đọc thẻ dễ lỗi | ✅ |
| P1 | Mọi tham số vẽ khai báo **một chỗ** (`spec.py`), giao diện lấy qua `/api/draw/schema` | không rải số cứng; đổi một dòng | ✅ |
| P2 | Tab vẽ **không bao giờ gọi máy**; hai tab chỉ nối qua bản thảo. ~~Chạy phải qua xem trước + xác nhận~~ → **bỏ từ 12/11/2026 (xem C9)** | an toàn | ✅ |

## 2. Điều khiển máy và an toàn
| # | Quyết định | Vì sao | |
|---|---|---|---|
| C1 | Jog, bút, Zero chỉ khi Idle; Home khi Idle / Alarm | an toàn | ✅ |
| C2 | Jog dùng `$J=…` | chạy được khi chưa Home, hủy được ngay | ✅ |
| C3 | Zero dùng `G10 L20 P1` | chuẩn FluidNC | ✅ |
| C4 | Bút 3 nấc **Z3 / Z1,5 / Z0** (03/11/2026, trước là Z5 / Z2,5). **Đã tách (09/11/2026):** điều khiển tay (nút Bút lên, Home, hủy, jog) nhấc **Z5**; chỉ G-code sinh ra nhấc thấp (mặc định Z3, chỉnh 2 / 1,5). Khung 2D coi bút xuống khi Z ≤ Z xuống + 0,5 mm (không dựa vào Z lên) | nhấc 3 mm đủ khỏi giấy, nhanh hơn; điều khiển tay hiếm khi cần nhanh nên nhấc cao cho chắc | 🧪 chưa thử lâu trên giấy cong · ✅ tách (máy giả) |
| C5 | Gốc (0,0) trên trái, Y xuống; không lật khung 2D, không đảo trục Y | ✅ chủ dự án xác nhận hướng trục đúng 05/11/2026 | ✅ |
| C6 | Nút Tạm dừng chỉ cho tác vụ; nút Hủy jog riêng | đúng bản chất firmware (Hold hủy jog, không resume được) | ✅ |
| C7 | Cấu hình máy một panel: "Máy" (YAML trên mạch: Áp dụng vào RAM, Lưu vào mạch sau khi sao lưu) và "App" (hồ sơ phần mềm). Không cho sửa chân GPIO, kinematics | chỉnh thông số không cần WebUI / Wi-Fi | ✅ |
| C8 | **Home tự nâng bút trước** (03/11/2026) | bút hạ bằng trọng lực, quên nâng thì kéo vệt chéo qua giấy | ✅ |
| C9 | **Bỏ bước bắt buộc "Xem trước" + ô tích "Tôi đã xem trước đường chạy và vùng vẽ"** trước nút ▶ Chạy (12/11/2026, chủ dự án yêu cầu). Nạp tệp là khung 2D hiện ngay đường chạy + vùng làm việc. Nút Chạy vẫn cần: máy nối và dữ liệu mới, đã mở khóa chuyển động, máy Idle, tệp không có dòng bị cấm / ngoài hành trình. Là một công tắc `REQUIRE_PREVIEW_CONFIRM` ở đầu `views/control.js` (đổi `true` là có lại nút + ô tích, đổi tệp lại phải làm lại) | xem trước phát lại chậm, người vận hành đã nhìn khung vẽ ngay khi nạp; việc chống chạy nhầm do khóa chuyển động (mặc định chỉ đọc, tự khóa sau 15 phút) và Idle đảm nhận. Chỉ chặn ở giao diện, máy chủ chưa từng kiểm "đã xem trước" | ✅ (ẩn) · ⏳ chủ dự án dùng thử |
| C10 | **Chờ sau nâng / hạ bút mặc định 0** (13/11/2026; trước 0,02 từ 12/11, 0,05 từ 03/11). Ô chờ vẫn còn, gõ số khác được | tờ nhấc bút 13/11 (Z3, hạ 2000, Sakura): hàng **chờ 0** nét đủ, đầu nét không hụt, không kéo vệt; Biểu đồ: hàng đợi trong máy **đầy suốt** (không G4 thì máy không phải xả hàng đợi). Hàng **chờ 0,02**: hàng đợi tụt về 0 ở mỗi lần nhấc, chậm hơn ~0,08 s mỗi lần (~6,3 s so với ~8 s cho 20 gạch, đọc trên biểu đồ). Chủ dự án: còn chỉnh vị trí kẹp bút cho chắc. `spec.py` `delay_up_s` / `delay_down_s`, `index.html` ô `pen-delay-*` | ✅ |
| D4 | Hủy 3 chế độ: `soft` (mặc định: chạy hết bộ đệm, nâng bút), `hard` (Hold → Reset → `$X` → nâng bút), `reset`. Chỉ báo "đã nâng bút" khi báo cáo xác nhận Z | giữ được Home khi có thể; không báo an toàn giả | ✅ |
| D10 | Gửi từng dòng, chờ `ok` (**giữ**, 13/11/2026) | FluidNC trả `ok` khi dòng vào hàng đợi; thử 1500 dòng ở F3000 không giật. **Đo 13/11 (tờ 7.6):** cách này chỉ đạt **~125 dòng/giây** (~8 ms một lượt gửi + chờ, phần truyền chữ ở 115200 chỉ ~2 ms), nên chuỗi dài đoạn < ~1 mm ở 8000 bị chậm (vòng 754 mm bằng đoạn 0,1 mm: 60,7 s thay vì 5,7 s). Nhưng **mô phỏng trên bản vẽ thật** (ảnh mẫu A5, mọi kiểu tô, khớp số đo 7.6 trong 4 %) cho thấy chậm thêm **~0 %**: nét đã rút gọn, đoạn ngắn đi từng cụm xen nét dài, bộ đệm 15 khối của máy nạp lại kịp. Vì vậy **không làm "gửi dồn" (đếm ký tự)**: lợi gần như không có, mà phần dừng / lỗi / tiếp tục từ điểm dừng phức tạp hơn. Xem lại nếu sau này có kiểu tô hay ảnh nhập toàn đoạn rất ngắn (ước tính đã tính giới hạn này, D12) | ✅ |
| D11 | Giữ **115200 baud** (**chốt**, 13/11/2026) | đo 13/11: chỗ chậm là thời gian chờ `ok`, không phải tốc độ dây; tăng baud chỉ bớt phần ~2 ms truyền chữ trong ~8 ms mỗi dòng, mà phải đổi cả YAML lẫn app (đặt sai khi Wi-Fi mạch tắt thì khó nối lại) | ✅ |
| D12 | **Gộp nét thành cung G2/G3 + đoạn G1 dài** khi sinh G-code (13/11/2026, chủ dự án chọn sau tờ 7.6) | tờ 7.6: vòng tròn bằng **G2 chạy 5,7 s, đủ tốc, hàng đợi đầy**; cùng vòng bằng G1 đoạn 1 / 0,5 / 0,25 / 0,1 mm: 6,0 / 11,6 / 23,3 / 60,7 s; trên giấy không khác nhau. `drawing/arcs.py`: sai lệch ≤ 0,02 mm so với nét gốc, bán kính 0,2–2000 mm, không quá 300° một lệnh, chỉ khi tọa độ ≥ 3 chữ số lẻ; tính trên tọa độ máy (đảo Y đổi G2 ↔ G3). Ảnh mẫu A5: bớt 6–25 % số dòng (sóng biên độ 0 %: dạng sin không khớp cung); thời gian gần như không đổi (vì D10). Tắt bằng `USE_ARCS = False` ở `drawing/gcode.py` nếu máy báo lỗi với G2/G3 | ✅ máy giả · ⏳ in thật |
| M6 | Sau `$X` máy chạy được G-code kể cả chưa Home → giao diện cảnh báo | sự thật firmware | ✅ |
| S7 | Bộ làm sạch G-code chặn `$…`, ký tự tức thời, `G10 G28 G30 G38 G53 G55–G59 G92`; báo một lần tối đa 5 dòng kèm số dòng. Giao diện giữ cùng danh sách | các lệnh đó đổi gốc / hệ tọa độ → bản vẽ lệch khỏi giấy; danh sách ngắn để tệp thường không bị từ chối oan | ✅ |
| P11 | Tiếp tục từ điểm dừng: lùi 64 dòng rồi lùi tới đầu nét gần nhất, dựng lại trạng thái, kiểm gốc Zero | `ok` chỉ là "đã vào hàng đợi"; vẽ chồng vô hại, bỏ sót thì mất nét | ✅ máy giả · 🧪 máy thật |
| O2 | Hai vai trò khách / quản lý bằng PIN; máy chủ **chặn mặc định**; vẫn giữ lớp mở khóa chuyển động (**không đặt PIN** cho lớp này, PIN chỉ dùng để đăng nhập, 09/11/2026) | đề tài cấp trường: khách chỉ xem / gửi ảnh, không cần tài khoản, hàng chờ | ✅ (gửi ảnh ✅ 09/11/2026) |

## 3. Tạo bản vẽ và xử lý ảnh
| # | Quyết định | Vì sao | |
|---|---|---|---|
| P3 | Ảnh → nét chạy ở **tiến trình con ưu tiên thấp**; hủy = kết thúc tiến trình; trần 600 s, 4 GB (Linux) | MiniPC yếu vừa điều khiển vừa xử lý; ảnh lạ không làm sập server | ✅ (RAM trên Ubuntu 🧪) |
| P4 | Thứ tự: EXIF → cắt → thu nhỏ → lọc sắc độ → tạo nét | chi phí tỷ lệ số điểm ảnh; làm nét trước khi thu nhỏ là mất | ✅ |
| P5 | Cỡ làm việc = khung ÷ bút × 1,3 (400–4000 điểm); ảnh nhỏ chỉ phóng tới 720; kéo khung lệch > 12 % thì tạo lại nét | khoảng cách nét đúng theo mm thật; thêm điểm ảnh không thêm chi tiết | ✅ |
| P6 | Kiểu tô: zigzag (mặc định, 45°), sóng, xoắn ốc, viền; thêm lớp viền tùy chọn | ít nhấc bút; không vượt 200 000 dòng | ✅ |
| P15 | **Mỗi mức đậm nhạt = một dải, một lượt gạch, khoảng cách riêng** (`level_plan`: độ phủ 0 → 90 % chia đều, s = nét thật ÷ độ phủ; nét thật = 1,375 × cỡ bút). 5 mức mặc định | mô phỏng: sai số 0,174 → 0,071, nét ngắn hơn 45 % so với chồng lớp | ✅ mô phỏng · 🧪 in giấy |
| P16 | Zigzag / sóng quay đầu bằng **nửa vòng tròn** | góc vuông ép máy ~7 mm/s, mực đọng thành giọt | 🧪 |
| P17 | **Vẽ lần lượt từng mức đậm nhạt** (nhạt → đậm, viền cuối), mỗi mức sắp xếp riêng; tắt được (`optimize.group_levels`, mặc định bật 09/11/2026 → **tắt từ 12/11/2026**: in thật thấy nhấc bút nhiều, lâu hơn) | thứ tự cũ (sắp xếp chung) cho quãng bay ngắn nhất nhưng bút nhảy qua lại giữa các mảng và để sót nét lẻ phải bay về cuối; chủ dự án muốn thứ tự gọn. Giá: quãng bay ≈ ×3 (≈ +20–30 s). Mực ướt / khô: chưa kiểm | ✅ máy giả · 🧪 in giấy |
| P18 | **Nối nét gần** thay vì nhấc bút (`optimize.bridge`, mặc định bật, 12/11/2026): đầu nét sau ≤ 4 × bề rộng nét và đoạn nối nằm trong vùng đậm ≥ 0,2 | in thật: phần lớn thời gian là nhấc bút, 55–80 % lần nhấc chỉ bay ≤ 2–3 mm. Ảnh mẫu A5: bớt 55–82 % lần nhấc, nhanh 30–50 %, mực +3 %. Không dùng cho viền / nhiều màu (đoạn nối sẽ kẻ ngang mép / lấn màu) | ✅ mô phỏng · 🧪 in giấy |
| P19 | **Ước tính thời gian có gia tốc** (hình thang, junction 0,05, gia tốc 3000); backend và `lib/gcode.js` cùng công thức. Từ 13/11/2026: + 0,025 s mỗi lần nhấc, + 0,025 s mỗi G4, giới hạn 125 dòng/giây (trước: + 0,15 s mỗi lần nhấc). **Số lần nhấc bút trong Biểu đồ đếm theo Z** (trước đếm G0, ra 0 khi di chuyển bằng G1) | cách cũ (quãng ÷ tốc độ) ngắn hơn thật 1,7–1,9 lần (12/11). Đo 13/11: tờ 7.6 ước 110,9 / thật 111 s; A4 mèo theo dáng thật ÷ ước = 0,87, A4 em bé đan chéo 0,94 | ✅ |
| P20 | **Khung xem trước vẽ theo lớp, lưu sẵn** (`preview.js`): lớp nền (vùng, lưới, đường của tệp), lớp phần đã vẽ xong, lớp phát lại nằm trong canvas ẩn; mỗi lần có vị trí máy chỉ dán lại + vẽ thêm đoạn mới + vài nét động | vẽ lại cả tệp 10 lần/giây làm tab Điều khiển đơ trên laptop yếu khi chạy tác vụ (12/11/2026). Kéo / thu phóng vẫn vẽ lại lớp nền | ✅ test hàm thuần · ⏳ đo trên máy yếu |
| P13 | Viền: top-hat (nét mực ≤ 4 mm → đường giữa) + Canny trên ảnh làm phẳng màu (mean shift, kênh a / b Lab) + vòng viền chấm + nối khe ≤ 1,5 mm + cắt râu theo bề dày nét + khép vòng. Thay DoG cũ | DoG cho hai đường song song ở nét dày, mất viền mảng không có nét đen | ✅ ảnh mẫu · 🧪 in giấy |
| P7 | Nhiều màu 2–4: k-means trên Lab có nhấn sắc độ; mỗi màu một tệp G-code, tên có mã màu | để thử; đổi bút giữa các tệp | ✅ |
| P8 | Trình duyệt thu nhỏ ảnh và xem trước độ sáng; máy chủ luôn tự làm được và kiểm lại | gửi nhẹ; không tin dữ liệu từ trình duyệt | ✅ |
| P9 | Bỏ nút "Tạo nháp", "Tạo G-code"; G-code tự tính lại. **Đổi 09/11/2026:** nạp ảnh chỉ hiện ảnh xám, bấm **"Tạo nét"** mới tạo nét (khách thấy nút "Gửi ảnh" thay vào) | bản nháp không nhanh hơn đáng kể; cắt / chỉnh tông xong mới tốn máy chủ, MiniPC không chạy nét cho lần chỉnh dở | ✅ bỏ nút nháp · ✅ nút Tạo nét (09/11/2026; SVG vẫn tạo ngay) |
| P10 | Cắt ảnh ngay trên web, gửi tỷ lệ vùng cắt cho máy chủ | tiện hơn chỉnh ảnh trước khi gửi | ✅ |
| P12 | Tờ mẫu hiệu chỉnh bút do máy chủ tạo thành bản thảo thường (nút đã bỏ, route còn) | đi cùng đường xem trước / xác nhận | ✅ |
| P14 | 5 preset: Chân dung, Phong cảnh, Cận cảnh, Ảnh 2D, Schematic. **Không thêm kiểu tô mới** trừ khi khác hẳn và đẹp hơn | tập trung chất lượng; stipple / TSP đã bỏ | ✅ · 🧪 in giấy |
| O3 | Không viết lại tô nét / skeleton bằng JS | không nhanh hơn, thêm lỗi | ✅ |

## 4. Dữ liệu
| # | Quyết định | Vì sao | |
|---|---|---|---|
| S1 | Một thư mục dữ liệu `data/`, ba thư mục con cố định; **không có ô nhập đường dẫn** trên giao diện | người lạ không trỏ được máy chủ ghi ra chỗ khác | ✅ |
| S2 | Macro lưu ở máy chủ | mọi trình duyệt thấy cùng bộ, sao lưu cùng dữ liệu | ✅ |
| S3 | Xem thư mục dữ liệu qua giao diện, chỉ đọc + tải về | MiniPC không màn hình | ✅ |
| S4 | Tệp nhanh = bản thảo đã ghim | | ✅ |
| S10 | **Số liệu chạy máy** ghi ra `data/job_logs/*.csv` (tốc độ thật, hàng đợi `Bf:`, Z, dòng đã nhận), giữ 30 lần / 150 MB; ghi trong luồng đọc serial nhưng mọi lỗi đĩa chỉ tắt nhật ký đó. Biểu đồ tự vẽ bằng canvas, nằm trong Khung nhìn 2D (nút chuyển) | tab Công việc đã bỏ; cần số đo thật để quyết định baud, hệ số ước tính, so sánh thông số; không thư viện ngoài vì demo không có Internet | ✅ máy giả · ⏳ máy thật (`$10=3`) |
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
| O9 | **Người điều khiển vào thẳng địa chỉ mạng nội bộ** (cùng Wi-Fi / hotspot với MiniPC), không qua Cloudflare; người xem từ xa qua Cloudflare (trễ ~30–150 ms, bù bằng vệt bút nội suy theo G-code). Dừng khẩn thật = **nút cứng** | lệnh không phải ra Internet rồi quay về; mất mạng ngoài vẫn điều khiển được; nút cứng không phụ thuộc mạng / trình duyệt / backend | ⏳ |
| O8 | Demo **không cần Internet**: giao diện không tải gì từ ngoài; tự phát Wi-Fi | buổi trình diễn có thể không có mạng | ✅ |

## 6. Giao diện và tài liệu
| # | Quyết định | Vì sao | |
|---|---|---|---|
| B1 | Terminal giữ tiếng Anh | dễ tra mã lỗi | ✅ |
| B2 | Lỗi / alarm dịch theo mã; Alarm không mã hiện "Alarm (chưa rõ mã)" | | ✅ |
| B5 | Tên VMU PlotterPen; màu chỉ sửa ở `tokens.css`; `polish.css` nạp sau cùng | một nơi đổi màu, dễ hoàn nguyên | ✅ |
| X1 | Tài liệu đánh số 01–11 cho người đọc (từ nhỏ đến lớn), tệp `AI_*` cho AI; bản đồ mã sinh tự động | đỡ phân cấp; người không học code đọc được; AI khỏi quét cả kho | ✅ |
