"""Chỉnh sắc độ: ảnh xám uint8 -> bản đồ độ đậm float32 0..1 (1 = đen nhất, cần nhiều mực nhất).

Thứ tự (sau khi đã thu nhỏ): khử nhiễu -> tự cân sáng -> mức đen/trắng + gamma -> tương phản -> CLAHE -> đảo.
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
    if raster.contrast != 1.0:                            # kéo giãn quanh xám giữa 0,5: sáng sáng thêm, tối tối thêm (cắt ở 0 / 1)
        x = np.clip((x - 0.5) * raster.contrast + 0.5, 0.0, 1.0, out=x)
    if raster.clahe:
        u8 = (x * 255.0 + 0.5).astype(np.uint8)
        u8 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(u8)
        x = u8.astype(np.float32) / 255.0
    d = 1.0 - x
    if style.invert:
        d = 1.0 - d
    return d


SUBJECT_FEATHER = 0.08           # mép vùng chủ thể mờ dần: rộng ± 8 % bán kính (nền không bị cắt thành đường cứng)


def subject_weight(shape: str, rect: tuple[float, float, float, float], crop: tuple[float, float, float, float],
                   h: int, w: int) -> np.ndarray:
    """Trọng số 0..1 (1 = trong vùng chủ thể) cho ảnh đã cắt cỡ (h, w). `rect` và `crop` = (x, y, w, h) tỷ lệ 0..1 của ảnh GỐC;
    vùng chủ thể đổi sang tọa độ của phần đã cắt. Elip: khoảng cách chuẩn hóa tới tâm; chữ nhật: khoảng cách Chebyshev."""
    sx, sy, sw, sh = rect
    cx, cy, cw, ch = crop
    # tâm và nửa cạnh của vùng chủ thể, tính theo phần đã cắt (0..1)
    mx = ((sx + sw / 2) - cx) / cw
    my = ((sy + sh / 2) - cy) / ch
    rx = max(1e-6, sw / 2 / cw)
    ry = max(1e-6, sh / 2 / ch)
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w
    ys = (np.arange(h, dtype=np.float32) + 0.5) / h
    dx = np.abs(xs - mx)[None, :] / rx
    dy = np.abs(ys - my)[:, None] / ry
    r = np.sqrt(dx * dx + dy * dy) if shape == "ellipse" else np.maximum(dx, dy)
    return np.clip((1.0 + SUBJECT_FEATHER - r) / (2.0 * SUBJECT_FEATHER), 0.0, 1.0).astype(np.float32)


def apply_subject(dark: np.ndarray, raster) -> np.ndarray:
    """Làm nhạt ngoài vùng chủ thể: độ đậm × (ngoài + (1 − ngoài) × trọng số). Không chọn hình thì giữ nguyên."""
    if raster.subject_shape == "none" or raster.subject_outside >= 1.0:
        return dark
    rect = (raster.subject_x, raster.subject_y, raster.subject_w, raster.subject_h)
    crop = (raster.crop_x, raster.crop_y, raster.crop_w, raster.crop_h)
    weight = subject_weight(raster.subject_shape, rect, crop, dark.shape[0], dark.shape[1])
    out = raster.subject_outside
    return (dark * (out + (1.0 - out) * weight)).astype(np.float32)
