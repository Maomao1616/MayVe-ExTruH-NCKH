# Ý tưởng tính năng mới (beta, CHƯA làm)

Ghi lại các ý tưởng đã bàn ngày 01/11/2026 để lần sau làm tiếp không phải bàn lại. Chưa có dòng code nào; các con số thời gian là **ước lượng**, phải đo trên MiniPC thật (i5-3210M, không card đồ họa; bước 1 trong `PLAN_ONLINE.md`).

Bối cảnh sử dụng: bút **0,2 / 0,4 / 0,5 mm**, viết chữ dùng **0,5**; văn bản Word thường cỡ **14–16** (Arial / Times New Roman); khổ A4 (210 × 297 mm) vừa vùng vẽ 285 × 318 mm.

## Cấu trúc chung: chỉ thêm "nguồn nét"

Dây chuyền hiện có: **ảnh → nét → G-code**. Phần "nét → G-code" (đặt lên giấy, nhấc/hạ bút, sắp thứ tự nét) dùng chung. Mỗi tính năng mới chỉ là một nguồn tạo nét đổ vào đó, không đụng phần đang chạy tốt:

```
PDF từ Word ──→ ảnh từng trang → skeleton ─┐
Câu lệnh    ──→ AI tạo ảnh nét ─────────────┼──→ NÉT ──→ G-code (đã có)
Mẫu chữ tay ──→ bộ chữ riêng → bộ viết chữ ─┘
```

Thứ tự nên làm: (1) in nguyên trang PDF → (2) định dạng bộ chữ + bộ viết chữ → (3) lấy mẫu chữ tay → (4) viết Word bằng chữ tay → (5) AI tạo ảnh.

---

## 1. In nguyên trang Word / PDF (khả thi cao, làm trước)

**Cách làm:** người dùng tự **Lưu thành PDF trong Word** (File → Save As → PDF) rồi nạp PDF; mỗi trang thành một bản thảo. Mỗi trang được kết xuất thành ảnh rồi đi qua **skeleton** (đã có trong nét viền, `services/drawing/edges.py`) → mỗi nét chữ thành một đường giữa.

- Giữ đúng font, đúng dấu tiếng Việt, đúng bố cục (PDF → ảnh không làm lệch bố cục).
- Không tự chuyển Word → PDF trên MiniPC: LibreOffice thiếu font Arial/Times có thể làm chữ xuống dòng khác. Để Word xuất PDF là đúng nhất và MiniPC khỏi cài LibreOffice.

**Vì sao skeleton hợp với chữ 14–16 + bút 0,5:**

| Loại chữ (cỡ 14–16) | Nét chữ thật | Vẽ bằng bút 0,5 |
|---|---|---|
| Thường (Arial, Times) | ~0,45–0,55 mm | một nét ≈ y hệt bản in |
| Đậm (Bold) | ~0,8 mm | một nét hơi mảnh; muốn giống thì 2 đường sát nhau (không cần tô kín) |
| Nét mảnh của Times | ~0,15–0,2 mm | thành dày bằng nét chính (mất thanh đậm), vẫn dễ đọc |
| Lỗ chữ e, a, o | ~1 mm | còn hở, không bị bít |

Bút 0,4 gần như 0,5; bút 0,2 trông mảnh như bút kim (hợp vẽ hình chi tiết hơn).

**Preset "Văn bản" cần khác preset ảnh ở các điểm:**

1. **Độ phân giải cao hơn: ~10–12 điểm ảnh/mm** (ảnh thường chỉ cần khung ÷ bút × 1,3 ≈ 3–4 điểm ảnh/mm).
   - Tranh gạch / zigzag / xoắn ốc lấy **độ đậm nhạt từng vùng**, chi tiết nhỏ hơn khoảng cách nét không vẽ được, nên thấp là đủ.
   - Chữ cần **vị trí đường giữa chính xác**. Chữ cỡ 14 cao ~2,6 mm (thường) / ~3,5 mm (hoa). Ở 3–4 px/mm chữ "o" chỉ ~10 px, cung bị gãy; ở 10–12 px/mm nét chữ 5–6 px, chữ "o" ~30 px, đường giữa trơn.
   - Cách làm: đổi `OVERSAMPLE` (`raster_in.py`, hiện 1,3) riêng cho preset này, khoảng 5–6. `MAX_SIDE_PX` 4000 vẫn đủ (A4 dài 297 mm → trần ~13,5 px/mm).
   - A4 ở 12 px/mm ≈ 9 triệu điểm ảnh, gấp ~16 lần ảnh thường → lâu hơn (ước vài giây đến vài chục giây/trang), không quá tải nhờ các giới hạn bên dưới.
