"""Đường nét (mm, đã bố trí) -> dòng G-code + thống kê. Không gọi máy.

Quy ước (khớp gcode.js và job.py): dòng đầu `G90 G21`; có `F`; dòng <= 200 ký tự; không `$`;
bút lên = pen_up_z, xuống = pen_down_z; mỗi nét kết thúc bằng bút lên (nên file kết thúc bút lên).
Chỉ dùng G0/G1 (cung tròn G2/G3: giai đoạn 6, tùy chọn).
Di chuyển không vẽ dùng G0 khi travel_feed >= rapid_feed của máy; nếu thấp hơn thì G1 kèm F
(vì G0 luôn chạy ở tốc độ tối đa của firmware).
"""
from __future__ import annotations

import math

from ..job import MAX_LINE_LEN, MAX_LINES
from .errors import DrawError
from .spec import Params
from .shapes import Stroke


def fmt(v: float, precision: int) -> str:
    s = f"{v:.{precision}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def to_machine(x: float, y: float, machine: Params) -> tuple[float, float]:
    """ĐIỂM DUY NHẤT đổi tọa độ bản vẽ -> tọa độ máy (hướng trục chưa kiểm chứng, giả định C5)."""
    return (x, machine.work_h - y) if machine.invert_y else (x, y)


def clean_strokes(strokes: list[Stroke], precision: int) -> tuple[list[Stroke], int]:
    """Làm tròn theo độ chính xác xuất, bỏ điểm trùng liên tiếp, bỏ nét < 2 điểm. Trả (nét, số nét bỏ)."""
    out: list[Stroke] = []
    dropped = 0
    for s in strokes:
        pts: Stroke = []
        for x, y in s:
            p = (round(x, precision), round(y, precision))
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(pts) >= 2:
            out.append(pts)
        else:
            dropped += 1
    return out, dropped


def build_gcode(strokes: list[Stroke], gp: Params, machine: Params) -> tuple[list[str], dict, list[dict]]:
    prec = gp.precision
    cleaned, dropped = clean_strokes(strokes, prec)
    if not cleaned:
        raise DrawError("empty_drawing", "Không còn nét nào sau khi làm sạch.")
    up, down = gp.pen_up_z, gp.pen_down_z
    use_g0 = gp.travel_feed >= machine.rapid_feed

    feed = {"cur": None}

    def f(value: float) -> str:      # chỉ ghi F khi đổi (F là modal); dòng G1 đầu tiên luôn có F
        if feed["cur"] == value:
            return ""
        feed["cur"] = value
        return f" F{fmt(value, 3)}"

    def xy(p) -> str:
        mx, my = to_machine(p[0], p[1], machine)
        return f"X{fmt(mx, prec)} Y{fmt(my, prec)}"

    lines = ["G90 G21", f"G1 Z{fmt(up, 3)}{f(gp.pen_feed)}"]
    if gp.delay_up_s > 0:
        lines.append(f"G4 P{fmt(gp.delay_up_s, 3)}")
    draw_mm = travel_mm = 0.0
    prev = (0.0, 0.0)            # ước tính: bắt đầu từ gốc
    npts = 0
    xs, ys = [], []
    for s in cleaned:
        travel_mm += math.dist(prev, s[0])
        lines.append(f"G0 {xy(s[0])}" if use_g0 else f"G1 {xy(s[0])}{f(gp.travel_feed)}")
        lines.append(f"G1 Z{fmt(down, 3)}{f(gp.pen_feed)}")
        if gp.delay_down_s > 0:
            lines.append(f"G4 P{fmt(gp.delay_down_s, 3)}")
        for a, b in zip(s, s[1:]):
            draw_mm += math.dist(a, b)
            lines.append(f"G1 {xy(b)}{f(gp.draw_feed)}")
        lines.append(f"G1 Z{fmt(up, 3)}{f(gp.pen_feed)}")
        if gp.delay_up_s > 0:
            lines.append(f"G4 P{fmt(gp.delay_up_s, 3)}")
        prev = s[-1]
        npts += len(s)
        xs += [p[0] for p in s]
        ys += [p[1] for p in s]

    if len(lines) > MAX_LINES:
        raise DrawError("too_many_lines", f"G-code {len(lines)} dòng, vượt giới hạn {MAX_LINES}. "
                                          "Hãy tăng 'đơn giản hóa' hoặc giảm chi tiết.")
    longest = max(len(x) for x in lines)
    if longest > MAX_LINE_LEN:      # không xảy ra với G0/G1 thường; giữ làm chốt chặn
        raise DrawError("bad_gcode", f"Dòng G-code dài {longest} ký tự (tối đa {MAX_LINE_LEN}).")

    z_s = len(cleaned) * 2 * abs(up - down) / gp.pen_feed * 60
    eff_travel = min(gp.travel_feed, machine.rapid_feed)
    est = (draw_mm / gp.draw_feed * 60 + travel_mm / eff_travel * 60 + z_s
           + len(cleaned) * (gp.delay_up_s + gp.delay_down_s) + gp.delay_up_s)
    stats = {
        "strokes": len(cleaned), "points": npts, "lines": len(lines),
        "draw_mm": round(draw_mm, 2), "travel_mm": round(travel_mm, 2),
        "pen_lifts": len(cleaned), "est_seconds": round(est, 1),   # chưa tính gia tốc (D7)
        "bounds": {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)},
    }
    warnings: list[dict] = []
    if dropped:
        warnings.append({"code": "dropped_strokes", "count": dropped})
    if gp.draw_feed > machine.rapid_feed or gp.travel_feed > machine.rapid_feed:
        warnings.append({"code": "feed_above_rapid", "count": 1})
    return lines, stats, warnings
