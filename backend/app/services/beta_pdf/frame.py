"""Đường kẻ (viền bảng, khung, gạch chân) -> nét thẳng sạch, vẽ thẳng từ vector PDF, KHÔNG qua ảnh và skeleton.

Từ PDF Word / trình duyệt, một viền ô thường được vẽ thành hình chữ nhật tô đặc rất mỏng, và mỗi cạnh chung của hai ô bị vẽ 2 lần,
nên cần:
  1. tách mọi hình thành các cạnh (đoạn thẳng);
  2. đường dày hơn 1,5 × bút thì thay bằng 2 đường sát nhau (như chữ đậm vẽ 2 đường) để nét ra gần đúng độ dày;
  3. gộp cạnh ngang / dọc trùng nhau hoặc nối tiếp nhau thành một đường dài;
  4. nối các cạnh gặp nhau thành một nét liền (góc vuông được dựng đúng giao điểm), ưu tiên đi thẳng ở ngã ba, ngã tư;
  5. sắp thứ tự gần nhất.
"""
from __future__ import annotations

import math

from . import pathing

AXIS_TOL_MM = 0.25               # cạnh lệch trục ít hơn mức này coi là ngang / dọc
SAME_LINE_MM = 0.3               # hai cạnh song song cách nhau ít hơn mức này coi là một đường
TOUCH_MM = 0.3                   # hai đoạn cùng đường hở nhau ít hơn mức này thì nối liền
JOIN_TOL_MM = 0.35               # hai đầu cạnh cách nhau ít hơn mức này coi là gặp nhau
THICK_FACTOR = 1.5               # đường dày hơn bút × mức này thì vẽ 2 đường
MAX_OFFSET_MM = 1.0              # hai đường song song lệch tối đa mức này so với tâm
MIN_EDGE_MM = 0.05               # cạnh ngắn hơn mức này bỏ
MAX_EDGES_TO_CHAIN = 3000        # nhiều hơn thì bỏ bước nối (O(n²)), chỉ gộp và sắp thứ tự


def _edges(segments, o):
    out = []
    for seg in segments:
        pts = list(seg.pts)
        pairs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if seg.closed and len(pts) > 2 else [])
        for a, b in pairs:
            if math.dist(a, b) < MIN_EDGE_MM:
                continue
            if o.thick_double and seg.width_mm > THICK_FACTOR * o.pen_mm:
                d = min((seg.width_mm - o.pen_mm) / 2, MAX_OFFSET_MM)
                length = math.dist(a, b)
                nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
                for s in (1, -1):
                    out.append(((a[0] + nx * d * s, a[1] + ny * d * s), (b[0] + nx * d * s, b[1] + ny * d * s)))
            else:
                out.append((tuple(a), tuple(b)))
    return out


def _orient(e):
    (ax, ay), (bx, by) = e
    if abs(ay - by) <= AXIS_TOL_MM:
        return "h"
    if abs(ax - bx) <= AXIS_TOL_MM:
        return "v"
    return None


def _merge_axis(edges, kind: str):
    """Gộp cạnh ngang (hoặc dọc) cùng đường, chồng hoặc nối tiếp nhau."""
    items = []
    for e in edges:
        (ax, ay), (bx, by) = e
        if kind == "h":
            items.append(((ay + by) / 2, min(ax, bx), max(ax, bx)))
        else:
            items.append(((ax + bx) / 2, min(ay, by), max(ay, by)))
    items.sort()
    out = []
    i = 0
    while i < len(items):
        group = [items[i]]
        j = i + 1
        while j < len(items) and items[j][0] - group[0][0] <= SAME_LINE_MM:
            group.append(items[j])
            j += 1
        i = j
        group.sort(key=lambda t: t[1])
        cur = list(group[0])
        coords = [group[0][0]]
        merged = []
        for c, lo, hi in group[1:]:
            if lo <= cur[2] + TOUCH_MM:
                cur[2] = max(cur[2], hi)
                coords.append(c)
            else:
                merged.append((sum(coords) / len(coords), cur[1], cur[2]))
                cur, coords = [c, lo, hi], [c]
        merged.append((sum(coords) / len(coords), cur[1], cur[2]))
        for c, lo, hi in merged:
            out.append(((lo, c), (hi, c)) if kind == "h" else ((c, lo), (c, hi)))
    return out


def _dedupe(edges):
    seen, out = set(), []
    for a, b in edges:
        key = tuple(sorted(((round(a[0], 1), round(a[1], 1)), (round(b[0], 1), round(b[1], 1)))))
        if key not in seen:
            seen.add(key)
            out.append((a, b))
    return out


def _direction(a, b):
    d = math.dist(a, b) or 1.0
    return (b[0] - a[0]) / d, (b[1] - a[1]) / d


def _chain(edges):
    """Nối các cạnh gặp nhau thành nét liền; ở ngã rẽ ưu tiên đi thẳng, góc vuông đặt đúng giao điểm."""
    left = [(e[0], e[1]) for e in sorted(edges, key=lambda e: (min(e[0][1], e[1][1]), min(e[0][0], e[1][0])))]
    out = []
    while left:
        a, b = left.pop(0)
        path = [a, b]
        while True:
            end = path[-1]
            last_dir = _direction(path[-2], end)
            best, best_flip, best_dot = None, False, -2.0
            for i, (p, q) in enumerate(left):
                for flip, (s, t) in ((False, (p, q)), (True, (q, p))):
                    if math.dist(end, s) <= JOIN_TOL_MM:
                        d = _direction(s, t)
                        dot = last_dir[0] * d[0] + last_dir[1] * d[1]
                        if dot > best_dot:
                            best, best_flip, best_dot = i, flip, dot
            if best is None or best_dot < -0.5:             # không còn cạnh nối tiếp, hoặc chỉ còn đường quay đầu
                break
            p, q = left.pop(best)
            s, t = (q, p) if best_flip else (p, q)
            prev, nxt = _orient((path[-2], end)), _orient((s, t))
            if prev and nxt and prev != nxt:                # góc vuông: dựng đúng giao điểm của đường ngang và đường dọc
                if prev == "h":
                    corner = ((s[0] + t[0]) / 2, (path[-2][1] + end[1]) / 2)
                else:
                    corner = ((path[-2][0] + end[0]) / 2, (s[1] + t[1]) / 2)
                path[-1] = corner
            path.append(t)
        out.append(path)
    return out


def build(segments, o) -> list:
    """Danh sách nét (mm, tọa độ trang) của mọi đường kẻ."""
    edges = _edges(segments, o)
    horizontal = [e for e in edges if _orient(e) == "h"]
    vertical = [e for e in edges if _orient(e) == "v"]
    other = _dedupe([e for e in edges if _orient(e) is None])
    merged = _merge_axis(horizontal, "h") + _merge_axis(vertical, "v") + other
    strokes = _chain(merged) if len(merged) <= MAX_EDGES_TO_CHAIN else [list(e) for e in merged]
    return pathing.order_nearest(strokes)
