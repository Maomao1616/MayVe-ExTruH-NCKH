"""Bắt nét viền bằng hiệu hai Gaussian (DoG, lõi của XDoG): nét đen nơi vùng tối hơn xung quanh.

Chỉ lấy biên / đường mảnh, không tô đặc vùng tối (vùng đặc là việc của các kiểu tô).
Ảnh vào là độ đậm 0..1 (1 = đen). Ra mặt nạ bool cần làm mảnh (trace.py).
"""
from __future__ import annotations

import cv2
import numpy as np

SIGMA_PX = 1.0           # độ mảnh của nét bắt được, theo điểm ảnh làm việc (≈ bề rộng bút / 1,3)
K = 1.6                  # tỷ lệ hai Gaussian (1,6 xấp xỉ toán tử Laplacian-of-Gaussian)
THRESHOLD = 0.03         # độ chênh tối thiểu (thang 0..1) mới tính là nét: cao hơn = ít nét nhiễu


def ink_mask(dark: np.ndarray, sigma_px: float = SIGMA_PX, threshold: float = THRESHOLD) -> np.ndarray:
    g1 = cv2.GaussianBlur(dark, (0, 0), sigma_px)
    g2 = cv2.GaussianBlur(dark, (0, 0), sigma_px * K)
    return (g1 - g2) > threshold
