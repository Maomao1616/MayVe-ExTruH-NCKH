"""Phân quyền khách / quản lý bằng mã PIN (docs/08_TRIEN_KHAI.md phần B).

- Quản lý = ai nhập đúng PIN quản lý: được cấp phiên (cookie ngẫu nhiên, lưu trong RAM).
  PIN lấy từ dòng `admin=...` của data/pin.txt (đổi được trên giao diện, áp dụng ngay), nếu không có thì từ biến
  môi trường EXTRUXY_ADMIN_PIN (launcher đặt từ chính tệp đó lúc khởi động).
- Khách = không có phiên: chỉ gọi được các route trong GUEST_ROUTES (xem trạng thái, khai báo tham số tab vẽ).
- CHẶN MẶC ĐỊNH: route /api nào không nằm trong GUEST_ROUTES đều cần quản lý, kể cả route thêm sau này.
- Chưa đặt EXTRUXY_ADMIN_PIN: giữ hành vi cũ (ai vào cũng là quản lý) để chạy tay khi code không phiền;
  giao diện hiện cảnh báo. BẮT BUỘC đặt khi cho máy khác vào mạng.
- Lớp này nằm NGOÀI lớp "mở khóa chuyển động" (services/machine.py): quản lý vẫn phải mở khóa mới chạy được máy.
"""
from __future__ import annotations

import os
import re
import secrets
import threading
import time

from . import paths
from .services.machine import ServiceError

COOKIE = "extruxy_session"
SESSION_TTL_S = 12 * 3600       # hết hạn sau 12 giờ kể từ lúc đăng nhập
MAX_FAILS = 5                   # sai liên tiếp chừng này lần thì khóa đăng nhập
LOCK_S = 60                     # ... trong chừng này giây (cho mọi nguồn: qua Cloudflare IP nguồn luôn là 127.0.0.1)
PIN_MIN, PIN_MAX = 4, 64        # độ dài PIN mới; chữ + số + ký hiệu ASCII, không khoảng trắng (launcher PowerShell đọc tệp theo ANSI)
_PIN_OK = re.compile(r"[!-~]+")
_ADMIN_LINE = re.compile(r"^\s*admin\s*=\s*(\S+)\s*$", re.IGNORECASE)

# Route khách được gọi. (phương thức, đường dẫn) khớp CHÍNH XÁC; mọi thứ khác dưới /api cần quản lý.
GUEST_ROUTES = frozenset({
    ("GET", "/api/health"),            # trang ẩn báo "còn mở"
    ("GET", "/api/status"),            # xem trạng thái chung, chỉ đọc
    ("POST", "/api/customer"),          # khách gửi ảnh cho chủ máy (api/customer.py); xem / xóa danh sách là việc quản lý
    ("GET", "/api/events"),            # luồng SSE: khách nhận trạng thái, nhật ký chỉ gửi cho quản lý (api/events.py)
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
    def _file_pin() -> str | None:
        try:
            for line in paths.data_file("pin.txt").read_text(encoding="utf-8", errors="replace").splitlines():
                match = _ADMIN_LINE.match(line)
                if match:
                    return match.group(1)
        except OSError:
            pass
        return None

    @staticmethod
    def pin() -> str | None:
        """Đọc mỗi lần gọi (không nhớ) để test và người vận hành đổi được mà không sửa mã.
        data/pin.txt thắng biến môi trường: đổi PIN trên giao diện có hiệu lực ngay, không cần khởi động lại."""
        return AuthService._file_pin() or (os.environ.get("EXTRUXY_ADMIN_PIN") or "").strip() or None

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

    def change_pin(self, old_pin: str, new_pin: str) -> str:
        """Đổi PIN quản lý. Chưa có PIN thì đặt luôn (ai vào cũng là quản lý, giống hành vi cũ). Trả mã phiên mới
        cho người đổi; mọi phiên khác bị đăng xuất. Sai PIN cũ tính vào cùng bộ đếm khóa với đăng nhập."""
        if not (PIN_MIN <= len(new_pin) <= PIN_MAX) or not _PIN_OK.fullmatch(new_pin):
            raise ServiceError("bad_new_pin",
                               f"PIN mới dài {PIN_MIN}–{PIN_MAX} ký tự, gồm chữ / số / ký hiệu, không khoảng trắng và không dấu tiếng Việt.", 400)
        now = time.time()
        with self._lock:
            expected = self.pin()
            if expected is not None:
                if now < self._locked_until:
                    wait = int(self._locked_until - now) + 1
                    raise ServiceError("login_locked", f"Nhập sai nhiều lần, thử lại sau {wait} giây.", 429)
                if not secrets.compare_digest(old_pin.encode(), expected.encode()):
                    self._fails += 1
                    if self._fails >= MAX_FAILS:
                        self._fails = 0
                        self._locked_until = now + LOCK_S
                    raise ServiceError("bad_pin", "Sai mã PIN hiện tại.", 401)
            self._write_pin(new_pin)
            self._fails = 0
            self._sessions.clear()
            token = secrets.token_urlsafe(32)
            self._sessions[token] = now + SESSION_TTL_S
            return token

    @staticmethod
    def _write_pin(new_pin: str) -> None:
        """Ghi dòng admin= vào data/pin.txt, giữ nguyên các dòng khác (vd unlock=). Ghi nguyên tử."""
        target = paths.data_file("pin.txt")
        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        kept = [ln for ln in lines if not _ADMIN_LINE.match(ln)]
        text = "\n".join([f"admin={new_pin}", *kept]) + "\n"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(target)
        except OSError as exc:
            raise ServiceError("pin_write_failed", f"Không ghi được data/pin.txt: {exc}", 500) from exc

    def logout(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(token, None)

    # --- cổng kiểm của middleware ---
    def allowed(self, method: str, path: str, token: str | None) -> bool:
        return (method, path) in GUEST_ROUTES or self.is_admin(token)


auth = AuthService()
