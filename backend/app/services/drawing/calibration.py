"""Tờ mẫu hiệu chỉnh bút: tạo thành một BẢN THẢO như mọi bản khác (xem trước, nạp sang Điều khiển, chạy).

Một tờ A5 đặt đứng, tỷ lệ 1:1 (không co giãn), gồm:
  * chữ "F" ở góc trên trái: bất đối xứng nên nhìn là biết bản vẽ có bị lật / xoay trục không;
  * thước 100 mm có vạch mỗi 10 mm: đo bằng thước thật để kiểm tra bước/mm của máy;
  * 8 dải tô zigzag có khoảng cách dòng = cỡ nét đoán × hệ số khác nhau (từ trên xuống, dày → thưa), để ĐO bề
    rộng nét thật: dải thưa nhất mà vẫn đen kín (chưa ướt / bóng mực) có khoảng cách ≈ bề rộng nét. Dải thưa hơn lộ
    khe trắng; dải dày hơn chồng nét, thừa mực. Số đo đó ghi vào ô "Bút vẽ" (Tùy chọn) ở tab Tạo bản vẽ.
Chỉ dùng cho thử máy thật; tab Tạo bản vẽ vẫn không gọi máy.
"""
from __future__ import annotations

from typing import Any, Mapping

from . import drafts, service, spec
from .errors import DrawError
from .shapes import Layer

PAPER = "a5"
# khoảng cách dòng = bút × hệ số; bút 0,4: 0,32 / 0,40 / 0,45 / 0,50 / 0,60 / 0,80 / 1,0 / 1,2 mm (dày ở quanh 0,4–0,5
# để phân biệt nét 0,40 với 0,45 trên giấy Ivory)
BAND_FACTORS = (0.8, 1.0, 1.125, 1.25, 1.5, 2.0, 2.5, 3.0)
WIDTH_MM, BAND_H, GAP = 130.0, 14.0, 2.0
HEADER_H = 24.0                                              # chữ F + thước
RULER_X0, RULER_LEN = 28.0, 100.0

# Hai cỡ tờ: A5 (mặc định, thước 100 mm) và A6 gọn hơn (vừa phần trong lề 5 mm của A6 = 95 × 138 mm; thước 80 mm).
SIZES = {
    "a5": {"width": WIDTH_MM, "band_h": BAND_H, "gap": GAP, "ruler_x0": RULER_X0, "ruler_len": RULER_LEN},
    "a6": {"width": 95.0, "band_h": 10.0, "gap": 1.5, "ruler_x0": 14.0, "ruler_len": 80.0},
}


def _size(paper: str) -> dict:
    if paper not in SIZES:
        raise DrawError("bad_param", f"paper: chỉ nhận {', '.join(SIZES)}.")
    return SIZES[paper]


def layers(pen_width_mm: float, paper: str = PAPER) -> list[Layer]:
    z = _size(paper)
    width, band_h, gap, ruler_x0, ruler_len = z["width"], z["band_h"], z["gap"], z["ruler_x0"], z["ruler_len"]
    strokes: list[list[tuple[float, float]]] = []
    # chữ F cao 20 mm, rộng 12 mm (nét dọc, thanh trên, thanh giữa)
    strokes += [[(2, 22), (2, 2)], [(2, 2), (14, 2)], [(2, 12), (11, 12)]]
    # thước (100 mm ở A5, 80 mm ở A6): đường chính + vạch 10 mm (vạch đầu, giữa, cuối dài hơn)
    y = 14.0
    strokes.append([(ruler_x0, y), (ruler_x0 + ruler_len, y)])
    ticks = int(ruler_len // 10)
    for i in range(ticks + 1):
        x = ruler_x0 + i * 10
        tick = 6.0 if i in (0, ticks // 2, ticks) else 3.0
        strokes.append([(x, y), (x, y - tick)])
    # các dải tô
    top = HEADER_H + 4
    for index, factor in enumerate(BAND_FACTORS):
        y0 = top + index * (band_h + gap)
        pitch = pen_width_mm * factor
        count = int(band_h / pitch) + 1
        path: list[tuple[float, float]] = []
        for row in range(count):
            yy = min(y0 + row * pitch, y0 + band_h)
            ends = (0.0, width) if row % 2 == 0 else (width, 0.0)
            path += [(ends[0], yy), (ends[1], yy)]
        strokes.append(path)
    return [Layer("1", [[tuple(p) for p in s] for s in strokes])]


def height_mm(paper: str = PAPER) -> float:
    z = _size(paper)
    return HEADER_H + 4 + len(BAND_FACTORS) * z["band_h"] + (len(BAND_FACTORS) - 1) * z["gap"]


def make_draft(name: str, machine_raw: Mapping[str, Any], gcode_raw: Mapping[str, Any],
               pen_width_mm: float, paper_x_mm: float = 0.0, paper_y_mm: float = 0.0, paper: str = PAPER) -> dict:
    if not 0.1 <= pen_width_mm <= 2:
        raise DrawError("bad_param", "pen_width_mm: ngoài khoảng 0,1–2 mm.")
    z = _size(paper)
    height = height_mm(paper)
    layout = {"paper": paper, "paper_x_mm": paper_x_mm, "paper_y_mm": paper_y_mm,
              "width_mm": z["width"], "height_mm": height, "fit": "contain", "center": True}
    result, placed = service.build(layers(pen_width_mm, paper), machine_raw, layout, gcode_raw,
                                   (0.0, 0.0, z["width"], height))
    machine = spec.parse("machine", machine_raw).as_dict()
    params = {"machine": dict(machine_raw), "layout": layout, "gcode": dict(gcode_raw),
              "source": {"mode": "calibration", "pen_width_mm": pen_width_mm, "paper": paper,
                         "band_factors": list(BAND_FACTORS)}}
    return {"draft": drafts.create(name, result, placed, machine, params), "warnings": result["warnings"]}
