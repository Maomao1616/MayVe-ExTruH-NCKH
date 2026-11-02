# FUTURE_UPGRADE_BETA — các nâng cấp để dành

Cập nhật 02/11/2026 (đã gộp `BETA.md` cũ vào đây). Danh sách ý tưởng **chưa làm và chưa xếp lịch**, để không quên. Phần làm ngay nằm ở [PLAN_ONLINE.md](PLAN_ONLINE.md) mục 2 (phân quyền khách / quản lý).

**Ký hiệu**: ✅ chủ dự án đã đồng ý ý này (nhưng chưa xếp lịch) · 💡 gợi ý của AI · ⚠ chưa kiểm chứng / chưa đo. Mọi con số thời gian là **ước lượng**, phải đo trên MiniPC thật (i5-3210M, không card đồ họa).

Bối cảnh sử dụng: bút **0,2 / 0,4 / 0,5 mm**, viết chữ dùng **0,5**; văn bản Word thường cỡ **14–16** (Arial / Times New Roman); khổ A4 (210 × 297 mm) vừa vùng vẽ 285 × 318 mm.

**Mục lục**
- Phần A — tính năng vẽ mới: 1 tab Beta PDF · 2 bộ chữ + bộ viết chữ · 3 lấy mẫu chữ tay · 4 viết Word bằng chữ tay · 5 AI tạo ảnh · 6 MiniPC có chịu nổi không
- Phần B — mở cho nhiều người: 7 tài khoản người dùng · 8 thư mục riêng · 9 hàng chờ, nét gốc · 10 màu · 11 Cloudflare nâng cao
- Phần C — việc nhỏ khác, cần đo
- Phần D — hướng nghiên cứu thêm (thư viện + điện tử / IoT, kèm từ khóa tìm): 14 chữ PDF / nét đơn · 15 ảnh → nét đơn · 16 chọn theo phần cứng · 17 điện tử / IoT · 18 lời khuyên đã kiểm là sai · 19–20 (chuyển sang 21) · **21 áp vào phần cứng thật: tốc độ, bút, điện tử, chân trống, ESP32-S3, tính năng mới, thứ tự làm**

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

---

# Phần D — hướng nghiên cứu thêm (ghi 02/11/2026, chưa làm)

Chỉ là hướng đi + từ khóa để tự tìm; chưa thử thư viện nào trong dự án. Từ khóa để tiếng Anh vì tìm dễ ra hơn. Nguyên tắc chung: **không sửa firmware FluidNC**; đóng góp của đề tài nằm ở cách ghép dây chuyền, tối ưu cho phần cứng yếu, phần cứng bên ngoài và **số đo trước / sau**.

## 14. Nâng cấp dây chuyền chữ PDF / nét đơn
Dây chuyền: PDF → ảnh trang → tách nền → skeleton → tỉa râu → làm mượt → vpype → G-code.

