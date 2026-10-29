"""SimLink: máy FluidNC giả để phát triển khi chưa có board.

Hiệu chỉnh theo log board thật (MKS DLC32, FluidNC v4.1.1, MACHINE.md 29/10/2026):
  - bật lên: `[MSG:INFO: ALARM: Unhomed]` + `ALARM:14`, trạng thái Alarm (must_home);
    sau `$X` mọi G-code chạy được kể cả khi chưa Home (không có ALARM:14 về sau),
  - `!` khi Run -> Hold:1 -> Hold:0, `~` chạy tiếp; `!` khi Jog -> hủy jog, về Idle,
  - Reset khi Run/Jog/Hold:1 -> ALARM:3; khi Idle/Hold:0 -> Idle, không alarm;
    khi đang Alarm -> vẫn Alarm (chưa Home thì báo lại ALARM:14),
  - soft limit G-code: `ok` TRƯỚC rồi mới `ALARM:2`,
  - Home xong: `[MSG:Homed:XY]` rồi `ok`,
  - ALARM:1 (hard limit): `$X` trả ok nhưng vẫn Alarm, phải Reset trước.
Vẫn là XẤP XỈ: vận tốc không đổi (không gia tốc), cung G2/G3 đi thẳng tới điểm cuối.
Giới hạn mặc định lấy từ ConfigNCKH-16 ($130-$132): X 285, Y 318, Z 5 mm, must_home bật.
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
    BANNER = "Grbl 4.1 [FluidNC v4.1.1 (sim) '$' for help]"
    HOLD_DECEL_S = 0.1           # Hold:1 -> Hold:0 (~100 ms trên máy thật)
    SETTINGS = ("$10=1", "$13=0", "$20=1", "$21=1", "$22=1", "$23=7", "$30=0", "$32=0",
                "$100=80.000", "$101=80.000", "$102=100.000",
                "$110=6000.000", "$111=6000.000", "$112=3000.000",
                "$120=600.000", "$121=600.000", "$122=1000.000",
                "$130=285.000", "$131=318.000", "$132=5.000")
    _ALARM_TEXT = {1: "Hard Limit", 2: "Soft Limit", 3: "Abort Cycle",
                   6: "Homing Fail Reset", 14: "Unhomed"}
    # Alarm làm mất vị trí gốc (ước lượng).
    _LOSE_HOME = {1, 3, 6, 7, 8, 9, 12, 13, 14, 16}

    def __init__(self, travel=(285.0, 318.0, 5.0), rapid_mm_min=(6000.0, 6000.0, 3000.0),
                 planner_blocks: int = 16, rx_size: int = 128, speed: float = 1.0,
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
        self._raw = ""
        # Cấu hình giữ qua Reset (như trên flash), rút gọn từ `$CD` thật của ConfigNCKH-16.
        self._config_file = "ConfigNCKH-16.yaml"
        self._config = self._default_config(travel, rapid_mm_min, planner_blocks)
        self._files = {self._config_file: "\n".join(self._cfg_dump())}
        self._boot()

    @staticmethod
    def _default_config(travel, rapid, planner_blocks) -> dict:
        def axis(i, accel, homing_cycle, motor):
            return {"steps_per_mm": (80.0, 80.0, 100.0)[i], "max_rate_mm_per_min": float(rapid[i]),
                    "acceleration_mm_per_sec2": accel, "max_travel_mm": float(travel[i]),
                    "soft_limits": True,
                    "homing": {"cycle": homing_cycle, "positive_direction": False, "mpos_mm": 0.0,
                               "feed_mm_per_min": (150.0, 150.0, 50.0)[i],
                               "seek_mm_per_min": (1000.0, 1000.0, 200.0)[i]},
                    "motor0": motor}
        return {
            "board": "MKS DLC32 V2.1", "name": "MAYVE (sim)",
            "kinematics": {"CoreXY": {"x_scaler": 1.0}},
            "axes": {
                "homing_runs": 1,
                "X": axis(0, 600.0, 1, {"limit_neg_pin": "gpio.36", "hard_limits": True}),
                "Y": axis(1, 600.0, 1, {"limit_neg_pin": "gpio.35", "hard_limits": True}),
                "Z": axis(2, 1000.0, 0, {"hard_limits": False,
                                         "rc_servo": {"output_pin": "gpio.32", "pwm_hz": 50,
                                                      "min_pulse_us": 1350, "max_pulse_us": 1950}}),
            },
            "arc_tolerance_mm": 0.002, "junction_deviation_mm": 0.01,
            "planner_blocks": planner_blocks,
        }

    # --- trạng thái máy -------------------------------------------------------
    def _boot(self) -> None:
        self._pos = [0.0, 0.0, 0.0]
        self._state = "Alarm" if self._must_home else "Idle"
        self._reset_required = False         # ALARM:1: $X không đủ, phải Reset
        self._hold_sub = "0"
        self._hold_left = 0.0
        self._home_left = 0.0
        self._homed = False
        self._homed_axes: set[str] = set()   # trục đã Home
        self._home_axes = "XY"               # trục đang Home
        self._wco = [0.0, 0.0, 0.0]          # độ lệch hệ tọa độ làm việc (G10 L20 P1)
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
            if self._must_home:
                self._emit("[MSG:INFO: ALARM: Unhomed]")
                self._emit("ALARM:14")

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
            self._raw = self._input.popleft().strip()     # giữ nguyên hoa/thường cho tên tệp
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
            if code != 14:               # ALARM:14 không làm mất trục đã Home
                self._homed_axes.clear()
        self._emit(f"[MSG:INFO: ALARM: {self._ALARM_TEXT.get(code, code)}]")
        self._emit(f"ALARM:{code}")
        if code == 1:
            self._reset_required = True
            self._emit("[MSG:ERR: Reset to continue]")

    def simulate_hard_limit(self) -> None:
        """Giả lập chạm công tắc hành trình (chỉ để test)."""
        with self._lock:
            self._alarm(1)

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
            self._emit("[VER:4.1 FluidNC v4.1.1 (sim):]")
            self._emit("[MSG:Machine: SIM]")
            self._emit("ok")
        elif text == "$$":
            for line in self.SETTINGS:
                self._emit(line)
            self._emit("ok")
        elif text == "$G":
            dist = "G90" if self._absolute else "G91"
            self._emit(f"[GC:G{self._motion_mode} G54 G17 G21 {dist} G94 M5 M9 T0 "
                       f"F{self._feed:g} S0]")
            self._emit("ok")
        elif text in ("$X", "$ALARM/DISABLE"):
            if self._state == "Alarm" and not self._reset_required:
                self._state = "Idle"
                self._emit("[MSG:INFO: Caution: Unlocked]")
            self._emit("ok")
        elif re.fullmatch(r"\$H[XY]*", text):   # $H, $HX, $HY
            if self._state not in ("Idle", "Alarm") or self._reset_required:
                self._error(8)
            else:
                self._home_axes = text[2:] or "XY"
                self._state = "Home"
                self._home_left = self._homing_time
        elif text.startswith("$REPORT/"):
            self._emit("ok")
        elif self._config_command(text):
            pass
        else:
            self._error(3)

    # --- cấu hình (giống board thật: $CD, $/path, $Config/Filename, $LocalFS) ------
    @staticmethod
    def _cfg_text(value) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            return f"{value:.6f}"
        return str(value)

    def _cfg_dump(self, node=None, indent: int = 0) -> list[str]:
        node = self._config if node is None else node
        lines = []
        for key, value in node.items():
            if isinstance(value, dict):
                lines.append(f"{' ' * indent}{key}: ")
                lines += self._cfg_dump(value, indent + 2)
            else:
                lines.append(f"{' ' * indent}{key}: {self._cfg_text(value)}")
        return lines

    def _cfg_find(self, path: str):
        """(nút cha, khóa thật) cho path chữ thường, hoặc (None, None)."""
        node, parts = self._config, path.strip("/").lower().split("/")
        for part in parts[:-1]:
            key = next((k for k in node if isinstance(node[k], dict) and k.lower() == part), None)
            if key is None:
                return None, None
            node = node[key]
        key = next((k for k in node if not isinstance(node[k], dict) and k.lower() == parts[-1]), None)
        return (node, key) if key is not None else (None, None)

    def _config_command(self, text: str) -> bool:
        raw = self._raw
        if text == "$CONFIG/FILENAME":
            self._emit(f"$Config/Filename={self._config_file}")
        elif text == "$CD":
            for line in self._cfg_dump():
                self._emit(line)
        elif text.startswith("$CD="):
            name = raw.split("=", 1)[1].strip().split("/")[-1]
            self._files[name] = "\n".join(self._cfg_dump())
        elif text.startswith("$LOCALFS/SHOW="):
            name = raw.split("=", 1)[1].strip().split("/")[-1]
            if name not in self._files:
                self._error(65)
                return True
            for line in self._files[name].splitlines():
                self._emit(line)
        elif text == "$LOCALFS/LIST":
            for name, body in self._files.items():
                self._emit(f"[FILE: {name}|SIZE:{len(body)}]")
        elif text.startswith("$/"):
            path, _, value = raw[2:].partition("=")
            parent, key = self._cfg_find(path)
            if parent is None:
                self._error(3)
                return True
            if value:
                try:
                    parent[key] = type(parent[key])(float(value)) if not isinstance(parent[key], bool) \
                        else value.strip().lower() == "true"
                except ValueError:
                    self._error(3)
                    return True
                self._sync_from_config()
            else:
                current = parent[key]                    # thật: '$/axes/x/max_rate_mm_per_min=6000.000'
                shown = f"{current:.3f}" if isinstance(current, float) else self._cfg_text(current)
                self._emit(f"$/{path.strip('/')}={shown}")
        else:
            return False
        self._emit("ok")
        return True

    def _sync_from_config(self) -> None:
        axes = self._config["axes"]
        self._travel = tuple(float(axes[a]["max_travel_mm"]) for a in "XYZ")
        self._rapid = tuple(float(axes[a]["max_rate_mm_per_min"]) for a in "XYZ")

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
                target[i] = vals[axis] + self._wco[i] if absolute else target[i] + vals[axis]
        return target

    def _out_of_range(self, target: list[float]) -> bool:
        return any(t < -1e-9 or t > self._travel[i] + 1e-9 for i, t in enumerate(target))

    def _gcode(self, text: str) -> None:
        if self._state == "Alarm":
            self._error(9)
            return
        gs, vals, extra = [], {}, {}
        for letter, num in _WORD.findall(text):
            if letter == "G":
                gs.append(int(float(num)))
            elif letter in "XYZF":
                vals[letter] = float(num)
            elif letter in "LP":
                extra[letter] = float(num)
        if 10 in gs:
            # G10 L20 P1 X.. Y..: đặt gốc làm việc G54 tại vị trí hiện tại (không chuyển động)
            if extra.get("L") == 20 and extra.get("P") == 1:
                base = self._base_target()
                for i, axis in enumerate(_AXES):
                    if axis in vals:
                        self._wco[i] = base[i] - vals[axis]
                self._reports = 0  # báo WCO ngay ở lần báo cáo kế tiếp
                self._emit("ok")
            else:
                self._error(20)
            return
        for g in gs:
            if g in (2, 3):
                self._motion_mode = 1   # cung tròn: sim chỉ đi thẳng tới điểm cuối
            elif g == 90:
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
        # Máy thật: sau `$X`, G-code chạy được kể cả khi chưa Home (must_home chỉ chặn lúc bật).
        target = self._targets(vals, self._absolute)
        if self._out_of_range(target):
            self._emit("[MSG:INFO: Soft limit exceeded]")
            self._emit("ok")             # máy thật trả ok TRƯỚC rồi mới ALARM:2
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
        if self._state == "Run":
            self._state, self._hold_sub, self._hold_left = "Hold", "1", self.HOLD_DECEL_S
        elif self._state == "Jog":
            self._jog_cancel()           # máy thật: `!` khi Jog hủy jog, về Idle tại chỗ

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
        state = self._state
        moving = state in ("Run", "Jog", "Home") or (state == "Hold" and self._hold_sub == "1")
        self._input.clear()
        self._planner.clear()
        self._current = None
        self._home_left = 0.0
        self._reset_required = False
        if moving:
            self._alarm(6 if state == "Home" else 3)
        elif state == "Alarm":
            if self._must_home and not self._homed:
                self._alarm(14)          # máy thật: Reset trong Alarm khi chưa Home -> ALARM:14
        else:
            self._state = "Idle"         # Idle hoặc Hold:0: không alarm (đã thử trên board)
        self._emit(self.BANNER)

    # --- chuyển động ----------------------------------------------------------
    def _advance(self, dt: float) -> None:
        if self._state == "Home":
            self._home_left -= dt
            if self._home_left <= 0:
                for axis in self._home_axes:
                    self._pos[_AXES.index(axis)] = 0.0
                self._homed_axes |= set(self._home_axes)
                self._homed = {"X", "Y"} <= self._homed_axes
                self._state = "Idle"
                self._emit(f"[MSG:Homed:{self._home_axes}]")
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
            fields.append("WCO:" + ",".join(f"{v:.3f}" for v in self._wco))
        self._reports += 1
        return "<" + "|".join(fields) + ">"
