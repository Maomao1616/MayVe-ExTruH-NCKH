"""Kiểu tô "Theo dáng ảnh" (flow field), BẢN THÔ 12/11/2026 (bước F1–F3 của docs/10_HUONG_PHAT_TRIEN.md mục 0.5).

Nét không chạy theo một góc cố định mà uốn DỌC theo dáng ảnh (má, lông, tóc, nếp vải):
  1. Trường hướng: tensor cấu trúc của ảnh độ đậm -> hướng dọc theo cạnh + độ "rõ hướng" (0..1). Chỗ phẳng, không rõ
     hướng thì trộn dần về góc gạch của kiểu tô (ô "Góc", mặc định 45°) để nét không quằn quại vô cớ.
  2. Đặt đường đều nhau (Jobard–Lefer): đi từ một điểm gieo theo trường hướng về hai phía; xong một đường thì gieo đường
     mới cách nó đúng một khoảng; một đường dừng khi ra vùng sáng, quá gần đường khác, hay cong gắt hơn bán kính tối thiểu.
  3. Độ đậm liền (không chia mức): khoảng cách đường tại mỗi chỗ = bề rộng nét ÷ độ phủ mong muốn ở chỗ đó.
Chưa có: lớp hai cho vùng rất đậm (F4), nối đầu các đường kề nhau, chỉnh theo ảnh thật (F5), preset (F6).

Kiểm "quá gần": mọi đường đã vẽ được tô lên một ảnh nhị phân (ô OCC_PX_MM); hỏi một hình vuông quanh điểm có chấm nào.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from .hatch import Field

FLOW_STEP_MM = 0.3               # bước đi theo trường hướng (mm); điểm của nét cách nhau chừng này
FLOW_GRAD_SIGMA_MM = 1.0         # làm mờ ảnh trước khi lấy đạo hàm: bỏ hạt nhiễu nhỏ hơn ~1 mm
FLOW_TENSOR_SIGMA_MM = 4.0       # làm mờ tensor cấu trúc: hướng thay đổi êm trong ~4 mm (to hơn = nét thẳng hơn, ít rối)
FLOW_COHERENCE_FULL = 0.35       # độ rõ hướng từ mức này trở lên thì theo hẳn hướng ảnh; thấp hơn thì trộn dần về góc mặc định
FLOW_MIN_RADIUS_MM = 1.5         # cong gắt hơn bán kính này thì dừng đường (máy không phải giảm tốc / rung ở 8000 mm/phút)
FLOW_MAX_SEP_LINES = 5.0         # khoảng cách đường lớn nhất = 5 × bề rộng nét (vùng nhạt). 10 × ra sọc lẻ tẻ (mô phỏng 12/11);
                                 # 5 × gần bằng mức nhạt nhất của gạch 5 mức (bề rộng ÷ 0,225 = 4,4 ×)
FLOW_MIN_SEP_LINES = 1.1         # khoảng cách nhỏ nhất = 1,1 × bề rộng nét (vùng đậm nhất, chưa đè nét)
FLOW_MAX_COVER = 0.9             # độ phủ lớn nhất (như MAX_COVERAGE của các kiểu gạch)
FLOW_WHITE = 0.1                 # dưới độ phủ này để giấy trắng (không gieo, không đi qua); gạch 5 mức để trắng dưới ~0,11
FLOW_TEST_RATIO = 0.5            # đang đi mà cách đường khác < 0,5 × khoảng cách tại chỗ đó thì dừng
FLOW_SEED_RATIO = 0.95           # điểm gieo phải cách mọi đường ≥ 0,95 × khoảng cách
FLOW_MIN_LEN_SEPS = 3.0          # bỏ đường ngắn hơn 3 × khoảng cách (gạch vụn: mỗi cái tốn một lần nhấc bút)
FLOW_MAX_LEN_MM = 250.0          # một đường dài tối đa chừng này (mỗi phía một nửa)
FLOW_SEED_EVERY = 3              # gieo ứng viên ở mỗi 3 điểm của một đường vừa xong (hai bên)
FLOW_GRID_SEED_MM = 2.0          # lưới điểm gieo dự phòng (vùng chưa có đường nào lan tới), sắp từ đậm tới nhạt
OCC_PX_MM = 0.1                  # ô của ảnh đánh dấu đường đã vẽ


def _blur(img: np.ndarray, sigma_px: float) -> np.ndarray:
    return cv2.GaussianBlur(img, (0, 0), sigma_px) if sigma_px >= 0.5 else img


def direction_field(f: Field, default_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(dx, dy, độ rõ hướng) cùng cỡ f.dark. (dx, dy) là vector đơn vị DỌC theo cạnh (vuông góc gradient), có dấu tùy ý."""
    px = f.px_mm
    d = _blur(f.dark.astype(np.float32), FLOW_GRAD_SIGMA_MM / px)
    gx = cv2.Sobel(d, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(d, cv2.CV_32F, 0, 1, ksize=3)
    s = FLOW_TENSOR_SIGMA_MM / px
    jxx, jyy, jxy = _blur(gx * gx, s), _blur(gy * gy, s), _blur(gx * gy, s)
    tr = jxx + jyy
    root = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)
    coherence = np.where(tr > 1e-9, root / np.maximum(tr, 1e-9), 0.0).astype(np.float32)
    # Góc nhân đôi (hướng không có dấu): gradient 2φ = atan2(2jxy, jxx - jyy); hướng nét = φ + 90° -> 2θ = 2φ + 180°
    c2, s2 = -(jxx - jyy), -(2 * jxy)
    norm = np.maximum(np.hypot(c2, s2), 1e-12)
    w = np.clip(coherence / FLOW_COHERENCE_FULL, 0.0, 1.0)
    a = math.radians(default_deg) * 2
    c2 = w * c2 / norm + (1 - w) * math.cos(a)
    s2 = w * s2 / norm + (1 - w) * math.sin(a)
    theta = 0.5 * np.arctan2(s2, c2)
    return np.cos(theta).astype(np.float32), np.sin(theta).astype(np.float32), coherence


