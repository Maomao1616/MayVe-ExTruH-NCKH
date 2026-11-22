"""Ảnh nằm trong trang PDF -> nét vẽ. Mỗi khung ảnh được nhận diện rồi đi một trong hai đường:

* ẢNH CHỤP / ảnh nhiều tông (`photo`): dùng lại NGUYÊN đường tô ảnh của tab Tạo bản vẽ (`drawing.raster.build_raster`): cắt từ trang ở
  `image_dpi`, tô theo kiểu đã chọn (Đan chéo, Đường dòng, Sóng…) trong đúng khung, rồi tịnh tiến về vị trí trên trang. Thành lớp ảnh
  (bút tô riêng, vd Sakura 0,4) nên ra tệp G-code riêng.
* HÌNH VẼ NÉT (`lineart`: sơ đồ khối, mạch điện, đồ thị, công thức dạng ảnh; nền trắng, nét đen mảnh): kiểu tô đan chéo hầu như không vẽ
  được gì vì ảnh quá sáng (đã gặp trên PDF thật 22/11/2026: cả sơ đồ chỉ ra 2 nét). Nên lấy đường giữa nét như chữ: kết xuất khung ở
  `skeleton_dpi` -> nhị phân -> skeleton -> dò nét (`text.skeleton_strokes`). Mặc định cùng bút và cùng tệp G-code với chữ.
Nhận diện (`classify`): ≥ 70 % điểm ảnh gần trắng và ≤ 20 % điểm xám trung gian là hình vẽ nét, còn lại là ảnh chụp (ảnh chụp thường có nhiều xám trung gian).
Giới hạn: chạy ngay trong tiến trình hiện tại (không tách tiến trình con như tab Tạo bản vẽ), nên giữ `image_dpi` ≤ 300 và ảnh nhỏ.
"""
from __future__ import annotations

from ..drawing import raster
from ..drawing.errors import DrawError
from . import pathing, text

MIN_SIDE_MM = 3.0                # khung ảnh nhỏ hơn mức này (mm) bỏ qua (biểu tượng nhỏ, đường kẻ dạng ảnh)
PROBE_DPI = 100                  # độ phân giải thử để nhận diện hình vẽ nét / ảnh chụp
LINEART_BLUR_MM = 0.25           # làm mịn Gauss trước khi lấy đường giữa nét (ảnh nhúng trong PDF thường mờ, có răng cưa); đo: 156 -> 115 nét trên sơ đồ khối, nét sạch hơn;
                                 # 0,45 mm trở lên làm mất nét mảnh
LINEART_WHITE = 0.70             # ≥ mức này điểm ảnh gần trắng (> 200) ...
LINEART_MID = 0.20               # ... và ≤ mức này điểm ảnh xám trung gian (64..192) thì là hình vẽ nét (đo trên PDF thật: sơ đồ 0,82–0,96 / 0,03–0,11; ký hiệu Hy Lạp lưu dạng ảnh 6 mm 0,75–0,84 / 0,11–0,16)
WHITE_LEVEL = 200
MID_LO, MID_HI = 64, 192


def classify(gray) -> str:
    """"lineart" nếu ảnh xám (numpy 2-D) là nét mảnh trên nền trắng, ngược lại "photo"."""
    if gray.size == 0:
        return "photo"
    white = float((gray > WHITE_LEVEL).mean())
    mid = float(((gray >= MID_LO) & (gray <= MID_HI)).mean())
    return "lineart" if white >= LINEART_WHITE and mid <= LINEART_MID else "photo"


def build(doc, page_index: int, boxes, o):
    """(nét ảnh chụp, nét hình vẽ nét, cảnh báo) trong tọa độ trang."""
    photos: list = []
    lines: list = []
    warnings: list = []
    for box in boxes:
        w, h = box.x1 - box.x0, box.y1 - box.y0
        if w < MIN_SIDE_MM or h < MIN_SIDE_MM:
            continue
        bbox = (box.x0, box.y0, box.x1, box.y1)
        kind = o.image_kind
        if kind == "auto":
            kind = classify(doc.render_gray(page_index, bbox, PROBE_DPI))
        if kind == "lineart":
            found = text.skeleton_strokes(doc, page_index, bbox, o.skeleton_dpi, o.skeleton_threshold, LINEART_BLUR_MM)
            if found:
                lines += pathing.order_nearest(found, (box.x0, box.y0))
            else:
                warnings.append({"code": "beta_image_skipped", "count": 1, "detail": "empty"})
            continue
        style = "crosshatch" if kind == "photo" else kind               # auto đã quyết "photo": dùng Đan chéo
        opts = {
            "raster": {"pen_width_mm": o.image_pen_mm},
            "style": {"kind": style},
            "layout": {"paper": "custom", "paper_width_mm": w, "paper_height_mm": h, "margin_mm": 0.0, "width_mm": w, "height_mm": h},
        }
        try:
            png = doc.render_png(page_index, bbox, o.image_dpi)
            layers, frame, _info, _warn = raster.build_raster(png, "beta-image", opts, None)
        except DrawError as exc:                              # ảnh trống / quá sáng: bỏ ảnh đó, vẫn vẽ phần còn lại
            warnings.append({"code": "beta_image_skipped", "count": 1, "detail": exc.code})
            continue
        sx, sy = w / frame.w, h / frame.h
        for layer in layers:
            for s in layer.strokes:
                photos.append([(box.x0 + x * sx, box.y0 + y * sy) for x, y in s])
    return photos, lines, warnings
