import io

import numpy as np
import pytest
from PIL import Image

from app.services.drawing import palette, raster, spec
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


# --- Tách mực theo bộ bút (22/11/2026) ---
def _share(rgb, ink_set, boost=0.0):
    arr = np.full((20, 20, 3), rgb, np.uint8)
    dark = np.full((20, 20), 0.8, np.float32)
    return {c: float(d.mean()) for c, _, d in palette.separate_inks(arr, dark, ink_set, boost)}


def test_ink_boost_gives_colour_pens_more_and_black_less_but_keeps_grey_black():
    dull = (80, 90, 120)                                   # xanh xám tối (tóc, bóng): mặc định đen lấn
    base, boosted = _share(dull, "kdn"), _share(dull, "kdn", 1.0)
    assert boosted["#141414"] < base["#141414"] * 0.6      # đen giảm rõ
    assert boosted["#1e2f6e"] > base["#1e2f6e"]            # navy được dùng nhiều hơn
    assert _share((90, 90, 90), "kdn", 1.0)["#141414"] > 0.6      # xám trung tính vẫn là bút đen


def test_separate_inks_gives_each_pen_its_own_color_of_the_image():
    kdn = _share((200, 40, 60), "kdn")                    # đỏ -> bút đỏ gần như một mình
    assert kdn["#c8283c"] > 0.6 and kdn["#141414"] < 0.1
    grey = _share((90, 90, 90), "kdn")                    # xám trung tính -> bút đen
    assert grey["#141414"] > 0.6
    purple = _share((110, 40, 120), "kdn")                # tím -> đỏ + navy cùng góp
    assert purple["#c8283c"] > 0.15 and purple["#1e2f6e"] > 0.15
    cmyk = _share((240, 215, 20), "cmyk")                 # vàng -> bút vàng
    assert cmyk["#f0d214"] > 0.6
    paper = _share((255, 255, 255), "kdn")                # giấy trắng -> không bút nào
    assert max(paper.values()) < 0.01


def test_inks_import_makes_one_layer_per_pen_light_to_dark_black_last():
    data, _ = bands_png([(15, 15, 15), (200, 40, 60), (30, 45, 120)])
    out = raster.import_raster(data, "x", {"palette": {"mode": "inks", "ink_set": "kdn"},
                                           "raster": {"quality": "draft", "auto_levels": False}, "layout": {"paper": "a5"}})
    colors = [l["color"] for l in out["source"]["layers"]]
    assert colors == ["#c8283c", "#1e2f6e", "#141414"] and out["warnings"] == []
    assert all(l["strokes"] > 0 for l in out["source"]["layers"])
    cmyk = raster.import_raster(data, "x", {"palette": {"mode": "inks", "ink_set": "cmyk"},
                                            "raster": {"quality": "draft", "auto_levels": False}, "layout": {"paper": "a5"}})
    assert [l["color"] for l in cmyk["source"]["layers"]][-1] == "#141414"      # bút đen vẽ sau cùng


def test_each_pen_can_have_its_own_line_width():
    """22/11/2026: bút mảnh (đen 0,28) vẽ nhiều nét hơn bút dày (0,38) trên cùng vùng; ô trống = ô Bút vẽ."""
    ramp = np.tile(np.linspace(250, 15, 300).astype(np.uint8)[None, :, None], (200, 1, 3))     # dải xám trắng -> đen (có tông thật)
    buf = io.BytesIO(); Image.fromarray(ramp, "RGB").save(buf, "PNG"); data = buf.getvalue()
    base = {"palette": {"mode": "inks", "ink_set": "kdn"}, "raster": {"quality": "draft", "auto_levels": False, "pen_width_mm": 0.4},
            "layout": {"paper": "a5"}}
    thick = raster.import_raster(data, "x", base)["source"]["layers"][-1]["strokes"]
    thin_opts = {**base, "palette": {"mode": "inks", "ink_set": "kdn", "ink_w3": 0.28}}
    thin = raster.import_raster(data, "x", thin_opts)["source"]["layers"][-1]["strokes"]
    assert thin > thick                                           # bút đen mảnh hơn thì dày nét hơn để đủ đậm
    assert spec.parse("palette", {"ink_w1": 0.38}).ink_w1 == 0.38 and spec.parse("palette", {}).ink_w2 is None
