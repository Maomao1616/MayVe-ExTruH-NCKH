# FUTURE_UPGRADE_BETA — các nâng cấp để dành

Cập nhật 02/11/2026 (đã gộp `BETA.md` cũ vào đây). Danh sách ý tưởng **chưa làm và chưa xếp lịch**, để không quên. Phần làm ngay nằm ở [PLAN_ONLINE.md](PLAN_ONLINE.md) mục 2 (phân quyền khách / quản lý).

**Ký hiệu**: ✅ chủ dự án đã đồng ý ý này (nhưng chưa xếp lịch) · 💡 gợi ý của AI · ⚠ chưa kiểm chứng / chưa đo. Mọi con số thời gian là **ước lượng**, phải đo trên MiniPC thật (i5-3210M, không card đồ họa).

Bối cảnh sử dụng: bút **0,2 / 0,4 / 0,5 mm**, viết chữ dùng **0,5**; văn bản Word thường cỡ **14–16** (Arial / Times New Roman); khổ A4 (210 × 297 mm) vừa vùng vẽ 285 × 318 mm.

**Mục lục**
- Phần A — tính năng vẽ mới: 1 tab Beta PDF · 2 bộ chữ + bộ viết chữ · 3 lấy mẫu chữ tay · 4 viết Word bằng chữ tay · 5 AI tạo ảnh · 6 MiniPC có chịu nổi không
- Phần B — mở cho nhiều người: 7 tài khoản người dùng · 8 thư mục riêng · 9 hàng chờ, nét gốc · 10 màu · 11 Cloudflare nâng cao
- Phần C — việc nhỏ khác, cần đo

---

# Phần A — tính năng vẽ mới

## Cấu trúc chung: chỉ thêm "nguồn nét"
Dây chuyền hiện có: **ảnh → nét → G-code**. Phần "nét → G-code" (đặt lên giấy, nhấc/hạ bút, sắp thứ tự nét) dùng chung. Mỗi tính năng mới chỉ là một nguồn tạo nét đổ vào đó, không đụng phần đang chạy tốt:

```
PDF từ Word ──→ ảnh từng trang → skeleton ─┐
Câu lệnh    ──→ AI tạo ảnh nét ─────────────┼──→ NÉT ──→ G-code (đã có)
Mẫu chữ tay ──→ bộ chữ riêng → bộ viết chữ ─┘
```
Thứ tự nên làm: (1) tab Beta PDF → (2) bộ chữ + bộ viết chữ → (3) lấy mẫu chữ tay → (4) viết Word bằng chữ tay → (5) AI tạo ảnh.

## 1. Tab Beta: in nguyên trang PDF / Word ✅ (khả thi cao, làm trước)
*Khi nào: sau buổi đo bút (cần độ rộng nét thật của bút 0,5 để đặt preset).*

**Giao diện** (ý chủ dự án): một tab riêng tên **Beta**, chỉ có:
- Nạp tệp PDF.
- Xem trang PDF như bản in, hiện **số trang** và chọn trang.
- Vector hóa trang đang chọn → hiện ảnh nét thử.
- **Một preset mặc định cho chữ viết** (preset "Văn bản", 7 điểm bên dưới).

**Cách làm:** người dùng tự **Lưu thành PDF trong Word** (File → Save As → PDF) rồi nạp PDF; mỗi trang thành một bản thảo. Trang được kết xuất thành ảnh rồi đi qua **skeleton** (đã có trong nét viền, `services/drawing/edges.py`) → mỗi nét chữ thành một đường giữa.
- Giữ đúng font, đúng dấu tiếng Việt, đúng bố cục.
- Không tự chuyển Word → PDF trên MiniPC: LibreOffice thiếu font Arial/Times có thể làm chữ xuống dòng khác. Để Word xuất PDF là đúng nhất và MiniPC khỏi cài LibreOffice.

**Vì sao skeleton hợp với chữ 14–16 + bút 0,5:**

| Loại chữ (cỡ 14–16) | Nét chữ thật | Vẽ bằng bút 0,5 |
|---|---|---|
| Thường (Arial, Times) | ~0,45–0,55 mm | một nét ≈ y hệt bản in |
| Đậm (Bold) | ~0,8 mm | một nét hơi mảnh; muốn giống thì 2 đường sát nhau (không cần tô kín) |
| Nét mảnh của Times | ~0,15–0,2 mm | thành dày bằng nét chính (mất thanh đậm), vẫn dễ đọc |
| Lỗ chữ e, a, o | ~1 mm | còn hở, không bị bít |

