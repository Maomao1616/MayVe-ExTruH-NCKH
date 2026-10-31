"""Nét viền phác họa: ảnh -> mặt nạ đường mảnh 1 điểm ảnh (trace.py dò thành nét liền).

Ba lớp, gộp lại rồi nối khe hở:
1. Nét mực (vùng ĐẬM hẹp, dày tới ~4 mm: viền hoạt hình, chữ, chấm mắt): top-hat trên ảnh độ đậm,
   làm mảnh thành ĐƯỜNG GIỮA -> bút đi một lượt, nét dày không thành hai đường song song.
   Vạch SÁNG mảnh trên nền tối (thanh giường, dây sáng) cũng lấy đường giữa.
   Chấm đậm (skeleton gần như một điểm) -> vẽ vòng viền của chấm.
2. Ranh giới mảng (hai vùng khác sáng tối HOẶC khác màu, không cần nét đen): Canny trên ảnh đã làm mịn
   giữ cạnh (bilateral), thêm hai kênh màu a/b của Lab nên đỏ cạnh xanh cùng độ sáng vẫn có viền.
   Bỏ phần nằm sát nét mực (Canny cho hai mép của một nét mực, lớp 1 đã có đường giữa).
3. Nối khe hở: mỗi đầu mút nhìn về phía trước (trong góc 55°), gặp nét khác trong ~1,5 mm thì kẻ nối.

Ảnh vào là độ đậm 0..1 (1 = đen) và (tùy chọn) ảnh màu RGB cùng cỡ. `detail` = low / medium / high.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

# mức chi tiết -> (Canny thấp, Canny cao, ngưỡng nét mực top-hat 0..1, cạnh mảng ngắn nhất mm)
DETAIL = {
    "low": (30, 80, 0.22, 4.0),          # ảnh chụp nhiều chi tiết (lông, gỗ, lá): chỉ giữ khối chính
    "medium": (18, 50, 0.16, 2.5),
    "high": (10, 30, 0.11, 1.5),         # hình vẽ đơn giản, nét nhạt
}
INK_MAX_MM = 4.0         # nét mực / chấm dày tới chừng này thì lấy đường giữa (dày hơn = mảng, lấy viền)
LIGHT_MAX_MM = 1.2       # vạch sáng mảnh hơn chừng này thì lấy đường giữa
GAP_MM = 1.5             # khe hở được nối (tính cả phần đầu nét co lại khi làm mảnh nét dày)
GAP_ANGLE = 55.0         # độ lệch hướng tối đa khi nối (độ)


def _odd(n: float) -> int:
    n = max(3, int(round(n)))
    return n if n % 2 else n + 1


def _tophat(img: np.ndarray, size_px: float) -> np.ndarray:
    k = _odd(size_px)
    return cv2.morphologyEx(img, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))


def _remove_small(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_pixels
    return keep[lab]


def _drop_short(mask: np.ndarray, min_px: float) -> np.ndarray:
    """Bỏ mẩu cạnh có khung bao ngắn hơn min_px (nhiễu kết cấu: lông, vân gỗ)."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = np.maximum(stats[1:, cv2.CC_STAT_WIDTH], stats[1:, cv2.CC_STAT_HEIGHT]) >= min_px
    return keep[lab]


def ink_mask(ds: np.ndarray, px_mm: float, threshold: float) -> np.ndarray:
    """Nét mực mọi độ dày tới INK_MAX_MM + vạch sáng mảnh. `ds` = độ đậm đã làm mịn."""
    ink = (_tophat(ds, INK_MAX_MM / px_mm) > threshold) & (ds > 0.35)
    ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    light = (_tophat(1.0 - ds, LIGHT_MAX_MM / px_mm) > threshold + 0.06) & (ds < 0.75)
    light = _remove_small(light, max(4, int((2.0 / px_mm) ** 2 / 4)))
    return _remove_small(ink | light, 8)


