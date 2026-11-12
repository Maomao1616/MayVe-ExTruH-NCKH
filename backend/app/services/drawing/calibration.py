"""Tờ mẫu hiệu chỉnh bút: tạo thành một BẢN THẢO như mọi bản khác (xem trước, nạp sang Điều khiển, chạy).

Một tờ A5 đặt đứng, tỷ lệ 1:1 (không co giãn), gồm:
  * chữ "F" ở góc trên trái: bất đối xứng nên nhìn là biết bản vẽ có bị lật / xoay trục không;
  * thước 100 mm có vạch mỗi 10 mm: đo bằng thước thật để kiểm tra bước/mm của máy;
  * 8 dải tô zigzag có khoảng cách dòng = cỡ nét đoán × hệ số khác nhau (từ trên xuống, dày → thưa), để ĐO bề
    rộng nét thật: dải thưa nhất mà vẫn đen kín (chưa ướt / bóng mực) có khoảng cách ≈ bề rộng nét. Dải thưa hơn lộ
    khe trắng; dải dày hơn chồng nét, thừa mực. Số đo đó ghi vào ô "Bút vẽ" (Tùy chọn) ở tab Tạo bản vẽ.
Chỉ dùng cho thử máy thật; tab Tạo bản vẽ vẫn không gọi máy.
"""
from __future__ import annotations

from typing import Any, Mapping

from . import drafts, service, spec
from .errors import DrawError
from .shapes import Layer

PAPER = "a5"
# khoảng cách dòng = bút × hệ số; bút 0,4: 0,32 / 0,40 / 0,45 / 0,50 / 0,60 / 0,80 / 1,0 / 1,2 mm (dày ở quanh 0,4–0,5
# để phân biệt nét 0,40 với 0,45 trên giấy Ivory)
BAND_FACTORS = (0.8, 1.0, 1.125, 1.25, 1.5, 2.0, 2.5, 3.0)
WIDTH_MM, BAND_H, GAP = 130.0, 14.0, 2.0
HEADER_H = 24.0                                              # chữ F + thước
RULER_X0, RULER_LEN = 28.0, 100.0

# Hai cỡ tờ: A5 (mặc định, thước 100 mm) và A6 gọn hơn (vừa phần trong lề 5 mm của A6 = 95 × 138 mm; thước 80 mm).
SIZES = {
    "a5": {"width": WIDTH_MM, "band_h": BAND_H, "gap": GAP, "ruler_x0": RULER_X0, "ruler_len": RULER_LEN},
    "a6": {"width": 95.0, "band_h": 10.0, "gap": 1.5, "ruler_x0": 14.0, "ruler_len": 80.0},
}


def _size(paper: str) -> dict:
    if paper not in SIZES:
        raise DrawError("bad_param", f"paper: chỉ nhận {', '.join(SIZES)}.")
    return SIZES[paper]


