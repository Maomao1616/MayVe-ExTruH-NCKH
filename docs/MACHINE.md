# ExtruXY – Machine Correct (Sự thật máy thật)

**Board**: MKS DLC32 V2.1 · **Firmware**: FluidNC v4.1.1 (esp32-wifi) · **Config**: ConfigNCKH-16.yaml
**Trạng thái test**: Đã test tay không motor/servo (29/10/2026). Chưa test với motor/servo thực tế.

---

## A. Sự thật đã xác nhận (✅)

### A1. Kích thước và Settings
- `$130=285`, `$131=318`, `$132=5` (khớp YAML).
- `$100=80`, `$101=80`, `$102=100` (khớp giả định).
- `$110=6000`, `$111=6000`, `$112=3000`.

### A2. Công tắc hành trình
- Cổng X → Pn:X · Cổng Y → Pn:Y. **Không đảo nhãn**.
- Mức `:high` đúng (giữ = kích). Không cần sửa YAML.

### A3. Trạng thái Boot và $X
- Boot lên → firmware tự vào `Alarm` (do `must_home: true`). G-code bị chặn (error:9).
- Gửi `$X` → về `Idle` → **mọi lệnh G-code đều chạy được** (kể cả X/Y khi chưa Home thực).
- *Hệ quả*: `must_home` chỉ chặn lúc boot. Sau `$X`, UI cần cảnh báo người dùng nếu chạy G-code vượt hành trình mà chưa Home.

### A4. Soft limit — Thứ tự phản hồi
Gửi `g0 x1000` → firmware trả `ok` **trước**, `ALARM:2` **sau**. Backend đã xử lý đúng.

### A5. Feed Hold và Jog
- Đang chạy G-code (Run) → `!` → Hold:1 → Hold:0 (~100ms). Resume được bằng `~`.
- Đang chạy Jog (`$J`) → `!` → **Hủy jog ngay lập tức**, về Idle tại chỗ. KHÔNG resume được.

### A6. Reset và Hủy tác vụ
- Reset từ Run → `ALARM:3` (Abort Cycle).
- Reset từ Hold → Có thể ra `ALARM:3` hoặc về thẳng `Idle` (tùy thời điểm gửi).
- Đã triển khai 3 chế độ Hủy: `reset` (cũ), `soft` (chạy nốt buffer), `hard` (Hold -> Reset -> $X -> Nâng bút).

### A7. Rút cáp USB
- Máy chạy nốt các block trong buffer planner (vài giây) rồi dừng.
- Cắm lại: Backend báo `lost_reason: PermissionError(13)`. Cần nối lại, máy về Idle, không cần reset board.

### A8. Báo cáo trạng thái
- Đủ trường: `MPos`, `WPos`, `WCO`, `Bf`, `F`, `Pn`.
- Dòng `[MSG:Homed:XY]` xuất hiện sau khi Home xong.

### A9. Hold / Jog / Reset (kiểm lại 29/10/2026, sau khi sửa backend)
- Reset khi Hold: về `Idle`, không alarm. Reset ở Alarm khi chưa Home: ra `ALARM:14`.
- `$J` rồi `!`: hủy hẳn, `~` không chạy tiếp được.
- Chạm công tắc hành trình (ALARM:1): **phải Reset trước, rồi mới `$X`** được. Backend đã xử lý (`_unlock_alarm`).
- Chế độ chỉ đọc: `$$ $E $A $Limits $SS $G` đọc được, `$X` gửi được, `?` `!` `~` gõ ở terminal hoạt động.

### A10. Hủy tác vụ trên máy thật (không servo)
- **Dừng êm:** chờ Idle mới → `$J=G90 G21 Z5 F3000` → `pen lift confirmed (Z5)`. Không alarm.
- **Dừng gấp:** Hold → Reset → Idle mới (không alarm) → nâng bút → `pen lift confirmed`. Dừng khi đang Hold cũng không lỗi.
- Trong lúc đang dừng an toàn, nút/lệnh chuyển động bị chặn (`stopping`).
- Rút cáp khi đang chạy: job báo `failed` kèm `PermissionError(13)`, kết nối bị khóa lại về chỉ đọc.
- Z5/Z0 lấy theo WebUI FluidNC: gửi cùng tọa độ thì đúng, không cần đo thêm.

### A11. Sửa cấu hình qua USB (Cài đặt → Cấu hình máy, 29/10/2026)
- Cú pháp đã thử: `$Config/Filename` → `ConfigNCKH-16.yaml`; `$CD` in YAML đang chạy;
  `$/axes/x/max_rate_mm_per_min[=v]` đọc/ghi (ghi chỉ trong RAM); `$LocalFS/List`, `$LocalFS/Show=/<tệp>`;
  `$CD=/localfs/<tệp>` ghi YAML đang chạy ra tệp. Bộ nhớ trống ~60 KB.
- Đọc từ máy: giá trị khớp ConfigNCKH-16. Áp dụng (X 5500): máy đổi tạm, hàng hiện dấu ●.
- Lưu vào mạch: ghi đè YAML thành công, bản gốc được sao lưu về `data/config_backups/`.
- Tắt nguồn, bật lại: giá trị đã lưu vẫn còn.
- `$CD=` viết lại tệp theo dạng chuẩn (mất chú thích `#`, `engine: I2S_STREAM` thành `engine: I2S`); máy vẫn khởi động và chạy bình thường.
- Thanh bút 3 nấc (Z5 / Z2.5 / Z0): chạy đúng, nấc sáng khớp vị trí.

---

## B. Chưa test / Làm tiếp
- B1: Xác nhận thời gian Home chính xác (X, Y, XY).
- B2: Hướng X+/Y+ thực tế trên giấy (dự kiến X+ đi trái, Y+ đi xuống).
- B3: Z bút lên/xuống thực tế (Servo GPIO 32).
- B4: Cung G2/G3 trên máy thật.
