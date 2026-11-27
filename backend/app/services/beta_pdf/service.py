"""Tab Beta: một trang PDF -> các lớp nét (cùng kiểu kết quả với `drawing.raster.build_raster`), nên phần xem trước, bố trí, tạo G-code,
lưu bản thảo của tab Tạo bản vẽ dùng lại được nguyên vẹn.

Dây chuyền (chi tiết và lý do ở docs/10_TAB_BETA_PDF.md):
  đọc trang (reader.py) -> đường kẻ (frame.py) + chữ (text.py) + ảnh (images.py) -> hai lớp -> lưu vào TASKS như một bản vẽ đã nạp.
Lớp 1 = chữ + đường kẻ (bút bi, `pen_mm`), lớp 2 = ảnh (bút tô, `image_pen_mm`). Mỗi lớp một tệp G-code, đổi bút giữa hai tệp.
"""
from __future__ import annotations

import time

from ..drawing import layout
from ..drawing.errors import DrawError
from ..drawing.shapes import Box, Layer
from ..drawing.store import TASKS, Parsed
from ..drawing.svg_in import layer_stats
from . import frame, images, options, text
from .reader import PdfDoc

TEXT_COLOR = "#141414"
IMAGE_COLOR = "#067a4e"


def page_info(data: bytes) -> dict:
    """Số trang và khổ từng trang (mm) để giao diện hiện bộ chọn trang."""
    with PdfDoc(data) as doc:
        sizes = doc.page_sizes()
        return {"pages": doc.page_count, "sizes": [{"w": w, "h": h} for w, h in sizes]}


def page_preview(data: bytes, page: int, dpi: float) -> bytes:
    """PNG của trang gốc để so sánh với nét sinh ra."""
    with PdfDoc(data) as doc:
        return doc.render_png(page - 1, None, dpi)


def build(data: bytes, name: str, raw_options: dict | None, ctx=None):
    """(các lớp, khung, thông tin, cảnh báo) của một trang. Hàm thuần: không đụng bộ nhớ chung."""
    from ..drawing.service import MAX_POINTS
    o = options.parse(raw_options)
    timings: dict[str, float] = {}

    def step(key: str, progress: float, message: str) -> None:
        if ctx:
            ctx.step(key, progress, message)

    t0 = time.perf_counter()
    step("read", 0.05, "Đọc trang PDF")
    with PdfDoc(data) as doc:
        index = o.page - 1
        content = doc.read_page(index)
        timings["read"] = time.perf_counter() - t0
        warnings: list[dict] = []
        if content.stats["page_rotation"]:
            warnings.append({"code": "beta_page_rotated", "count": 1})
        if content.stats["rotated_chars"]:
            warnings.append({"code": "beta_rotated_text", "count": content.stats["rotated_chars"]})
        if content.stats["filled_areas"]:
            warnings.append({"code": "beta_filled_areas", "count": content.stats["filled_areas"]})

        t1 = time.perf_counter()
        step("style", 0.2, "Dựng nét chữ và đường kẻ")
        lines = frame.build(content.segments, o) if o.frame else []
        words, tstats = text.build(content, o, doc, index)
        if tstats["missing"]:
            warnings.append({"code": "beta_missing_chars", "count": tstats["missing"]})
        if tstats["missing_sample"]:
            warnings.append({"code": "beta_fallback_chars", "count": tstats["fallback"], "detail": tstats["missing_sample"]})
        if ctx:
            ctx.check()
        step("style", 0.5, "Tô ảnh trong trang")
        pictures, diagrams, image_warnings = images.build(doc, index, content.images, o) if o.images else ([], [], [])
        warnings += image_warnings
        timings["style"] = time.perf_counter() - t1

    t2 = time.perf_counter()
    step("optimize", 0.8, "Gộp nét")
    if o.lineart_with_text:
        ink = lines + diagrams + words                       # đường kẻ, hình vẽ nét, rồi chữ theo dòng
    else:
        ink = lines + words
        pictures = pictures + diagrams                       # hình vẽ nét thành lớp ảnh riêng
    
    raw: list[tuple[str, str, str, list]] = []
    if ink:
        raw.append(("1", "Chữ và đường kẻ", TEXT_COLOR, ink))
    if pictures:
        raw.append(("2", "Ảnh", IMAGE_COLOR, pictures))
    if not raw:
        raise DrawError("empty_drawing", "Trang không có chữ, đường kẻ hay ảnh để vẽ (trang rỗng, hoặc PDF dạng quét: hãy bật 'Ảnh trong trang').")
    total_points = sum(len(s) for _, _, _, st in raw for s in st)
    if total_points > MAX_POINTS:
        raise DrawError("too_many_points", f"{total_points} điểm, vượt giới hạn {MAX_POINTS}.")
    layers: list[Layer] = []
    metas: list[dict] = []
    for lid, label, color, strokes in raw:
        layer = Layer(f"{lid}-{color[1:]}", strokes)
        layers.append(layer)
        metas.append({"id": layer.id, "name": label, "color": color, **layer_stats([layer])})
    timings["optimize"] = time.perf_counter() - t2

    page = Box(0.0, 0.0, content.width_mm, content.height_mm)
    b = layout.content_bounds(layers)
    stats = layer_stats(layers)
    timings["total"] = sum(timings.values())
    info = {
        "mode": "beta_pdf", "name": name, "page": o.page,
        "page_mm": {"w": round(content.width_mm, 2), "h": round(content.height_mm, 2)},
        "frame": "page",
        "bounds": {"x": b.x, "y": b.y, "w": b.w, "h": b.h},
        "layers": metas,
        "optimize": {"before": stats, "after": stats, "pipeline": []},
        "beta": {"text": tstats, "frame_strokes": len(lines), "image_boxes": len(content.images), "image_strokes": len(pictures), "diagram_strokes": len(diagrams),
                 "mode": o.text_mode, "pdf": content.stats},
        "timings": {k: round(v, 3) for k, v in timings.items()},
    }
    return layers, page, info, warnings


def import_page(data: bytes, name: str, raw_options: dict | None, token: str | None = None, ctx=None) -> dict:
    """Chạy `build` rồi đặt kết quả vào bộ nhớ tạm bản vẽ (như `raster.import_raster`). Trả {task, source, warnings}."""
    layers, page, info, warnings = build(data, name, raw_options, ctx)
    token = TASKS.put(Parsed(layers, page, info), token)
    return {"task": token, "source": info, "warnings": warnings}
