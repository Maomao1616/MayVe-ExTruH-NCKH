"""Phân tích các dòng phản hồi của FluidNC v4.1.1.

Định dạng dựa trên source (Report.cpp, Channel.cpp, Protocol.cpp). Cần đối chiếu
lại với log đọc từ board thật (Bước 4) trước khi tin hoàn toàn.
"""
from __future__ import annotations

from typing import Any

# Ký tự điều khiển tức thời (gửi một byte, không kèm xuống dòng).
STATUS_QUERY = b"?"
FEED_HOLD = b"!"
CYCLE_START = b"~"
SOFT_RESET = b"\x18"
JOG_CANCEL = b"\x85"

# Chỉ ghi những mã đã đối chiếu trong source v4.1.1 (Alarm.h, Error.h).
ALARM_NAMES = {
    1: "HardLimit", 2: "SoftLimit", 3: "AbortCycle", 4: "ProbeFailInitial",
    5: "ProbeFailContact", 6: "HomingFailReset", 7: "HomingFailDoor",
    8: "HomingFailPulloff", 9: "HomingFailApproach", 10: "SpindleControl",
    11: "StartupPin", 12: "HomingAmbiguousSwitch", 13: "HardStop",
    14: "Unhomed", 15: "Init", 16: "ExpanderReset", 17: "GCodeError",
    18: "ProbeHardLimit",
}
ERROR_NAMES = {
    3: "InvalidStatement", 8: "IdleError", 9: "SystemGcLock",
    10: "SoftLimitError", 11: "Overflow", 15: "TravelExceeded",
    16: "InvalidJogCommand", 20: "GcodeUnsupportedCommand",
}


def _floats(text: str) -> list[float]:
    return [float(v) for v in text.split(",") if v != ""]


def parse_status(line: str) -> dict[str, Any] | None:
    """Phân tích báo cáo trạng thái dạng <Idle|MPos:0,0,0|Bf:15,128|FS:0,0>.

    Trả về None nếu dòng không phải báo cáo trạng thái.
    """
    line = line.strip()
    if not (line.startswith("<") and line.endswith(">")):
        return None
    parts = line[1:-1].split("|")
    state, _, sub = parts[0].partition(":")
    out: dict[str, Any] = {
        "state": state, "substate": sub or None,
        "mpos": None, "wpos": None, "wco": None,
        "planner_free": None, "rx_free": None,
        "feed": None, "spindle": None, "sd": None, "pins": None,
    }
    for field in parts[1:]:
        key, _, val = field.partition(":")
        try:
            if key == "MPos":
                out["mpos"] = _floats(val)
            elif key == "WPos":
                out["wpos"] = _floats(val)
            elif key == "WCO":
                out["wco"] = _floats(val)
            elif key == "Bf":
                planner, rx = val.split(",")
                out["planner_free"], out["rx_free"] = int(planner), int(rx)
            elif key == "FS":
                feed, spindle = val.split(",")[:2]
                out["feed"], out["spindle"] = float(feed), float(spindle)
            elif key == "F":
                out["feed"] = float(val)
            elif key == "Pn":
                out["pins"] = val
            elif key == "SD":
                percent, _, name = val.partition(",")
                out["sd"] = {"percent": float(percent), "file": name}
        except ValueError:
            continue  # bỏ qua trường lỗi, giữ các trường còn lại
    return out


def classify_line(line: str) -> dict[str, Any]:
    """Phân loại một dòng phản hồi: ok, error, alarm, status, banner, message, other."""
    text = line.strip()
    if text == "ok":
        return {"kind": "ok"}
    if text.startswith("error:"):
        try:
            code = int(text[6:].split()[0])
        except (ValueError, IndexError):
            return {"kind": "other", "text": text}
        return {"kind": "error", "code": code, "name": ERROR_NAMES.get(code)}
    if text.startswith("ALARM:"):
        try:
            code = int(text[6:].split()[0])
        except (ValueError, IndexError):
            return {"kind": "other", "text": text}
        return {"kind": "alarm", "code": code, "name": ALARM_NAMES.get(code)}
    status = parse_status(text)
    if status is not None:
        return {"kind": "status", "status": status}
    if text.startswith("Grbl "):
        return {"kind": "banner", "text": text}
    if text.startswith("[MSG:"):
        return {"kind": "message", "text": text[5:].rstrip("]")}
    return {"kind": "other", "text": text}


def is_read_only_command(line: str) -> bool:
    """True nếu lệnh chỉ đọc thông tin, không làm máy chuyển động hay đổi cấu hình."""
    text = line.strip().upper().replace(" ", "")
    exact = {"$I", "$CMD", "$$", "$#", "$G", "$CD", "$SD/STATUS", "$FILES/LISTGCODE"}
    prefixes = ("$SD/LIST", "$LOCALFS/LIST", "$LOCALFS/SHOW=")
    return text in exact or text.startswith(prefixes)
