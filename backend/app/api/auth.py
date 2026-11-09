"""API đăng nhập quản lý bằng mã PIN. Mỏng: logic ở app/auth.py."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from ..auth import COOKIE, SESSION_TTL_S, auth
from ..services.machine import ServiceError, machine

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    pin: str = Field(max_length=64)


class ChangePinRequest(BaseModel):
    old_pin: str = Field("", max_length=64)
    new_pin: str = Field(max_length=64)


def _role(request: Request) -> dict:
    return {"role": "admin" if auth.is_admin(request.cookies.get(COOKIE)) else "guest",
            "pin_set": auth.pin_set()}


@router.get("/me")
def me(request: Request):
    return _role(request)


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response):
    token = auth.login(req.pin)
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_TTL_S, httponly=True, samesite="strict",
                        secure=https, path="/")
    return {"role": "admin", "pin_set": True}


@router.post("/pin")
def change_pin(req: ChangePinRequest, request: Request, response: Response):
    """Đổi PIN quản lý (cần đang là quản lý: không nằm trong GUEST_ROUTES). Người đổi được cấp phiên mới."""
    token = auth.change_pin(req.old_pin, req.new_pin)
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_TTL_S, httponly=True, samesite="strict",
                        secure=https, path="/")
    return {"role": "admin", "pin_set": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    was_admin = auth.pin_set() and auth.is_admin(token)
    auth.logout(token)
    response.delete_cookie(COOKIE, path="/")
    if was_admin:                       # quản lý rời đi thì khóa chuyển động lại (lớp an toàn thứ hai)
        try:
            machine.set_motion(False, None)
        except ServiceError:
            pass                        # máy được mở khóa cố định từ lúc khởi động: không khóa được
    return {"role": "guest", "pin_set": auth.pin_set()}
