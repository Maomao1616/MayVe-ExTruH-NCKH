# Tổng hợp thuật toán DrawingBotV3: Phương pháp vẽ, Kiểu nguệch ngoạc & Cách tính độ đậm nhạt

> Tài liệu nghiên cứu tổng hợp từ mã nguồn và tài liệu kỹ thuật của dự án **DrawingBotV3** (tác giả Ollie Lansdell / SonarSonic) kết hợp với các nghiên cứu đồ họa NPR (*Non-Photorealistic Rendering*). Tài liệu tập trung vào:
> 1. Phân loại và nguyên lý toàn bộ các phương pháp vẽ (**Path Finding Modules - PFMs**).
> 2. Phân tích chi tiết **kiểu vẽ nguệch ngoạc (Scribble / Squiggles / Sketch)**.
> 3. Cơ chế toán học và thuật toán **tính toán độ đậm nhạt (Tone / Shading / Density)**.
> 4. Kỹ thuật vẽ đa bút / đa lớp: **Bộ bút xám (Grayscale) & Hệ màu CMYK trên máy vẽ**.
> 5. Phân tích nguyên nhân gốc rễ (**Root Cause**): Tại sao ảnh nét hiện tại bị thô, mất chi tiết tinh xảo?
> 6. Đề xuất kiến trúc: Giữ nguyên 5 kiểu cũ + Bổ sung 2 tùy chọn Chi tiết cao (**High-Detail / Unconstrained** cho Crosshatch & Flow) kèm số liệu thực nghiệm đo đạc.

---

## 1. Tổng quan kiến trúc xử lý của DrawingBotV3

DrawingBotV3 là phần mềm chuyển đổi ảnh bitmap (raster) thành các đường vẽ vector dành riêng cho máy vẽ bút (pen plotters), máy cắt laser, CNC. 

```
Ảnh đầu vào (Raster)
       │
       ▼
[ Trạm 1: Tiền xử lý ảnh (Pre-Processing) ]
  • Chuyển đổi không gian màu sang Luminance (độ sáng)
  • Lọc tương phản, Gamma, Mức đen/trắng, Ngưỡng, CLAHE
       │
       ▼
[ Trạm 2: Mô-đun sinh nét (Path Finding Modules - PFMs) ]
  • Lựa chọn 1 trong hơn 50 kiểu vẽ (Hatch, Sketch, Scribble, Streamlines, Adaptive, Voronoi...)
  • Điều biến nét dựa trên bản đồ tông (Tone Map) hoặc vòng lặp bóc tách (Virtual Erasing)
       │
       ▼
[ Trạm 3: Phân tách màu / Đa bút (Multi-Pen / CMYK / Palette) ]
  • Phân bổ đường nét theo lớp mực: Darkest First, Luminance-Weighted, CMYK
       │
       ▼
[ Trạm 4: Tối ưu hóa đường chạy bút (Path Optimization) ]
  • Đơn giản hóa nét (Ramer-Douglas-Peucker)
  • Nối ghép các mẩu gần nhau (Line Merging)
  • Sắp xếp hành trình giảm thời gian nhấc bút (2-opt TSP Solver / Linesort)
       │
       ▼
Xuất Vector (SVG) / G-code điều khiển máy
```

---

## 2. Toàn bộ các phương pháp vẽ (Path Finding Modules - PFMs)

DrawingBotV3 chia các thuật toán sinh nét thành 8 nhóm lớn:

| Nhóm PFM | Các kiểu cụ thể tiêu biểu | Đặc điểm hình học của nét | Ứng dụng phù hợp |
|---|---|---|---|
| **1. Sketch** | *Sketch Lines, Sketch Curves (Catmull-Rom), Sketch Quad/Cubic Beziers, Sketch Waves, Sketch Shapes, Sketch Sobel Edges, Sketch Flow Field, Sketch Sweeping Curves* | Nét vẽ tự do dạng phác thảo bút chì/bút kim; nét ngắn hoặc uốn lượn; lặp nhiều lớp để tạo bóng | Chân dung ký họa, tranh nghệ thuật phác thảo, minh họa kiến trúc |
| **2. Scribble / Spirals** | *Adaptive Circular Scribbles, Spiral Circular Scribbles, Hatch Circular Scribbles, Spiral Sawtooth, Spiral Archimedean* | Vòng tròn xoắn ốc liên tục (loops), đường xoắn ốc toàn cục điều biến bán kính/biên độ | Tranh vẽ một nét liền (single-line art), chân dung biểu cảm, hạn chế nhấc bút |
| **3. Streamlines** | *Streamlines Flow Field, Streamlines Edge Field, Streamlines Superformula* | Đường dòng mượt mà, song song uốn lượn theo trường vector hướng (gradient/Sobel) | Tranh trừu tượng, mô phỏng tóc/nước/địa hình topo |
| **4. Hatch** | *Hatch Sawtooth, Hatch Parallel, Crosshatching, Hatch Custom Angle* | Lưới đường thẳng song song hoặc đan chéo góc; thay đổi khoảng cách hoặc răng cưa | Tranh khắc đồng cổ điển, bản vẽ kỹ thuật |
| **5. Adaptive** | *Adaptive Stippling, Adaptive Triangulation, Adaptive Shapes, Adaptive Dashes, Adaptive TSP, Adaptive Letters* | Điểm chấm hoặc hình học phân bổ mật độ linh hoạt theo chi tiết ảnh (vùng nhiều chi tiết nét dày hơn) | Tranh chấm điểm (stipple), tranh nối điểm TSP một nét |
| **6. LBG (Linde-Buzo-Gray)** | *LBG Stippling, LBG Triangulation, LBG Circular Scribbles, LBG Quad Tiles, LBG TSP* | Sử dụng thuật toán lượng tử hóa vector LBG để tối ưu vị trí tâm điểm theo trọng số độ sáng | Cho kết quả phân bố điểm tự nhiên và cân bằng hơn Adaptive thông thường |
| **7. Voronoi & Mosaics** | *Voronoi Shapes, Centroidal Voronoi, Mosaic Rectangles, Mosaic Segments, Mosaic Triangulation* | Chia ảnh thành các ô đa giác tế bào (cells), tô đặc hoặc kẻ viền từng ô theo độ sáng | Tranh khảm kính màu, tranh đa giác thấp (Low-Poly) |
| **8. Contours / Outlines** | *Edge Detection (Sobel, Canny, FDoG), Marching Squares, Trace Outlines* | Nét đi theo ranh giới vùng tương phản cao, bao viền chủ thể | Bản vẽ nét viền, tranh hoạt hình 2D, schematic |

---

## 3. Chuyên sâu: Kiểu vẽ nguệch ngoạc (Scribble & Sketch)

Trong DrawingBotV3 và nghệ thuật đồ họa thuật toán, "vẽ nguệch ngoạc" được hiện thực hóa qua **ba hướng tiếp cận chính**:

### 3.1 Hướng 1: Sketch PFMs — Vòng lặp tìm vùng tối & tẩy sáng ảo (Dark-Seeking & Virtual Erasing)
Đây là cách tiếp cận mô phỏng họa sĩ phác thảo nét ngẫu nhiên bằng tay:

```
[Khởi tạo bản đồ mực cần vẽ Dark = 1 - Brightness]
                    │
                    ▼
       ┌──► [Tìm điểm pixel P tối nhất hiện tại]
       │            │
       │            ▼
       │    [Phóng 1 đoạn nét từ P]
       │    • Chiều dài: tăng dần theo step_mm
       │    • Hướng: uốn cong nhẹ (Turn Angle) hoặc đi theo Gradient
       │    • Điều kiện ngắt nét: chạm vùng sáng hoặc đạt Squiggle Max Length
       │            │
       │            ▼
       │    [Tẩy sáng ảo (Virtual Erase) vùng ảnh dưới nét]
       │    • Dark[vùng quét] = Dark[vùng quét] - Erase_Factor
       │            │
       │            ▼
       └─── [Kiểm tra: Còn vùng thiếu mực & Chưa đạt Line Density?]
                    │ (Nếu xong)
                    ▼
          [Xuất danh sách nét Sketch]
```

* **Cơ chế tẩy sáng (Erase Kernel):** Mỗi khi nét vẽ đi qua tọa độ $(x, y)$, ma trận độ đậm tại lân cận bán kính $R_{\text{erase}}$ bị trừ đi một lượng:
  $$\Delta_{\text{dark}}(u, v) = \text{Erase\_Amount} \times \exp\left(-\frac{(u-x)^2 + (v-y)^2}{2 R_{\text{erase}}^2}\right)$$
