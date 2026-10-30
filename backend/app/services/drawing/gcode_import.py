"""Nhập một tệp G-code có sẵn (từ phần mềm khác) thành MỘT BẢN THẢO: một tệp = một bản.

Không dựng lại nét từ ảnh/SVG: chỉ làm sạch bằng đúng bộ kiểm tra của tác vụ (`clean_gcode`: bỏ chú thích,
chặn `$` và ký tự lạ), đọc G-code để lấy nét cho ảnh minh họa và số liệu, rồi ghi như mọi bản thảo.
Cung G2/G3 chỉ được vẽ thành đoạn thẳng nối hai đầu trong ảnh minh họa (G-code lưu nguyên, chạy đúng).
Bút nhấc/hạ nhận ra qua trục Z: nếu tệp có từ hai mức Z trở lên thì Z thấp hơn trung điểm là bút xuống;
nếu không có Z thì mọi G1/G2/G3 là nét vẽ.
"""
from __future__ import annotations

import math
import re

from ..job import JobError, clean_gcode
from . import drafts
from .errors import DrawError
from .shapes import Layer

_WORD = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
MM_PER_INCH = 25.4
DEFAULT_FEED = 1000.0
RAPID_FEED = 6000.0


def analyse(lines: list[str]) -> tuple[list[list[tuple[float, float]]], dict, list[dict]]:
    """(nét vẽ, số liệu, cảnh báo) từ các dòng đã làm sạch."""
    zs = {round(float(n), 4) for line in lines for c, n in _WORD.findall(line.upper()) if c == "Z"}
    has_pen = len(zs) > 1
    threshold = (min(zs) + max(zs)) / 2 if has_pen else None

    x = y = 0.0
    z = max(zs) if has_pen else 0.0                    # chưa biết thì coi như bút đang nhấc
    absolute, unit, feed, motion = True, 1.0, 0.0, None
    strokes: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] | None = None
    draw_mm = travel_mm = seconds = 0.0
    arcs = 0
    lifts = 0
    xs: list[float] = []
    ys: list[float] = []

    def pen_down() -> bool:
        return (z <= threshold) if has_pen else motion in (1, 2, 3)

    for line in lines:
        vals: dict[str, float] = {}
        dwell = False
        for letter, num in _WORD.findall(line.upper()):
            n = float(num)
            if letter == "G":
                g = round(n)
                if g in (0, 1, 2, 3):
                    motion = g
                elif g == 4:
                    dwell = True
                elif g == 20:
                    unit = MM_PER_INCH
                elif g == 21:
                    unit = 1.0
                elif g == 90:
                    absolute = True
                elif g == 91:
                    absolute = False
            elif letter == "F":
                feed = n * unit
            elif letter in "XYZP":
                vals[letter] = n
        if dwell and "P" in vals:
            seconds += vals["P"]
            continue
        if motion is None or not any(a in vals for a in "XYZ"):
            continue
        nx = (vals["X"] * unit if absolute else x + vals["X"] * unit) if "X" in vals else x
        ny = (vals["Y"] * unit if absolute else y + vals["Y"] * unit) if "Y" in vals else y
        nz = (vals["Z"] * unit if absolute else z + vals["Z"] * unit) if "Z" in vals else z
        was_down = pen_down()
        dz = abs(nz - z)
        z = nz
        now_down = pen_down()
        length = math.dist((x, y), (nx, ny))
        speed = RAPID_FEED if motion == 0 else (feed if feed > 0 else DEFAULT_FEED)
        seconds += math.hypot(length, dz) / speed * 60
        if motion in (2, 3) and length > 0:
            arcs += 1
        if length > 0:
            if motion != 0 and now_down:
                draw_mm += length
                if current is None:
                    current = [(x, y)]
                    strokes.append(current)
                current.append((nx, ny))
                xs += [x, nx]
                ys += [y, ny]
            else:
                travel_mm += length
        if has_pen and was_down and not now_down:
            lifts += 1
            current = None
        if not has_pen and (motion == 0 or length == 0) and current is not None:
            lifts += 1
            current = None
        x, y = nx, ny
    if current is not None:
        lifts += 1

    if not strokes:
        raise DrawError("empty_drawing", "Tệp không có đường vẽ nào (không có chuyển động XY khi bút xuống).")
    stats = {"strokes": len(strokes), "points": sum(len(s) for s in strokes), "lines": len(lines),
             "draw_mm": round(draw_mm, 2), "travel_mm": round(travel_mm, 2), "pen_lifts": lifts,
             "est_seconds": round(seconds, 1),
             "bounds": {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)}}
    warnings = [{"code": "arcs_approximated", "count": arcs}] if arcs else []
    return strokes, stats, warnings


def import_gcode(name: str, text: str, work_w: float, work_h: float) -> dict:
    try:
        lines = clean_gcode(text.splitlines())
    except JobError as exc:
        raise DrawError("bad_gcode", exc.message, exc.status) from exc
    if not lines:
        raise DrawError("empty_job", "Tệp không có dòng lệnh nào.")
    strokes, stats, warnings = analyse(lines)
    b = stats["bounds"]
    result = {"files": [{"layer": "1", "name": "draw", "gcode": "\n".join(lines) + "\n", "stats": stats}],
              "paper": {"x": 0.0, "y": 0.0, "w": work_w, "h": work_h},
              "box": {"x": b["x0"], "y": b["y0"], "w": b["x1"] - b["x0"], "h": b["y1"] - b["y0"]},
              "warnings": warnings}
    machine = {"work_w": work_w, "work_h": work_h}
    params = {"source": {"mode": "gcode_import", "name": name}}
    draft = drafts.create((name or "G-code")[:80], result, [Layer("1", strokes)], machine, params)
    return {"draft": draft, "warnings": warnings}
