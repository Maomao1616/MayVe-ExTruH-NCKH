"""Các router HTTP. Thêm router mới: tạo file trong api/ rồi thêm vào ROUTERS."""
from .auth import router as auth_router
from .config import router as config_router
from .draw import router as draw_router
from .machine import router as machine_router
from .storage import router as storage_router

ROUTERS = (auth_router, machine_router, config_router, draw_router, storage_router)