Bút 0,4 gần như 0,5; bút 0,2 trông mảnh như bút kim (hợp vẽ hình chi tiết hơn).

**Preset "Văn bản" khác preset ảnh ở 7 điểm:**
1. **Độ phân giải ~10–12 điểm ảnh/mm** (ảnh thường chỉ cần khung ÷ bút × 1,3 ≈ 3–4 điểm ảnh/mm).
   - Tranh gạch lấy **độ đậm nhạt từng vùng**, chi tiết nhỏ hơn khoảng cách nét không vẽ được, nên thấp là đủ.
   - Chữ cần **vị trí đường giữa chính xác**. Chữ cỡ 14 cao ~2,6 mm (thường) / ~3,5 mm (hoa). Ở 3–4 px/mm chữ "o" chỉ ~10 px, cung bị gãy; ở 10–12 px/mm chữ "o" ~30 px, đường giữa trơn.
   - Cách làm: đổi `OVERSAMPLE` (`raster_in.py`, hiện 1,3) riêng cho preset này, khoảng 5–6. `MAX_SIDE_PX` 4000 vẫn đủ (A4 dài 297 mm → trần ~13,5 px/mm).
   - A4 ở 12 px/mm ≈ 9 triệu điểm ảnh, gấp ~16 lần ảnh thường → lâu hơn (ước vài giây đến vài chục giây/trang), không quá tải nhờ các giới hạn ở mục 6.
2. **Tắt nối khe hở** (`GAP_MM` 1,5 trong `edges.py`): khoảng cách giữa hai chữ cái chỉ ~0,5–0,8 mm, để nguyên sẽ nối dính các chữ.
3. **Cắt râu ngắn** sau skeleton (chân chữ Times để lại nhánh nhỏ).
4. **Làm mượt nét** sau skeleton (bỏ bậc thang điểm ảnh).
5. **Nét dày hơn ~1,5 lần bút** (chữ đậm, tiêu đề to): vẽ 2 đường sát nhau.
6. **Tỉ lệ 1:1**: trang A4 vẽ đúng 210 × 297 mm, không phóng/thu theo khung.
7. Chữ dưới cỡ 8 không khuyên dùng (bút 0,4–0,5 dễ bít lỗ chữ).

⚠ Bút 0,5 hiện **chưa có trong danh sách bút dựng sẵn** (`spec.py`: `PENS = (0.2, 0.4)`); vẫn gõ tay 0,5 vào ô bề rộng bút được.

**Thời gian vẽ** một trang kín chữ: ước 20–30 phút, chủ yếu do nhấc/hạ bút hàng nghìn lần.

**Thử ngay không cần code:** xuất một trang ra PNG 300 dpi (hoặc chụp màn hình ở 200–300 %) → tab Tạo bản vẽ → nét viền + preset Schematic + khung A4. Dự đoán sẽ thấy đúng hai lỗi: chữ thô (độ phân giải thấp) và chữ dính nhau (nối khe hở), chính là điểm 1 và 2.

## 2. Định dạng bộ chữ + bộ viết chữ (lõi cho mục 3–4)
Một **định dạng bộ chữ** dùng chung để sau này thay bộ chữ không phải sửa bộ viết:
- Mỗi ký tự: vài **biến thể**; mỗi biến thể là các **nét** (đường gấp khúc) đo theo chiều cao chữ (đường chân = 0, chiều cao chữ thường = 1), kèm bề rộng chữ, khoảng trống trái/phải.
- Kèm **thông số phong cách**: độ nghiêng, tỉ lệ chữ hoa / chữ thường, khoảng cách chữ / từ, độ lượn của dòng, mức lệch ngẫu nhiên.
- **Bộ viết chữ**: nhận văn bản → xếp dòng trên khổ giấy (lề, xuống dòng, căn lề) → chọn biến thể (không lặp cùng một biến thể liền nhau) → thêm lệch ngẫu nhiên nhẹ → nét → G-code như cũ.
- Thử trước bằng một font nét đơn có sẵn (thêm dấu tiếng Việt bằng cách ghép).
- **Dấu tiếng Việt** ghép theo quy tắc: chữ gốc (a ă â đ ê ô ơ ư …) + 5 dấu thanh. Khó nhất là chữ chồng hai dấu (ấ ầ ẩ ẫ ậ …): dấu thanh đặt cạnh dấu mũ, không đè lên.

