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
