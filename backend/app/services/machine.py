"""MachineService: quản lý kết nối, trạng thái máy và nhật ký.

Đây là nơi duy nhất giữ Link. Frontend chỉ gọi API, không chạm serial.

Quy ước khóa (thứ tự cố định, tránh khóa chéo):
    _job_write_lock -> self._lock -> JobRunner._cond
Không bao giờ lấy _job_write_lock khi đang giữ self._lock.

Dừng an toàn (soft/hard) chạy trên luồng nền và giữ một `token` riêng. Khi token còn
hiệu lực, chỉ luồng dừng được gửi lệnh chuyển động; job mới và lệnh người dùng bị chặn.
Disconnect / mất kết nối xóa token, nên luồng dừng cũ không thể gửi lệnh vào phiên mới.
"""
from __future__ import annotations

import math
import os
import re
import secrets
import threading
import time
from collections import deque

from ..links.base import BaseLink, LinkError
from ..links.sim_link import SimLink
from .job import JobError, JobRunner, clean_gcode
from ..links.protocol import (CYCLE_START, FEED_HOLD, JOG_CANCEL, REALTIME_TEXT, SOFT_RESET,
                        STATUS_QUERY, classify_line, homing_axes, is_motion_free_command)

REALTIME = {
    "status": STATUS_QUERY,
    "hold": FEED_HOLD,
    "resume": CYCLE_START,
    "reset": SOFT_RESET,
    "jog_cancel": JOG_CANCEL,
}
# Alarm làm mất vị trí gốc (ước lượng, cần xác minh bằng máy thật).
_LOSE_HOME = {1, 3, 6, 7, 8, 9, 12, 13, 14, 16}

PEN_TOL_MM = 0.05          # sai số chấp nhận khi xác nhận Z đã tới đích
PEN_LIFT_MAX_S = 120.0     # chờ xác nhận nâng bút tối đa


