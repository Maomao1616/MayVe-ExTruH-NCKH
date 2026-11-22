"""Chỉnh sắc độ: ảnh xám uint8 -> bản đồ độ đậm float32 0..1 (1 = đen nhất, cần nhiều mực nhất).

Thứ tự (sau khi đã thu nhỏ): khử nhiễu -> tự cân sáng -> mức đen/trắng + gamma -> tương phản -> CLAHE -> làm nét -> đảo.
"""
from __future__ import annotations

import json

import cv2
import numpy as np

cv2.setNumThreads(2)             # chừa CPU cho việc điều khiển máy


SHARPEN_SIGMA_MM = 1.5          # làm nét cục bộ: trừ bản mờ Gauss cỡ này (mm; ~4 điểm ảnh ở A4 bút 0,5). Thử 18/11/2026 ảnh bưu điện A4: hệ số 1,5 làm rõ
                                 # vòm, cột, vòng đồng hồ mà không thêm nét (314 -> 328 nét); thêm lớp viền thì nguệch ngoạc, tương phản 1,8 mất tông giữa
SHARPEN_SIGMA_PX = 4.0           # dùng khi không biết cỡ điểm ảnh (test)


def darkness(gray: np.ndarray, raster, style, ctx=None, px_mm: float | None = None) -> np.ndarray:
    """`raster` = nhóm tham số raster, `style` = nhóm kiểu tô (chỉ dùng `invert`). `px_mm` = cỡ một điểm ảnh (mm), cho làm nét."""
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
    if raster.sharpen > 0:                                # unsharp mask: x + hệ số × (x − bản mờ), cắt 0..1
        sigma = SHARPEN_SIGMA_MM / px_mm if px_mm else SHARPEN_SIGMA_PX
        x = np.clip(x + raster.sharpen * (x - cv2.GaussianBlur(x, (0, 0), max(sigma, 0.5))), 0.0, 1.0).astype(np.float32)
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


# Tự tách chủ thể (22/11/2026): GrabCut của OpenCV (không cần thư viện thêm) trên bản thu nhỏ, khởi tạo bằng khung gần cả ảnh.
# Chủ thể = người / vật ở giữa, nền = phần còn lại. Mặt nạ làm mịn mép rồi dùng như trọng số của vùng elip / chữ nhật.
AUTO_SUBJECT_SIDE = 320          # cạnh dài của bản thu nhỏ đưa vào GrabCut (px); ~1 s mỗi ảnh
AUTO_SUBJECT_MARGIN = 0.04       # khung khởi tạo chừa lề 4 % mỗi phía: ngoài khung chắc chắn là nền
AUTO_SUBJECT_ITERS = 5           # số vòng GrabCut
AUTO_SUBJECT_FEATHER = 0.012     # độ mờ mép (sigma) theo cạnh dài: tránh lộ vòng cắt
AUTO_SUBJECT_MIN = 0.05          # chủ thể < 5 % hoặc > 92 % ảnh coi như tách thất bại (không đổi gì)
AUTO_SUBJECT_MAX = 0.92


def auto_subject_weight(rgb: np.ndarray, h: int, w: int) -> np.ndarray | None:
    """Trọng số 0..1 (1 = chủ thể) cỡ (h, w) từ ảnh màu RGB đã cắt; None nếu tách không ra kết quả hợp lý."""
    sh, sw = rgb.shape[:2]
    scale = AUTO_SUBJECT_SIDE / max(sh, sw)
    small = cv2.resize(np.ascontiguousarray(rgb[:, :, ::-1]), (max(8, round(sw * scale)), max(8, round(sh * scale))),
                       interpolation=cv2.INTER_AREA)
    th, tw = small.shape[:2]
    mx, my = int(tw * AUTO_SUBJECT_MARGIN), int(th * AUTO_SUBJECT_MARGIN)
    rect = (mx, my, tw - 2 * mx, th - 2 * my)
    mask = np.zeros((th, tw), np.uint8)
    cv2.setRNGSeed(1)                                          # k-means trong GrabCut: cố định để kết quả lặp lại
    try:
        cv2.grabCut(small, mask, rect, np.zeros((1, 65)), np.zeros((1, 65)), AUTO_SUBJECT_ITERS, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg = cv2.morphologyEx(cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel), cv2.MORPH_CLOSE, kernel)   # bỏ đốm, lấp lỗ nhỏ
    share = float((fg > 0).mean())
    if not AUTO_SUBJECT_MIN <= share <= AUTO_SUBJECT_MAX:
        return None
    soft = cv2.GaussianBlur(fg.astype(np.float32) / 255.0, (0, 0), AUTO_SUBJECT_FEATHER * max(th, tw))
    return np.clip(cv2.resize(soft, (w, h), interpolation=cv2.INTER_LINEAR), 0.0, 1.0).astype(np.float32)


