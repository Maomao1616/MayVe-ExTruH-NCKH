"""Kiểu tô: zigzag, sóng, xoắn ốc, gạch chéo chồng lớp, sóng biến thiên. Mỗi kiểu nhận Field (độ đậm) -> danh sách nét (mm).

Thêm kiểu mới = một hàm đăng ký @FILLERS.register("tên") + thêm tên vào spec.STYLES.
"""
from __future__ import annotations

import math

import numpy as np

from . import edges, hatch, trace
from .hatch import Field
from .registry import FILLERS
from .shapes import Stroke

# Nét thật ÷ số trong ô "Bút vẽ". Từ 11/11/2026 ô đó ghi thẳng BỀ RỘNG NÉT ĐO TRÊN GIẤY của từng bút (đo bằng tờ hiệu
# chỉnh), nên hệ số = 1,0. Lịch sử: 1,375 (Sakura 0,4 loang 0,55 trên giấy thường), 1,1 (ước tính trên Ivory 250 g/m²).
# Muốn đổi bề rộng nét của một bút thì sửa danh sách bút (index.html, ô draw-pen-width), không sửa số này.
LINE_WIDTH_RATIO = 1.0
DEFAULT_SPACING_PEN = 2.0        # khoảng cách nét mặc định = 2 × bề rộng nét thật (một lớp phủ ~50% mực)
WAVE_AMPLITUDE_RATIO = 0.18      # biên độ sóng = 0,18 × khoảng cách nét (nhỏ hơn thì ít nét hơn, đúng tông hơn; mô phỏng 03/11/2026)


def spacing_of(style, pen_mm: float) -> float:
    """Khoảng cách nét tham chiếu: một lớp gạch cách chừng này phủ ~50% mực."""
    if style.spacing_mm is not None:
        return style.spacing_mm
    return DEFAULT_SPACING_PEN * LINE_WIDTH_RATIO * pen_mm


MAX_COVERAGE = 0.9               # mức đậm nhất vẽ được bằng một lượt (cách ~0,49 mm với nét 0,44 mm: gần đặc)


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


SOFT_SPREAD = 0.9               # chuyển mức mềm: dải giáp ranh rộng 0,9 × nửa bước độ phủ về mỗi phía (gần như nối liền hai mức)
SOFT_WHITE = 0.5                 # phía giáp giấy trắng chỉ lệch một nửa: vùng gần trắng không bị vài dòng lẻ tẻ chạy qua
SOFT_TURN_MM = 2.0               # nối sang dòng cách xa hơn 1 dòng chỉ khi vòng quay đầu cao ≤ 2 mm (đoạn nối là mực thừa)


def _passes(f: Field, style, pen_mm: float, ctx, angle: float | None = None):
    """(mặt nạ, góc, khoảng cách nét) cho từng dải đậm nhạt.

    Cứng (soft_levels = false): mỗi dải một mặt nạ, các mặt nạ không chồng nhau, ranh giới là một đường.
    Mềm (mặc định): mỗi dải 8 mặt nạ, dòng gạch thứ i dùng mặt nạ i % 8 có ngưỡng lệch riêng (hatch.dither_offsets).
    Ở chỗ giáp hai mức, dòng của mức nhạt thưa dần còn dòng của mức đậm dày dần: độ đậm chuyển liền."""
    s_ref = spacing_of(style, pen_mm)
    line_w = LINE_WIDTH_RATIO * pen_mm
    plan = level_plan(style.levels, line_w, s_ref / (DEFAULT_SPACING_PEN * line_w))
    base = style.angle if angle is None else angle
    soft = getattr(style, "soft_levels", False)
    step = MAX_COVERAGE / max(1, style.levels - 1)          # khoảng cách độ phủ giữa hai mức kề nhau
    offsets = hatch.dither_offsets(SOFT_SPREAD * step / 2) if soft else [0.0]
    d = hatch.blur(f, s_ref)                                # làm mờ một lần, mọi ngưỡng dùng chung
    ge: dict[float, np.ndarray] = {}                        # mặt nạ "đậm >= ngưỡng"

    def mask_ge(t: float) -> np.ndarray:
        if t not in ge:
            if ctx:
                ctx.check()
            ge[t] = hatch.threshold_mask(d, t, s_ref, f.px_mm)
        return ge[t]

    for index, (lo, hi, s) in enumerate(plan):
        masks = []
        for off in offsets:
            low = mask_ge(lo + off * (SOFT_WHITE if index == 0 else 1.0))
            masks.append(low if hi == math.inf else low & ~mask_ge(hi + off))
        if any(m.any() for m in masks):
            yield (masks if soft else masks[0]), base % 180.0, s


