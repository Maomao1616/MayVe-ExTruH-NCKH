# ExtruXY – Sổ quyết định (29/10/2026)

**Chọn gì – vì sao / đổi ở đâu – mức chắc.** Chi tiết cấu trúc xem `PROJECT_MAP.md`; bối cảnh và việc tiếp theo xem `handover-prompt.md`.

**Cột "Chắc":** **Chốt** = chủ dự án đã quyết · ⚠ = giả định, **chưa kiểm chứng trên máy thật** · **Chờ làm** = đã quyết, chưa viết code · **Đề xuất** = Claude đã đề xuất, chủ dự án chưa trả lời rõ.
**Trạng thái code** (ghi cuối dòng khi cần): ✅ người dùng xác nhận đã áp dụng và chạy · 📦 Claude đã đưa bản vá/gói, **chưa có xác nhận đã áp dụng** (AI tiếp quản phải kiểm tra trong mã nguồn thật bằng `grep`) · ⏳ chưa làm.

## Kiến trúc và quy tắc code
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| A1 | Backend Python + frontend JavaScript thuần. Chạy cục bộ; sau này đặt lên **mini PC (i5 thế hệ 3)**, không dùng Raspberry Pi hay hosting chia sẻ vì cần xử lý ảnh | Xử lý ảnh hợp Python; `pyserial` ổn định. Mini PC: cần Windows 10+ (Python 3.12) hoặc cài Linux, RAM ≥ 4 GB, SSD, tắt chế độ ngủ | Chốt |
| A2 | Frontend chỉ hiển thị, backend là nguồn sự thật; hỏi backend mỗi 0,4 giây | Không đoán sai trạng thái; đổi ở `POLL` (`config.js`) | Chốt |
| A3 | Không framework, không bước build; giữ `import ... with {type:"json"}` | Đơn giản, dễ giao AI khác. Test frontend thuần dùng `node --test` | Chốt |
| A4 | SimLink (giả) và SerialLink (thật). Máy thật **mặc định khóa chuyển động**; cách mở khóa xem mục "An toàn" (S1–S5) | An toàn | Chốt |
| A5 | Chỉ `api.js` gọi mạng, chỉ `state.js` thăm dò | Một nơi để sửa | Chốt |
| A6 | Một phần tử giao diện một chủ ghi; view không import lẫn nhau (dùng `state.js`, `jobstore.js`, `macros.js`, sự kiện `extruxy:message`, `extruxy:macros-changed`) | Từng có hai nơi ghi terminal → giật. Kiểm: `grep -n "<id>" js/*.js js/views/*.js` | Chốt |
| A7 | Mỗi tab một file view, một hàm vào cửa; khối là hàm riêng; khối lớn tách file nhưng vẫn do hàm vào cửa gọi. Phần dùng chung mọi tab (Dock, chỉ báo đầu trang) là view riêng: `dock.js` (`initDock`), `header.js` (`initHeader`). **Đã bỏ tab Công việc** (xem F8) | Dễ chia, khớp cách đang làm | Chốt |
| A8 | Không tự thêm tính năng/endpoint ngoài yêu cầu; sửa nhỏ chỉ đưa đoạn cần sửa (file, vị trí, đoạn thay); mỗi phần mới có test và ghi rõ cái gì chưa kiểm chứng; không nhận đã chạy test nếu chưa chạy | Người dùng kiểm soát phạm vi; AI cũng có thể sai | Chốt |