| Bước | Thư viện / cách | Được gì | Từ khóa tìm |
|---|---|---|---|
| Kết xuất trang | `pypdfium2` (Apache/BSD) hoặc PyMuPDF (AGPL; làm đề tài thì được, bán phần mềm thì cân nhắc) | PDF → ảnh đúng DPI | `pypdfium2 render page`, `PyMuPDF get_pixmap dpi` |
| Bố cục từng ký tự | PyMuPDF `get_text("rawdict")`: từng ký tự + hộp bao + điểm đặt; font / cỡ chữ theo cụm chữ | Biết dòng nào đậm / tiêu đề → vẽ 2 đường; tách chữ khỏi hình, bảng; dùng lại cho chế độ chữ tay | `PyMuPDF rawdict chars origin bbox` |
| Phân vùng trang theo cấu trúc PDF | PyMuPDF `get_text("dict")` (khối chữ / khối ảnh), `get_drawings()` (đường kẻ bảng, gạch dưới, gạch phân số, căn thức) | PDF xuất từ Word có sẵn cấu trúc: chữ → skeleton; **đường kẻ → vẽ thẳng bằng vector** (chính xác tuyệt đối); ảnh trong trang → dây chuyền tô hiện có | `PyMuPDF get_drawings`, `PyMuPDF get_text dict blocks image` |
| Hai bút trên một trang | Lớp chữ (bút bi 0,5) + lớp tranh (Sakura 0,4) thành 2 tệp G-code, đổi bút giữa chừng | Dùng lại cơ chế đa màu (mỗi lớp một tệp) | |
| Tách chữ khỏi nền | `skimage.filters.threshold_sauvola` | Chỉ cần với PDF quét; PDF xuất từ Word thì ngưỡng thường là đủ | `Sauvola thresholding document binarization` |
| Skeleton + độ dày nét | `skeletonize(method="lee")`, `thin`, `medial_axis` (trả khoảng cách tới mép) | Tự đo độ dày nét từng điểm → tự phát hiện chữ đậm | `medial axis transform stroke width`, `Zhang-Suen thinning` |
| Tỉa râu | `skan` (skeleton → đồ thị, đầu mút / ngã ba) + tự cắt nhánh cụt ngắn | Bỏ râu chân chữ Times | `skeleton spur pruning`, `skan skeleton branch` |
| Làm mượt | `scipy.signal.savgol_filter`, `scipy.interpolate.splprep`, Chaikin | Bỏ bậc thang điểm ảnh | `Savitzky-Golay polyline smoothing`, `Chaikin curve smoothing` |
| Đường giữa từ vector (không qua ảnh) | Inkscape `--export-text-to-path` → thư viện `centerline` (Voronoi, Shapely) | Chính xác, không phụ thuộc độ phân giải. ⚠ râu ở góc nhọn, chậm hơn | `polygon centerline voronoi`, `straight skeleton glyph`, `font stroke extraction` |
| Dọn nét trùng | plugin `deduplicate` của vpype | Xóa đoạn vẽ chồng (`linemerge` không làm được) | `vpype deduplicate` |
| Gộp đoạn thành cung | ArcWelderLib (C++, dòng lệnh): chuỗi `G1` → `G2/G3` | Ít dòng G-code → bớt tải USB, chạy liền hơn. ⚠ `G2/G3` chưa thử máy thật (MACHINE B4) | `ArcWelder arc fitting gcode`, `gcode G2 G3 compression` |
| Đo chất lượng | `pytesseract` (gói `vie`) hoặc EasyOCR trên **ảnh chụp tờ đã vẽ** | Số "% ký tự đọc đúng" so với chữ gốc, đưa vào báo cáo | `character error rate OCR`, `tesseract vie traineddata` |

Font nét đơn có dấu tiếng Việt: chưa tìm thấy bộ nào có sẵn → tự ghép dấu (mục 2). Từ khóa: `single line font`, `stroke font`, `Hershey text Inkscape`, `NextDraw stroke font`.

## 15. Nâng cấp ảnh → nét đơn (tranh tô màu, hoạt hình)
Đang có: bilateral + Canny + top-hat + skeleton + nối khe hở (`edges.py`).

| Hướng | Thư viện / cách | Từ khóa tìm |
|---|---|---|
| Phẳng màu trước khi tìm viền | `cv2.pyrMeanShiftFiltering`, `skimage.segmentation.slic` / `felzenszwalb` | `mean shift filtering cartoon`, `SLIC superpixels` |
| Viền kiểu nét vẽ tay | XDoG (tự viết bằng OpenCV) | `XDoG extended difference of gaussians` |
| AI nhẹ tìm viền | TEED (~58 nghìn tham số, ICCV 2023), PiDiNet, HED; chạy qua `cv2.dnn` hoặc onnxruntime | `TEED edge detection`, `PiDiNet`, `HED opencv dnn` |
| AI ảnh chụp → tranh nét | Informative Drawings (CVPR 2022, ONNX ~8,6 MB, MIT). ⚠ chạy CPU chậm, đo trên i5-3210M trước | `informative drawings onnx`, `photo to line drawing` |
| AI hoạt hình → nét | Anime2Sketch (MIT, chỉ có PyTorch ~218 MB, phải tự chuyển ONNX) | `Anime2Sketch` |
| Dò đường giữa khác để so | `autotrace --centerline` | `autotrace centerline` |

