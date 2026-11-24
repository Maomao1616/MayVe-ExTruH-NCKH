"""Địa chỉ + mã QR để mở giao diện từ máy khác (docs/13). Khách thấy địa chỉ Internet; địa chỉ mạng nhà chỉ cho quản lý."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..auth import COOKIE, auth
from ..services import share

router = APIRouter(prefix="/api")


@router.get("/share")
def get_share(request: Request):
    items = share.share_items()
    if not auth.is_admin(request.cookies.get(COOKIE)):
        items = [i for i in items if i["kind"] == "public"]        # IP trong mạng nhà không cần lộ cho người ngoài
    return {"items": items}
