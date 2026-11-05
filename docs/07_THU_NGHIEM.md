# 07 — Thử nghiệm và hiệu chỉnh trên giấy

> Dành cho người vận hành máy (không cần lập trình). Mục tiêu: chốt các con số mặc định (bề rộng nét, khoảng cách, số mức, gamma,
> preset, tốc độ) **bằng bản in thật**, vì màn hình không cho biết mực loang, giấy thấm, bút khô ra sao.
> Ký hiệu: ✅ đã chốt bằng bản in · 🧪 mới thử bằng ảnh mẫu / mô phỏng · ⏳ chưa làm.
> Kết quả thử máy đã có: [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) mục 6.

## 0. Nguyên tắc
- **Mọi quyết định về độ đậm phải nhìn tờ giấy.** Khung xem trước trên web chỉ để kiểm hình học (đủ nét, đúng chỗ, không vượt khổ).
- **Mỗi lần chỉ đổi một thông số.** Cùng giấy, cùng bút, cùng tốc độ.
- **Ghi số ở góc tờ** (bút, khoảng cách, số mức, gamma, preset, tốc độ, ngày) rồi chụp ảnh.
- Làm theo thứ tự: mục trước chốt con số mục sau dùng. Mỗi bút (0,2 / 0,4 / 0,5) làm riêng.
- Tệp G-code thử có sẵn: `python tools/make_test_gcode.py` ghi vào `export\test-gcode\` (không lên Git). Nạp ở tab Điều khiển → Xem trước → Chạy. **Mỗi bài một tờ giấy mới.**

## 1. Bề rộng nét thật: tờ mẫu hiệu chỉnh bút
Tờ có chữ F (kiểm hướng X / Y), thước 100 mm (kiểm tỷ lệ) và **8 dải gạch** cách nhau 0,8 / 1 / 1,25 / 1,5 / 2 / 2,5 / 3 / 4 × cỡ bút. Nút trên giao diện đã bỏ; cần in lại thì gọi `POST /api/draw/calibration` ở `http://127.0.0.1:8000/docs` (gửi `pen_width_mm`).

| Xem gì | Kết luận |
|---|---|
| Thước đúng 100 mm? | ✅ đúng. Sai thì kiểm `steps_per_mm` trước khi làm tiếp |
| Dải **sát nhất còn đặc mà chưa ướt / quăn** | khoảng cách ≈ bề rộng nét thật |
| Dải trông **xám vừa** (đứng 40–50 cm, chưa thấy từng sợi) | ≈ 2 × bề rộng nét (phủ 50 %) |
| Dải thưa nhất còn đọc thành mảng | mức sáng nhất có ý nghĩa |

✅ 03/11/2026, Sakura 0,4, tốc độ 3000: dải 0,5 mm đặc, 0,6 mm gần đặc, 0,8 mm còn sợi → nét thật **~0,55 mm** → `LINE_WIDTH_RATIO = 1.375` (`backend/app/services/drawing/styles.py`). Phần mềm tự suy ra mọi khoảng cách nét từ con số này ([06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md) mục 6).
⏳ Bề rộng nét **phụ thuộc tốc độ**: in lại tờ này ở tốc độ đã chốt (bài 7.4), sửa `LINE_WIDTH_RATIO = nét thật ÷ cỡ ngòi` nếu khác.

## 2. Thang đậm nhạt: ảnh thử preset (thang xám)
Chỉ làm **một lần cho mỗi bút + loại giấy**, để chốt số cho preset.

1. Tab Tạo bản vẽ → **"Ảnh thử preset (thang xám)"**: nạp ảnh 11 bậc (0, 10 … 100 % đen) + một dải chuyển liền.
2. Chọn preset **Chân dung** → chờ tạo nét → **Lưu bản thảo** (tên tự thành "Thang xám · Chân dung") → vẽ.
3. Làm tương tự với **Phong cảnh** và **Cận cảnh**. Ba tờ là đủ (Ảnh 2D và Schematic chỉ vẽ viền, thang xám không nói lên gì).
4. Nhìn từng tờ, sửa đúng preset đó theo bảng dưới.

Cần biết: với 5 mức, 11 bậc ảnh được gộp thành **5 bậc trên giấy** (giấy trắng + 4 mật độ: 22 / 45 / 68 / 90 % mực). Hai bậc ảnh kề nhau ra cùng mật độ là đúng thiết kế.

