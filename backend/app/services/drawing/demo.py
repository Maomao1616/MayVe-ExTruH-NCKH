"""DỮ LIỆU GIẢ cho ảnh raster (giai đoạn dựng giao diện): chưa có thuật toán thật, trả vài nét mẫu để
frontend thử tiến trình / nháp / bố trí. Thay bằng dây chuyền thật ở GĐ6 (docs/DRAW_ROADMAP.md);
hợp đồng API không đổi."""
from __future__ import annotations

import math
import time

from .layout import content_bounds
from .shapes import Layer
from .store import TASKS, Parsed

STUB_STEP_S = 0.25          # giả lập thời gian xử lý để thấy thanh tiến trình (test đặt 0)
STEPS = (("read", "Đọc ảnh"), ("style", "Tạo nét"), ("optimize", "Tối ưu"))


def _spiral(cx: float, cy: float, r: float, turns: int = 8, n: int = 900):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = t * turns * 2 * math.pi
        pts.append((cx + r * t * math.cos(a), cy + r * t * math.sin(a)))
    return pts


def import_demo(ctx, token: str, name: str) -> dict:
    for i, (step, message) in enumerate(STEPS):
        ctx.step(step, i / len(STEPS), message)
        time.sleep(STUB_STEP_S)
    circle = [(50 + 50 * math.cos(a / 60 * 2 * math.pi), 50 + 50 * math.sin(a / 60 * 2 * math.pi))
              for a in range(61)]
    layer = Layer("1", [circle, _spiral(50, 50, 45)])
    b = content_bounds([layer])
    info = {"mode": "demo", "stub": True, "name": name,
            "bounds": {"x": b.x, "y": b.y, "w": b.w, "h": b.h},
            "layers": [{"id": "1", "name": None, "color": None, "strokes": 2,
                        "points": sum(len(s) for s in layer.strokes)}]}
    TASKS.put(Parsed([layer], None, info), token)
    return {"source": info, "warnings": [{"code": "demo_data", "count": 1}]}
