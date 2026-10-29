# Bàn giao ExtruXY (29/10/2026)

Ba tệp liên quan: **handover-prompt.md** (tệp này: bối cảnh, tiến độ, việc tiếp, việc khi có máy thật) · **PROJECT_MAP.md** (file, luồng dữ liệu, lộ trình, quy tắc làm song song) · **DECISIONS.md** (quyết định và lý do). Tệp này không lặp lại chi tiết của hai tệp kia.
Phần A: dán vào chat mới. Phần B: việc khi cắm máy thật. Phần C: tài liệu đưa vào nguồn chung của Project.

---

## PHẦN A: LỆNH BÀN GIAO

---BẮT ĐẦU---

Bạn là AI tiếp quản một dự án đang làm dở. Đọc bản này cùng `PROJECT_MAP.md`, `DECISIONS.md` (và `DRAW_ROADMAP.md` nếu làm tab Tạo bản vẽ), rồi làm tiếp ngay; đừng hỏi lại những gì đã nêu. Thiếu thông tin thật sự cần thì hỏi tối đa một câu.
**Việc đầu tiên: người dùng sẽ gửi kèm mã nguồn mới (`backend.zip`, `frontend.zip`). Mã đó là sự thật; tài liệu này có thể lệch.** Giải nén, chạy `pytest` (backend) và `node --test tests/` từng tệp (frontend), rồi đối chiếu mục 3 để biết bản vá nào đã có trong mã.

### 1. BỐI CẢNH & MỤC TIÊU
* Người dùng là sinh viên làm đề tài nghiên cứu khoa học (Project "Nghiên Cứu Khoa Học"): máy viết/máy vẽ CNC tự động, nâng cấp từ đồ án CĐT 2023, kiểu CoreXY, bút tháo lắp nhanh. Mạch MKS DLC32 V2.1 gắn driver TMC2209, FluidNC v4.1.1, USB serial 115200, cấu hình `ConfigNCKH-16.yaml` (X 285 × Y 318 × Z 5 mm; Z là servo bút; công tắc hành trình X, Y thường đóng).
* **Người dùng KHÔNG phải dân chuyên code.** Cần hiểu hướng đi, kế hoạch, vai trò từng file, tư duy logic (để bảo vệ đề tài), không cần hiểu từng dòng. Họ cũng giao việc cho AI khác; code các AI đó từng gây rối.
* **Mục tiêu:** phần mềm điều khiển riêng "ExtruXY Plotter Control System" chạy cục bộ: kết nối, điều khiển tay, terminal, xem trước và chạy G-code, khung 2D, macro (Dock), tab Cài đặt; tab Tạo bản vẽ (ảnh → xử lý bằng Python → G-code) do **AI khác làm song song**.
* **Hướng triển khai:** hiện chạy trên máy cá nhân (Windows, PowerShell, venv ở `C:\Users\ducwt\Documents\ExtruXY\backend`, Git). Giai đoạn sau: **mini PC i5 thế hệ 3** làm máy chủ (xử lý ảnh, cấu hình WiFi hoặc truyền USB từng dòng). Không dùng Raspberry Pi/hosting chia sẻ (xử lý ảnh), laptop không hợp mô hình IoT.
* **Chưa có motor/servo nối vào board.** Đã có mạch MKS với driver và 2 công tắc hành trình; đã chạy thử Home/jog/Zero qua serial không motor (28/10). Mọi thứ khác thử bằng SimLink. Người dùng dùng Claude trên điện thoại (ưu tiên đoạn ngắn, bảng).

