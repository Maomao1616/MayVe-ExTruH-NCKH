"""Lõi tô bằng nét: bản đồ độ đậm -> mặt nạ từng mức -> đường quét song song / xoắn ốc -> các nét (mm).

Mọi hàm thuần numpy / OpenCV, tọa độ ra bằng mm trong khung ảnh (gốc trên trái, Y xuống).
Mỗi dải đậm nhạt (styles.level_plan) có mặt nạ riêng và một lượt gạch với khoảng cách riêng.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

CHUNK_CELLS = 2_000_000          # số mẫu tối đa xử lý một lượt (giới hạn RAM)
MIN_RUN_MM = 0.3                 # đoạn ngắn hơn chừng này bỏ qua (bút không vẽ nổi)
BRIDGE_MM = 3.0                  # khe trắng ngắn hơn chừng này trên xoắn ốc thì vẽ liền (đỡ một lần nhấc bút ≈ 0,6 s)
SPIRAL_BRIDGE_PITCHES = 6.0      # nối qua khe trắng tới chừng này lần bước xoắn
SPIRAL_MIN_PITCHES = 4.0         # bỏ mẩu ngắn hơn chừng này lần bước xoắn
WAVE_POINT_BUDGET = 100_000      # số điểm tối đa mong muốn cho đường sóng của một lớp (G-code giới hạn 200 000 dòng)


@dataclass(frozen=True)
class Field:
    """Bản đồ độ đậm + hệ tọa độ mm của nó."""
    dark: np.ndarray             # float32 (h, w), 0..1
    width_mm: float
    height_mm: float
    rgb: np.ndarray | None = None   # uint8 (h, w, 3) cùng cỡ, chỉ có khi vẽ viền (ranh giới mảng màu)

    @property
    def h(self) -> int:
        return self.dark.shape[0]

    @property
    def w(self) -> int:
        return self.dark.shape[1]

    @property
    def px_mm(self) -> float:
        return min(self.width_mm / self.w, self.height_mm / self.h)


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


TURN_POINTS = 7                  # nửa vòng tròn quay đầu: 7 điểm = 6 đoạn, mỗi chỗ rẽ ~30° (máy giữ được ~24 mm/s)


def serpentine(d, n, vmin, lines, spacing_mm: float, shape=None, round_turns: bool = True):
    """Nối các đoạn của dòng kề nhau thành nét liền kiểu zigzag (đi - về). shape(u0,u1,v)->mảng (k,2) tùy biến.

    Chỉ nối khi đầu vào của đoạn mới ở gần cuối đoạn trước (theo hướng quét): ít nhấc bút nhất mà
    đường nối không băng qua vùng trắng xa.

    round_turns: chỗ quay đầu là NỬA VÒNG TRÒN bán kính spacing / 2 (đỉnh vòng tròn đúng tại mép đoạn), không phải
    hai góc vuông. Hai góc vuông ép máy giảm tốc gần về 0 (junction_deviation 0,01 mm: ~7 mm/s) và bút đứng lâu ở mép
    nên mực loang thành giọt; nửa vòng tròn giữ ~24 mm/s và đỡ chậm hơn nhiều.
    """
    jump = max(2.5 * spacing_mm, 0.8)
    r = spacing_mm / 2.0

    def make(a, b, v):
        return shape(a, b, v) if shape else np.array([[a, v], [b, v]])

    # nét = {"parts": [mảng uv...], "last": (a_dùng, v) của đoạn cuối}
    strokes: list[dict] = []
    open_prev: list[tuple[float, dict, float]] = []             # (u cuối, nét, hướng ±1) của dòng trước
    for i, runs in enumerate(lines):
        v = vmin + i * spacing_mm
        forward = (i % 2 == 0)
        taken: set[int] = set()
        open_now: list[tuple[float, dict, float]] = []
        for u0, u1 in (runs if forward else reversed(runs)):
            a, b = (u0, u1) if forward else (u1, u0)             # đi từ a tới b
            sgn = 1.0 if b > a else -1.0
            best, bd = -1, jump
            for k, (ue, _, _) in enumerate(open_prev):
                if k not in taken and abs(ue - a) <= bd:
                    best, bd = k, abs(ue - a)
            if best < 0:
                stroke = {"parts": [make(a, b, v)], "last": (a, v)}
                strokes.append(stroke)
            else:
                taken.add(best)
                ue, stroke, psgn = open_prev[best]
                a_prev, v_prev = stroke["last"]
                apex = (ue + a) / 2.0
                cut = apex - psgn * r                            # hai đầu cung nằm cùng u, đỉnh cung tại apex
                turn = (round_turns and abs(ue - a) <= 0.7 * r
                        and (cut - a_prev) * psgn >= r and (b - cut) * sgn >= 2 * r)
                if turn:
                    stroke["parts"][-1] = make(a_prev, cut, v_prev)
                    t = np.linspace(-math.pi / 2, math.pi / 2, TURN_POINTS)
                    stroke["parts"].append(np.stack([cut + psgn * r * np.cos(t),
                                                     (v_prev + v) / 2 + (v - v_prev) / 2 * np.sin(t)], axis=1))
                    a = cut
                stroke["parts"].append(make(a, b, v))
                stroke["last"] = (a, v)
            open_now.append((b, stroke, sgn))
        open_prev = open_now
    out = []
    for st in strokes:
        uv = np.concatenate(st["parts"])
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
    """Xoắn ốc Archimedes từ tâm ảnh, bước pitch_mm; cắt theo mặt nạ. Mỗi đoạn True là một nét.

    Mỗi nét tốn một lần nhấc + hạ bút (~0,25 s = ~20 mm vẽ ở 5000 mm/min), nên nối qua khe trắng tới
    6 × bước (tối thiểu BRIDGE_MM) và bỏ mẩu ngắn hơn 4 × bước (gần như không thấy)."""
    cx, cy = f.width_mm / 2, f.height_mm / 2
    r_max = math.hypot(cx, cy) + pitch_mm
    step = max(f.px_mm * 0.7, 1e-3)
    total = math.pi * r_max * r_max / pitch_mm                  # chiều dài xấp xỉ
    n = int(total / step) + 1
    strokes = []
    bridge = max(BRIDGE_MM, SPIRAL_BRIDGE_PITCHES * pitch_mm)
    min_run = max(MIN_RUN_MM, SPIRAL_MIN_PITCHES * pitch_mm)
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
            if merged and (a0 - merged[-1][1]) * step <= bridge:
                merged[-1][1] = a1                              # nối qua khe trắng ngắn
            else:
                merged.append([a0, a1])
        for a0, a1 in merged:
            if (a1 - a0) * step >= min_run:
                strokes.append(np.stack([x[a0:a1 + 1], y[a0:a1 + 1]], axis=1))
    return strokes
