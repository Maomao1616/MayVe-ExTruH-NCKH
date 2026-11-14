# 10 — Hướng phát triển (ý tưởng chưa xếp lịch)

> Dành cho người đọc và người viết báo cáo (phần "hướng phát triển"). Chưa làm. Mọi thời gian là **ước lượng**, phải đo trên MiniPC thật.
> Ký hiệu: ✅ chủ dự án đã đồng ý ý này · 💡 gợi ý · ⚠ chưa kiểm chứng.
> Thư viện / thuật toán ảnh có thể thêm: [06_THUAT_TOAN_XU_LY_ANH.md](06_THUAT_TOAN_XU_LY_ANH.md) mục 17. Việc đã xếp lịch: [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md).

Nguyên tắc chung: **không sửa firmware FluidNC.** Đóng góp của đề tài nằm ở cách ghép dây chuyền, tối ưu cho phần cứng yếu, phần cứng gắn thêm bên ngoài, và **số đo trước / sau**.

---

## 0. Lộ trình thuật toán ảnh (chốt với chủ dự án 12/11/2026)

Nguồn: tài liệu tư vấn AI khác (ý tưởng A–F, 12/11/2026) đối chiếu với mã và số đo in thật cùng ngày. **Triết lý giữ nguyên: ít lần nhấc bút, không râu / nét vụn, chạy được trên CPU MiniPC, không cần mạng.** Mỗi việc thêm vào dây chuyền **có sẵn** (`raster_in` → `tone` → `Field` → kiểu tô `FILLERS` → `optimize` → `gcode`), không viết lại dây chuyền.

### 0.1 Đã làm ngày 12/11
| Việc | Ở đâu | Số đo |
|---|---|---|
| Nối nét gần thay vì nhấc bút | `optimize.bridge` | ảnh mẫu A5: −55–82 % lần nhấc, −30–50 % thời gian |
| Ước tính thời gian có gia tốc | `gcode.path_time`, `lib/gcode.js` | khớp tỷ lệ thật 1,7–1,9 |
| **Đan 3 hướng** (ba lớp lệch 60°) | `styles.crosshatch3` | mô phỏng mực: sai tông 0,036 (gạch chéo 0,042); số nhấc bút gần bằng gạch chéo |
| **Tờ hiệu chỉnh tông** (16 ô độ phủ × 5 kiểu: zigzag, gạch chéo, đan 3 hướng, sóng biên độ, xoắn ốc) | `calibration.tone_layers`; Cài đặt → Tờ thử | chờ in + chụp ([07](07_THU_NGHIEM.md) mục 2b) |

### 0.2 Bước tiếp, theo thứ tự
| # | Việc | Chờ gì | Ước lượng |
|---|---|---|---|
| 1 ✅ | **Đường cong tông** (0.3) | xong 13/11/2026 cho đan chéo + xoắn ốc ([06](06_THUAT_TOAN_XU_LY_ANH.md) 8.12); sóng biên độ chờ in lại | — |
| 2 | **XDoG cho viền ảnh lệch sáng** (0.4) | 2–3 ảnh thật (em bé, ngược sáng, đèn đêm) | 1 buổi |
| 3 | **Flow field: nét theo dáng ảnh** (0.5) | **bản thô F1–F3 đã có 12/11** (kiểu "Theo dáng ảnh (thử nghiệm)"); chờ in thử A6 + ảnh thú thật | còn F4–F6 |
| 3b ✅ | **Đan chéo + theo dáng** (kiểu lai) | xong 13/11/2026 ([06](06_THUAT_TOAN_XU_LY_ANH.md) 8.11); **14/11 ẩn khỏi giao diện**: chủ dự án tách đan chéo / theo dáng thành hai kiểu riêng, Chân dung đổi sang sóng biến thiên ([09](09_QUYET_DINH_THIET_KE.md) P28, P29) | — |
| 4 ✅ | **Buffer + G2/G3** (0.6) | xong 13/11/2026 | — |