def flow_strokes(f: Field, line_w: float, default_deg: float = 45.0, spacing_scale: float = 1.0,
                 ctx=None) -> list[np.ndarray]:
    """Danh sách nét (mảng N × 2, mm). `spacing_scale` kéo giãn mọi khoảng cách (người dùng đặt khoảng cách khác mặc định)."""
    h, w = f.h, f.w
    sx, sy = f.width_mm / w, f.height_mm / h
    dx, dy, _ = direction_field(f, default_deg)
    cover = np.clip(_blur(f.dark.astype(np.float32), 0.5 * line_w / f.px_mm), 0.0, FLOW_MAX_COVER)
    sep = np.clip(spacing_scale * line_w / np.maximum(cover, 1e-3),
                  FLOW_MIN_SEP_LINES * line_w, FLOW_MAX_SEP_LINES * line_w * spacing_scale).astype(np.float32)

    ow, oh = int(math.ceil(f.width_mm / OCC_PX_MM)) + 1, int(math.ceil(f.height_mm / OCC_PX_MM)) + 1
    occ = np.zeros((oh, ow), np.uint8)

    def cell(x: float, y: float) -> tuple[int, int]:
        return min(h - 1, max(0, int(y / sy))), min(w - 1, max(0, int(x / sx)))

    def busy(x: float, y: float, radius: float) -> bool:
        k = max(1, int(radius / OCC_PX_MM))
        cx, cy = int(x / OCC_PX_MM), int(y / OCC_PX_MM)
        return bool(occ[max(0, cy - k):cy + k + 1, max(0, cx - k):cx + k + 1].any())

    def stamp(points) -> None:
        if len(points) >= 2:
            pts = np.round(np.asarray(points) / OCC_PX_MM).astype(np.int32)
            cv2.polylines(occ, [pts], False, 1, 1)
        elif points:
            x, y = points[0]
            occ[min(oh - 1, int(y / OCC_PX_MM)), min(ow - 1, int(x / OCC_PX_MM))] = 1

    max_turn = FLOW_STEP_MM / FLOW_MIN_RADIUS_MM                # góc quay tối đa mỗi bước (rad)
    cos_max = math.cos(max_turn)
    max_steps = int(FLOW_MAX_LEN_MM / 2 / FLOW_STEP_MM)

    def trace(x: float, y: float, vx: float, vy: float, stamped_from: int) -> list[tuple[float, float]]:
        """Đi một phía từ (x, y) theo hướng ban đầu (vx, vy). Điểm cũ hơn `lag` bước được đánh dấu ngay (chống tự quấn)."""
        out: list[tuple[float, float]] = []
        for i in range(max_steps):
            nx, ny = x + vx * FLOW_STEP_MM, y + vy * FLOW_STEP_MM
            if not (0.0 <= nx <= f.width_mm and 0.0 <= ny <= f.height_mm):
                break
            r, c = cell(nx, ny)
            if cover[r, c] < FLOW_WHITE:
                break
            s = float(sep[r, c])
            if busy(nx, ny, FLOW_TEST_RATIO * s):
                break
            ux, uy = float(dx[r, c]), float(dy[r, c])
            if ux * vx + uy * vy < 0:
                ux, uy = -ux, -uy
            if ux * vx + uy * vy < cos_max:                      # cong gắt quá: dừng
                break
            out.append((nx, ny))
            x, y, vx, vy = nx, ny, ux, uy
            lag = int(2 * s / FLOW_STEP_MM) + 2
            j = len(out) - 1 - lag
            if j >= stamped_from:
                stamp(out[j:j + 2])
        return out

    strokes: list[np.ndarray] = []
    queue: list[np.ndarray] = []

    def try_seed(x: float, y: float) -> bool:
        if not (0.0 <= x <= f.width_mm and 0.0 <= y <= f.height_mm):
            return False
        r, c = cell(x, y)
        if cover[r, c] < FLOW_WHITE or busy(x, y, FLOW_SEED_RATIO * float(sep[r, c])):
            return False
        vx, vy = float(dx[r, c]), float(dy[r, c])
        s = float(sep[r, c])
        lag = int(2 * s / FLOW_STEP_MM) + 2
        fwd = trace(x, y, vx, vy, lag)
        back = trace(x, y, -vx, -vy, lag)
        pts = back[::-1] + [(x, y)] + fwd
        length = FLOW_STEP_MM * (len(pts) - 1)
        if length < FLOW_MIN_LEN_SEPS * s:
            stamp([(x, y)])                                      # gạch vụn: bỏ, nhưng đánh dấu chỗ gieo để khỏi thử lại mãi
            return False
        arr = np.asarray(pts, np.float64)
        stamp(pts)
        strokes.append(arr)
        queue.append(arr)
        return True

    def drain() -> None:
        while queue:
            if ctx:
                ctx.check()
            line = queue.pop()
            for k in range(0, len(line), FLOW_SEED_EVERY):
                x, y = line[k]
                r, c = cell(x, y)
                nx_, ny_ = -float(dy[r, c]), float(dx[r, c])        # pháp tuyến
                for side in (1.0, -1.0):
                    # Khoảng cách lấy ở CHỖ GIEO (lặp 2 lần), không phải ở đường cũ: lan từ đậm sang nhạt mà lấy ở đường cũ
                    # thì đường dày quá, vùng trung bình đậm hơn mong muốn ~0,15 (mô phỏng 12/11).
                    s = float(sep[r, c])
                    for _ in range(2):
                        rr, cc = cell(x + side * nx_ * s, y + side * ny_ * s)
                        s = 0.5 * (s + float(sep[rr, cc]))
                    try_seed(x + side * nx_ * s, y + side * ny_ * s)

    # Gieo dự phòng theo lưới, đậm trước: mỗi vùng tách rời đều có đường; trong vùng thì lan dần từ đường đầu tiên.
    g = FLOW_GRID_SEED_MM
    xs = np.arange(g / 2, f.width_mm, g)
    ys = np.arange(g / 2, f.height_mm, g)
    gx, gy = np.meshgrid(xs, ys)
    gx, gy = gx.ravel(), gy.ravel()
    rows = np.minimum(h - 1, (gy / sy).astype(int))
    cols = np.minimum(w - 1, (gx / sx).astype(int))
    order = np.argsort(-cover[rows, cols], kind="stable")
    for i in order:
        if cover[rows[i], cols[i]] < FLOW_WHITE:
            break
        if try_seed(float(gx[i]), float(gy[i])):
            drain()
    return strokes
