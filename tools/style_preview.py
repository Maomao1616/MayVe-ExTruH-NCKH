r"""Vẽ thử một ảnh với nhiều kiểu tô / preset ra PNG để so (không cần mở giao diện), kèm số nét, thời gian ước tính.

    cd backend && .venv\Scripts\python.exe ..\tools\style_preview.py anh.jpg [--paper a5] [--pen 0.5]
        [--kinds crosshatch,crosshatch_flow] [--set style.outline_overlay=true --set raster.gamma=1.1] [--out ..\export\preview]

- Mỗi kiểu một ảnh <tên ảnh>_<khổ>_<kiểu>.png (nét đen, nét bút đúng bề rộng) + một ảnh ghép tất cả cạnh nhau.
- Kiểu crosshatch_flow: đường viền bao khối tô ĐỎ để thấy chúng nằm ở đâu.
- --set nhóm.tham_số=giá_trị (nhóm: raster / style / layout / optimize, tên tham số như spec.py) ghi đè cho mọi kiểu.
- Ảnh mẫu không có tệp: dùng "astronaut" hoặc "cat" (skimage). Mặc định G-code: 8000, Z3 / 0, hạ 2000, chờ 0.
Mặc định ghi vào export/preview/ (không lên Git).
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.drawing import gcode, raster, spec, styles     # noqa: E402

PX_PER_MM = 8                    # độ phân giải ảnh xem trước
SHEET_W = 2400                   # bề rộng ảnh ghép (điểm ảnh)


def load(src: str) -> tuple[np.ndarray, str]:
    if src in ("astronaut", "cat"):
        from skimage import data
        return (data.astronaut() if src == "astronaut" else data.chelsea()), src
    return np.array(Image.open(src).convert("RGB")), Path(src).stem


def parse_value(v: str):
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return v


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--paper", default="a5")
    ap.add_argument("--pen", type=float, default=0.5, help="bề rộng nét (mm), như ô Bút vẽ")
    ap.add_argument("--kinds", default="crosshatch,crosshatch_flow", help=f"cách nhau dấu phẩy; có: {', '.join(spec.STYLES)}")
    ap.add_argument("--set", action="append", default=[], help="nhóm.tham_số=giá_trị")
    ap.add_argument("--out", default=str(ROOT / "export" / "preview"))
    a = ap.parse_args()
    img, name = load(a.image)
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "PNG")
    data = buf.getvalue()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    machine = spec.parse("machine", {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 10000})
    gp = spec.parse("gcode", {"pen_up_z": 3, "pen_down_z": 0, "pen_down_feed": 2000})

    captured: dict = {}
    real = styles.crosshatch_flow_groups

    def spy(*args, **kw):                                    # giữ lại đường theo dáng để tô đỏ
        groups = real(*args, **kw)
        captured["curves"] = groups[-1]                      # nhóm cuối: đường viền bao khối (từ 14/11/2026)
        return groups

    styles.GROUPERS["crosshatch_flow"] = spy
    tiles = []
    for kind in [k.strip() for k in a.kinds.split(",") if k.strip()]:
        opts = {"raster": {"pen_width_mm": a.pen}, "style": {"kind": kind, "levels": 5},
                "layout": {"paper": a.paper, "margin_mm": 5}}
        for item in a.set:
            key, _, value = item.partition("=")
            group, _, param = key.partition(".")
            opts.setdefault(group, {})[param] = parse_value(value)
        captured.clear()
        t0 = time.time()
        layers, frame, info, _ = raster.build_raster(data, "t", opts)
        dt = time.time() - t0
        strokes = [s for layer in layers for s in layer.strokes]
        _, st, _ = gcode.build_gcode(strokes, gp, machine)
        k = PX_PER_MM
        canvas = np.full((int(frame.h * k) + 4, int(frame.w * k) + 4, 3), 255, np.uint8)
        width = max(1, int(round(a.pen * k)))
        for s in strokes:
            cv2.polylines(canvas, [np.int32(np.asarray(s) * k)], False, (0, 0, 0), width, cv2.LINE_AA)
        for s in captured.get("curves", []):
            cv2.polylines(canvas, [np.int32(np.asarray(s) * k)], False, (0, 0, 220), width, cv2.LINE_AA)
        path = out / f"{name}_{a.paper}_{kind}.png"
        cv2.imwrite(str(path), canvas)
        label = f"{kind}  {st['strokes']} nét  {st['est_seconds'] / 60:.1f} phút"
        cv2.putText(canvas, label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 0, 0), 2)
        tiles.append(canvas)
        print(f"{kind:16} nét {st['strokes']:5}  nhấc bút {st['pen_lifts']:5}  ước tính {st['est_seconds'] / 60:5.1f} phút  "
              f"mực {st['draw_mm'] / 1000:5.1f} m  dòng {st['lines']:6} ({st.get('arcs', 0)} cung)  xử lý {dt:.1f} s -> {path.name}")
    if len(tiles) > 1:
        h = min(t.shape[0] for t in tiles)
        sheet = np.hstack([t[:h] for t in tiles])
        sheet = cv2.resize(sheet, None, fx=SHEET_W / sheet.shape[1], fy=SHEET_W / sheet.shape[1], interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / f"{name}_{a.paper}_so-sanh.jpg"), sheet)
        print(f"ảnh ghép: {out / f'{name}_{a.paper}_so-sanh.jpg'}")


if __name__ == "__main__":
    main()
