"""Kiểu tô: zigzag, sóng, xoắn ốc. Mỗi kiểu nhận Field (độ đậm) -> danh sách nét (mm).

Thêm kiểu mới = một hàm đăng ký @FILLERS.register("tên") + thêm tên vào spec.STYLES.
"""
from __future__ import annotations

import math

import numpy as np

from . import edges, hatch, trace
from .hatch import Field
from .registry import FILLERS
from .shapes import Stroke

DEFAULT_SPACING_PEN = 2.0        # khoảng cách nét mặc định = 2 × bề rộng bút


def spacing_of(style, pen_mm: float) -> float:
    return style.spacing_mm if style.spacing_mm is not None else DEFAULT_SPACING_PEN * pen_mm


def _clip_out(arrays: list[np.ndarray], f: Field) -> list[Stroke]:
    out: list[Stroke] = []
    for a in arrays:
        if len(a) < 2:
            continue
        x = np.clip(a[:, 0], 0.0, f.width_mm)
        y = np.clip(a[:, 1], 0.0, f.height_mm)
        out.append([(float(px), float(py)) for px, py in zip(np.round(x, 3), np.round(y, 3))])
    return out


def _passes(f: Field, style, pen_mm: float, ctx, angle: float | None = None):
    """(mặt nạ, góc, pha) cho từng lượt tô."""
    s = spacing_of(style, pen_mm)
    levels = style.levels
    step = 180.0 / levels
    base = style.angle if angle is None else angle
    ts = hatch.thresholds(levels)
    for j, t in enumerate(ts):
        if ctx:
            ctx.check()
        mask = hatch.level_mask(f, t, s)
        if mask.any():
            yield mask, (base + j * step) % 180.0, (j * 0.5) % 1.0


@FILLERS.register("zigzag")
def zigzag(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    s = spacing_of(style, pen_mm)
    out: list[np.ndarray] = []
    for mask, angle, phase in _passes(f, style, pen_mm, ctx, angle):
        d, n, vmin, lines = hatch.scan_runs(mask, f, angle, s, phase)
        out += hatch.serpentine(d, n, vmin, lines, s)
    return _clip_out(out, f)


@FILLERS.register("wave")
def wave(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    s = spacing_of(style, pen_mm)
    amp = style.amplitude_mm if style.amplitude_mm is not None else 0.35 * s
    amp = min(amp, 0.5 * s)                                     # sóng kề nhau không chạm nhau
    passes = [(d, n, vmin, lines) for mask, a, phase in _passes(f, style, pen_mm, ctx, angle)
              for d, n, vmin, lines in [hatch.scan_runs(mask, f, a, s, phase)]]
    # Bước sóng: tối thiểu 6 lần biên độ / 6 lần bề rộng bút; dài hơn nếu tổng chiều dài nét sẽ làm vượt
    # ngân sách điểm (mỗi chu kỳ 5 điểm). Ảnh đậm nhiều thì sóng thưa hơn chứ không vượt giới hạn G-code.
    total = sum(u1 - u0 for _, _, _, lines in passes for runs in lines for u0, u1 in runs)
    wavelength = max(6.0 * amp, 6.0 * pen_mm, 5.0 * total / hatch.WAVE_POINT_BUDGET)
    shape = hatch.sine_shape(amp, wavelength, wavelength / 5)
    out: list[np.ndarray] = []
    for d, n, vmin, lines in passes:
        out += hatch.serpentine(d, n, vmin, lines, s, shape)
    return _clip_out(out, f)


@FILLERS.register("spiral")
def spiral(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    s = spacing_of(style, pen_mm)
    out: list[np.ndarray] = []
    for mask, _angle, phase in _passes(f, style, pen_mm, ctx, angle):
        out += hatch.spiral_runs(mask, f, s, phase)
    return _clip_out(out, f)


@FILLERS.register("outline")
def outline(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    """Nét viền phác họa: DoG -> skeleton -> nét liền theo đường giữa."""
    skel = trace.skeleton(edges.ink_mask(f.dark), min_pixels=8)
    if ctx:
        ctx.check()
    return trace.to_strokes(skel, f.width_mm / f.w, f.height_mm / f.h, min_len_mm=max(1.0, 3.0 * pen_mm))


def fill(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None,
         overlay: bool | None = None) -> list[Stroke]:
    """`angle` ghi đè góc gạch (mỗi màu một góc); `overlay` ghi đè outline_overlay (đa màu chỉ phủ viền một lần)."""
    strokes = FILLERS.get(style.kind)(f, style, pen_mm, ctx, angle)
    if overlay is None:
        overlay = style.outline_overlay
    if overlay and style.kind != "outline":     # viền vẽ SAU cùng cho nét rõ
        if ctx:
            ctx.check()
        strokes = strokes + outline(f, style, pen_mm, ctx)
    return strokes
