"""Sổ đăng ký: gom các biến thể cùng loại (kiểu vector hóa...). Thêm kiểu mới không sửa chỗ khác.

    @VECTORIZERS.register("centerline")
    def centerline(...): ...
"""
from __future__ import annotations

from typing import Callable

from .errors import DrawError


class Registry:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: dict[str, Callable] = {}

    def register(self, name: str) -> Callable[[Callable], Callable]:
        def decorator(fn: Callable) -> Callable:
            if name in self._items:
                raise ValueError(f"{self.kind} '{name}' đã được đăng ký")
            self._items[name] = fn
            return fn
        return decorator

    def get(self, name: str) -> Callable:
        try:
            return self._items[name]
        except KeyError:
            raise DrawError("unknown_option",
                            f"Không có {self.kind} '{name}'. Hiện có: {', '.join(self.names()) or '(chưa có)'}") from None

    def names(self) -> list[str]:
        return sorted(self._items)


VECTORIZERS = Registry("kiểu vector hóa")
FILLERS = Registry("kiểu tô")          # zigzag / wave / spiral (styles.py): ảnh độ đậm -> đường nét
