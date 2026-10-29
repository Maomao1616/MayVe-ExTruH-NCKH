# ExtruXY – Sổ quyết định (Cập nhật 29/10/2026)

**Chọn gì – vì sao / đổi ở đâu – mức chắc.** ⚠ = giả định, **chưa kiểm chứng**. ✅ = đã verify trên máy thật (không motor).

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
| C4 | Z5 = bút lên, Z0 = bút xuống | Giả định, chờ test servo thực tế | ⚠ |
| C5 | Gốc (0,0) trên trái. X+ đi trái, Y+ đi xuống (Khớp WebUI) | `VIEW.flipX/Y = false` | ✅ |
| C6 | Nút Tạm dừng (Header) chỉ dùng cho Run. Nút Hủy Jog riêng cho Jog. | Đúng bản chất firmware | ✅ |
| D4 | **Hủy tác vụ 3 chế độ**: `reset` (cũ), `soft` (chạy nốt buffer 60s + nâng bút), `hard` (Hold -> Reset -> $X -> nâng bút). Mặc định UI dùng `soft`, fallback sang `hard` nếu lỗi. | An toàn, giữ được Home nếu có thể | ✅ |
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