### 0.3 Đường cong tông (ý tưởng D) ✅
Mục tiêu: các mức đậm nhạt **trông cách đều nhau bằng mắt** trên đúng bút + giấy, thay vì cách đều theo độ phủ tính toán (mực loang, giấy hút, mắt nhạy ở vùng sáng hơn vùng tối).
- T1 ✅ Tờ hiệu chỉnh tông: 16 ô độ phủ 0–90 % (0 = giấy trắng), 3 ô đen đặc làm mốc đen + mốc căn ảnh, chữ F chỉ hướng. Ba kiểu gạch (zigzag / gạch chéo / đan 3 hướng) chia lớp **đúng như kiểu tô thật**; sóng biên độ chạy đúng `wave_am_groups` trên ô đậm đều, xoắn ốc là `spiral_runs` bước = nét ÷ độ phủ (thêm 12/11/2026). Chỉ cần vẽ 3 tờ: đan 3 hướng, sóng biên độ, xoắn ốc (zigzag / gạch chéo mượn đường cong đan 3). Thông số từng ô (độ phủ, góc, khoảng cách) lưu trong bản thảo (`params.source.cells`).
- T2 Chủ dự án vẽ A6: Sakura 0,5 × 3 kiểu gạch (Ivory, 8000), UB-155 0,38 zigzag nếu còn mực; chụp thẳng, ánh sáng đều (07 mục 2b).
- T3 AI đo ảnh: cắt phần giữa 60 % mỗi ô, lấy độ xám trung bình, quy về 0 = ô giấy trắng, 1 = trung bình 3 ô đen → bảng *độ phủ danh định → độ đậm nhìn thấy*.
- T4 Sửa mã: `level_plan` chọn độ phủ cho từng mức bằng **hàm ngược** của bảng (nội suy tuyến tính từng đoạn, đơn điệu) để các mức cách đều theo độ đậm nhìn thấy. Bảng lưu là **hằng số HOA** theo từng bút trong `styles.py` (kèm ngày đo), chọn theo bút ở ô "Bút vẽ" (cần thêm mã bút vào yêu cầu, hiện chỉ gửi bề rộng). Không có bảng thì giữ cách tính hiện tại. Đo trước / sau bằng `tools/ink_sim.py` + in lại thang xám.
- **Kết quả 13/11/2026:** T3 ✅ (4 kiểu, bảng ở [06](06_THUAT_TOAN_XU_LY_ANH.md) 8.12). T4 ✅ làm khác dự tính: không sửa `level_plan` mà đổi trường độ đậm trước khi chia mức (`styles.tone_cover`), áp 75 % (mô phỏng: áp đủ làm dải chuyển liền đậm quá); một bảng chung, chưa chọn theo bút. Chỉ đan chéo, xoắn ốc, kiểu lai (chủ dự án chọn).
- T5 (sau) Tự đo từ ảnh: tìm 3 ô đen + F, nắn phối cảnh (OpenCV có sẵn), đọc 16 ô. Chỉ làm khi phải hiệu chỉnh nhiều bút / giấy.
- Rủi ro: điện thoại tự cân sáng / màu → luôn chuẩn hóa theo ô trắng và ô đen **trên cùng tờ**; giấy láng phản chiếu → chụp xiên nhẹ, tránh đèn chiếu thẳng.

