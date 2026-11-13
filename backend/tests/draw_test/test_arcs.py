"""Gộp chuỗi điểm thành cung G2/G3 + đoạn G1 dài (arcs.py) và chỗ dùng nó trong gcode.build_gcode."""
import math
import re

import pytest

from app.services.drawing import arcs, gcode as gc, spec

M = spec.parse("machine", {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 8000})
NUM = re.compile(r"([XYIJ])(-?[\d.]+)")


def G(**kw):
    kw.setdefault("pen_up_z", 3)
    kw.setdefault("pen_down_z", 0)
    return spec.parse("gcode", kw)


def circle(cx, cy, r, step, turns=1.0, ccw=True):
    n = int(round(2 * math.pi * r / step))
    k = int(n * turns)
    s = 1 if ccw else -1
    return [(cx + r * math.cos(s * 2 * math.pi * i / n), cy + r * math.sin(s * 2 * math.pi * i / n)) for i in range(k + 1)]


def walk(start, moves, step=0.05):
    """Điểm dày dọc theo các lệnh fit() để đo sai lệch so với nét gốc."""
    pts = [start]
    cur = start
    for m in moves:
        if m[0] == "L":
            end = (m[1], m[2])
            n = max(1, int(math.dist(cur, end) / step))
            pts += [(cur[0] + (end[0] - cur[0]) * t / n, cur[1] + (end[1] - cur[1]) * t / n) for t in range(1, n + 1)]
        else:
            _, ex, ey, cx, cy, cw = m
            r = math.hypot(cur[0] - cx, cur[1] - cy)
            a0 = math.atan2(cur[1] - cy, cur[0] - cx)
            a1 = math.atan2(ey - cy, ex - cx)
            sweep = -((a0 - a1) % (2 * math.pi)) if cw else (a1 - a0) % (2 * math.pi)
            n = max(1, int(abs(sweep) * r / step))
            pts += [(cx + r * math.cos(a0 + sweep * t / n), cy + r * math.sin(a0 + sweep * t / n)) for t in range(1, n + 1)]
            end = (ex, ey)
        cur = end
    return pts


def max_gap(a, b):
    """Khoảng cách lớn nhất từ một điểm của a tới điểm gần nhất của b (b dày)."""
    return max(min(math.dist(p, q) for q in b) for p in a)


def test_circle_of_short_segments_becomes_few_arcs():
    pts = circle(50, 50, 10, 0.1, turns=1.0)
    moves = arcs.fit(pts)
    assert len(moves) <= 4                                    # 629 đoạn -> vài cung (không gộp quá 300° một lần)
    assert all(m[0] == "A" and not m[5] for m in moves)       # ngược kim đồng hồ = G3
    for m in moves:
        assert math.hypot(m[3] - 50, m[4] - 50) < 0.01
    assert max_gap(pts, walk(pts[0], moves)) <= arcs.ARC_TOL_MM + 0.03


def test_clockwise_circle_gives_g2():
    moves = arcs.fit(circle(0, 0, 5, 0.2, turns=0.5, ccw=False))
    assert moves and all(m[0] == "A" and m[5] for m in moves)


def test_collinear_points_merge_into_one_line():
    assert arcs.fit([(i * 0.3, 2.0) for i in range(40)]) == [("L", pytest.approx(11.7), 2.0)]


def test_sharp_zigzag_keeps_every_corner():
    pts = [(i, (i % 2) * 3.0) for i in range(12)]
    moves = arcs.fit(pts)
    assert [(m[1], m[2]) for m in moves] == pts[1:] and all(m[0] == "L" for m in moves)


def test_line_then_semicircle_then_line_stays_on_path():
    a = [(x * 0.5, 0.0) for x in range(21)]                              # 0 -> 10
    turn = [(10 + 2 * math.sin(t * math.pi / 30), 2 - 2 * math.cos(t * math.pi / 30)) for t in range(1, 31)]
    b = [(10 - x * 0.5, 4.0) for x in range(1, 21)]
    pts = a + turn + b
    moves = arcs.fit(pts)
    assert [m[0] for m in moves] == ["L", "A", "L"]
    assert max_gap(pts, walk(pts[0], moves)) <= arcs.ARC_TOL_MM + 0.03


def test_backtracking_points_are_not_merged_into_a_line():
    moves = arcs.fit([(0, 0), (5, 0), (3, 0), (8, 0)])
    assert len(moves) == 3


def _arc_lines(lines):
    return [l for l in lines if l.startswith(("G2", "G3"))]


def _radius_mismatch(lines):
    x = y = 0.0
    worst = 0.0
    for ln in lines:
        v = dict((k, float(n)) for k, n in NUM.findall(ln))
        if ln.startswith(("G2", "G3")):
            cx, cy = x + v["I"], y + v["J"]
            worst = max(worst, abs(math.hypot(x - cx, y - cy) - math.hypot(v["X"] - cx, v["Y"] - cy)))
        if "X" in v:
            x, y = v["X"], v["Y"]
    return worst


def test_build_gcode_writes_arcs_and_radii_match():
    lines, st, _ = gc.build_gcode([circle(100, 100, 10, 0.1, turns=1.0)], G(), M)
    arcs_ = _arc_lines(lines)
    assert arcs_ and st["arcs"] == len(arcs_) and st["lines"] < 20
    assert all("I" in l and "J" in l and "F" in lines[lines.index(arcs_[0])] for l in arcs_)
    assert _radius_mismatch(lines) < 0.005                    # firmware báo lỗi nếu lệch > 0,005 mm


def test_invert_y_swaps_arc_direction():
    pts = [circle(100, 100, 10, 0.1, turns=0.5)]
    normal, _, _ = gc.build_gcode(pts, G(), M)
    flipped, _, _ = gc.build_gcode(pts, G(), spec.parse("machine", {**M.as_dict(), "invert_y": True}))
    assert {l[:2] for l in _arc_lines(normal)} == {"G3"}
    assert {l[:2] for l in _arc_lines(flipped)} == {"G2"}


def test_low_precision_or_switch_off_keeps_g1_only(monkeypatch):
    pts = [circle(100, 100, 10, 0.1, turns=0.5)]
    lines, _, _ = gc.build_gcode(pts, G(precision=2), M)
    assert not _arc_lines(lines)
    monkeypatch.setattr(gc, "USE_ARCS", False)
    lines, st, _ = gc.build_gcode(pts, G(), M)
    assert not _arc_lines(lines) and st["arcs"] == 0 and st["lines"] > 300


def test_estimate_respects_lines_per_second(monkeypatch):
    """Tờ 7.6 (13/11/2026): vòng 754 mm bằng đoạn 0,1 mm mất 60,7 s thật (~125 dòng/giây), bằng G2 5,7 s."""
    pts = [circle(100, 100, 10, 0.1, turns=12)]
    monkeypatch.setattr(gc, "USE_ARCS", False)
    _, slow, _ = gc.build_gcode(pts, G(draw_feed=8000), M)
    assert slow["est_seconds"] >= (len(pts[0]) - 1) / gc.EST_LINES_PER_S
    monkeypatch.setattr(gc, "USE_ARCS", True)
    _, fast, _ = gc.build_gcode(pts, G(draw_feed=8000), M)
    assert fast["est_seconds"] < slow["est_seconds"] / 5


def test_default_delays_are_zero_so_no_g4():
    lines, _, _ = gc.build_gcode([[(0, 0), (5, 0)], [(10, 10), (12, 10)]], G(), M)
    assert not any(l.startswith("G4") for l in lines)
