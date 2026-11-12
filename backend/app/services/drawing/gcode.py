"""Đường nét (mm, đã bố trí) -> dòng G-code + thống kê. Không gọi máy.

Quy ước (khớp gcode.js và job.py): dòng đầu `G90 G21`; có `F`; dòng <= 200 ký tự; không `$`;
bút lên = pen_up_z, xuống = pen_down_z; mỗi nét kết thúc bằng bút lên (nên file kết thúc bút lên).
Chỉ dùng G0/G1 (cung tròn G2/G3: giai đoạn 6, tùy chọn).
Di chuyển không vẽ dùng G0 khi travel_feed >= rapid_feed của máy; nếu thấp hơn thì G1 kèm F
(vì G0 luôn chạy ở tốc độ tối đa của firmware).
"""
from __future__ import annotations

import math

from ..job import MAX_LINE_LEN, MAX_LINES
from .errors import DrawError
from .spec import Params
from .shapes import Stroke


EST_ACCEL_MM_S2 = 3000.0     # gia tốc X / Y / Z dùng để ƯỚC TÍNH thời gian (máy chạy ổn ở 3000, đo 12/11/2026)
EST_JUNCTION_MM = 0.05       # junction_deviation đang dùng trên mạch (11/11/2026): qua góc càng gắt càng phải giảm tốc
EST_LIFT_OVERHEAD_S = 0.15   # mỗi lần nhấc bút mất thêm ~0,15 s ngoài chuyển động: lệnh G4 bắt máy chạy hết hàng đợi rồi mới
                             # chờ, sau đó phần mềm nạp lại (buffer tụt về 0 ở mỗi lần nhấc, 12/11/2026). Chỉnh theo tỷ lệ
                             # thực tế / ước tính cũ = 1,7–1,9 trên giấy (zigzag, đan chéo, xoắn ốc); chưa đo riêng từng tệp


def move_time(length: float, v0: float, v1: float, vmax: float, accel: float) -> float:
    """Thời gian đi một đoạn thẳng dài `length` (mm), vào ở v0, ra ở v1, tối đa vmax (mm/s), gia tốc accel (mm/s²).
    Hình thang (tăng tốc – đều – giảm tốc) hoặc tam giác nếu đoạn quá ngắn để kịp đạt vmax."""
    if length <= 0:
        return 0.0
    d_acc = (vmax * vmax - v0 * v0) / (2 * accel)
    d_dec = (vmax * vmax - v1 * v1) / (2 * accel)
    if d_acc + d_dec <= length:
        return (vmax - v0) / accel + (vmax - v1) / accel + (length - d_acc - d_dec) / vmax
    peak = math.sqrt(max(v0 * v0, v1 * v1, (2 * accel * length + v0 * v0 + v1 * v1) / 2))
    return max(0.0, (peak - v0) / accel) + max(0.0, (peak - v1) / accel)


def path_time(points, vmax: float, accel: float = EST_ACCEL_MM_S2, junction: float = EST_JUNCTION_MM) -> float:
    """Thời gian vẽ một nét liền (dừng ở đầu và cuối) theo cách bộ lập kế hoạch Grbl / FluidNC tính tốc độ qua góc:
    v_góc² = a × δ × sin(θ/2) / (1 − sin(θ/2)), rồi quét xuôi / ngược để không vượt quá gia tốc."""
    seg = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        L = math.hypot(bx - ax, by - ay)
        if L > 0:
            seg.append((L, (bx - ax) / L, (by - ay) / L))
    n = len(seg)
    if n == 0:
        return 0.0
    vj = [0.0] * (n + 1)                                  # tốc độ tại các đỉnh; đỉnh 0 và n là đầu / cuối nét
    for i in range(1, n):
        cos_t = -(seg[i - 1][1] * seg[i][1] + seg[i - 1][2] * seg[i][2])
        if cos_t > 0.999999:                              # quay ngược hẳn
            continue
        if cos_t < -0.999999:                             # đi thẳng
            vj[i] = vmax
            continue
        sin_half = math.sqrt(0.5 * (1.0 - cos_t))
        vj[i] = min(vmax, math.sqrt(accel * junction * sin_half / (1.0 - sin_half)))
    for i in range(1, n + 1):                             # quét xuôi: không tăng tốc quá a trên đoạn trước
        vj[i] = min(vj[i], math.sqrt(vj[i - 1] ** 2 + 2 * accel * seg[i - 1][0]))
    for i in range(n - 1, -1, -1):                        # quét ngược: kịp giảm tốc trước đỉnh sau
        vj[i] = min(vj[i], math.sqrt(vj[i + 1] ** 2 + 2 * accel * seg[i][0]))
    return sum(move_time(seg[i][0], vj[i], vj[i + 1], vmax, accel) for i in range(n))


def fmt(v: float, precision: int) -> str:
    s = f"{v:.{precision}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def to_machine(x: float, y: float, machine: Params) -> tuple[float, float]:
    """ĐIỂM DUY NHẤT đổi tọa độ bản vẽ -> tọa độ máy (hướng trục đã xác nhận đúng 05/11/2026 với invert_y = false)."""
    return (x, machine.work_h - y) if machine.invert_y else (x, y)