## Hiển thị
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| B1 | Terminal giữ tiếng Anh nguyên gốc, không i18n; chỉ thêm dòng theo `seq`; Xóa chỉ xóa hiển thị. **Mã lỗi/alarm của firmware và mã lỗi API không cần dịch thêm** (chủ dự án) | Tra mã lỗi dễ; log backend không bị đụng | Chốt |
| B2 | Lỗi/alarm firmware hiện ở bảng trạng thái, dịch `t('error.N')`, `t('alarm.N')` theo `.code`; alarm chỉ hiện khi máy ở trạng thái Alarm. Từ 28/10: **Reset xóa `last_error`/`last_alarm`** ở backend (lỗi `error:9` cũ cứ hiện mãi) | `vi.json`, `en.json`; `machine.py` (`send_realtime`) | Chốt · 📦 |
| B3 | Dòng trạng thái trong terminal: tối đa 1 lần/giây. Chủ dự án muốn **in đều mỗi giây (không chỉ khi đổi), có `WPos` và `Pn`, bỏ giờ ở đầu dòng**: đặt `onlyWhenChanged:false`, thêm `wpos`/`pins` vào chuỗi, hằng `SHOW_TIME=false`. Lưu ý đệm 500 dòng đầy sau ≈ 8 phút | `STATUS_ECHO`, `echoStatus`, `addLine` (`terminal.js`) | Đề xuất · 📦 |
| B4 | Vị trí về "—" khi chưa kết nối | Backend giữ số cuối sau ngắt | Chốt |
| B5 | Đổi dòng `sys` tiếng Việt của backend sang tiếng Anh (các dòng mới từ 28/10 đã viết tiếng Anh) | `machine.py`, `serial_link.py`, `sim_link.py` | Chờ làm |
| B6 | **Chỉ báo đầu trang** (`header.js`, chủ ghi duy nhất của `backend-status-*`, `machine-state`, `machine-status-dot`, `job-status-dot`): backend vàng nhấp nháy khi chờ phản hồi đầu / xanh / đỏ; máy: chưa kết nối / "Dữ liệu cũ" / trạng thái firmware; công việc: chấm màu. Phải **bỏ `data-i18n`** khỏi `backend-status-text` và `machine-state` | Trước đó không có code nào ghi các phần tử này nên đứng mãi ở "Đang kiểm tra backend…" | Chốt · 📦 |
| B7 | Nút ↻ làm mới (`refresh-status-btn`) và thanh `system-alert` hiện **chưa có code nào điều khiển** | Việc làm đẹp giao diện | Chờ làm |

## Điều khiển máy
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| C1 | Jog, XY 0, bút, Zero mở khi `Idle`; Home khi `Idle`/`Alarm`; hủy jog khi `Jog`; cần: đã kết nối + dữ liệu mới (≤ 2 giây) + `motion_unlocked` | `updateControls` trong `control.js`, `POLL.staleMs` | Chốt · ✅ trên sim; jog/Home/Zero đã chạy qua serial thật không motor |
| C2 | Jog `$J=G91 ...`; XY 0 và bút dùng jog tuyệt đối `$J=G90 ...` (luôn kèm `F`; thiếu `F` firmware trả `error:22`) | Chạy được cả khi chưa Home (tránh `ALARM:14`) | Chốt |
| C3 | Zero `G10 L20 P1 ...`; Home từng trục `$HX`, `$HY` | **Đã chạy đúng qua serial thật 28/10 (không motor)** | Chốt (chứng thực một phần) |
| C4 | Z5 = bút lên, Z0 = bút xuống. Nâng bút bằng `$J=G90 Z.. F..` là tọa độ **làm việc**, giả định Z làm việc trùng Z máy | `penUpZ`, `penDownZ`, `penFeed` (`config.js`) | ⚠ |
| C5 | Gốc (0,0) trên trái, X sang phải, Y xuống | `VIEW.flipX/flipY` | ⚠ |
| C6 | Không phím tắt; không hộp xác nhận Home/Zero/ngắt kết nối; Reset chỉ là dừng mềm, không gọi là dừng khẩn cấp (cần nút ngắt nguồn vật lý). Hiện nút Reset trong terminal có hộp thoại xác nhận riêng (chủ dự án tự thêm) | Dừng khẩn cấp thật là cắt nguồn | Chốt |
| C7 | `homed_guess` là đoán, theo từng trục; chỉ true khi đủ X và Y; `ALARM:14` không làm mất trục đã Home | `machine.py`, `sim_link.py` | Chốt |
| C8 | Firmware yêu cầu Reset trước rồi mới `$X` sau khi chạm giới hạn cứng; nên gợi ý trên nút Mở khóa | Quan sát 28/10 | Chốt |