# Mỗi kiểu có hai dạng: `*_groups` trả [nhóm của mức nhạt nhất, ..., nhóm của mức đậm nhất] (mỗi nhóm là một danh sách nét),
# còn hàm đăng ký ở FILLERS trả danh sách phẳng (như cũ). `fill_groups` cho bước tối ưu sắp xếp RIÊNG từng mức, để bút vẽ
# lần lượt từng mức đậm nhạt thay vì nhảy qua lại giữa các mức (xem raster.py, tùy chọn optimize.group_levels).
def _link(d, n, vmin, lines, s: float, soft: bool, shape=None) -> list[np.ndarray]:
    """Nối các đoạn gạch thành nét liền. Cứng: serpentine (dòng kề nhau). Mềm: các dòng kết thúc so le nên nối cả sang
    dòng cách 2–8 dòng (hatch.join_rows), không thì mỗi đoạn thành một nét riêng, nhấc bút gấp ~10 lần."""
    if not soft:
        return hatch.serpentine(d, n, vmin, lines, s, shape)
    make = shape or (lambda a, b, v: np.array([[a, v], [b, v]]))
    rows = [[make(u0, u1, vmin + i * s) for u0, u1 in runs] for i, runs in enumerate(lines)]
    joined = hatch.join_rows(rows, s, hatch.DITHER_RANKS, max_turn_mm=SOFT_TURN_MM, fixed_reach=True)
    return [hatch.uv_to_xy(d, n, uv) for uv in joined]


def zigzag_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    groups = []
    for mask, a, s in _passes(f, style, pen_mm, ctx, angle):
        d, n, vmin, lines = hatch.scan_runs(mask, f, a, s)
        groups.append(_clip_out(_link(d, n, vmin, lines, s, isinstance(mask, list)), f))
    return groups


