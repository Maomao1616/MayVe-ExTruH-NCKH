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
| A7 | Mỗi tab một tệp view. Bỏ tab Công việc (gộp vào Điều khiển). **Bỏ thẻ SD / Flash** | thực tế chỉ stream từ máy tính; MKS đọc thẻ dễ lỗi | ✅ |
| P1 | Mọi tham số vẽ khai báo **một chỗ** (`spec.py`), giao diện lấy qua `/api/draw/schema` | không rải số cứng; đổi một dòng | ✅ |
| P2 | Tab vẽ **không bao giờ gọi máy**; hai tab chỉ nối qua bản thảo; chạy phải qua xem trước + xác nhận | an toàn | ✅ |

## 2. Điều khiển máy và an toàn
| # | Quyết định | Vì sao | |
|---|---|---|---|
| C1 | Jog, bút, Zero chỉ khi Idle; Home khi Idle / Alarm | an toàn | ✅ |
| C2 | Jog dùng `$J=…` | chạy được khi chưa Home, hủy được ngay | ✅ |
| C3 | Zero dùng `G10 L20 P1` | chuẩn FluidNC | ✅ |
| C4 | Bút 3 nấc **Z3 / Z1,5 / Z0** (03/11/2026, trước là Z5 / Z2,5) | nhấc 3 mm đủ khỏi giấy, nhanh hơn | 🧪 chưa thử lâu trên giấy cong |
| C5 | Gốc (0,0) trên trái, Y xuống; không lật khung 2D, không đảo trục Y | ✅ chủ dự án xác nhận hướng trục đúng 05/11/2026 | ✅ |
| C6 | Nút Tạm dừng chỉ cho tác vụ; nút Hủy jog riêng | đúng bản chất firmware (Hold hủy jog, không resume được) | ✅ |
| C7 | Cấu hình máy một panel: "Máy" (YAML trên mạch: Áp dụng vào RAM, Lưu vào mạch sau khi sao lưu) và "App" (hồ sơ phần mềm). Không cho sửa chân GPIO, kinematics | chỉnh thông số không cần WebUI / Wi-Fi | ✅ |
| C8 | **Home tự nâng bút trước** (03/11/2026) | bút hạ bằng trọng lực, quên nâng thì kéo vệt chéo qua giấy | ✅ |
| D4 | Hủy 3 chế độ: `soft` (mặc định: chạy hết bộ đệm, nâng bút), `hard` (Hold → Reset → `$X` → nâng bút), `reset`. Chỉ báo "đã nâng bút" khi báo cáo xác nhận Z | giữ được Home khi có thể; không báo an toàn giả | ✅ |
| D10 | Gửi từng dòng, chờ `ok` | FluidNC trả `ok` khi dòng vào hàng đợi, nên hàng đợi luôn đầy; thử 1500 dòng ở F3000 không giật | ✅ |
| M6 | Sau `$X` máy chạy được G-code kể cả chưa Home → giao diện cảnh báo | sự thật firmware | ✅ |
| S7 | Bộ làm sạch G-code chặn `$…`, ký tự tức thời, `G10 G28 G30 G38 G53 G55–G59 G92`; báo một lần tối đa 5 dòng kèm số dòng. Giao diện giữ cùng danh sách | các lệnh đó đổi gốc / hệ tọa độ → bản vẽ lệch khỏi giấy; danh sách ngắn để tệp thường không bị từ chối oan | ✅ |
| P11 | Tiếp tục từ điểm dừng: lùi 64 dòng rồi lùi tới đầu nét gần nhất, dựng lại trạng thái, kiểm gốc Zero | `ok` chỉ là "đã vào hàng đợi"; vẽ chồng vô hại, bỏ sót thì mất nét | ✅ máy giả · 🧪 máy thật |
| O2 | Hai vai trò khách / quản lý bằng PIN; máy chủ **chặn mặc định**; vẫn giữ lớp mở khóa chuyển động | đề tài cấp trường: khách chỉ xem / gửi ảnh, không cần tài khoản, hàng chờ | ✅ (gửi ảnh ⏳) |

