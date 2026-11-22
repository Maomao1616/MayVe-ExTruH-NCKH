"""Chia 2–4 màu: k-means (OpenCV) trên Lab, ảnh thu nhỏ ~300 px; mỗi màu một vùng, mỗi vùng một lớp bút.

Chỉ để thử mô hình, không cần chính xác: mỗi vùng được tô với mật độ tối thiểu (để màu sáng vẫn hiện),
đậm hơn theo độ đậm của ảnh. Màu nền sáng nhất bị bỏ (coi là giấy) khi skip_background.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

SAMPLE_SIDE = 300
MIN_DENSITY = 0.35               # mật độ nền của vùng màu: luôn có ít nhất một lượt gạch
BACKGROUND_L = 80                # màu sáng hơn mức này (thang L 0..100) mới bị coi là nền
CHROMA_BOOST = 4                 # pixel rực (độ bão hòa cao) được lặp lại chừng này lần khi học cụm
CHROMA_MIN = 45.0                # ngưỡng 'rực' trên thang a, b đã nhân trọng số
CHROMA_WEIGHT = 2.2              # nhấn sắc độ khi phân cụm: đèn màu nhỏ giữa nền tối trung tính vẫn có cụm riêng


@dataclass(frozen=True)
class Region:
    color: str                   # "#rrggbb" (tâm cụm)
    lightness: float             # 0..100
    mask: np.ndarray             # bool (h, w)


def _hex(rgb) -> str:
    r, g, b = (int(round(float(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _weighted(lab: np.ndarray) -> np.ndarray:
    """Lab (uint8 OpenCV) -> float32 [L, a, b] với a, b nhân CHROMA_WEIGHT quanh 0."""
    out = lab.astype(np.float32)
    out[..., 1:] = (out[..., 1:] - 128.0) * CHROMA_WEIGHT
    return out


def split(rgb: np.ndarray, colors: int, skip_background: bool, ctx=None) -> list[Region]:
    """Vùng theo từng màu, sắp từ tối đến sáng. Có thể ít hơn `colors` nếu ảnh ít màu thật."""
    h, w = rgb.shape[:2]
    lab = _weighted(cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB))
    scale = min(1.0, SAMPLE_SIDE / max(h, w))
    small = cv2.resize(lab, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    data = small.reshape(-1, 3)
    vivid = data[np.hypot(data[:, 1], data[:, 2]) > CHROMA_MIN]
    if len(vivid):                                            # màu rực chiếm ít diện tích vẫn có cụm riêng
        data = np.concatenate([data] + [vivid] * (CHROMA_BOOST - 1))
    colors = max(1, min(colors, len(np.unique(data, axis=0))))
    cv2.setRNGSeed(1)                                         # kết quả lặp lại được
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, _, centers = cv2.kmeans(data, colors, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    if ctx:
        ctx.check()
    dist = np.empty((h, w, colors), dtype=np.float32)
    for i, c in enumerate(centers):
        dist[:, :, i] = ((lab - c) ** 2).sum(axis=2)
    label = dist.argmin(axis=2)
    label = cv2.medianBlur(label.astype(np.uint8), 5)         # bỏ đốm lẻ
    regions: list[Region] = []
    for i in np.argsort(centers[:, 0]):                       # tối -> sáng theo L (OpenCV: 0..255)
        L = float(centers[i, 0]) * 100.0 / 255.0
        mask = label == i
        if not mask.any():
            continue
        if skip_background and L > BACKGROUND_L and colors > 1:
            continue
        lab_c = np.array([[[centers[i, 0], centers[i, 1] / CHROMA_WEIGHT + 128.0, centers[i, 2] / CHROMA_WEIGHT + 128.0]]])
        rgb_c = cv2.cvtColor(np.clip(lab_c, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)[0, 0]
        regions.append(Region(_hex(rgb_c), L, mask))
    return regions


def density(dark: np.ndarray, region: Region) -> np.ndarray:
    """Bản đồ độ đậm cho riêng một màu: chỉ trong vùng, tối thiểu MIN_DENSITY."""
    d = np.clip(dark + MIN_DENSITY, 0.0, 1.0)
    return np.where(region.mask, d, 0.0).astype(np.float32)


# === Tách mực (22/11/2026, chủ dự án): chia ảnh theo BỘ BÚT, mỗi bút một lớp với độ đậm riêng =========================
# Khác k-means ở trên (chia VÙNG màu): ở đây mỗi bút tô cả những chỗ mực của nó góp vào màu điểm ảnh (trộn trừ màu như in offset).
# Thuật toán: mật độ quang học OD = -log10(RGB / 255) của điểm ảnh ≈ Σ a_i × OD của bút i (a_i >= 0, giải đúng bằng cách thử
# mọi tập bút con, có phạt nhẹ bút màu để chỗ xám ưu tiên bút đen). Độ đậm của bút i = độ đậm ảnh (đã qua chỉnh tông) × phần
# mực bút i góp. Nhờ vậy mức đen / gamma / tương phản / CLAHE vẫn tác dụng như ảnh đơn sắc.
INK_SETS = {
    # tên bộ -> [(tên, màu bút "#rrggbb", góc lệch so với ô Góc, phạt)] theo THỨ TỰ VẼ: bút nhạt trước, bút đen sau cùng
    "kdn": [("red", "#c8283c", 60.0, 0.06), ("navy", "#1e2f6e", 120.0, 0.06), ("black", "#141414", 0.0, 0.0)],
    "cmyk": [("yellow", "#f0d214", 0.0, 0.04), ("magenta", "#d2287a", 75.0, 0.04), ("cyan", "#008cc8", 15.0, 0.04),
             ("black", "#141414", 45.0, 0.0)],
}
INK_EPS = 1e-3                   # OD nhỏ hơn mức này coi là giấy trắng
# "Độ nổi màu" (0..1, 22/11/2026): bút đen có OD lớn nhất nên lấn át; ba hệ số dưới đây cùng tăng theo độ nổi
BOOST_CHROMA = 1.2               # độ rực (a, b trong Lab) nhân thêm tối đa +120 % khi boost = 1: màu nhạt vẫn đủ sức gọi bút màu
BOOST_COST_CUT = 0.8             # phạt bút màu giảm tối đa 80 %
BOOST_BLACK_CUT = 0.6            # trọng số bút đen giảm tối đa 60 % ở chỗ có bút màu (chỗ chỉ có đen thì không đổi vì chuẩn hóa)


def _od(rgb: np.ndarray) -> np.ndarray:
    return -np.log10(np.clip(rgb.astype(np.float32), 1.0, 255.0) / 255.0)


def _saturate(rgb: np.ndarray, boost: float) -> np.ndarray:
    """Tăng độ rực: nhân a, b trong Lab (giữ nguyên độ sáng)."""
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab[:, :, 1:] = 128.0 + (lab[:, :, 1:] - 128.0) * (1.0 + BOOST_CHROMA * boost)
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)


def separate_inks(rgb: np.ndarray, dark: np.ndarray, ink_set: str, boost: float = 0.0):
    """[(màu "#rrggbb", góc lệch, bản đồ độ đậm float32)] cho từng bút của bộ, theo thứ tự vẽ.
    boost 0..1 = độ nổi màu: màu rực hơn, bút màu bị phạt ít hơn, bút đen bớt lấn."""
    inks = INK_SETS[ink_set]
    boost = float(np.clip(boost, 0.0, 1.0))
    if boost > 0:
        rgb = _saturate(rgb, boost)
    h, w = dark.shape
    small_h, small_w = rgb.shape[:2]
    od = _od(rgb).reshape(-1, 3)                                         # (N, 3)
    pen = np.stack([_od(np.array(_rgb(c), np.float32)) for _, c, _, _ in inks])    # (k, 3)
    pen_lum = pen.mean(axis=1)                                           # độ tối của bút ở phủ 100 %
    cost = np.array([p for *_, p in inks], np.float32) * (1.0 - BOOST_COST_CUT * boost)
    k = len(inks)
    best = np.full(len(od), np.inf, np.float32)
    amount = np.zeros((len(od), k), np.float32)
    ata_all = pen @ pen.T
    for mask in range(1, 1 << k):                                        # mọi tập bút con khác rỗng
        idx = [i for i in range(k) if mask >> i & 1]
        a = pen[idx]                                                     # (m, 3)
        ata = a @ a.T + 1e-4 * np.eye(len(idx))
        rhs = od @ a.T - 0.5 * cost[idx][None, :]                         # (N, m)
        sol = np.linalg.solve(ata, rhs.T).T                              # (N, m)
        ok = (sol >= 0).all(axis=1)
        res = ((od - sol @ a) ** 2).sum(axis=1) + (sol * cost[idx][None, :]).sum(axis=1)
        better = ok & (res < best)
        best = np.where(better, res, best)
        amount[better] = 0.0                                             # bút ngoài tập này không góp mực
        for j, i in enumerate(idx):
            amount[better, i] = sol[better, j]
    lum = pen_lum.copy()
    lum[np.array([p == 0.0 for *_, p in inks])] *= 1.0 - BOOST_BLACK_CUT * boost      # bút đen (phạt 0) bớt lấn
    weight = amount * lum[None, :]                                       # mực bút i góp vào độ tối
    total = weight.sum(axis=1, keepdims=True)
    share = np.where(total > INK_EPS, weight / np.maximum(total, 1e-6), 0.0)
    share = share.reshape(small_h, small_w, k)
    if (small_h, small_w) != (h, w):
        share = cv2.resize(share, (w, h), interpolation=cv2.INTER_LINEAR)
    share = share.reshape(h, w, k)
    out = []
    for i, (name, color, angle, _) in enumerate(inks):
        out.append((color, angle, np.clip(dark * share[:, :, i], 0.0, 1.0).astype(np.float32)))
    return out


def _rgb(hexcolor: str):
    return tuple(int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