def layers(pen_width_mm: float, paper: str = PAPER) -> list[Layer]:
    z = _size(paper)
    width, band_h, gap, ruler_x0, ruler_len = z["width"], z["band_h"], z["gap"], z["ruler_x0"], z["ruler_len"]
    strokes: list[list[tuple[float, float]]] = []
    # chữ F cao 20 mm, rộng 12 mm (nét dọc, thanh trên, thanh giữa)
    strokes += [[(2, 22), (2, 2)], [(2, 2), (14, 2)], [(2, 12), (11, 12)]]
    # thước (100 mm ở A5, 80 mm ở A6): đường chính + vạch 10 mm (vạch đầu, giữa, cuối dài hơn)
    y = 14.0
    strokes.append([(ruler_x0, y), (ruler_x0 + ruler_len, y)])
    ticks = int(ruler_len // 10)
    for i in range(ticks + 1):
        x = ruler_x0 + i * 10
        tick = 6.0 if i in (0, ticks // 2, ticks) else 3.0
        strokes.append([(x, y), (x, y - tick)])
    # các dải tô
    top = HEADER_H + 4
    for index, factor in enumerate(BAND_FACTORS):
        y0 = top + index * (band_h + gap)
        pitch = pen_width_mm * factor
        count = int(band_h / pitch) + 1
        path: list[tuple[float, float]] = []
        for row in range(count):
            yy = min(y0 + row * pitch, y0 + band_h)
            ends = (0.0, width) if row % 2 == 0 else (width, 0.0)
            path += [(ends[0], yy), (ends[1], yy)]
        strokes.append(path)
    return [Layer("1", [[tuple(p) for p in s] for s in strokes])]


def height_mm(paper: str = PAPER) -> float:
    z = _size(paper)
    return HEADER_H + 4 + len(BAND_FACTORS) * z["band_h"] + (len(BAND_FACTORS) - 1) * z["gap"]


def make_draft(name: str, machine_raw: Mapping[str, Any], gcode_raw: Mapping[str, Any],
               pen_width_mm: float, paper_x_mm: float = 0.0, paper_y_mm: float = 0.0, paper: str = PAPER) -> dict:
    if not 0.1 <= pen_width_mm <= 2:
        raise DrawError("bad_param", "pen_width_mm: ngoài khoảng 0,1–2 mm.")
    z = _size(paper)
    height = height_mm(paper)
    layout = {"paper": paper, "paper_x_mm": paper_x_mm, "paper_y_mm": paper_y_mm,
              "width_mm": z["width"], "height_mm": height, "fit": "contain", "center": True}
    result, placed = service.build(layers(pen_width_mm, paper), machine_raw, layout, gcode_raw,
                                   (0.0, 0.0, z["width"], height))
    machine = spec.parse("machine", machine_raw).as_dict()
    params = {"machine": dict(machine_raw), "layout": layout, "gcode": dict(gcode_raw),
              "source": {"mode": "calibration", "pen_width_mm": pen_width_mm, "paper": paper,
                         "band_factors": list(BAND_FACTORS)}}
    return {"draft": drafts.create(name, result, placed, machine, params), "warnings": result["warnings"]}


# --- Tờ hiệu chỉnh TÔNG (12/11/2026): đo độ đậm nhìn thấy theo độ phủ, để dựng đường cong tông cho từng bút + giấy ----
# 16 ô vuông xếp 4 × 4, đọc từ trái sang phải, trên xuống dưới; ô i có độ phủ danh định TONE_STEPS[i] (ô 0 = giấy trắng).
# Độ phủ = bề rộng nét ÷ khoảng cách dòng, đúng công thức các kiểu tô dùng (styles.level_plan); ô gạch chéo / đan 3 hướng
# chia độ phủ cho các lớp đúng như kiểu tô thật (styles.cross_split / cross3_split). Ba ô vuông đen đặc ở góc trên phải,
# dưới trái, dưới phải là mốc ĐEN chuẩn + mốc căn ảnh chụp; góc trên trái là chữ F (biết tờ có bị xoay không).
TONE_STEPS = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80, 0.90)
TONE_STYLES = ("zigzag", "crosshatch", "crosshatch3", "wave_am", "spiral")
# Sóng biên độ và xoắn ốc không chia lớp như gạch: ô sóng chạy ĐÚNG hàm tô thật (styles.wave_am_groups) trên một ô đậm đều
# bằng độ phủ của ô, ô xoắn ốc là xoắn ốc từ tâm ô có bước = bề rộng nét ÷ độ phủ (hatch.spiral_runs).
TONE_PIXEL_MM = 0.1              # độ phân giải ô đậm đều dùng cho sóng biên độ
TONE_ANGLE = 45.0                # góc gạch như mặc định của kiểu tô
TONE_GRID = 4                    # 4 × 4 ô
TONE_TOP = 24.0                  # phần đầu: chữ F + mốc góc trên
TONE_MARK = 4.0                  # cạnh ô mốc đen (mm)
TONE_SOLID = 0.8                 # ô mốc: khoảng cách dòng = 0,8 × nét (đặc hẳn)
TONE_SIZES = {
    "a6": {"patch": 20.0, "gap": 3.0},       # 4 × 20 + 3 × 3 = 89 mm ≤ 95 (A6 trừ lề)
    "a5": {"patch": 30.0, "gap": 4.0},       # 132 mm ≤ 138; ô to hơn: dải thưa (5 %) vẫn có nhiều dòng để đo
}


def _tone_size(paper: str) -> dict:
    if paper not in TONE_SIZES:
        raise DrawError("bad_param", f"paper: chỉ nhận {', '.join(TONE_SIZES)}.")
    return TONE_SIZES[paper]


def tone_layer_covers(cover: float, style: str) -> list[tuple[float, float]]:
    """Độ phủ danh định của một ô -> [(độ phủ từng lớp, góc)] theo đúng cách chia lớp của kiểu tô."""
    import numpy as np
    from . import styles
    if style not in TONE_STYLES:
        raise DrawError("bad_param", f"style: chỉ nhận {', '.join(TONE_STYLES)}.")
    if cover <= 0:
        return []
    if style in ("zigzag", "wave_am", "spiral"):                 # một lớp (sóng biên độ: độ phủ là mức đậm của ô)
        parts = [cover]
        step = 0.0
    elif style == "crosshatch":
        parts = [float(x[0]) for x in styles.cross_split(np.array([cover], np.float32))]
        step = styles.CROSS_ANGLE
    else:
        parts = [float(x[0]) for x in styles.cross3_split(np.array([cover], np.float32))]
        step = styles.CROSS3_ANGLE
    return [(p, (TONE_ANGLE + i * step) % 180.0) for i, p in enumerate(parts) if p > 1e-4]


def _hatch_square(x0: float, y0: float, size: float, spacing: float, angle: float) -> list[list[tuple[float, float]]]:
    """Một ô vuông gạch zigzag (quay đầu nửa vòng tròn) bằng đúng hàm gạch của kiểu tô."""
    import numpy as np
    from . import hatch, styles
    px = 0.1
    n = int(round(size / px))
    f = hatch.Field(np.ones((n, n), np.float32), size, size)
    d, nv, vmin, lines = hatch.scan_runs(np.ones((n, n), bool), f, angle, spacing)
    out = styles._clip_out(styles._link(d, nv, vmin, lines, spacing, False), f)
    return [[(x0 + x, y0 + y) for x, y in s] for s in out]


def _uniform_field(size: float, cover: float):
    import numpy as np
    from . import hatch
    n = int(round(size / TONE_PIXEL_MM))
    return hatch.Field(np.full((n, n), cover, np.float32), size, size)


def _spiral_square(x0: float, y0: float, size: float, pitch: float) -> list[list[tuple[float, float]]]:
    """Xoắn ốc từ tâm ô (hatch.spiral_runs như kiểu tô thật). Đoạn nằm ngoài ô bị CẮT BỎ, không kẹp vào mép (kẹp sẽ ra
    các cạnh thẳng thừa mực quanh ô); chỗ xoắn ốc ra khỏi ô ở góc rồi quay lại thành nét riêng."""
    import numpy as np
    from . import hatch
    f = _uniform_field(size, 1.0)
    out: list[list[tuple[float, float]]] = []
    for a in hatch.spiral_runs(np.ones(f.dark.shape, bool), f, pitch):
        inside = (a[:, 0] >= 0) & (a[:, 0] <= size) & (a[:, 1] >= 0) & (a[:, 1] <= size)
        edges = np.flatnonzero(np.diff(np.concatenate(([0], inside.astype(np.int8), [0]))))
        for start, stop in zip(edges[0::2], edges[1::2]):
            if stop - start >= 2:
                out.append([(x0 + round(float(x), 3), y0 + round(float(y), 3)) for x, y in a[start:stop]])
    return out


def _wave_am_square(x0: float, y0: float, size: float, pen_width_mm: float, cover: float,
                    angle: float) -> list[list[tuple[float, float]]]:
    """Một ô sóng biên độ: chạy đúng styles.wave_am_groups trên ô đậm đều = `cover` (khoảng cách đường mặc định)."""
    from types import SimpleNamespace
    from . import styles
    f = _uniform_field(size, cover)
    style = SimpleNamespace(spacing_mm=None, angle=angle)
    groups = styles.wave_am_groups(f, style, pen_width_mm, None, angle)
    return [[(x0 + x, y0 + y) for x, y in s] for g in groups for s in g]


def _spacing_of(style: str, pen_width_mm: float, cover: float) -> float:
    """Khoảng cách đường ghi vào thông tin ô: gạch / xoắn ốc = bề rộng ÷ độ phủ; sóng biên độ cố định (đổi biên độ)."""
    if style == "wave_am":
        from . import styles
        return styles.AM_SPACING_LINES * pen_width_mm
    return pen_width_mm / cover


def _tone_square(style: str, x0: float, y0: float, patch: float, pen_width_mm: float, cover: float, angle: float):
    if style == "wave_am":
        return _wave_am_square(x0, y0, patch, pen_width_mm, cover, angle)
    if style == "spiral":
        return _spiral_square(x0, y0, patch, pen_width_mm / cover)
    return _hatch_square(x0, y0, patch, pen_width_mm / cover, angle)


def tone_layers(pen_width_mm: float, paper: str = "a6", style: str = "zigzag") -> tuple[list[Layer], dict]:
    z = _tone_size(paper)
    patch, gap = z["patch"], z["gap"]
    width = TONE_GRID * patch + (TONE_GRID - 1) * gap
    grid_bottom = TONE_TOP + TONE_GRID * patch + (TONE_GRID - 1) * gap
    height = grid_bottom + 3.0 + TONE_MARK
    strokes: list[list[tuple[float, float]]] = [[(2, 22), (2, 2)], [(2, 2), (14, 2)], [(2, 12), (11, 12)]]   # chữ F
    solid = TONE_SOLID * pen_width_mm
    for mx, my in ((width - TONE_MARK, 0.0), (0.0, height - TONE_MARK), (width - TONE_MARK, height - TONE_MARK)):
        strokes += _hatch_square(mx, my, TONE_MARK, solid, 0.0)
    cells = []
    for i, cover in enumerate(TONE_STEPS):
        row, col = divmod(i, TONE_GRID)
        x0, y0 = col * (patch + gap), TONE_TOP + row * (patch + gap)
        parts = tone_layer_covers(cover, style)
        for part, angle in parts:
            strokes += _tone_square(style, x0, y0, patch, pen_width_mm, part, angle)
        cells.append({"n": i, "cover": cover, "x": round(x0, 3), "y": round(y0, 3),
                      "layers": [{"cover": round(p, 4), "angle": a, "spacing_mm": round(_spacing_of(style, pen_width_mm, p), 4)}
                                 for p, a in parts]})
    info = {"width": width, "height": height, "patch_mm": patch, "gap_mm": gap, "cells": cells}
    return [Layer("1", strokes)], info


def make_tone_draft(name: str, machine_raw: Mapping[str, Any], gcode_raw: Mapping[str, Any], pen_width_mm: float,
                    paper_x_mm: float = 0.0, paper_y_mm: float = 0.0, paper: str = "a6", style: str = "zigzag") -> dict:
    if not 0.1 <= pen_width_mm <= 2:
        raise DrawError("bad_param", "pen_width_mm: ngoài khoảng 0,1–2 mm.")
    layers_, info = tone_layers(pen_width_mm, paper, style)
    w, h = info["width"], info["height"]
    layout = {"paper": paper, "paper_x_mm": paper_x_mm, "paper_y_mm": paper_y_mm,
              "width_mm": w, "height_mm": h, "fit": "contain", "center": True}
    result, placed = service.build(layers_, machine_raw, layout, gcode_raw, (0.0, 0.0, w, h))
    machine = spec.parse("machine", machine_raw).as_dict()
    params = {"machine": dict(machine_raw), "layout": layout, "gcode": dict(gcode_raw),
              "source": {"mode": "calibration", "sheet": "tone", "style": style, "pen_width_mm": pen_width_mm,
                         "paper": paper, "steps": list(TONE_STEPS), **info}}
    return {"draft": drafts.create(name, result, placed, machine, params), "warnings": result["warnings"]}
