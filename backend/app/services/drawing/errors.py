"""Lỗi của tab Tạo bản vẽ. `code` ổn định để frontend dịch (quy ước E3), `message` chỉ để tra cứu."""
from __future__ import annotations


class DrawError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
