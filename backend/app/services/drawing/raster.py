"""Dây chuyền ảnh raster -> đường nét: đọc -> chỉnh sắc độ -> tô nét -> tối ưu vpype.

Khổ giấy chỉ dùng làm hộp tham chiếu (phần trong lề) để tính độ phân giải và khoảng cách nét theo mm;
bản vẽ sinh ra có kích thước tự nhiên của ảnh trong hộp đó, còn phóng to / thu nhỏ do layout lo.
"""
from __future__ import annotations

from . import optimize, palette, raster_in, spec, styles, tone
from .errors import DrawError
from .hatch import Field
from .layout import content_bounds, paper_size
from .shapes import Box, Layer
from .store import TASKS, Parsed
from .svg_in import document_to_layers, layer_stats


def reference_box(layout_raw) -> tuple[float, float]:
    """Hộp (mm) mà ảnh phải nằm gọn: khung vẽ thật nếu frontend gửi width_mm/height_mm (cạnh theo hướng
    ảnh gốc, chưa xoay), không thì phần trong lề của tờ giấy. Nhờ vậy khoảng cách nét luôn tính theo
    kích thước thật trên giấy, không bị giãn khi người dùng kéo khung."""
    lp = spec.parse("layout", layout_raw)
    pw, ph = paper_size(lp)
    w, h = pw - 2 * lp.margin_mm, ph - 2 * lp.margin_mm
    if w <= 0 or h <= 0:
        raise DrawError("bad_param", f"layout: lề {lp.margin_mm:g} mm quá lớn so với tờ giấy {pw:g}x{ph:g} mm")
    if lp.width_mm is not None and lp.height_mm is not None:
        return lp.width_mm, lp.height_mm
    return w, h


def import_raster(data: bytes, name: str, opts: dict, token: str | None = None, ctx=None) -> dict:
    from .service import MAX_POINTS
    rp = spec.parse("raster", opts.get("raster"))
    sp = spec.parse("style", opts.get("style"))
    op = spec.parse("optimize", opts.get("optimize"))
    pp = spec.parse("palette", opts.get("palette"))
    ref_w, ref_h = reference_box(opts.get("layout"))
    if sp.kind not in styles.FILLERS.names():
        raise DrawError("unsupported_style", f"Kiểu tô '{sp.kind}' chưa có.")

    def step(key: str, progress: float, message: str) -> None:
        if ctx:
            ctx.step(key, progress, message)

    warnings: list[dict] = []
    multi = pp.mode == "multi"
    if multi and sp.kind == "outline":                       # viền đơn sắc: không chia màu
        multi = False
        warnings.append({"code": "palette_ignored", "count": 1})

    step("read", 0.05, "Đọc ảnh")
    img = raster_in.load(data, rp, ref_w, ref_h, ctx, color=multi)
    step("tone", 0.2, "Chỉnh sắc độ")
    dark = tone.darkness(img.gray, rp, sp, ctx)
    step("style", 0.3, "Tạo nét")
    field = Field(dark, img.width_mm, img.height_mm)
    colors: dict[str, str] = {}
    raw_layers: list[Layer] = []
    if multi:
        regions = palette.split(img.rgb, pp.colors, pp.skip_background, ctx)
        for i, region in enumerate(regions):
            step("style", 0.3 + 0.4 * i / max(1, len(regions)), f"Tạo nét màu {i + 1}/{len(regions)}")
            f = Field(palette.density(dark, region), img.width_mm, img.height_mm)
            angle = (sp.angle + i * 180.0 / len(regions)) % 180.0       # mỗi màu một góc để dễ phân biệt
            strokes = styles.fill(f, sp, rp.pen_width_mm, ctx, angle, overlay=False)
            if strokes:
                raw_layers.append(Layer(str(len(raw_layers) + 1), strokes))
                colors[raw_layers[-1].id] = region.color
        if raw_layers and sp.outline_overlay:                         # viền vẽ bằng bút đậm nhất (lớp 1)
            raw_layers[0].strokes += styles.outline(field, sp, rp.pen_width_mm, ctx)
    else:
        strokes = styles.fill(field, sp, rp.pen_width_mm, ctx)
        if strokes:
            raw_layers.append(Layer("1", strokes))
    del dark, field
    if not raw_layers:
        raise DrawError("empty_drawing", "Không có vùng nào đủ đậm để vẽ (ảnh quá sáng — thử hạ mức trắng hoặc tăng gamma).")
    before = layer_stats(raw_layers)
    if before["points"] > MAX_POINTS:
        raise DrawError("too_many_points", f"{before['points']} điểm, vượt giới hạn {MAX_POINTS} (tăng khoảng cách nét).")

    step("optimize", 0.7, "Tối ưu nét")
    doc = optimize.run(optimize.layers_to_document(raw_layers), op)
    layers, meta = document_to_layers(doc)
    if not layers:
        raise DrawError("empty_drawing", "Sau khi tối ưu không còn nét nào (thử giảm 'bỏ nét ngắn').")
    for layer, m in zip(layers, meta):                        # mã màu nằm ngay trong tên lớp -> tên tệp G-code
        hexcolor = colors.get(layer.id)
        layer.id = m["id"] = f"{layer.id}-{hexcolor[1:]}" if hexcolor else layer.id
        colors[layer.id] = hexcolor
    if ctx:
        ctx.check()

    frame = Box(0.0, 0.0, img.width_mm, img.height_mm)       # cả tấm ảnh, giữ phần trắng ở rìa
    b = content_bounds(layers)
    info = {
        "mode": "raster", "name": name,
        "image_px": {"w": img.source_px[0], "h": img.source_px[1]},
        "work_px": {"w": int(img.gray.shape[1]), "h": int(img.gray.shape[0])},
        "frame": "page",
        "page_mm": {"w": img.width_mm, "h": img.height_mm},
        "bounds": {"x": b.x, "y": b.y, "w": b.w, "h": b.h},
        "layers": [dict(m, color=colors.get(l.id), **layer_stats([l])) for m, l in zip(meta, layers)],
        "optimize": {"before": before, "after": layer_stats(layers),
                     "pipeline": optimize.build_pipeline(op, before["strokes"])},
    }
    token = TASKS.put(Parsed(layers, frame, info), token)
    return {"task": token, "source": info, "warnings": warnings}
