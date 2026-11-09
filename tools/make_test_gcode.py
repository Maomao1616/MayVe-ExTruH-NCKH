"""Sinh sẵn các tệp G-code cho các bài thử máy (docs/07_THU_NGHIEM.md mục 6). Chỉ dùng thư viện chuẩn.

    python tools/make_test_gcode.py                 # ghi vào export/test-gcode/ (không lên Git)
    python tools/make_test_gcode.py --up 3 --down 0 --pen-feed 3000 --out thu-muc-khac

Nạp từng tệp ở tab Điều khiển → Xem trước → Chạy như mọi G-code khác. Z lấy theo hồ sơ máy (mặc định 3 / 0).
Mọi tệp nằm trong vùng 285 × 318 mm, chỉ dùng G0 / G1 / G4, không đổi gốc tọa độ, không Home.

Từ 09/11/2026 các bộ sinh nằm ở backend/app/services/drawing/testgcode.py (dùng chung với giao diện: Cài đặt → "Tờ thử /
hiệu chỉnh" tạo thẳng bản thảo, khỏi chạy lệnh tay). Tệp này chỉ còn là lớp vỏ dòng lệnh; tên hàm giữ nguyên.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Nạp theo đường dẫn tệp (không `import app...`): chạy được cả khi chưa cài thư viện ảnh của backend.
_spec = importlib.util.spec_from_file_location("testgcode", ROOT / "backend" / "app" / "services" / "drawing" / "testgcode.py")
_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)

WORK_W, WORK_H = _core.WORK_W, _core.WORK_H
num, Writer = _core.num, _core.Writer
lift_cost, lost_steps, accel = _core.lift_cost, _core.lost_steps, _core.accel
speed_strips, drag_test, build_all = _core.speed_strips, _core.drag_test, _core.build_all


def main() -> None:
    ap = argparse.ArgumentParser(description="Sinh G-code cho các bài thử tốc độ (docs/07_THU_NGHIEM.md mục 6).")
    ap.add_argument("--up", type=float, default=3.0, help="Z khi nâng bút (mm), mặc định 3")
    ap.add_argument("--down", type=float, default=0.0, help="Z khi hạ bút (mm), mặc định 0")
    ap.add_argument("--pen-feed", type=float, default=3000.0, help="tốc độ nâng bút (mm/phút), mặc định 3000")
    ap.add_argument("--down-feed", type=float, default=2000.0, help="tốc độ hạ bút (mm/phút), mặc định 2000")
    ap.add_argument("--draw-feed", type=float, default=5000.0, help="tốc độ vẽ (mm/phút), mặc định 5000")
    ap.add_argument("--out", default=str(ROOT / "export" / "test-gcode"), help="thư mục ghi (mặc định export/test-gcode)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in build_all(args.up, args.down, args.pen_feed, args.draw_feed, args.down_feed).items():
        (out / name).write_text(text, encoding="utf-8")
        print(f"{name}: {text.count(chr(10))} dòng")
    print(f"Đã ghi vào {out}")


if __name__ == "__main__":
    main()
