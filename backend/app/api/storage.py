"""API lưu trữ: macro (CRUD) và xem/tải nội dung thư mục dữ liệu (chỉ đọc). Mỏng: logic ở services."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..services import macros, storage
from ..services.machine import ServiceError

router = APIRouter(prefix="/api")


class MacroIn(BaseModel):
    name: str
    type: str
    lines: list[str] | str
    needsHome: bool = False


def _wrap(fn, *args):
    try:
        return fn(*args)
    except (macros.MacroError, storage.StorageError) as exc:
        raise ServiceError(exc.code, exc.message, exc.status) from exc


def _data(req: MacroIn) -> dict[str, Any]:
    return req.model_dump()


@router.get("/macros")
def macro_list():
    return {"macros": macros.list_macros(), "limits": macros.LIMITS}


@router.post("/macros", status_code=201)
def macro_create(req: MacroIn):
    return {"macro": _wrap(macros.create, _data(req))}


@router.put("/macros/{macro_id}")
def macro_update(macro_id: str, req: MacroIn):
    return {"macro": _wrap(macros.update, macro_id, _data(req))}


@router.delete("/macros/{macro_id}")
def macro_delete(macro_id: str):
    _wrap(macros.delete, macro_id)
    return {"ok": True}


@router.get("/storage")
def storage_overview():
    return storage.overview()


@router.get("/storage/file")
def storage_file(area: str, path: str):
    target = _wrap(storage.resolve_file, area, path)
    return FileResponse(target, filename=target.name)
