"""Gộp chuỗi điểm của một nét thành ít lệnh hơn: cung tròn G2/G3 và đoạn thẳng G1 dài (bỏ điểm gần thẳng hàng).

Lý do (đo máy thật 13/11/2026, tờ thử 7.6): phần mềm gửi một dòng rồi chờ `ok`, máy chỉ nhận được ~125 dòng/giây
dù đoạn dài hay ngắn. Ở tốc độ vẽ 8000 mm/phút (133 mm/s), nét gồm các đoạn ngắn hơn ~1 mm bị chậm lại:
vòng tròn 754 mm vẽ bằng đoạn 0,1 mm mất 60,7 s, bằng cung G2 chỉ 5,7 s (đủ tốc, hàng đợi trong máy đầy).
Sai lệch so với nét gốc không quá ARC_TOL_MM ở mọi điểm và mọi trung điểm đoạn: nhỏ hơn nhiều so với bề rộng nét.

Chạy trên tọa độ MÁY (sau gcode.to_machine) vì đảo trục Y làm đổi chiều quay G2 <-> G3.
"""
from __future__ import annotations

import math

import numpy as np

ARC_TOL_MM = 0.02          # sai lệch tối đa so với nét gốc (nét bút 0,38–0,5 mm: không thấy được)
ARC_MIN_POINTS = 4         # cung phải ôm ít nhất 4 điểm (3 đoạn); ít hơn thì để G1 (cung không bớt được dòng nào)
ARC_MIN_R_MM = 0.2         # cung nhỏ hơn thế coi như góc gắt: giữ G1
ARC_MAX_R_MM = 2000.0      # cung lớn hơn thế gần như thẳng: để phần đoạn thẳng xử lý (tránh I / J khổng lồ)
ARC_MAX_SWEEP_DEG = 300.0  # không gộp gần trọn vòng: đầu và cuối trùng nhau thì G2 hiểu thành cả vòng tròn
ARC_MIN_PRECISION = 3      # chỉ gộp cung khi tọa độ ghi >= 3 chữ số thập phân (firmware báo lỗi nếu bán kính đầu / cuối lệch > 0,005 mm)


def _circle(a, b, c):
    """Tâm và bán kính đường tròn qua 3 điểm; None nếu gần thẳng hàng."""
    ax, ay = a
    bx, by = b
    cx, cy = c
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    a2, b2, c2 = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def _line_ok(p: np.ndarray, i: int, j: int, tol: float) -> bool:
    """Các điểm i..j nằm sát đoạn thẳng p[i] -> p[j] và đi một chiều (không quay lại)."""
    if j - i < 2:
        return True
    a, b = p[i], p[j]
    v = b - a
    L = math.hypot(v[0], v[1])
    if L < 1e-9:
        return False
    q = p[i + 1:j] - a
    dist = np.abs(q[:, 0] * v[1] - q[:, 1] * v[0]) / L
    along = (q[:, 0] * v[0] + q[:, 1] * v[1]) / L
    return bool(np.all(dist <= tol) and np.all(np.diff(np.concatenate(([0.0], along, [L]))) > -tol))


def _arc_ok(p: np.ndarray, i: int, j: int, tol: float):
    """(tâm x, tâm y, cw) nếu các điểm i..j nằm trên một cung tròn hợp lệ, không thì None."""
    if j - i + 1 < ARC_MIN_POINTS:
        return None
    circ = _circle(p[i], p[(i + j) // 2], p[j])
    if circ is None:
        return None
    cx, cy, r = circ
    if not ARC_MIN_R_MM <= r <= ARC_MAX_R_MM:
        return None
    seg = p[i:j + 1]
    mids = (seg[1:] + seg[:-1]) / 2
    for pts in (seg, mids):
        if np.max(np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - r)) > tol:
            return None
    rel = seg - (cx, cy)
    cross = rel[:-1, 0] * rel[1:, 1] - rel[:-1, 1] * rel[1:, 0]
    dot = rel[:-1, 0] * rel[1:, 0] + rel[:-1, 1] * rel[1:, 1]
    ang = np.arctan2(cross, dot)                            # góc quay từng đoạn (dương = ngược kim đồng hồ)
    if np.all(ang > 0):
        cw = False
    elif np.all(ang < 0):
        cw = True
    else:
        return None
    if math.degrees(abs(float(np.sum(ang)))) > ARC_MAX_SWEEP_DEG:
        return None
    return cx, cy, cw


def _longest(ok, i: int, n: int) -> int:
    """j lớn nhất (i < j < n) mà ok(i, j) đúng: nhân đôi bước rồi chia đôi. Coi như ok đơn điệu theo j."""
    lo = i + 1                     # coi như luôn đúng (một đoạn / giá trị khởi đầu)
    step = 1
    hi = None
    while True:
        j = min(n - 1, lo + step)
        if j <= lo:
            return lo
        if ok(i, j):
            lo = j
            step *= 2
            if lo == n - 1:
                return lo
        else:
            hi = j
            break
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(i, mid):
            lo = mid
        else:
            hi = mid
    return lo


def fit(points: list[tuple[float, float]], tol: float = ARC_TOL_MM) -> list[tuple]:
    """Chuỗi điểm (tọa độ máy) -> danh sách lệnh sau điểm đầu: ("L", x, y) hoặc ("A", x, y, tâm x, tâm y, cw)."""
    p = np.asarray(points, float)
    n = len(p)
    out: list[tuple] = []
    i = 0
    while i < n - 1:
        jl = _longest(lambda a, b: _line_ok(p, a, b, tol), i, n)
        arc = None
        ja = i
        if n - i >= ARC_MIN_POINTS:
            def arc_ok(a, b):
                return b - a + 1 < ARC_MIN_POINTS or _arc_ok(p, a, b, tol) is not None
            ja = _longest(arc_ok, i, n)
            arc = _arc_ok(p, i, ja, tol) if ja - i + 1 >= ARC_MIN_POINTS else None
        if arc is not None and ja > jl:
            out.append(("A", float(p[ja][0]), float(p[ja][1]), arc[0], arc[1], arc[2]))
            i = ja
        else:
            out.append(("L", float(p[jl][0]), float(p[jl][1])))
            i = jl
    return out
