"""API tab Tạo bản vẽ. Mỏng: mọi logic nằm trong services/drawing. Không gọi máy trực tiếp (A4).

Hợp đồng (docs/DRAW_ROADMAP.md mục 3):
  GET  /schema                      tham số, khổ giấy, bút, kiểu tô, giới hạn
  POST /import                      nạp SVG hoặc ảnh (tác vụ nền) -> 202 {task, state}
  POST /svg                         như /import nhưng chạy đồng bộ, chỉ SVG (giữ để tương thích)
  GET  /tasks/{id}                  tiến trình; POST /tasks/{id}/cancel; DELETE /tasks/{id}
  GET  /tasks/{id}/preview          nét rút gọn để vẽ nháp (tọa độ nguồn)
  POST /gcode                       tính G-code + số liệu (không lưu)
  GET/POST /drafts, POST /drafts/reorder, GET /drafts/{id}[/gcode/{file}|/preview.svg], PATCH/DELETE /drafts/{id}
  GET/PUT /settings                 thư mục bản thảo + hạn mức
Được gắn vào app trong api/__init__.py (danh sách ROUTERS).
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from ..services.drawing import DrawError, describe, drafts, import_svg, make_gcode, spec
from ..services.drawing import calibration, gcode_import, isolated, preview, raster, service
from ..services.drawing.shapes import Layer
from ..services.drawing.store import TASKS
from ..services.drawing.svg_in import MAX_SVG_BYTES
from ..services.drawing.tasks import JOBS
from ..services.machine import ServiceError

router = APIRouter(prefix="/api/draw")

MAX_RASTER_BYTES = 40 * 1024 * 1024
RASTER_EXT = (".png", ".jpg", ".jpeg", ".webp")
IMPORT_KEYS = {"svg", "optimize", "raster", "style", "palette", "layout"}


class LayerIn(BaseModel):
    id: str = "1"
    strokes: list[list[tuple[float, float]]] = []


class GcodeRequest(BaseModel):
    task: str | None = None                       # mã bản vẽ đã nạp (từ /import)...
    layers: list[LayerIn] | None = None           # ...hoặc gửi thẳng đường nét (mm)
    machine: dict[str, Any]
    layout: dict[str, Any] = {}
    gcode: dict[str, Any] = {}
    source_bounds: tuple[float, float, float, float] | None = None


class DraftRequest(GcodeRequest):
    name: str = Field(default="Bản vẽ", max_length=80)


class DraftOrder(BaseModel):
    ids: list[str] = Field(max_length=1000)


class DraftPatch(BaseModel):
    name: str | None = None
    pinned: bool | None = None
    priority: int | None = None


class CalibrationRequest(BaseModel):
    machine: dict[str, Any]
    gcode: dict[str, Any] = {}
    pen_width_mm: float = Field(0.4, allow_inf_nan=False)
    paper_x_mm: float = Field(0.0, ge=0, le=5000, allow_inf_nan=False)
    paper_y_mm: float = Field(0.0, ge=0, le=5000, allow_inf_nan=False)


class SettingsRequest(BaseModel):
    max_count: int
    max_mb: int


def _wrap(fn, *args):
    """Đổi lỗi nội bộ thành lỗi chuẩn của dự án: {"error": {"code", "message"}}."""
    try:
        return fn(*args)
    except DrawError as exc:
        raise ServiceError(exc.code, exc.message, exc.status) from exc


def _options(options: str, allowed: set[str]) -> dict:
    try:
        opts = json.loads(options or "{}")
    except ValueError:
        raise DrawError("bad_param", "options: không phải JSON hợp lệ") from None
    if not isinstance(opts, dict) or set(opts) - allowed:
        raise DrawError("bad_param", f"options: chỉ nhận khóa {', '.join(sorted(allowed))}")
    return opts


def _resolve(req: GcodeRequest):
    """(lớp, hộp nguồn) từ `task` hoặc từ `layers` gửi thẳng."""
    if bool(req.task) == bool(req.layers):
        raise DrawError("bad_param", "gcode: gửi đúng một trong 'task' hoặc 'layers'")
    bounds = req.source_bounds
    if req.task:
        parsed = TASKS.get(req.task)
        if bounds is None and parsed.frame is not None:
            f = parsed.frame
            bounds = (f.x, f.y, f.x + f.w, f.y + f.h)
        return parsed.layers, bounds
    return [Layer(l.id, [list(s) for s in l.strokes]) for l in req.layers], bounds


@router.get("/schema")
def schema():
    return describe()


# --- nạp tệp (tác vụ nền) -----------------------------------------------------------
@router.post("/import", status_code=202)
def import_file(file: UploadFile = File(...), options: str = Form("{}")):
    """SVG -> import_svg; ảnh -> isolated.run_import (tiến trình riêng, ưu tiên thấp). Trả mã tác vụ ngay."""
    def run():
        opts = _options(options, IMPORT_KEYS)
        name = (file.filename or "ban-ve")[:80]
        is_svg = name.lower().endswith(".svg")
        if not is_svg and not name.lower().endswith(RASTER_EXT):
            raise DrawError("bad_image", "Chỉ nhận SVG, PNG, JPG hoặc WEBP.")
        data = file.file.read((MAX_SVG_BYTES if is_svg else MAX_RASTER_BYTES) + 1)
        if is_svg:
            spec.parse("svg", opts.get("svg")); spec.parse("optimize", opts.get("optimize"))
            work = lambda ctx, token: import_svg(data, opts.get("svg"), opts.get("optimize"), token, ctx)
        else:
            if len(data) > MAX_RASTER_BYTES:
                raise DrawError("file_too_large", f"Ảnh lớn hơn {MAX_RASTER_BYTES // (1024 * 1024)} MB.", 413)
            for group in ("raster", "style", "palette", "optimize"):
                spec.parse(group, opts.get(group))        # lỗi tham số báo ngay, không đợi tác vụ
            raster.reference_box(opts.get("layout"))
            work = lambda ctx, token: isolated.run_import(data, name, opts, token, ctx)
        return JOBS.submit(work).view()
    return _wrap(run)


@router.post("/svg")
def svg(file: UploadFile = File(...), options: str = Form("{}")):
    """Nạp SVG đồng bộ (+ tối ưu nét). `options` = {"svg": {...}, "optimize": {...}}. Trả mã `task`."""
    def run():
        opts = _options(options, {"svg", "optimize"})
        data = file.file.read(MAX_SVG_BYTES + 1)
        return import_svg(data, opts.get("svg"), opts.get("optimize"))
    return _wrap(run)


@router.get("/tasks/{token}")
def task_state(token: str):
    return _wrap(lambda: JOBS.get(token).view())


@router.post("/tasks/{token}/cancel")
def task_cancel(token: str):
    _wrap(JOBS.cancel, token)
    return {"ok": True}


@router.delete("/tasks/{token}")
def drop_task(token: str):
    TASKS.drop(token)
    return {"ok": True}


@router.get("/tasks/{token}/preview")
def task_preview(token: str, tol: float = 0.3):
    def run():
        if not 0 <= tol <= 10:
            raise DrawError("bad_param", "tol: ngoài khoảng 0..10 mm")
        parsed = TASKS.get(token)
        colors = {l["id"]: l.get("color") for l in parsed.info.get("layers", [])}
        out = preview.build(parsed.layers, colors, tol)
        f = parsed.frame                       # hộp nguồn mà /gcode sẽ dùng (None = hộp bao của nét)
        out["frame"] = {"x": f.x, "y": f.y, "w": f.w, "h": f.h} if f else None
        return out
    return _wrap(run)


# --- G-code ---------------------------------------------------------------------------
@router.post("/gcode")
def gcode(req: GcodeRequest):
    def run():
        layers, bounds = _resolve(req)
        return make_gcode(layers, req.machine, req.layout, req.gcode, bounds)
    return _wrap(run)


# --- bản thảo ---------------------------------------------------------------------------
@router.post("/drafts", status_code=201)
def draft_create(req: DraftRequest):
    def run():
        layers, bounds = _resolve(req)
        result, placed = service.build(layers, req.machine, req.layout, req.gcode, bounds)
        machine = spec.parse("machine", req.machine).as_dict()
        params = {"machine": req.machine, "layout": req.layout, "gcode": req.gcode}
        if req.task:
            params["source"] = {k: v for k, v in TASKS.get(req.task).info.items() if k in ("mode", "name")}
        return {"draft": drafts.create(req.name, result, placed, machine, params), "warnings": result["warnings"]}
    return _wrap(run)


MAX_GCODE_BYTES = 20 * 1024 * 1024


@router.post("/drafts/import-gcode", status_code=201)
def draft_import_gcode(file: UploadFile = File(...), work_w: float = Form(285.0), work_h: float = Form(318.0)):
    """Một tệp G-code có sẵn = một bản thảo (làm sạch bằng bộ kiểm tra của tác vụ). Xem drawing/gcode_import.py."""
    def run():
        if not (1 <= work_w <= 5000 and 1 <= work_h <= 5000):
            raise DrawError("bad_param", "work_w/work_h: ngoài khoảng 1–5000 mm.")
        data = file.file.read(MAX_GCODE_BYTES + 1)
        if len(data) > MAX_GCODE_BYTES:
            raise DrawError("file_too_large", f"Tệp lớn hơn {MAX_GCODE_BYTES // (1024 * 1024)} MB.", 413)
        name = re.sub(r"\.[^.]*$", "", (file.filename or "G-code").strip()) or "G-code"
        return gcode_import.import_gcode(name, data.decode("utf-8", errors="replace"), work_w, work_h)
    return _wrap(run)


@router.post("/calibration", status_code=201)
def calibration_create(req: CalibrationRequest):
    """Tạo bản thảo tờ mẫu hiệu chỉnh bút (chữ F, thước 100 mm, 8 dải tô). Xem services/drawing/calibration.py."""
    return _wrap(calibration.make_draft, "Mẫu hiệu chỉnh bút", req.machine, req.gcode,
                 req.pen_width_mm, req.paper_x_mm, req.paper_y_mm)


@router.get("/drafts")
def draft_list():
    return {"drafts": _wrap(drafts.list_drafts)}


@router.get("/drafts/{draft_id}")
def draft_get(draft_id: str):
    return {"draft": _wrap(drafts.get, draft_id)}


@router.get("/drafts/{draft_id}/gcode/{layer_file}")
def draft_gcode(draft_id: str, layer_file: str):
    return PlainTextResponse(_wrap(drafts.read_gcode, draft_id, layer_file))


@router.get("/drafts/{draft_id}/preview.svg")
def draft_preview(draft_id: str):
    return Response(_wrap(drafts.read_preview, draft_id), media_type="image/svg+xml")


@router.post("/drafts/reorder")
def drafts_reorder(req: DraftOrder):
    _wrap(drafts.reorder, req.ids)
    return {"drafts": drafts.list_drafts()}


@router.patch("/drafts/{draft_id}")
def draft_patch(draft_id: str, req: DraftPatch):
    return {"draft": _wrap(drafts.update, draft_id, req.name, req.pinned, req.priority)}


@router.delete("/drafts/{draft_id}")
def draft_delete(draft_id: str):
    _wrap(drafts.delete, draft_id)
    return {"ok": True}


# --- cài đặt thư mục bản thảo -------------------------------------------------------------
@router.get("/settings")
def settings_get():
    return {"settings": drafts.load_settings(), "limits": drafts.LIMITS, "folder": str(drafts.root_dir())}


@router.put("/settings")
def settings_put(req: SettingsRequest):
    saved = _wrap(drafts.save_settings, req.model_dump())
    return {"settings": saved, "limits": drafts.LIMITS, "folder": str(drafts.root_dir())}