@FILLERS.register("zigzag")
def zigzag(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(zigzag_groups(f, style, pen_mm, ctx, angle))


def wave_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    passes = []
    for mask, a, s in _passes(f, style, pen_mm, ctx, angle):
        amp = style.amplitude_mm if style.amplitude_mm is not None else WAVE_AMPLITUDE_RATIO * s
        amp = min(amp, 0.5 * s)                              # sóng kề nhau không chạm nhau
        passes.append((amp, s, isinstance(mask, list)) + tuple(hatch.scan_runs(mask, f, a, s)))
    # Bước sóng: tối thiểu 6 lần biên độ / 6 lần bề rộng bút; dài hơn nếu tổng chiều dài nét sẽ làm vượt
    # ngân sách điểm (mỗi chu kỳ 5 điểm). Ảnh đậm nhiều thì sóng thưa hơn chứ không vượt giới hạn G-code.
    total = sum(u1 - u0 for *_, lines in passes for runs in lines for u0, u1 in runs)
    budget_wl = 5.0 * total / hatch.WAVE_POINT_BUDGET
    groups = []
    for amp, s, soft, d, n, vmin, lines in passes:
        wavelength = max(6.0 * amp, 6.0 * pen_mm, budget_wl)
        shape = hatch.sine_shape(amp, wavelength, wavelength / 5)
        groups.append(_clip_out(_link(d, n, vmin, lines, s, soft, shape), f))
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


# --- Gạch chéo chồng lớp: tông nhạt một hướng, tông đậm thêm lớp thứ hai vuông góc -------------------------------
CROSS_START = 0.45               # độ phủ bắt đầu thêm lớp thứ hai (dưới mức này chỉ một hướng như zigzag)
CROSS_SLOPE = 0.5                # trên CROSS_START, lớp một chỉ tăng nửa phần, phần còn lại do lớp hai gánh
CROSS_ANGLE = 90.0               # lớp hai lệch góc này so với lớp một


def cross_split(dark: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Độ phủ mong muốn T -> (độ phủ lớp một, độ phủ lớp hai) sao cho 1 - (1 - a)(1 - b) = T (hai lớp chồng chéo).

    T = 0,9 (đậm nhất): mỗi lớp ~0,68, tức mỗi hướng cách ~0,65 mm thay vì một hướng cách 0,49 mm: ít ướt giấy hơn."""
    t = np.minimum(dark, MAX_COVERAGE)
    a = np.where(t <= CROSS_START, t, CROSS_START + (t - CROSS_START) * CROSS_SLOPE)
    b = np.where(t <= CROSS_START, 0.0, 1.0 - (1.0 - t) / np.maximum(1.0 - a, 1e-6))
    return a.astype(np.float32), np.clip(b, 0.0, 1.0).astype(np.float32)


def crosshatch_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    """Hai lượt zigzag (mỗi lượt đủ các mức, chuyển mức mềm nếu bật): lớp một ở góc gạch, lớp hai lệch CROSS_ANGLE chỉ
    ở vùng đậm. Thứ tự vẽ: hết lớp một (nhạt → đậm) rồi mới lớp hai, mực lớp dưới có thời gian khô."""
    a, b = cross_split(f.dark)
    base = style.angle if angle is None else angle
    first = zigzag_groups(Field(a, f.width_mm, f.height_mm), style, pen_mm, ctx, base)
    second = zigzag_groups(Field(b, f.width_mm, f.height_mm), style, pen_mm, ctx, (base + CROSS_ANGLE) % 180.0)
    return first + second


@FILLERS.register("crosshatch")
def crosshatch(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(crosshatch_groups(f, style, pen_mm, ctx, angle))


# --- Đan 3 hướng: như gạch chéo nhưng ba lớp lệch nhau 60° (12/11/2026, chủ dự án đề xuất) --------------------------
CROSS3_START2 = 0.35             # độ phủ bắt đầu thêm lớp hai (sớm hơn gạch chéo 0,45: ba hướng chia nhau gánh tông)
CROSS3_START3 = 0.65             # độ phủ bắt đầu thêm lớp ba
CROSS3_SLOPE = 0.5               # sau khi lớp kế tiếp vào, lớp trước chỉ tăng nửa phần
CROSS3_ANGLE = 60.0              # ba lớp ở góc gạch, +60°, +120°


def cross3_split(dark: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Độ phủ mong muốn T -> (a, b, c) của ba lớp sao cho 1 - (1 - a)(1 - b)(1 - c) = T.

    T = 0,9 (đậm nhất): a ≈ 0,63, b ≈ 0,43, c ≈ 0,54 — mỗi hướng thưa hơn gạch chéo (~0,68): mực ít đọng hơn, mặt đậm
    nhìn như lưới tam giác thay vì ô vuông."""
    t = np.minimum(dark, MAX_COVERAGE)
    s2, s3, k = CROSS3_START2, CROSS3_START3, CROSS3_SLOPE
    a = np.where(t <= s2, t, s2 + (t - s2) * k)
    a3 = s2 + (s3 - s2) * k                                       # lớp một tại lúc lớp ba bắt đầu
    b_at3 = 1.0 - (1.0 - s3) / (1.0 - a3)                         # lớp hai tại lúc lớp ba bắt đầu
    b = np.where(t <= s2, 0.0,
                 np.where(t <= s3, 1.0 - (1.0 - t) / np.maximum(1.0 - a, 1e-6), b_at3 + (t - s3) * k))
    c = np.where(t <= s3, 0.0, 1.0 - (1.0 - t) / np.maximum((1.0 - a) * (1.0 - b), 1e-6))
    return tuple(np.clip(x, 0.0, 1.0).astype(np.float32) for x in (a, b, c))


def crosshatch3_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    """Ba lượt zigzag (mỗi lượt đủ các mức, chuyển mức mềm nếu bật), lớp sau chỉ ở vùng đậm hơn; vẽ hết lớp này mới
    sang lớp kia."""
    base = style.angle if angle is None else angle
    groups: list[list[Stroke]] = []
    for i, part in enumerate(cross3_split(f.dark)):
        if part.max() > 0:
            groups += zigzag_groups(Field(part, f.width_mm, f.height_mm), style, pen_mm, ctx,
                                    (base + i * CROSS3_ANGLE) % 180.0)
    return groups


@FILLERS.register("crosshatch3")
def crosshatch3(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(crosshatch3_groups(f, style, pen_mm, ctx, angle))


# --- Sóng biến thiên: một lưới sóng, độ đậm đổi liền (không chia mức) ---------------------------------------------
AM_SPACING_LINES = 4.0           # khoảng cách các đường sóng = 4 × nét thật (bút 0,4: 1,76 mm); đường thẳng phủ 25 %
AM_AMPLITUDE = 0.45              # biên độ tối đa = 0,45 × khoảng cách đường: hai đường kề nhau gần chạm nhau ở chỗ đậm nhất
AM_WAVE_LINES = 2.0              # bước sóng (cố định) = 2 × nét thật: hai sườn sóng vừa đủ không đè lên nhau. Cố định để mọi
                                 # đường cùng pha, song song nhau (thử 11/11: bước sóng đổi theo độ đậm làm các đường cắt nhau
                                 # thành lưới rối)
AM_DITHER = 0.35                 # dòng thưa / dày xuất hiện so le trong ±35 % quanh ngưỡng của nó
AM_WHITE = 0.6                   # dưới 0,6 × độ phủ của lưới thưa nhất thì để giấy trắng
AM_MIN_RUN = 3.0                 # bỏ đoạn sóng ngắn hơn 3 × khoảng cách đường (~5 mm), lấp khe ngắn hơn một nửa mức đó:
                                 # gạch vụn ở vùng sáng mỗi cái tốn một lần nhấc bút


def _am_tier(i: int) -> tuple[int, int]:
    """Dòng i thuộc lưới nào: 0 = cách 4 dòng (luôn có, trừ chỗ trắng), 1 = cách 2 dòng, 2 = các dòng lẻ. Kèm số thứ tự
    của dòng trong lưới đó (để lấy độ lệch ngưỡng so le)."""
    if i % 4 == 0:
        return 0, i // 4
    if i % 2 == 0:
        return 1, i // 4
    return 2, i // 2


def wave_am_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    """Mỗi đường sóng đổi biên độ liên tục theo độ đậm (bước sóng cố định): chỗ nào đậm thì sóng cao, đường dài ra nên
    phủ nhiều mực hơn. Vùng sáng hơn mức một lưới đường thẳng phủ được thì bớt dần đường (còn 1/2, rồi 1/4), các đường
    bớt đi kết thúc so le. Không có ngưỡng chia mức nên không có ranh giới mức; đổi lại vùng đậm nhiều chỗ đổi hướng,
    máy vẽ chậm hơn zigzag."""
    line_w = LINE_WIDTH_RATIO * pen_mm
    s0 = style.spacing_mm if style.spacing_mm is not None else AM_SPACING_LINES * line_w
    c_base = min(MAX_COVERAGE, line_w / s0)                 # độ phủ khi mọi đường đều thẳng
    thresholds = (AM_WHITE * c_base / 4, c_base / 2, c_base)   # lưới 0 / 1 / 2 có mặt từ độ phủ này
    offsets = hatch.dither_offsets(AM_DITHER)
    a = style.angle if angle is None else angle
    cov = np.minimum(hatch.blur(f, s0 / 2), MAX_COVERAGE)

    def row_threshold(i: int) -> float:
        tier, k = _am_tier(i)
        return thresholds[tier] * (1.0 + offsets[k % len(offsets)])

    def present(c: np.ndarray, tier: int) -> np.ndarray:
        t = thresholds[tier]
        return np.clip((c - t * (1 - AM_DITHER)) / (2 * AM_DITHER * t), 0.0, 1.0)

    def local_cover(c: np.ndarray) -> np.ndarray:            # độ phủ trung bình của các đường thẳng đang có mặt
        return c_base * (0.25 + 0.25 * present(c, 1) + 0.5 * present(c, 2))

    wave = AM_WAVE_LINES * line_w
    if ctx:
        ctx.check()
    d, n, rows = hatch.am_wave_rows(cov, f, a % 180.0, s0, row_threshold, local_cover, AM_AMPLITUDE * s0,
                                    wave, wave, AM_MIN_RUN * s0)
    # Chỉ nối khi quay đầu và hai đầu gần thẳng hàng (thường ở mép ảnh), vòng tối đa 2 khoảng cách đường. Nối chỗ khác
    # (giữa vùng sáng, hai đường kết thúc so le) ra các móc chữ U / Z lạc lõng: thà nhấc bút (thử 11/11/2026).
    joined = hatch.join_rows(rows, s0, max_turn_mm=2 * s0, reach_mm=s0, turn_only=True)
    strokes = [hatch.uv_to_xy(d, n, uv) for uv in joined]
    return [_clip_out(strokes, f)]


@FILLERS.register("wave_am")
def wave_am(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(wave_am_groups(f, style, pen_mm, ctx, angle))


GROUPERS = {"zigzag": zigzag_groups, "wave": wave_groups, "spiral": spiral_groups,
            "crosshatch": crosshatch_groups, "crosshatch3": crosshatch3_groups, "wave_am": wave_am_groups}


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
