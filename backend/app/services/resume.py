"""Điểm dừng của tác vụ G-code, để "Tiếp tục từ dòng N" sau khi hủy / lỗi / mất kết nối.

Khi một tác vụ kết thúc không trọn vẹn (hủy, lỗi, mất kết nối), JobRunner ghi lại tệp G-code đã làm sạch
cùng số dòng đã được máy nhận (`done`) vào <thư mục dữ liệu>/resume.json (chỉ một chỗ: điểm dừng mới nhất).
Tác vụ chạy trọn thì xóa điểm dừng.

Vì sao không tiếp tục đúng tại dòng `done`:
  * `ok` của firmware chỉ nghĩa là dòng đã vào hàng đợi chuyển động, chưa chắc đã chạy; hủy cứng/Reset
    làm mất phần đang chờ. Nên lùi `RESUME_MARGIN` dòng cho chắc.
  * Máy đang ở chỗ khác (đã Home, bút đã nâng). Nên bắt đầu lại ở một dòng mà BÚT ĐANG NHẤC (đầu một nét),
    và dựng lại trạng thái cần thiết (đơn vị, G90, tốc độ F, vị trí XY) bằng vài dòng mở đầu: nâng bút,
    chạy tới đầu nét, đặt lại F. Vẽ chồng lên một đoạn đã vẽ thì vô hại; bỏ sót thì mất nét.
  * Gốc làm việc (WCO, đặt bằng Zero) phải như lúc dừng, nếu không bản vẽ lệch. Lưu WCO lúc dừng để so.
Chỉ khôi phục được khi phần đã chạy chỉ dùng G90, G20/G21, G0-G3, G4, F, X Y Z; thấy G91/G92/G10/G28/G30/G53/
G55-G59/M3/M4 thì từ chối (không đoán).
"""
from __future__ import annotations

import json
import re
import threading
import time

from .. import paths

RESUME_MARGIN = 64             # lùi ngần này dòng so với dòng máy đã nhận
Z_EPS = 1e-6
WCO_TOL = 0.01                 # mm; lệch hơn thế coi là đã đổi gốc làm việc
FILE_NAME = "resume.json"

_WORD = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
_UNSAFE_G = {91, 92, 10, 28, 30, 53, 55, 56, 57, 58, 59}
_UNSAFE_M = {3, 4}
_lock = threading.Lock()


