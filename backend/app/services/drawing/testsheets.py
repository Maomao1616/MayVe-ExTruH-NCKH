"""Tờ thử máy thành BẢN THẢO thường (xem trước, nạp sang Điều khiển, chạy): nhấc bút, mất bước, gia tốc / góc, tốc độ, vệt kéo.

G-code do `testgcode.py` sinh (cùng bộ với tools/make_test_gcode.py), nhập bằng `gcode_import.import_gcode` nên đi qua đúng
bộ làm sạch của tác vụ. Chỉ dùng cho thử máy thật; tab Tạo bản vẽ vẫn không gọi máy.
Tờ nhấc bút trả thêm `rows`: hàng N ↔ (Z nhấc, chờ, tốc độ hạ) để giao diện hiện bảng và nút "Dùng hàng N".
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from . import gcode_import, spec, testgcode as tg
from .errors import DrawError

KINDS = ("lift", "lost", "accel", "speed", "drag", "arc")
NAMES = {"lift": "Tờ thử nhấc bút", "lost": "Tờ thử 7.2 mất bước", "accel": "Tờ thử 7.3 gia tốc",
         "speed": "Tờ thử 7.4 tốc độ vẽ", "drag": "Tờ thử 7.5 vệt kéo", "arc": "Tờ thử 7.6 đoạn ngắn và cung G2"}
MAX_LIST = 8
DEFAULT_DELAYS = (0.02, 0.05, 0.1)                # tờ nhấc bút: chờ thử mặc định (giây)
DEFAULT_SPEEDS = (7000, 8000, 9000, 10000)        # 7.2 / 7.3 / 7.4: tốc độ thử mặc định (mm/phút)
SPEED_MIN, SPEED_MAX = 100.0, 20000.0             # = khoảng của gcode.draw_feed trong spec.py


def _span(speeds: list[int]) -> str:
    return f"{speeds[0]}" if len(speeds) == 1 else f"{speeds[0]}–{speeds[-1]}"


def _numbers(options: Mapping[str, Any], key: str, default: list[float], lo: float, hi: float, label: str) -> list[float]:
    raw = options.get(key, default)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        raw = [raw]                         # một số lẻ (vd ô "Chờ nâng" của bài 7.5) = danh sách một giá trị
    if not isinstance(raw, (list, tuple)) or not 1 <= len(raw) <= MAX_LIST:
        raise DrawError("bad_param", f"{label}: cần 1–{MAX_LIST} giá trị.")
    out = []
    for v in raw:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
            raise DrawError("bad_param", f"{label}: mỗi giá trị phải là số trong khoảng {lo:g}–{hi:g}.")
        out.append(float(v))
    return sorted(set(out))


def make_draft(kind: str, machine_raw: Mapping[str, Any], gcode_raw: Mapping[str, Any], options: Mapping[str, Any]) -> dict:
    from . import drafts            # nhập muộn: tránh vòng nhập khi gói được nạp
    if kind not in KINDS:
        raise DrawError("bad_param", f"kind: chỉ nhận {', '.join(KINDS)}.")
    machine = spec.parse("machine", machine_raw)
    gp = spec.parse("gcode", gcode_raw)
    down, pen_feed, draw_feed = gp.pen_down_z, gp.pen_feed, gp.draw_feed
    down_feed = gp.pen_down_feed
    delay = gp.delay_down_s                 # chờ của các bài 7.2–7.4 = ô "chờ" đang dùng ở tab Tạo bản vẽ
    rows: list[dict] | None = None

    def speeds() -> list[int]:
        # Không chặn theo tốc độ tối đa của máy: tờ thử là để tìm giới hạn. Firmware vẫn tự chặn ở max_rate_mm_per_min.
        return [int(s) for s in _numbers(options, "speeds", list(DEFAULT_SPEEDS), SPEED_MIN, SPEED_MAX, "speeds (tốc độ thử)")]

    if kind == "lift":
        ups = _numbers(options, "ups", [1.0, 3.0, 5.0], down + 0.3, machine.z_travel, "ups (Z nhấc)")
        delays = _numbers(options, "delays", list(DEFAULT_DELAYS), 0.0, 5.0, "delays (chờ, giây)")
        dfeeds = _numbers(options, "down_feeds", [1000.0, 2000.0], 100.0, 20000.0, "down_feeds (tốc độ hạ)")
        if len(ups) * len(delays) * len(dfeeds) > tg.LIFT_MAX_ROWS:
            raise DrawError("too_many_rows", f"Quá nhiều hàng (tối đa {tg.LIFT_MAX_ROWS}). Bớt giá trị ở một nhóm.")
        rows = tg.lift_rows(ups, delays, dfeeds, pen_feed=pen_feed, down=down, draw_feed=draw_feed)
        text = tg.lift_sheet(rows, down, pen_feed, draw_feed)
        label = f"{NAMES[kind]} ({len(rows)} hàng)"
    elif kind == "lost":
        s = speeds()
        text = tg.lost_steps(gp.pen_up_z, down, pen_feed, draw_feed, speeds=s, delay=delay, down_feed=down_feed)
        label = f"{NAMES[kind]} ({_span(s)})"
    elif kind == "accel":
        s = speeds()
        text = tg.accel(gp.pen_up_z, down, pen_feed, draw_feed, speeds=s, delay=delay, down_feed=down_feed)
        label = f"{NAMES[kind]} ({_span(s)})"
    elif kind == "speed":
        s = speeds()
        text = tg.speed_strips(gp.pen_up_z, down, pen_feed, speeds=s, delay=delay, down_feed=down_feed)
        label = f"{NAMES[kind]} ({_span(s)})"
    elif kind == "arc":
        text = tg.arc_test(gp.pen_up_z, down, pen_feed, draw_feed, delay=delay, down_feed=down_feed)
        label = f"{NAMES[kind]} ({tg.num(draw_feed)})"
    else:  # drag
        delay = _numbers(options, "delay", [0.05], 0.0, 5.0, "delay (chờ, giây)")[0]
        text = tg.drag_test(gp.pen_up_z, down, pen_feed, draw_feed, delay=delay, down_feed=down_feed)
        label = f"{NAMES[kind]} (chờ {tg.num(delay)} s)"

    source = {"kind": kind}
    if rows is not None:
        source["rows"] = rows
    result = gcode_import.import_gcode(label, text, machine.work_w, machine.work_h, source=("testsheet", source),
                                       check_bounds=True)
    if rows is not None:
        result["rows"] = rows
    return result
