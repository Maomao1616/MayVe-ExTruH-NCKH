"""Kiểu tô: mỗi kiểu nhận Field (độ đậm) -> danh sách nét (mm).

Mục lục (14/11/2026; danh sách hiện trên giao diện = spec.UI_STYLES, các kiểu ẩn vẫn chạy cho bản thảo cũ / làm nền):
  A. Nền dùng chung     level_plan (chia mức), đường cong tông (tone_cover), _passes / _link (mặt nạ từng mức, nối dòng),
                        zigzag_groups (một lượt gạch: nền của đan chéo và lớp đậm của sóng biên độ)
  B. Kiểu đang hiện     crosshatch       Gạch chéo chồng lớp (Chân dung, kèm lớp viền FDoG)
                        flow             Theo dáng ảnh (flow field, lõi ở flow.py; hiện lại 14/11/2026)
                        wave_am          Sóng biên độ (Phong cảnh)
                        spiral           Xoắn ốc (Cận cảnh)
                        outline          Nét viền (Ảnh 2D, Schematic; thuật toán ở edges.py / trace.py)
  C. Kiểu đã ẩn         zigzag (13/11: đan chéo đẹp hơn), wave (sóng thường, như trên), crosshatch3 (đan 3 hướng: tông
                        như đan chéo, nét rối hơn), crosshatch_flow (đan chéo + viền hàng rào; 14/11 chủ dự án: khối rối,
                        lệch tông hơn đan chéo + lớp viền -> tách đan chéo / theo dáng thành hai kiểu)
Hiện lại một kiểu ẩn = thêm tên vào spec.UI_STYLES + một dòng <option> ở index.html (ô style-kind) + khóa dịch vi / en.
Thêm kiểu mới = một hàm đăng ký @FILLERS.register("tên") + tên vào spec.STYLES (+ GROUPERS nếu chia nhóm theo mức).
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


# --- Đường cong tông (docs/10 mục 0.3, T3–T4) ------------------------------------------------------------------------
# Đo 13/11/2026: tờ hiệu chỉnh tông, Sakura 0,5, mặt bóng Ivory 250 g/m², 8000 mm/phút, chụp điện thoại, đọc 60 % giữa
# mỗi ô, chuẩn hóa theo giấy quanh ô và 3 ô mốc đen, độ đậm theo CIE L* (mắt thấy). Ô có độ phủ TONE_COVERS[i] (calibration.
# TONE_STEPS) trông đậm TONE_CURVES[kiểu][i] (0 = giấy, 1 = ô mốc đen; đã trừ ô giấy, làm cho tăng dần).
# Đọc: vùng trung bình trông NHẠT hơn độ phủ (phủ 50 % đan chéo chỉ thấy 0,39) -> trước đây phải hạ gamma bù tay.
# Dùng: độ đậm ảnh d (0..1) = độ đậm mắt thấy mong muốn (tỷ lệ với đường cong ở MAX_COVERAGE), tra NGƯỢC ra độ phủ cần vẽ.
# Các kiểu không có bảng giữ cách cũ (độ phủ = độ đậm ảnh). Bút / giấy khác: đo tờ mới, thêm bảng.
TONE_COVERS = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80, 0.90)
TONE_CURVES = {
    # đan chéo (đan 3 hướng đo gần trùng, lệch <= 0,03; zigzag chưa áp: chủ dự án chỉ chọn đan chéo + xoắn ốc 13/11)
    "crosshatch": (0.0, 0.041, 0.073, 0.103, 0.113, 0.154, 0.194, 0.244, 0.246, 0.325, 0.374, 0.436, 0.437, 0.624, 0.787,
                   0.931),
    # xoắn ốc: đậm nhanh, gần chạm trần từ 70 % (vòng chồng nhau thành vệt chữ thập ở ô đậm)
    "spiral": (0.0, 0.023, 0.086, 0.107, 0.163, 0.193, 0.266, 0.319, 0.380, 0.452, 0.552, 0.683, 0.712, 0.804, 0.822,
               0.927),
}
TONE_CURVE_STYLES = {"crosshatch": "crosshatch", "spiral": "spiral", "crosshatch_flow": "crosshatch"}
USE_TONE_CURVE = True            # False = bỏ đường cong (độ phủ = độ đậm ảnh như trước 13/11/2026)
TONE_CURVE_STRENGTH = 0.75       # áp 75 % đường cong. Mô phỏng (tools/ink_sim.py, cột "sai mắt"; đan chéo): áp đủ thì ô đậm
                                 # ĐỀU đúng nhất (sai 0,14 -> 0,05) nhưng dải chuyển liền đậm quá (0,037 -> 0,047, chỗ giáp hai
                                 # mức các dòng chồng nhau); 0,75: ô đều 0,071, dải 0,033. Xoắn ốc cũng tốt nhất ở 0,75


def tone_cover(dark: np.ndarray, kind: str) -> np.ndarray:
    """Độ đậm ảnh -> độ phủ cần vẽ theo đường cong tông của kiểu `kind` (không có bảng thì trả nguyên)."""
    table = TONE_CURVES.get(TONE_CURVE_STYLES.get(kind, ""))
    if not USE_TONE_CURVE or table is None:
        return dark
    covers = np.asarray(TONE_COVERS, np.float64)
    seen = np.maximum.accumulate(np.asarray(table, np.float64)) + 1e-4 * np.arange(len(table))   # tăng ngặt để tra ngược
    v_max = float(np.interp(MAX_COVERAGE, covers, seen))
    want = np.clip(dark, 0.0, None) * (v_max / MAX_COVERAGE)                 # d = MAX_COVERAGE vẫn ra độ phủ MAX_COVERAGE
    out = np.interp(want, seen, covers, right=MAX_COVERAGE)
    out = dark + TONE_CURVE_STRENGTH * (out - dark)
    return np.where(dark >= MAX_COVERAGE, dark, out).astype(np.float32)


def _toned(f: Field, kind: str) -> Field:
    if not USE_TONE_CURVE or TONE_CURVE_STYLES.get(kind) is None:
        return f
    return Field(tone_cover(f.dark, kind), f.width_mm, f.height_mm, f.rgb)


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
# Bớt "râu" kiểu gạch / đan chéo (14/11/2026, ảnh chân dung A4 bút 0,4 của chủ dự án; đo tools/style_preview.py):
# dải đậm hẹp (song cửa, sợi tóc) gạch thành răng cưa, mẩu gạch 0,3–1,5 mm thành chấm lẻ, dòng ngắn nối chéo thành bậc
# thang. Bỏ cả ba: đan chéo 1120 -> 942 nét, 19,4 -> 17,1 phút. Chủ dự án: chi tiết đậm hẹp mất đi trông gọn hơn.
HATCH_THIN_SPACINGS = 1.5        # dải đậm hẹp hơn 1,5 × khoảng cách nét (bút 0,4: 1,2 mm) không gạch. 2,5 (14/11 bản đầu)
                                 # làm mất mắt, mũi khi không có viền (chủ dự án xem bản thảo)
HATCH_MIN_RUN_MM = 1.5           # mẩu gạch ngắn hơn chừng này bỏ (trước: 0,3 mm)
HATCH_WHITE = 0.2                # độ phủ dưới mức này để giấy trắng hẳn, mép giáp trắng không so le: nổi chủ thể


def _passes(f: Field, style, pen_mm: float, ctx, angle: float | None = None, clean: bool = False,
            barrier: np.ndarray | None = None):
    """(mặt nạ, góc, khoảng cách nét) cho từng dải đậm nhạt.

    Cứng (soft_levels = false): mỗi dải một mặt nạ, các mặt nạ không chồng nhau, ranh giới là một đường.
    Mềm (mặc định): mỗi dải 8 mặt nạ, dòng gạch thứ i dùng mặt nạ i % 8 có ngưỡng lệch riêng (hatch.dither_offsets).
    Ở chỗ giáp hai mức, dòng của mức nhạt thưa dần còn dòng của mức đậm dày dần: độ đậm chuyển liền.
    `clean` (kiểu gạch / đan chéo): bỏ dải hẹp hơn HATCH_THIN_SPACINGS × khoảng cách, dưới HATCH_WHITE để trắng hẳn.
    `barrier`: mặt nạ đường viền; dòng gạch dừng ở viền, không tràn sang khối bên cạnh."""
    s_ref = spacing_of(style, pen_mm)
    line_w = LINE_WIDTH_RATIO * pen_mm
    plan = level_plan(style.levels, line_w, s_ref / (DEFAULT_SPACING_PEN * line_w))
    base = style.angle if angle is None else angle
    soft = getattr(style, "soft_levels", False)
    step = MAX_COVERAGE / max(1, style.levels - 1)          # khoảng cách độ phủ giữa hai mức kề nhau
    offsets = hatch.dither_offsets(SOFT_SPREAD * step / 2) if soft else [0.0]
    d = hatch.blur(f, s_ref)                                # làm mờ một lần, mọi ngưỡng dùng chung
    ge: dict[float, np.ndarray] = {}                        # mặt nạ "đậm >= ngưỡng"
    open_mm = HATCH_THIN_SPACINGS * s_ref if clean else None

    def mask_ge(t: float) -> np.ndarray:
        if t not in ge:
            if ctx:
                ctx.check()
            ge[t] = hatch.threshold_mask(d, t, s_ref, f.px_mm, open_mm, barrier)
        return ge[t]

    for index, (lo, hi, s) in enumerate(plan):
        masks = []
        for off in offsets:
            if index == 0 and clean:
                low = mask_ge(max(lo, HATCH_WHITE))                  # mép giáp giấy trắng: một đường, không so le
            else:
                low = mask_ge(lo + off * (SOFT_WHITE if index == 0 else 1.0))
            masks.append(low if hi == math.inf else low & ~mask_ge(hi + off))
        if any(m.any() for m in masks):
            yield (masks if soft else masks[0]), base % 180.0, s


# Mỗi kiểu có hai dạng: `*_groups` trả [nhóm của mức nhạt nhất, ..., nhóm của mức đậm nhất] (mỗi nhóm là một danh sách nét),
# còn hàm đăng ký ở FILLERS trả danh sách phẳng (như cũ). `fill_groups` cho bước tối ưu sắp xếp RIÊNG từng mức, để bút vẽ
# lần lượt từng mức đậm nhạt thay vì nhảy qua lại giữa các mức (xem raster.py, tùy chọn optimize.group_levels).
def _link(d, n, vmin, lines, s: float, soft: bool, shape=None, turn_only: bool = False) -> list[np.ndarray]:
    """Nối các đoạn gạch thành nét liền. Cứng: serpentine (dòng kề nhau). Mềm: các dòng kết thúc so le nên nối cả sang
    dòng cách 2–8 dòng (hatch.join_rows), không thì mỗi đoạn thành một nét riêng, nhấc bút gấp ~10 lần.
    `turn_only`: chỉ nối bằng vòng quay đầu, không kẻ đường chéo sang dòng khác (đường chéo = bậc thang ở mép mảng)."""
    if not soft:
        return hatch.serpentine(d, n, vmin, lines, s, shape)
    make = shape or (lambda a, b, v: np.array([[a, v], [b, v]]))
    rows = [[make(u0, u1, vmin + i * s) for u0, u1 in runs] for i, runs in enumerate(lines)]
    joined = hatch.join_rows(rows, s, hatch.DITHER_RANKS, max_turn_mm=SOFT_TURN_MM, fixed_reach=True, turn_only=turn_only)
    return [hatch.uv_to_xy(d, n, uv) for uv in joined]


# === A. Nền dùng chung (tiếp): một lượt gạch zigzag ===================================================================
def zigzag_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None,
                  barrier: np.ndarray | None = None) -> list[list[Stroke]]:
    groups = []
    for mask, a, s in _passes(f, style, pen_mm, ctx, angle, clean=True, barrier=barrier):
        d, n, vmin, lines = hatch.scan_runs(mask, f, a, s, min_run_mm=HATCH_MIN_RUN_MM)
        groups.append(_clip_out(_link(d, n, vmin, lines, s, isinstance(mask, list), turn_only=True), f))
    return groups


@FILLERS.register("zigzag")                 # C. ẩn khỏi giao diện 13/11/2026
def zigzag(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(zigzag_groups(f, style, pen_mm, ctx, angle))


# === C. Kiểu ẩn: sóng thường (13/11/2026) ===============================================================================
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


# === B. Xoắn ốc ===========================================================================================================
def spiral_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    f = _toned(f, "spiral")
    groups = []
    for mask, _angle, s in _passes(f, style, pen_mm, ctx, angle):
        groups.append(_clip_out(hatch.spiral_runs(mask, f, s), f))
    return groups


@FILLERS.register("spiral")
def spiral(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(spiral_groups(f, style, pen_mm, ctx, angle))


# === B. Gạch chéo chồng lớp: tông nhạt một hướng, tông đậm thêm lớp thứ hai vuông góc -------------------------------
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
    return _cross_layers(_toned(f, "crosshatch"), style, pen_mm, ctx, angle)


def _cross_layers(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None,
                  barrier: np.ndarray | None = None) -> list[list[Stroke]]:
    """Hai lớp đan chéo trên trường độ phủ ĐÃ áp đường cong tông. `barrier`: đường viền chặn dòng gạch."""
    a, b = cross_split(f.dark)
    base = style.angle if angle is None else angle
    first = zigzag_groups(Field(a, f.width_mm, f.height_mm), style, pen_mm, ctx, base, barrier)
    second = zigzag_groups(Field(b, f.width_mm, f.height_mm), style, pen_mm, ctx, (base + CROSS_ANGLE) % 180.0,
                           barrier)
    return first + second


@FILLERS.register("crosshatch")
def crosshatch(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(crosshatch_groups(f, style, pen_mm, ctx, angle))


# === C. Kiểu ẩn (13/11/2026): đan 3 hướng, như gạch chéo nhưng ba lớp lệch nhau 60° (12/11/2026, chủ dự án đề xuất) --------------------------
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


# === B. Sóng biến thiên (sóng biên độ): một lưới sóng, độ đậm đổi liền (không chia mức) ---------------------------------------------
AM_SPACING_LINES = 4.0           # khoảng cách các đường sóng = 4 × nét thật (bút 0,4: 1,76 mm); đường thẳng phủ 25 %
AM_AMPLITUDE = 0.45              # biên độ tối đa = 0,45 × khoảng cách đường: hai đường kề nhau gần chạm nhau ở chỗ đậm nhất
AM_WAVE_LINES = 2.0              # bước sóng (cố định) = 2 × nét thật: hai sườn sóng vừa đủ không đè lên nhau. Cố định để mọi
                                 # đường cùng pha, song song nhau (thử 11/11: bước sóng đổi theo độ đậm làm các đường cắt nhau
                                 # thành lưới rối)
AM_DITHER = 0.35                 # dòng thưa / dày xuất hiện so le trong ±35 % quanh ngưỡng của nó
AM_WHITE = 1.6                   # lưới thưa nhất (1/4 số đường, phủ 0,0625) có mặt từ 1,6 × 0,0625 = độ phủ 0,10; dưới đó
                                 # giấy trắng. Trước 14/11/2026: 0,6 (từ 0,04): má sáng có đường thẳng cách 4 dòng
AM_FILL = False                  # mặc định (style.am_fill ghi đè): False = vùng sáng vừa bớt đường cho đúng tông (có khe trắng
                                 # so le); True = từ độ phủ 0,10 có đủ mọi đường thẳng (vùng da phủ đều đường, đậm hơn ảnh chút)
AM_MIN_RUN = 3.0                 # bỏ đoạn sóng ngắn hơn 3 × khoảng cách đường (~5 mm), lấp khe ngắn hơn một nửa mức đó:
                                 # gạch vụn ở vùng sáng mỗi cái tốn một lần nhấc bút
# Vùng rất đậm (13/11/2026). Tờ tông in thật (Sakura 0,5, mặt bóng): ô phủ 90 % chỉ trông đậm 0,71 (đan chéo 0,93). Vẽ lại
# tờ đó trên máy tính: mực hình học của sóng chỉ 0,47 / 0,54 / 0,62 / 0,70 / 0,78 ở ô 50 / 60 / 70 / 80 / 90 % (sườn sóng
# dốc đè lên nhau); đổi biên độ / bước sóng / khoảng cách đường không lên quá 0,83. Nên thêm lớp gạch thẳng vuông góc ở
# vùng đậm, bù đúng phần sóng thiếu.
AM_DARK_LAYER = True             # False = chỉ sóng như trước 13/11 (ô đậm nhất ~0,7)
AM_EFF_KNEE = 0.45               # tới độ phủ này sóng phủ đủ
AM_EFF_SLOPE = 0.78              # trên đó mực thật chỉ tăng 0,78 phần độ phủ mong muốn ((0,78 − 0,43) ÷ (0,9 − 0,45))


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
    if getattr(style, "am_fill", AM_FILL):                  # phủ đều: mọi lưới có mặt cùng lúc từ độ phủ 0,10 (14/11/2026, chủ dự án:
        thresholds = (thresholds[0],) * 3                   # "cả vùng mặt đều có nét", không khe trắng do bớt đường)
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
    groups = [_clip_out(strokes, f)]
    if AM_DARK_LAYER:
        # Mực sóng phủ thật (hình học, nét 0,5 mm): bằng độ phủ mong muốn tới AM_EFF_KNEE, trên đó chỉ tăng AM_EFF_SLOPE phần
        # (sườn sóng dốc đè lên nhau). Lớp gạch thẳng vuông góc bù phần thiếu: 1 - (1 - sóng)(1 - gạch) = mong muốn.
        eff = np.where(cov <= AM_EFF_KNEE, cov, AM_EFF_KNEE + (cov - AM_EFF_KNEE) * AM_EFF_SLOPE)
        extra = np.clip(1.0 - (1.0 - cov) / np.maximum(1.0 - eff, 1e-6), 0.0, 1.0).astype(np.float32)
        if extra.max() > 0:
            from types import SimpleNamespace
            hatch_style = SimpleNamespace(levels=getattr(style, "levels", 5), soft_levels=getattr(style, "soft_levels", True),
                                          spacing_mm=None, angle=a)     # khoảng cách gạch mặc định, không theo khoảng cách sóng
            groups += zigzag_groups(Field(extra, f.width_mm, f.height_mm), hatch_style, pen_mm, ctx, (a + 90.0) % 180.0)
    return groups


@FILLERS.register("wave_am")
def wave_am(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(wave_am_groups(f, style, pen_mm, ctx, angle))


# === C. Kiểu ẩn (13/11/2026): theo dáng ảnh thuần (flow field, bản thô 12/11/2026): nét uốn dọc theo dáng ảnh, độ đậm liền. Thuật toán ở flow.py ------
def flow_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    from . import flow
    line_w = LINE_WIDTH_RATIO * pen_mm
    scale = spacing_of(style, pen_mm) / (DEFAULT_SPACING_PEN * line_w)      # người dùng đặt khoảng cách khác mặc định
    base = style.angle if angle is None else angle
    # Không áp đường cong tông (thử 14/11/2026 rồi bỏ): sau khi sửa cửa sổ kiểm tra (flow.busy), mực phủ đã bám đúng độ đậm; thêm
    # đường cong thì tools/ink_sim.py báo vùng giữa đậm quá (sai mắt 0,043 -> 0,063)
    return [_clip_out(flow.flow_strokes(f, line_w, base, scale, ctx), f)]


@FILLERS.register("flow")
def flow_fill(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(flow_groups(f, style, pen_mm, ctx, angle))


# === B. Đan chéo + theo dáng (13/11/2026, chủ dự án chọn làm mặc định Chân dung) ---------------------------------------
# In thật 13/11: đan chéo thuần đủ đậm nhạt nhưng cứng, mắt / mũi / mép mặt không tách khỏi nền khi nhìn gần; theo dáng
# thuần có "hồn" ở A4 nhưng quá "nghệ thuật" và ở A6 không ra hình. Lai: đan chéo gánh tông, thêm vài đường theo dáng
# CHỈ ở dải viền (chỗ độ đậm đổi mạnh VÀ hướng rõ). Lớp đan vẽ thưa đi đúng phần mực đường theo dáng đã phủ (đo bằng
# cách vẽ các đường đó lên ảnh), nên độ đậm tổng không đổi.
HYB_FLOW_SHARE = 0.5             # trong dải viền, đường theo dáng gánh tối đa một nửa độ phủ; phần còn lại là đan chéo
HYB_EDGE_SIGMA_MM = 1.0          # làm mờ trước khi đo độ dốc độ đậm (bỏ hạt nhỏ hơn ~1 mm)
HYB_EDGE_LO = 0.04               # độ đậm đổi chậm hơn 0,04 / mm: không phải viền
HYB_EDGE_HI = 0.12               # đổi từ 0,12 / mm trở lên: viền rõ hẳn
HYB_COHERENCE = 0.3              # độ rõ hướng từ mức này: hướng đủ tin để vẽ theo
HYB_BAND_MM = 1.5                # nới dải viền ra mỗi phía chừng này (vài đường song song ôm theo viền)
HYB_INK_PX_MM = 0.1              # ô của ảnh vẽ thử các đường theo dáng để đo mực đã phủ


def edge_band(f: Field, default_deg: float = 45.0) -> np.ndarray:
    """0..1: chỗ nào là dải viền có hướng rõ (1 = chắc chắn), cùng cỡ f.dark."""
    import cv2
    from . import flow
    px = f.px_mm
    d = cv2.GaussianBlur(f.dark.astype(np.float32), (0, 0), max(0.5, HYB_EDGE_SIGMA_MM / px))
    gy, gx = np.gradient(d)
    grad = np.hypot(gx, gy) / px                                         # độ đậm đổi mỗi mm
    _, _, coh = flow.direction_field(f, default_deg)
    e = np.clip((grad - HYB_EDGE_LO) / (HYB_EDGE_HI - HYB_EDGE_LO), 0, 1) * np.clip(coh / HYB_COHERENCE, 0, 1)
    r = max(1, int(round(HYB_BAND_MM / px)))
    e = cv2.dilate(e.astype(np.float32), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    return np.clip(cv2.GaussianBlur(e, (0, 0), max(0.5, 0.5 / px)), 0, 1)


def ink_cover(strokes: list[Stroke], f: Field, line_w: float) -> np.ndarray:
    """Độ phủ mực thật của các nét (bề rộng line_w), trung bình trong ~2 bề rộng nét, cùng cỡ f.dark."""
    import cv2
    k = HYB_INK_PX_MM
    canvas = np.zeros((int(math.ceil(f.height_mm / k)) + 1, int(math.ceil(f.width_mm / k)) + 1), np.uint8)
    t = max(1, int(round(line_w / k)))
    for s in strokes:
        if len(s) >= 2:
            cv2.polylines(canvas, [np.round(np.asarray(s) / k * 16).astype(np.int32)], False, 255, t, cv2.LINE_8, 4)
    cov = cv2.resize(canvas.astype(np.float32) / 255, (f.w, f.h), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(cov, (0, 0), max(0.5, 2 * line_w / f.px_mm))


CONTOUR_BARRIER_PENS = 2.0       # hàng rào quanh đường viền rộng 2 × nét: dòng gạch dừng cách mép nét viền ~nửa nét


def stroke_mask(strokes: list[Stroke], f: Field, width_mm: float) -> np.ndarray:
    """Mặt nạ bool cùng cỡ f.dark: các nét vẽ với bề rộng width_mm."""
    import cv2
    canvas = np.zeros((f.h, f.w), np.uint8)
    t = max(1, int(round(width_mm / f.px_mm)))
    sx, sy = f.w / f.width_mm * 16, f.h / f.height_mm * 16
    for s in strokes:
        if len(s) >= 2:
            pts = np.round(np.asarray(s) * [sx, sy] - 8).astype(np.int32)      # tâm điểm ảnh ở +0,5
            cv2.polylines(canvas, [pts], False, 1, t, cv2.LINE_8, 4)
    return canvas.astype(bool)


def crosshatch_flow_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    """Đan chéo trong từng khối + MỘT đường viền cong (FDoG, làm mượt) bao quanh khối, vẽ sau cùng.

    14/11/2026 (chủ dự án): đường viền là hàng rào: dòng gạch dừng ở viền nên khối đậm (tóc) không lan sang khối nhạt
    (mặt), mắt / mũi giữ khung dáng. Thay cách 13/11 (2–3 đường theo dáng song song ở dải viền, trông như râu;
    edge_band / ink_cover giữ lại cho kiểu khác)."""
    line_w = LINE_WIDTH_RATIO * pen_mm
    contour = outline(f, style, pen_mm, ctx)
    barrier = stroke_mask(contour, f, CONTOUR_BARRIER_PENS * line_w)
    if ctx:
        ctx.check()
    return _cross_layers(_toned(f, "crosshatch_flow"), style, pen_mm, ctx, angle, barrier) + [contour]


@FILLERS.register("crosshatch_flow")
def crosshatch_flow(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    return _flat(crosshatch_flow_groups(f, style, pen_mm, ctx, angle))


GROUPERS = {"zigzag": zigzag_groups, "wave": wave_groups, "spiral": spiral_groups,
            "crosshatch": crosshatch_groups, "crosshatch3": crosshatch3_groups, "wave_am": wave_am_groups,
            "flow": flow_groups, "crosshatch_flow": crosshatch_flow_groups}


# === B. Nét viền ==========================================================================================================
OUTLINE_MIN_LEN_MM = 4.0         # bỏ nét viền ngắn hơn chừng này (trước 14/11/2026: 1 mm). Ảnh chân dung A4 bút 0,4, cùng làm
                                 # mượt 0,8 mm (trace.SMOOTH_MM): XDoG 210 -> 145 nét, 1,7 -> 1,3 phút, hết gạch vụn quanh mắt
@FILLERS.register("outline")
def outline(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[Stroke]:
    """Nét viền phác họa (edges.py): nét mực + ranh giới mảng sáng tối / màu + nối khe hở -> nét liền.

    Ranh giới mảng: kiểu Nét viền dùng Canny (cũ) trừ khi tích "Dùng XDoG" (outline_xdog); lớp viền phủ lên kiểu tô khác
    LUÔN dùng XDoG (13/11/2026, chủ dự án: kiểu tô cần nét tách giữa các vùng, XDoG ra viền mắt / mũi rõ hơn Canny)."""
    method = "xdog" if (style.kind != "outline" or getattr(style, "outline_xdog", False)) else "canny"
    skel = edges.outline_mask(f.dark, f.rgb, f.width_mm / f.w, style.outline_detail, ctx, method)
    if ctx:
        ctx.check()
    return trace.to_strokes(skel, f.width_mm / f.w, f.height_mm / f.h, min_len_mm=max(OUTLINE_MIN_LEN_MM, 3.0 * pen_mm))


# === Điểm vào cho raster.py ===============================================================================================
def fill_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None,
                overlay: bool | None = None) -> list[list[Stroke]]:
    """Nét tô chia nhóm theo mức đậm nhạt (nhạt → đậm), nhóm viền (nếu có) cuối cùng. Nhóm rỗng bị bỏ.
    `angle` ghi đè góc gạch (mỗi màu một góc); `overlay` ghi đè outline_overlay (đa màu chỉ phủ viền một lần)."""
    grouper = GROUPERS.get(style.kind)
    groups = grouper(f, style, pen_mm, ctx, angle) if grouper else [FILLERS.get(style.kind)(f, style, pen_mm, ctx, angle)]
    if overlay is None:
        overlay = style.outline_overlay
    if overlay and style.kind not in ("outline", "crosshatch_flow"):     # viền vẽ SAU cùng cho nét rõ (crosshatch_flow đã có)
        if ctx:
            ctx.check()
        groups = groups + [outline(f, style, pen_mm, ctx)]
    return [g for g in groups if g]


def fill(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None,
         overlay: bool | None = None) -> list[Stroke]:
    """Như fill_groups nhưng một danh sách phẳng (thứ tự: mức nhạt → đậm, viền cuối)."""
    return _flat(fill_groups(f, style, pen_mm, ctx, angle, overlay))