2. **Tắt nối khe hở** (`bridge`, `GAP_MM` 1,5 trong `edges.py`): khoảng cách giữa hai chữ cái chỉ ~0,5–0,8 mm, để nguyên sẽ nối dính các chữ.
3. **Cắt râu ngắn** sau skeleton (chân chữ Times để lại nhánh nhỏ, rõ hơn ở cỡ 14–16).
4. **Làm mượt nét** sau skeleton (bỏ bậc thang điểm ảnh).
5. **Nét dày hơn ~1,5 lần bút** (chữ đậm, tiêu đề to): vẽ 2 đường sát nhau.
6. **Tỉ lệ 1:1**: trang A4 vẽ đúng 210 × 297 mm, không phóng/thu theo khung.
7. Chữ dưới cỡ 8 không khuyên dùng (bút 0,4–0,5 dễ bít lỗ chữ).

**Thời gian vẽ** một trang kín chữ: ước 20–30 phút, chủ yếu do nhấc/hạ bút hàng nghìn lần (chữ 14–16 ít chữ hơn mỗi trang nên nhanh hơn chữ 11–12).

**Thử ngay không cần code:** xuất một trang ra PNG (hoặc chụp màn hình ở 200–300 %) → tab Tạo bản vẽ → nét viền + preset Schematic + khung A4. Dự đoán sẽ thấy đúng hai lỗi: chữ thô (độ phân giải thấp) và chữ dính nhau (nối khe hở), chính là điểm 1 và 2 ở trên.

---

## 2. Định dạng bộ chữ + bộ viết chữ (lõi cho mục 3–4)

Chuẩn bị một **định dạng bộ chữ** dùng chung để sau này thay bộ chữ không phải sửa bộ viết:

- Mỗi ký tự: vài **biến thể**; mỗi biến thể là các **nét** (đường gấp khúc) đo theo chiều cao chữ (đường chân = 0, chiều cao chữ thường = 1), kèm bề rộng chữ, khoảng trống trái/phải.
- Kèm **thông số phong cách**: độ nghiêng, tỉ lệ chữ hoa / chữ thường, khoảng cách chữ / từ, độ lượn của dòng, mức lệch ngẫu nhiên.
- **Bộ viết chữ**: nhận văn bản → xếp dòng trên khổ giấy (lề, xuống dòng, căn lề) → chọn biến thể (không lặp cùng một biến thể liền nhau) → thêm lệch ngẫu nhiên nhẹ → nét → G-code như cũ.
- Thử trước bằng một font nét đơn có sẵn (thêm dấu tiếng Việt bằng cách ghép, xem mục 3).
- **Dấu tiếng Việt** ghép theo quy tắc: chữ gốc (a ă â đ ê ô ơ ư …) + 5 dấu thanh. Khó nhất là chữ chồng hai dấu (ấ ầ ẩ ẫ ậ …): dấu thanh đặt cạnh dấu mũ, không đè lên.

---

## 3. Lấy mẫu chữ tay → bộ chữ riêng

Không "học phong cách" từ một ảnh viết tự do: máy phải tự cắt và nhận ra từng chữ, với chữ tay tiếng Việt rất khó và hay sai. Thay vào đó tách hai phần:

1. **Tờ mẫu có ô kẻ**: mỗi ký tự viết 3 lần (muốn giống thật hơn thì 5–10 lần) → **hình dáng** từng chữ. Chỉ cần chữ gốc + dấu, không cần đủ 134 chữ có dấu: khoảng 80 ký tự (thường, hoa, số, dấu câu, dấu thanh) × 3 ≈ 2–3 trang A4.
2. **Một đoạn văn viết tự nhiên**: app chỉ **đo thông số chung** (độ nghiêng, cao/thấp, khoảng cách, dòng lượn) → **phong cách**.

**Cách lấy mẫu tốt nhất: viết thẳng lên màn hình cảm ứng** (điện thoại, máy tính bảng, ngón tay hoặc bút cảm ứng) ngay trong app: ghi được đúng từng nét theo thứ tự viết, sạch, không cần skeleton; máy vẽ cũng vẽ theo thứ tự đó nên tự nhiên hơn. Quét tờ giấy rồi skeleton là cách dự phòng.

Chữ nối liền (chữ thảo) khó hơn nhiều: để sau cùng, bắt đầu với chữ viết rời.

---

## 4. Viết nội dung Word bằng chữ tay

Khác mục 1: chữ tay rộng hẹp khác font gốc nên **không giữ được đúng bố cục Word**. Lấy **nội dung** (đoạn văn, tiêu đề, căn lề) từ Word/PDF rồi bộ viết chữ (mục 2) tự xếp lại trên A4.