## 3. Lấy mẫu chữ tay → bộ chữ riêng
Không "học phong cách" từ một ảnh viết tự do (máy phải tự cắt và nhận ra từng chữ, chữ tay tiếng Việt rất khó và hay sai). Tách hai phần:
1. **Tờ mẫu có ô kẻ**: mỗi ký tự viết 3 lần (muốn giống thật hơn thì 5–10 lần) → **hình dáng** từng chữ. Chỉ cần chữ gốc + dấu: khoảng 80 ký tự × 3 ≈ 2–3 trang A4.
2. **Một đoạn văn viết tự nhiên**: app chỉ **đo thông số chung** (độ nghiêng, cao/thấp, khoảng cách, dòng lượn) → **phong cách**.

**Cách lấy mẫu tốt nhất: viết thẳng lên màn hình cảm ứng** (điện thoại, máy tính bảng) ngay trong app: ghi đúng từng nét theo thứ tự viết, sạch, không cần skeleton; máy vẽ cũng vẽ theo thứ tự đó nên tự nhiên hơn. Quét giấy rồi skeleton là cách dự phòng. Chữ nối liền (chữ thảo) để sau cùng.

## 4. Viết nội dung Word bằng chữ tay
Chữ tay rộng hẹp khác font gốc nên **không giữ được đúng bố cục Word**. Lấy **nội dung** (đoạn văn, tiêu đề, căn lề) rồi bộ viết chữ (mục 2) tự xếp lại trên A4.

| Chế độ | Nguồn | Bố cục | Kiểu chữ |
|---|---|---|---|
| In nguyên trang (mục 1) | ảnh từng trang PDF | giữ đúng | font gốc |
| Viết bằng chữ tay (mục 4) | nội dung chữ | xếp lại | bộ chữ của bạn |

**Giống viết tay thật đến đâu:** liếc qua thì giống; nhìn kỹ vẫn lộ (nét đều tuyệt đối, không vệt mực đọng, chữ rời, viết dài thì lặp biến thể). Chỉ dùng chữ của chính mình hoặc người đã đồng ý; dùng cho thiệp, thư, ghi chú, bản viết mẫu. Không dùng để nộp thay cho bài bắt buộc tự tay viết, và không làm tính năng "qua mặt người kiểm tra".

## 5. Gõ câu lệnh → AI tạo ảnh → bản vẽ (làm cuối)
- **Không chạy AI tạo ảnh trên MiniPC**: không card đồ họa → vài phút mỗi ảnh, 4–8 GB RAM, có thể làm chậm việc điều khiển máy vẽ.
- **Gọi dịch vụ trên mạng**: nhanh, đẹp, MiniPC rất nhẹ. Cần internet, tài khoản API, **mất phí theo ảnh**; mở cho người ngoài thì phải giới hạn số lần / chi phí.
- Tự thêm vào câu lệnh kiểu "tranh nét đen trắng, không tô bóng": ảnh nét sạch vẽ đẹp hơn ảnh chụp nhiều.
- Phương án khác: AI viết thẳng hình dạng đường nét (SVG) → G-code; hợp hình đơn giản (biểu tượng, sơ đồ).

## 6. MiniPC có chịu nổi không

| Việc | Tải | Ghi chú |
|---|---|---|
| PDF → ảnh → skeleton (mục 1) | vừa | ~16 lần điểm ảnh so với ảnh thường; trong giới hạn |
| Bộ viết chữ, tạo bộ chữ (mục 2–4) | rất nhẹ | chỉ tính đường nét |
| AI tạo ảnh qua mạng (mục 5) | rất nhẹ | tốn phí API |
| AI tạo ảnh chạy tại chỗ | **không nên** | vài phút/ảnh, ngốn RAM |

**Các giới hạn bảo vệ đã có** (không cần nới cho các tính năng trên):

