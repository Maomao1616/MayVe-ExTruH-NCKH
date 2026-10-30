"""Tờ mẫu hiệu chỉnh bút: tạo thành một BẢN THẢO như mọi bản khác (xem trước, nạp sang Điều khiển, chạy).

Một tờ A5 đặt đứng, tỷ lệ 1:1 (không co giãn), gồm:
  * chữ "F" ở góc trên trái: bất đối xứng nên nhìn là biết bản vẽ có bị lật / xoay trục không;
  * thước 100 mm có vạch mỗi 10 mm: đo bằng thước thật để kiểm tra bước/mm của máy;
  * 8 dải tô zigzag có khoảng cách dòng = độ rộng bút × hệ số khác nhau (từ trên xuống), để chọn
    khoảng cách đẹp nhất cho loại bút đang dùng (dải dày quá thì loang, thưa quá thì lộ giấy).
Chỉ dùng cho thử máy thật; tab Tạo bản vẽ vẫn không gọi máy.
"""
from __future__ import annotations

from typing import Any, Mapping

from . import drafts, service, spec
from .errors import DrawError
from .shapes import Layer

PAPER = "a5"
BAND_FACTORS = (0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0)     # khoảng cách dòng = bút × hệ số
WIDTH_MM, BAND_H, GAP = 130.0, 14.0, 2.0
HEADER_H = 24.0                                              # chữ F + thước
RULER_X0, RULER_LEN = 28.0, 100.0


def layers(pen_width_mm: float) -> list[Layer]:
    strokes: list[list[tuple[float, float]]] = []
    # chữ F cao 20 mm, rộng 12 mm (nét dọc, thanh trên, thanh giữa)
    strokes += [[(2, 22), (2, 2)], [(2, 2), (14, 2)], [(2, 12), (11, 12)]]
    # thước 100 mm: đường chính + vạch 10 mm (vạch 50 mm dài hơn)
    y = 14.0
    strokes.append([(RULER_X0, y), (RULER_X0 + RULER_LEN, y)])
    for i in range(11):
        x = RULER_X0 + i * 10
        tick = 6.0 if i in (0, 5, 10) else 3.0
        strokes.append([(x, y), (x, y - tick)])
    # các dải tô
    top = HEADER_H + 4
    for index, factor in enumerate(BAND_FACTORS):
        y0 = top + index * (BAND_H + GAP)
        pitch = pen_width_mm * factor
        count = int(BAND_H / pitch) + 1
        path: list[tuple[float, float]] = []
        for row in range(count):
            yy = min(y0 + row * pitch, y0 + BAND_H)
            ends = (0.0, WIDTH_MM) if row % 2 == 0 else (WIDTH_MM, 0.0)
            path += [(ends[0], yy), (ends[1], yy)]
        strokes.append(path)
    return [Layer("1", [[tuple(p) for p in s] for s in strokes])]


def height_mm() -> float:
    return HEADER_H + 4 + len(BAND_FACTORS) * BAND_H + (len(BAND_FACTORS) - 1) * GAP


def make_draft(name: str, machine_raw: Mapping[str, Any], gcode_raw: Mapping[str, Any],
               pen_width_mm: float, paper_x_mm: float = 0.0, paper_y_mm: float = 0.0) -> dict:
    if not 0.1 <= pen_width_mm <= 2:
        raise DrawError("bad_param", "pen_width_mm: ngoài khoảng 0,1–2 mm.")
    layout = {"paper": PAPER, "paper_x_mm": paper_x_mm, "paper_y_mm": paper_y_mm,
              "width_mm": WIDTH_MM, "height_mm": height_mm(), "fit": "contain", "center": True}
    result, placed = service.build(layers(pen_width_mm), machine_raw, layout, gcode_raw,
                                   (0.0, 0.0, WIDTH_MM, height_mm()))
    machine = spec.parse("machine", machine_raw).as_dict()
    params = {"machine": dict(machine_raw), "layout": layout, "gcode": dict(gcode_raw),
              "source": {"mode": "calibration", "pen_width_mm": pen_width_mm,
                         "band_factors": list(BAND_FACTORS)}}
    return {"draft": drafts.create(name, result, placed, machine, params), "warnings": result["warnings"]}
