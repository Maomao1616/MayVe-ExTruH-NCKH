"""API tab Tạo bản vẽ. Mỏng: mọi logic nằm trong services/drawing. Không gọi máy trực tiếp (A4).

Được gắn vào app trong api/__init__.py (danh sách ROUTERS).
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from ..services.drawing import DrawError, describe, import_svg, make_gcode
from ..services.drawing.shapes import Layer
from ..services.drawing.store import TASKS
from ..services.drawing.svg_in import MAX_SVG_BYTES
from ..services.machine import ServiceError

router = APIRouter(prefix="/api/draw")


class LayerIn(BaseModel):
    id: str = "1"
    strokes: list[list[tuple[float, float]]] = []


class GcodeRequest(BaseModel):
    task: str | None = None                       # mã bản vẽ đã nạp (từ /svg)...
    layers: list[LayerIn] | None = None           # ...hoặc gửi thẳng đường nét (mm)
    machine: dict[str, Any]
    layout: dict[str, Any] = {}
    gcode: dict[str, Any] = {}
    source_bounds: tuple[float, float, float, float] | None = None


def _wrap(fn):
    """Đổi lỗi nội bộ thành lỗi chuẩn của dự án: {"error": {"code", "message"}}."""
    try:
        return fn()
    except DrawError as exc:
        raise ServiceError(exc.code, exc.message, exc.status) from exc


@router.get("/schema")
def schema():
    return describe()


@router.post("/svg")
def svg(file: UploadFile = File(...), options: str = Form("{}")):
    """Nạp SVG (+ tối ưu nét). `options` là JSON: {"svg": {...}, "optimize": {...}}. Trả mã `task`."""
    def run():
        try:
            opts = json.loads(options or "{}")
        except ValueError:
            raise DrawError("bad_param", "options: không phải JSON hợp lệ") from None
        if not isinstance(opts, dict) or set(opts) - {"svg", "optimize"}:
            raise DrawError("bad_param", "options: chỉ nhận khóa 'svg' và 'optimize'")
        data = file.file.read(MAX_SVG_BYTES + 1)
        return import_svg(data, opts.get("svg"), opts.get("optimize"))
    return _wrap(run)


@router.post("/gcode")
def gcode(req: GcodeRequest):
    def run():
        if bool(req.task) == bool(req.layers):
            raise DrawError("bad_param", "gcode: gửi đúng một trong 'task' hoặc 'layers'")
        bounds = req.source_bounds
        if req.task:
            parsed = TASKS.get(req.task)
            layers = parsed.layers
            if bounds is None and parsed.frame is not None:
                f = parsed.frame
                bounds = (f.x, f.y, f.x + f.w, f.y + f.h)
        else:
            layers = [Layer(l.id, [list(s) for s in l.strokes]) for l in req.layers]
        return make_gcode(layers, req.machine, req.layout, req.gcode, bounds)
    return _wrap(run)


@router.delete("/tasks/{token}")
def drop_task(token: str):
    TASKS.drop(token)
    return {"ok": True}
