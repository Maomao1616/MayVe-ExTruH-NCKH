"""Ghép các bước: kiểm tra tham số -> bố trí -> G-code (mỗi lớp một tệp) -> kiểm bằng chính bộ làm sạch
của JobRunner. Thuần Python (không FastAPI) để test được độc lập."""
from __future__ import annotations

import math
from typing import Any, Mapping

from ..job import JobError, clean_gcode
from . import gcode as gc, layout as lo, spec
from .errors import DrawError
from .types import Box, Layer

MAX_POINTS = 2_000_000       # chặn đầu vào quá lớn (bảo vệ RAM máy yếu)


def _check_layers(layers: list[Layer]) -> None:
    if not layers:
        raise DrawError("empty_drawing", "Chưa có lớp nào.")
    seen: set[str] = set()
    total = 0
    for layer in layers:
        if not layer.id or len(layer.id) > 40 or layer.id in seen:
            raise DrawError("bad_param", f"layers: id lớp rỗng, quá dài hoặc trùng ('{layer.id}')")
        seen.add(layer.id)
        for s in layer.strokes:
            total += len(s)
            for x, y in s:
                if not (math.isfinite(x) and math.isfinite(y)):
                    raise DrawError("bad_param", "layers: tọa độ không hữu hạn")
    if total > MAX_POINTS:
        raise DrawError("too_many_points", f"{total} điểm, vượt giới hạn {MAX_POINTS}.")


def make_gcode(layers: list[Layer], machine_raw: Mapping[str, Any] | None,
               layout_raw: Mapping[str, Any] | None = None, gcode_raw: Mapping[str, Any] | None = None,
               source_bounds: tuple[float, float, float, float] | None = None) -> dict:
    machine = spec.parse("machine", machine_raw)
    layout = spec.parse("layout", layout_raw)
    gp = spec.parse("gcode", gcode_raw)

    if gp.pen_up_z == gp.pen_down_z:
        raise DrawError("bad_param", "gcode: pen_up_z và pen_down_z không được bằng nhau")
    for name in ("pen_up_z", "pen_down_z"):
        if getattr(gp, name) > machine.z_travel:
            raise DrawError("bad_param", f"gcode.{name}: vượt hành trình Z ({machine.z_travel:g} mm)")

    _check_layers(layers)
    if source_bounds is not None:
        x0, y0, x1, y1 = source_bounds
        src = Box(x0, y0, x1 - x0, y1 - y0)
        if not all(math.isfinite(v) for v in source_bounds) or src.w < 0 or src.h < 0:
            raise DrawError("bad_param", "source_bounds: không hợp lệ")
    else:
        src = lo.content_bounds(layers)

    pl = lo.plan(src, layout, machine)
    placed = lo.place_layers(layers, pl, layout.reverse)

    W, H = machine.work_w, machine.work_h
    files = []
    warnings: list[dict] = []
    for layer in placed:
        if not layer.strokes:
            continue
        for s in layer.strokes:           # chốt chặn: phép đặt không bao giờ được đẩy nét ra ngoài vùng máy
            for x, y in s:
                if x < -lo.EPS or y < -lo.EPS or x > W + lo.EPS or y > H + lo.EPS:
                    raise DrawError("out_of_area", f"Có nét vượt vùng làm việc {W:g}x{H:g} mm.")
        lines, stats, warns = gc.build_gcode(layer.strokes, gp, machine)
        try:
            if clean_gcode(lines) != lines:
                raise DrawError("internal_error", "G-code bị bộ làm sạch của tác vụ thay đổi.")
        except JobError as exc:
            raise DrawError("internal_error", f"G-code không qua bộ kiểm tra tác vụ: {exc.message}") from exc
        files.append({"layer": layer.id, "name": "draw" if len(placed) == 1 else f"draw-{layer.id}",
                      "gcode": "\n".join(lines) + "\n", "stats": stats})
        warnings += [dict(w, layer=layer.id) for w in warns]
    if not files:
        raise DrawError("empty_drawing", "Không có nét nào để vẽ.")
    b = pl.box
    return {"files": files, "box": {"x": b.x, "y": b.y, "w": b.w, "h": b.h,
                                    "scale_x": pl.sx, "scale_y": pl.sy},
            "warnings": warnings}
