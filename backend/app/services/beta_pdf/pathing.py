"""Tiện ích đi nét dùng chung: nối nét liền nhau, sắp thứ tự gần nhất, đo độ dài. Thuần hàm, không phụ thuộc PDF."""
from __future__ import annotations

import math

JOIN_MM = 0.25                   # đầu nét này cách đuôi nét trước không quá mức này thì nối thành một nét (đỡ một lần nhấc bút)


def length(stroke) -> float:
    return sum(math.dist(a, b) for a, b in zip(stroke, stroke[1:]))


def join(strokes, gap: float = JOIN_MM) -> list:
    """Nối nét kế nhau nếu điểm cuối nét trước gần điểm đầu (hoặc điểm cuối, khi đó đảo chiều) nét sau. Giữ nguyên thứ tự."""
    out: list = []
    for s in strokes:
        if len(s) < 2:
            continue
        if out and math.dist(out[-1][-1], s[0]) <= gap:
            out[-1].extend(s[1:])
        elif out and math.dist(out[-1][-1], s[-1]) <= gap:
            out[-1].extend(reversed(s[:-1]))
        else:
            out.append(list(s))
    return out


def order_nearest(strokes, start=(0.0, 0.0)) -> list:
    """Sắp các nét theo "láng giềng gần nhất" (có đảo chiều nét nếu đầu kia gần hơn). O(n²): dùng cho vài nghìn nét trở xuống."""
    left = [list(s) for s in strokes if len(s) >= 2]
    out: list = []
    pos = start
    while left:
        best, flip, best_d = 0, False, float("inf")
        for i, s in enumerate(left):
            d0 = math.dist(pos, s[0])
            d1 = math.dist(pos, s[-1])
            if d0 < best_d:
                best, flip, best_d = i, False, d0
            if d1 < best_d:
                best, flip, best_d = i, True, d1
        s = left.pop(best)
        if flip:
            s.reverse()
        out.append(s)
        pos = s[-1]
    return out


def stats(strokes) -> dict:
    """Số nét (≈ số lần nhấc bút), tổng độ dài vẽ và độ dài di chuyển trên không (mm)."""
    draw = pen_up = 0.0
    prev = None
    points = 0
    for s in strokes:
        points += len(s)
        draw += length(s)
        if prev is not None:
            pen_up += math.dist(prev, s[0])
        prev = s[-1]
    return {"strokes": len(strokes), "points": points, "draw_mm": round(draw, 2), "pen_up_mm": round(pen_up, 2)}