## 3. Tạo bản vẽ và xử lý ảnh
| # | Quyết định | Vì sao | |
|---|---|---|---|
| P3 | Ảnh → nét chạy ở **tiến trình con ưu tiên thấp**; hủy = kết thúc tiến trình; trần 600 s, 4 GB (Linux) | MiniPC yếu vừa điều khiển vừa xử lý; ảnh lạ không làm sập server | ✅ (RAM trên Ubuntu 🧪) |
| P4 | Thứ tự: EXIF → cắt → thu nhỏ → lọc sắc độ → tạo nét | chi phí tỷ lệ số điểm ảnh; làm nét trước khi thu nhỏ là mất | ✅ |
| P5 | Cỡ làm việc = khung ÷ bút × 1,3 (400–4000 điểm); ảnh nhỏ chỉ phóng tới 720; kéo khung lệch > 12 % thì tạo lại nét | khoảng cách nét đúng theo mm thật; thêm điểm ảnh không thêm chi tiết | ✅ |
| P6 | Kiểu tô: zigzag (mặc định, 45°), sóng, xoắn ốc, viền; thêm lớp viền tùy chọn | ít nhấc bút; không vượt 200 000 dòng | ✅ |
| P15 | **Mỗi mức đậm nhạt = một dải, một lượt gạch, khoảng cách riêng** (`level_plan`: độ phủ 0 → 90 % chia đều, s = nét thật ÷ độ phủ; nét thật = 1,375 × cỡ bút). 5 mức mặc định | mô phỏng: sai số 0,174 → 0,071, nét ngắn hơn 45 % so với chồng lớp | ✅ mô phỏng · 🧪 in giấy |
| P16 | Zigzag / sóng quay đầu bằng **nửa vòng tròn** | góc vuông ép máy ~7 mm/s, mực đọng thành giọt | 🧪 |
| P13 | Viền: top-hat (nét mực ≤ 4 mm → đường giữa) + Canny trên ảnh làm phẳng màu (mean shift, kênh a / b Lab) + vòng viền chấm + nối khe ≤ 1,5 mm + cắt râu theo bề dày nét + khép vòng. Thay DoG cũ | DoG cho hai đường song song ở nét dày, mất viền mảng không có nét đen | ✅ ảnh mẫu · 🧪 in giấy |
| P7 | Nhiều màu 2–4: k-means trên Lab có nhấn sắc độ; mỗi màu một tệp G-code, tên có mã màu | để thử; đổi bút giữa các tệp | ✅ |
| P8 | Trình duyệt thu nhỏ ảnh và xem trước độ sáng; máy chủ luôn tự làm được và kiểm lại | gửi nhẹ; không tin dữ liệu từ trình duyệt | ✅ |
| P9 | Bỏ nút "Tạo nháp", "Tạo G-code": nạp là tạo nét, G-code tự tính lại | bản nháp không nhanh hơn đáng kể | ✅ |
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
| S5 | Không ghi nhật ký hệ thống ra tệp | log dài, khó đọc; điểm dừng + sao lưu đã đủ phục hồi | ✅ |
| S6 | Nhập G-code có sẵn = một tệp một bản thảo, qua cùng bộ làm sạch | chạy lại, ghim tệp từ phần mềm khác | ✅ |
| S8 | `data/` nằm ở gốc dự án | cập nhật chỉ thay `backend/` + `frontend/` | ✅ |
| S9 | Ảnh gốc không ghi ra đĩa | riêng tư, đỡ dung lượng | ✅ |

## 5. Triển khai
| # | Quyết định | Vì sao | |
|---|---|---|---|
| O4 | Bản mang đi Windows = Python embeddable + launcher; một icon bật, tự tắt sau 10 phút không có trang | bạn bè chạy được không cần cài Python; không phải nhớ tắt | ✅ |
| O5 | Cập nhật = zip chỉ mã (~0,3 MB) + `Cap nhat.bat` giữ `Python/` và `data/` | khỏi gửi lại ~450 MB | ✅ |
| O1 | MiniPC chạy cả máy chủ và giao diện; một địa chỉ qua Cloudflare Tunnel; không dùng host chia sẻ | host chỉ chứa tệp tĩnh, không giảm tải; cổng USB phải ở MiniPC | ⏳ |
| O6 | MiniPC chạy bằng Docker (venv + systemd dự phòng); IP cố định bằng giữ chỗ DHCP | image gói sẵn thư viện hệ thống; không lộ IP nhà | ⏳ |
| O7 | Quản lý dùng tab vẽ như hiện tại (việc mới hủy việc cũ), không tách "nạp ảnh" và "tạo nét" | chỉ một người tạo nét | ✅ |
| O8 | Demo **không cần Internet**: giao diện không tải gì từ ngoài; tự phát Wi-Fi | buổi trình diễn có thể không có mạng | ✅ |

## 6. Giao diện và tài liệu
| # | Quyết định | Vì sao | |
|---|---|---|---|
| B1 | Terminal giữ tiếng Anh | dễ tra mã lỗi | ✅ |
| B2 | Lỗi / alarm dịch theo mã; Alarm không mã hiện "Alarm (chưa rõ mã)" | | ✅ |
| B5 | Tên VMU PlotterPen; màu chỉ sửa ở `tokens.css`; `polish.css` nạp sau cùng | một nơi đổi màu, dễ hoàn nguyên | ✅ |
| X1 | Tài liệu đánh số 01–11 cho người đọc (từ nhỏ đến lớn), tệp `AI_*` cho AI; bản đồ mã sinh tự động | đỡ phân cấp; người không học code đọc được; AI khỏi quét cả kho | ✅ |