### 2. THÔNG TIN CỐT LÕI (chi tiết ở PROJECT_MAP và DECISIONS)
* Backend FastAPI + pyserial (`MachineService`, `JobRunner`, `SimLink`, `SerialLink`); frontend JavaScript thuần ES modules. Frontend chỉ hiển thị; `api.js` là nơi duy nhất gọi mạng; `state.js` là nơi duy nhất thăm dò (0,4 giây).
* **Quy tắc bắt buộc:** một phần tử HTML một chủ ghi; view không import lẫn nhau (dùng `state.js`, `jobstore.js`, `macros.js`, sự kiện `extruxy:message`, `extruxy:macros-changed`); mỗi tab một file view với một hàm vào cửa (`initControl`, `initSettings`, `initDock`, `initHeader`...); mọi chữ hiển thị qua `t()` (có ở cả `vi.json` và `en.json`; thiếu khóa thì hiện chính tên khóa, ví dụ `control.motion.unlock`); không tự thêm tính năng/endpoint.
* **Hiển thị:** terminal giữ tiếng Anh nguyên gốc; mã lỗi firmware/API **không cần dịch thêm** (người dùng xác nhận); lỗi/alarm hiện ở bảng trạng thái qua `t('error.<code>')` / `t('alarm.<code>')`.
* **Dữ liệu thật:** `status.machine` có thể `null`; `last_alarm`/`last_error` là `{code,name,at}`, backend xóa khi Reset hoặc kết nối lại; backend không ghi báo cáo `<...>` vào log; `machine` còn lại sau khi ngắt (giao diện phải kiểm tra `connected`); `status.job.state`: `running → finishing → done | failed | cancelled`; `connection` có `motion_unlocked`, `motion_permanent`, `unlock_available`, `unlock_needs_pin`, `unlock_seconds_left`.
* **An toàn:** máy thật mặc định khóa chuyển động; mở bằng nút trên giao diện (hướng C), tự khóa sau 15 phút rảnh/ngắt kết nối; xem DECISIONS mục S.
* **Giả định chưa kiểm chứng (đừng nói như sự thật):** Z5 = bút lên, Z0 = bút xuống (và `$J=G90 Z..` dùng tọa độ làm việc); gốc (0,0) trên trái, Y xuống; hành vi Hủy tác vụ (Dừng êm / Dừng gấp) trên firmware thật; Reset từ Hold có gây `ALARM:3` không; macro nâng bút khi chưa Home; tốc độ gửi từng dòng với đoạn rất ngắn; nhãn X/Y trong YAML (driver và công tắc có vẻ cắm chéo).
* **G-code:** chạy bằng gửi từng dòng từ máy tính (backend chờ `ok`, dừng khi `error`/`ALARM`/timeout, chặn `$...` trong tệp). **Đã bỏ thẻ SD/flash** (quyết định cuối, D9): không viết lớp lưu trữ, không nút tải lên, không chế độ "chạy từ thẻ".

### 3. TIẾN ĐỘ & VIỆC TIẾP THEO
**Người dùng đã xác nhận áp dụng:** kết nối, trạng thái, terminal; điều khiển; G-code và khung 2D; sửa 4 lỗi backend (`ok` bị nuốt sau hủy, `error` khi Home, dòng lọt sau hủy, cờ `_awaiting`); nút mở khóa chuyển động hoạt động (ảnh chụp 28/10). Người dùng **tự làm lại frontend**: hàng chờ công việc chuyển sang tab Điều khiển, bỏ tab Công việc, chỉnh CSS; khối Flash/SD ở Cài đặt giờ là thừa.

**Claude đã đưa bản vá, chưa có xác nhận đã áp dụng (kiểm tra trong mã bằng `grep`):**
| Bản vá | Dấu hiệu có trong mã |
|---|---|
| Timeout → Feed Hold | `job.py`: `_svc.job_hold()` sau `_fail("timeout"` |
| Poller: mỗi kết nối một cờ dừng | `machine.py`: `self._poll_stop = threading.Event()` trong `connect`, `_poll_loop(self, stop)` |
| Khóa chuyển động (hướng C) | `machine.py`: `set_motion`, `_check_relock`; `routes.py`: `/motion`; `control.js`: `initMotionLock` |
| Hủy tác vụ 3 chế độ | `machine.py`: `cancel_job(mode,...)`, `_stop_sequence`; `routes.py`: `CancelRequest`; `api.js`: `jobCancel(mode, liftZ, liftFeed)`; hộp thoại có `modal-cancel-job-btn-hard`. **Phần backend mới chỉ nằm trong bản sao của Claude; có thể chưa được chép sang** |
| Reset xóa `last_error`/`last_alarm` | `machine.py` nhánh `action == "reset"` |
| Gói Dock + macro + header | `macros.js`, `views/dock.js`, `views/header.js`, `tests/macros.test.mjs`; `index.html` có `<aside id="dock">`; bỏ `data-i18n` ở `backend-status-text`, `machine-state` |
| Dòng trạng thái terminal đều mỗi giây (`Pn`, `WPos`, bỏ giờ) | `terminal.js`: `STATUS_ECHO`, `SHOW_TIME` |
| Test hồi quy backend | `tests/test_regressions.py` (11), `tests/test_motion_unlock.py` (6). Trong bản sao của Claude toàn bộ backend 85/85 pass; **kết quả test thật là của người dùng** |

