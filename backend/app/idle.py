"""Tự tắt server khi không còn trang web nào mở (bản đóng gói chạy ẩn, không có cửa sổ để đóng).

Chỉ bật khi đặt EXTRUXY_IDLE_EXIT_MIN > 0 (launcher/start.ps1 đặt 10); chạy tay `uvicorn` thì không bao giờ tự tắt.
Mỗi yêu cầu HTTP gọi `touch()`. Trang đang mở hỏi /api/status liên tục; tab bị ẩn vẫn gửi /api/health
mỗi 30 giây (core/state.js), nên chỉ khi đóng hết trang mới im lặng. Đang chạy tác vụ G-code thì không tắt.
"""
from __future__ import annotations

import os
import threading
import time

CHECK_EVERY_S = 30.0

_last = time.monotonic()


def touch() -> None:
    global _last
    _last = time.monotonic()


def limit_minutes() -> float:
    try:
        return max(0.0, float(os.environ.get("EXTRUXY_IDLE_EXIT_MIN", "0")))
    except ValueError:
        return 0.0


def start(machine) -> threading.Event | None:
    """Bật luồng canh (nếu được cấu hình). Hết hạn: ngắt kết nối máy gọn gàng rồi thoát tiến trình.
    Trả về Event để dừng luồng canh (test dùng), None nếu không bật."""
    minutes = limit_minutes()
    if minutes <= 0:
        return None
    stop = threading.Event()

    def watch() -> None:
        while not stop.wait(CHECK_EVERY_S):
            if time.monotonic() - _last < minutes * 60:
                continue
            if machine.job_active():
                touch()                          # đang vẽ: chờ vẽ xong rồi mới tính lại
                continue
            try:
                machine.disconnect()
            finally:
                os._exit(0)                      # chạy ẩn, không có console: thoát thẳng
            return

    threading.Thread(target=watch, name="idle-exit", daemon=True).start()
    return stop
