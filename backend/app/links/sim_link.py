"""SimLink: máy FluidNC giả để phát triển khi chưa có board.

Hành vi dựa trên source FluidNC v4.1.1 (đã đọc), nhưng đây chỉ là XẤP XỈ.
Các điểm chưa chắc, cần hiệu chỉnh bằng log thật ở Bước 4:
  - thời điểm và dạng `ok` ở một số lệnh,
  - phản hồi sau ALARM:14 (ở đây chỉ phát ALARM, không phát ok/error),
  - chuyển động dùng vận tốc không đổi (không mô phỏng gia tốc).
Giới hạn mặc định lấy từ ConfigNCKH-14: X 285, Y 318, Z 5 mm, must_home bật.
"""
from __future__ import annotations

import math
import re
import threading
import time
from collections import deque

from .base import BaseLink, LinkError

_WORD = re.compile(r"([A-Z])(-?\d*\.?\d+)")
_AXES = "XYZ"


class SimLink(BaseLink):
    kind = "sim"
    TICK_S = 0.02
    BANNER = "Grbl 3.9 [FluidNC v4.1.1 (sim)]"
    # Alarm làm mất vị trí gốc (ước lượng).
    _LOSE_HOME = {1, 3, 6, 7, 8, 9, 12, 13, 14, 16}

    def __init__(self, travel=(285.0, 318.0, 5.0), rapid_mm_min=(6000.0, 6000.0, 3000.0),
                 planner_blocks: int = 15, rx_size: int = 128, speed: float = 1.0,
                 must_home: bool = True, homing_time_s: float = 1.5) -> None:
        super().__init__()
        self._travel = travel
        self._rapid = rapid_mm_min
        self._planner_max = planner_blocks
        self._rx_size = rx_size
        self._speed = speed
        self._must_home = must_home
        self._homing_time = homing_time_s
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._open = False
        self._boot()

    # --- trạng thái máy -------------------------------------------------------
    def _boot(self) -> None:
        self._pos = [0.0, 0.0, 0.0]
        self._state = "Idle"
        self._hold_sub = "0"
        self._hold_left = 0.0
        self._home_left = 0.0
        self._homed = False
        self._absolute = True
        self._motion_mode = 0
        self._feed = 1000.0
        self._input: deque[str] = deque()
        self._planner: deque[dict] = deque()
        self._current: dict | None = None
        self._reports = 0

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        with self._lock:
            if self._open:
                return
            self._open = True
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="sim-link", daemon=True)
            self._thread.start()
            self._emit(self.BANNER)

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None
        self._open = False

    # --- giao diện ghi --------------------------------------------------------
    def write_line(self, text: str) -> None:
        if not self._open:
            raise LinkError("SimLink is not open")
        with self._lock:
            self._input.append(text)

    def write_realtime(self, data: bytes) -> None:
        if not self._open:
            raise LinkError("SimLink is not open")
        with self._lock:
            for byte in data:
                if byte == 0x3F:      # ?
                    self._emit(self._status_line())
                elif byte == 0x21:    # !
                    self._feed_hold()
                elif byte == 0x7E:    # ~
                    self._cycle_start()
                elif byte == 0x18:    # Ctrl-X
                    self._soft_reset()
                elif byte == 0x85:    # hủy jog
                    self._jog_cancel()

    # --- vòng lặp nền ---------------------------------------------------------
    def _run(self) -> None:
        last = time.monotonic()
        while not self._stop.is_set():
            time.sleep(self.TICK_S)
            now = time.monotonic()
            dt = (now - last) * self._speed
            last = now
            with self._lock:
                self._process_input()
                self._advance(dt)

    def _planner_free(self) -> int:
        used = len(self._planner) + (1 if self._current else 0)
        return max(0, self._planner_max - used)

    @staticmethod
    def _clean(raw: str) -> str:
        text = re.sub(r"\([^)]*\)", "", raw)
        return text.split(";")[0].strip().upper().replace(" ", "")

    @staticmethod
    def _is_motion(text: str) -> bool:
        if text.startswith("$J="):
            return True
        return not text.startswith("$") and bool(re.search(r"[XYZ]-?[\d.]", text))

    def _process_input(self) -> None:
        while self._input and self._state != "Home":
            text = self._clean(self._input[0])
            if self._is_motion(text) and self._planner_free() == 0:
                break  # planner đầy: giữ dòng lại, chưa trả ok (giống máy thật)
            self._input.popleft()
            self._handle(text)

    # --- xử lý lệnh -----------------------------------------------------------
    def _error(self, code: int) -> None:
        self._emit(f"error:{code}")

    def _alarm(self, code: int) -> None:
        self._input.clear()
        self._planner.clear()
        self._current = None
        self._state = "Alarm"
        if code in self._LOSE_HOME:
            self._homed = False
        self._emit(f"ALARM:{code}")

    def _handle(self, text: str) -> None:
        if not text:
            self._emit("ok")
        elif text.startswith("$J="):
            self._jog(text[3:])
        elif text.startswith("$"):
            self._dollar(text)
        else:
            self._gcode(text)

    def _dollar(self, text: str) -> None:
        if text == "$I":
            self._emit("[VER:3.9 FluidNC v4.1.1 (sim):]")
            self._emit("ok")
        elif text == "$X":
            if self._state == "Alarm":
                self._state = "Idle"
                self._emit("[MSG:INFO: Caution: Unlocked]")
            self._emit("ok")
        elif text == "$H":
            if self._state not in ("Idle", "Alarm"):
                self._error(8)
            else:
                self._state = "Home"
                self._home_left = self._homing_time
        elif text.startswith("$REPORT/"):
            self._emit("ok")
        else:
            self._error(3)

    def _base_target(self) -> list[float]:
        if self._planner:
            return list(self._planner[-1]["target"])
        if self._current:
            return list(self._current["target"])
        return list(self._pos)

    def _targets(self, vals: dict, absolute: bool) -> list[float]:
        target = self._base_target()
        for i, axis in enumerate(_AXES):
            if axis in vals:
                target[i] = vals[axis] if absolute else target[i] + vals[axis]
        return target

    def _out_of_range(self, target: list[float]) -> bool:
        return any(t < -1e-9 or t > self._travel[i] + 1e-9 for i, t in enumerate(target))

    def _gcode(self, text: str) -> None:
        if self._state == "Alarm":
            self._error(9)
            return
        gs, vals = [], {}
        for letter, num in _WORD.findall(text):
            if letter == "G":
                gs.append(int(float(num)))
            elif letter in "XYZF":
                vals[letter] = float(num)
        for g in gs:
            if g in (2, 3):
                self._error(20)
                return
            if g == 90:
                self._absolute = True
            elif g == 91:
                self._absolute = False
            elif g in (0, 1):
                self._motion_mode = g
        if "F" in vals:
            self._feed = vals["F"]
        if not any(a in vals for a in _AXES):
            self._emit("ok")
            return
        if self._must_home and not self._homed:
            self._emit("[MSG:INFO: Unhomed axes: XY]")
            self._alarm(14)
            return
        target = self._targets(vals, self._absolute)
        if self._out_of_range(target):
            self._alarm(2)
            return
        self._planner.append({"target": target, "rapid": self._motion_mode == 0,
                              "feed": self._feed, "jog": False})
        self._emit("ok")

    def _jog(self, text: str) -> None:
        if self._state == "Alarm":
            self._error(9)
            return
        if self._state not in ("Idle", "Jog"):
            self._error(8)
            return
        absolute = self._absolute
        vals = {}
        for letter, num in _WORD.findall(text):
            if letter == "G" and int(float(num)) == 90:
                absolute = True
            elif letter == "G" and int(float(num)) == 91:
                absolute = False
            elif letter in "XYZF":
                vals[letter] = float(num)
        if "F" not in vals or not any(a in vals for a in _AXES):
            self._error(16)
            return
        target = self._targets(vals, absolute)
        if self._out_of_range(target):
            self._error(15)
            return
        self._planner.append({"target": target, "rapid": False, "feed": vals["F"], "jog": True})
        self._emit("ok")

    # --- ký tự điều khiển tức thời -------------------------------------------
    def _feed_hold(self) -> None:
        if self._state in ("Run", "Jog"):
            self._state, self._hold_sub, self._hold_left = "Hold", "1", 0.2

    def _cycle_start(self) -> None:
        if self._state == "Hold":
            if self._current or self._planner:
                jog = (self._current or self._planner[0])["jog"]
                self._state = "Jog" if jog else "Run"
            else:
                self._state = "Idle"

    def _jog_cancel(self) -> None:
        if self._state == "Jog":
            self._planner.clear()
            self._current = None
            self._state = "Idle"

    def _soft_reset(self) -> None:
        moving = self._state in ("Run", "Jog", "Hold", "Home")
        self._input.clear()
        self._planner.clear()
        self._current = None
        self._home_left = 0.0
        if moving:
            self._emit_alarm_after_reset(6 if self._state == "Home" else 3)
        self._emit(self.BANNER)

    def _emit_alarm_after_reset(self, code: int) -> None:
        self._state = "Alarm"
        if code in self._LOSE_HOME:
            self._homed = False
        self._emit(f"ALARM:{code}")

    # --- chuyển động ----------------------------------------------------------
    def _advance(self, dt: float) -> None:
        if self._state == "Home":
            self._home_left -= dt
            if self._home_left <= 0:
                self._pos[0] = self._pos[1] = 0.0
                self._homed = True
                self._state = "Idle"
                self._emit("ok")
            return
        if self._state == "Hold":
            if self._hold_sub == "1":
                self._hold_left -= dt
                if self._hold_left <= 0:
                    self._hold_sub = "0"
            return
        if self._state == "Alarm":
            return
        if self._current is None and self._planner:
            self._current = self._planner.popleft()
            self._state = "Jog" if self._current["jog"] else "Run"
        if self._current is None:
            if self._state in ("Run", "Jog"):
                self._state = "Idle"
            return
        block = self._current
        rate_mm_min = self._rapid[0] if block["rapid"] else min(block["feed"], self._rapid[0])
        step = max(rate_mm_min, 1.0) / 60.0 * dt
        delta = [block["target"][i] - self._pos[i] for i in range(3)]
        dist = math.sqrt(sum(d * d for d in delta))
        if dist <= step:
            self._pos = list(block["target"])
            self._current = None
        else:
            for i in range(3):
                self._pos[i] += delta[i] / dist * step
        if self._current is None and not self._planner:
            self._state = "Idle"

    # --- báo cáo trạng thái ---------------------------------------------------
    def _status_line(self) -> str:
        state = f"Hold:{self._hold_sub}" if self._state == "Hold" else self._state
        mpos = ",".join(f"{v:.3f}" for v in self._pos)
        fields = [state, f"MPos:{mpos}", f"Bf:{self._planner_free()},{self._rx_size}",
                  f"FS:{self._feed if self._current else 0:.0f},0"]
        if self._reports % 10 == 0:
            fields.append("WCO:0.000,0.000,0.000")
        self._reports += 1
        return "<" + "|".join(fields) + ">"
