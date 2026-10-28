"""Khai báo tham số MỘT chỗ: tên, kiểu, mặc định, giới hạn. Dùng để kiểm tra đầu vào VÀ để trả cho
frontend qua /api/draw/schema (frontend không rải số cứng).

Thêm/sửa một tham số = sửa đúng một dòng trong LAYOUT / GCODE / MACHINE bên dưới.
Tham số `required=True` không có mặc định: frontend phải gửi (lấy từ MACHINE trong config.js),
backend không tự đặt số riêng của máy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from .errors import DrawError
from .registry import VECTORIZERS


@dataclass(frozen=True)
class Param:
    name: str
    kind: str                      # "float" | "int" | "bool" | "choice"
    default: Any = None
    min: float | None = None
    max: float | None = None
    choices: tuple[str, ...] = ()
    unit: str = ""
    required: bool = False


# Khổ giấy dựng sẵn (mm, đặt đứng). Frontend dùng để điền rộng/cao; backend không phụ thuộc.
PAPERS = {"a4": (210.0, 297.0), "a5": (148.0, 210.0), "letter": (215.9, 279.4)}

# Khung vẽ trong vùng làm việc của máy.
LAYOUT = (
    Param("width_mm", "float", 100.0, 1, 5000, unit="mm"),
    Param("height_mm", "float", 100.0, 1, 5000, unit="mm"),
    Param("margin_mm", "float", 5.0, 0, 500, unit="mm"),
    Param("fit", "choice", "contain", choices=("contain", "stretch")),
    Param("center", "bool", True),                       # căn giữa khung vẽ trong vùng làm việc
    Param("offset_x_mm", "float", 0.0, 0, 5000, unit="mm"),   # góc trên trái khung khi center=false
    Param("offset_y_mm", "float", 0.0, 0, 5000, unit="mm"),
    Param("flip_x", "bool", False),
    Param("flip_y", "bool", False),
    Param("reverse", "bool", False),                     # đảo thứ tự các nét
)

# Thông số vẽ (khớp các ô trong tab).
GCODE = (
    Param("draw_feed", "float", 3000.0, 10, 20000, unit="mm/min"),
    Param("travel_feed", "float", 6000.0, 10, 20000, unit="mm/min"),
    Param("pen_up_z", "float", required=True, min=0, max=1000, unit="mm"),
    Param("pen_down_z", "float", required=True, min=0, max=1000, unit="mm"),
    Param("pen_feed", "float", 3000.0, 10, 20000, unit="mm/min"),
    Param("delay_up_s", "float", 0.2, 0, 60, unit="s"),
    Param("delay_down_s", "float", 0.2, 0, 60, unit="s"),
    Param("precision", "int", 3, 1, 4),
)

# Giới hạn phần cứng: LẤY TỪ MACHINE trong config.js, backend không tự đặt.
MACHINE = (
    Param("work_w", "float", required=True, min=1, max=5000, unit="mm"),
    Param("work_h", "float", required=True, min=1, max=5000, unit="mm"),
    Param("z_travel", "float", required=True, min=0, max=1000, unit="mm"),
    Param("rapid_feed", "float", required=True, min=10, max=100000, unit="mm/min"),
    # Điểm DUY NHẤT đảo chiều Y khi chưa kiểm chứng hướng trục thật (giả định C5).
    Param("invert_y", "bool", False),
)

GROUPS = {"layout": LAYOUT, "gcode": GCODE, "machine": MACHINE}


class Params:
    """Tham số đã kiểm tra, truy cập bằng thuộc tính, không sửa được."""
    __slots__ = ("_v",)

    def __init__(self, values: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_v", dict(values))

    def __getattr__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, "_v")[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Params là bất biến")

    def as_dict(self) -> dict[str, Any]:
        return dict(self._v)


def _coerce(group: str, p: Param, v: Any) -> Any:
    where = f"{group}.{p.name}"
    if p.kind == "bool":
        if not isinstance(v, bool):
            raise DrawError("bad_param", f"{where}: phải là true hoặc false")
        return v
    if p.kind == "choice":
        if v not in p.choices:
            raise DrawError("bad_param", f"{where}: chỉ nhận {', '.join(p.choices)}")
        return v
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise DrawError("bad_param", f"{where}: phải là số")
    if not math.isfinite(v):
        raise DrawError("bad_param", f"{where}: không phải số hữu hạn")
    if p.kind == "int":
        if float(v) != int(v):
            raise DrawError("bad_param", f"{where}: phải là số nguyên")
        v = int(v)
    else:
        v = float(v)
    if (p.min is not None and v < p.min) or (p.max is not None and v > p.max):
        raise DrawError("bad_param", f"{where}: ngoài khoảng {p.min}..{p.max} {p.unit}".strip())
    return v


def parse(group: str, raw: Mapping[str, Any] | None) -> Params:
    """Điền mặc định, từ chối tham số lạ (bắt lỗi gõ sai tên), kiểm kiểu và khoảng giá trị."""
    specs = GROUPS[group]
    raw = dict(raw or {})
    unknown = sorted(set(raw) - {p.name for p in specs})
    if unknown:
        raise DrawError("bad_param", f"{group}: tham số lạ: {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for p in specs:
        if raw.get(p.name) is not None:
            values[p.name] = _coerce(group, p, raw[p.name])
        elif p.required:
            raise DrawError("bad_param", f"{group}.{p.name}: thiếu (bắt buộc)")
        else:
            values[p.name] = p.default
    return Params(values)


def describe() -> dict:
    """Nội dung cho GET /api/draw/schema."""
    from .service import MAX_POINTS
    from ..job import MAX_LINES

    def row(p: Param) -> dict:
        return {"name": p.name, "kind": p.kind, "default": p.default, "min": p.min, "max": p.max,
                "choices": list(p.choices), "unit": p.unit, "required": p.required}

    return {
        "papers": {k: {"w": w, "h": h} for k, (w, h) in PAPERS.items()},
        "params": {g: [row(p) for p in specs] for g, specs in GROUPS.items()},
        "vectorizers": VECTORIZERS.names(),
        "limits": {"max_lines": MAX_LINES, "max_points": MAX_POINTS},
    }
