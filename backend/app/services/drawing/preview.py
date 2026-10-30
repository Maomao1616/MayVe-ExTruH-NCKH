"""Nét xem nháp: rút gọn để vẽ lên canvas (tọa độ NGUỒN, trước bố trí; frontend tự di chuyển/co giãn).

Sai số mặc định 0,3 mm; vượt trần số điểm thì tăng sai số dần cho tới khi vừa."""
from __future__ import annotations

from .layout import content_bounds
from .shapes import Layer

MAX_PREVIEW_POINTS = 100_000


def _simplify(stroke: list[tuple[float, float]], tol: float) -> list[list[float]]:
    if tol <= 0 or len(stroke) <= 2:
        return [[round(x, 3), round(y, 3)] for x, y in stroke]
    from shapely.geometry import LineString
    line = LineString(stroke).simplify(tol, preserve_topology=False)
    return [[round(x, 3), round(y, 3)] for x, y in line.coords]


def build(layers: list[Layer], colors: dict[str, str | None] | None = None, tol: float = 0.3,
          limit: int = MAX_PREVIEW_POINTS) -> dict:
    colors = colors or {}
    for _ in range(8):
        out = [{"id": l.id, "color": colors.get(l.id), "strokes": [_simplify(s, tol) for s in l.strokes]}
               for l in layers]
        total = sum(len(s) for l in out for s in l["strokes"])
        if total <= limit:
            break
        tol = max(tol * 2, 0.1)
    b = content_bounds(layers)
    return {"bounds": {"x": b.x, "y": b.y, "w": b.w, "h": b.h}, "tolerance_mm": tol, "points": total,
            "layers": out}
