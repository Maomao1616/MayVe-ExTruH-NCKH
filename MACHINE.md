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

---

## B. Chưa test / Làm tiếp
- B1: Xác nhận thời gian Home chính xác (X, Y, XY).
- B2: Hướng X+/Y+ thực tế trên giấy (dự kiến X+ đi trái, Y+ đi xuống).
- B3: Z bút lên/xuống thực tế (Servo GPIO 32).
- B4: Cung G2/G3 trên máy thật.