| Giới hạn | Giá trị | Ở đâu |
|---|---|---|
| Cỡ tệp ảnh tải lên | 40 MB | `api/draw.py` `MAX_RASTER_BYTES` |
| Cỡ tệp SVG | 20 MB | `services/drawing/svg_in.py` `MAX_SVG_BYTES` |
| Điểm ảnh ảnh gốc | 60 triệu | `raster_in.py` `MAX_PIXELS` |
| Cạnh dài ảnh làm việc | 400–4000 px | `raster_in.py` `MIN_SIDE_PX, MAX_SIDE_PX` |
| Điểm ảnh / bề rộng bút | 1,3 | `raster_in.py` `OVERSAMPLE` (preset Văn bản sẽ đổi riêng) |
| Thời gian một lần xử lý | 600 s | `isolated.py` `DEFAULT_TIMEOUT_S` / `EXTRUXY_DRAW_TIMEOUT_S` |
| RAM tiến trình xử lý (chỉ Linux) | 4096 MB | `isolated.py` `DEFAULT_MAX_MB` / `EXTRUXY_DRAW_MAX_MB` |
| Ưu tiên thấp | `BELOW_NORMAL` / `nice 10` | `isolated.py` |
| Tổng **điểm nét** (không phải điểm ảnh) | 2 triệu | `service.py` `MAX_POINTS` |
| Sắp thứ tự nét kỹ (2-opt) | ≤ 15 000 nét | `optimize.py` `TWO_OPT_MAX_STROKES` |
| Dòng G-code một tác vụ | 200 000 | `services/job.py` `MAX_LINES` |

Bản vẽ dày nhất từng tạo (~90 000 dòng G-code) mới chưa tới 5 % trần `MAX_POINTS`. Một trang A4 kín chữ ở 12 px/mm ước 200 000–300 000 điểm trước khi làm gọn, vẫn dưới trần.

---

# Phần B — mở cho nhiều người (sau bản khách + quản lý)

## 7. Tài khoản "người dùng"
*Khi nào: khi khách cần tự tạo nét / tự lưu bản thảo thay vì chỉ gửi ảnh.*
- Đăng ký chỉ **tên đăng nhập + mật khẩu**, bỏ email, không cần duyệt. ✅
- Form đăng ký **không bao giờ** tạo ra quản lý. Mỗi trình duyệt một cookie phiên riêng. ✅
- 💡 Mật khẩu băm bằng `hashlib.scrypt` (thư viện chuẩn), không lưu nguyên văn.
- 💡 Giới hạn nhập sai theo tài khoản (qua Cloudflare mọi yêu cầu đến từ 127.0.0.1; IP thật ở header `CF-Connecting-IP`, ⚠ chưa thử).
- 💡 Mã tài khoản tự sinh, không dùng tên đăng nhập làm tên thư mục.

## 8. Thư mục riêng theo tài khoản
- Mỗi tài khoản một thư mục, người này không xem được của người kia; quản lý xem hết. ✅
- 💡 Quản lý giữ các thư mục cũ (`drafts/`, …) nguyên vẹn; người thường nằm ở thư mục con theo mã tài khoản.
- Giữ tối đa **3 ngày** cho tài khoản thường; thư mục quản lý không áp giới hạn. ✅
- 💡 Nút **ghim** của quản lý; bản đang chờ quản lý chạy máy không bị xóa.
- 💡 Hạn mức dung lượng áp cả cho quản lý. ⚠ Chưa biết cơ chế tự dọn hiện tại của `drafts.py` dựa vào số lượng hay dung lượng.
- `/api/storage`, `preview.svg`, `gcode/{layer_file}` đều phải kiểm chủ.

## 9. Người dùng tự tạo nét trên máy chủ (hàng chờ)
*Chỉ cần khi nhiều người cùng tạo nét. Quản lý một mình thì giữ cách tự tạo nét như hiện tại.*

**Tách "nạp ảnh" khỏi "tạo nét"** ✅
Hiện nạp ảnh tự gọi vector hóa ở 4 chỗ trong `frontend/js/views/drawing.js`: chọn tệp (`:129`), áp vùng cắt (`:58`), đổi preset (`:294`), kéo khung lệch >12% (`:282`). Backend chỉ có một cửa `POST /api/draw/import` vừa nhận ảnh vừa tạo nét (`api/draw.py:118`). Với người dùng thường: chỉ tạo nét khi bấm **"Tạo vector"**; tắt tự tạo lại khi kéo khung.

**Hàng chờ (làn nặng)** ✅ theo thứ tự đến, một việc một lúc, nhãn chủ việc, khách đóng tab việc vẫn chạy và tự lưu vào thư mục chủ.
- Sửa `tasks.py:64-70`: bỏ hành vi **việc mới hủy việc cũ**; mỗi người chỉ hủy việc của mình, quản lý hủy được mọi việc.
- 💡 Mỗi người tối đa một việc đang chờ; hàng có trần; hiện vị trí trong hàng và ước tính thời gian.
- 💡 Ảnh không giữ trong RAM theo hàng chờ: lưu ra thư mục tài khoản, xóa sau khi xong.
- Hàng chờ trong RAM → khởi động lại là mất, báo người gửi gửi lại.
- `idle.py`: phải tính cả việc đang chờ / đang chạy, kẻo server tự tắt khi khách đóng tab.

