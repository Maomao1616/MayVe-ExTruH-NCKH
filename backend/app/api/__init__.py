"""Các router HTTP. Thêm router mới: tạo file trong api/ rồi thêm vào ROUTERS."""
from .config import router as config_router
from .draw import router as draw_router
from .machine import router as machine_router
from .storage import router as storage_router

ROUTERS = (machine_router, config_router, draw_router, storage_router)