**Tiếp theo (theo thứ tự):**
1. Đối chiếu bảng trên với mã mới; áp dụng phần còn thiếu; chạy test; bỏ các khối thừa của SD/Flash và Macro giữ chỗ cũ (xem PROJECT_MAP).
2. **Hồ sơ máy trong Cài đặt** (F7): chỉnh/lưu kích thước, Z bút lên/xuống, tốc độ bút, chiều trục ngay trên giao diện (hiện sửa `config.js`).
3. **Làm đẹp giao diện:** gắn nút ↻ làm mới và thanh `system-alert` (chưa có code); trạng thái chờ/rỗng/lỗi từng khối; màn hình hẹp; Dock khớp CSS mới và chế độ sáng/tối.
4. Hàng chờ ở tab Điều khiển: chốt thiết kế backend (mỗi tệp vẫn Xem trước + tích xác nhận).
5. **Backend ghi nhận:** log rotation 3 ngày (E2); đổi dòng `sys` tiếng Việt sang tiếng Anh (B5); tùy chọn `homed_axes`.
6. Khi có motor/servo: Phần B, rồi chỉnh `config.js` (`penUpZ`, `penDownZ`, `VIEW`) và SimLink.
7. Giai đoạn mini PC: xác thực + PIN thật, WiFi/USB, gửi trước nhiều dòng (D10), "Tiếp tục từ dòng N" (D11), thư viện G-code trên máy chủ (M7). Chỉ khi chủ dự án yêu cầu.
8. Cập nhật `PROJECT_MAP.md`, `DECISIONS.md` sau mỗi thay đổi lớn.

**Tab Tạo bản vẽ:** do AI khác làm song song theo `DRAW_ROADMAP.md`; quy tắc ở `PROJECT_MAP.md` mục 7. Đừng sửa file của tab này, và ngược lại.

### 4. PHONG CÁCH & LƯU Ý
* **Tiếng Việt, ngắn gọn, vào trọng tâm cùng đáp án**, giải thích các khóa dẫn tới đáp án; bảng khi so sánh; đoạn ngắn (đọc trên điện thoại). Người dùng hay trả lời ngắn; "Tiếp" nghĩa là làm tiếp; tin nhắn đôi khi bị cụt.
* Trước code: nói bằng lời thường **việc này làm gì, vì sao, đổi file nào**. **Sửa nhỏ: nêu file, vị trí (nên theo đoạn chữ để tìm, vì số dòng lệch) và đoạn cần thay/thêm, không tạo lại cả file**; khi nhiều file thì đóng gói zip kèm `HUONG-DAN.txt` (tệp mới + đoạn chèn).
* Không ngầm nâng cấp; ghi rõ "chưa kiểm chứng" và thử bằng gì; không nhận đã chạy test/trình duyệt nếu chưa chạy. Trước khi vá, **xin zip mới nhất** vì người dùng tự sửa giao diện.
* Giữ thói quen: áp từng bước nhỏ → test → thử bằng sim → commit Git. Sau mỗi bản vá nên chạy "đột biến" (gỡ bản sửa, test phải fail) để biết test có ý nghĩa.

### 5. BÀI HỌC ĐÃ TRẢ GIÁ
* Hai nơi cùng ghi một phần tử gây giật terminal: kiểm bằng `grep -n "<id>" js/*.js js/views/*.js`. Đừng đặt biến tên `t` trong module đã import `t`. Khi dán HTML mới, kiểm trùng `id` (từng có `macro-list` trùng với khối giữ chỗ cũ).
* Chữ không đổi sau khi sửa `.json` hoặc hiện tên khóa: thiếu khóa dịch hoặc cache; Ctrl+Shift+R hoặc F12 → Network → Disable cache. Dán vào JSON nhớ **thêm dấu phẩy** sau dòng cuối cũ.
* Sửa Python xong phải **khởi động lại server**; nút gọi API mới mà server cũ thì 404/405.
* Đọc mã nguồn thay vì suy đoán (từng nói nhầm backend xóa dữ liệu khi ngắt kết nối; từng nói nhầm "Reset sau Hold không Alarm" — SimLink viết theo mã FluidNC cho thấy ngược lại).
* Phần tử giao diện không có code ghi sẽ đứng yên mãi (chấm "Đang kiểm tra backend…"): khi thêm HTML tĩnh phải có chủ ghi.
* Tài liệu bàn giao cũ `Tài_liệu_bàn_giao_dự_án_ExtruXY.txt` (AI khác viết) có 3 chỗ sai: nói backend ghi báo cáo trạng thái vào log (không), vùng 285×310 (đúng 285×318), `last_error` là số (là đối tượng có `.code`). Không dùng nguyên bản.

---END---

---

## PHẦN B: VIỆC KHI CẮM MÁY THẬT

**0. An toàn:** tay gần công tắc nguồn; chưa đặt giấy, bút nâng cao hoặc chưa lắp; vùng di chuyển trống. Reset trong phần mềm chỉ là dừng mềm. **Tắt nguồn trước khi cắm/rút motor khỏi driver TMC2209.**

**Đã làm 28/10 (không motor):** bước 1 (chỉ đọc), Home X/Y/XY, jog, Zero, vài `ALARM`/`error` (xem DECISIONS, "Dữ liệu thật"). Thẻ SD: đã bỏ.

