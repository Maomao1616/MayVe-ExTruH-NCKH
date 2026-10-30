"""Chỉnh sắc độ: ảnh xám uint8 -> bản đồ độ đậm float32 0..1 (1 = đen nhất, cần nhiều mực nhất).

Thứ tự (sau khi đã thu nhỏ): khử nhiễu -> tự cân sáng -> mức đen/trắng + gamma -> CLAHE -> đảo.
"""
from __future__ import annotations

import cv2
import numpy as np

cv2.setNumThreads(2)             # chừa CPU cho việc điều khiển máy


def darkness(gray: np.ndarray, raster, style, ctx=None) -> np.ndarray:
    """`raster` = nhóm tham số raster, `style` = nhóm kiểu tô (chỉ dùng `invert`)."""
    img = gray
    if raster.denoise:                                    # NLM: chậm, chỉ khi bật
        img = cv2.fastNlMeansDenoising(img, None, h=7, templateWindowSize=5, searchWindowSize=15)
        if ctx:
            ctx.check()
    if raster.auto_levels:                                # kéo giãn 1–99% (bỏ điểm sáng/tối cực đoan)
        p1, p99 = np.percentile(img, (1, 99))
        if p99 - p1 >= 16:                                # ảnh phẳng gần một màu thì đừng khuếch đại nhiễu
            stretched = (img.astype(np.float32) - p1) * (255.0 / (p99 - p1))
            img = np.clip(stretched, 0, 255).astype(np.uint8)
    lo, hi = raster.black_point, raster.white_point
    if hi <= lo:
        hi = lo + 1
    x = (img.astype(np.float32) - lo) / (hi - lo)
    np.clip(x, 0.0, 1.0, out=x)
    if raster.gamma != 1.0:
        np.power(x, 1.0 / raster.gamma, out=x)            # gamma > 1 làm sáng vùng giữa
    if raster.clahe:
        u8 = (x * 255.0 + 0.5).astype(np.uint8)
        u8 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(u8)
        x = u8.astype(np.float32) / 255.0
    d = 1.0 - x
    if style.invert:
        d = 1.0 - d
    return d
