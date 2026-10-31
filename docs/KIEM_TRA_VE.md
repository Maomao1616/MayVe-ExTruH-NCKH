# KIEM_TRA_VE — cách thử và tinh chỉnh các chế độ vẽ

Dành cho người vận hành máy vẽ (không cần lập trình). Mục tiêu: chốt các con số mặc định (khoảng cách nét, số mức, gamma, preset) **bằng bản in thật**, vì màn hình không cho biết mực loang, giấy thấm, bút khô ra sao.
Ký hiệu: ✅ đã chốt bằng bản in · 🧪 mới thử bằng ảnh mẫu trên máy tính.

## 0. Nguyên tắc
- **Mọi bước đều phải vẽ thật lên giấy.** Khung xem trước trên web chỉ dùng để kiểm tra hình học trước khi vẽ (nét đủ, đúng chỗ, đúng số dải / số bậc, không vượt khổ), đỡ phí giấy. Web **không** cho biết độ đậm thật: trên màn hình nét nào cũng mảnh như nhau, còn trên giấy mực loang, giấy thấm, bút đậm nhạt khác nhau. Các quyết định "dải nào xám vừa", "bậc nào tách rõ" chỉ làm được khi nhìn tờ giấy.
- **Mỗi lần chỉ đổi một thông số.** Cùng loại giấy, cùng cây bút, cùng tốc độ vẽ.
- **Ghi số ngay góc tờ giấy** (bút, khoảng cách, số mức, gamma, preset, ngày) rồi chụp ảnh tờ giấy để so về sau.
- Làm theo thứ tự dưới đây: bước trước chốt con số mà bước sau dùng. Bút 0,2 và 0,4 làm riêng.
- Ghi kết quả vào bảng ở mục 6.

## 1. Khoảng cách nét theo bút: tờ mẫu hiệu chỉnh bút
Đã in và lưu lại (ảnh chụp tờ mẫu). Nút tạo tờ mẫu đã bỏ khỏi giao diện; cần in lại thì gọi `POST /api/draw/calibration` (vẫn còn ở backend, `drawing/calibration.py`) qua `http://127.0.0.1:8000/docs`.
Tờ có chữ F (kiểm hướng X/Y), thước 100 mm (kiểm tỷ lệ) và **8 dải gạch** với khoảng cách = bề rộng bút × 0,8 / 1 / 1,25 / 1,5 / 2 / 2,5 / 3 / 4.

| Xem gì | Kết luận |
|---|---|
| Thước đo được đúng 100 mm? | sai thì kiểm `steps_per_mm` trong cấu hình máy trước khi làm tiếp |
| Dải **sát nhất** mà nét chưa nhòe thành mảng / giấy chưa ướt, quăn | mức đậm nhất dùng được |
| Dải trông như **xám vừa** | khoảng cách mặc định (hiện `DEFAULT_SPACING_PEN = 2.0` × bút, `backend/app/services/drawing/styles.py`) |
| Dải thưa nhất còn đọc thành "mảng" chứ không thành từng sợi | mức sáng nhất có ý nghĩa |

## 2. Thang đậm nhạt: ảnh thử preset (thang xám)
**Chỉ làm MỘT LẦN cho mỗi cây bút + loại giấy**, để chốt số cho preset. Vẽ hằng ngày **không** phải làm bước này: chỉ nạp ảnh → chọn preset → (nếu cần) chỉnh 1–2 ô.

| Ô trên giao diện | Dùng thế nào khi vẽ hằng ngày |
|---|---|
| Số mức đậm nhạt | preset đã chọn sẵn; muốn nhanh / tương phản mạnh thì giảm, muốn mịn thì tăng |
| Tự cân sáng | để bật, tự kéo ảnh tối / nhạt về vừa |
| Gamma, mức đen, mức trắng | preset đã điền; chỉ chỉnh khi một ảnh cụ thể ra quá đậm hoặc quá nhạt |

**Cách làm (lấy preset làm gốc, tăng giảm quanh nó):**
1. Tab Tạo bản vẽ → Bản thảo đã lưu → bấm **"Ảnh thử preset (thang xám)"**: phần mềm tự nạp ảnh 11 bậc (0, 10 … 100 % đen) + một dải chuyển liền bên dưới.
2. Chọn preset **Chân dung** → chờ tạo nét → **Lưu bản thảo** (tên tự thành "Thang xám · Chân dung") → vẽ.
3. Làm tương tự với **Phong cảnh** và **Cận cảnh / Đồ vật**. Ba tờ là đủ.
4. Nhìn từng tờ, sửa đúng preset đó theo bảng dưới, vẽ lại tờ đó nếu cần.

Ảnh 2D / Hình vẽ và Schematic chỉ vẽ viền: thang xám không nói lên gì (chỉ ra khung), thử bằng một hình vẽ thật (mục 4).

| Thấy gì trên tờ | Sửa trong preset (`frontend/js/views/drawing/presets.js`) |
|---|---|
| Hai bậc kề nhau trông như nhau (bút loang) | giảm `style-levels` 1 bậc |
| Bậc đậm nhất bết mực, giấy ướt | tăng khoảng cách nét (mục 1) hoặc giảm `style-levels` |
| Cả tờ quá đậm, các bậc giữa đã gần đen | tăng `image-gamma` thêm 0,1–0,2 |
| Cả tờ quá nhạt, các bậc nhạt còn trắng trơn | giảm `image-gamma` 0,1–0,2 (không dưới 0,8) |
| Vùng nhạt lộ từng sợi, lổn nhổn | giảm khoảng cách nét (`style-spacing`, mm) |

