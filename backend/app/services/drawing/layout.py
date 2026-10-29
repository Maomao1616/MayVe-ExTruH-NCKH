"""Bố trí: đặt đường nét vào KHUNG VẼ nằm trong TỜ GIẤY, tờ giấy nằm trong vùng làm việc của máy.

Tờ giấy neo ở gốc máy O(0,0) (góc trên trái, Y xuống), có thể dịch bằng paper_x/paper_y.
Thứ tự: xác định tờ giấy -> kiểm tờ giấy nằm trong vùng máy -> trừ lề -> khung vẽ (mặc định lấp đầy,
căn giữa hoặc theo offset) -> co giãn (contain/stretch) -> căn nội dung giữa khung -> lật trong khung
-> đảo thứ tự nét.
Mọi lớp dùng CHUNG một phép đặt (tính trên hộp bao của tất cả lớp) để các lớp luôn khớp nhau.
Tọa độ ra: mm, gốc trên trái, Y xuống (chưa đảo trục máy; việc đó nằm ở gcode.to_machine).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .errors import DrawError
from .shapes import Box, Layer
from .spec import PAPERS, Params

EPS = 1e-6


@dataclass(frozen=True)
class Placement:
    src: Box          # hộp bao nội dung gốc
    paper: Box        # tờ giấy trên máy
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


def paper_size(layout: Params) -> tuple[float, float]:
    if layout.paper == "custom":
        if layout.paper_width_mm is None or layout.paper_height_mm is None:
            raise DrawError("bad_param", "layout: paper=custom cần paper_width_mm và paper_height_mm")
        return layout.paper_width_mm, layout.paper_height_mm
    return PAPERS[layout.paper]


def plan(src: Box, layout: Params, machine: Params) -> Placement:
    W, H = machine.work_w, machine.work_h
    pw, ph = paper_size(layout)
    px, py = layout.paper_x_mm, layout.paper_y_mm
    if px + pw > W + EPS or py + ph > H + EPS:
        raise DrawError("paper_out_of_area",
                        f"Tờ giấy {pw:g}x{ph:g} mm đặt tại ({px:g}, {py:g}) vượt vùng làm việc {W:g}x{H:g} mm.")
    m = layout.margin_mm
    iw, ih = pw - 2 * m, ph - 2 * m                  # phần trong lề của tờ giấy
    if iw <= EPS or ih <= EPS:
        raise DrawError("bad_param", f"layout: lề {m:g} mm quá lớn so với tờ giấy {pw:g}x{ph:g} mm")
    w = layout.width_mm if layout.width_mm is not None else iw
    h = layout.height_mm if layout.height_mm is not None else ih
    if layout.center:
        bx, by = px + m + (iw - w) / 2, py + m + (ih - h) / 2
    else:
        bx, by = px + m + layout.offset_x_mm, py + m + layout.offset_y_mm
    if (w > iw + EPS or h > ih + EPS or bx < px + m - EPS or by < py + m - EPS
            or bx + w > px + m + iw + EPS or by + h > py + m + ih + EPS):
        raise DrawError("box_out_of_paper",
                        f"Khung vẽ {w:g}x{h:g} mm không nằm trong phần trong lề ({iw:g}x{ih:g} mm) của tờ giấy.")
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
    return Placement(src, Box(px, py, pw, ph), Box(bx, by, w, h), sx, sy, ox, oy,
                     layout.flip_x, layout.flip_y)


def place_layers(layers: list[Layer], pl: Placement, reverse: bool) -> list[Layer]:
    out: list[Layer] = []
    for layer in layers:
        strokes = [[pl.map(x, y) for x, y in s] for s in layer.strokes]
        if reverse:
            strokes.reverse()
        out.append(Layer(layer.id, strokes))
    return out