| Thấy gì trên tờ | Sửa trong `frontend/js/views/drawing/presets.js` |
|---|---|
| Hai mật độ kề nhau trông như nhau | giảm `style-levels` 1 bậc |
| Bậc đậm nhất bết mực, giấy ướt | giảm `MAX_COVERAGE` (0,9 trong `styles.py`) hoặc tăng `style-spacing` |
| Cả tờ quá đậm, các bậc giữa gần đen | tăng `image-gamma` 0,1–0,2 |
| Cả tờ quá nhạt | giảm `image-gamma` 0,1–0,2 (không dưới 0,8) |
| Vùng nhạt lộ từng sợi, lổn nhổn | giảm `style-spacing` (mm; trống = 1,1 với bút 0,4) |
| Tông giữa lệch so với dải chuyển liền | ghi lại độ đậm nhìn thấy từng bậc → dùng làm **đường cong tông** ([10_HUONG_PHAT_TRIEN.md](10_HUONG_PHAT_TRIEN.md)) |

## 3. Từng kiểu tô: soi chỗ nào
| Kiểu | Soi trên giấy | Chỉnh ở đâu |
|---|---|---|
| Zigzag | chỗ quay đầu ở mép vùng còn đọng mực không (đã đổi sang nửa vòng tròn 03/11) | ô Góc gạch, Khoảng cách nét |
| Sóng | sóng kề nhau có chạm nhau không; máy có giật ở chỗ lượn không | ô Biên độ sóng (trống = 0,18 × khoảng cách, tối đa 0,5 ×) |
| Xoắn ốc | tâm xoắn có bết mực không; vệt nối ngang vùng sáng (khe trắng < 6 × bước xoắn được vẽ liền) | `SPIRAL_BRIDGE_PITCHES` trong `hatch.py` |
| Viền | viền khối có liền không, thừa vụn không, nét dày ra **một** đường không | ô Chi tiết viền (Ít / Vừa / Nhiều); hằng số `edges.py` (mục 4) |
| Thêm lớp viền | viền có lệch so với mảng tô, có làm rối không | tắt, hoặc Chi tiết viền = Ít |

## 4. Nét viền: ảnh thử và hằng số
Thử 3 loại ảnh: (a) hình vẽ / sticker có viền đen, (b) hình mảng màu phẳng không viền, (c) ảnh chụp thật.

| Hằng số (`edges.py`) | Ý nghĩa | Khi nào đổi |
|---|---|---|
| `INK_MAX_MM = 4.0` | nét mực dày tới chừng này → một đường giữa | viền hoạt hình rất dày vẫn ra hai đường → tăng |
| `LIGHT_MAX_MM = 1.2` | vạch sáng mảnh hơn → một đường giữa | |
| `GAP_MM = 1.5` | khe hở được nối | còn đứt → tăng; nối nhầm hai nét → giảm |
| `SPUR_MM` (2,4 / 1,6 / 1,0) | râu ngắn hơn chừng này bị cắt | còn râu ở góc chữ → tăng; mất chân linh kiện ngắn → giảm |
| `DETAIL` | ngưỡng Canny, ngưỡng nét mực, mẩu cạnh ngắn nhất | mức Vừa còn vụn trên ảnh chụp → tăng số cuối (mm) của `medium` |

## 5. Preset với ảnh thật
Sau mục 1–2, vẽ mỗi preset bằng một ảnh thật đúng loại (A5). Ghi: thời gian vẽ thật, thời gian ước tính, số lần nhấc bút, nhận xét.

| Preset | Ảnh thử nên dùng |
|---|---|
| Chân dung | ảnh tự chụp, mặt đủ sáng |
| Phong cảnh | trời mây + nhà, cảnh đêm có đèn, hoàng hôn |
| Cận cảnh / Đồ vật | cốc cà phê, đồ ăn |
| Ảnh 2D / Hình vẽ | sticker, hoạt hình, ảnh chụp màn hình |
| Schematic | sơ đồ mạch, bản vẽ scan nền xám, mạch in đơn giản |

Ảnh đêm vốn tối nên tốn mực và thời gian: thử tăng gamma (1,3–1,5) và bật khử nhiễu.