Vì sao cần: ba kiểu tô chia ảnh thành 3–5 mức (`levels`); mỗi mức thêm **một lượt** nét (zigzag: gạch chéo góc khác; sóng: thêm lượt sóng; xoắn ốc: thêm vòng). "5 mức" trên phần mềm chưa chắc ra 5 bậc phân biệt được trên giấy; in một tờ là biết.

## 3. Từng kiểu tô: soi chỗ nào

| Kiểu | Soi trên giấy | Chỉnh ở đâu |
|---|---|---|
| **Zigzag** | chỗ quay đầu ở mép vùng có đọng mực đậm hơn không; các lớp gạch chéo có tạo vân lạ (moiré) không | ô Góc gạch; khoảng cách nét |
| **Sóng** | sóng kề nhau có chạm nhau không; máy có giật / chậm ở chỗ lượn gấp không | ô Biên độ sóng (mặc định 0,35 × khoảng cách, tối đa 0,5 ×) |
| **Xoắn ốc** | tâm xoắn có bết mực không; có vệt nét chạy ngang vùng sáng không (khe trắng < 3 mm được vẽ nối liền để đỡ nhấc bút) | `BRIDGE_MM = 3.0` trong `backend/app/services/drawing/hatch.py` |
| **Nét viền** | viền mỗi khối có liền không, có thừa vụn (lông, vân gỗ) không, nét dày có ra **một** đường không | ô **Chi tiết viền** (Ít / Vừa / Nhiều); hằng số `edges.py` (mục 4) |
| **Thêm lớp viền** (trên kiểu tô) | viền có lệch so với mảng tô không; có làm bức vẽ rối không | tắt đi, hoặc để Chi tiết viền = Ít |

## 4. Nét viền: ảnh thử và hằng số
Thử 3 loại ảnh: (a) hình vẽ / sticker có viền đen (kể cả dán lên ảnh chụp), (b) hình mảng màu phẳng không viền, (c) ảnh chụp thật (chân dung, đồ vật).

| Hằng số (`backend/app/services/drawing/edges.py`) | Ý nghĩa | Khi nào đổi |
|---|---|---|
| `INK_MAX_MM = 4.0` | nét mực dày tới chừng này → một đường giữa; dày hơn → viền hai phía | viền hoạt hình rất dày vẫn ra hai đường → tăng |
| `LIGHT_MAX_MM = 1.2` | vạch sáng mảnh hơn → một đường giữa | |
| `GAP_MM = 1.5` | khe hở được nối | còn đứt → tăng; nối nhầm hai nét khác nhau → giảm |
| `DETAIL` (bảng 3 mức) | ngưỡng Canny, ngưỡng nét mực, mẩu cạnh ngắn nhất | mức Vừa còn vụn trên ảnh chụp → tăng số cuối (mm) của `medium` |

## 5. Preset: thử với ảnh thật
Sau khi chốt mục 1–2, vẽ mỗi preset bằng một ảnh thật đúng loại (khổ A5), ghi: **thời gian vẽ thật**, thời gian phần mềm ước tính (chưa tính gia tốc nên thường ngắn hơn thật), số lần nhấc bút, nhận xét.

| Preset | Kiểu | Ảnh thử nên dùng |
|---|---|---|
| Chân dung | zigzag 5 mức, khử nhiễu, gamma 1,15, viền Ít | ảnh tự chụp, mặt người đủ sáng |
| Phong cảnh | sóng 4 mức, góc 30°, CLAHE, viền Ít | trời mây + nhà, cảnh đêm có đèn, hoàng hôn |
| Cận cảnh / Đồ vật | xoắn ốc 4 mức, gamma 1,25, viền Ít | cốc cà phê, đồ ăn, đồ vật |
| Ảnh 2D / Hình vẽ | nét viền, chi tiết Vừa | sticker, hoạt hình, truyện tranh, ảnh chụp màn hình |
| Schematic / Bản vẽ kỹ thuật | nét viền, mức đen/trắng 60–200 | sơ đồ mạch, bản vẽ scan nền xám |

Sửa số trong `frontend/js/views/drawing/presets.js` (mỗi preset vài dòng, chung một `BASE`). Ảnh đêm / sân khấu vốn tối nên tốn mực và thời gian: thử tăng gamma (1,3–1,5) và bật khử nhiễu.

## 6. Bảng ghi kết quả (điền dần)
| Ngày | Bút | Giấy | Thử gì | Thông số | Thời gian thật / ước tính | Kết luận |
|---|---|---|---|---|---|---|
| | 0,4 | | tờ mẫu hiệu chỉnh | | | |
| | 0,4 | | Thang xám · Chân dung | | | |
| | 0,4 | | Thang xám · Phong cảnh | | | |
| | 0,4 | | Thang xám · Cận cảnh | | | |

Khi đã chốt, cập nhật số mặc định trong mã (đường dẫn ở trên) và đổi 🧪 thành ✅ trong `DRAW_ROADMAP.md` / `STATUS.md`.
