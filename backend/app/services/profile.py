"""Hồ sơ phần mềm: thông số chỉ phần mềm dùng (không nằm trong YAML của mạch).

Lưu ở <thư mục dữ liệu>/profile.json (app/paths.py) để mọi trình duyệt (laptop, mini PC) dùng chung.
Z bút là tọa độ làm việc (G90 Z..); hành trình Z thật do firmware giới hạn (soft limit).
"""
from __future__ import annotations

import json
import math
import threading

from .. import paths

DEFAULTS = {
    "pen_up_z": 5.0,        # đã khớp WebUI FluidNC trên máy thật
    "pen_mid_z": 2.5,
    "pen_down_z": 0.0,
    "pen_feed": 3000.0,     # mm/phút, <= $112 (3000)
    "jog_max_step": 50.0,   # mm, bước jog lớn nhất được hiện
}
LIMITS = {
    "pen_up_z": (-100, 100), "pen_mid_z": (-100, 100), "pen_down_z": (-100, 100),
    "pen_feed": (1, 30000), "jog_max_step": (0.1, 1000),
}

_lock = threading.Lock()


class ProfileError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code, self.message, self.status = "bad_param", message, 400


def validate(data: dict) -> dict:
    out = {}
    for key, default in DEFAULTS.items():
        value = data.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ProfileError(f"{key}: phải là số.")
        lo, hi = LIMITS[key]
        if not lo <= value <= hi:
            raise ProfileError(f"{key}: {value:g} ngoài khoảng {lo:g}–{hi:g}.")
        out[key] = float(value)
    if not out["pen_down_z"] < out["pen_mid_z"] < out["pen_up_z"]:
        raise ProfileError("Z bút phải theo thứ tự: xuống < giữa < lên.")
    return out


def load() -> dict:
    with _lock:
        try:
            data = json.loads(paths.data_file("profile.json").read_text(encoding="utf-8"))
            return validate(data if isinstance(data, dict) else {})
        except (OSError, ValueError, ProfileError):
            return dict(DEFAULTS)


def save(data: dict) -> dict:
    clean = validate(data)
    with _lock:
        target = paths.data_file("profile.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(clean, indent=2), encoding="utf-8")
        tmp.replace(target)              # ghi nguyên tử: không bao giờ để tệp dở dang
    return clean
