"""Sinh số chuẩn từ backend cho frontend/tests/imageprep.test.mjs (chạy lại khi đổi tone.py hoặc raster_in.py).
Chạy (đã bật venv của backend):  python frontend/tests/fixtures/make_image_fixtures.py"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
from app.services.drawing import raster_in, spec, tone  # noqa: E402

out = Path(__file__).resolve().parent


def side(refw, refh, aw, ah, pen, override=None):
    s = min(refw / aw, refh / ah)
    cap = max(aw, ah, raster_in.UPSCALE_TO_PX)
    return raster_in.work_side_px(max(aw * s, ah * s), pen, "final", override, cap)


sides = [{"ref": [rw, rh], "px": [aw, ah], "pen": pen, "override": ov, "side": side(rw, rh, aw, ah, pen, ov)}
         for rw, rh, aw, ah, pen, ov in [(200, 287, 1200, 1600, 0.4, None), (200, 287, 4000, 3000, 0.2, None),
                                         (60, 40, 4000, 3000, 0.4, None), (285, 318, 6000, 4000, 0.1, None),
                                         (200, 287, 1200, 1600, 0.4, 1000), (138, 200, 3000, 2000, 0.4, None),
                                         (200, 287, 300, 200, 0.4, None)]]
(out / "side_cases.json").write_text(json.dumps(sides), encoding="utf-8")

g = np.clip(np.random.default_rng(3).normal(120, 25, (1, 400)), 0, 255).astype(np.uint8)
rows = []
for kw, st in [({}, {}), ({"auto_levels": False, "gamma": 1.4}, {}),
               ({"black_point": 40, "white_point": 210}, {"invert": True}),
               ({"auto_levels": True, "gamma": 0.7, "black_point": 10}, {}),
               ({"auto_levels": True}, {})]:
    d = tone.darkness(g, spec.parse("raster", kw), spec.parse("style", st))
    rows.append({"raster": kw, "style": st, "display": [int(round(255 * (1 - v))) for v in d[0]]})
(out / "tone_cases.json").write_text(json.dumps({"gray": g[0].tolist(), "rows": rows}), encoding="utf-8")
print("ok", len(sides), len(rows))