class ResumeError(Exception):
    def __init__(self, code: str, message: str, status: int = 409) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _fmt(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


# --- tính điểm bắt đầu lại (hàm thuần, test không cần máy) -------------------------------
class _State:
    __slots__ = ("x", "y", "z", "feed", "inch")

    def __init__(self) -> None:
        self.x = self.y = self.z = self.feed = None
        self.inch = False

    def copy(self):
        other = _State()
        other.x, other.y, other.z, other.feed, other.inch = self.x, self.y, self.z, self.feed, self.inch
        return other


def _words(line: str):
    for letter, number in _WORD.findall(line.upper()):
        yield letter, float(number)


def _apply(state: _State, line: str) -> bool:
    """Cập nhật trạng thái theo một dòng. Trả False nếu dòng dùng thứ ta không dựng lại được."""
    ok = True
    for letter, num in _words(line):
        if letter == "G":
            g = round(num)
            if g in _UNSAFE_G:
                ok = False
            elif g == 20:
                state.inch = True
            elif g == 21:
                state.inch = False
        elif letter == "M" and round(num) in _UNSAFE_M:
            ok = False
        elif letter == "F":
            state.feed = num
        elif letter == "X":
            state.x = num
        elif letter == "Y":
            state.y = num
        elif letter == "Z":
            state.z = num
    return ok


def plan(lines: list[str], done: int, pen_feed: float, margin: int = RESUME_MARGIN) -> dict:
    """Chọn dòng bắt đầu lại và các dòng mở đầu.

    `done` = số dòng đầu tiên máy đã nhận. Trả {start, prefix, rewound, pen_known}; `start` là chỉ số
    (từ 0) của dòng đầu tiên sẽ chạy lại. Ném ResumeError nếu không khôi phục an toàn được.
    """
    total = len(lines)
    if total == 0 or done <= 0:
        return {"start": 0, "prefix": [], "rewound": 0, "pen_known": False}
    target = max(0, min(done, total) - margin)

    zs = set()
    for line in lines:
        for letter, num in _words(line):
            if letter == "Z":
                zs.add(round(num, 4))
    has_pen = len(zs) > 1
    z_up = max(zs) if has_pen else None

    state = _State()
    best_index, best_state = 0, state.copy()
    unsafe_at = None
    for i in range(target + 1):
        pen_is_up = (not has_pen) or (state.z is not None and abs(state.z - z_up) <= Z_EPS)
        if pen_is_up:
            best_index, best_state = i, state.copy()
        if i == target:
            break
        if not _apply(state, lines[i]) and unsafe_at is None:
            unsafe_at = i
    if unsafe_at is not None and unsafe_at < best_index:
        raise ResumeError(
            "not_resumable",
            f"Dòng {unsafe_at + 1} dùng lệnh không dựng lại được trạng thái (G91/G92/G10/G28/G53/M3...). "
            "Chạy lại từ đầu thay vì tiếp tục.")

    prefix: list[str] = []
    if best_index > 0:
        s = best_state
        prefix.append("G90 G20" if s.inch else "G90 G21")
        if has_pen and s.z is not None:
            prefix.append(f"G1 Z{_fmt(s.z)} F{_fmt(pen_feed)}")
        if s.x is not None or s.y is not None:
            words = ([f"X{_fmt(s.x)}"] if s.x is not None else []) + ([f"Y{_fmt(s.y)}"] if s.y is not None else [])
            prefix.append("G0 " + " ".join(words))
        if s.feed is not None:
            prefix.append(f"G1 F{_fmt(s.feed)}")
    return {"start": best_index, "prefix": prefix, "rewound": min(done, total) - best_index,
            "pen_known": has_pen}


# --- lưu / đọc điểm dừng ---------------------------------------------------------------
def _path():
    return paths.data_file(FILE_NAME)


def save(name: str, lines: list[str], done: int, state: str, error: dict | None,
         wco: list[float] | None) -> None:
    record = {"version": 1, "name": name, "state": state, "error": error,
              "total": len(lines), "done": max(0, min(done, len(lines))), "wco": wco,
              "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "lines": lines}
    with _lock:
        target = _path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".tmp")
            tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            tmp.replace(target)
        except OSError:
            pass            # không ghi được điểm dừng thì thôi, không làm hỏng việc đang dừng


def clear() -> None:
    with _lock:
        try:
            _path().unlink()
        except OSError:
            pass


def load() -> dict | None:
    with _lock:
        try:
            data = json.loads(_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    if (not isinstance(data, dict) or data.get("version") != 1
            or not isinstance(data.get("lines"), list) or not data["lines"]):
        return None
    return data


def describe(current_wco: list[float] | None, pen_feed: float) -> dict:
    """Thông tin gửi cho giao diện (không kèm toàn bộ dòng G-code)."""
    record = load()
    if record is None:
        return {"available": False}
    out = {"available": True, "name": record["name"], "state": record["state"], "error": record["error"],
           "total": record["total"], "done": record["done"], "created": record["created"],
           "wco_changed": _wco_changed(record.get("wco"), current_wco)}
    try:
        p = plan(record["lines"], record["done"], pen_feed)
        out.update(resumable=True, resume_line=p["start"] + 1, rewound=p["rewound"], reason=None)
    except ResumeError as exc:
        out.update(resumable=False, resume_line=None, rewound=0, reason=exc.code, message=exc.message)
    return out


def _wco_changed(saved, current) -> bool:
    if not saved or not current:
        return False            # không biết một trong hai: không chặn, giao diện vẫn nhắc người dùng
    return any(abs(a - b) > WCO_TOL for a, b in zip(saved, current))
