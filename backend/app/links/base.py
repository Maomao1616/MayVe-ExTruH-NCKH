"""Giao diện chung cho mọi kiểu kết nối tới bộ điều khiển (máy thật hoặc mô phỏng)."""
from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import Callable

log = logging.getLogger(__name__)


class LinkError(ConnectionError):
    """Lỗi kết nối hoặc ghi dữ liệu."""


class BaseLink(ABC):
    """SerialLink và SimLink cùng giao diện này để phần còn lại không phải phân biệt."""

    kind = "base"

    def __init__(self) -> None:
        self._line_listeners: list[Callable[[str], None]] = []
        self._close_listeners: list[Callable[[str], None]] = []
        self._listener_lock = threading.Lock()

    # --- đăng ký nhận dữ liệu -------------------------------------------------
    def add_listener(self, callback: Callable[[str], None]) -> None:
        """callback(line) được gọi cho mỗi dòng nhận được (từ luồng nền)."""
        with self._listener_lock:
            self._line_listeners.append(callback)

    def add_close_listener(self, callback: Callable[[str], None]) -> None:
        """callback(reason) được gọi khi kết nối tự đóng ngoài ý muốn."""
        with self._listener_lock:
            self._close_listeners.append(callback)

    def _emit(self, line: str) -> None:
        with self._listener_lock:
            listeners = list(self._line_listeners)
        for callback in listeners:
            try:
                callback(line)
            except Exception:  # một listener lỗi không được làm sập luồng đọc
                log.exception("Listener lỗi khi xử lý dòng: %r", line)

    def _emit_closed(self, reason: str) -> None:
        with self._listener_lock:
            listeners = list(self._close_listeners)
        for callback in listeners:
            try:
                callback(reason)
            except Exception:
                log.exception("Close listener lỗi")

    # --- giao diện bắt buộc ---------------------------------------------------
    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def write_line(self, text: str) -> None:
        """Gửi một dòng lệnh (tự thêm xuống dòng)."""

    @abstractmethod
    def write_realtime(self, data: bytes) -> None:
        """Gửi ký tự điều khiển tức thời (?, !, ~, Ctrl-X, ...), không thêm xuống dòng."""