def clean_strokes(strokes: list[Stroke], precision: int) -> tuple[list[Stroke], int]:
    """Làm tròn theo độ chính xác xuất, bỏ điểm trùng liên tiếp, bỏ nét < 2 điểm. Trả (nét, số nét bỏ)."""
    out: list[Stroke] = []
    dropped = 0
    for s in strokes:
        pts: Stroke = []
        for x, y in s:
            p = (round(x, precision), round(y, precision))
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(pts) >= 2:
            out.append(pts)
        else:
            dropped += 1
    return out, dropped


def build_gcode(strokes: list[Stroke], gp: Params, machine: Params) -> tuple[list[str], dict, list[dict]]:
    prec = gp.precision
    cleaned, dropped = clean_strokes(strokes, prec)
    if not cleaned:
        raise DrawError("empty_drawing", "Không còn nét nào sau khi làm sạch.")
    up, down = gp.pen_up_z, gp.pen_down_z
    # Cơ cấu bút hạ bằng trọng lực: hạ chậm (đáp nhẹ, đỡ gãy ngòi), nâng nhanh. Không đặt = hai chiều như nhau.
    down_feed = gp.pen_down_feed if gp.pen_down_feed is not None else gp.pen_feed
    use_g0 = gp.travel_feed >= machine.rapid_feed

    feed = {"cur": None}

    def f(value: float) -> str:      # chỉ ghi F khi đổi (F là modal); dòng G1 đầu tiên luôn có F
        if feed["cur"] == value:
            return ""
        feed["cur"] = value
        return f" F{fmt(value, 3)}"

    def xy(p) -> str:
        mx, my = to_machine(p[0], p[1], machine)
        return f"X{fmt(mx, prec)} Y{fmt(my, prec)}"

    lines = ["G90 G21", f"G1 Z{fmt(up, 3)}{f(gp.pen_feed)}"]
    if gp.delay_up_s > 0:
        lines.append(f"G4 P{fmt(gp.delay_up_s, 3)}")
    draw_mm = travel_mm = 0.0
    prev = (0.0, 0.0)            # ước tính: bắt đầu từ gốc
    npts = 0
    xs, ys = [], []
    for s in cleaned:
        travel_mm += math.dist(prev, s[0])
        lines.append(f"G0 {xy(s[0])}" if use_g0 else f"G1 {xy(s[0])}{f(gp.travel_feed)}")
        lines.append(f"G1 Z{fmt(down, 3)}{f(down_feed)}")
        if gp.delay_down_s > 0:
            lines.append(f"G4 P{fmt(gp.delay_down_s, 3)}")
        for a, b in zip(s, s[1:]):
            draw_mm += math.dist(a, b)
            lines.append(f"G1 {xy(b)}{f(gp.draw_feed)}")
        lines.append(f"G1 Z{fmt(up, 3)}{f(gp.pen_feed)}")
        if gp.delay_up_s > 0:
            lines.append(f"G4 P{fmt(gp.delay_up_s, 3)}")
        prev = s[-1]
        npts += len(s)
        xs += [p[0] for p in s]
        ys += [p[1] for p in s]

    if len(lines) > MAX_LINES:
        raise DrawError("too_many_lines", f"G-code {len(lines)} dòng, vượt giới hạn {MAX_LINES}. "
                                          "Hãy tăng 'đơn giản hóa' hoặc giảm chi tiết.")
    longest = max(len(x) for x in lines)
    if longest > MAX_LINE_LEN:      # không xảy ra với G0/G1 thường; giữ làm chốt chặn
        raise DrawError("bad_gcode", f"Dòng G-code dài {longest} ký tự (tối đa {MAX_LINE_LEN}).")

    # Ước tính có gia tốc (12/11/2026: bản cũ chia quãng đường cho tốc độ, máy thật lâu hơn 1,7–1,9 lần).
    # Mỗi nét dừng ở đầu / cuối (nâng, hạ bút); qua góc giảm tốc theo junction; G4 chờ thêm đúng số giây.
    eff_travel = min(gp.travel_feed, machine.rapid_feed)
    acc = EST_ACCEL_MM_S2
    dz = abs(up - down)
    z_one = move_time(dz, 0, 0, gp.pen_feed / 60, acc) + move_time(dz, 0, 0, down_feed / 60, acc)
    draw_s = sum(path_time(s, gp.draw_feed / 60, acc) for s in cleaned)
    travel_s, prev = 0.0, (0.0, 0.0)
    for s in cleaned:
        travel_s += move_time(math.dist(prev, s[0]), 0, 0, eff_travel / 60, acc)
        prev = s[-1]
    est = (draw_s + travel_s + len(cleaned) * (z_one + EST_LIFT_OVERHEAD_S)
           + len(cleaned) * (gp.delay_up_s + gp.delay_down_s) + gp.delay_up_s)
    stats = {
        "strokes": len(cleaned), "points": npts, "lines": len(lines),
        "draw_mm": round(draw_mm, 2), "travel_mm": round(travel_mm, 2),
        "pen_lifts": len(cleaned), "est_seconds": round(est, 1),   # có gia tốc (EST_ACCEL_MM_S2)
        "bounds": {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)},
    }
    warnings: list[dict] = []
    if dropped:
        warnings.append({"code": "dropped_strokes", "count": dropped})
    if gp.draw_feed > machine.rapid_feed or gp.travel_feed > machine.rapid_feed:
        warnings.append({"code": "feed_above_rapid", "count": 1})
    return lines, stats, warnings