## G-code và khung 2D
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| D1 | Chạy bằng **gửi từng dòng từ máy tính**, chờ `ok`; trình duyệt đọc tệp rồi gửi danh sách dòng | Dễ tạm dừng/hủy/báo tiến trình; FluidNC giữ `ok` khi hàng đợi đầy | Chốt |
| D2 | Backend làm sạch dòng, **chặn** `$...`, `? ! ~`, Ctrl-X, dòng > 200 ký tự | Tệp không được đổi cài đặt hay điều khiển ngoài luồng (`job.py`) | Chốt |
| D3 | Dòng lỗi hoặc `ALARM` → dừng tác vụ + Feed Hold; **timeout (120 s không có `ok`) cũng Feed Hold** (📦); đang chạy thì chặn lệnh khác, realtime vẫn dùng được | Tránh máy tự chạy tiếp | Chốt |
| D4 | **Hủy tác vụ có 3 chế độ** (`POST /api/jobs/cancel`, trường `mode`): `reset` (cũ, mặc định); `soft` = **Dừng êm**: ngừng gửi, máy chạy nốt đoạn trong bộ đệm, rồi nâng bút, không Alarm, giữ Home; `hard` = **Dừng gấp**: Feed Hold → Reset → `$X` → nâng bút bằng jog; máy vào Alarm 3, phải Home lại. `soft` mà máy đang Hold/Door/Alarm thì tự chuyển `hard`. Giao diện: hộp thoại hủy có hai nút | `machine.py` (`cancel_job`, `_stop_sequence`), `routes.py` (`CancelRequest`), `control.js`, `index.html`. **Sửa lời cũ:** Reset từ Hold vẫn Alarm 3 theo SimLink (viết theo mã nguồn FluidNC); chưa kiểm trên board | ⚠ · 📦 |
| D5 | Phải Xem trước và tích xác nhận mới Chạy được; tệp vượt vùng làm việc (tính cả WCO) bị khóa Chạy. Cảnh báo `unsupported_g`, `unsupported_m`, `arc_params` hiện **không** khóa nút Chạy; khóa chúng là **đề xuất** thay đổi D7 | `control.js` | Chốt (phần khóa theo cảnh báo: Đề xuất) |
| D6 | Xem trước chỉ đọc G-code ở trình duyệt, có phát lại; chạy thật hiện vị trí máy báo về và vết bút khi bút xuống. Lưu ý: ngay sau khởi động Z = 0 nên vết bút có thể hiện "bút xuống" dù bút chưa hạ (phụ thuộc C4) | `preview.js` | Chốt |
| D7 | Thời gian ước tính không tính gia tốc; sau `M2/M30` không gửi; `G92`, `G10`, `G28/30`, `G53`, `G55–59` chỉ cảnh báo | `gcode.js` | Chốt |
| D8 | SimLink: `G2/G3` đi thẳng tới điểm cuối | Máy thật hỗ trợ cung tròn | Chốt |
| D9 | **Bỏ hoàn toàn thẻ SD/Flash** (chủ dự án 29/10). Lý do nêu: thẻ chưa nhận (`error:60`, log `sdmmc_card_init failed 0x106`, nguyên nhân chưa xác định, nghi do định dạng; wiki FluidNC khuyên định dạng bằng SD Memory Card Formatter); truyền tệp qua USB (XModem, cần chế độ thô cho cổng COM) hoặc WiFi (IP đổi, chưa có xác thực) phức tạp và nhiều rủi ro. Chỉ dùng streaming từ máy tính; khi có mini PC thì backend chạy ở đó. Việc bỏ: lớp lưu trữ backend, khối Thẻ SD/Flash, nút tải lên trong khối G-code, chế độ "chạy từ thẻ" (`initRunModeSwitch`) | Đơn giản hóa; có thể xem lại khi có mini PC | Chốt |
| D10 | **Rủi ro khi chỉ streaming (⚠ cần đo):** (a) bộ chạy gửi một dòng rồi chờ `ok` (stop-and-wait): đường cong bị chia thành đoạn rất ngắn (~0,2 mm, 50 mm/s → vài trăm dòng/giây) có thể làm bộ lập kế hoạch cạn, máy giật. Cách chữa nếu có: gửi trước nhiều dòng (đếm ký tự kiểu Grbl). (b) Đứt cáp/treo máy chủ giữa chừng: máy chạy nốt bộ đệm rồi dừng, bút có thể còn hạ | Cần đo bằng tệp vài nghìn đoạn ngắn trên board | ⚠ |
| D11 | Ý tưởng chưa chốt: **"Tiếp tục từ dòng N"** (backend nhớ dòng cuối nhận `ok`; sau sự cố nâng bút, về điểm đó, chạy tiếp); **thư viện G-code trên đĩa máy chủ** (`data/gcode/`: liệt kê, tải lên từ trình duyệt, xóa) làm nguồn cho nút "Tệp nhanh" | Thay vai trò của thẻ SD mà không đụng MKS | Đề xuất |