* **Ý nghĩa:** Vùng tối được vẽ trước; nét vẽ đè lên sẽ làm vùng đó "sáng dần" trong mắt thuật toán, buộc các nét tiếp theo phải dạt sang vùng tối khác. Nhờ vậy, nét không bị chồng chất đen kịt tại một chỗ mà tự động phân bổ đều.

### 3.2 Hướng 2: Circular Scribbles — Vòng lặp xoắn ốc thích ứng (Thuật toán Chiu et al., 2015)
DrawingBotV3 tích hợp thuật toán nổi tiếng từ bài báo khoa học: *"Tone- and Feature-Aware Circular Scribble Art"* (Chun-Chia Chiu, Yi-Hsiang Lo, Ruen-Rone Lee, Hung-Kuo Chu - 2015).

#### Các bước thuật toán:
1. **Trích xuất bản đồ tông mục tiêu ($T_{\text{target}}$):** Ảnh xám được làm mờ Gauss để đại diện cho mật độ tông liên tục mà mắt người cảm nhận từ xa.
2. **Trích xuất bản đồ viền đặc trưng ($F_{\text{edge}}$):** Dùng bộ lọc phát hiện biên (DoG/Sobel) để xác định ranh giới chủ thể cần giữ nét rõ.
3. **Phân đoạn & Dò đường đi toàn cục (Global Trajectory):** 
   * Chia ảnh thành các miền cục bộ không giao nhau.
   * Xâu chuỗi các miền thành một **đường dẫn liên tục duy nhất (Eulerian / TSP Path)** đi qua toàn bộ bức tranh mà không nhấc bút.
4. **Điều biến vòng xoắn nguệch ngoạc (Circular Scribble Modulation):** Dọc theo đường dẫn toàn cục, thuật toán sinh các vòng tròn xoay tròn liên tục $(x(t), y(t))$:
   $$x(t) = x_{\text{path}}(t) + R(t) \cdot \cos(\theta(t))$$
   $$y(t) = y_{\text{path}}(t) + R(t) \cdot \sin(\theta(t))$$
   * **Bán kính vòng xoay $R(t)$:** Nằm trong khoảng $[R_{\min}, R_{\max}]$, tỉ lệ nghịch hoặc tỉ lệ thuận với độ đậm tùy cài đặt (thường vùng tối có bán kính nhỏ và nén sít lại, hoặc bán kính lớn đan xen nhiều tầng).
   * **Vận tốc góc $\theta(t)$ & Bước tiến:** Vùng tối có mật độ vòng tròn dày đặc ($\Delta \theta$ lớn trên mỗi bước đi), vùng sáng vòng thưa hoặc bỏ qua (`Ignore White`).
   * **Uốn theo biên đặc trưng:** Khi đi gần mép $F_{\text{edge}}$, tâm và hình dáng vòng lặp dẹt lại thành elip ép sát theo cạnh biên để giữ độ sắc nét của hình ảnh.

### 3.3 Hướng 3: Random Walk có ràng buộc (Constrained Random Walk)
Phương pháp này giống như nguyên mẫu thực nghiệm `_scribble_proto2.py` trong dự án VMU PlotterPen:
* Từ điểm thiếu mực, cho một "hạt" di chuyển ngẫu nhiên từng bước `step_mm`.
* Hướng đi tại mỗi bước dao động góc $\pm \Delta\theta$ (quán tính hướng đi tránh giật góc 90° gây rung máy vẽ).
* Mỗi bước đi ghi nhận diện tích phủ bằng bề rộng nét thực của bút:
  $$\text{Cover}(x, y) \leftarrow \text{Cover}(x, y) + \frac{\text{pen\_width} \times \text{step\_mm}}{\text{pixel\_area}}$$
* Khi hạt đi vào vùng đã đủ mực hoặc ra vùng giấy trắng, nét vẽ bị ngắt (`break`). Nét ngắn dưới `min_length` bị loại bỏ để bảo vệ servo bút.

---

## 4. Cách tính toán độ đậm nhạt (Tone, Shading & Density Calculation)

Máy vẽ chỉ có 2 trạng thái: **có mực** hoặc **không có mực** trên nền giấy trắng. Độ đậm nhạt thực chất là **mật độ quang học** (tỉ lệ diện tích phủ mực trên bề mặt giấy).

