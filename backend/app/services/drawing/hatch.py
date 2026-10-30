"""Lõi tô bằng nét: bản đồ độ đậm -> mặt nạ từng mức -> đường quét song song / xoắn ốc -> các nét (mm).

Mọi hàm thuần numpy / OpenCV, tọa độ ra bằng mm trong khung ảnh (gốc trên trái, Y xuống).
Một mức j chỉ vẽ nơi độ đậm >= j/levels; các mức xoay góc khác nhau nên chồng lên thành tô chéo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

CHUNK_CELLS = 2_000_000          # số mẫu tối đa xử lý một lượt (giới hạn RAM)
MIN_RUN_MM = 0.3                 # đoạn ngắn hơn chừng này bỏ qua (bút không vẽ nổi)
BRIDGE_MM = 3.0                  # khe trắng ngắn hơn chừng này trên xoắn ốc thì vẽ liền (đỡ một lần nhấc bút ≈ 0,6 s)
WAVE_POINT_BUDGET = 100_000      # số điểm tối đa mong muốn cho đường sóng của một lớp (G-code giới hạn 200 000 dòng)


@dataclass(frozen=True)
class Field:
    """Bản đồ độ đậm + hệ tọa độ mm của nó."""
    dark: np.ndarray             # float32 (h, w), 0..1
    width_mm: float
    height_mm: float

    @property
    def h(self) -> int:
        return self.dark.shape[0]

    @property
    def w(self) -> int:
        return self.dark.shape[1]

    @property
    def px_mm(self) -> float:
        return min(self.width_mm / self.w, self.height_mm / self.h)


def thresholds(levels: int) -> list[float]:
    """levels mức sáng tối -> levels-1 lượt tô; lượt j vẽ nơi độ đậm >= j/levels."""
    return [j / levels for j in range(1, levels)]


def level_mask(f: Field, threshold: float, spacing_mm: float) -> np.ndarray:
    """Mặt nạ bool: làm mờ nhẹ, ngưỡng, nối khe hẹp, bỏ đốm nhỏ hơn khoảng cách nét (bút không vẽ nổi)."""
    sigma = max(0.0, 0.35 * spacing_mm / f.px_mm)
    d = cv2.GaussianBlur(f.dark, (0, 0), sigma) if sigma >= 0.5 else f.dark
    m = (d >= threshold).astype(np.uint8)
    k = int(max(1, round(spacing_mm / f.px_mm)))
    if k >= 2:
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k | 1, k | 1))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kern)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kern)
    return m.astype(bool)


def _lookup(mask: np.ndarray, f: Field, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ix = np.floor(x * (f.w / f.width_mm)).astype(np.int32)
    iy = np.floor(y * (f.h / f.height_mm)).astype(np.int32)
    ok = (ix >= 0) & (ix < f.w) & (iy >= 0) & (iy < f.h)
    out = np.zeros(x.shape, dtype=bool)
    out[ok] = mask[iy[ok], ix[ok]]
    return out


def _runs(on: np.ndarray):
    """Các đoạn True liên tiếp theo hàng: (hàng, cột đầu, cột cuối-bao-gồm)."""
    pad = np.zeros((on.shape[0], on.shape[1] + 2), dtype=np.int8)
    pad[:, 1:-1] = on
    d = np.diff(pad, axis=1)
    s = np.argwhere(d == 1)
    e = np.argwhere(d == -1)
    return s[:, 0], s[:, 1], e[:, 1] - 1


# --- đường quét song song ------------------------------------------------------------
def scan_runs(mask: np.ndarray, f: Field, angle_deg: float, spacing_mm: float, phase: float = 0.0):
    """Trả (u_hướng, v_pháp, danh sách theo dòng các (u0, u1)) trên các dòng cách nhau spacing_mm."""
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)])
    n = np.array([-math.sin(a), math.cos(a)])
    corners = np.array([[0, 0], [f.width_mm, 0], [0, f.height_mm], [f.width_mm, f.height_mm]])
    us, vs = corners @ d, corners @ n
    umin, umax = float(us.min()), float(us.max())
    vmin = float(vs.min()) + (phase % 1.0) * spacing_mm
    n_lines = int((float(vs.max()) - vmin) / spacing_mm) + 1
    du = max(f.px_mm * 0.7, 1e-3)
    n_u = int((umax - umin) / du) + 1
    u = umin + np.arange(n_u) * du
    lines: list[list[tuple[float, float]]] = [[] for _ in range(n_lines)]
    rows_per = max(1, CHUNK_CELLS // n_u)
    for r0 in range(0, n_lines, rows_per):
        r1 = min(n_lines, r0 + rows_per)
        v = vmin + np.arange(r0, r1)[:, None] * spacing_mm
        x = u[None, :] * d[0] + v * n[0]
        y = u[None, :] * d[1] + v * n[1]
        on = _lookup(mask, f, x, y)
        rows, c0, c1 = _runs(on)
        for r, a0, a1 in zip(rows.tolist(), c0.tolist(), c1.tolist()):
            u0, u1 = umin + a0 * du, umin + a1 * du
            if u1 - u0 >= MIN_RUN_MM:
                lines[r0 + r].append((u0, u1))
    return d, n, vmin, lines


def serpentine(d, n, vmin, lines, spacing_mm: float, shape=None):
    """Nối các đoạn của dòng kề nhau thành nét liền kiểu zigzag (đi - về). shape(u0,u1,v)->mảng (k,2) tùy biến.

    Chỉ nối khi đầu vào của đoạn mới ở gần cuối đoạn trước (theo hướng quét): ít nhấc bút nhất mà
    đường nối không băng qua vùng trắng xa.
    """
    jump = max(2.5 * spacing_mm, 0.8)
    strokes: list[list[np.ndarray]] = []
    open_prev: list[tuple[float, list[np.ndarray]]] = []        # (u cuối, nét) của dòng trước
    for i, runs in enumerate(lines):
        v = vmin + i * spacing_mm
        forward = (i % 2 == 0)
        taken: set[int] = set()
        open_now: list[tuple[float, list[np.ndarray]]] = []
        for u0, u1 in (runs if forward else reversed(runs)):
            a, b = (u0, u1) if forward else (u1, u0)             # đi từ a tới b
            pts = shape(a, b, v) if shape else np.array([[a, v], [b, v]])
            best, bd = -1, jump
            for k, (ue, _) in enumerate(open_prev):
                if k not in taken and abs(ue - a) <= bd:
                    best, bd = k, abs(ue - a)
            if best >= 0:
                taken.add(best)
                stroke = open_prev[best][1]
            else:
                stroke = []
                strokes.append(stroke)
            stroke.append(pts)
            open_now.append((b, stroke))
        open_prev = open_now
    out = []
    for parts in strokes:
        uv = np.concatenate(parts)
        xy = np.stack([uv[:, 0] * d[0] + uv[:, 1] * n[0], uv[:, 0] * d[1] + uv[:, 1] * n[1]], axis=1)
        out.append(xy)
    return out


def sine_shape(amplitude: float, wavelength: float, step: float):
    """Hàm tạo đường sóng dọc theo đoạn (pha cố định theo u nên các dòng kề nhau song song nhau)."""
    def shape(a: float, b: float, v: float) -> np.ndarray:
        length = abs(b - a)
        k = max(2, int(length / step) + 1)
        uu = np.linspace(a, b, k)
        vv = v + amplitude * np.sin(2 * math.pi * uu / wavelength)
        return np.stack([uu, vv], axis=1)
    return shape


# --- xoắn ốc --------------------------------------------------------------------------
def spiral_runs(mask: np.ndarray, f: Field, pitch_mm: float, phase: float = 0.0):
    """Xoắn ốc Archimedes từ tâm ảnh, bước pitch_mm; cắt theo mặt nạ. Mỗi đoạn True là một nét."""
    cx, cy = f.width_mm / 2, f.height_mm / 2
    r_max = math.hypot(cx, cy) + pitch_mm
    step = max(f.px_mm * 0.7, 1e-3)
    total = math.pi * r_max * r_max / pitch_mm                  # chiều dài xấp xỉ
    n = int(total / step) + 1
    strokes = []
    for k0 in range(0, n, CHUNK_CELLS):
        k = np.arange(k0, min(n, k0 + CHUNK_CELLS + 1), dtype=np.float64)    # chồng 1 mẫu để không đứt nét
        theta = np.sqrt(4 * math.pi * k * step / pitch_mm)
        r = pitch_mm * theta / (2 * math.pi) + phase * pitch_mm
        x, y = cx + r * np.cos(theta), cy + r * np.sin(theta)
        on = _lookup(mask, f, x, y)[None, :]
        _, s, e = _runs(on)
        runs = list(zip(s.tolist(), e.tolist()))
        merged: list[list[int]] = []
        for a0, a1 in runs:
            if merged and (a0 - merged[-1][1]) * step <= BRIDGE_MM:
                merged[-1][1] = a1                              # nối qua khe trắng ngắn
            else:
                merged.append([a0, a1])
        for a0, a1 in merged:
            if (a1 - a0) * step >= MIN_RUN_MM:
                strokes.append(np.stack([x[a0:a1 + 1], y[a0:a1 + 1]], axis=1))
    return strokes