Hai chế độ tách bạch:

| Chế độ | Nguồn | Bố cục | Kiểu chữ |
|---|---|---|---|
| In nguyên trang (mục 1) | ảnh từng trang PDF | giữ đúng | font gốc |
| Viết bằng chữ tay (mục 4) | nội dung chữ | xếp lại | bộ chữ của bạn |

**Giống viết tay thật đến đâu:** liếc qua thì giống; nhìn kỹ vẫn lộ (nét đều tuyệt đối, không vệt mực đọng, tốc độ đều nên không run, chữ rời, viết dài thì lặp biến thể). Chỉ dùng chữ của chính mình hoặc người đã đồng ý; dùng cho thiệp, thư, ghi chú, bản viết mẫu. Không dùng để nộp thay cho bài bắt buộc tự tay viết, và không làm tính năng "qua mặt người kiểm tra".

---

## 5. Gõ câu lệnh → AI tạo ảnh → bản vẽ (làm cuối)

- **Không chạy AI tạo ảnh trên MiniPC**: không card đồ họa → vài phút mỗi ảnh, 4–8 GB RAM, chất lượng tạm, có thể làm chậm việc điều khiển máy vẽ.
- **Gọi dịch vụ trên mạng** (OpenAI, Google, Stability…): nhanh, đẹp, MiniPC rất nhẹ. Cần internet, tài khoản API, **mất phí theo ảnh**; mở cho người ngoài thì phải giới hạn số lần / chi phí.
- Tự thêm vào câu lệnh kiểu "tranh nét đen trắng, không tô bóng": ảnh nét sạch vẽ đẹp hơn ảnh chụp nhiều.
- Phương án khác: AI viết thẳng hình dạng đường nét (SVG) → G-code; hợp hình đơn giản (biểu tượng, sơ đồ), không hợp tranh chi tiết.

---

## MiniPC có chịu nổi không

| Việc | Tải | Ghi chú |
|---|---|---|
| PDF → ảnh → skeleton (mục 1) | vừa | lâu hơn ảnh thường ~16 lần điểm ảnh; trong giới hạn |
| Bộ viết chữ, tạo bộ chữ (mục 2–4) | rất nhẹ | chỉ tính đường nét, không cần AI |
| AI tạo ảnh qua mạng (mục 5) | rất nhẹ | tốn phí API |
| AI tạo ảnh chạy tại chỗ | **không nên** | vài phút/ảnh, ngốn RAM |

## Các giới hạn bảo vệ đã có (không cần nới cho các tính năng trên)

| Giới hạn | Giá trị | Ở đâu |
|---|---|---|
| Cỡ tệp ảnh tải lên | 40 MB | `api/draw.py` `MAX_RASTER_BYTES` |
| Cỡ tệp SVG | 20 MB | `services/drawing/svg_in.py` `MAX_SVG_BYTES` |
| Điểm ảnh ảnh gốc | 60 triệu | `raster_in.py` `MAX_PIXELS` |
| Cạnh dài ảnh làm việc | 400–4000 px | `raster_in.py` `MIN_SIDE_PX, MAX_SIDE_PX` |
| Điểm ảnh / bề rộng bút | 1,3 | `raster_in.py` `OVERSAMPLE` (preset Văn bản sẽ đổi riêng) |
| Thời gian một lần xử lý | 600 s | `isolated.py` `DEFAULT_TIMEOUT_S` / `EXTRUXY_DRAW_TIMEOUT_S` |
| RAM tiến trình xử lý (chỉ Linux, chưa thử Ubuntu) | 4096 MB | `isolated.py` `DEFAULT_MAX_MB` / `EXTRUXY_DRAW_MAX_MB` |
| Ưu tiên thấp | `BELOW_NORMAL` / `nice 10` | `isolated.py` |
| Tổng **điểm nét** (không phải điểm ảnh; chủ yếu chặn SVG khổng lồ) | 2 triệu | `service.py` `MAX_POINTS` |
| Sắp thứ tự nét kỹ (2-opt) | ≤ 15 000 nét | `optimize.py` `TWO_OPT_MAX_STROKES` |
| Dòng G-code một tác vụ (giới hạn chạm trước trong thực tế) | 200 000 | `services/job.py` `MAX_LINES` |

Tham khảo: bản vẽ dày nhất từng tạo (~90 000 dòng G-code) mới chưa tới 5 % trần `MAX_POINTS`. Một trang A4 kín chữ ở 12 px/mm ước 200 000–300 000 điểm trước khi làm gọn, vẫn dưới trần.