## 16. Chọn theo phần cứng
| Mức | Gồm | Hợp với |
|---|---|---|
| Nhẹ | Dây chuyền hiện tại | MiniPC vừa điều khiển vừa xử lý |
| **Vừa** (nên làm trước) | + Sauvola, `medial_axis`, skan, làm mượt, `deduplicate` (chỉ numpy / scipy, gần như không thêm RAM) | MiniPC i5-3210M |
| Nặng | + mô hình ONNX, đường giữa từ vector | Laptop, hoặc chỉ chạy khi máy vẽ rảnh |
| Tách máy | Laptop xử lý ảnh → gửi bản thảo sang MiniPC | MiniPC chỉ lo điều khiển |

## 17. Hướng điện tử / IoT (không sửa firmware)
| # | Hướng | Làm gì | Từ khóa tìm |
|---|---|---|---|
| 1 | Cách gửi G-code | So "gửi một dòng chờ `ok`" (đang dùng) với "đếm ký tự" (lấp bộ đệm nhận). Vẽ biểu đồ trường `Bf:` (bộ đệm) theo thời gian để thấy chỗ máy "đói lệnh". ⚠ Chưa rõ cỡ bộ đệm nhận của FluidNC | `grbl character counting streaming`, `grbl planner buffer starvation`, `FluidNC serial buffer` |
| 2 | Tinh chỉnh cấu hình | Gia tốc, `junction_deviation`, tốc độ tối đa, vi bước → bảng thời gian vẽ / chất lượng nét (sửa qua tab Cài đặt, không code) | `grbl junction deviation`, `FluidNC acceleration_mm_per_sec2` |
| 3 | Bút servo | Đo thời gian nhấc / hạ thật (~0,7 s mỗi nét theo cấu hình thật, chi phí lớn nhất; xem 21.1), giảm độ cao nhấc Z, chỉnh thời gian chờ, thử servo nhanh hơn; đo xung bằng máy hiện sóng / logic analyzer | `servo response time measurement`, `pen plotter servo lift delay`, `FluidNC RcServo` |
| 4 | Driver động cơ bước | A4988 so với TMC2209 chạy độc lập (êm, mượt), chỉnh dòng Vref, đo nhiệt. ⚠ Cần sơ đồ chân / jumper của DLC32 V2.1 | `TMC2209 standalone StealthChop`, `A4988 Vref current`, `MKS DLC32 V2.1 schematic` |
| 5 | An toàn phần cứng | FluidNC không hỗ trợ trực tiếp nút dừng khẩn cấp → nút **cắt nguồn 12 V** + nút cứng Tạm dừng / Tiếp tục qua `feed_hold_pin`, `cycle_start_pin`, `safety_door_pin`, `macro0..3_pin` | `FluidNC E-Stop Button wiki`, `FluidNC control pins` |
| 6 | Camera | Mã ArUco ở góc bàn → tự tìm vị trí giấy, tự đặt Zero; chụp tờ đã vẽ → so với xem trước bằng SSIM + OCR (mục 14) | `OpenCV ArUco`, `homography paper detection`, `SSIM structural similarity` |
| 7 | Giám sát, thông báo | MQTT lên bảng theo dõi hoặc bot Telegram báo "vẽ xong / lỗi"; ESP32 riêng (không đụng MKS) đo điện năng mỗi bản vẽ | `paho-mqtt`, `Mosquitto`, `Telegram bot sendMessage`, `INA219 ESP32`, `PZEM-004T` |
| 8 | So đường truyền | Độ trễ, độ ổn định USB so với Wi-Fi (telnet / WebSocket của FluidNC); ghi lý do chọn USB (Wi-Fi vượt qua khóa của phần mềm) | `FluidNC telnet websocket`, `serial latency measurement` |
| 9 | Truy cập từ xa có phân quyền | Đã có thiết kế: `PLAN_ONLINE.md` | `Cloudflare Tunnel` |

