"""Phân tích các dòng phản hồi của FluidNC v4.1.1.

Định dạng dựa trên source (Report.cpp, Channel.cpp, Protocol.cpp). Cần đối chiếu
lại với log đọc từ board thật (Bước 4) trước khi tin hoàn toàn.
"""
from __future__ import annotations

import math
from typing import Any

# Ký tự điều khiển tức thời (gửi một byte, không kèm xuống dòng).
STATUS_QUERY = b"?"
FEED_HOLD = b"!"
CYCLE_START = b"~"
SOFT_RESET = b"\x18"
JOG_CANCEL = b"\x85"

# Tên mã theo `$A` và `$E` đọc từ board thật (MKS DLC32, FluidNC v4.1.1, 29/10/2026).
ALARM_NAMES = {
    1: "HardLimit", 2: "SoftLimit", 3: "AbortCycle", 4: "ProbeFailInitial",
    5: "ProbeFailContact", 6: "HomingFailReset", 7: "HomingFailDoor",
    8: "HomingFailPulloff", 9: "HomingFailApproach", 10: "SpindleControl",
    11: "StartupPin", 12: "HomingAmbiguousSwitch", 13: "HardStop",
    14: "Unhomed", 15: "Init", 16: "ExpanderReset", 17: "GCodeError",
    18: "ProbeHardLimit",
}
ERROR_NAMES = {
    1: "ExpectedCommandLetter", 2: "BadNumberFormat", 3: "InvalidStatement",
    4: "NegativeValue", 5: "SettingDisabled", 6: "StepPulseTooShort",
    7: "FailedToReadSettings", 8: "IdleError", 9: "SystemGcLock",
    10: "SoftLimitError", 11: "LineTooLong", 12: "MaxStepRateExceeded",
    13: "CheckDoor", 14: "LineTooLong", 15: "TravelExceeded",
    16: "InvalidJogCommand", 17: "LaserModeRequiresPwm", 18: "NoHomingCycle",
    19: "SingleAxisHoming", 20: "GcodeUnsupportedCommand",
    21: "GcodeModalGroupViolation", 22: "GcodeUndefinedFeedRate",
    23: "GcodeValueNotInteger", 24: "GcodeAxisCommandConflict",
    25: "GcodeWordRepeated", 26: "GcodeNoAxisWords", 27: "GcodeInvalidLineNumber",
    28: "GcodeValueWordMissing", 29: "GcodeUnsupportedCoordSys",
    30: "GcodeG53InvalidMotionMode", 31: "GcodeAxisWordsExist",
    32: "GcodeNoAxisWordsInPlane", 33: "GcodeInvalidTarget",
    34: "GcodeArcRadiusError", 35: "GcodeNoOffsetsInPlane", 36: "GcodeUnusedWords",
    37: "GcodeG43DynamicAxisError", 38: "GcodeMaxValueExceeded",
    39: "PParamMaxExceeded", 40: "CheckControlPins",
    60: "FsFailedMount", 61: "FsFailedRead", 62: "FsFailedOpenDir",
    63: "FsDirNotFound", 64: "FsFileEmpty", 65: "FsFileNotFound",
    66: "FsFailedOpenFile", 67: "FsFailedBusy", 68: "FsFailedDelDir",
    69: "FsFailedDelFile", 70: "FsFailedRenameFile",
    80: "NumberRange", 81: "InvalidValue", 82: "FsFailedCreateFile",
    83: "FsFailedFormat", 90: "MessageFailed", 100: "NvsSetFailed",
    101: "NvsGetStatsFailed", 110: "AuthenticationFailed", 111: "Eol", 112: "Eof",
    113: "Reset", 114: "NoData", 115: "Deferred", 120: "AnotherInterfaceBusy",
    130: "JogCancelled", 150: "BadPinSpecification", 151: "BadRuntimeConfigSetting",
    152: "ConfigurationInvalid", 160: "UploadFailed", 161: "DownloadFailed",
    162: "ReadOnlySetting", 170: "ExpressionDivideByZero",
    171: "ExpressionInvalidArgument", 173: "ExpressionUnknownOp",
    174: "ExpressionArgumentOutOfRange", 175: "ExpressionSyntaxError",
    176: "FlowControlSyntaxError", 177: "FlowControlNotExecutingMacro",
    178: "FlowControlOutOfMemory", 179: "FlowControlStackOverflow",
    180: "ParameterAssignmentFailed", 181: "GcodeValueWordInvalid",
}

