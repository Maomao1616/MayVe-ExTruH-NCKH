"""MachineService: quản lý kết nối, trạng thái máy và nhật ký.

Đây là nơi duy nhất giữ Link. Frontend chỉ gọi API, không chạm serial.
"""
from __future__ import annotations

import os 
import secrets
import re
import threading
import time
from collections import deque
from tracemalloc import stop

from ..links.base import BaseLink, LinkError
from ..links.sim_link import SimLink
from .job import JobError, JobRunner, clean_gcode
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
        self._motion_permanent = bool(allow_motion)
        self._unlock_forbidden = os.environ.get("EXTRUXY_NO_UNLOCK") == "1"
        self._unlock_pin = os.environ.get("EXTRUXY_UNLOCK_PIN") or None
        try:
            self._unlock_minutes = float(os.environ.get("EXTRUXY_UNLOCK_MINUTES", "15"))
        except ValueError:
            self._unlock_minutes = 15.0
        self._motion_activity = 0.0
        self._lock = threading.RLock()
        self._link: BaseLink | None = None
        self._poll_stop = threading.Event()
        self._poller: threading.Thread | None = None
        self._log: deque[dict] = deque(maxlen=500)
        self._seq = 0
        self._info: dict = {"mode": None, "port": None, "baud": None}
        self._lost_reason: str | None = None
        self._job = JobRunner(self)
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
        self._homed_axes: set[str] = set()   # trục đã Home (đoán); đủ X và Y mới coi là đã Home
        self._homing_axes = "XY"             # trục của lệnh Home gần nhất ($H, $HX, $HY)
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
            self._job.reset()
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
            self._add_log("sys", "system", f"Connected ({mode})")
            self._poll_stop = threading.Event()
            self._poller = threading.Thread(target=self._poll_loop, args=(self._poll_stop,),
                                name="status-poller", daemon=True)
            self._poller.start()

            
            return self.connection_info()
        
        

    def disconnect(self) -> dict:
        with self._lock:
            link, self._link = self._link, None
            self._poll_stop.set()
            self._relock("Disconnected")
            
        if link is not None:
            self._job.abort("disconnected", "Disconnected")
            link.close()
            self._add_log("sys", "system", "Disconnected")
        return self.connection_info()

    def _on_link_closed(self, reason: str) -> None:
        with self._lock:
            if self._link is None:
                return
            self._link = None
            self._poll_stop.set()
            self._lost_reason = reason
            self._relock("Connection lost")
            self._job.abort("link_lost", reason)
            self._add_log("sys", "system", reason)

    def _poll_loop(self, stop: threading.Event) -> None:
        while not stop.wait(self.POLL_S):
            self._check_relock()
            link = self._link
            if link is None:
                return
            try:
                link.write_realtime(STATUS_QUERY)
            except LinkError as exc:
                self._on_link_closed(str(exc))
                return
            
    def set_motion(self, on: bool, pin: str | None = None) -> dict:
        with self._lock:
            if on:
                if self._unlock_forbidden:
                    raise ServiceError("unlock_forbidden", "Mở khóa từ giao diện đã bị tắt.", 403)
                if self._unlock_pin is not None and not secrets.compare_digest(
                        (pin or "").encode(), self._unlock_pin.encode()):
                    raise ServiceError("bad_pin", "Sai mã PIN.", 403)
                self.allow_motion = True
                self._motion_activity = time.time()
                self._add_log("sys", "system", "Motion unlocked")
            else:
                if self._motion_permanent:
                    raise ServiceError("unlock_permanent",
                                    "Máy được mở khóa từ lúc khởi động.", 409)
                self._relock("Motion locked")
            return self.connection_info()

    def _relock(self, why: str) -> None:       # gọi khi đang giữ self._lock
        if self.allow_motion and not self._motion_permanent:
            self.allow_motion = False
            self._add_log("sys", "system", f"{why}: motion locked")

    def _touch_motion(self) -> None:
        self._motion_activity = time.time()

    def _unlock_seconds_left(self) -> int | None:
        if not self.allow_motion or self._motion_permanent or self._unlock_minutes <= 0:
            return None
        return max(0, int(self._unlock_minutes * 60 - (time.time() - self._motion_activity)))

    def _check_relock(self) -> None:
        with self._lock:
            if not self.allow_motion or self._motion_permanent or self._unlock_minutes <= 0:
                return
            state = self._status["state"] if self._status else None
            if self._job.active or state not in (None, "Idle", "Alarm", "Sleep"):
                self._motion_activity = time.time()
                return
            if time.time() - self._motion_activity > self._unlock_minutes * 60:
                self._relock("Idle timeout")

    def connection_info(self) -> dict:
        with self._lock:
            return {"connected": self._link is not None, **self._info,
                    "lost_reason": self._lost_reason,
                    "motion_unlocked": self._info["mode"] == "sim" or self.allow_motion,
                    "motion_permanent": self._motion_permanent,
                    "unlock_available": not self._unlock_forbidden,
                    "unlock_needs_pin": self._unlock_pin is not None,
                    "unlock_seconds_left": self._unlock_seconds_left()  
}
    
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
                    # ALARM:14 (chưa Home) chỉ làm mất trục đã Home khi ta đang đoán sai.
                    if info["code"] != 14 or self._homed_guess:
                        self._homed_axes.clear()
                    self._homed_guess = False
                self._saw_home = False
                self._homing_pending = False
                self._job.on_alarm(info["code"])
            elif kind == "ok":
                if self._job.on_response("ok", info):
                    return  # `ok` của dòng G-code trong tác vụ: không ghi nhật ký (quá nhiều)
                if self._homing_pending:  # chỉ đáng tin khi chưa có lệnh khác đang chờ ok
                    self._mark_homed()
                    self._homing_pending = False
            elif kind == "error":
                self._last_error = {"code": info["code"], "name": info["name"], "at": time.time()}
                self._homing_pending = False        # thêm
                self._job.on_response("error", info)
            elif kind == "banner":
                self._banner = info["text"]
            self._add_log("rx", "device", line)

    def _mark_homed(self) -> None:
        """Ghi nhận trục vừa Home xong; chỉ coi là đã Home khi đủ cả X và Y."""
        self._homed_axes |= set(self._homing_axes)
        self._homed_guess = {"X", "Y"} <= self._homed_axes

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
            self._mark_homed()
            self._saw_home = False
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
            if self._job.active:
                raise ServiceError(
                    "job_running",
                    "Đang chạy tác vụ G-code. Hãy dừng tác vụ trước khi gửi lệnh khác.", 409)
            if self._info["mode"] == "serial" and not self.allow_motion and not is_read_only_command(text):
                raise ServiceError(
                    "motion_locked",
                    "Máy thật đang ở chế độ chỉ đọc. Chỉ cho phép lệnh đọc thông tin "
                    "(vd $I, $CMD, $G, $SD/ListJSON).", 403)
            self._add_log("tx", source, text)
            if not is_read_only_command(text):
                self._touch_motion()
            command = text.replace(" ", "").upper()
            if re.fullmatch(r"\$H[XY]*", command):   # $H, $HX, $HY
                self._homing_pending = True
                self._homing_axes = command[2:] or "XY"
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

    # --- tác vụ G-code (gửi từng dòng, xem services/job.py) ---------------------
    def start_job(self, name: str, lines: list[str]) -> dict:
        try:
            cleaned = clean_gcode(lines)           # ngoài khóa: tệp lớn có thể mất một lúc
        except JobError as exc:
            raise ServiceError(exc.code, exc.message, exc.status) from exc
        with self._lock:
            self._require_link()
            if self._info["mode"] == "serial" and not self.allow_motion:
                raise ServiceError("motion_locked", "Máy thật đang ở chế độ chỉ đọc.", 403)
            state = self._status["state"] if self._status else None
            if state != "Idle":
                raise ServiceError("not_idle", f"Máy phải ở trạng thái Idle (hiện tại: {state}).", 409)
            try:
                self._touch_motion()
                return self._job.start(name, cleaned, pre_cleaned=True)
            except JobError as exc:
                raise ServiceError(exc.code, exc.message, exc.status) from exc

    def cancel_job(self, mode: str = "reset", lift_z: float | None = None,
                   lift_feed: float = 1000.0) -> dict:
        if mode not in ("reset", "soft", "hard"):
            raise ServiceError("bad_request", f"mode không hợp lệ: {mode}", 400)

        # 1) Dừng gửi dòng mới (không Reset — Reset là bước riêng)
        try:
            self._job.cancel()
        except JobError as exc:
            raise ServiceError(exc.code, exc.message, exc.status) from exc

        # 2) Xử lý theo mode
        if mode == "reset":
            self._reset_now()
        elif mode == "soft":
            if not self._soft_stop(lift_z, lift_feed):
                # Không thể chạy nốt buffer → rơi về hard
                self._hard_stop(lift_z, lift_feed)
        else:  # hard
            self._hard_stop(lift_z, lift_feed)

        return self._job.snapshot()

    def _reset_now(self) -> None:
        """Reset ngay (hành vi cũ)."""
        try:
            self.send_realtime("reset")
        except ServiceError:
            pass

    def _soft_stop(self, lift_z: float | None, lift_feed: float) -> bool:
        self.log_system("Soft stop: waiting for buffer to finish...")
        deadline = time.time() + 60.0
        while time.time() < deadline:
            state = self.machine_state()[0]
            if state == "Idle":
                self.log_system("Soft stop: machine is Idle.")
                break
            if state in ("Alarm", "Hold"):
                self.log_system(f"Soft stop: machine is {state}, falling back to hard stop.")
                return False
            time.sleep(0.1)
        else:
            self.log_system("Soft stop: timeout, falling back to hard stop.")
            return False

        if lift_z is not None:
            self.log_system(f"Soft stop: lifting pen to Z{lift_z}.")
            try:
                self.send_line(f"$J=G90 G21 Z{lift_z} F{lift_feed}")
            except ServiceError as exc:
                self.log_system(f"Soft stop: failed to lift pen: {exc}")
                return False
        return True

    def _hard_stop(self, lift_z: float | None, lift_feed: float) -> None:
        self.log_system("Hard stop: starting sequence...")
        
        # 1) Feed Hold
        state = self.machine_state()[0]
        if state in ("Run", "Jog"):
            self.log_system("Hard stop: sending Feed Hold.")
            try: self.send_realtime("hold")
            except ServiceError: pass
            deadline = time.time() + 3.0
            while time.time() < deadline:
                if self.machine_state()[0] in ("Hold", "Alarm", "Idle"):
                    break
                time.sleep(0.1)

        # 2) Reset
        state = self.machine_state()[0]
        if state != "Alarm":
            self.log_system("Hard stop: sending Reset.")
            try: self.send_realtime("reset")
            except ServiceError: pass
            deadline = time.time() + 5.0  # Tăng lên 5s để đợi board khởi động lại
            while time.time() < deadline:
                if self.machine_state()[0] == "Alarm":
                    break
                time.sleep(0.1)

        # 3) $X
        if self.machine_state()[0] == "Alarm":
            self.log_system("Hard stop: sending $X.")
            try: self.send_line("$X")
            except ServiceError: return
            deadline = time.time() + 5.0  # Tăng lên 5s
            while time.time() < deadline:
                if self.machine_state()[0] == "Idle":
                    break
                time.sleep(0.1)

        # 4) Jog Z
        if lift_z is not None:
            if self.machine_state()[0] == "Idle":
                self.log_system(f"Hard stop: lifting pen to Z{lift_z}.")
                try: self.send_line(f"$J=G90 G21 Z{lift_z} F{lift_feed}")
                except ServiceError: pass
            else:
                self.log_system("Hard stop: machine is not Idle, cannot lift pen.")


    # JobRunner gọi các hàm dưới đây từ luồng của nó.
    def log_system(self, text: str) -> None:
        with self._lock:
            self._add_log("sys", "system", text)

    def job_write(self, line: str) -> None:
        with self._lock:
            self._require_link().write_line(line)   # không ghi nhật ký từng dòng

    def job_hold(self) -> None:
        try:
            self.send_realtime("hold")
        except ServiceError:
            pass

    def machine_state(self) -> tuple[str | None, float | None]:
        with self._lock:
            return (self._status["state"] if self._status else None), self._updated_at

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
                "job": self._job.snapshot(),
            }

    def log_since(self, seq: int = 0) -> dict:
        with self._lock:
            entries = [e for e in self._log if e["seq"] > seq]
            return {"entries": entries, "last_seq": self._seq}


machine = MachineService()
