"""API tab Tạo bản vẽ. Mỏng: mọi logic nằm trong services/drawing. Không gọi máy trực tiếp (A4).

Gắn vào main.py bằng MỘT dòng (đặt ngay sau `app.include_router(router)`):
    from .routes_draw import router as draw_router; app.include_router(draw_router)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .services.drawing import DrawError, describe, make_gcode
from .services.drawing.shapes import Layer
from .services.machine import ServiceError

router = APIRouter(prefix="/api/draw")


class LayerIn(BaseModel):
    id: str = "1"
    strokes: list[list[tuple[float, float]]] = Field(default_factory=list)


class GcodeRequest(BaseModel):
    layers: list[LayerIn] = Field(min_length=1)
    machine: dict[str, Any]
    layout: dict[str, Any] = Field(default_factory=dict)
    gcode: dict[str, Any] = Field(default_factory=dict)
    source_bounds: tuple[float, float, float, float] | None = None


@router.get("/schema")
def schema():
    return describe()


@router.post("/gcode")
def gcode(req: GcodeRequest):
    layers = [Layer(l.id, [list(s) for s in l.strokes]) for l in req.layers]
    try:
        return make_gcode(layers, req.machine, req.layout, req.gcode, req.source_bounds)
    except DrawError as exc:       # đổi sang lỗi chuẩn của dự án: {"error": {"code", "message"}}
        raise ServiceError(exc.code, exc.message, exc.status) from exc