# Một ký tự gõ ở terminal được gửi như ký tự tức thời (không kèm xuống dòng).
REALTIME_TEXT = {"?": "status", "!": "hold", "~": "resume"}

# Lệnh chỉ đọc, theo danh sách `$CMD` thật (cả tên ngắn và tên dài, viết HOA, bỏ dấu cách).
_READ_EXACT = {
    "$", "$HELP", "$I", "$BUILD/INFO", "$CMD", "$COMMANDS/LIST",
    "$$", "$GRBLSETTINGS/LIST", "$#", "$GCODE/OFFSETS", "$G", "$GCODE/MODES",
    "$CD", "$CONFIG/DUMP", "$E", "$ERRORS/LIST", "$A", "$ALARMS/LIST",
    "$S", "$SETTINGS/LIST", "$SC", "$SETTINGS/LISTCHANGED", "$L", "$GRBLNAMES/LIST",
    "$LIMITS", "$LIMITS/SHOW", "$SS", "$STARTUP/SHOW", "$HEAP", "$HEAP/SHOW",
    "$GS", "$GRBL/SHOW", "$T", "$STATE", "$CI", "$CHANNEL/INFO", "$V", "$SETTINGS/STATS",
    "$BS", "$BACKTRACE/SHOW", "$GD", "$GPIO/DUMP", "$PL", "$PARAMETERS/LIST",
    "$ESP", "$ESP0", "$WEBUI/HELP", "$ESP400", "$WEBUI/LIST", "$ESP410", "$WIFI/LISTAPS",
    "$ESP420", "$SYSTEM/STATS", "$ESP800", "$FIRMWARE/INFO", "$ESP111", "$SYSTEM/IP",
    "$WIFI/STATUS", "$SD/STATUS", "$ESP200", "$ESP210", "$LOCALFS/SIZE", "$ESP720",
    "$LOCALFS/HASHES", "$FILES/LISTGCODE", "$CONFIG/FILENAME",
}
_READ_PREFIXES = ("$SD/LIST", "$LOCALFS/LIST", "$LOCALFS/SHOW=", "$SD/SHOW=", "$ESP221=",
                  "$FILES/LISTGCODE=", "$FILE/SHOWHASH=", "$FILE/SHOWSOME=", "$GPIO/READ")
# Không làm máy chuyển động nhưng không chỉ đọc: được phép cả khi máy thật đang khóa.
_NO_MOTION_EXACT = {"$X", "$ALARM/DISABLE"}
# Lệnh Home: tên ngắn và tên dài -> các trục sẽ Home.
_HOME_AXES = {"$H": "XY", "$HOME": "XY", "$HX": "X", "$HOME/X": "X",
              "$HY": "Y", "$HOME/Y": "Y", "$HXY": "XY", "$HYX": "XY"}


def _floats(text: str) -> list[float]:
    """Danh sách tọa độ; ValueError nếu có giá trị không hữu hạn (nan/inf) để bỏ cả trường."""
    values = [float(v) for v in text.split(",") if v != ""]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("non-finite coordinate")
    return values


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


def _norm(line: str) -> str:
    return line.strip().upper().replace(" ", "")


def is_read_only_command(line: str) -> bool:
    """True nếu lệnh chỉ đọc thông tin, không làm máy chuyển động hay đổi cấu hình."""
    text = _norm(line)
    if text.startswith("$/"):           # $/axes/x/max_rate_mm_per_min: đọc; có "=" là ghi
        return "=" not in text
    return text in _READ_EXACT or text.startswith(_READ_PREFIXES)


def is_motion_free_command(line: str) -> bool:
    """Chỉ đọc, hoặc `$X` (mở Alarm, không chuyển động): luôn được gửi tới máy thật."""
    return is_read_only_command(line) or _norm(line) in _NO_MOTION_EXACT


def homing_axes(line: str) -> str | None:
    """'XY'/'X'/'Y' nếu là lệnh Home ($H, $HX, $Home/Y...), ngược lại None."""
    return _HOME_AXES.get(_norm(line))
