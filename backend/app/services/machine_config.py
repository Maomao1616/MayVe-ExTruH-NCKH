"""Đọc / sửa / lưu cấu hình FluidNC qua cổng serial.

Cú pháp đã thử trên board thật (MKS DLC32, FluidNC v4.1.1, 29/10/2026):
  $Config/Filename                 -> $Config/Filename=ConfigNCKH-16.yaml
  $CD                              -> toàn bộ YAML ĐANG CHẠY
  $/axes/x/max_rate_mm_per_min     -> $/axes/x/max_rate_mm_per_min=6000.000
  $/axes/x/max_rate_mm_per_min=v   -> đổi trong RAM (mất khi tắt máy)
  $LocalFS/Show=/<tệp>             -> nội dung nguyên văn của tệp
  $CD=/localfs/<tệp>               -> ghi YAML đang chạy ra tệp. FluidNC viết lại theo dạng chuẩn
                                      (mất chú thích #, thêm mục mặc định), nên luôn sao lưu
                                      nguyên văn tệp gốc về máy tính trước khi ghi.

Chỉ cho sửa các mục trong FIELDS (tốc độ, gia tốc, hành trình, Home, servo). Không cho sửa
chân GPIO, kinematics, stepping: sai những mục đó có thể làm mạch không khởi động được.
Giới hạn min/max dưới đây chỉ để chặn số vô lý; firmware vẫn là lớp kiểm tra cuối.
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

BACKUP_DIR = Path(__file__).resolve().parents[2] / "data" / "config_backups"
FILE_TIMEOUT_S = 10.0           # $CD / $LocalFS/Show trả ~200 dòng qua 115200 baud
VALUE_TOL = 1e-3


@dataclass(frozen=True)
class Field:
    path: str                   # đường dẫn FluidNC, chữ thường: "axes/x/max_rate_mm_per_min"
    group: str                  # x | y | z | general
    unit: str
    min: float
    max: float
    integer: bool = False


def _axis_fields(axis: str, travel_max: float) -> list[Field]:
    base = f"axes/{axis}"
    return [
        Field(f"{base}/max_rate_mm_per_min", axis, "mm/min", 1, 30000),
        Field(f"{base}/acceleration_mm_per_sec2", axis, "mm/s²", 1, 10000),
        Field(f"{base}/max_travel_mm", axis, "mm", 0.1, travel_max),
    ]


FIELDS: tuple[Field, ...] = (
    *_axis_fields("x", 2000),
    Field("axes/x/homing/seek_mm_per_min", "x", "mm/min", 1, 30000),
    Field("axes/x/homing/feed_mm_per_min", "x", "mm/min", 1, 10000),
    *_axis_fields("y", 2000),
    Field("axes/y/homing/seek_mm_per_min", "y", "mm/min", 1, 30000),
    Field("axes/y/homing/feed_mm_per_min", "y", "mm/min", 1, 10000),
    *_axis_fields("z", 100),
    Field("axes/z/motor0/rc_servo/min_pulse_us", "z", "µs", 500, 2500, integer=True),
    Field("axes/z/motor0/rc_servo/max_pulse_us", "z", "µs", 500, 2500, integer=True),
    Field("junction_deviation_mm", "general", "mm", 0.0001, 1),
    Field("arc_tolerance_mm", "general", "mm", 0.0001, 1),
)
FIELD_BY_PATH = {f.path: f for f in FIELDS}


class ConfigError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# --- hàm thuần (test không cần máy) ----------------------------------------------
def fmt(value: float, integer: bool = False) -> str:
    if integer:
        return str(int(round(value)))
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def lookup(tree: dict, path: str):
    """Đi theo path trong cây YAML, không phân biệt hoa thường ('X' trong dump = 'x')."""
    node = tree
    for part in path.split("/"):
        if not isinstance(node, dict):
            return None
        match = next((k for k in node if str(k).lower() == part), None)
        if match is None:
            return None
        node = node[match]
    return node


def parse_yaml(lines: list[str]) -> dict:
    try:
        tree = yaml.safe_load("\n".join(lines))
    except yaml.YAMLError as exc:
        raise ConfigError("bad_config", f"Không đọc được YAML từ máy: {exc}", 502) from exc
    if not isinstance(tree, dict):
        raise ConfigError("bad_config", "Máy không trả về cấu hình YAML.", 502)
    return tree


def extract(tree: dict) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for f in FIELDS:
        value = lookup(tree, f.path)
        out[f.path] = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    return out


def validate(values: dict[str, float], current: dict[str, float | None]) -> dict[str, float]:
    """Kiểm tra trước khi gửi bất kỳ lệnh nào: sai một mục là không gửi mục nào."""
    clean: dict[str, float] = {}
    for path, raw in values.items():
        f = FIELD_BY_PATH.get(path)
        if f is None:
            raise ConfigError("bad_param", f"Không cho phép sửa mục: {path}")
        value = float(raw)
        if not math.isfinite(value) or not f.min <= value <= f.max:
            raise ConfigError("bad_param", f"{path}: {value:g} ngoài khoảng {f.min:g}–{f.max:g} {f.unit}")
        clean[path] = float(round(value)) if f.integer else value
    merged = {**current, **clean}
    lo = merged.get("axes/z/motor0/rc_servo/min_pulse_us")
    hi = merged.get("axes/z/motor0/rc_servo/max_pulse_us")
    if lo is not None and hi is not None and lo >= hi:
        raise ConfigError("bad_param", "Servo: min_pulse_us phải nhỏ hơn max_pulse_us.")
    return clean


def _setting_value(lines: list[str], path: str) -> float | None:
    """'$/axes/x/max_rate_mm_per_min=6000.000' -> 6000.0"""
    pattern = re.compile(rf"^\$/{re.escape(path)}=(.+)$", re.IGNORECASE)
    for line in lines:
        m = pattern.match(line.strip())
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


# --- làm việc với máy (svc: MachineService) ----------------------------------------
def _require_settled(svc) -> None:
    state, _, _ = svc.machine_state()
    if state not in ("Idle", "Alarm"):
        raise ConfigError("not_idle", f"Máy phải Idle hoặc Alarm để sửa cấu hình (hiện tại: {state}).", 409)


def config_filename(svc) -> str:
    for line in svc.query("$Config/Filename"):
        m = re.match(r"^\$Config/Filename=(.+)$", line.strip(), re.IGNORECASE)
        if m:
            name = m.group(1).strip().lstrip("/")
            if re.fullmatch(r"[\w.\-]+\.ya?ml", name):
                return name
            raise ConfigError("bad_config", f"Tên tệp cấu hình lạ: {name}", 502)
    raise ConfigError("bad_config", "Máy không trả tên tệp cấu hình.", 502)


def read_config(svc) -> dict:
    """Giá trị ĐANG CHẠY + giá trị trong TỆP. Mục khác nhau = đã áp dụng nhưng chưa lưu."""
    name = config_filename(svc)
    running = extract(parse_yaml(svc.query("$CD", timeout=FILE_TIMEOUT_S)))
    saved = extract(parse_yaml(svc.query(f"$LocalFS/Show=/{name}", timeout=FILE_TIMEOUT_S)))
    unsaved = [p for p in running
               if running[p] is not None and (saved[p] is None or abs(running[p] - saved[p]) > VALUE_TOL)]
    return {
        "file": name,
        "values": running,
        "saved": saved,
        "unsaved": unsaved,
        "fields": [{"path": f.path, "group": f.group, "unit": f.unit, "min": f.min, "max": f.max,
                    "integer": f.integer} for f in FIELDS],
    }


def apply_values(svc, values: dict[str, float]) -> dict:
    """Đổi trong RAM của máy (mất khi tắt máy) rồi đọc lại từng mục để xác nhận."""
    if not values:
        raise ConfigError("bad_param", "Không có mục nào để áp dụng.")
    _require_settled(svc)
    current = extract(parse_yaml(svc.query("$CD", timeout=FILE_TIMEOUT_S)))
    clean = validate(values, current)
    failed = []
    for path, value in clean.items():
        f = FIELD_BY_PATH[path]
        svc.query(f"$/{path}={fmt(value, f.integer)}")
        got = _setting_value(svc.query(f"$/{path}"), path)
        if got is None or abs(got - value) > max(VALUE_TOL, abs(value) * 1e-6):
            failed.append({"path": path, "wanted": value, "got": got})
    svc.log_system(f"Config: applied {len(clean) - len(failed)}/{len(clean)} value(s) in RAM (not saved)."
                   + (f" NOT confirmed: {', '.join(x['path'] for x in failed)}" if failed else ""))
    result = read_config(svc)
    result["failed"] = failed
    return result


def save_to_board(svc) -> dict:
    """Sao lưu nguyên văn tệp gốc về máy tính, rồi ghi YAML đang chạy đè lên tệp trên mạch."""
    _require_settled(svc)
    name = config_filename(svc)
    original = svc.query(f"$LocalFS/Show=/{name}", timeout=FILE_TIMEOUT_S)
    if not original:
        raise ConfigError("bad_config", f"Không đọc được tệp {name} để sao lưu.", 502)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_{name}"
    backup.write_text("\n".join(original) + "\n", encoding="utf-8")
    svc.log_system(f"Config: original {name} backed up to {backup}")

    running = extract(parse_yaml(svc.query("$CD", timeout=FILE_TIMEOUT_S)))
    svc.query(f"$CD=/localfs/{name}", timeout=FILE_TIMEOUT_S)
    written = extract(parse_yaml(svc.query(f"$LocalFS/Show=/{name}", timeout=FILE_TIMEOUT_S)))
    mismatched = [p for p, v in running.items()
                  if v is not None and (written[p] is None or abs(written[p] - v) > VALUE_TOL)]
    svc.log_system(f"Config: saved running config to {name}"
                   + (f"; MISMATCH after save: {', '.join(mismatched)}" if mismatched else "; verified."))
    return {"file": name, "backup": str(backup), "verified": not mismatched, "mismatched": mismatched}
