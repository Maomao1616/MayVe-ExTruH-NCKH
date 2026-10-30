"""Nạp SVG (nhiều lớp) bằng vpype -> các lớp đường nét tính bằng mm.

vpype dùng đơn vị px CSS (96 px = 1 inch); ta đổi sang mm ngay khi xuất ra, phần còn lại của dây chuyền chỉ biết mm.
Tách riêng `document_to_layers` (thuần, dùng được với đối tượng giả) để test không cần vpype.
"""
from __future__ import annotations

import io
import math

import numpy as np

from . import optimize, spec
from .errors import DrawError
from .layout import content_bounds
from .shapes import Box, Layer
from .store import TASKS, Parsed

MM_PER_PX = 25.4 / 96
PX_PER_MM = 96 / 25.4
MAX_SVG_BYTES = 20 * 1024 * 1024


def read_svg(data: bytes, quantization_mm: float):
    if len(data) > MAX_SVG_BYTES:
        raise DrawError("file_too_large", f"Tệp SVG lớn hơn {MAX_SVG_BYTES // (1024 * 1024)} MB.", 413)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise DrawError("bad_svg", "SVG phải mã hóa UTF-8.") from None
    if "<svg" not in text:
        raise DrawError("bad_svg", "Tệp không phải SVG.")
    if "<!ENTITY" in text:                      # chặn tấn công mở rộng thực thể XML
        raise DrawError("bad_svg", "SVG có khai báo ENTITY, bị từ chối.")
    import vpype
    try:
        return vpype.read_multilayer_svg(io.StringIO(text), quantization_mm * PX_PER_MM)
    except Exception as exc:
        raise DrawError("bad_svg", f"Không đọc được SVG: {exc}") from exc


def _prop(lc, key_name: str):
    try:
        import vpype
        key = getattr(vpype, key_name)
        if not lc.property_exists(key):
            return None
        v = lc.property(key)
        return getattr(v, "as_hex", lambda: str(v))() if v is not None else None
    except Exception:
        return None


def document_to_layers(doc) -> tuple[list[Layer], list[dict]]:
    """Document (px) -> (lớp, thông tin lớp). Bỏ lớp rỗng và đoạn < 2 điểm."""
    layers: list[Layer] = []
    meta: list[dict] = []
    for lid in sorted(doc.layers):
        lc = doc.layers[lid]
        strokes = []
        for line in lc.lines:
            arr = np.asarray(line)
            if arr.size < 2:
                continue
            xy = np.column_stack((arr.real, arr.imag)) * MM_PER_PX
            strokes.append([(x, y) for x, y in xy.tolist()])
        if strokes:
            layers.append(Layer(str(lid), strokes))
            meta.append({"id": str(lid), "name": _prop(lc, "METADATA_FIELD_NAME"),
                         "color": _prop(lc, "METADATA_FIELD_COLOR")})
    return layers, meta


def layer_stats(layers: list[Layer]) -> dict:
    strokes = points = 0
    draw = pen_up = 0.0
    for layer in layers:
        prev = None
        for s in layer.strokes:
            strokes += 1
            points += len(s)
            for a, b in zip(s, s[1:]):
                draw += math.dist(a, b)
            if prev is not None:
                pen_up += math.dist(prev, s[0])
            prev = s[-1]
    return {"strokes": strokes, "points": points, "draw_mm": round(draw, 2), "pen_up_mm": round(pen_up, 2)}


def _page_mm(doc) -> tuple[float, float] | None:
    ps = getattr(doc, "page_size", None)
    if ps and len(ps) == 2 and ps[0] > 0 and ps[1] > 0:
        return ps[0] * MM_PER_PX, ps[1] * MM_PER_PX
    return None


def import_svg(data: bytes, svg_raw=None, optimize_raw=None, token: str | None = None, ctx=None) -> dict:
    from .service import MAX_POINTS
    sp = spec.parse("svg", svg_raw)
    op = spec.parse("optimize", optimize_raw)

    if ctx:
        ctx.step("read", 0.1, "Đọc SVG")
    doc = read_svg(data, sp.quantization_mm)
    page = _page_mm(doc)
    first, _ = document_to_layers(doc)
    if not first:
        raise DrawError("empty_drawing", "SVG không có đường nét (chữ cần chuyển thành path trước).")
    before = layer_stats(first)
    del first
    if before["points"] > MAX_POINTS:
        raise DrawError("too_many_points", f"{before['points']} điểm, vượt giới hạn {MAX_POINTS}.")

    if ctx:
        ctx.step("optimize", 0.5, "Tối ưu nét")
    doc = optimize.run(doc, op)
    layers, meta = document_to_layers(doc)
    if not layers:
        raise DrawError("empty_drawing", "Sau khi tối ưu không còn nét nào (thử giảm 'bỏ nét ngắn').")
    after = layer_stats(layers)

    warnings: list[dict] = []
    frame = None
    if sp.frame == "page":
        if page:
            frame = Box(0.0, 0.0, page[0], page[1])
        else:
            warnings.append({"code": "no_page_size", "count": 1})
    b = content_bounds(layers)
    info = {
        "page_mm": {"w": page[0], "h": page[1]} if page else None,
        "frame": "page" if frame else "content",
        "bounds": {"x": b.x, "y": b.y, "w": b.w, "h": b.h},
        "layers": [dict(m, **layer_stats([l])) for m, l in zip(meta, layers)],
        "optimize": {"before": before, "after": after, "pipeline": optimize.build_pipeline(op, before["strokes"])},
    }
    token = TASKS.put(Parsed(layers, frame, info), token)
    return {"task": token, "source": info, "warnings": warnings}
