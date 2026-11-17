r"""Đo sai tông của một kiểu tô trên ẢNH THẬT, trước / sau vòng sửa sai (backend/app/services/drawing/refine.py).

    cd backend && .venv\Scripts\python.exe ..\tools\ink_real.py ANH.jpg crosshatch [--pen 0.5] [--passes 0,1,2,3]

Chạy đúng chuỗi của app (đọc ảnh vào khung A4 trừ lề → chỉnh tông → Field → kiểu tô), dựng ảnh mực với bề rộng nét thật bằng
refine.ink_cover (đã đối chiếu diện tích hợp nét tính bằng shapely: lệch -1…-3 %), làm mờ cỡ 2 mm, rồi so với độ phủ kiểu tô
định vẽ. In: sai số tuyệt đối, độ lệch trung bình (âm = thiếu mực), chiều dài nét, số nét, thời gian vẽ ước tính, và độ lệch
theo từng dải độ đậm mong muốn (để thấy thiếu / thừa mực ở vùng sáng hay vùng tối). Ảnh không được ghi ra đâu cả.

Giới hạn: đo CHỈ độ phủ ở cỡ ~2 mm, không đo vẻ đẹp, độ sắc nét hay mực loang trên giấy (xem docs/07 để thử bằng giấy).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.drawing import raster_in, refine, spec, styles, tone    # noqa: E402
from app.services.drawing.hatch import Field                              # noqa: E402

BINS = ((0.0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.0))
BOX_MM = (200.0, 287.0)                                                   # khung A4 trừ lề 5 mm


def load_field(path: str, pen: float, style: dict):
    rp = spec.parse("raster", {"pen_width_mm": pen})
    sp = spec.parse("style", style)
    img = raster_in.load(Path(path).read_bytes(), rp, BOX_MM[0], BOX_MM[1], None, color=False)
    dark = tone.apply_subject(tone.darkness(img.gray, rp, sp, None), rp)
    return Field(dark, img.width_mm, img.height_mm, None), sp


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("kind", nargs="?", default="crosshatch", choices=sorted(styles.REFINE_KINDS))
    ap.add_argument("--pen", type=float, default=0.5, help="bề rộng nét đo trên giấy (mm)")
    ap.add_argument("--passes", default="0,1,2,3", help="các số lượt sửa sai cần so, cách nhau dấu phẩy")
    a = ap.parse_args()
    line_w = styles.LINE_WIDTH_RATIO * a.pen
    print(f"{Path(a.image).name} · {a.kind} · bút {a.pen} mm")
    for passes in (int(p) for p in a.passes.split(",")):
        f, sp = load_field(a.image, a.pen, {"kind": a.kind, "outline_overlay": False, "refine_passes": passes})
        t = time.time()
        strokes = styles.fill(f, sp, a.pen, None, overlay=False)
        dt = time.time() - t
        want = np.clip(styles.tone_cover(f.dark, a.kind), 0.0, styles.MAX_COVERAGE)
        cover, cell = refine.ink_cover(strokes, f.width_mm, f.height_mm, line_w)
        sigma = refine.REFINE_SIGMA_MM / cell
        target = cv2.resize(want, (cover.shape[1], cover.shape[0]), interpolation=cv2.INTER_AREA)
        got, goal = cv2.GaussianBlur(cover, (0, 0), sigma), cv2.GaussianBlur(target, (0, 0), sigma)
        err = got - goal
        length = sum(float(np.hypot(*np.diff(np.asarray(s), axis=0).T).sum()) for s in strokes)
        minutes = (length / (8000 / 60) + len(strokes) * 0.05) / 60
        bins = "  ".join(f"{float(err[(goal >= lo) & (goal < hi)].mean()):+.3f}" if ((goal >= lo) & (goal < hi)).any() else "  -  "
                         for lo, hi in BINS)
        print(f"  sửa sai {passes}: sai {np.abs(err).mean():.4f} · lệch {err.mean():+.4f} · {length / 1000:6.1f} m · "
              f"{len(strokes):5d} nét · ~{minutes:5.1f} ph · tạo {dt:4.1f} s | lệch theo mức 0-.1 .1-.3 .3-.5 .5-.7 .7-1: {bins}")


if __name__ == "__main__":
    main()