def region_edges(ds: np.ndarray, rgb: np.ndarray | None, lo: int, hi: int) -> np.ndarray:
    """Ranh giới mảng sáng/tối và mảng màu (Canny trên ảnh đã làm mịn giữ cạnh)."""
    gray = (255.0 * (1.0 - ds)).astype(np.uint8)
    gray = cv2.bilateralFilter(cv2.bilateralFilter(gray, 0, 30, 3), 0, 30, 3)
    edges = cv2.Canny(gray, lo, hi, L2gradient=True) > 0
    if rgb is not None and rgb.shape[:2] == ds.shape:
        lab = cv2.bilateralFilter(cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB), 0, 25, 3)
        for c in (1, 2):                                   # a (xanh lá - đỏ), b (xanh dương - vàng)
            edges |= cv2.Canny(np.ascontiguousarray(lab[..., c]), lo, hi, L2gradient=True) > 0
    return edges


def blob_rings(ink: np.ndarray, skel: np.ndarray) -> np.ndarray:
    """Chấm đậm (mắt, nút): skeleton ngắn so với bề dày -> vòng viền của chấm, không để mất chấm."""
    n, lab, _, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    rings = np.zeros(ink.shape, np.uint8)
    if n <= 1:
        return rings > 0
    dist = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 3)
    radius = np.zeros(n, np.float32)
    np.maximum.at(radius, lab.ravel(), dist.ravel())
    sk_len = np.bincount(lab[skel], minlength=n)
    for i in np.nonzero((radius >= 2.0) & (sk_len < 5.0 * radius))[0]:
        if i == 0:
            continue
        cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(rings, cs, -1, 1, 1)
    return rings > 0


def bridge(skel: np.ndarray, gap_px: float, max_angle: float = GAP_ANGLE) -> np.ndarray:
    """Nối khe hở: từ mỗi đầu mút đi thẳng ra phía trước tìm điểm nét gần nhất (trong góc), kẻ đoạn nối."""
    from scipy.spatial import cKDTree

    sk = skel.astype(np.uint8)
    neighbours = cv2.filter2D(sk, -1, np.ones((3, 3), np.float32), borderType=cv2.BORDER_CONSTANT) - sk
    ends = np.argwhere((sk > 0) & (neighbours == 1))
    pts = np.argwhere(sk > 0)
    if len(ends) == 0 or len(pts) < 2:
        return skel
    tree = cKDTree(pts)
    out = sk.copy()
    cos_max = math.cos(math.radians(max_angle))
    for y, x in ends:
        near = pts[tree.query_ball_point((y, x), 5)]
        v = np.array((y, x), np.float64) - near.mean(axis=0)     # hướng đi ra của đầu mút
        nv = math.hypot(*v)
        if nv < 0.5:
            continue
        v /= nv
        best, best_d = None, gap_px + 1.0
        for j in tree.query_ball_point((y, x), gap_px):
            w = pts[j] - (y, x)
            dist = math.hypot(*w)
            if 2.0 <= dist < best_d and (w @ v) / dist >= cos_max:
                best, best_d = pts[j], dist
        if best is not None:
            cv2.line(out, (int(x), int(y)), (int(best[1]), int(best[0])), 1, 1)
    return out > 0


def outline_mask(dark: np.ndarray, rgb: np.ndarray | None, px_mm: float, detail: str = "medium",
                 ctx=None) -> np.ndarray:
    """Mặt nạ đường mảnh 1 điểm ảnh, sẵn sàng cho trace.to_strokes."""
    from skimage.morphology import skeletonize

    lo, hi, threshold, min_mm = DETAIL.get(detail, DETAIL["medium"])
    ds = cv2.bilateralFilter(dark.astype(np.float32), 0, 0.12, 2)       # bớt nhiễu JPEG, giữ mép nét
    ink = ink_mask(ds, px_mm, threshold)
    ink_skel = skeletonize(ink)
    rings = blob_rings(ink, ink_skel)
    if ctx:
        ctx.check()
    reg = region_edges(ds, rgb, lo, hi)
    reg &= ~(cv2.dilate(ink.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
    reg = _drop_short(reg, min_mm / px_mm)
    if ctx:
        ctx.check()
    merged = ink_skel | reg | rings
    merged = skeletonize(cv2.dilate(merged.astype(np.uint8), np.ones((2, 2), np.uint8)) > 0)
    merged = bridge(merged, gap_px=max(3.0, GAP_MM / px_mm))
    return skeletonize(merged)
