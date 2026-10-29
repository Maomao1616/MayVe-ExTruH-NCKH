"""Bộ nhớ tạm các bản vẽ đã nạp (để đổi tham số bố trí/G-code không phải nạp lại ảnh/SVG).
Giữ vài tác vụ gần nhất để tiết kiệm RAM máy yếu."""
from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from .errors import DrawError
from .shapes import Box, Layer


@dataclass
class Parsed:
    layers: list[Layer]
    frame: Box | None = None                 # khung gốc để co giãn (None = hộp bao của nét)
    info: dict = field(default_factory=dict)


class TaskStore:
    def __init__(self, capacity: int = 3) -> None:
        self.capacity = capacity
        self._items: OrderedDict[str, Parsed] = OrderedDict()
        self._lock = threading.Lock()

    def put(self, item: Parsed) -> str:
        token = uuid.uuid4().hex
        with self._lock:
            self._items[token] = item
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
        return token

    def get(self, token: str) -> Parsed:
        with self._lock:
            item = self._items.get(token)
            if item is None:
                raise DrawError("unknown_task", "Bản vẽ đã nạp không còn (hết bộ nhớ tạm). Hãy nạp lại tệp.", 404)
            self._items.move_to_end(token)
            return item

    def drop(self, token: str) -> None:
        with self._lock:
            self._items.pop(token, None)


TASKS = TaskStore()