## 6. Bài thử tốc độ (sau khi chốt nét)
Mục đích: vẽ nhanh hơn mà nét không xấu, máy không mất bước.
- **Thông số máy** (gia tốc, `junction_deviation_mm`, tốc độ tối đa): Cài đặt → Cấu hình máy → Áp dụng (chỉ RAM). Chốt được rồi mới Lưu vào mạch.
- **Thông số G-code** (chờ, tốc độ vẽ / di chuyển / bút): tab Tạo bản vẽ. **Z bút**: Cài đặt → Cấu hình máy, mục App.
- Tệp có sẵn: `7.1-cho-0.20s / 0.10s / 0.05s`, `7.1-nhac-Z2 / Z1.5`, `7.2-mat-buoc`, `7.3-gia-toc-rang-cua`, `7.4-toc-do-ve` (3000 / 4000 / 5000 / 6000), `7.5-keo-vet-cho-0.05s / 0.10s`. Mặc định Z 3 / 0, nâng 3000, hạ 2000, vẽ 5000; đổi bằng `--up`, `--down`, `--down-feed`, `--draw-feed`.

| # | Bài | Cách làm | Nhìn gì | Tình trạng |
|---|---|---|---|---|
| 7.1 | Chi phí nhấc bút | 100 gạch 2 mm; thời gian thật ÷ 100 = một chu kỳ nhấc + hạ + chờ. Đổi chờ 0,2 → 0,1 → 0,05 s; Z nhấc 3 → 2 → 1,5 | bút kéo vệt khi di chuyển (nhấc chưa kịp)? đầu nét hụt (hạ chưa chạm)? bút nảy? | ✅ chờ 0,05 s đủ nét; ⏳ đo thời gian chính xác |
| 7.2 | Mất bước | vẽ dấu + ở góc → chạy nhanh nhiều lần → vẽ lại dấu + | hai dấu trùng khít = không mất bước | ✅ 03/11 (6000 mm/min, ~20 phút) |
| 7.3 | Gia tốc + góc | cùng đoạn chữ ở gia tốc 1000 / 1500 / 2000 / 3000, rồi `junction_deviation` 0,01 / 0,03 | thời gian; gợn sóng sau góc chữ | ⏳ |
| 7.4 | Tốc độ vẽ từng bút | dải đường thẳng 3000 / 4000 / 5000 / 6000, mỗi bút một tờ, **chụp cận đo bề rộng nét** | tốc độ cao nhất mà nét chưa nhạt / đứt; bề rộng nét ở đó (→ `LINE_WIDTH_RATIO`) | 🧪 6000 vẫn đậm (ảnh xa); ⏳ đo |
| 7.5 | Vệt kéo khi đi xa | hai chấm cách 240 mm, G0 qua lại 5 lần, mỗi lần một mức chờ nâng; đổi Z nhấc 3 / 4 / 5. Dán giấy phẳng | vệt mảnh nối hai chấm = bút chưa rời giấy | ⏳ |

**Hạ chậm, nhấc nhanh** (bút hạ bằng trọng lực): ô "Tốc độ hạ bút" (mặc định 2000). Thử 600–1500 nếu bút còn nảy hoặc loang mực đầu nét.

## 7. Bảng ghi kết quả (điền dần)
| Ngày | Bút | Giấy | Thử gì | Thông số | Thời gian thật / ước tính | Kết luận |
|---|---|---|---|---|---|---|
| 03/11/2026 | 0,4 | | tờ mẫu hiệu chỉnh | vẽ 3000 | | nét ~0,55 mm |
| 03/11/2026 | | | 7.2 mất bước | G0 6000, gia tốc 2000 / 3000, Vref 1,4 V | ~20 phút | không mất bước |
| | 0,4 | | tờ mẫu hiệu chỉnh | vẽ 5000 | | |
| | 0,5 | | tờ mẫu hiệu chỉnh | | | |
| | 0,4 | | Thang xám · Chân dung | | | |
| | 0,4 | | Thang xám · Phong cảnh | | | |
| | 0,4 | | Thang xám · Cận cảnh | | | |
| | | | 7.4 bề rộng nét theo tốc độ | 3000 / 4000 / 5000 / 6000 | | |
| | | | 7.5 vệt kéo | Z 3 / 4 / 5, chờ 0,05 / 0,1 | | |

Khi đã chốt: sửa số mặc định trong mã (đường dẫn ở trên), ghi kết quả vào [02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) mục 6, đánh dấu xong ở [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md).
