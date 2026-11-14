"""Mặt nạ nét -> làm mảnh (skeleton) -> dò thành các nét liền (mm).

Skeleton cho đường GIỮA nét nên bút đi một lượt thay vì hai đường song song (như dò biên).
Dò đồ thị: bắt đầu từ các đầu mút, tại chỗ rẽ ưu tiên đi thẳng; nhánh còn lại bắt đầu từ chính điểm rẽ.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

OFFSETS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
SMOOTH_MM = 0.8                  # làm mượt nét theo chiều dài thật (Gauss dọc nét, sigma mm). Trước 14/11/2026: trung bình
                                 # 3 điểm × 2 lượt (~1 điểm ảnh = 0,3 mm) còn răng cưa của lưới điểm ảnh -> nét run
CLOSED_SIGMA_FRAC = 0.05         # vòng kín: sigma ≤ 5 % chu vi (bán kính co ≤ ~5 %)
SMOOTH_STEP_PX = 0.5             # lấy mẫu lại nét mỗi 0,5 điểm ảnh trước khi làm mượt
SIMPLIFY_PX = 0.6
CLOSE_PX = 2.0                   # hai đầu một nét cách nhau không quá chừng này điểm ảnh thì khép thành vòng


def skeleton(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    # nạp scikit-image lúc cần (~0,65 s): server chính không xử lý ảnh (tiến trình con làm), bật nhanh hơn
    from skimage.morphology import remove_small_objects, skeletonize
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


def smooth(pts: np.ndarray, sigma_px: float) -> np.ndarray:
    """Làm mượt Gauss dọc theo chiều dài nét. Nét hở giữ nguyên hai đầu và hướng ở đầu (đệm đối xứng qua điểm đầu /
    cuối); vòng kín (điểm đầu = điểm cuối) làm mượt vòng quanh."""
    from scipy.ndimage import gaussian_filter1d
    if len(pts) < 4 or sigma_px <= 0:
        return pts
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    if s[-1] < 2 * SMOOTH_STEP_PX:
        return pts
    t = np.linspace(0.0, s[-1], max(4, int(s[-1] / SMOOTH_STEP_PX) + 1))
    p = np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], axis=1)
    sig = sigma_px / (t[1] - t[0])
    if len(pts) > 6 and (pts[0] == pts[-1]).all():
        sig = min(sig, CLOSED_SIGMA_FRAC * s[-1] / (t[1] - t[0]))   # vòng nhỏ (chấm mắt): làm mượt ít để không co lại
        q = gaussian_filter1d(p[:-1], sig, axis=0, mode="wrap")
        return np.concatenate([q, q[:1]]).astype(np.float32)
    k = min(len(p) - 1, int(3 * sig) + 1)
    pre = 2 * p[0] - p[1:k + 1][::-1]
    post = 2 * p[-1] - p[-k - 1:-1][::-1]
    q = gaussian_filter1d(np.concatenate([pre, p, post]), sig, axis=0, mode="nearest")[k:k + len(p)]
    return q.astype(np.float32)


def to_strokes(skel: np.ndarray, px_x_mm: float, px_y_mm: float, min_len_mm: float) -> list[list[tuple[float, float]]]:
    strokes = []
    scale = np.array([px_x_mm, px_y_mm], dtype=np.float32)
    for p in paths(skel):
        closed = len(p) > 6 and float(np.hypot(*(p[0] - p[-1]))) <= CLOSE_PX
        if closed:
            p = np.concatenate([p, p[:1]])                 # vòng kín (hình tròn, số 0, chữ o): khép lại, đừng để hở một điểm ảnh
        p = smooth(p, SMOOTH_MM / ((px_x_mm + px_y_mm) / 2))
        if len(p) > 2:
            p = cv2.approxPolyDP(p.reshape(-1, 1, 2), SIMPLIFY_PX, False).reshape(-1, 2)
        if closed and len(p) > 2:
            p = np.concatenate([p, p[:1]]) if (p[-1] != p[0]).any() else p      # approxPolyDP có thể bỏ điểm cuối trùng đầu
        mm = (p + 0.5) * scale
        length = float(np.hypot(*np.diff(mm, axis=0).T).sum()) if len(mm) > 1 else 0.0
        if length >= min_len_mm:
            strokes.append([(round(float(x), 3), round(float(y), 3)) for x, y in mm])
    return strokes