## An toàn và khóa chuyển động
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| S1 | Máy thật mặc định **khóa**; SimLink luôn mở | `connection_info().motion_unlocked` | Chốt |
| S2 | **Hướng C** (đã chốt): mở khóa bằng nút "Mở khóa chuyển động" trên giao diện (banner chỉ đọc ở tab Điều khiển); thanh "CHẠY THẬT" đếm ngược + nút Khóa lại. Endpoint `POST /api/motion {on, pin}` | `machine.py` (`set_motion`, `_relock`, `_check_relock`), `routes.py`, `control.js` (`initMotionLock`) | Chốt · ✅ (chủ dự án báo chạy OK) |
| S3 | Tự khóa lại: khi ngắt kết nối/mất cáp, khi khởi động lại server, và sau `EXTRUXY_UNLOCK_MINUTES` phút rảnh (mặc định 15; 0 = tắt; máy đang bận hoặc có tác vụ thì không tính là rảnh) | Mở khóa phải có thời hạn | Chốt |
| S4 | Biến môi trường: `EXTRUXY_ALLOW_MOTION=1` = mở khóa **cố định** từ lúc khởi động (không tự khóa, không khóa lại được); `EXTRUXY_UNLOCK_PIN` (nếu đặt: nút đòi PIN; hiện nhập bằng hộp thoại tạm của trình duyệt); `EXTRUXY_NO_UNLOCK=1` (cấm mở từ giao diện) | Cục bộ không cần PIN; truy cập từ xa bắt buộc PIN | Chốt |
| S5 | **Truy cập từ xa:** làm xác thực trước nút mở khóa; qua VPN (ví dụ Tailscale), không mở cổng MKS ra Internet (WebUI FluidNC mặc định không bật mật khẩu, ⚠ chưa kiểm). Máy đặt xa cần nút ngắt nguồn vật lý hoặc ổ cắm điều khiển được, và camera | Reset trong app không phải dừng khẩn cấp | Chốt hướng |
| S6 | Khởi động server bằng một file `chay-server.bat` (bật venv, mở trình duyệt, `uvicorn app.main:app`, không `--reload`) | Tiện; chế độ do nút giao diện quyết định, không cần hai file | Chốt |