# Vùng chủ thể VẼ TAY (22/11/2026): chủ dự án tô quanh người / vật trên ảnh gốc, tô bớt để loại chỗ thừa. Gửi lên là các đa giác
# (tọa độ 0..1 của ảnh GỐC) nên nhẹ; backend tô thành mặt nạ, làm mịn mép rồi dùng như trọng số.
SUBJECT_FREE_MAX_SHAPES = 60     # số nét vẽ tối đa mỗi loại (thêm / bớt)
SUBJECT_FREE_MAX_POINTS = 800    # số điểm tối đa mỗi nét
SUBJECT_FREE_FEATHER = 0.01      # độ mờ mép (sigma) theo cạnh dài ảnh
SUBJECT_FREE_MIN_SHARE = 0.0005  # mặt nạ nhỏ hơn mức này (0,05 % ảnh) coi như chưa vẽ gì


def free_subject_weight(text: str, crop: tuple[float, float, float, float], h: int, w: int) -> np.ndarray | None:
    """Trọng số 0..1 cỡ (h, w) từ các đa giác vẽ tay `text` (JSON); None nếu không đọc được hoặc chưa tô gì trong vùng đã cắt."""
    try:
        data = json.loads(text or "")
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("add"), list):
        return None
    cx, cy, cw, ch = crop
    mask = np.zeros((h, w), np.uint8)

    def draw(shapes, value: int) -> None:
        for pts in (shapes if isinstance(shapes, list) else [])[:SUBJECT_FREE_MAX_SHAPES]:
            try:
                arr = np.asarray(pts[:SUBJECT_FREE_MAX_POINTS], np.float32)
            except (TypeError, ValueError):
                continue
            if arr.ndim != 2 or arr.shape[0] < 3 or arr.shape[1] != 2 or not np.isfinite(arr).all():
                continue
            xy = np.empty_like(arr)
            xy[:, 0] = (arr[:, 0] - cx) / cw * w
            xy[:, 1] = (arr[:, 1] - cy) / ch * h
            cv2.fillPoly(mask, [np.clip(np.round(xy), -1e6, 1e6).astype(np.int32)], value)

    draw(data["add"], 255)
    draw(data.get("sub"), 0)                                   # tô bớt vẽ sau cùng: luôn thắng
    if float((mask > 0).mean()) < SUBJECT_FREE_MIN_SHARE:
        return None
    soft = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), SUBJECT_FREE_FEATHER * max(h, w))
    return np.clip(soft, 0.0, 1.0).astype(np.float32)


def apply_subject(dark: np.ndarray, raster, rgb: np.ndarray | None = None, warnings: list | None = None) -> np.ndarray:
    """Làm nhạt ngoài vùng chủ thể: độ đậm × (ngoài + (1 − ngoài) × trọng số). Không chọn hình thì giữ nguyên.
    Hình "auto" tự tách chủ thể từ ảnh màu `rgb`; tách không ra thì giữ nguyên và ghi cảnh báo."""
    if raster.subject_shape == "none" or raster.subject_outside >= 1.0:
        return dark
    if raster.subject_shape == "auto":
        weight = auto_subject_weight(rgb, dark.shape[0], dark.shape[1]) if rgb is not None else None
        if weight is None:
            if warnings is not None:
                warnings.append({"code": "subject_auto_failed", "count": 1})
            return dark
        out = raster.subject_outside
        return (dark * (out + (1.0 - out) * weight)).astype(np.float32)
    crop = (raster.crop_x, raster.crop_y, raster.crop_w, raster.crop_h)
    if raster.subject_shape == "free":
        weight = free_subject_weight(raster.subject_poly, crop, dark.shape[0], dark.shape[1])
        if weight is None:
            if warnings is not None:
                warnings.append({"code": "subject_free_invalid", "count": 1})
            return dark
        out = raster.subject_outside
        return (dark * (out + (1.0 - out) * weight)).astype(np.float32)
    rect = (raster.subject_x, raster.subject_y, raster.subject_w, raster.subject_h)
    weight = subject_weight(raster.subject_shape, rect, crop, dark.shape[0], dark.shape[1])
    out = raster.subject_outside
    return (dark * (out + (1.0 - out) * weight)).astype(np.float32)
