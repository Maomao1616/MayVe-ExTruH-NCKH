import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import idle
from .api import ROUTERS
from .services.machine import ServiceError, machine

# Backend điều khiển máy thật nên mặc định chỉ phục vụ máy cục bộ (uvicorn mặc định bind
# 127.0.0.1). Chạy qua LAN: đặt EXTRUXY_ALLOWED_HOSTS="192.168.1.20,localhost" (hoặc "*").
ALLOWED_HOSTS = {h.strip().lower() for h in
                 os.environ.get("EXTRUXY_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
                 if h.strip()}
MAX_BODY_BYTES = 64 * 1024 * 1024    # đủ cho SVG 20 MB và tệp G-code 200.000 dòng
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    idle.start(machine)  # bản đóng gói: tự tắt khi đóng hết trang (EXTRUXY_IDLE_EXIT_MIN)
    yield
    machine.disconnect()  # đóng cổng serial gọn gàng khi tắt server


app = FastAPI(title="ExtruXY Backend", version="0.2.0", lifespan=lifespan)
for router in ROUTERS:
    app.include_router(router)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _host_name(host: str) -> str:
    """'127.0.0.1:8000' -> '127.0.0.1', '[::1]:8000' -> '[::1]'."""
    if host.startswith("["):
        return host.split("]", 1)[0] + "]"
    return host.split(":", 1)[0]


@app.middleware("http")
async def local_guard(request: Request, call_next):
    """Chặn DNS rebinding (Host lạ) và trang web khác gửi lệnh tới máy (Origin lạ)."""
    idle.touch()
    host = (request.headers.get("host") or "").lower()
    if "*" not in ALLOWED_HOSTS and _host_name(host) not in ALLOWED_HOSTS:
        return _error(403, "bad_host", f"Host không được phép: {host or '(trống)'}")
    if request.method not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is not None and urlsplit(origin).netloc.lower() != host:
            return _error(403, "bad_origin", "Yêu cầu từ trang khác bị chặn.")
        try:
            length = int(request.headers.get("content-length") or 0)
        except ValueError:
            return _error(400, "bad_request", "Content-Length không hợp lệ.")
        if length > MAX_BODY_BYTES:
            return _error(413, "too_large", "Yêu cầu quá lớn.")
    return await call_next(request)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return _error(exc.status, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Giữ dạng {"detail": [...]} mà api.js dựa vào, nhưng bỏ `input`/`ctx`: chúng có thể
    # chứa NaN/Infinity làm chính phản hồi lỗi 422 sập thành 500.
    detail = [{k: e[k] for k in ("type", "loc", "msg") if k in e} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
