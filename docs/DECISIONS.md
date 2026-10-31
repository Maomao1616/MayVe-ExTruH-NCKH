# VMU PlotterPen (ExtruXY) – Sổ quyết định (Cập nhật 31/10/2026)

**Chọn gì – vì sao / đổi ở đâu – mức chắc.** ⚠ = giả định, **chưa kiểm chứng**. ✅ = đã làm và kiểm (máy thật không motor hoặc test tự động). ⏳ = đã quyết, chưa làm. ❌ = đã bỏ. Tình trạng chi tiết: `STATUS.md`.

## Kiến trúc và Quy tắc code
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| A1 | Backend Python + Frontend JS thuần | Xử lý ảnh hợp Python, dễ giao AI | ✅ |
| A2 | Frontend chỉ hiển thị, backend là nguồn sự thật | Tránh đoán sai trạng thái | ✅ |
| A3 | Không framework, không build | Đơn giản, dễ bảo trì | ✅ |
| A4 | SimLink và SerialLink. Máy thật **mặc định chỉ đọc** | An toàn | ✅ |
| A5 | Chỉ `api.js` gọi mạng, chỉ `state.js` thăm dò | Một nơi để sửa | ✅ |
| A6 | Một phần tử HTML một chủ ghi | Tránh giật, xung đột | ✅ |
| A7 | Mỗi tab một file view. **Bỏ tab Jobs**, gộp vào Control. **Bỏ hoàn toàn SD/Flash**. | Tinh gọn theo thực tế sử dụng | ✅ |

## Điều khiển máy & An toàn
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| C1 | Jog, XY 0, bút, Zero mở khi `Idle`; Home khi `Idle`/`Alarm` | An toàn | ✅ |
| C2 | Jog dùng `$J=...` | Chạy được khi chưa Home | ✅ |
| C3 | Zero dùng `G10 L20 P1 ...` | Chuẩn FluidNC | ✅ |
| C4 | Bút 3 nấc: Z5 lên, Z2.5 giữa, Z0 xuống (sửa được ở Cài đặt → Cấu hình máy, mục App) | Khớp WebUI FluidNC, đã thử thanh bút trên máy thật | ✅ |
| C7 | **Cấu hình máy một panel**: mục "Máy" (YAML trên mạch) Áp dụng = `$/axes/...` vào RAM, Lưu vào mạch = `$CD=/localfs/<tệp>` sau khi sao lưu bản gốc về máy tính; mục "App" lưu ở `data/profile.json`. Không cho sửa chân GPIO, kinematics, stepping | Chỉnh thông số không cần WiFi/WebUI; đã thử đọc, áp dụng, lưu, khởi động lại (MACHINE A11) | ✅ |
| C5 | Gốc (0,0) trên trái. X+ đi trái, Y+ đi xuống (Khớp WebUI) | `VIEW.flipX/Y = false` | ✅ |
| C6 | Nút Tạm dừng (Header) chỉ dùng cho Run. Nút Hủy Jog riêng cho Jog. | Đúng bản chất firmware | ✅ |
| D4 | **Hủy tác vụ 3 chế độ**: `reset` (cũ), `soft` (chạy nốt buffer 60s + nâng bút), `hard` (Hold -> Reset -> $X nếu Alarm -> nâng bút, chỉ báo xong khi Z thật tới đích). Mặc định UI dùng `soft`, fallback sang `hard` nếu lỗi. | An toàn, giữ được Home nếu có thể; đã thử trên máy thật (MACHINE A10) | ✅ |
| D9 | **Bỏ hoàn toàn thẻ SD / Flash**. Chỉ streaming từ máy tính. | MKS quá tải, dễ lỗi. Chờ mini PC i5. | ✅ |
| D10 | Streaming gửi từng dòng chờ ok. Test 1500 dòng @ F3000 không nhảy Run/Idle. | Ổn định | ✅ |
| M6 | Boot lên Alarm do must_home. Sau `$X`, G-code chạy được kể cả chưa Home. UI phải cảnh báo. | Sự thật firmware | ✅ |

## Hiển thị và Trải nghiệm
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| B1 | Terminal giữ tiếng Anh nguyên gốc, không i18n | Dễ tra mã lỗi | ✅ |
| B2 | Lỗi/alarm firmware dịch theo `.code`. Nếu Alarm không có mã (từ boot) hiển thị "Alarm (chưa rõ mã)". | Tránh hiển thị "—" gây nhầm lẫn | ✅ |
| B3 | Dòng trạng thái terminal in 1s/lần, chỉ khi có thay đổi | Tránh ngập log | ✅ |
| B4 | Log cũ (`last_error`, `last_alarm`) giữ nguyên sau Reset | Giúp user trace lỗi lịch sử | ✅ |

