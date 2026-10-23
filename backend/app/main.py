from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .routes import router
from .services.machine import ServiceError, machine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    machine.disconnect()  # đóng cổng serial gọn gàng khi tắt server


app = FastAPI(title="ExtruXY Backend", version="0.2.0", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status,
                        content={"error": {"code": exc.code, "message": exc.message}})

from pathlib import Path
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