### 0.4 XDoG cho viền ảnh lệch sáng (ý tưởng B) ✅ xong 13/11/2026 (X1–X3; X4 chờ in thật)
Thử nhanh 12/11 (ảnh mẫu chân dung + mèo, A5, bút 0,5): Canny mức "ít" 199 nét, mặt gần như trống; Canny "nhiều" 341 nét, vụn như vết nứt; **XDoG 215 nét, mắt / mũi / miệng hiện rõ**, đường gọn hơn. Lý do: XDoG so mỗi điểm với vùng quanh nó (hiệu hai bản làm mờ σ và 1,6σ), không dùng một ngưỡng cho cả ảnh như Canny.
- **Làm 13/11/2026 (khác dự tính ở X1):** không có ô chọn "Cách tìm viền" mà là ô tích **"Dùng XDoG"** chỉ ở kiểu Nét viền (`style.outline_xdog`), còn lớp viền phủ lên kiểu tô **luôn** XDoG; thêm preset "Phác họa ảnh". Hằng số `XDOG_*` ở `edges.py`, σ 0,7 mm (không phải 0,35: mất viền đầu). Chi tiết [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 9.1, [09](09_QUYET_DINH_THIET_KE.md) P26. Còn: móc chữ U vùng sáng — thử bật "Thêm lớp viền" ở Chân dung xem có che bớt không.
- X1 Thêm tham số `style.outline_method` = `canny` (mặc định) | `xdog` (ô chọn "Cách tìm viền" cạnh "Mức chi tiết viền"; `spec.py` + `index.html` + `FIELDS` + vi/en). Chỉ thay lớp **ranh giới mảng** (`edges.region_edges`); lớp **nét mực top-hat** (chữ, nét hoạt hình → đường giữa) giữ nguyên, nên chữ không thành hai mép.
- X2 Hằng số đầu tệp `edges.py`: `XDOG_SIGMA_MM` 0,35, `XDOG_K` 1,6, `XDOG_TAU` 0,98, ngưỡng theo mức chi tiết (ít / vừa / nhiều). Không thêm thư viện (OpenCV `GaussianBlur`).
- X3 Test: ảnh tổng hợp nửa sáng nửa tối có cạnh ở cả hai nửa → XDoG tìm được cạnh ở nửa tối, Canny "ít" thì không; số nét không vượt Canny "vừa"; nét mực dày vẫn là một đường giữa.
- X4 Chỉnh trên ảnh của chủ dự án; gửi ảnh so trước / sau (số nét, số lần nhấc bút, thời gian).
- Không dùng XDoG cho chữ gõ: chữ đi đường font / PDF (mục 1.1, 1.2).
- Rủi ro: vùng tối nhiều nhiễu hạt → lấm tấm nét vụn. Chặn bằng làm mờ trước (đã có bilateral), bỏ nét ngắn (`_drop_short`), cắt râu (`prune_spurs`); gợi ý bật "Khử nhiễu" với ảnh tối.

### 0.5 Flow field: nét theo dáng ảnh (ý tưởng A) ✅ ưu tiên thẩm mỹ cao nhất
Cho chân dung người / động vật: nét gạch **uốn theo** má, lông, tóc, nếp vải thay vì luôn chéo 45°, để bức vẽ có "hồn". Là **một kiểu tô mới** (`@FILLERS.register("flow")` + `spec.STYLES` + `GROUPERS` + ô chọn "Theo dáng ảnh"); các kiểu cũ không đổi.

Cách làm (chỉ NumPy + OpenCV đang có):
1. **Trường hướng**: Sobel trên ảnh độ đậm đã làm mờ nhẹ (σ ≈ 1 mm) → tensor cấu trúc (gx², gx·gy, gy²) làm mờ rộng (σ ≈ 3–5 mm) → hướng nét = **dọc theo cạnh** (vuông góc gradient), độ "rõ hướng" (coherence) 0..1. Chỗ phẳng (coherence thấp: trán, nền trơn) **trộn dần về góc mặc định 45°** để nét không quằn quại vô cớ. Tính một lần, gắn vào `Field` (có lưu kết quả), các kiểu tô khác dùng lại được.
2. **Mật độ**: khoảng cách nét tại mỗi điểm = bề rộng nét ÷ độ phủ mong muốn (giống `level_plan`, sau này theo đường cong tông 0.3), giới hạn trong [bề rộng nét, 10 × bề rộng nét].
3. **Đặt đường đều nhau** (Jobard–Lefer, "evenly-spaced streamlines"): gieo đường đầu ở vùng đậm, đi hai phía theo trường hướng (Runge–Kutta bước 0,25–0,5 mm); mỗi đường xong thì gieo đường mới song song cách nó đúng khoảng cách tại chỗ đó. Lưới băm ô vuông để kiểm "gần nét khác" nhanh.
4. **Dừng một đường khi**: ra vùng sáng (dưới ngưỡng mức nhạt nhất), cách nét khác < 0,5 × khoảng cách, cong gắt hơn bán kính tối thiểu (`FLOW_MIN_RADIUS_MM` ≈ 1,5 mm: máy không phải giảm tốc / rung ở 8000), hoặc dài quá giới hạn.
5. **Chống râu và nhấc bút**: bỏ đường ngắn hơn 3 × khoảng cách; nối đầu các đường kề nhau bằng vòng quay đầu (như zigzag) khi hai đầu gần nhau; sau đó `optimize` + nối nét gần như mọi kiểu tô.
6. **Vùng rất đậm**: thêm lớp hai theo hướng vuông góc với trường hướng (như gạch chéo, chia độ phủ bằng `cross_split`) → "đan theo dáng".

**Trạng thái 12/11/2026:** bản thô gộp F1–F3 đã có (`flow.py`, kiểu `flow`, số đo ở [06](06_THUAT_TOAN_XU_LY_ANH.md) mục 8.10). So với tiêu chí nhận: nhấc bút và thời gian **đạt** (ít hơn đan chéo 40–56 %), xử lý 4–5 s **đạt**, sai tông mô phỏng 0,056 **chưa đạt** (đan chéo 0,042). Chưa in. Hướng phối trộn với đan 3 (lai: lớp 1 theo dáng, lớp 2–3 gạch thẳng; hoặc cong chỗ có hướng rõ, thẳng chỗ phẳng) chỉ quyết sau khi in so sánh.

**13/11/2026 (in thật):** theo dáng thuần ra hình ở A4 (mèo 6:21), không ra hình ở A6; đan 3 không đẹp hơn đan chéo. Chủ dự án chốt hướng lai "cong ở viền, thẳng gánh tông": kiểu `crosshatch_flow` ([06](06_THUAT_TOAN_XU_LY_ANH.md) 8.11), mặc định Chân dung. Đan 3 và theo dáng thuần bỏ khỏi danh sách kiểu tô (mã giữ lại). Móc chữ U ở chỗ quay đầu vùng sáng (thấy rõ trên em bé A4): **tạm giữ**; chủ dự án định xử lý bằng XDoG + thêm lớp nét viền (0.4) thay vì nhấc bút thêm.

Các bước giao, mỗi bước có ảnh xem trước để chủ dự án duyệt:
| Bước | Làm | Duyệt bằng |
|---|---|---|
| F1 | Trường hướng + ảnh gỡ lỗi (mũi tên hướng phủ lên ảnh), chưa sinh nét | ảnh hướng trên 3 ảnh mẫu (người, mèo, chó) |
| F2 | Đường đều nhau, một khoảng cách cố định | ảnh xem trước; số nét, số lần nhấc bút |
| F3 | Khoảng cách theo độ đậm (5 mức / liền) | mô phỏng mực (`ink_sim.py`); **in thử A6** |
| F4 | Lớp hai cho vùng đậm | in thử A6, so với gạch chéo / đan 3 hướng |
| F5 | Chỉnh hằng số theo ảnh thật của chủ dự án | ảnh trước / sau |
| F6 | Preset (vd "Chân dung nghệ thuật", "Động vật") | in A5 |

**Tiêu chí nhận** (so với gạch chéo, cùng ảnh, A5, bút 0,5): số lần nhấc bút ≤ 1,2×; thời gian ước tính ≤ 1,2×; sai tông mô phỏng ≤ gạch chéo; không nét nào ngắn hơn 3 × khoảng cách; xử lý ≤ 15 s trên laptop (đo lại trên MiniPC, giới hạn tiến trình con 600 s vẫn giữ); chủ dự án duyệt trên giấy.
Rủi ro: trường hướng nhiễu → nét rối (chặn bằng làm mờ tensor + trộn về 45° chỗ coherence thấp); nhiều đường ngắn → nhiều nhấc bút (bước 5); vòng lặp Python chậm (giới hạn số điểm, đo từng bước trong `info.timings`).

### 0.6 Buffer và cung G2/G3 (ý tưởng E) ✅ xong 13/11/2026
**Kết quả:** tờ 7.6 + tờ nhấc bút ngày 13/11 ([07](07_THU_NGHIEM.md) mục 6, [02](02_PHAN_CUNG_MAY.md) F13–F14). Đã làm: chờ mặc định 0 ([09](09_QUYET_DINH_THIET_KE.md) C10), gộp cung G2/G3 (D12, `drawing/arcs.py`), ước tính tính giới hạn ~125 dòng/giây + xả hàng đợi ở G4. **Không làm** gửi dồn / tăng baud (D10, D11): mô phỏng gửi lệnh trên ảnh mẫu A5 (mọi kiểu tô, khớp số đo 7.6 trong 4 %) cho thấy bản vẽ thật chậm thêm ~0 %. Dưới đây giữ để tra cứu.
- Chủ dự án xác nhận máy **đã từng vẽ được G2/G3** (trước 12/11/2026).
- Số đo 12/11: buffer chỉ tụt về 0 lúc **nhấc bút** (G4 bắt máy xả hàng đợi), nét dài thì đầy → nghẽn hiện tại **không do USB**. Việc trước: thử **chờ 0** (bỏ G4) trên tờ nhấc bút.
- B0 (12/11) Tờ thử **7.6 đoạn ngắn / cung G2** đã có sẵn ([07](07_THU_NGHIEM.md) mục 6): cùng một vòng tròn bằng G1 đoạn 1 → 0,1 mm và bằng G2; kết quả quyết định có cần B3 không.
- B1 Chủ dự án gửi nhật ký chạy (`data/job_logs/*.json` + `.csv`, sau khi gõ `$10=3`) của một bức sóng biên độ và một bức gạch chéo.
- B2 AI đọc `starved_pct`, `planner_blocks`: nếu máy đói lệnh **giữa các nét dài** (không phải lúc nhấc bút) thì làm B3 hoặc D11 (tăng baud, gửi dồn theo số ký tự bộ đệm).
- B3 Gộp đoạn thẳng thành cung G2/G3 cho sóng / xoắn ốc / flow field (sai số ≤ 0,01–0,02 mm, giữ G1 khi không khớp); xem trước (`lib/gcode.js` đã đọc được G2/G3) và ước tính phải tính đúng cung.

### 0.7 Không làm (đi ngược triết lý ít nhấc bút / không râu, hoặc chưa cần)
| Ý tưởng | Vì sao bỏ |
|---|---|
| C. Dithering 2D từng điểm ảnh (Floyd–Steinberg, Jarvis, Stucki, Atkinson, blue-noise) | quyết định theo từng điểm ảnh → đốm và đoạn ngắn → **nhiều nhấc bút, nét vụn**. "Chuyển mức mềm" hiện tại so le theo **cả dòng gạch** để nét vẫn liền (mô phỏng: bậc 0,059 so với 0,099 khi tắt) |
| F. Tối ưu theo hàm chi phí, giữ thứ tự nhạt → đậm, tối ưu 30–180 s | phần "phạt nhấc bút" đã có (nối nét gần); vẽ từng mức nhạt → đậm in thật thấy **lâu hơn** (đã tắt mặc định); 30–180 s quá lâu cho MiniPC |
| Viết lại dây chuyền thành "PipelineContext" dict chung | dây chuyền đã chia bước rõ; dict chung mất phần kiểm tham số của `spec.py`, phải viết lại ~3600 dòng |
| AI dò cạnh / GPU / API ngoài | MiniPC i5-3210M chỉ có đồ họa tích hợp (không CUDA); demo phải chạy offline. Xem lại sau khi 0.3–0.5 xong, luôn có đường CPU dự phòng và tắt được |

---

## 1. Tính năng vẽ mới: chỉ thêm "nguồn nét"
Phần "nét → G-code" dùng chung. Mỗi tính năng mới chỉ là một nguồn nét mới đổ vào đó:
```
PDF từ Word  ──► ảnh từng trang → skeleton ──┐
Câu lệnh     ──► AI tạo ảnh nét ─────────────┼──► NÉT ──► G-code (đã có)
Mẫu chữ tay  ──► bộ chữ riêng → bộ viết chữ ─┘
```
Thứ tự nên làm: tab Beta PDF → bộ chữ + bộ viết chữ → lấy mẫu chữ tay → viết Word bằng chữ tay → AI tạo ảnh.

### 1.1 Tab Beta: in nguyên trang PDF ✅ (khả thi cao, làm trước)
- Tab riêng: nạp PDF, xem trang như bản in, chọn trang, vector hóa trang đó, một preset **"Văn bản"**.
- Người dùng tự "Lưu thành PDF" trong Word (giữ đúng font, dấu tiếng Việt, bố cục). Không đổi Word → PDF trên MiniPC (LibreOffice thiếu font làm chữ xuống dòng khác).
- Kết xuất trang thành ảnh (`pypdfium2` hoặc PyMuPDF) → skeleton (đã có) → mỗi nét chữ một đường giữa.
- Đọc cấu trúc PDF (PyMuPDF `get_text("rawdict")`, `get_drawings()`): đường kẻ bảng vẽ thẳng bằng vector, chữ đậm vẽ 2 đường, ảnh trong trang đi kiểu tô. Lớp chữ (bút bi 0,5) và lớp tranh (Sakura 0,4) thành 2 tệp G-code.

| Chữ cỡ 14–16 | Nét chữ thật | Bút 0,5 vẽ một nét |
|---|---|---|
| Thường (Arial, Times) | ~0,45–0,55 mm | gần y bản in |
| Đậm | ~0,8 mm | hơi mảnh; muốn giống thì 2 đường sát nhau |
| Nét mảnh của Times | ~0,15–0,2 mm | dày bằng nét chính, vẫn dễ đọc |
| Lỗ chữ e, a, o | ~1 mm | còn hở |

**Preset "Văn bản" khác preset ảnh ở 7 điểm:** (1) độ phân giải ~10–12 điểm / mm (`OVERSAMPLE` ~5–6 thay 1,3; chữ "o" cỡ 14 chỉ ~10 điểm ảnh ở độ phân giải ảnh thường); (2) tắt nối khe hở (khe giữa hai chữ chỉ 0,5–0,8 mm); (3) cắt râu (đã có); (4) làm mượt; (5) nét dày > 1,5 × bút thì 2 đường; (6) tỷ lệ 1:1; (7) không khuyên chữ dưới cỡ 8.

Thời gian: trang A4 kín chữ ~2000 ký tự × 2,5 nét ≈ **5000 lần nhấc bút**. Ở ~0,25 s mỗi lần nhấc / hạ (cấu hình hiện tại) + vẽ ≈ **35 phút** ⚠ ước. Thử ngay không cần code: xuất trang PDF ra PNG 300 dpi → tab Tạo bản vẽ → preset Schematic: sẽ thấy đúng hai lỗi (chữ thô, chữ dính), chính là điểm (1) và (2).

### 1.2 Bộ chữ + bộ viết chữ
- Định dạng bộ chữ: mỗi ký tự vài biến thể, mỗi biến thể là các nét đo theo chiều cao chữ; kèm phong cách (nghiêng, khoảng cách, độ lượn, lệch ngẫu nhiên).
- Bộ viết chữ: văn bản → xếp dòng trên khổ giấy → chọn biến thể (không lặp liền) → lệch nhẹ → nét → G-code.
- Dấu tiếng Việt ghép theo quy tắc (chữ gốc + 5 dấu thanh; khó nhất là chồng hai dấu ấ ầ ẩ ẫ ậ). Chưa có font nét đơn nào có sẵn dấu tiếng Việt (Hershey không có).

### 1.3 Lấy mẫu chữ tay
- Tờ mẫu có ô kẻ: mỗi ký tự viết 3 lần (~80 ký tự × 3 ≈ 2–3 trang) → hình dáng. Một đoạn văn tự nhiên → đo phong cách chung.
- Tốt nhất: **viết thẳng lên màn hình cảm ứng** trong app (ghi đúng thứ tự nét, sạch, không cần skeleton).
- Chỉ dùng chữ của chính mình hoặc người đã đồng ý; không dùng để nộp thay bài bắt buộc tự viết.

### 1.4 Gõ câu lệnh → AI tạo ảnh → bản vẽ (làm cuối)
- **Không chạy AI tạo ảnh trên MiniPC** (không card đồ họa: vài phút mỗi ảnh, 4–8 GB RAM).
- Gọi dịch vụ trên mạng: nhanh, nhẹ cho MiniPC, nhưng cần Internet, mất phí theo ảnh, phải giới hạn số lần khi mở cho người ngoài.
- Tự thêm vào câu lệnh "tranh nét đen trắng, không tô bóng".

### 1.5 MiniPC có chịu nổi không
| Việc | Tải |
|---|---|
| PDF → ảnh → skeleton | vừa (~16 lần điểm ảnh so với ảnh thường, vẫn trong giới hạn) |
| Bộ viết chữ | rất nhẹ |
| AI tạo ảnh qua mạng | rất nhẹ (tốn phí) |
| AI tạo ảnh tại chỗ | **không nên** |

Giới hạn bảo vệ đã có: ảnh ≤ 40 MB, SVG ≤ 20 MB, ảnh gốc ≤ 60 triệu điểm, ảnh làm việc 400–4000 điểm cạnh dài, mỗi lần xử lý ≤ 600 s, RAM tiến trình ≤ 4 GB (Linux), tổng điểm nét ≤ 2 triệu, 2-opt ≤ 15 000 nét, G-code ≤ 200 000 dòng.

---

## 2. Mở cho nhiều người (sau bản khách + quản lý)
| Ý | Ghi chú |
|---|---|
| Tài khoản "người dùng" ✅ | chỉ tên + mật khẩu, không email; mật khẩu băm bằng `hashlib.scrypt` 💡; form đăng ký không bao giờ tạo quản lý |
| Thư mục riêng theo tài khoản ✅ | người này không xem được của người kia; giữ 3 ngày; mọi route đọc tệp phải kiểm chủ |
| Hàng chờ tạo nét ✅ | tách "nạp ảnh" khỏi "tạo nét" (nút "Tạo nét", đã đưa vào kế hoạch [11_VIEC_CAN_LAM.md](11_VIEC_CAN_LAM.md) mục 5 bước 4); một việc một lúc theo thứ tự đến; mỗi người chỉ hủy việc của mình; `idle.py` phải tính việc đang chờ |
| Lưu nét gốc `strokes.json` ✅ | đổi bố trí / G-code mà không vector lại; "dấu vân tay" = băm (ảnh + vùng cắt + tham số vector) để biết nét đã cũ |
| Màu chỉ cho quản lý ✅ | khóa ở máy chủ, không chỉ ẩn ô |
| Cloudflare nâng cao 💡 | Cloudflare Access làm thêm lớp đăng nhập ngoài; giới hạn tần suất theo `CF-Connecting-IP` |

---

## 3. Điện tử và IoT (không sửa firmware)

### 3.1 Dùng chân trống của MKS (chỉ sửa YAML + nối dây)
- `feed_hold_pin` + `cycle_start_pin`: **2 nút cứng Tạm dừng / Chạy tiếp** trên máy, chạy cả khi mất mạng.
- **Cảm biến bút** (công tắc nhỏ hoặc Hall + nam châm trên giá bút) vào `probe` (`gpio.22`): báo cáo có `Pn:P` → phần mềm biết **bút thật sự đã nhấc** (hiện chỉ biết lệnh Z), thêm đèn "Bút" cạnh đèn X / Y, dừng khi bút kẹt. Phần mềm đã đọc `Pn` sẵn.
- ⚠ Dò chân bằng sơ đồ mạch trước ([02_PHAN_CUNG_MAY.md](02_PHAN_CUNG_MAY.md) mục 3, 8).

### 3.2 ESP32-S3: các nút mạng riêng (không đụng MKS)
| Nút | Làm gì | Từ khóa |
|---|---|---|
| Bảng điều khiển không dây | OLED / TFT + 3 nút + còi + LED: trạng thái, % tiến độ, tạm dừng / chạy tiếp qua API (cần "mã thiết bị"). Nút an toàn vẫn phải nối dây | `ESP32-S3 OLED HTTP client` |
| Đo điện năng | INA226 trên dây 12 V → Wh mỗi bản vẽ | `INA226 ESP32` |
| Nhiệt độ | DS18B20 trên driver / động cơ → cảnh báo | `DS18B20 ESP32` |
| Camera xem trực tiếp | ESP32-S3 + OV2640, MJPEG 640×480 ⚠ đo khung/s | `ESP32-S3 CameraWebServer` |
| Giao tiếp | MQTT (Mosquitto chạy trên MiniPC, không cần Internet) hoặc HTTP | `paho-mqtt`, `PubSubClient` |

ESP32 dùng hạ áp 5 V riêng (servo giật dòng làm ESP32 khởi động lại).

### 3.3 Hướng nghiên cứu khác
| Hướng | Làm gì | Từ khóa |
|---|---|---|
| Cách gửi G-code | so "gửi một dòng chờ `ok`" với "đếm ký tự" (lấp bộ đệm nhận); vẽ biểu đồ `Bf:` theo thời gian để thấy chỗ "đói lệnh". Rủi ro an toàn: dòng lỗi vẫn nằm trong bộ đệm | `grbl character counting streaming` |
| Tinh chỉnh cấu hình | gia tốc, `junction_deviation`, vi bước → bảng thời gian vẽ / chất lượng nét | `grbl junction deviation` |
| Bút servo | đo thời gian nhấc / hạ thật bằng máy hiện sóng / logic analyzer; thử servo nhanh hơn | `FluidNC RcServo` |
| Driver | TMC2209 StealthChop (êm) và SpreadCycle (khỏe ở tốc độ cao); nguồn 24 V | `TMC2209 standalone SpreadCycle` |
| Camera tự căn giấy | mã ArUco ở góc bàn → tự tìm vị trí giấy, tự đặt Zero; chụp tờ đã vẽ → so với xem trước bằng SSIM + OCR | `OpenCV ArUco homography` |
| Thông báo | MQTT lên bảng theo dõi, bot Telegram báo "vẽ xong / lỗi" | `Telegram bot sendMessage` |
| So đường truyền | độ trễ USB so với Wi-Fi của FluidNC; ghi lý do chọn USB (Wi-Fi vượt qua khóa của phần mềm) | `FluidNC telnet websocket` |

---

## 4. Tính năng phần mềm nhỏ
- 💡 Vệt bút theo dòng G-code cho cả macro / tiếp tục tác vụ (hiện chỉ cho tệp đang chạy).
- 💡 `.devcontainer/` cho GitHub Codespaces.
- 💡 Đổi PIN quản lý ngay trên giao diện; mã QR địa chỉ LAN trên giao diện.
- 💡 2-opt trong Web Worker, chỉ khi đo trên MiniPC thấy sắp xếp nét lâu.
- ✅ Thời gian ước tính có tính gia tốc (12/11/2026, `gcode.path_time`).
- 💡 Ghi mốc tiến độ định kỳ để tiếp tục được cả khi mất điện / tắt server giữa chừng.

---

## 5. Lời khuyên đã kiểm là sai (từ một tư vấn AI khác, 02/11/2026): đừng làm theo
- "`pdftocairo -svg` giữ chữ trong thẻ `<text>`": không có tài liệu xác nhận; có người báo SVG ra không thấy chữ.
- "`vpype-text` tự ép font Hershey tiếng Việt": plugin ngừng phát triển; Hershey không có dấu tiếng Việt.
- "`findContours` trên nét 1 điểm ảnh": ra hai đường bao.
- "`potrace` vector hóa nét mượt": ra nét đôi.
- "`docx2pdf`": cần Word cài sẵn; MiniPC Ubuntu không có.