class ServiceError(Exception):
    """Lỗi có mã ổn định để frontend tự quyết định cách hiển thị."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _num(value: float) -> str:
    """Số cho G-code: dạng thập phân cố định (không bao giờ ra '1e-05')."""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _work_z(status: dict) -> float | None:
    wpos = status.get("wpos")
    return wpos[2] if wpos and len(wpos) >= 3 else None


def _hold_done(st: dict) -> bool:
    """Feed Hold đã dừng hẳn (Hold:0), hoặc máy đã Idle/Alarm."""
    return st.get("state") in ("Idle", "Alarm") or (
        st.get("state") == "Hold" and str(st.get("substate") or "0") == "0")


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
        # Số thứ tự báo cáo trạng thái: tăng mãi, không reset (đáng tin hơn so sánh thời gian).
        self._status_seq = 0
        self._stop_token: object | None = None
        # query(): gom các dòng trả lời của MỘT lệnh tới `ok`/`error` (vd $CD ~200 dòng).
        self._capture: dict | None = None
        self._query_lock = threading.Lock()
        # Đồng bộ điểm ghi G-code với cancel để không lọt dòng sau khi hủy.
        self._job_write_lock = threading.Lock()
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
        # Số dòng đã gửi (ngoài tác vụ) chưa nhận `ok`/`error`. FluidNC trả đúng một
        # `ok`/`error` cho mỗi dòng; query() chờ số này về 0 để không nhận nhầm `ok`.
        self._pending_acks = 0
        # Board thật: sau ALARM:1 firmware báo "Reset to continue"; `$X` trả ok nhưng vẫn Alarm.
        self._reset_required = False
        self._updated_at: float | None = None
        self._status_mono: float | None = None

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
            self._stop_token = None
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
            self._abandon_stop("Disconnected")
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
            self._abandon_stop("Connection lost")
            self._relock("Connection lost")
            self._job.abort("link_lost", reason)
            self._add_log("sys", "system", reason)

    def _abandon_stop(self, why: str) -> None:      # gọi khi đang giữ self._lock
        if self._capture is not None:                # query() đang chờ: trả lỗi ngay
            self._capture["result"] = ("lost", {})
            self._capture["done"].set()
            self._capture = None
        if self._stop_token is not None:
            self._stop_token = None
            self._add_log("sys", "system",
                          f"{why}: safe stop abandoned; machine stop / pen lift NOT confirmed.")

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
            busy = self._job.active or self._stop_token is not None
            if busy or state not in (None, "Idle", "Alarm", "Sleep"):
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
                    "unlock_seconds_left": self._unlock_seconds_left()}

    # --- nhận dữ liệu ---------------------------------------------------------
    def _on_line(self, line: str) -> None:
        info = classify_line(line)
        kind = info["kind"]
        with self._lock:
            if kind == "status":
                self._update_status(info["status"])
                return  # không ghi báo cáo trạng thái vào nhật ký (quá nhiều)
            if self._capture is not None and kind not in ("alarm", "banner"):
                if self._take_captured(kind, info, line):
                    return
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
                self._pending_acks = max(0, self._pending_acks - 1)
                if self._homing_pending:  # chỉ đáng tin khi chưa có lệnh khác đang chờ ok
                    self._mark_homed()
                    self._homing_pending = False
            elif kind == "error":
                self._last_error = {"code": info["code"], "name": info["name"], "at": time.time()}
                self._homing_pending = False
                if not self._job.on_response("error", info):
                    self._pending_acks = max(0, self._pending_acks - 1)
            elif kind == "banner":
                self._banner = info["text"]
            elif kind == "other" and info["text"].startswith("[VER:"):
                # `$I` -> [VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]. Board thật không reset khi
                # mở cổng (DTR tắt) nên thường không có banner: dùng dòng này thay thế.
                self._banner = info["text"]
            elif kind == "message":
                self._on_message(info["text"])
            self._add_log("rx", "device", line)

    def _take_captured(self, kind: str, info: dict, line: str) -> bool:   # giữ self._lock
        """Dòng thuộc lệnh query() đang chờ. True nếu đã xử lý xong (không đi tiếp)."""
        cap = self._capture
        if kind in ("ok", "error"):
            cap["result"] = (kind, info)
            self._capture = None
            cap["done"].set()
            if kind == "error":
                self._last_error = {"code": info["code"], "name": info["name"], "at": time.time()}
                self._add_log("rx", "device", line)
            return True
        cap["lines"].append(line)       # không ghi nhật ký từng dòng (vd $CD ~200 dòng)
        return True

    def query(self, command: str, timeout: float = 5.0) -> list[str]:
        """Gửi MỘT lệnh `$...` và trả các dòng máy trả lời trước `ok`.

        Lỗi `error:N` -> ServiceError("device_error"). Không chạy khi đang chạy tác vụ,
        đang dừng an toàn hoặc đang chờ Home, vì khi đó không biết `ok` thuộc lệnh nào.
        """
        command = command.strip()
        with self._query_lock:
            # Chờ các dòng đã gửi trước đó (vd $I của giao diện) nhận xong `ok`.
            settle = time.monotonic() + 2.0
            while time.monotonic() < settle:
                with self._lock:
                    if self._pending_acks == 0:
                        break
                time.sleep(0.02)
            with self._lock:
                link = self._require_link()
                if self._job.active:
                    raise ServiceError("job_running", "Đang chạy tác vụ G-code.", 409)
                if self._homing_pending:
                    raise ServiceError("busy", "Máy đang Home, thử lại sau.", 409)
                self._guard_stop(None)
                if (self._info["mode"] == "serial" and not self.allow_motion
                        and not is_motion_free_command(command)):
                    raise ServiceError("motion_locked",
                                       "Máy thật đang ở chế độ chỉ đọc: mở khóa để ghi cấu hình.", 403)
                cap = {"lines": [], "done": threading.Event(), "result": None}
                self._capture = cap
                self._add_log("tx", "system", command)
                try:
                    link.write_line(command)
                except LinkError as exc:
                    self._capture = None
                    raise ServiceError("link_error", str(exc), 502) from exc
            if not cap["done"].wait(timeout):
                with self._lock:
                    if self._capture is cap:
                        self._capture = None
                raise ServiceError("timeout", f"Máy không trả lời lệnh {command}.", 504)
        kind, info = cap["result"]
        if kind == "lost":
            raise ServiceError("link_error", "Mất kết nối khi đang chờ máy trả lời.", 502)
        if kind == "error":
            raise ServiceError("device_error", f"{command} -> error:{info.get('code')}", 400)
        return cap["lines"]

    def _on_message(self, text: str) -> None:     # gọi khi đang giữ self._lock
        homed = re.fullmatch(r"Homed:([XYZ]+)", text.strip())
        if homed:
            # `[MSG:Homed:XY]`: firmware tự báo Home xong (đã thấy trên board thật).
            self._homing_axes = homed.group(1)
            self._mark_homed()
            self._homing_pending = False
            self._saw_home = False
        elif "Reset to continue" in text:
            self._reset_required = True
            if self._last_alarm is not None:
                self._last_alarm["reset_required"] = True

    def _mark_homed(self) -> None:
        """Ghi nhận trục vừa Home xong; chỉ coi là đã Home khi đủ cả X và Y."""
        self._homed_axes |= set(self._homing_axes)
        self._homed_guess = {"X", "Y"} <= self._homed_axes

    def _update_status(self, st: dict) -> None:
        if st["wco"]:
            self._wco = st["wco"]
        wco = self._wco
        if wco:
            # Chỉ quy đổi khi số trục khớp; zip() sẽ âm thầm cắt bớt nếu lệch.
            if st["wpos"] is None and st["mpos"] and len(st["mpos"]) == len(wco):
                st["wpos"] = [m - c for m, c in zip(st["mpos"], wco)]
            elif st["mpos"] is None and st["wpos"] and len(st["wpos"]) == len(wco):
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
        self._status_seq += 1
        self._updated_at = time.time()
        self._status_mono = time.monotonic()

    def _add_log(self, direction: str, source: str, text: str) -> None:
        self._seq += 1
        self._log.append({"seq": self._seq, "t": time.time(), "dir": direction,
                          "source": source, "text": text})

    # --- gửi lệnh -------------------------------------------------------------
    def _require_link(self) -> BaseLink:
        if self._link is None:
            raise ServiceError("not_connected", "Chưa kết nối bộ điều khiển.", 409)
        return self._link

    def _guard_stop(self, token: object | None) -> None:   # gọi khi đang giữ self._lock
        """Lúc đang dừng an toàn, chỉ luồng dừng (đúng token hiện hành) được gửi lệnh."""
        if token is None:
            if self._stop_token is not None:
                raise ServiceError("stopping",
                                   "Đang dừng an toàn (Hold/Reset/nâng bút). Chờ hoàn tất.", 409)
        elif token is not self._stop_token:
            raise ServiceError("stop_superseded",
                               "Trình tự dừng đã hết hiệu lực (kết nối đã thay đổi).", 409)

    def send_line(self, text: str, source: str = "terminal") -> dict:
        text = text.strip()
        # `?`, `!`, `~` gõ ở terminal là ký tự tức thời: đi thẳng tới máy, kể cả khi đang
        # chạy tác vụ (đó chính là lúc cần `!`). Gửi kèm xuống dòng sẽ sinh thêm một `ok`
        # lạ làm lệch việc đếm `ok` của tác vụ.
        action = REALTIME_TEXT.get(text)
        if action is not None:
            return self.send_realtime(action)
        return self._send_line(text, source)

    def _send_line(self, text: str, source: str, token: object | None = None) -> dict:
        text = text.strip()
        if not text or "\n" in text or "\r" in text:
            raise ServiceError("bad_request", "Lệnh phải là đúng một dòng, không rỗng.", 400)
        with self._lock:
            link = self._require_link()
            if self._job.active:
                # Mỗi dòng gửi thêm sẽ có `ok` riêng, làm lệch việc đếm `ok` của tác vụ.
                raise ServiceError(
                    "job_running",
                    "Đang chạy tác vụ G-code: chỉ gửi được ? ! ~ và các nút dừng.", 409)
            if self._capture is not None:
                raise ServiceError("busy", "Đang đọc/ghi cấu hình máy, thử lại sau giây lát.", 409)
            motion_free = is_motion_free_command(text)
            if not motion_free:
                self._guard_stop(token)
            if self._info["mode"] == "serial" and not self.allow_motion and not motion_free:
                raise ServiceError(
                    "motion_locked",
                    "Máy thật đang ở chế độ chỉ đọc. Chỉ cho phép lệnh đọc thông tin "
                    "(vd $I, $$, $G, $E) và $X.", 403)
            self._add_log("tx", source, text)
            if not motion_free:
                self._touch_motion()
            axes = homing_axes(text)
            if axes is not None:
                self._homing_pending = True
                self._homing_axes = axes
            try:
                link.write_line(text)
            except LinkError as exc:
                raise ServiceError("link_error", str(exc), 502) from exc
            self._pending_acks += 1
        return {"sent": text}

    def send_realtime(self, action: str) -> dict:
        return self._send_realtime(action)

    def _send_realtime(self, action: str, token: object | None = None) -> dict:
        data = REALTIME.get(action)
        if data is None:
            raise ServiceError("bad_request", f"Hành động không hợp lệ: {action}", 400)
        with self._lock:
            link = self._require_link()
            # Hold/Reset/hủy Jog/status luôn được phép (an toàn). Resume thì không được
            # chen vào trình tự dừng; luồng dừng cũ thì không được gửi gì vào phiên mới.
            if token is not None or action == "resume":
                self._guard_stop(token)
            if action != "status":
                self._add_log("tx", "realtime", action)
            if action == "reset":
                # Reset hủy mọi thứ đang chờ: không để `ok` đến muộn làm homed_guess bật sai.
                self._homing_pending = False
                self._saw_home = False
                self._reset_required = False
                self._pending_acks = 0            # Reset xóa bộ đệm: không còn `ok` nào sắp tới
                # Xóa lỗi/alarm cũ ngay lúc phát Reset; nếu firmware phát Alarm mới,
                # _on_line sẽ ghi nhận lại alarm đó sau Reset.
                self._last_error = None
                self._last_alarm = None
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
            self._guard_stop(None)
            if self._capture is not None:
                raise ServiceError("busy", "Đang đọc/ghi cấu hình máy, thử lại sau giây lát.", 409)
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
        """Hủy job.

        reset: Reset ngay như hành vi cũ.
        soft : Chờ buffer chạy hết; nếu timeout/trạng thái bất thường thì hard stop.
        hard : Feed Hold -> Reset -> mở khóa nếu cần -> xác nhận Idle -> nâng bút.

        Soft/hard chạy nền để không chặn API/UI. Snapshot trả về chỉ là trạng thái
        job, không khẳng định máy đã dừng hoặc bút đã lên; xem `stopping` và nhật ký.
        """
        if mode not in ("reset", "soft", "hard"):
            raise ServiceError("bad_request", f"Chế độ hủy không hợp lệ: {mode}", 400)
        if lift_z is not None and not math.isfinite(lift_z):
            raise ServiceError("bad_request", "lift_z phải là số hữu hạn.", 400)
        if not (math.isfinite(lift_feed) and lift_feed > 0):
            raise ServiceError("bad_request", "lift_feed phải là số dương hữu hạn.", 400)

        # Đặt token TRƯỚC khi hủy job: không có khoảnh khắc nào job đã hủy mà
        # start_job()/lệnh người dùng lại lọt vào trước trình tự dừng.
        token = object() if mode != "reset" else None
        with self._lock:
            self._guard_stop(None)
            self._stop_token = token
        try:
            self._job.cancel()
        except JobError as exc:
            self._end_stop(token)
            raise ServiceError(exc.code, exc.message, exc.status) from exc

        if mode == "reset":
            self._reset_now()
        else:
            threading.Thread(
                target=self._stop_sequence,
                args=(token, mode, lift_z, lift_feed),
                name="safe-stop",
                daemon=True,
            ).start()

        return self._job.snapshot()

    def _end_stop(self, token: object | None) -> None:
        with self._lock:
            if token is not None and self._stop_token is token:
                self._stop_token = None

    def _reset_now(self) -> None:
        """Reset tức thì; giữ nguyên hành vi của mode mặc định."""
        try:
            self.send_realtime("reset")
        except ServiceError as exc:
            self.log_system(f"Cancel: Reset failed ({exc.code}); machine stop is NOT confirmed.")

    def _stop_status(self, token: object) -> dict | None:
        """Trạng thái hiện tại nếu token còn hiệu lực và còn kết nối; ngược lại None."""
        with self._lock:
            if token is not self._stop_token or self._link is None:
                return None
            return dict(self._status) if isinstance(self._status, dict) else {}

    def _status_marker(self) -> int:
        """Lấy mốc báo cáo trước khi gửi lệnh; chỉ báo cáo có seq lớn hơn mới là 'mới'."""
        with self._lock:
            return self._status_seq

    def _wait_state(self, predicate, timeout: float, after: int | None = None,
                    token: object | None = None) -> dict | None:
        """Chờ báo cáo trạng thái MỚI (seq > after) thỏa predicate.

        predicate chạy khi đang giữ self._lock. Trả None nếu hết giờ, mất kết nối
        hoặc token dừng hết hiệu lực.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._link is None:
                    return None
                if token is not None and token is not self._stop_token:
                    return None
                status = self._status
                fresh = after is None or self._status_seq > after
                if fresh and isinstance(status, dict) and predicate(status):
                    return dict(status)
            time.sleep(0.05)
        return None

    def _stop_sequence(self, token: object, mode: str, lift_z: float | None,
                       lift_feed: float) -> None:
        """Trình tự soft/hard stop chạy trên luồng nền."""
        try:
            status = self._stop_status(token)
            if status is None:
                self.log_system(
                    "Safe stop: link unavailable or session changed; machine stop is NOT confirmed."
                )
                return

            state = status.get("state")
            if mode == "soft" and state in ("Hold", "Door", "Alarm"):
                self.log_system(
                    f"Soft stop: machine is {state}; falling back to hard stop."
                )
                mode = "hard"

            # Soft stop: cho máy chạy hết những lệnh đã được nhận vào buffer.
            if mode == "soft":
                self.log_system("Soft stop: waiting for queued moves to finish...")
                marker = self._status_marker()
                result = self._wait_state(
                    lambda st: st.get("state") in ("Idle", "Hold", "Door", "Alarm"),
                    timeout=120.0, after=marker, token=token,
                )
                if result is None:
                    if self._stop_status(token) is None:
                        self.log_system("Soft stop: session changed; stop abandoned.")
                        return
                    self.log_system(
                        "Soft stop timed out or status was lost; falling back to hard stop."
                    )
                    mode = "hard"
                elif result.get("state") != "Idle":
                    self.log_system(
                        f"Soft stop: machine entered {result.get('state')}; falling back to hard stop."
                    )
                    mode = "hard"
                else:
                    self.log_system("Soft stop: fresh Idle status confirmed.")

            # Hard stop cũng là đường dự phòng nếu soft stop không hoàn tất.
            if mode == "hard":
                if not self._hard_stop_sequence(token):
                    self.log_system(
                        "Safe stop: Idle was not confirmed. The pen was NOT lifted."
                    )
                    return

            if lift_z is None:
                self.log_system("Safe stop: done (no pen lift requested).")
                return

            # Sau soft stop hoặc hard stop, chỉ jog Z khi máy đang Idle.
            if self._send_pen_lift(token, lift_z, lift_feed):
                return

            # Giữ dự phòng của hành vi cũ: nếu nâng bút thất bại sau soft,
            # thử trình tự hard stop và thử nâng lại một lần.
            if mode == "soft" and self._stop_status(token) is not None:
                self.log_system(
                    "Soft stop: pen lift failed; falling back to hard stop and retrying."
                )
                if self._hard_stop_sequence(token):
                    self._send_pen_lift(token, lift_z, lift_feed)

        except ServiceError as exc:
            self.log_system(
                f"Safe stop failed ({exc.code}). The pen may still be DOWN."
            )
        except Exception as exc:
            self.log_system(
                f"Safe stop failed unexpectedly ({type(exc).__name__}). "
                "The pen may still be DOWN."
            )
        finally:
            self._end_stop(token)

    def _send_pen_lift(self, token: object, lift_z: float, lift_feed: float) -> bool:
        """Jog Z lên rồi chờ báo cáo Idle MỚI có Z (tọa độ làm việc) tới đích.

        True chỉ khi trạng thái máy xác nhận Z đã tới, không chỉ là lệnh đã gửi.
        """
        status = self._stop_status(token)
        if status is None or status.get("state") != "Idle":
            self.log_system(
                "Safe stop: machine is not confirmed Idle; cannot lift the pen."
            )
            return False

        z_text = _num(lift_z)
        start_z = _work_z(status)
        marker = self._status_marker()
        sent_at = time.time()
        self.log_system(f"Safe stop: sending pen lift jog to Z{z_text}.")
        try:
            self._send_line(f"$J=G90 G21 Z{z_text} F{_num(lift_feed)}", "system", token)
        except ServiceError as exc:
            self.log_system(
                f"Safe stop: pen lift command failed ({exc.code}); the pen may still be DOWN."
            )
            return False
        self.log_system(f"Safe stop: pen lift sent (Z{z_text}); waiting for confirmation.")

        # Thời gian chờ theo quãng đường thực tế, có dư cho gia tốc; không biết Z hiện tại thì chờ tối đa.
        if start_z is None:
            timeout = PEN_LIFT_MAX_S
        else:
            timeout = min(PEN_LIFT_MAX_S, 3.0 + abs(lift_z - start_z) / lift_feed * 60.0 * 2)

        def rejected() -> bool:                           # chạy khi đang giữ self._lock
            return self._last_error is not None and self._last_error["at"] >= sent_at

        def settled(st: dict) -> bool:
            if rejected() or st.get("state") == "Alarm":
                return True
            z = _work_z(st)
            return st.get("state") == "Idle" and z is not None and abs(z - lift_z) <= PEN_TOL_MM

        result = self._wait_state(settled, timeout=timeout, after=marker, token=token)
        if result is None:
            self.log_system(
                f"Safe stop: pen lift NOT confirmed (no fresh Idle status at Z{z_text} "
                f"within {timeout:.0f}s). The pen may still be DOWN."
            )
            return False
        with self._lock:
            error = self._last_error if rejected() else None
        if error is not None:
            self.log_system(
                f"Safe stop: pen lift rejected by firmware (error:{error['code']}). "
                "The pen may still be DOWN."
            )
            return False
        if result.get("state") == "Alarm":
            self.log_system("Safe stop: ALARM during pen lift. The pen may still be DOWN.")
            return False
        self.log_system(f"Safe stop: pen lift confirmed (Z{_num(_work_z(result))}).")
        return True

    def _hard_stop_sequence(self, token: object) -> bool:
        """Feed Hold -> Reset -> unlock nếu cần; True chỉ khi xác nhận Idle mới."""
        status = self._stop_status(token)
        if status is None:
            self.log_system("Hard stop: link unavailable or session changed.")
            return False

        state = status.get("state")

        # 1) Feed Hold, nếu máy đang chuyển động.
        if state in ("Run", "Jog"):
            self.log_system("Hard stop: sending Feed Hold.")
            marker = self._status_marker()
            try:
                self._send_realtime("hold", token)
            except ServiceError as exc:
                self.log_system(
                    f"Hard stop: Feed Hold failed ({exc.code}); attempting Reset."
                )
            else:
                if self._wait_state(_hold_done, timeout=3.0, after=marker, token=token) is None:
                    self.log_system(
                        "Hard stop: Feed Hold completion not confirmed; attempting Reset."
                    )

        status = self._stop_status(token)
        if status is None:
            self.log_system("Hard stop: link lost or session changed before Reset.")
            return False
        state = status.get("state")
        state_was_reset = False

        # 2) Reset; chờ báo cáo mới để không phụ thuộc trạng thái cache cũ.
        if state != "Alarm":
            state_was_reset = True
            self.log_system("Hard stop: sending Reset.")
            marker = self._status_marker()
            try:
                self._send_realtime("reset", token)
            except ServiceError as exc:
                self.log_system(f"Hard stop: Reset command failed ({exc.code}).")
                return False

            settled = self._wait_state(
                lambda st: st.get("state") in ("Idle", "Alarm"),
                timeout=5.0, after=marker, token=token,
            )
            if settled is None:
                self.log_system(
                    "Hard stop: no fresh Idle/Alarm status after Reset."
                )
                return False
            state = settled.get("state")

        # 3) Nếu đang Alarm, mở khóa rồi chờ Idle mới.
        if state == "Alarm" and not self._unlock_alarm(token, reset_sent=state_was_reset):
            return False

        # Luôn lấy một báo cáo Idle mới cuối cùng trước khi cho phép jog Z.
        marker = self._status_marker()
        try:
            self._send_realtime("status", token)
        except ServiceError as exc:
            self.log_system(f"Hard stop: status query failed ({exc.code}).")
            return False
        final_status = self._wait_state(
            lambda st: st.get("state") == "Idle",
            timeout=3.0, after=marker, token=token,
        )
        if final_status is None:
            self.log_system(
                "Hard stop: fresh Idle status was not confirmed; pen was NOT lifted."
            )
            return False

        self.log_system("Hard stop: fresh Idle status confirmed.")
        return True

    def _unlock_alarm(self, token: object, reset_sent: bool) -> bool:
        """Alarm -> Idle: `$X`; nếu firmware đòi Reset trước (ALARM:1) hoặc `$X` không
        đủ thì Reset rồi `$X` lại một lần. True chỉ khi thấy báo cáo Idle mới."""
        for attempt in (1, 2):
            with self._lock:
                need_reset = self._reset_required
            if need_reset or attempt == 2:
                if reset_sent and not need_reset:
                    break                       # đã Reset ở bước trước, thử lại cũng vô ích
                self.log_system("Hard stop: firmware needs Reset before $X; sending Reset."
                                if need_reset else
                                "Hard stop: $X did not clear the Alarm; sending Reset.")
                marker = self._status_marker()
                try:
                    self._send_realtime("reset", token)
                except ServiceError as exc:
                    self.log_system(f"Hard stop: Reset command failed ({exc.code}).")
                    return False
                if self._wait_state(lambda st: st.get("state") in ("Idle", "Alarm"),
                                    timeout=5.0, after=marker, token=token) is None:
                    self.log_system("Hard stop: no fresh status after Reset.")
                    return False
                reset_sent = True
            self.log_system("Hard stop: sending $X.")
            marker = self._status_marker()
            try:
                self._send_line("$X", "system", token)
            except ServiceError as exc:
                self.log_system(f"Hard stop: unlock failed ({exc.code}).")
                return False
            if self._wait_state(lambda st: st.get("state") == "Idle",
                                timeout=3.0, after=marker, token=token) is not None:
                return True
        self.log_system("Hard stop: Idle was not confirmed after $X; the pen was NOT lifted.")
        return False

    # JobRunner gọi các hàm dưới đây từ luồng của nó.
    def log_system(self, text: str) -> None:
        with self._lock:
            self._add_log("sys", "system", text)

    def job_write(self, line: str, job_id: int) -> None:
        """Ghi một dòng của job chỉ khi job vẫn còn sống.

        _job_write_lock được dùng chung với JobRunner.cancel(): thao tác check-live
        và ghi cổng serial là một vùng tới hạn so với thao tác cancel.
        """
        with self._job_write_lock:
            with self._lock:
                if not self._job.is_live(job_id):
                    return
                self._require_link().write_line(line)   # không ghi log từng dòng

    def job_hold(self) -> None:
        """Feed Hold khi tác vụ lỗi/timeout, rồi chờ báo cáo mới xác nhận máy đã dừng.

        Trạng thái job `failed` KHÔNG chứng minh máy đã dừng; nhật ký nói rõ điều đó.
        """
        marker = self._status_marker()
        try:
            self.send_realtime("hold")
        except ServiceError as exc:
            self.log_system(f"Job: Feed Hold failed ({exc.code}); machine stop is NOT confirmed.")
            return
        if self._wait_state(_hold_done, timeout=3.0, after=marker) is None:
            self.log_system("Job: Feed Hold sent but stop is NOT confirmed (no fresh status).")
        else:
            self.log_system("Job: Feed Hold confirmed.")

    def machine_state(self) -> tuple[str | None, int, float | None]:
        """(trạng thái, seq báo cáo, số giây từ báo cáo gần nhất)."""
        with self._lock:
            state = self._status["state"] if self._status else None
            age = None if self._status_mono is None else time.monotonic() - self._status_mono
            return state, self._status_seq, age

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
                "stopping": self._stop_token is not None,
                "job": self._job.snapshot(),
            }

    def log_since(self, seq: int = 0) -> dict:
        with self._lock:
            entries = [e for e in self._log if e["seq"] > seq]
            return {"entries": entries, "last_seq": self._seq}


machine = MachineService()
