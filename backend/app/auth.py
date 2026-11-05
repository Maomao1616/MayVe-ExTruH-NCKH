"""Phân quyền khách / quản lý bằng mã PIN (docs/08_TRIEN_KHAI.md phần B).

- Quản lý = ai nhập đúng EXTRUXY_ADMIN_PIN: được cấp phiên (cookie ngẫu nhiên, lưu trong RAM).
- Khách = không có phiên: chỉ gọi được các route trong GUEST_ROUTES (xem trạng thái, khai báo tham số tab vẽ).
- CHẶN MẶC ĐỊNH: route /api nào không nằm trong GUEST_ROUTES đều cần quản lý, kể cả route thêm sau này.
- Chưa đặt EXTRUXY_ADMIN_PIN: giữ hành vi cũ (ai vào cũng là quản lý) để chạy tay khi code không phiền;
  giao diện hiện cảnh báo. BẮT BUỘC đặt khi cho máy khác vào mạng.
- Lớp này nằm NGOÀI lớp "mở khóa chuyển động" (services/machine.py): quản lý vẫn phải mở khóa mới chạy được máy.
"""
from __future__ import annotations

import os
import secrets
import threading
import time

from .services.machine import ServiceError

COOKIE = "extruxy_session"
SESSION_TTL_S = 12 * 3600       # hết hạn sau 12 giờ kể từ lúc đăng nhập
MAX_FAILS = 5                   # sai liên tiếp chừng này lần thì khóa đăng nhập
LOCK_S = 60                     # ... trong chừng này giây (cho mọi nguồn: qua Cloudflare IP nguồn luôn là 127.0.0.1)

# Route khách được gọi. (phương thức, đường dẫn) khớp CHÍNH XÁC; mọi thứ khác dưới /api cần quản lý.
GUEST_ROUTES = frozenset({
    ("GET", "/api/health"),            # trang ẩn báo "còn mở"
    ("GET", "/api/status"),            # xem trạng thái chung, chỉ đọc
    ("GET", "/api/connection"),
    ("GET", "/api/draw/schema"),       # khai báo tham số để vẽ ô nhập tab Tạo bản vẽ
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
})


class AuthService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, float] = {}     # mã phiên -> giờ hết hạn
        self._fails = 0
        self._locked_until = 0.0

    # --- cấu hình ---
    @staticmethod
    def pin() -> str | None:
        """Đọc mỗi lần gọi (không nhớ) để test và người vận hành đổi được mà không sửa mã."""
        return (os.environ.get("EXTRUXY_ADMIN_PIN") or "").strip() or None

    def pin_set(self) -> bool:
        return self.pin() is not None

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._fails = 0
            self._locked_until = 0.0

    # --- phiên ---
    def _purge(self, now: float) -> None:
        for token in [t for t, until in self._sessions.items() if until <= now]:
            del self._sessions[token]

    def is_admin(self, token: str | None) -> bool:
        if not self.pin_set():
            return True
        if not token:
            return False
        with self._lock:
            self._purge(time.time())
            return token in self._sessions

    def login(self, pin: str) -> str:
        expected = self.pin()
        if expected is None:
            raise ServiceError("pin_not_set", "Chưa đặt EXTRUXY_ADMIN_PIN nên không có gì để đăng nhập.", 400)
        now = time.time()
        with self._lock:
            if now < self._locked_until:
                wait = int(self._locked_until - now) + 1
                raise ServiceError("login_locked", f"Nhập sai nhiều lần, thử lại sau {wait} giây.", 429)
            if not secrets.compare_digest(pin.encode(), expected.encode()):
                self._fails += 1
                if self._fails >= MAX_FAILS:
                    self._fails = 0
                    self._locked_until = now + LOCK_S
                raise ServiceError("bad_pin", "Sai mã PIN quản lý.", 401)
            self._fails = 0
            self._purge(now)
            token = secrets.token_urlsafe(32)
            self._sessions[token] = now + SESSION_TTL_S
            return token

    def logout(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(token, None)

    # --- cổng kiểm của middleware ---
    def allowed(self, method: str, path: str, token: str | None) -> bool:
        return (method, path) in GUEST_ROUTES or self.is_admin(token)


auth = AuthService()