## 18. Lời khuyên đã kiểm là sai (từ một tư vấn AI khác, 02/11/2026): đừng làm theo
- "`pdftocairo -svg` giữ chữ trong thẻ `<text>` kèm tọa độ": không có tài liệu xác nhận; có người dùng báo SVG ra **không thấy chữ**. Muốn tọa độ chữ thì đọc thẳng PDF (`rawdict`, mục 14).
- "`vpype-text` tự ép font Hershey tiếng Việt": plugin **đã ngừng phát triển**, không xuống dòng; Hershey không có dấu tiếng Việt.
- "`findContours` trên nét 1 điểm ảnh": dò đường bao nên ra **hai đường**; dùng dò theo đồ thị như `trace.py`.
- "`potrace` vector hóa nét mượt": cũng ra nét đôi; đã bỏ (DRAW_ROADMAP mục 6).
- "`docx2pdf`": cần Word cài trên máy; MiniPC Ubuntu không có → người dùng tự xuất PDF.

## 19. Chọn trước cho đề tài
Đã thay bằng **21.8** (xếp lại theo phần cứng thật, mục tiêu: sản phẩm thật, máy vẽ tích hợp IoT, càng tối ưu càng tốt; báo cáo để sau).

## 20. Thông tin phần cứng
Đã có: `MACHINE.md` mục C (servo, driver, nguồn, đai, bút, cấu hình đọc từ mạch). **Còn thiếu**: mã động cơ bước + dòng định mức; kiểu giá bút (lò xo hay để bút tự nặng); hãng module TMC2209 (để tính đúng dòng từ Vref).

## 21. Áp vào phần cứng thật (ghi 02/11/2026)
Số hiện tại lấy từ `MACHINE.md` mục C. Mọi con số "ước được" là **tính tay, chưa đo**.

### 21.1 Những thông số làm máy nhanh lên (thử bằng KIEM_TRA_VE mục 7, không cần code)
| Thông số | Hiện tại | Thử | Ghi chú |
|---|---|---|---|
| Thời gian chờ sau nhấc / hạ (`delay_up_s`, `delay_down_s`) | 0,2 / 0,2 s | 0,1 → 0,05 s | Servo chỉ cần ~0,1 s cho cả 54°. Bút bi cần chạm giấy trước khi đi → giữ thời gian chờ sau khi hạ nhỉnh hơn |
| Độ cao nhấc (Z bút lên) | Z5 | Z3 → Z2 | Miễn là bút không quẹt giấy khi di chuyển; nhấc thấp hơn thì nhanh hơn và va giấy nhẹ hơn |
| Gia tốc Z | 1000 mm/s² | 2000–3000 | Z là trục ảo của servo; giới hạn thật là tốc độ servo |
| Điện áp servo | 5 V | 6 V (vặn XL4005; **không vượt 6 V**, đo khi servo đang chạy) | Nhanh hơn ~17 % (0,12 → 0,10 s/60°), khỏe hơn |
| Gia tốc X / Y | 600 mm/s² | 1000 → 1500 → 2000 | Chữ toàn đoạn ngắn nên gia tốc quyết định tốc độ thật. Soi gợn sóng sau góc chữ, kiểm mất bước |
| `junction_deviation_mm` | 0,01 | 0,02–0,05 | Qua góc nhanh hơn; độ bo góc nhỏ hơn nét bút rất nhiều |
| `planner_blocks` | 16 | 32 ⚠ | Chỉ có ích nếu lệnh gửi đủ nhanh (mục 17 hướng 1); ⚠ kiểm giới hạn RAM của FluidNC |
| Tốc độ di chuyển không vẽ | 6000 mm/min | cao hơn | Chỉ sau khi qua bài thử mất bước |

**Ước một trang chữ A4 cỡ 14** (⚠ rất thô): khoảng 2000 ký tự × ~2,5 nét (dấu tiếng Việt là nét riêng) ≈ **5000 lần nhấc bút**.

| | Nhấc / hạ bút | Vẽ + di chuyển | Tổng |
|---|---|---|---|
| Cấu hình hiện tại (~0,7 s mỗi nét, gia tốc 600) | ~58 phút | ~25 phút | **~80 phút** |
| Sau tối ưu (~0,25 s mỗi nét, gia tốc 2000) | ~21 phút | ~14 phút | **~35 phút** |