## Tạo bản vẽ và xử lý ảnh
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| P1 | Mọi tham số vẽ khai báo MỘT chỗ (`spec.py`), frontend lấy qua `/api/draw/schema` | Không rải số cứng; đổi một dòng | ✅ |
| P2 | Tab vẽ **không bao giờ gọi máy**; chỉ ghi bản thảo; Hàng đợi = danh sách bản thảo; chạy phải qua xem trước + xác nhận ở Điều khiển | An toàn | ✅ |
| P3 | Ảnh → nét chạy ở **tiến trình riêng, ưu tiên thấp** (`isolated.py`); hủy = kết thúc tiến trình; trần thời gian 600 s, RAM 4 GB (Linux) | MiniPC yếu vừa điều khiển vừa xử lý ảnh; ảnh lạ không làm sập server | ✅ (RAM trên Ubuntu ⚠) |
| P4 | Thứ tự xử lý ảnh: EXIF → cắt → thu nhỏ → lọc sắc độ → bắt nét/tô. Lọc **sau** thu nhỏ | Chi phí tỉ lệ số điểm ảnh; làm nét trước thu nhỏ bị mất | ✅ |
| P5 | Cỡ làm việc = khung thật ÷ bề rộng bút × 1,3, kẹp 400–4000 px; ảnh nhỏ chỉ phóng nhẹ tới 720 px; kéo khung lệch >12% thì tự tạo lại nét | Mật độ gạch đúng theo mm/bút ở kích thước thật; thêm điểm ảnh không thêm chi tiết | ✅ |
| P6 | Kiểu tô: zigzag (mặc định, góc 45°), sóng (bước sóng tự giãn theo ngân sách 100 000 điểm), xoắn ốc (nối khe trắng < 3 mm), viền (DoG + skeleton) + phủ viền | Ít nhấc bút; không vượt 200 000 dòng G-code | ✅ (ngưỡng viền, góc ⚠) |
| P7 | Đa màu 2–4: k-means trên Lab có nhấn sắc độ; mỗi màu một lớp **một tệp G-code**, id lớp `<số>-<mãmàu>`; đổi bút giữa các tệp | Chỉ để thử mô hình; tên tệp tự mang mã màu | ✅ |
| P8 | Trình duyệt thu nhỏ ảnh trước khi gửi và xem trước độ sáng ngay; **backend luôn tự làm được và kiểm lại** | Gửi nhẹ, MiniPC khỏi giải mã ảnh lớn; không tin dữ liệu từ trình duyệt | ✅ |
| P9 | Giao diện gọn: bỏ "Tạo nháp" và "Tạo G-code" (G-code tự tính lại); có "Tạo lại nét"; 3 preset (Chân dung, Phong cảnh, Mạch điện/Bản vẽ) | Bản nháp không nhanh hơn đáng kể; ít nút thừa | ✅ |
| P10 | **Cắt ảnh trên trình duyệt** (`views/drawing/crop.js`), gửi `crop_x/y/w/h` (tỷ lệ 0..1 của ảnh gốc) cho backend cắt; trình duyệt thu nhỏ cả ảnh theo hệ số mà VÙNG CẮT cần (`imageprep.uploadTarget`). Áp dụng = nạp lại như tệp mới. SVG không cắt | trước đây định bỏ ("chỉnh ảnh trước khi gửi"), người dùng đổi ý: cắt ngay trên web tiện hơn | ✅ |
| P11 | **Tiếp tục từ điểm dừng** (`services/resume.py`): khi hủy / lỗi / mất kết nối, lưu tệp G-code đã làm sạch + số dòng máy đã nhận vào `data/resume.json` (một chỗ, chạy trọn thì xóa). Bấm Tiếp tục: lùi 64 dòng, rồi lùi tiếp tới dòng gần nhất mà **bút đang nhấc**; dựng lại `G90 G21`, nâng bút, `G0` tới đầu nét, `G1 F...`. Từ chối nếu phần đã chạy dùng G91/G92/G10/G28/G30/G53/G55-59/M3/M4. Lưu WCO lúc dừng; đổi gốc Zero thì hỏi lại | `ok` chỉ là "đã vào hàng đợi", hủy cứng làm mất phần đang chờ; vẽ chồng một đoạn thì vô hại, bỏ sót thì mất nét | ✅ (máy giả) ⚠ máy thật |
| P12 | Tờ mẫu hiệu chỉnh bút tạo bằng **backend** (`drawing/calibration.py`) thành bản thảo thường; A5, tỷ lệ 1:1 | thử máy thật cần chữ F, thước 100 mm, dải tô nhiều khoảng cách; đi cùng đường xem trước/xác nhận như mọi bản vẽ | ✅ |
| S1 | **Một thư mục dữ liệu, ba thư mục con cố định** (`app/paths.py`): `drafts/`, `config_backups/`, `macros/` + tệp lẻ. Gốc = `data/`, đổi bằng `EXTRUXY_DATA_DIR`. **Không có ô nhập đường dẫn trên giao diện** (bản cũ có `draft_dir`, nay bị bỏ qua) | người lạ vào web không được trỏ máy chủ ghi ra chỗ khác; giải nén zip ở máy mới là chạy (thư mục tự tạo) | ✅ |
| S2 | **Macro lưu ở máy chủ** (`data/macros/<id>.json`, `services/macros.py`), trình duyệt giữ bản sao; macro cũ trong `localStorage` tự chuyển lên một lần | mọi trình duyệt thấy cùng bộ, xem được trong Lưu trữ, sao lưu cùng thư mục dữ liệu | ✅ |
| S3 | **Xem thư mục dữ liệu qua giao diện, chỉ đọc + tải về** (`GET /api/storage`, `/api/storage/file`; đường dẫn kiểm regex, tối đa 2 cấp, nằm trong thư mục con cố định) | MiniPC không màn hình để mở thư mục | ✅ |
| S4 | **Tệp nhanh (dock) = bản thảo đã ghim**; bấm là nạp sang Điều khiển (vẫn phải Xem trước + xác nhận) | ghim sẵn việc hay dùng thì dễ chọn hơn danh sách tệp | ✅ |
| S6 | **Nhập G-code có sẵn = một tệp một bản thảo** (`drawing/gcode_import.py`, nút "Lưu vào bản thảo" ở Điều khiển → `POST /api/draw/drafts/import-gcode`). Làm sạch bằng `clean_gcode`, ảnh minh họa và số liệu đọc từ G-code (cung G2/G3 chỉ vẽ thành đoạn thẳng trong ảnh, G-code lưu nguyên) | chạy lại, ghim, chạy nhanh tệp từ phần mềm khác mà không phải chọn lại | ✅ |
| S7 | **`clean_gcode` chặn thêm G10, G28, G30, G38, G53, G55–G59, G92** (tính phần nguyên: G28.1, G59.3…) ngoài `$` và ký tự realtime; đi hết tệp rồi báo một lần tối đa 5 dòng kèm số dòng gốc. `lib/gcode.js` giữ cùng danh sách (`BLOCKED_G`) để báo ngay lúc nạp và khóa nút Chạy. G54, G91, G20, M0, M3/M5, lệnh lạ: **không chặn**, chỉ lưu ý | các lệnh trên đổi gốc/hệ tọa độ hoặc chạy tới chỗ máy tự chọn → bản vẽ lệch khỏi giấy; danh sách ngắn để tệp thường không bị từ chối oan | ✅ |
| S8 | **Thư mục `data/` nằm ở gốc dự án** (cùng cấp `backend/`, `frontend/`; `paths.py` `parents[2]`), không còn trong `backend/` | cập nhật chỉ thay `backend/` + `frontend/` mà không đụng bản thảo | ✅ |
| P13 | **Nét viền mới** (`edges.py`): nét mực ≤ 4 mm và vạch sáng mảnh → đường giữa (top-hat), ranh giới mảng sáng tối + màu (Canny trên bilateral, kênh a/b Lab), chấm đậm → vòng, nối khe hở ≤ 1,5 mm; `style.outline_detail` low/medium/high. Bỏ DoG cũ (hai đường song song ở nét dày, mất viền mảng không có nét đen, đứt nét, ăn mép tối cạnh vạch sáng) | ảnh hoạt hình / sticker dán ảnh chụp của chủ dự án cần đi đủ viền từng khối | ✅ (ảnh mẫu) ⚠ in giấy |
| P14 | **5 preset**: Chân dung, Phong cảnh, Cận cảnh / Đồ vật, Ảnh 2D / Hình vẽ, Schematic (bỏ các bộ gần trùng thông số: đêm, hoàng hôn, sân khấu, truyện tranh; cách thử ở `KIEM_TRA_VE.md`). **Không thêm kiểu tô mới** (crosshatch ≈ zigzag nhiều mức; stipple/TSP đã bỏ; flow field / đồng mức để sau) | chủ dự án: chỉ thêm kiểu khi khác hẳn và đẹp hơn; tập trung vào viền | ✅ ⚠ in giấy |
| S5 | **Không ghi nhật ký hệ thống ra tệp**; terminal giữ log trong bộ nhớ | log dài, khó đọc lại; điểm dừng + bản sao lưu đã đủ để phục hồi | ❌ |

