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

LINE_WIDTH_RATIO = 1.375         # nét thật ÷ cỡ ngòi: Sakura 0,4 ra nét ~0,55 mm (đo trên tờ hiệu chỉnh, mực loang)
DEFAULT_SPACING_PEN = 2.0        # khoảng cách nét mặc định = 2 × bề rộng nét thật (một lớp phủ ~50% mực)
WAVE_AMPLITUDE_RATIO = 0.18      # biên độ sóng = 0,18 × khoảng cách nét (nhỏ hơn thì ít nét hơn, đúng tông hơn; mô phỏng 03/11/2026)


def spacing_of(style, pen_mm: float) -> float:
    """Khoảng cách nét tham chiếu: một lớp gạch cách chừng này phủ ~50% mực."""
    if style.spacing_mm is not None:
        return style.spacing_mm
    return DEFAULT_SPACING_PEN * LINE_WIDTH_RATIO * pen_mm


MAX_COVERAGE = 0.9               # mức đậm nhất vẽ được bằng một lượt (cách ~0,62 mm với nét 0,55 mm: gần đặc)


def level_plan(levels: int, line_w: float, scale: float = 1.0) -> list[tuple[float, float, float]]:
    """Kế hoạch tô: [(đậm từ, đậm tới, khoảng cách nét mm)], mỗi dải một lượt gạch với khoảng cách riêng.

    `levels` mức sáng tối = `levels` bậc nhìn thấy (bậc 0 = giấy trắng, không vẽ). Độ phủ mục tiêu tăng đều
    0 -> MAX_COVERAGE nên các bậc cách đều nhau về độ đậm; nét dày `line_w` cách s phủ line_w / s, suy ra
    s = line_w / độ phủ. Ranh giới dải nằm giữa hai độ phủ kề nhau (mỗi vùng nhận bậc gần độ đậm của nó nhất).
    Mỗi chỗ chỉ một lượt nên ít nét hơn kiểu chồng nhiều lớp (mô phỏng: -37 % chiều dài, sai số một nửa).
    `scale` kéo giãn mọi khoảng cách (người dùng đặt khoảng cách khác mặc định).
    """
    n = max(1, levels - 1)
    cover = [MAX_COVERAGE * k / n for k in range(1, levels)]
    lows = [((cover[k - 1] if k else 0.0) + cover[k]) / 2 for k in range(levels - 1)]
    highs = lows[1:] + [math.inf]
    return [(lo, hi, max(0.1, scale * line_w / c)) for lo, hi, c in zip(lows, highs, cover)]


def _flat(groups: list[list[Stroke]]) -> list[Stroke]:
    return [s for g in groups for s in g]


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
    """(mặt nạ, góc, khoảng cách nét) cho từng dải đậm nhạt; các mặt nạ không chồng nhau."""
    s_ref = spacing_of(style, pen_mm)
    line_w = LINE_WIDTH_RATIO * pen_mm
    plan = level_plan(style.levels, line_w, s_ref / (DEFAULT_SPACING_PEN * line_w))
    base = style.angle if angle is None else angle
    ge: dict[float, np.ndarray] = {}                       # mặt nạ "đậm >= ngưỡng", làm mịn cùng một cỡ
    for lo, hi, _ in plan:
        for t in (lo, hi):
            if t != math.inf and t not in ge:
                if ctx:
                    ctx.check()
                ge[t] = hatch.level_mask(f, t, s_ref)
    for lo, hi, s in plan:
        mask = ge[lo] if hi == math.inf else ge[lo] & ~ge[hi]
        if mask.any():
            yield mask, base % 180.0, s


# Mỗi kiểu có hai dạng: `*_groups` trả [nhóm của mức nhạt nhất, ..., nhóm của mức đậm nhất] (mỗi nhóm là một danh sách nét),
# còn hàm đăng ký ở FILLERS trả danh sách phẳng (như cũ). `fill_groups` cho bước tối ưu sắp xếp RIÊNG từng mức, để bút vẽ
# lần lượt từng mức đậm nhạt thay vì nhảy qua lại giữa các mức (xem raster.py, tùy chọn optimize.group_levels).
def zigzag_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    groups = []
    for mask, a, s in _passes(f, style, pen_mm, ctx, angle):
        d, n, vmin, lines = hatch.scan_runs(mask, f, a, s)
        groups.append(_clip_out(hatch.serpentine(d, n, vmin, lines, s), f))
    return groups


