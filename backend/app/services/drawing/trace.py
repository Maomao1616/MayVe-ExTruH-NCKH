"""Mặt nạ nét -> làm mảnh (skeleton) -> dò thành các nét liền (mm).

Skeleton cho đường GIỮA nét nên bút đi một lượt thay vì hai đường song song (như dò biên).
Dò đồ thị: bắt đầu từ các đầu mút, tại chỗ rẽ ưu tiên đi thẳng; nhánh còn lại bắt đầu từ chính điểm rẽ.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from skimage.morphology import remove_small_objects, skeletonize

OFFSETS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
SMOOTH_PASSES = 2
SIMPLIFY_PX = 0.6


def skeleton(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    if min_pixels > 1:
        mask = remove_small_objects(mask, max_size=min_pixels - 1, connectivity=2)
    return skeletonize(mask)


def _graph(skel: np.ndarray):
    ys, xs = np.nonzero(skel)
    ident = np.full(skel.shape, -1, dtype=np.int32)
    ident[ys, xs] = np.arange(len(ys), dtype=np.int32)
    h, w = skel.shape
    nbrs: list[list[int]] = [[] for _ in range(len(ys))]
    for dy, dx in OFFSETS:
        y2, x2 = ys + dy, xs + dx
        ok = (y2 >= 0) & (y2 < h) & (x2 >= 0) & (x2 < w)
        other = np.full(len(ys), -1, dtype=np.int32)
        other[ok] = ident[y2[ok], x2[ok]]
        for i in np.nonzero(other >= 0)[0].tolist():
            nbrs[i].append(int(other[i]))
    return ys, xs, nbrs


def _walk(start: int, prev: int, nbrs, xs, ys, seen: bytearray) -> list[int]:
    """Đi từ start (đã coi là đã thăm) theo hướng ra xa prev, ưu tiên đi thẳng."""
    path = [start]
    cur, last = start, prev
    while True:
        cand = [n for n in nbrs[cur] if not seen[n]]
        if not cand:
            return path
        if len(cand) > 1 and last >= 0:
            dx, dy = xs[cur] - xs[last], ys[cur] - ys[last]
            cand.sort(key=lambda n: -((xs[n] - xs[cur]) * dx + (ys[n] - ys[cur]) * dy)
                      / (math.hypot(xs[n] - xs[cur], ys[n] - ys[cur]) or 1.0))
        nxt = cand[0]
        seen[nxt] = 1
        path.append(nxt)
        cur, last = nxt, cur


def paths(skel: np.ndarray) -> list[np.ndarray]:
    """Các nét dưới dạng mảng (k, 2) tọa độ điểm ảnh (x, y)."""
    ys, xs, nbrs = _graph(skel)
    n = len(ys)
    seen = bytearray(n)
    out: list[np.ndarray] = []

    def emit(ids: list[int]) -> None:
        if len(ids) >= 2:
            out.append(np.stack([xs[ids], ys[ids]], axis=1).astype(np.float32))

    order = [i for i in range(n) if len(nbrs[i]) == 1] + list(range(n))   # đầu mút trước, vòng kín sau
    for s in order:
        if seen[s]:
            continue
        seen[s] = 1
        anchors = [m for m in nbrs[s] if seen[m]]
        fwd = _walk(s, anchors[0] if anchors else -1, nbrs, xs, ys, seen)
        if len(nbrs[s]) >= 2 and not anchors:
            back = _walk(s, fwd[1] if len(fwd) > 1 else -1, nbrs, xs, ys, seen)
            ids = back[:0:-1] + fwd
        else:
            ids = fwd
        if anchors:
            ids = [anchors[0]] + ids                                       # nối với điểm rẽ đã thăm
        emit(ids)
    return out


def smooth(pts: np.ndarray, passes: int = SMOOTH_PASSES) -> np.ndarray:
    """Trung bình 3 điểm, giữ nguyên hai đầu (làm mượt bậc thang của lưới điểm ảnh)."""
    for _ in range(passes):
        if len(pts) < 3:
            break
        mid = (pts[:-2] + 2 * pts[1:-1] + pts[2:]) / 4.0
        pts = np.concatenate([pts[:1], mid, pts[-1:]])
    return pts


def to_strokes(skel: np.ndarray, px_x_mm: float, px_y_mm: float, min_len_mm: float) -> list[list[tuple[float, float]]]:
    strokes = []
    scale = np.array([px_x_mm, px_y_mm], dtype=np.float32)
    for p in paths(skel):
        p = smooth(p)
        if len(p) > 2:
            p = cv2.approxPolyDP(p.reshape(-1, 1, 2), SIMPLIFY_PX, False).reshape(-1, 2)
        mm = (p + 0.5) * scale
        length = float(np.hypot(*np.diff(mm, axis=0).T).sum()) if len(mm) > 1 else 0.0
        if length >= min_len_mm:
            strokes.append([(round(float(x), 3), round(float(y), 3)) for x, y in mm])
    return strokes