## Triển khai (theo `PLAN_ONLINE.md`)
| # | Quyết định | Vì sao | Chắc |
|---|---|---|---|
| O1 | MiniPC Ubuntu không màn hình chạy cả backend và giao diện; Python làm hết việc nặng; **không dùng host chia sẻ**, một địa chỉ qua Cloudflare Tunnel | Host chỉ chứa tệp tĩnh, không giảm tải, thêm CORS/cookie chéo tên miền; USB phải ở MiniPC | ⏳ |
| O2 | Khách (không đăng nhập) chỉ tải ảnh/dùng tab vẽ/lưu bản thảo; người vận hành nhập PIN ở Cài đặt mới dùng được phần còn lại; **backend chặn thật** | Ai biết địa chỉ cũng gửi được ảnh nhưng không điều khiển được máy | ⏳ |
| O4 | **Bản mang đi Windows** = Python 3.12 embeddable (`Python/`, `_pth` có `..\backend`) + `launcher/` (server chạy ẩn `--host 0.0.0.0`, tự đặt `EXTRUXY_ALLOWED_HOSTS` theo IP LAN). **Một icon bật, không có icon tắt**: server tự tắt sau 10 phút không có trang nào mở (`app/idle.py`, `EXTRUXY_IDLE_EXIT_MIN`), đang chạy G-code thì không tắt; trang ẩn vẫn gửi `/api/health` mỗi 30 s. Chi tiết `DONG_GOI.md` | bạn bè chạy được không cần cài Python; người dùng không phải nhớ tắt server | ✅ |
| O5 | **Cập nhật = zip chỉ `backend/`, `frontend/`, `launcher/`** (`tools/dong_goi.ps1`) + `Cap nhat.bat`: tắt server, thay mã (robocopy /MIR, bỏ qua `.venv`), giữ `Python/` + `data/`, cất bản cũ vào `_ban_cu/`, `requirements.txt` đổi thì `pip install` bằng pip trong `Python/` | lần sau chỉ gửi ~0,3 MB thay vì ~450 MB | ✅ |
| O6 | **MiniPC chạy bằng Docker** (đề xuất; venv + systemd là phương án dự phòng), không dùng `Python/` của Windows; IP cố định bằng giữ chỗ DHCP trên router; Cloudflare Tunnel thay cho mở cổng. Chi tiết `PLAN_ONLINE.md` 5c–5d | image gói sẵn thư viện hệ thống của OpenCV, cập nhật bằng build lại; không lộ IP nhà | ⏳ |
| O3 | JS chỉ nhận việc nhẹ khi kết quả giống và nhanh hơn/ngang Python; sắp xếp nét 2-opt trong Web Worker chỉ làm nếu đo trên MiniPC thấy cần | Không viết lại tô nét/skeleton bằng JS (không nhanh hơn, thêm lỗi) | ⏳ |

## Giao diện, tài liệu
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| B5 | Tên **VMU PlotterPen**; màu chỉ sửa ở `tokens.css` (`--highlight` cam nhấn, `--paper*` giấy/mực canvas theo theme); lớp `polish.css` nạp sau cùng, xóa dòng `<link>` là quay về như cũ | Một nơi đổi màu, dễ hoàn nguyên | ✅ |
| B6 | Bố cục tab Điều khiển: trạng thái một dòng ở hàng tiêu đề; cột trái 2/5 (tọa độ, jog, tệp), cột phải 3/5 (2D + tiến trình, terminal dài chạm hàng đợi); Hàng đợi rộng hết bề ngang | Dễ đọc; tiến trình nằm cạnh khung 2D | ✅ |
| X1 | Tài liệu có một cửa vào (`AI_START.md`), một nơi tình trạng (`STATUS.md`), bản đồ mã **sinh tự động** (`CODEMAP.md`) và công cụ xuất mã tiết kiệm token (`tools/export_context.py`) | Bàn giao cho AI khác mà không dán cả kho | ✅ |
