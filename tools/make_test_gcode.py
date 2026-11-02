"""Sinh sẵn các tệp G-code cho 4 bài thử tốc độ (docs/KIEM_TRA_VE.md mục 7). Chỉ dùng thư viện chuẩn.

    python tools/make_test_gcode.py                 # ghi vào export/test-gcode/ (không lên Git)
    python tools/make_test_gcode.py --up 5 --down 0 --pen-feed 3000 --out thu-muc-khac

Nạp từng tệp ở tab Điều khiển → Xem trước → Chạy như mọi G-code khác. Z lấy theo hồ sơ máy (mặc định 5 / 0).
Mọi tệp nằm trong vùng 285 × 318 mm, chỉ dùng G0 / G1 / G4, không đổi gốc tọa độ, không Home.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK_W, WORK_H = 285.0, 318.0


def num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


class Writer:
    def __init__(self, up: float, down: float, pen_feed: float, draw_feed: float, *, delay_up: float, delay_down: float):
        self.up, self.down, self.pen_feed, self.draw_feed = up, down, pen_feed, draw_feed
        self.delay_up, self.delay_down = delay_up, delay_down
        self.lines = ["G90 G21", f"G1 Z{num(up)} F{num(pen_feed)}"]
        if delay_up > 0:
            self.lines.append(f"G4 P{num(delay_up)}")

    def comment(self, text: str) -> None:
        self.lines.append(f"; {text}")

    def travel(self, x: float, y: float) -> None:
        self.lines.append(f"G0 X{num(x)} Y{num(y)}")

    def pen_down(self) -> None:
        self.lines.append(f"G1 Z{num(self.down)} F{num(self.pen_feed)}")
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
              strokes: int = 100) -> str:
    """7.1: 100 gạch ngắn 2 mm (lưới 10 × 10). Thời gian thật ÷ 100 ≈ một chu kỳ nhấc + hạ + chờ."""
    w = Writer(up_z if up_z is not None else up, down, pen_feed, draw_feed, delay_up=delay, delay_down=delay)
    w.comment(f"7.1 chi phi nhac but: {strokes} gach 2 mm, cho {delay} s, Z nhac {num(w.up)}")
    for i in range(strokes):
        x, y = 20 + (i % 10) * 8, 20 + (i // 10) * 8
        w.stroke([(x, y), (x + 2, y)])
    return w.text()


def lost_steps(up: float, down: float, pen_feed: float, draw_feed: float, *, round_trips: int = 60) -> str:
    """7.2: vẽ dấu + ở góc, di chuyển nhanh qua lại khắp vùng, quay về vẽ lại dấu +. Hai dấu trùng khít = không mất bước."""
    w = Writer(up, down, pen_feed, draw_feed, delay_up=0.1, delay_down=0.1)
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


def accel(up: float, down: float, pen_feed: float, draw_feed: float, *, pitch: float = 2.0) -> str:
    """7.3: răng cưa đoạn ngắn: soi gợn sóng sau góc (rung) và đo thời gian ở các gia tốc khác nhau."""
    w = Writer(up, down, pen_feed, draw_feed, delay_up=0.1, delay_down=0.1)
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


def speed_strips(up: float, down: float, pen_feed: float, speeds=(2000, 3000, 4500, 6000)) -> str:
    """7.4: mỗi tốc độ 3 đường thẳng dài 60 mm. Từ trên xuống: tốc độ tăng dần theo thứ tự trong `speeds`."""
    w = Writer(up, down, pen_feed, speeds[0], delay_up=0.1, delay_down=0.1)
    w.comment("7.4 toc do ve: tu tren xuong " + ", ".join(str(s) for s in speeds) + " mm/phut, moi toc do 3 duong")
    y = 30.0
    for speed in speeds:
        for _ in range(3):
            w.stroke([(40.0, y), (100.0, y)], feed=speed)
            y += 4
        y += 8
    return w.text()


def build_all(up: float, down: float, pen_feed: float, draw_feed: float) -> dict[str, str]:
    files = {
        "7.1-cho-0.20s.gcode": lift_cost(up, down, pen_feed, draw_feed, delay=0.2),
        "7.1-cho-0.10s.gcode": lift_cost(up, down, pen_feed, draw_feed, delay=0.1),
        "7.1-cho-0.05s.gcode": lift_cost(up, down, pen_feed, draw_feed, delay=0.05),
        "7.2-mat-buoc.gcode": lost_steps(up, down, pen_feed, draw_feed),
        "7.3-gia-toc-rang-cua.gcode": accel(up, down, pen_feed, draw_feed),
        "7.4-toc-do-ve.gcode": speed_strips(up, down, pen_feed),
    }
    # Z nhấc thấp hơn (chỉ khi còn khoảng hở hợp lý giữa Z nhấc và Z hạ)
    for z in (3.0, 2.0):
        if z > down + 0.5 and z < up:
            files[f"7.1-nhac-Z{num(z)}-cho-0.10s.gcode"] = lift_cost(up, down, pen_feed, draw_feed, delay=0.1, up_z=z)
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description="Sinh G-code cho các bài thử tốc độ (docs/KIEM_TRA_VE.md mục 7).")
    ap.add_argument("--up", type=float, default=5.0, help="Z khi nâng bút (mm), mặc định 5")
    ap.add_argument("--down", type=float, default=0.0, help="Z khi hạ bút (mm), mặc định 0")
    ap.add_argument("--pen-feed", type=float, default=3000.0, help="tốc độ trục Z (mm/phút), mặc định 3000")
    ap.add_argument("--draw-feed", type=float, default=3000.0, help="tốc độ vẽ (mm/phút), mặc định 3000")
    ap.add_argument("--out", default=str(ROOT / "export" / "test-gcode"), help="thư mục ghi (mặc định export/test-gcode)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in build_all(args.up, args.down, args.pen_feed, args.draw_feed).items():
        (out / name).write_text(text, encoding="utf-8")
        print(f"{name}: {text.count(chr(10))} dòng")
    print(f"Đã ghi vào {out}")


if __name__ == "__main__":
    main()