**Còn lại, làm không cần motor (máy "chạy ảo"):**
1. Mở khóa bằng nút giao diện (hoặc `$env:EXTRUXY_ALLOW_MOTION="1"`); xem thanh "CHẠY THẬT", thử Khóa lại, ngắt rồi nối lại (phải tự khóa).
2. **Công tắc:** bấm giữ từng công tắc, xem trường `Pn:` (WebUI hoặc dòng trạng thái terminal sau khi sửa B3) → xác nhận công tắc nào ứng trục nào, mức `:high` đúng; kết luận nhãn X/Y trong YAML.
3. **`G0 Z3` khi chưa Home:** có `ALARM:14` không (quyết định M5).
4. **Hold → Reset:** gửi `G1` dài, `!`, chờ `Hold:0`, Ctrl-X: có `ALARM:3` không; sau `$X`, jog `$J=G90 Z5 F1000` có chạy không (quyết định D4). Thử luôn hai nút Dừng êm / Dừng gấp.
5. **Jog khi đang Hold:** firmware có từ chối không (mã lỗi).
6. **Tốc độ gửi (D10):** chạy tệp vài nghìn đoạn ngắn (~0,2 mm, F3000), xem trạng thái có nhảy Run/Idle không (bộ lập kế hoạch cạn); đo dòng/giây.
7. `$CMD` (liệt kê lệnh thật), `$I`, `$$` đầy đủ.
8. Rút cáp USB khi máy đang di chuyển (một lần): máy chạy nốt hàng đợi không; mở lại cổng thế nào.

**Khi có motor/servo:**
* Jog bước nhỏ: X+ và Y+ đưa đầu bút về phía nào (quyết định `VIEW`); chiều quay; `steps_per_mm`.
* Bút: giá trị Z bút lên/xuống thật, servo có nhận jog tuyệt đối Z (cập nhật `penUpZ`, `penDownZ`, `penFeed`).
* Hành trình, công tắc giới hạn, hard limit: chép nguyên văn `ALARM:N`/`error:N` và hoàn cảnh.
* **G-code thật:** tệp vuông nhỏ, bút nâng cao rồi hạ xuống giấy; so khung 2D/vết bút với thực tế; thời gian ước tính với thực tế (không tính gia tốc); cung tròn `G2/G3`; tệp thiếu F, vượt vùng, có `M0`; Tạm dừng/Tiếp tục/Hủy (hai chế độ).

**Dữ liệu gửi lại để hoàn thiện SimLink** (để sau đó không cần cắm máy nữa): (1) kết quả `$I`, `$$`, `$#`, `$G`, `$CD`, `$CMD`; (2) 10 báo cáo trạng thái thô lúc Idle/jog/Home/Hold, kèm `Pn`; (3) hướng trục, hướng Home, tọa độ sau Home, vùng làm việc thực; (4) Z bút lên/xuống và jog Z; (5) phản hồi thật của `G10 L20 P1`, `$HX`, `$HY`, `$J=G90 ... X0 Y0` khi chưa Home, dòng vô nghĩa như `???`, `g0 x1000` (giải thích `error:1`); (6) mọi `ALARM:N`/`error:N`; (7) thời gian Home, độ trễ phản hồi; (8) hành vi rút cáp; (9) kết quả chạy G-code thật; (10) kết quả mục 4 và 6 ở trên. Tệp thô đã có: `báo_cáo_chạy_serial.txt` (28/10).

---

## PHẦN C: TÀI LIỆU ĐƯA VÀO NGUỒN CHUNG CỦA PROJECT
Nếu sang **tài khoản mới**, ghi chú tự động của phiên cũ không đi theo; phiên mới dựa vào các tệp này và Phần A.

1. `handover-prompt.md`, `PROJECT_MAP.md`, `DECISIONS.md` (cập nhật sau mỗi thay đổi lớn), `DRAW_ROADMAP.md`.
2. **Mã nguồn hiện tại:** zip `backend/` + `frontend/` đã áp dụng bản vá và commit (không kèm `.venv`, `__pycache__`, `.git`); nạp lại khi có thay đổi lớn.
3. `ConfigNCKH-16.yaml` (thay bằng bản mới nếu chỉnh); `báo_cáo_chạy_serial.txt` (dữ liệu thật 28/10); `README.md` phần cứng MKS DLC32, PDF đồ án gốc, PDF extruder/pen plotter; ảnh chụp giao diện.
4. Khi có máy thật: `machine-data.md` (gom dữ liệu Phần B), vài tệp G-code thật.
5. Có thể bỏ: `frontend-brief.md`, `backend-summary.md`/`control-plan.md`/`frontend-review.md`/`gcode-2d-plan.md` nếu đã lỗi thời so với mã mới (kiểm trước khi bỏ). Không dùng nguyên bản `Tài_liệu_bàn_giao_dự_án_ExtruXY.txt`.
6. Quyết định cuối: **bỏ thẻ SD/Flash** (D9); macro chỉ ở Dock (M2); khóa chuyển động hướng C (S2).
