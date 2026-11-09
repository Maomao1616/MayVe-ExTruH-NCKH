"""Sinh G-code cho các tờ thử máy (docs/07_THU_NGHIEM.md mục 6): nhấc bút, mất bước, gia tốc / góc, tốc độ vẽ, vệt kéo.

Chỉ dùng thư viện chuẩn và KHÔNG import gì của dự án: `tools/make_test_gcode.py` nạp thẳng tệp này (chạy được khi chưa cài
thư viện ảnh), còn backend (`POST /api/draw/testsheet`, tab Cài đặt → "Tờ thử / hiệu chỉnh") dùng cùng các hàm để tạo bản thảo.
Mọi tệp nằm trong vùng máy, chỉ dùng G0 / G1 / G4, không đổi gốc tọa độ, không Home.
"""
from __future__ import annotations

import itertools

WORK_W, WORK_H = 285.0, 318.0


def num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


class Writer:
    def __init__(self, up: float, down: float, pen_feed: float, draw_feed: float, *, delay_up: float, delay_down: float,
                 down_feed: float | None = None):
        self.up, self.down, self.pen_feed, self.draw_feed = up, down, pen_feed, draw_feed
        self.down_feed = down_feed if down_feed is not None else pen_feed      # hạ bút chậm hơn nâng: đỡ nảy, đỡ loang mực
        self.delay_up, self.delay_down = delay_up, delay_down
        self.lines = ["G90 G21", f"G1 Z{num(up)} F{num(pen_feed)}"]
        if delay_up > 0:
            self.lines.append(f"G4 P{num(delay_up)}")

    def comment(self, text: str) -> None:
        self.lines.append(f"; {text}")

    def travel(self, x: float, y: float) -> None:
        self.lines.append(f"G0 X{num(x)} Y{num(y)}")

    def pen_down(self) -> None:
        self.lines.append(f"G1 Z{num(self.down)} F{num(self.down_feed)}")
        if self.delay_down > 0:
            self.lines.append(f"G4 P{num(self.delay_down)}")

    def pen_up(self) -> None:
        self.lines.append(f"G1 Z{num(self.up)} F{num(self.pen_feed)}")
        if self.delay_up > 0:
            self.lines.append(f"G4 P{num(self.delay_up)}")

    def line_to(self, x: float, y: float, feed: float | None = None) -> None:
        self.lines.append(f"G1 X{num(x)} Y{num(y)} F{num(feed or self.draw_feed)}")

    def stroke(self, points: list[tuple[float, float]], feed: float | None = None) -> None:
        self.travel(*points[0])
        self.pen_down()
        for x, y in points[1:]:
            self.line_to(x, y, feed)
        self.pen_up()

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def lift_cost(up: float, down: float, pen_feed: float, draw_feed: float, *, delay: float, up_z: float | None = None,
              strokes: int = 100, down_feed: float | None = None) -> str:
    """7.1: 100 gạch ngắn 2 mm (lưới 10 × 10). Thời gian thật ÷ 100 ≈ một chu kỳ nhấc + hạ + chờ."""
    w = Writer(up_z if up_z is not None else up, down, pen_feed, draw_feed, delay_up=delay, delay_down=delay,
               down_feed=down_feed)
    w.comment(f"7.1 chi phi nhac but: {strokes} gach 2 mm, cho {delay} s, Z nhac {num(w.up)}")
    for i in range(strokes):
        x, y = 20 + (i % 10) * 8, 20 + (i // 10) * 8
        w.stroke([(x, y), (x + 2, y)])
    return w.text()


# --- Tờ nhấc bút nhiều hàng: mỗi hàng một tổ hợp (Z nhấc, chờ, tốc độ hạ) -----------------------------------------
LIFT_MAX_ROWS = 24
LIFT_STROKES = 20                 # gạch 2 mm mỗi hàng
LIFT_ROW_PITCH = 10.0
LIFT_Y0 = 20.0
LIFT_X_DOTS, LIFT_DOT_PITCH = 10.0, 3.0
LIFT_X_STROKES, LIFT_STROKE_PITCH = 95.0, 6.0


def lift_rows(ups, delays, down_feeds, *, pen_feed: float, down: float, draw_feed: float) -> list[dict]:
    """Các tổ hợp (hàng 1, 2, 3...): Z nhấc chạy chậm nhất trong vòng ngoài cùng, tốc độ hạ nhanh nhất ở vòng trong."""
    rows = []
    for n, (up, delay, dfeed) in enumerate(itertools.product(sorted(ups), sorted(delays), sorted(down_feeds)), start=1):
        # chu kỳ một gạch: nhấc + hạ + 2 lần chờ + 2 mm gạch (di chuyển G0 4 mm tính thêm ở tốc độ bút)
        cycle = ((up - down) / pen_feed + (up - down) / dfeed + 2 * 2 / draw_feed + 4 / pen_feed) * 60 + 2 * delay
        rows.append({"n": n, "up": up, "delay": delay, "down_feed": dfeed, "est_s": round(cycle * LIFT_STROKES, 1)})
    return rows


def lift_sheet(rows: list[dict], down: float, pen_feed: float, draw_feed: float) -> str:
    """Hàng k có k chấm ở đầu hàng (để biết là hàng nào), rồi LIFT_STROKES gạch 2 mm vẽ với đúng thông số của hàng.
    Chạy một lần, nhìn trên giấy hàng nào gạch đều, không kéo vệt, không hụt đầu nét, rồi bấm "Dùng hàng N"."""
    safe_up = max(r["up"] for r in rows)
    out: list[str] = []
    label = Writer(safe_up, down, pen_feed, draw_feed, delay_up=0.1, delay_down=0.1, down_feed=2000.0)
    label.comment("to nhac but: hang k co k cham o dau hang")
    for r in rows:
        y = LIFT_Y0 + (r["n"] - 1) * LIFT_ROW_PITCH
        for j in range(r["n"]):
            label.stroke([(LIFT_X_DOTS + j * LIFT_DOT_PITCH, y), (LIFT_X_DOTS + j * LIFT_DOT_PITCH + 0.4, y)])
    out += label.lines
    for r in rows:
        y = LIFT_Y0 + (r["n"] - 1) * LIFT_ROW_PITCH
        w = Writer(r["up"], down, pen_feed, draw_feed, delay_up=r["delay"], delay_down=r["delay"], down_feed=r["down_feed"])
        w.comment(f"hang {r['n']}: Z nhac {num(r['up'])}, cho {num(r['delay'])} s, toc do ha {num(r['down_feed'])}")
        for i in range(LIFT_STROKES):
            x = LIFT_X_STROKES + i * LIFT_STROKE_PITCH
            w.stroke([(x, y), (x + 2, y)])
        out += w.lines
    return "\n".join(out) + "\n"


def lost_steps(up: float, down: float, pen_feed: float, draw_feed: float, *, round_trips: int = 60,
               down_feed: float | None = None) -> str:
    """7.2: vẽ dấu + ở góc, di chuyển nhanh qua lại khắp vùng, quay về vẽ lại dấu +. Hai dấu trùng khít = không mất bước."""
    w = Writer(up, down, pen_feed, draw_feed, delay_up=0.1, delay_down=0.1, down_feed=down_feed)
    w.comment("7.2 mat buoc: ve dau + o (15,15), chay nhanh qua lai, ve lai dau + o cung cho")

    def cross() -> None:
        w.stroke([(8, 15), (22, 15)])
        w.stroke([(15, 8), (15, 22)])

    cross()
    for _ in range(round_trips):
        w.travel(270, 300)
        w.travel(15, 300)
        w.travel(270, 15)
        w.travel(15, 15)
    cross()
    return w.text()


def accel(up: float, down: float, pen_feed: float, draw_feed: float, *, pitch: float = 2.0,
          down_feed: float | None = None) -> str:
    """7.3: răng cưa đoạn ngắn: soi gợn sóng sau góc (rung) và đo thời gian ở các gia tốc khác nhau.

    Vẽ ở vị trí cố định (y 30–90 mm): mỗi lần chạy dùng MỘT tờ giấy mới, đừng chồng với 7.4."""
    w = Writer(up, down, pen_feed, draw_feed, delay_up=0.1, delay_down=0.1, down_feed=down_feed)
    w.comment(f"7.3 gia toc: rang cua buoc {num(pitch)} mm, 3 hang")
    for row in range(3):
        y0 = 30 + row * 25
        pts = [(30.0, y0)]
        x = 30.0
        for i in range(60):
            x += pitch
            pts.append((x, y0 + (10 if i % 2 == 0 else 0)))
        w.stroke(pts)
    return w.text()


def speed_strips(up: float, down: float, pen_feed: float, speeds=(3000, 4000, 5000, 6000),
                 down_feed: float | None = None) -> str:
    """7.4: mỗi tốc độ 3 đường thẳng dài 60 mm. Từ trên xuống: tốc độ tăng dần theo thứ tự trong `speeds`.

    Vẽ ở vị trí cố định: dùng MỘT tờ giấy mới, đừng chồng với 7.3."""
    w = Writer(up, down, pen_feed, speeds[0], delay_up=0.1, delay_down=0.1, down_feed=down_feed)
    w.comment("7.4 toc do ve: tu tren xuong " + ", ".join(str(s) for s in speeds) + " mm/phut, moi toc do 3 duong")
    y = 30.0
    for speed in speeds:
        for _ in range(3):
            w.stroke([(40.0, y), (100.0, y)], feed=speed)
            y += 4
        y += 8
    return w.text()


def drag_test(up: float, down: float, pen_feed: float, draw_feed: float, *, delay: float, trips: int = 5,
              down_feed: float | None = None) -> str:
    """7.5: bút có kéo vệt khi di chuyển xa không. Chấm một chấm, chạy G0 dài 240 mm sang chấm kia, rồi quay lại.

    Bút nâng đủ cao thì chỉ có các chấm; còn vệt mảnh nối hai chấm = bút chưa rời giấy (Z nhấc thấp,
    chờ nâng ngắn, giấy cong). Mỗi lần chạy dùng MỘT mức chờ; đổi Z nhấc bằng --up."""
    w = Writer(up, down, pen_feed, draw_feed, delay_up=delay, delay_down=delay, down_feed=down_feed)
    w.comment(f"7.5 keo vet: {trips} luot di-ve 240 mm, cho {delay} s, Z nhac {num(up)}")
    for i in range(trips):
        y = 30 + i * 12
        w.stroke([(20, y), (20.4, y)])
        w.stroke([(260, y), (260.4, y)])
    return w.text()


def build_all(up: float, down: float, pen_feed: float, draw_feed: float, down_feed: float | None = None) -> dict[str, str]:
    kw = {"down_feed": down_feed}
    files = {
        "7.1-cho-0.20s.gcode": lift_cost(up, down, pen_feed, draw_feed, delay=0.2, **kw),
        "7.1-cho-0.10s.gcode": lift_cost(up, down, pen_feed, draw_feed, delay=0.1, **kw),
        "7.1-cho-0.05s.gcode": lift_cost(up, down, pen_feed, draw_feed, delay=0.05, **kw),
        "7.2-mat-buoc.gcode": lost_steps(up, down, pen_feed, draw_feed, **kw),
        "7.3-gia-toc-rang-cua.gcode": accel(up, down, pen_feed, draw_feed, **kw),
        "7.4-toc-do-ve.gcode": speed_strips(up, down, pen_feed, **kw),
        "7.5-keo-vet-cho-0.05s.gcode": drag_test(up, down, pen_feed, draw_feed, delay=0.05, **kw),
        "7.5-keo-vet-cho-0.10s.gcode": drag_test(up, down, pen_feed, draw_feed, delay=0.1, **kw),
    }
    # Z nhấc thấp hơn (chỉ khi còn khoảng hở hợp lý giữa Z nhấc và Z hạ)
    for z in (2.0, 1.5):
        if z > down + 0.5 and z < up:
            files[f"7.1-nhac-Z{num(z)}-cho-0.10s.gcode"] = lift_cost(up, down, pen_feed, draw_feed, delay=0.1, up_z=z, **kw)
    return files