→ Với chữ, **nhấc bút là đòn bẩy lớn nhất**. Ước tính 20–30 phút ở mục 1 là lạc quan. Phần mềm đã hiện "số lần nhấc bút" và thời gian ước tính của từng bản vẽ: đo thật một đoạn chữ để chỉnh lại bảng này.

### 21.2 Bút
- Cơ cấu của bạn **hạ bút bằng trọng lực** (MACHINE C1): lực xuống giấy là trọng lượng cụm bút, không phải servo ép. Vậy ngòi hỏng chủ yếu do **bút rơi nhanh rồi nảy / va** lúc servo rút, ít do chạy nhanh. Giảm va: servo rút **chậm** ở đoạn cuối (tách "tốc độ hạ bút" khỏi `pen_feed`, sửa code nhỏ), cụm bút dẫn hướng trơn (không kẹt), khối nặng vừa đủ. Làm vậy có thể dùng lại bút 0,2 cho chi tiết. ⚠ Thử.
- Nhấc (servo đẩy lên) có thể nhanh; hạ (bút rơi) bị giới hạn bởi tốc độ servo rút và độ trơn của dẫn hướng → hai thời gian chờ `delay_up_s` / `delay_down_s` nên **chỉnh riêng**, thường chờ sau khi hạ lâu hơn chờ sau khi nhấc.
- Chạy nhanh quá thì mực có thể không kịp ra (nét nhạt / đứt) → tìm tốc độ vẽ cao nhất cho từng bút (KIEM_TRA_VE 7.4).
- Bút bi cần lực đè đều và hay hụt mực ở đầu nét → chỉnh bằng **khối nặng** của cụm bút; không giảm thời gian chờ sau khi hạ về 0.

### 21.3 Điện tử
- Servo 6 V (21.1). Tụ 470–1000 µF sát servo; GND của XL4005 nối chung với MKS.
- Thêm ESP32 thì dùng **hạ áp 5 V riêng** cho mạch logic: servo giật dòng có thể làm ESP32 khởi động lại.
- Dòng động cơ ~0,92 A RMS (R100, Vref 1,2 V) là đủ cho máy vẽ nhẹ; 17HS4401 định mức ~1,5–1,7 A. Muốn chạy nhanh hơn thì tăng dần Vref (1,2 → 1,4 → 1,57 V ≈ 1,2 A RMS) kèm bài thử mất bước (KIEM_TRA_VE 7.2); TMC2209 cần tản nhiệt; đo nhiệt động cơ và driver.
- 💡 Nguồn 24 V: với cùng driver, mô-men ở tốc độ cao tốt hơn hẳn; DLC32 nhận 12–24 V, XL4005 nhận tới ~32 V. ⚠ Kiểm quạt / thiết bị 12 V khác; phải mua nguồn mới.
- ⚠ TMC2209 chạy độc lập mặc định StealthChop (êm) nhưng yếu hơn ở tốc độ cao; SpreadCycle khỏe hơn. Tùy module có chân / jumper để chọn.

### 21.4 Dùng chân trống của MKS (chỉ sửa YAML + nối dây, không sửa firmware)
- `feed_hold_pin` + `cycle_start_pin`: **2 nút cứng Tạm dừng / Chạy tiếp** trên máy, vẫn chạy khi mất mạng.
- **Cảm biến bút** (công tắc nhỏ, hoặc cảm biến Hall + nam châm trên giá bút) nối vào `probe` (`gpio.22`): báo cáo trạng thái có `Pn:P` → phần mềm biết **bút thật sự đã nhấc** (hiện chỉ biết lệnh Z), thêm đèn "Bút" cạnh đèn X/Y, dừng khi bút kẹt. Phần mềm đã đọc `Pn` sẵn.
- Dừng khẩn cấp thật = nút **cắt nguồn 12 V** (không qua phần mềm).
- ⚠ `gpio.34–39` chỉ đọc vào và không có điện trở kéo lên bên trong → cần kéo lên ngoài (đầu limit trên mạch có thể đã có). Dò chân bằng sơ đồ mạch trước (MACHINE C2).

