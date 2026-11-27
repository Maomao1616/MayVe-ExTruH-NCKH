"""Các router HTTP. Thêm router mới: tạo file trong api/ rồi thêm vào ROUTERS."""
from .auth import router as auth_router
from .beta_pdf import router as beta_pdf_router      # tab Beta (docs/10); gỡ: bỏ dòng này và beta_pdf_router ở ROUTERS
from .config import router as config_router
from .customer import router as customer_router
from .draw import router as draw_router
from .events import router as events_router
from .machine import router as machine_router
from .share import router as share_router
from .storage import router as storage_router

ROUTERS = (auth_router, machine_router, events_router, config_router, customer_router, draw_router, storage_router, share_router, beta_pdf_router)
