"""MachineService: quản lý kết nối, trạng thái máy và nhật ký.

Đây là nơi duy nhất giữ Link. Frontend chỉ gọi API, không chạm serial.
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque

from ..links.base import BaseLink, LinkError
from ..links.sim_link import SimLink
from ..protocol import (CYCLE_START, FEED_HOLD, JOG_CANCEL, SOFT_RESET, STATUS_QUERY,
                        classify_line, is_read_only_command)

REALTIME = {
    "status": STATUS_QUERY,
    "hold": FEED_HOLD,
    "resume": CYCLE_START,
    "reset": SOFT_RESET,
    "jog_cancel": JOG_CANCEL,
}
# Alarm làm mất vị trí gốc (ước lượng, cần xác minh bằng máy thật).
_LOSE_HOME = {1, 3, 6, 7, 8, 9, 12, 13, 14, 16}


class ServiceError(Exception):
    """Lỗi có mã ổn định để frontend tự quyết định cách hiển thị."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class MachineService:
    POLL_S = 0.25

    def __init__(self, allow_motion: bool | None = None) -> None:
        if allow_motion is None:
            allow_motion = os.environ.get("EXTRUXY_ALLOW_MOTION") == "1"
        self.allow_motion = allow_motion
        self._lock = threading.RLock()
        self._link: BaseLink | None = None
        self._poll_stop = threading.Event()
        self._poller: threading.Thread | None = None
        self._log: deque[dict] = deque(maxlen=500)
        self._seq = 0
        self._info: dict = {"mode": None, "port": None, "baud": None}
        self._lost_reason: str | None = None
        self._clear_machine()

    def _clear_machine(self) -> None:
        self._status: dict | None = None
        self._wco: list[float] | None = None
        self._last_alarm: dict | None = None
        self._last_error: dict | None = None
        self._banner: str | None = None
        # "Đã home" chỉ là ĐOÁN: FluidNC không có trường báo cáo riêng cho việc này.
        # Hai tín hiệu: (1) thấy trạng thái Home rồi Idle, (2) nhận `ok` sau khi ta gửi $H.
        self._homed_guess = False
        self._saw_home = False
        self._homing_pending = False
        self._updated_at: float | None = None

    # --- kết nối --------------------------------------------------------------
    def connect(self, mode: str, port: str | None = None, baud: int = 115200,
                sim_speed: float = 1.0) -> dict:
        with self._lock:
            if self._link is not None:
                raise ServiceError("already_connected", "Đã kết nối. Hãy ngắt kết nối trước.", 409)
            if mode == "sim":
                link: BaseLink = SimLink(speed=sim_speed)
            elif mode == "serial":
                if not port:
                    raise ServiceError("bad_request", "Chế độ serial cần chọn cổng (port).", 400)
                from ..links.serial_link import SerialLink
                link = SerialLink(port, baud)
            else:
                raise ServiceError("bad_request", f"Chế độ không hợp lệ: {mode}", 400)
            self._clear_machine()
            self._lost_reason = None
            link.add_listener(self._on_line)
            link.add_close_listener(self._on_link_closed)
            try:
                link.open()
            except LinkError as exc:
                raise ServiceError("link_error", str(exc), 502) from exc
            self._link = link
            self._info = {"mode": mode, "port": port if mode == "serial" else None,
                          "baud": baud if mode == "serial" else None}
            self._add_log("sys", "system", f"Đã kết nối ({mode})")
            self._poll_stop.clear()
            self._poller = threading.Thread(target=self._poll_loop, name="status-poller", daemon=True)
            self._poller.start()
            return self.connection_info()

    def disconnect(self) -> dict:
        with self._lock:
            link, self._link = self._link, None
            self._poll_stop.set()
        if link is not None:
            link.close()
            self._add_log("sys", "system", "Đã ngắt kết nối")
        return self.connection_info()

    def _on_link_closed(self, reason: str) -> None:
        with self._lock:
            if self._link is None:
                return
            self._link = None
            self._poll_stop.set()
            self._lost_reason = reason
            self._add_log("sys", "system", reason)

    def _poll_loop(self) -> None:
        while not self._poll_stop.wait(self.POLL_S):
            link = self._link
            if link is None:
                return
            try:
                link.write_realtime(STATUS_QUERY)
            except LinkError as exc:
                self._on_link_closed(str(exc))
                return

    def connection_info(self) -> dict:
        with self._lock:
            return {"connected": self._link is not None, **self._info,
                    "lost_reason": self._lost_reason,
                    "motion_unlocked": self._info["mode"] == "sim" or self.allow_motion}

    # --- nhận dữ liệu ---------------------------------------------------------
    def _on_line(self, line: str) -> None:
        info = classify_line(line)
        kind = info["kind"]
        with self._lock:
            if kind == "status":
                self._update_status(info["status"])
                return  # không ghi báo cáo trạng thái vào nhật ký (quá nhiều)
            if kind == "alarm":
                self._last_alarm = {"code": info["code"], "name": info["name"], "at": time.time()}
                if info["code"] in _LOSE_HOME:
                    self._homed_guess = False
                self._saw_home = False
                self._homing_pending = False
            elif kind == "ok":
                if self._homing_pending:  # chỉ đáng tin khi chưa có lệnh khác đang chờ ok
                    self._homed_guess, self._homing_pending = True, False
            elif kind == "error":
                self._last_error = {"code": info["code"], "name": info["name"], "at": time.time()}
            elif kind == "banner":
                self._banner = info["text"]
            self._add_log("rx", "device", line)

    def _update_status(self, st: dict) -> None:
        if st["wco"]:
            self._wco = st["wco"]
        wco = self._wco
        if wco:
            if st["wpos"] is None and st["mpos"]:
                st["wpos"] = [m - c for m, c in zip(st["mpos"], wco)]
            elif st["mpos"] is None and st["wpos"]:
                st["mpos"] = [w + c for w, c in zip(st["wpos"], wco)]
        state = st["state"]
        if state == "Home":
            self._saw_home = True
        elif state == "Idle" and self._saw_home:
            self._homed_guess, self._saw_home = True, False
        elif state == "Alarm":
            self._saw_home = False
        self._status = st
        self._updated_at = time.time()

    def _add_log(self, direction: str, source: str, text: str) -> None:
        self._seq += 1
        self._log.append({"seq": self._seq, "t": time.time(), "dir": direction,
                          "source": source, "text": text})

    # --- gửi lệnh -------------------------------------------------------------
    def _require_link(self) -> BaseLink:
        if self._link is None:
            raise ServiceError("not_connected", "Chưa kết nối bộ điều khiển.", 409)
        return self._link

    def send_line(self, text: str, source: str = "terminal") -> dict:
        text = text.strip()
        if not text or "\n" in text or "\r" in text:
            raise ServiceError("bad_request", "Lệnh phải là đúng một dòng, không rỗng.", 400)
        with self._lock:
            link = self._require_link()
            if self._info["mode"] == "serial" and not self.allow_motion and not is_read_only_command(text):
                raise ServiceError(
                    "motion_locked",
                    "Máy thật đang ở chế độ chỉ đọc. Chỉ cho phép lệnh đọc thông tin "
                    "(vd $I, $CMD, $G, $SD/ListJSON).", 403)
            self._add_log("tx", source, text)
            if text.replace(" ", "").upper() == "$H":
                self._homing_pending = True
            try:
                link.write_line(text)
            except LinkError as exc:
                raise ServiceError("link_error", str(exc), 502) from exc
        return {"sent": text}

    def send_realtime(self, action: str) -> dict:
        data = REALTIME.get(action)
        if data is None:
            raise ServiceError("bad_request", f"Hành động không hợp lệ: {action}", 400)
        with self._lock:
            link = self._require_link()
            if action != "status":
                self._add_log("tx", "realtime", action)
            if action == "reset":
                # Reset hủy mọi thứ đang chờ: không để `ok` đến muộn làm homed_guess bật sai.
                self._homing_pending = False
                self._saw_home = False
            try:
                link.write_realtime(data)
            except LinkError as exc:
                raise ServiceError("link_error", str(exc), 502) from exc
        return {"sent": action}

    # --- đọc dữ liệu ----------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "connection": self.connection_info(),
                "machine": dict(self._status) if self._status else None,
                "homed_guess": self._homed_guess,
                "last_alarm": self._last_alarm,
                "last_error": self._last_error,
                "banner": self._banner,
                "updated_at": self._updated_at,
            }

    def log_since(self, seq: int = 0) -> dict:
        with self._lock:
            entries = [e for e in self._log if e["seq"] > seq]
            return {"entries": entries, "last_seq": self._seq}


machine = MachineService()
