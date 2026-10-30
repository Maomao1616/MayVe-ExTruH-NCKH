"""Nạp ảnh raster -> ảnh xám ở độ phân giải làm việc + kích thước thật (mm).

Thứ tự đã chốt (docs/DRAW_ROADMAP.md): EXIF + Image.draft -> cắt -> thu nhỏ -> xám.
Ảnh lớn thì thu nhỏ về độ phân giải cần cho bút. Ảnh nhỏ chỉ được phóng nhẹ (nội suy mịn) tới
UPSCALE_TO_PX cạnh dài để đường viền các vùng đậm nhạt không bị ô vuông; không bao giờ phóng quá mức đó
(thêm điểm ảnh không thêm chi tiết). Hộp tham chiếu (kích thước khung vẽ thật) chỉ để tính độ phân giải.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

from .errors import DrawError

MAX_PIXELS = 60_000_000          # chặn ảnh khổng lồ (bom giải nén) trước khi giải mã
OVERSAMPLE = 1.3                 # số điểm ảnh trên mỗi bề rộng bút
MIN_SIDE_PX, MAX_SIDE_PX = 400, 4000
DRAFT_FACTOR = 0.5               # bản nháp dùng nửa độ phân giải
UPSCALE_TO_PX = 720              # ảnh nhỏ được phóng nhẹ tới chừng này (cạnh dài), không hơn

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


@dataclass(frozen=True)
class Raster:
    gray: np.ndarray             # uint8, (h, w), 0 = đen
    width_mm: float              # kích thước thật của ảnh trong bản vẽ
    height_mm: float
    source_px: tuple[int, int]   # kích thước ảnh gốc sau khi cắt (w, h)
    rgb: np.ndarray | None = None   # uint8 (h, w, 3), chỉ có khi load(color=True)

    @property
    def mm_per_px(self) -> float:
        return self.width_mm / self.gray.shape[1]


def work_side_px(ref_long_mm: float, pen_mm: float, quality: str, override: int | None, cap: int) -> int:
    """Cạnh dài (điểm ảnh) cần xử lý: khung ÷ bút × 1,3, không vượt `cap`."""
    if override:
        side = override
    else:
        side = ref_long_mm / pen_mm * OVERSAMPLE * (DRAFT_FACTOR if quality == "draft" else 1.0)
        side = max(MIN_SIDE_PX, min(MAX_SIDE_PX, side))
    return int(max(2, min(cap, side)))


def load(data: bytes, p, ref_w_mm: float, ref_h_mm: float, ctx=None, color: bool = False) -> Raster:
    """`p` = tham số nhóm raster; (ref_w_mm, ref_h_mm) = hộp tham chiếu mà ảnh phải nằm gọn trong."""
    try:
        im = Image.open(io.BytesIO(data))
        w0, h0 = im.size
    except Image.DecompressionBombError:
        raise DrawError("bad_image", "Ảnh có quá nhiều điểm ảnh (> 60 triệu).", 413) from None
    except Exception:
        raise DrawError("bad_image", "Không đọc được ảnh (tệp hỏng hoặc sai định dạng).") from None
    if w0 < 2 or h0 < 2:
        raise DrawError("bad_image", "Ảnh quá nhỏ.")
    if ctx:
        ctx.check()

    # kích thước vùng cắt (tỷ lệ 0..1 của ảnh gốc, tính sau khi xoay EXIF -> nên xoay trước)
    try:
        orientation = im.getexif().get(0x0112, 1)
    except Exception:
        orientation = 1
    swap = orientation in (5, 6, 7, 8)
    cw_frac, ch_frac = p.crop_w, p.crop_h
    cx_frac, cy_frac = p.crop_x, p.crop_y
    cx_frac = min(cx_frac, 1 - 0.01); cy_frac = min(cy_frac, 1 - 0.01)
    cw_frac = min(cw_frac, 1 - cx_frac); ch_frac = min(ch_frac, 1 - cy_frac)
    ow, oh = (h0, w0) if swap else (w0, h0)
    crop_px_w, crop_px_h = max(2, round(ow * cw_frac)), max(2, round(oh * ch_frac))

    # hộp mm: ảnh đã cắt đặt gọn trong hộp tham chiếu, giữ tỷ lệ
    s = min(ref_w_mm / crop_px_w, ref_h_mm / crop_px_h)
    width_mm, height_mm = crop_px_w * s, crop_px_h * s
    side = work_side_px(max(width_mm, height_mm), p.pen_width_mm, p.quality, p.max_side_px,
                        max(crop_px_w, crop_px_h, UPSCALE_TO_PX))

    try:
        if im.format == "JPEG":                           # giải mã nhỏ ngay từ đầu, rẻ RAM
            full_long = max(crop_px_w, crop_px_h)
            ratio = side / full_long
            im.draft("RGB", (max(2, int(w0 * ratio)) if ratio < 1 else w0,
                             max(2, int(h0 * ratio)) if ratio < 1 else h0))
        im.load()
        im = ImageOps.exif_transpose(im)
    except Image.DecompressionBombError:
        raise DrawError("bad_image", "Ảnh có quá nhiều điểm ảnh (> 60 triệu).", 413) from None
    except Exception:
        raise DrawError("bad_image", "Không đọc được ảnh (tệp hỏng hoặc sai định dạng).") from None
    if ctx:
        ctx.check()

    if im.mode in ("RGBA", "LA", "P"):                    # nền trong suốt -> trắng
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB" if color else "L")

    W, H = im.size                                        # có thể nhỏ hơn bản gốc nếu draft
    box = (round(W * cx_frac), round(H * cy_frac),
           min(W, round(W * (cx_frac + cw_frac))), min(H, round(H * (cy_frac + ch_frac))))
    if box[2] - box[0] >= 2 and box[3] - box[1] >= 2:
        im = im.crop(box)
    w, h = im.size
    long_side = max(w, h)
    if long_side != side:                                 # thu nhỏ (trung bình vùng) hoặc phóng nhẹ (bicubic)
        k = side / long_side
        method = (Image.Resampling.BICUBIC if k > 1 else
                  Image.Resampling.BOX if k < 0.5 else Image.Resampling.LANCZOS)
        im = im.resize((max(2, round(w * k)), max(2, round(h * k))), method)
    if color:
        return Raster(np.asarray(im.convert("L"), dtype=np.uint8), width_mm, height_mm, (crop_px_w, crop_px_h),
                      np.asarray(im, dtype=np.uint8))
    return Raster(np.asarray(im, dtype=np.uint8), width_mm, height_mm, (crop_px_w, crop_px_h))
