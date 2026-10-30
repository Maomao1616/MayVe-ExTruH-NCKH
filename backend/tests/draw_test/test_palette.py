import io

import numpy as np
import pytest
from PIL import Image

from app.services.drawing import palette, raster
from app.services.drawing.store import TASKS


def bands_png(colors, w=300, h=200):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    n = len(colors)
    for i, c in enumerate(colors):
        arr[:, i * w // n:(i + 1) * w // n] = c
    b = io.BytesIO(); Image.fromarray(arr, "RGB").save(b, "PNG")
    return b.getvalue(), arr


def test_split_finds_the_bands_dark_to_light():
    _, arr = bands_png([(10, 10, 60), (200, 40, 40), (240, 240, 120)])
    regions = palette.split(arr, 3, skip_background=False)
    assert len(regions) == 3
    assert [r.lightness for r in regions] == sorted(r.lightness for r in regions)
    assert all(r.mask.sum() > 0.25 * arr.shape[0] * arr.shape[1] for r in regions)


def test_skip_background_drops_the_bright_paper_color():
    _, arr = bands_png([(20, 20, 20), (250, 250, 250)])
    regions = palette.split(arr, 2, skip_background=True)
    assert len(regions) == 1 and regions[0].lightness < 40


def test_flat_image_gives_one_region():
    _, arr = bands_png([(90, 90, 90)])
    assert len(palette.split(arr, 4, skip_background=False)) == 1


def test_multicolor_import_makes_one_layer_per_color_with_colors():
    data, _ = bands_png([(10, 10, 60), (200, 40, 40), (60, 160, 60)])
    out = raster.import_raster(data, "x", {"palette": {"mode": "multi", "colors": 3},
                                           "raster": {"quality": "draft"}, "layout": {"paper": "a5"}})
    layers = out["source"]["layers"]
    assert len(layers) == 3 and all(l["color"].startswith("#") and l["strokes"] > 0 for l in layers)
    assert len({l["color"] for l in layers}) == 3
    assert out["warnings"] == []
    ids = [l.id for l in TASKS.get(out["task"]).layers]
    assert [i.split("-")[0] for i in ids] == ["1", "2", "3"]
    assert all(i.endswith("-" + l["color"][1:]) for i, l in zip(ids, layers))      # mã màu nằm trong tên lớp


def test_multicolor_with_outline_style_warns_and_stays_mono():
    data, _ = bands_png([(10, 10, 10), (250, 250, 250)])
    out = raster.import_raster(data, "x", {"palette": {"mode": "multi"}, "style": {"kind": "outline"},
                                           "layout": {"paper": "a5"}})
    assert out["warnings"] == [{"code": "palette_ignored", "count": 1}] and len(out["source"]["layers"]) == 1