@FILLERS.register("zigzag")
def zigzag(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(zigzag_groups(f, style, pen_mm, ctx, angle))


def wave_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    passes = []
    for mask, a, s in _passes(f, style, pen_mm, ctx, angle):
        amp = style.amplitude_mm if style.amplitude_mm is not None else WAVE_AMPLITUDE_RATIO * s
        amp = min(amp, 0.5 * s)                              # sóng kề nhau không chạm nhau
        passes.append((amp, s) + tuple(hatch.scan_runs(mask, f, a, s)))
    # Bước sóng: tối thiểu 6 lần biên độ / 6 lần bề rộng bút; dài hơn nếu tổng chiều dài nét sẽ làm vượt
    # ngân sách điểm (mỗi chu kỳ 5 điểm). Ảnh đậm nhiều thì sóng thưa hơn chứ không vượt giới hạn G-code.
    total = sum(u1 - u0 for *_, lines in passes for runs in lines for u0, u1 in runs)
    budget_wl = 5.0 * total / hatch.WAVE_POINT_BUDGET
    groups = []
    for amp, s, d, n, vmin, lines in passes:
        wavelength = max(6.0 * amp, 6.0 * pen_mm, budget_wl)
        groups.append(_clip_out(hatch.serpentine(d, n, vmin, lines, s, hatch.sine_shape(amp, wavelength, wavelength / 5)), f))
    return groups


@FILLERS.register("wave")
def wave(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(wave_groups(f, style, pen_mm, ctx, angle))


def spiral_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    groups = []
    for mask, _angle, s in _passes(f, style, pen_mm, ctx, angle):
        groups.append(_clip_out(hatch.spiral_runs(mask, f, s), f))
    return groups


@FILLERS.register("spiral")
def spiral(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(spiral_groups(f, style, pen_mm, ctx, angle))


GROUPERS = {"zigzag": zigzag_groups, "wave": wave_groups, "spiral": spiral_groups}


@FILLERS.register("outline")
def outline(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    """Nét viền phác họa (edges.py): nét mực + ranh giới mảng sáng tối / màu + nối khe hở -> nét liền."""
    skel = edges.outline_mask(f.dark, f.rgb, f.width_mm / f.w, style.outline_detail, ctx)
    if ctx:
        ctx.check()
    return trace.to_strokes(skel, f.width_mm / f.w, f.height_mm / f.h, min_len_mm=max(1.0, 3.0 * pen_mm))


def fill_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None,
                overlay: bool | None = None) -> list[list[Stroke]]:
    """Nét tô chia nhóm theo mức đậm nhạt (nhạt → đậm), nhóm viền (nếu có) cuối cùng. Nhóm rỗng bị bỏ.
    `angle` ghi đè góc gạch (mỗi màu một góc); `overlay` ghi đè outline_overlay (đa màu chỉ phủ viền một lần)."""
    grouper = GROUPERS.get(style.kind)
    groups = grouper(f, style, pen_mm, ctx, angle) if grouper else [FILLERS.get(style.kind)(f, style, pen_mm, ctx, angle)]
    if overlay is None:
        overlay = style.outline_overlay
    if overlay and style.kind != "outline":     # viền vẽ SAU cùng cho nét rõ
        if ctx:
            ctx.check()
        groups = groups + [outline(f, style, pen_mm, ctx)]
    return [g for g in groups if g]


def fill(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None,
         overlay: bool | None = None) -> list[Stroke]:
    """Như fill_groups nhưng một danh sách phẳng (thứ tự: mức nhạt → đậm, viền cuối)."""
    return _flat(fill_groups(f, style, pen_mm, ctx, angle, overlay))