## Macro và Dock (29/10/2026)
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| M1 | **Dock** bên trái luôn hiện ở mọi tab (nút ⚡ ở mép trái, panel mở/thu, nhớ trạng thái, phủ lên giao diện chứ không đổi bố cục). Dock chỉ để **truy cập nhanh**: macro và tệp | `dock.js`, khối `<aside id="dock">`, CSS cuối `style.css` | Chốt · 📦 |
| M2 | **Macro chỉ nằm trong Dock** (tạo/sửa/xóa/chạy tại đó). **Bỏ** khối "Macro nhanh" ở tab Điều khiển và panel Macro ở Cài đặt (không có code nào dùng chúng). Thay F2 cũ | Dock luôn hiện nên không cần hai nơi | Chốt · 📦 |
| M3 | Hai loại macro: `gcode` (1–50 dòng, không có `$`, chạy như **tác vụ** nên có tiến trình/hủy/dừng khi lỗi) và `command` (đúng 1 dòng, được là `$H`, `$X`…, gửi bằng lệnh đơn). Không gửi nhiều dòng bằng lệnh đơn vì lệnh đơn không chờ `ok` | `macros.js`, `dock.js` | Chốt · 📦 |
| M4 | Lưu bằng `localStorage` (khóa `extruxy-macros-v1`); đổi nơi lưu (backend, flash của mini PC) chỉ sửa `readAll`/`writeAll` trong `macros.js`. Kiểm tra: tên 1–40 ký tự và không trùng, ≤ 50 dòng, mỗi dòng ≤ 200 ký tự, cấm `? ! ~`, tối đa 30 macro | `macros.js`; test `tests/macros.test.mjs` (5 test) | Chốt · 📦 |
| M5 | Macro có cờ `needsHome`, **mặc định tắt** (không bắt Home): `ALARM:14` của firmware đã chặn chuyển động khi chưa Home nên app không cần chặn thay. Việc cần thử: khi chưa Home, gửi `G0 Z3` xem có `ALARM:14` không; nếu có thì macro nâng/hạ bút phải dùng `$J=G90 Z.. F..` (khi đó cần nới hẹp D2 cho `$J=` trong macro, chủ dự án duyệt) | Chủ dự án thấy bắt Home là bó buộc | Chốt · ⚠ |
| M6 | Nút macro bật khi: kết nối + dữ liệu mới + không khóa; `gcode` chỉ khi `Idle`; `command` khi `Idle` hoặc `Alarm`; không có tác vụ đang chạy; `needsHome` thì cần `homed_guess`. Tắt thì có chú thích lý do (rê chuột) | `whyNotRunnable` trong `dock.js` | Chốt · 📦 |
| M7 | Mục "Tệp nhanh" trong Dock chỉ là chỗ giữ sẵn. Nguồn tương lai: thư viện G-code trên máy chủ (D11), không phải thẻ SD | Sau khi bỏ SD | Đề xuất |
| M8 | Macro mẫu "Chấm" = `G90`, `G0 Z0`, `G4 P0.2`, `G0 Z5` phụ thuộc C4 nên **chưa đưa vào mẫu mặc định** | | ⚠ |