### 4.1 Tiền xử lý bản đồ độ đậm (Luminance to Darkness Map)
1. **Chuyển RGB sang độ sáng (Luminance $Y$):**
   $$Y = 0.299 R + 0.587 G + 0.114 B \quad (0 \le Y \le 255)$$
2. **Chuẩn hóa sang độ đậm đích ($D \in [0, 1]$):**
   $$D = 1.0 - \frac{Y}{255.0}$$
3. **Hiệu chỉnh phi tuyến (Tone Curve / Luminance Power):**
   $$D_{\text{curved}} = D^{\gamma_{\text{power}}}$$
   * $\gamma > 1$: Kéo sáng các vùng xám trung gian, làm nổi vùng tối nhất.
   * $\gamma < 1$: Tăng mật độ nét ở các vùng xám nhạt.
4. **Cắt ngưỡng trắng/đen (Threshold & White Cutoff):** Vùng có $D < D_{\min}$ (thường là 0.05–0.15) được gán hẳn bằng 0 để giữ giấy trắng tinh, tránh nét vẽ thừa lẻ tẻ.

---

### 4.2 Ba nguyên lý toán học quy đổi độ đậm thành đường nét

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BA NGUYÊN LÝ BIẾN ĐỘ ĐẬM THÀNH NÉT                     │
├──────────────────────────────┬──────────────────────────────┬───────────────┤
│ 1. ĐIỀU BIẾN HÌNH HỌC        │ 2. VÒNG LẶP TẨY SÁNG ẢO      │ 3. CHẬP SAI SỐ│
│    (Geometric Spacing)       │    (Virtual Erasing)         │    (Tone Conv)│
├──────────────────────────────┼──────────────────────────────┼───────────────┤
│ Khoảng cách nét s = w / D    │ Vẽ nét -> trừ độ đậm vùng vẽ │ Chập Gauss mô │
│ Dày ở vùng tối, thưa ở sáng  │ Lặp cho đến khi hết vùng tối │ phỏng mắt nhìn│
│ (Áp dụng: Hatch, Sóng, Xoắn) │ (Áp dụng: Sketch, Scribble)  │ (Chiu et al.) │
└──────────────────────────────┴──────────────────────────────┴───────────────┘
```

#### Nguyên lý 1: Điều biến hình học (Geometric Spacing / Frequency Modulation)
* Áp dụng trong: *Hatch, Crosshatching, Wave AM, Spiral*.
* Công thức vật lý chuẩn:
  $$\text{Độ phủ } D = \frac{w}{s} \iff s = \frac{w}{D}$$
  *(với $w$ là bề rộng vết mực thật của bút, $s$ là khoảng cách giữa 2 tâm nét).*
* Giới hạn thực tế: Để tránh rách giấy, độ phủ tối đa $D_{\max} \approx 0.85 - 0.90$ (tương đương $s_{\min} \approx 1.11 w$).

#### Nguyên lý 2: Vòng lặp phản hồi tẩy sáng ảo (Additive Ink / Virtual Erasing)
* Áp dụng trong: *Sketch Lines, Sketch Curves, Random Walk Scribble*.
* Thuật toán duy trì một ma trận thâm hụt mực:
  $$\text{Deficit}(x, y) = \max\left(0, D_{\text{target}}(x, y) - \text{Cover}_{\text{accumulated}}(x, y)\right)$$
* Mỗi bước đi của bút đóng góp một lượng mực nhất định vào $\text{Cover}$. Thuật toán ưu tiên đặt nét ở nơi $\text{Deficit}$ cao nhất và kết thúc khi tổng $\sum \text{Deficit} < \epsilon$.

#### Nguyên lý 3: Tối thiểu hóa sai số chập (Convolved Tone Map Matching)
* Áp dụng trong: *Adaptive Circular Scribbles, Stippling*.
* Mắt người nhìn nét vẽ từ xa đóng vai trò như một bộ lọc thông thấp (Gauss). Độ đậm mô phỏng được tính bằng phép tích chập:
  $$\text{Tone}_{\text{simulated}}(x, y) = \left( \text{BinaryLines} * G_\sigma \right)(x, y)$$
  *(trong đó $G_\sigma$ là nhân Gauss với $\sigma$ tương ứng góc nhìn mắt người).*
* Sai số năng lượng:
  $$E = \iint \left| \text{Tone}_{\text{target}}(x, y) - \text{Tone}_{\text{simulated}}(x, y) \right|^2 dx\,dy$$
* Thuật toán điều chỉnh tần số và bán kính vòng xoắn để cực tiểu hóa sai số năng lượng $E$.

---

## 5. Chuyên đề: Đa bút & Hệ màu CMYK trên máy vẽ (Optical Color Mixing)

### 5.1 Vì sao vẽ 1 màu (đơn sắc) là khó nhất?
Khi chỉ có 1 cây bút đen duy nhất, việc tạo bóng đổ đậm bắt buộc phải ép các nét vẽ sát nhau ($s < 0.5\text{ mm}$). Điều này dẫn đến giới hạn vật lý:
1. Mực chưa kịp khô, ngòi bút cào lên vết mực ướt làm xơ giấy, rách giấy hoặc đọng thành vũng loang lổ.
2. Máy phải đảo chiều liên tục ở cự ly hẹp gây rung khựng cơ khí CoreXY.
3. Kẻ các đường song song đơn thuần làm mắt cảm nhận như một "mảng tôn sọc", thiếu độ sâu tự nhiên.

### 5.2 Giải pháp 1: Bộ bút sắc độ xám (Grayscale Multi-Pen / Tonal Slicing)
Sử dụng 3 đến 5 cây bút cùng màu nhưng khác độ đậm (ví dụ bộ bút chì hoặc bút dạ xám Copic / Sakura Micron Grayscale):
* Bút 1 (Đen): Vẽ vùng $80\% - 100\%$ độ tối (con ngươi, kẽ tóc, bóng đổ gắt).
* Bút 2 (Xám đậm): Vẽ vùng $60\% - 80\%$.
* Bút 3 (Xám vừa): Vẽ vùng $40\% - 60\%$.
* Bút 4 (Xám nhạt): Vẽ vùng $20\% - 40\%$.
* Bút 5 (Xám chì cực nhạt): Vẽ vùng sáng $5\% - 20\%$.

### 5.3 Giải pháp 2: Hệ màu CMYK (Thực tế và dễ mua nhất tại Việt Nam)
Với sinh viên/người dùng phổ thông, bộ bút xám đắt và khó mua. Giải pháp tối ưu là **bộ 4 cây bút bi gel màu thông dụng** (Thiên Long Gel-08/012, Zebra Sarasa, Marvy...):
* **Y (Yellow):** Vàng chanh
* **M (Magenta):** Hồng cánh sen hoặc Đỏ tươi
* **C (Cyan):** Xanh dương sáng hoặc Xanh da trời
* **K (blacK):** Đen

#### Nguyên lý hòa trộn quang học (Optical Mixing):
* $Y + C \rightarrow$ Mắt thấy **Xanh lá**.
* $Y + M \rightarrow$ Mắt thấy **Cam / Tông da người**.
* $M + C \rightarrow$ Mắt thấy **Tím**.
* $Y + M + C + K \rightarrow$ Mắt thấy **Nâu đen / Bóng tối sâu**.

#### Công thức toán học tách kênh CMYK từ ảnh RGB ($R, G, B \in [0, 1]$):
$$K = 1.0 - \max(R, G, B)$$
$$C = \frac{1.0 - R - K}{\max(1.0 - K, 10^{-6})}, \quad M = \frac{1.0 - G - K}{\max(1.0 - K, 10^{-6})}, \quad Y = \frac{1.0 - B - K}{\max(1.0 - K, 10^{-6})}$$
Mỗi kênh $C, M, Y, K$ được chuẩn hóa thành 1 bản đồ độ đậm $[0, 1]$ độc lập để chạy bộ sinh nét.

#### Quy tắc bắt buộc: Thứ tự thay bút từ sáng đến tối
$$\text{Vàng (Y)} \longrightarrow \text{Hồng/Đỏ (M)} \longrightarrow \text{Xanh (C)} \longrightarrow \text{Đen (K)}$$
* *Lý do vật lý:* Đầu ngòi bút vàng rất nhạy cảm. Nếu vẽ màu đen trước rồi vẽ vàng đè lên, mực đen còn ướt sẽ làm nghẹt và đen xì đầu ngòi bút vàng. Vẽ Vàng trước vừa sạch vừa khô nhanh, Đen vẽ cuối cùng để định hình khối và viền bóng.

#### CMYK + Kiểu Nguệch ngoạc (Scribble) — "Cặp đôi hoàn hảo":
Trong in ấn thông thường, 4 lớp CMYK thẳng phải xoay góc chuẩn (C: 15°, M: 75°, Y: 0°, K: 45°) để tránh hiện tượng giao thoa vân sọc (Moiré). Nhưng với **kiểu Nguệch ngoạc (Scribble)**, do nét là đường rối tự do không có góc quét cố định, **hệ thống hoàn toàn miễn nhiễm với Moiré**. 4 lớp sợi chỉ màu vàng, hồng, xanh, đen đan lồng cuộn vào nhau tạo hiệu ứng tranh phác họa đa sắc cực kỳ sống động và hiện đại.

---

## 6. Phân tích nguyên nhân gốc rễ (Root Cause Analysis): Vì sao ảnh nét hiện tại bị thô và thiếu chi tiết?

Trong quá trình phát triển máy vẽ VMU PlotterPen, các quyết định thiết kế đã đặt mục tiêu: **Ưu tiên tốc độ vẽ cực nhanh (2–4 phút), giảm tối đa số lần nhấc bút (vài chục đến vài trăm nét), tránh giật servo Z và chống nghẽn hàng đợi FluidNC**.

Chính các quy tắc tối ưu hóa này đã **trực tiếp bóp nghẹt độ sắc nét và xóa bỏ các chi tiết tinh tế của bức tranh**:

| Quy tắc đang áp đặt trong code | Vị trí mã nguồn | Tác động tiêu cực lên bức tranh |
|---|---|---|
| **Bộ lọc bớt râu `HATCH_MIN_RUN_MM = 5 mm`** | `styles.py:127` | Bất kỳ nét nào $< 5\text{ mm}$ đều bị xóa bỏ. Mắt người, đốm sáng con ngươi (catchlight), sống mũi, khóe môi, ria mép mèo ($0.8 - 3\text{ mm}$) **bị triệt tiêu hoàn toàn**. Mắt bị biến thành hốc đen vô hồn hoặc mất hẳn. |
| **Bỏ dải đậm hẹp `HATCH_THIN_SPACINGS = 1.5x`** | `styles.py:125` | Dải bóng hẹp hơn 1.5 lần khoảng cách nét (~1.5 mm) không được gạch nét, làm các chi tiết thanh mảnh bị đứt đoạn. |
| **Ép nối dòng `serpentine` & `bridge`** | `hatch.py`, `optimize.py` | Cố tình vẽ nửa vòng tròn quay đầu hoặc kéo nét nối xuyên mảng để không phải nhấc bút. Hậu quả: Mép mảng bóng (gò má, cánh mũi) bị **rìa răng cưa bậc thang thô kệch**, tranh trông như một "cuộn dây len quấn". |
| **Cắt ngưỡng trắng sớm `HATCH_WHITE = 0.2`** | `styles.py:133` | Vùng độ đậm $< 20\%$ bị gán thành 0 để "trắng hẳn nổi chủ thể". Toàn bộ dải chuyển tông da nhạt (highlights/gradient) bị mất sạch, tranh bị cháy sáng cục bộ. |
| **Làm mờ ảnh thô bạo `hatch.blur(f, s_ref)`** | `styles.py:150` | Làm mờ ảnh với bán kính bằng khoảng cách nét (~1.5 mm) trước khi kẻ nét, làm phẳng lỳ mọi vi tương phản (micro-contrast) của sợi lông, nếp nhăn. |

### So sánh triết lý: VMU PlotterPen vs. DrawingBotV3
* **VMU PlotterPen (Hiện tại):** Ưu tiên máy chạy nhanh (3–5 phút), ít nhấc bút (100–300 nét), sợ máy mỏi $\rightarrow$ Tranh bị thô, mất chi tiết tinh xảo.
* **DrawingBotV3 / Plotter thế giới:** Ưu tiên **cái hồn và độ tinh xảo của tác phẩm**. Sẵn sàng nhấc bút **3.000 – 15.000 lần**, vẽ trong **20 – 60 phút** để từng sợi lông mi, đốm mắt $0.8\text{ mm}$ đều được thể hiện sắc sảo.

---

## 7. Đề xuất kiến trúc: Giữ 5 kiểu cũ + Bổ sung 2 tùy chọn Chi tiết cao (Unconstrained Options)

### 7.1 Ý tưởng thiết kế
* **Giữ nguyên 5 kiểu vẽ hiện tại:** `crosshatch`, `wave_am`, `flow`, `spiral`, `outline` cùng 4 preset sẵn có để phục vụ các bài in nhanh, demo tốc độ cao (2–4 phút) và đảm bảo an toàn tuyệt đối cho phần cứng.
* **Tạo thêm 2 tùy chọn Chi tiết cao (hoặc công tắc "Bỏ giới hạn / High-Detail"):**
  1. `crosshatch_detail` (Gạch chéo chi tiết cao).
  2. `flow_detail` (Theo dáng chi tiết cao).

### 7.2 Các thay đổi cốt lõi khi kích hoạt chế độ Chi tiết cao
1. **Hạ `min_run_mm`:** $5.0\text{ mm} \longrightarrow 0.5 - 1.0\text{ mm}$ (giữ trọn vẹn đốm mắt, con ngươi, ria mép).
2. **Bỏ chặn dải hẹp:** `thin_spacings = 0` (cho phép vẽ các rãnh đậm thanh mảnh).
3. **Hạ ngưỡng trắng:** `white_cutoff = 0.02 - 0.05` (thay vì 0.20, giữ trọn vẹn tông da nhạt và gradient mịn).
4. **Tăng số mức đậm nhạt:** $5\text{ mức} \longrightarrow 7 - 8\text{ mức}$, khoảng cách nét khít hơn ($1.0\times - 1.5\times$ bề rộng nét).
5. **Nâng độ phủ tối đa:** `MAX_COVERAGE` từ $0.90 \longrightarrow 0.95 - 0.98$ cho vùng đen sâu thẳm.
6. **Cho phép nét rời:** Không ép buộc nối `serpentine` hay kéo `bridge` ở những vị trí gây mép răng cưa bậc thang; dựa vào thuật toán sắp xếp đường chạy `vpype linesort --two-opt` để tối ưu hành trình bay của bút.

---

## 8. Số liệu thực nghiệm đo đạc thực tế (`_detail_probe.py`)

Thử nghiệm trực tiếp trên ảnh mẫu mèo rừng (`meorung01.png`, kích thước $200.0 \times 133.2\text{ mm}$, bút $0.5\text{ mm}$, tốc độ máy $8000\text{ mm/phút}$, thời gian nhấc bút $0.05\text{ s}$):

| Cấu hình thử nghiệm | Số nét | Tổng chiều dài mực | Thời gian ước tính | Đánh giá chất lượng thị giác |
|---|---|---|---|---|
| **Hiện tại (5 mức, chặn 5 mm / 1.5× / 0.20 / 0.90)** | **1.003 nét** | **20.8 m** | **~3.4 phút** | Nhanh nhưng mất mắt mèo, mất ria mép, mép bóng bậc thang |
| **Mở lọc, 5 mức, khoảng cách 2× nét** | **2.628 nét** | **29.9 m** | **~5.9 phút** | Chi tiết mắt mũi hiện lại rõ rệt, da/lông bắt đầu có khối |
| **Mở lọc, 8 mức, khoảng cách 1.5× nét** | **3.933 nét** | **40.8 m** | **~8.4 phút** | Rất sắc nét, từng sợi lông tơ hiện rõ, tông chuyển mượt mà |
| **Mở lọc, 8 mức, khoảng cách 1.0× nét** | **6.237 nét** | **53.2 m** | **~11.9 phút** | Cực kỳ tinh xảo, đen sâu thẳm, đạt chuẩn tranh triển lãm |

### Kết luận thực nghiệm:
Đánh đổi từ **3.4 phút lên 8.4 – 11.9 phút** (chỉ tốn thêm khoảng 5–8 phút vẽ trên máy thật) nhưng số lượng nét chi tiết tăng gấp **4 đến 6 lần** (từ 1.000 nét lên gần 4.000–6.000 nét), loại bỏ hoàn toàn hiện tượng "mù mắt / mất ria" và biến bản vẽ thành một tác phẩm nghệ thuật thực thụ!
