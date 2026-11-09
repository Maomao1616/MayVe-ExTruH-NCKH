"""API ảnh khách gửi (services/customer.py). Chỉ POST /api/customer mở cho khách; mọi thứ khác cần quản lý.

  POST   /api/customer              (khách) multipart: file = ảnh, meta = JSON {name, note, params}
  GET    /api/customer              (quản lý) danh sách, mới nhất trước
  GET    /api/customer/{id}/image   (quản lý) ảnh đã thu nhỏ (JPEG)
  POST   /api/customer/{id}/seen    (quản lý) đánh dấu đã xem
  DELETE /api/customer/{id}         (quản lý) xóa
"""
from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from ..services import customer
from ..services.drawing.errors import DrawError
from ..services.machine import ServiceError

router = APIRouter(prefix="/api/customer")


def _wrap(fn, *args):
    try:
        return fn(*args)
    except DrawError as exc:
        raise ServiceError(exc.code, exc.message, exc.status) from exc


def _source(request: Request) -> str:
    """Nguồn để đếm số lần gửi: qua Cloudflare thì IP thật nằm ở CF-Connecting-IP (địa chỉ kết nối luôn là 127.0.0.1)."""
    forwarded = request.headers.get("cf-connecting-ip", "").strip()
    return forwarded[:64] or (request.client.host if request.client else "?")


@router.post("", status_code=201)
def send(request: Request, file: UploadFile = File(...), meta: str = Form("{}")):
    def run():
        try:
            info = json.loads(meta or "{}")
        except ValueError:
            raise DrawError("bad_param", "meta: không phải JSON hợp lệ.") from None
        if not isinstance(info, dict):
            raise DrawError("bad_param", "meta: phải là đối tượng JSON.")
        data = file.file.read(customer.LIMITS["image_bytes"] + 1)
        item = customer.create(data, file.filename or "anh", str(info.get("name") or ""), str(info.get("note") or ""),
                               info.get("params"), _source(request))
        return {"item": {"id": item["id"], "expires": item["expires"]}}      # khách không cần thấy phần còn lại
    return _wrap(run)


@router.get("")
def items():
    return {"items": _wrap(customer.list_items), "days": customer.keep_days()}


@router.get("/{item_id}/image")
def image(item_id: str):
    return FileResponse(_wrap(customer.image_path, item_id), media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=300"})


@router.post("/{item_id}/seen")
def seen(item_id: str):
    return {"item": _wrap(customer.mark_seen, item_id)}


@router.delete("/{item_id}")
def remove(item_id: str):
    _wrap(customer.delete, item_id)
    return {"ok": True}