## Backend và kế hoạch
| # | Quyết định | Vì sao / đổi ở đâu | Chắc |
|---|---|---|---|
| E1 | Backend không ghi báo cáo trạng thái `<...>` vào nhật ký; `machine`/`last_*` giữ sau khi ngắt (chỉ xóa khi kết nối lại hoặc khi Reset, xem B2) | Tránh ngập; còn xem vị trí cuối khi mất cáp | Chốt |
| E2 | Log rotation: giữ tối đa 3 ngày, chia file theo ngày. **Giữ ở backend** dù bỏ tab Công việc (cần bằng chứng sau khi mất điện/đứt cáp) | Không quá tải bộ nhớ | Chờ làm |
| E3 | Mã lỗi API ổn định; frontend dịch theo `code`, không hiện `message`. Mã mới: `bad_pin`, `unlock_forbidden`, `unlock_permanent`, `no_job`, `bad_request` (terminal có thể hiện nguyên mã) | Đổi ngôn ngữ được | Chốt |
| E4 | **Sửa lỗi backend 28/10** (đều có test hồi quy trong `tests/test_regressions.py`): `_awaiting` còn True sau hủy/lỗi nên `ok` đầu tiên bị nuốt (sửa trong `_finish`) ✅; `error` không xóa `_homing_pending` ✅; dòng lọt ra cổng sau khi hủy (kiểm `is_live` dưới khóa trong `job_write`) ✅; timeout không Feed Hold 📦; cờ dừng poller dùng chung nên 2 luồng khi kết nối lại nhanh (mỗi kết nối một `Event`) 📦; Reset xóa `last_error` 📦 | `job.py`, `machine.py` | Chốt |
| F1 | Thứ tự: Control → bổ sung API/lệnh → thử máy thật một lần → hoàn thiện bằng SimLink. Tab Cài đặt: giao diện trước, backend sau. Tab Tạo bản vẽ: backend trước | Người dùng muốn thấy kết quả sớm | Chốt |
| F2 | ~~Macro quản lý ở Cài đặt, chạy ở Điều khiển~~ → thay bằng M2 | | Thay thế |
| F3 | Giai đoạn đầu chỉ cần giao diện mượt, đẹp vừa phải; chủ dự án tự chỉnh CSS (29/10) | Ưu tiên chạy được | Chốt |
| F4 | Người dùng không phải dân chuyên code: giải thích vai trò/lý do bằng lời thường trước, code sau; trả lời ngắn, vào trọng tâm cùng đáp án, nêu các khóa dẫn tới đáp án; không ngầm nâng cấp | Cần hiểu và bảo vệ đề tài | Chốt |
| F5 | **Tab Tạo bản vẽ giao cho AI khác làm song song**, theo `DRAW_ROADMAP.md` và các quy tắc ở `PROJECT_MAP.md` mục 7 (nhánh Git `draw`, giao G-code qua `jobstore.setFile`, không sửa lõi) | Làm nhanh hơn | Chốt |
| F6 | Hàng chờ công việc nằm ở tab Điều khiển (giao diện do chủ dự án làm); **backend chưa có hàng đợi** — cần bàn thiết kế (mỗi tệp vẫn phải Xem trước + tích xác nhận theo D5) | | Chờ làm |
| F7 | Hồ sơ máy trong Cài đặt: chỉnh được kích thước vùng, Z bút lên/xuống, tốc độ bút, chiều trục (`VIEW.flipX/flipY`) ngay trên giao diện và lưu lại (hiện phải sửa `config.js`); cần nhiều khi thử máy thật vì C4, C5 còn ⚠ | | Chờ làm |
| F8 | **Bỏ tab Công việc** (không cần lịch sử log/lỗi trên giao diện vì nhóm tự kiểm soát); `views/jobs.js` không còn cần | Chủ dự án | Chốt |

## Dữ liệu thật đã có (28/10/2026, qua serial, chưa nối motor/servo)
| Điều | Kết quả |
|---|---|
| `$CD` trên board | Khớp `ConfigNCKH-16` (`name: MAYVE`). Trục X: công tắc `gpio.36`, driver `I2SO.5`; trục Y: công tắc `gpio.35`, driver `I2SO.1`. Firmware báo `engine: I2S` còn YAML ghi `I2S_STREAM` (có thể là tên mới của v4.1.1, vô hại) |
| Công việc đã chạy | Home X, Y, XY; jog; Zero; hủy khi đang chạy → `ALARM:3` |
| Công tắc hành trình | **Thường đóng**, cấu hình `:high` chạy đúng khi Home |
| Mã quan sát được | `ALARM:1, 2, 3, 6, 8, 9, 14`; `error:1, 2, 9, 22, 60`. `error:22` = jog thiếu `F`; `error:2` = số sai định dạng; `error:1` khi gõ `g0 x1000` chưa giải thích được |
| `Pn:` | Backend đọc vào `pins` nhưng giao diện không hiển thị; phản hồi `?` không vào log (E1). Kiểm chéo bằng WebUI |
| Thẻ SD | `$SD/List` → `error:60`; log: `sdmmc_card_init failed 0x106`, `No SD card detected`; đã đo thông 4 chân SPI (chưa đo chân detect `gpio.39`). Đã quyết bỏ (D9) |
| Mất điện | Backend báo mất kết nối (Windows `PermissionError(13…)`); kết nối lại thủ công |

## Cần xác nhận khi có máy thật
C4, C5, D4 (Reset từ Hold có Alarm 3 không; sau `$X` jog nâng bút có chạy không), D10 (tốc độ gửi, rút cáp), M5 (`G0 Z3` khi chưa Home), cung tròn `G2/G3`, chiều quay motor, Z servo, nhãn X/Y trong YAML (driver và công tắc có vẻ cắm chéo: trục `y` dùng driver socket X nhưng công tắc Y, và ngược lại — xem Phần B của `handover-prompt.md`).