### 21.5 ESP32-S3: các nút mạng riêng (không đụng MKS)
| Nút | Làm gì | Từ khóa |
|---|---|---|
| Bảng điều khiển không dây | Màn OLED / TFT + 3 nút + còi + LED: trạng thái, % tiến độ, tạm dừng / chạy tiếp qua API (cần "mã thiết bị" sau khi có đăng nhập). Nút an toàn vẫn phải là nút cứng nối dây | `ESP32-S3 OLED HTTP client`, `WS2812 status LED` |
| Đo điện năng | INA226 (hoặc INA219, chú ý trần dòng của điện trở đo) trên dây 12 V → Wh mỗi bản vẽ, hiện cạnh thời gian vẽ | `INA226 ESP32`, `energy per job` |
| Nhiệt độ | DS18B20 trên driver / động cơ → cảnh báo khi tăng dòng | `DS18B20 ESP32` |
| Camera xem trực tiếp | ESP32-S3 + OV2640, MJPEG 640×480 (hướng dẫn nói ~10–15 khung/s, ⚠ đo); backend chuyển tiếp để xem được qua tunnel | `ESP32-S3 CameraWebServer MJPEG` |
| Giao tiếp | MQTT với Mosquitto chạy trên MiniPC / laptop (chạy được khi không có Internet), hoặc HTTP đơn giản | `paho-mqtt`, `Mosquitto`, `PubSubClient` |

Chụp ảnh tờ đã vẽ (để đo SSIM / OCR) khi chưa có webcam: dùng **camera điện thoại qua nút tải ảnh** của giao diện (chạy được trên http, không cần HTTPS như khi mở camera trực tiếp).

### 21.6 Tính năng phần mềm mới (đóng góp riêng của đề tài)
- **Ghi số liệu tác vụ**: mỗi 0,1 s lưu giờ, trạng thái, vị trí, tốc độ thật (`FS:`), bộ đệm (`Bf:`) ra CSV + biểu đồ → thấy chỗ chậm, chỗ máy "đói lệnh", so thời gian thật với ước tính, tự chỉnh hệ số ước tính. Mọi số đo khác dựa vào cái này.
- **Hồ sơ tốc độ theo loại bản vẽ** (Chữ / Tranh / Đẹp nhất): đổi gia tốc, junction, tốc độ, thời gian chờ trước khi chạy (áp trong RAM như nút Áp dụng hiện có, xong trả lại).
- **Trình hiệu chỉnh nhấc bút**: vẽ một hàng gạch ngắn với nhiều thời gian chờ khác nhau, người dùng chọn hàng đẹp nhất → lưu vào hồ sơ.
- **Trang PDF hai bút** + **phân vùng trang theo cấu trúc PDF** (mục 14).
- **Bộ demo không mạng**: Wi-Fi riêng, IP cố định + QR, tắt Wi-Fi của MKS (PLAN_ONLINE 3.1).

### 21.7 Demo
Không có mạng dây / Wi-Fi → tự phát. Ưu tiên router du lịch hoặc router 4G bỏ túi; chi tiết và các cách khác: `PLAN_ONLINE.md` mục 3.1.

### 21.8 Thứ tự đề xuất
1. **Bài thử tốc độ** (KIEM_TRA_VE mục 7): nhấc bút, gia tốc, mất bước, tốc độ bút. Không cần code.
2. **Ghi số liệu tác vụ** (code nhỏ; mọi số đo sau dùng nó).
3. **Đăng nhập quản lý** (PLAN_ONLINE mục 2) trước khi cho người xem vào Wi-Fi demo.
4. **Hai nút cứng + cảm biến bút** qua chân trống (YAML + nối dây) + tách tốc độ hạ bút.
5. **Tab Beta PDF**: chữ + đường kẻ vector + hai bút.
6. **ESP32-S3**: chọn 1–2 nút (bảng điều khiển, điện năng, camera).
7. Hồ sơ tốc độ, trình hiệu chỉnh nhấc bút, khách gửi ảnh, Cloudflare.
