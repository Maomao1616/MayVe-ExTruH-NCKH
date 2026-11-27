"""Tab Beta (in trang PDF): tải PDF, xem trang gốc, nạp một trang thành bản vẽ.

  POST /api/beta/pdf/upload                   tải PDF (một lần) -> {doc, name, pages, sizes}
  GET  /api/beta/pdf/schema                   khai báo tham số của tab Beta
  GET  /api/beta/pdf/{doc}/page/{n}/preview.png   ảnh trang gốc (để so sánh)
  POST /api/beta/pdf/import                   {doc, options} -> 202 {task, state}; theo dõi bằng GET /api/draw/tasks/{task}
                                              (cùng cơ chế tác vụ nền và cùng kết quả như /api/draw/import, nên mở được ở tab Tạo bản vẽ)
Mọi route ở đây chỉ dành cho quản lý (mặc định của app/auth.py). Gỡ tính năng: xem docs/10_TAB_BETA_PDF.md mục "Cách gỡ".
"""
from __future__ import annotations

import re

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..services.beta_pdf import options, service
from ..services.beta_pdf.reader import MAX_PDF_BYTES
from ..services.beta_pdf.store import PDFS, Stored
from ..services.drawing import DrawError
from ..services.drawing.tasks import JOBS
from ..services.machine import ServiceError

router = APIRouter(prefix="/api/beta/pdf")


def _wrap(fn, *args):
    try:
        return fn(*args)
    except DrawError as exc:
        raise ServiceError(exc.code, exc.message, exc.status) from exc


def _name(filename: str | None) -> str:
    base = re.split(r"[\\/]", filename or "")[-1].strip() or "trang.pdf"
    return base[:80]


class ImportRequest(BaseModel):
    doc: str
    options: dict = Field(default_factory=dict)


@router.get("/schema")
def schema():
    return {"params": options.describe()}


@router.post("/upload", status_code=201)
def upload(file: UploadFile = File(...)):
    def run():
        data = file.file.read(MAX_PDF_BYTES + 1)
        info = service.page_info(data)                       # kiểm PDF hợp lệ, đếm trang
        token = PDFS.put(Stored(data, _name(file.filename), info["pages"]))
        return {"doc": token, "name": _name(file.filename), **info}
    return _wrap(run)


@router.get("/{doc}/page/{page}/preview.png")
def page_preview(doc: str, page: int, dpi: float = 80.0):
    def run():
        item = PDFS.get(doc)
        if not 1 <= page <= item.pages:
            raise DrawError("bad_param", f"Trang {page} không có (PDF có {item.pages} trang).")
        return Response(service.page_preview(item.data, page, max(20.0, min(dpi, 300.0))), media_type="image/png",
                        headers={"Cache-Control": "no-store"})
    return _wrap(run)


@router.post("/import", status_code=202)
def import_page(req: ImportRequest):
    def run():
        item = PDFS.get(req.doc)
        opts = options.parse(req.options)                    # lỗi tham số báo ngay, không đợi tác vụ
        if opts.page > item.pages:
            raise DrawError("bad_param", f"Trang {opts.page} không có (PDF có {item.pages} trang).")
        work = lambda ctx, token: service.import_page(item.data, item.name, req.options, token, ctx)
        return JOBS.submit(work).view()
    return _wrap(run)