**Làn nhẹ, nét gốc, dấu vân tay** ✅
- Ba tầng: A vector hóa (nặng, qua hàng chờ) · B bố trí (nhẹ, phần lớn tính ở trình duyệt `lib/paper.js`) · C G-code (nhẹ).
- **Làn nhẹ** (đổi bố trí + tạo lại G-code từ nét đã lưu) chạy ngay, không xếp hàng chung. 💡 Tối đa 1–2 việc cùng lúc. ⚠ Chưa đo có làm trễ luồng gửi G-code không; nếu có thì hoãn làn nhẹ khi máy đang chạy.
- **Lưu nét gốc** `strokes.json` cạnh `meta.json` trong thư mục bản thảo (hiện nét chỉ nằm trong RAM, `store.py`, 3 việc gần nhất). Không dùng pickle trong thư mục người dùng. ⚠ Ước tính 2–5 MB mỗi bản.
- 💡 `spec.py` gắn **nhóm** cho từng tham số: *Vector* (vùng cắt, sáng/tương phản, kiểu tô, khoảng gạch, bút, góc, số màu, khung lệch >12%) và *Bố trí* (xoay, lật, căn, lề, vị trí).
- 💡 **Dấu vân tay** = băm (ảnh + vùng cắt + tham số nhóm Vector). Giống → làn nhẹ; khác → báo "nét đã cũ".
- Cảnh báo: biểu tượng "nét đã cũ", nút "Tạo lại" kèm "đang có N việc trước", ghi rõ chỉnh sáng/tương phản cũng phải vector lại, việc đã vào hàng giữ bản sao tham số lúc bấm.

## 10. Màu cho người thường
- Người thường chỉ xám; chia 2–4 màu (`palette.py`) **khóa ở backend**, không chỉ ẩn ô nhập. ✅
- Muốn ảnh màu thì ghi chú nhờ quản lý (bản khách gửi ảnh đã có ô ghi chú). ✅

## 11. Cloudflare nâng cao
- 💡 Cloudflare Access làm thêm một lớp đăng nhập phía ngoài (kiểm điều kiện gói hiện hành).
- 💡 Giới hạn tần suất theo `CF-Connecting-IP` thay cho giới hạn chung cả máy.
- 💡 Trần kích thước yêu cầu theo vai trò thay cho `MAX_BODY_BYTES = 64 MB` chung.

---

# Phần C — việc nhỏ khác, cần đo

## 12. Việc nhỏ
- 💡 Thêm 0,5 vào bút dựng sẵn (`spec.py` `PENS`).
- 💡 Vệt bút theo dòng G-code cho cả macro / tiếp tục tác vụ (hiện chỉ áp cho tệp đang nạp; jog / macro / resume vẫn nối điểm tọa độ).
- 💡 `.devcontainer/` cho GitHub Codespaces: chốt Python 3.12 và tự `pip install`.
- 💡 Đổi mật khẩu quản lý trên giao diện (bản đầu chỉ đặt bằng biến môi trường).
- 💡 Mã QR địa chỉ LAN trên giao diện để điện thoại quét vào nhanh.
- 💡 (Tùy chọn) 2-opt trong Web Worker, chỉ khi đo trên MiniPC thấy bước sắp xếp nét lâu (DECISIONS O3).

## 13. Cần đo trên MiniPC trước khi quyết
| Việc | Cách |
|---|---|
| Một lần vector hóa mất bao lâu, khởi động tiến trình con chiếm bao nhiêu | `info.timings`, ảnh nhỏ và ảnh lớn |
| Đỉnh RAM tiến trình con (ảnh 4000 px, 4 màu) | `htop`; trần `EXTRUXY_DRAW_MAX_MB` chỉ có ở Linux |
| Bố trí + G-code ca lớn nhất (200 000 dòng) có làm trễ luồng gửi dòng khi máy đang chạy không | Máy giả hoặc máy thật đang vẽ |
| Kích thước thật của `strokes.json` | Vài ảnh mẫu |
| Hạn mức hợp lý: cỡ tệp, số việc chờ, trần thời gian | Đặt sau khi có số đo |
