"""Bố trí: đặt đường nét vào KHUNG VẼ (mm) trong vùng làm việc của máy.

Thứ tự: tính khung (căn giữa hoặc theo offset) -> kiểm lề -> co giãn (contain/stretch)
-> căn nội dung giữa khung -> lật trong khung -> đảo thứ tự nét.
Mọi lớp dùng CHUNG một phép đặt (tính trên hộp bao của tất cả lớp) để các lớp luôn khớp nhau.
Tọa độ ra: mm, gốc trên trái, Y xuống (chưa đảo trục máy; việc đó nằm ở gcode.to_machine).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .errors import DrawError
from .spec import Params
from .types import Box, Layer

EPS = 1e-6


@dataclass(frozen=True)
class Placement:
    src: Box          # hộp bao nội dung gốc
    box: Box          # khung vẽ trên máy
    sx: float
    sy: float
    ox: float         # góc trên trái của nội dung sau co giãn
    oy: float
    flip_x: bool
    flip_y: bool

    def map(self, x: float, y: float) -> tuple[float, float]:
        nx = self.ox + (x - self.src.x) * self.sx
        ny = self.oy + (y - self.src.y) * self.sy
        if self.flip_x:
            nx = 2 * (self.box.x + self.box.w / 2) - nx
        if self.flip_y:
            ny = 2 * (self.box.y + self.box.h / 2) - ny
        return nx, ny


def content_bounds(layers: Iterable[Layer]) -> Box:
    xs: list[float] = []
    ys: list[float] = []
    for layer in layers:
        for stroke in layer.strokes:
            for x, y in stroke:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise DrawError("empty_drawing", "Không có đường nét nào để vẽ.")
    return Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def plan(src: Box, layout: Params, machine: Params) -> Placement:
    W, H = machine.work_w, machine.work_h
    w, h, m = layout.width_mm, layout.height_mm, layout.margin_mm
    if layout.center:
        bx, by = (W - w) / 2, (H - h) / 2
    else:
        bx, by = layout.offset_x_mm, layout.offset_y_mm
    if bx < m - EPS or by < m - EPS or bx + w > W - m + EPS or by + h > H - m + EPS:
        raise DrawError("box_out_of_area",
                        f"Khung vẽ {w:g}x{h:g} mm (lề {m:g}) không nằm trong vùng làm việc {W:g}x{H:g} mm.")
    cw, ch = src.w, src.h
    if cw <= EPS and ch <= EPS:
        raise DrawError("empty_drawing", "Nội dung chỉ là một điểm, không có gì để vẽ.")
    rx = w / cw if cw > EPS else None
    ry = h / ch if ch > EPS else None
    if layout.fit == "stretch":
        sx = rx if rx is not None else 1.0
        sy = ry if ry is not None else 1.0
    else:  # contain: giữ tỷ lệ
        s = min(r for r in (rx, ry) if r is not None)
        sx = sy = s
    ox = bx + (w - cw * sx) / 2
    oy = by + (h - ch * sy) / 2
    return Placement(src, Box(bx, by, w, h), sx, sy, ox, oy, layout.flip_x, layout.flip_y)


def place_layers(layers: list[Layer], pl: Placement, reverse: bool) -> list[Layer]:
    out: list[Layer] = []
    for layer in layers:
        strokes = [[pl.map(x, y) for x, y in s] for s in layer.strokes]
        if reverse:
            strokes.reverse()
        out.append(Layer(layer.id, strokes))
    return out
