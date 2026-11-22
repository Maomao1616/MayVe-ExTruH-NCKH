"""Bộ nhớ tạm các tệp PDF đã tải lên (tải một lần, chọn trang nhiều lần). Giữ ít để tiết kiệm RAM máy yếu."""
from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass

from ..drawing.errors import DrawError


@dataclass
class Stored:
    data: bytes
    name: str
    pages: int


class PdfStore:
    def __init__(self, capacity: int = 2) -> None:
        self.capacity = capacity
        self._items: OrderedDict[str, Stored] = OrderedDict()
        self._lock = threading.Lock()

    def put(self, item: Stored) -> str:
        token = uuid.uuid4().hex
        with self._lock:
            self._items[token] = item
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
        return token

    def get(self, token: str) -> Stored:
        with self._lock:
            item = self._items.get(token)
            if item is None:
                raise DrawError("unknown_pdf", "PDF đã tải không còn trong bộ nhớ tạm. Hãy chọn lại tệp.", 404)
            self._items.move_to_end(token)
            return item

    def drop(self, token: str) -> None:
        with self._lock:
            self._items.pop(token, None)


PDFS = PdfStore()
