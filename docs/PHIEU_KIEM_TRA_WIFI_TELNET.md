# Phiếu kiểm tra mã Wi-Fi (Telnet) — 27/11/2026

> Kiểm tra lại 1 lượt toàn bộ phần kết nối Wi-Fi (telnet) theo hướng dẫn tại `data/phieu-26-11-wifi.md` (mục 7–8), trên commit `062ff85`.

## 1. Kết quả chạy kiểm thử tự động

| Phạm vi | Lệnh | Kết quả | Ghi chú |
|---|---|---|---|
| Backend Wi-Fi & API routes | `python -m pytest -q tests/test_telnet_link.py tests/test_routes.py -v` | **25 passed** (7.11s) | 10 bài `test_telnet_link.py` + 15 bài `test_routes.py` |
| Toàn bộ backend (`pytest`) | `python -m pytest -q --tb=short` | **694 passed, 1 failed** (35.03s) | Bài fail là `test_old_logs_are_pruned` khi chạy song song 6 tiến trình (đã biết trước trong phiếu, chạy riêng qua) |
| Frontend (`node --test`) | `node --test frontend/tests/locales.test.mjs frontend/tests/odometer.test.mjs` | **Chưa chạy được** | Máy hiện tại chưa cài `node` |

---

## 2. Đối chiếu các lỗi cũ đã nêu ở mục 8.1 (`phieu-26-11-wifi.md`)

| # | Vị trí | Tình trạng hiện tại | Chi tiết |
|---|---|---|---|
| 1 | `frontend/js/views/settings.js:673-675` | **Đã sửa** | `const real = s.connection?.mode === "serial" || s.connection?.mode === "wifi";` — đã chặn nút áp dụng cấu hình mạch khi chưa mở khóa cho cả Wi-Fi |
| 2 | `backend/app/links/telnet_link.py:24, 52` | **Đã sửa** | Đã tách `WRITE_TIMEOUT_S = LINK_SILENT_S` (3.0 s) cho `sendall`, luồng đọc dùng `select.select(..., READ_WAIT_S=0.5)` |
| 3–4 | `backend/app/links/telnet_link.py:4-7` | **Đã sửa** | Chú thích đầu tệp đã sửa, trỏ đúng `data/phieu-26-11-wifi.md` |
| 6 | `backend/tests/test_telnet_link.py:178-209` | **Đã sửa** | Đã bổ sung thêm 3 bài test: `write_after_close` + `close` 2 lần, lọc byte `0xFF`, và dòng dài > 4096 byte |

---

## 3. Các vấn đề / điểm cần lưu ý còn lại (quét ngày 27/11)

| # | Tệp:dòng | Vấn đề | Mức độ |
|---|---|---|---|
| 1 | `backend/app/links/telnet_link.py:104` | Mới lọc đơn lẻ byte `0xFF` (`raw.replace(b"\xff", b"")`), chưa bỏ các byte đi kèm trong chuỗi telnet IAC (vd `0xFF 0xFB..0xFE <option>`). FluidNC mặc định không chủ động gửi IAC nên thực tế chưa ảnh hưởng, nhưng nếu có thiết bị/proxy gửi IAC 3 byte sẽ sót 2 byte sau thành ký tự rác | Thấp |
| 2 | `backend/app/links/telnet_link.py:114-122` | Khi `sendall` bị timeout `WRITE_TIMEOUT_S` (3 s), `_write` ném `LinkError` để báo hỏng tác vụ/lệnh, nhưng không tự đóng socket ngay — việc đóng và báo `lost_reason` phụ thuộc luồng `_read_loop` phát hiện quá `LINK_SILENT_S` (3 s) ở chu kỳ kế tiếp | Thấp |
| 3 | `frontend/js/views/settings.js:353, 372` | Khi `mode === "wifi"`, logic submit vẫn đọc và kiểm tra `baud` dù ô baud đã bị ẩn (nếu `<select>` luôn có giá trị mặc định thì không lỗi, nhưng thừa bước kiểm tra cho Wi-Fi) | Thấp |
| 4 | `backend/app/links/telnet_link.py`, `backend/app/services/machine.py`, `frontend/js/**` | Kiểm tra toàn bộ chỗ dùng `"serial"` (`git grep -n '"serial"'`): không còn chỗ nào bỏ sót chế độ `"wifi"` về mặt an toàn hay khóa chuyển động (`REAL_MODES = ("serial", "wifi")`) | Không lỗi |

---

## 4. Các mục chưa kiểm chứng trên máy hiện tại

1. **Đối chiếu mã nguồn FluidNC (`D:\FluidNC-4.1.1`):** Thư mục không tồn tại trên máy đang kiểm tra nên chưa đối chiếu lại mã firmware.
2. **Thử nối mạch thật qua Wi-Fi (`fluidnc.local`):** Chưa thấy mạch `fluidnc.local` trên mạng Wi-Fi hiện tại (`DNS name does not exist`, cổng `23` và `80` không mở).
3. **Các việc phần cứng / đo tốc độ trong phiếu Wi-Fi (mục 4):** Chưa có `tools/do_duong_truyen.py` và chưa đo trực tiếp `$G` / mất sóng trên mạch thật.
