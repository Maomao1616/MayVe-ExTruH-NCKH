"""optimize.group_levels: vẽ lần lượt từng mức đậm nhạt (nhạt → đậm, viền cuối), mỗi mức tự sắp xếp riêng."""
import io
import math

import numpy as np
import pytest
from PIL import Image

from app.services.drawing import raster, spec, styles
from app.services.drawing.hatch import Field

EDGES = (0.11, 0.34, 0.56, 0.79)             # ranh giới mức của 5 mức (xem level_plan)


def gradient_png(w=600, h=400):
    buf = io.BytesIO()
    Image.fromarray(np.tile(np.linspace(255, 0, w), (h, 1)).astype("uint8")).save(buf, "PNG")
    return buf.getvalue()


def build(data, kind="spiral", group=True, **style):
    opts = {"raster": {"pen_width_mm": 0.4, "auto_levels": False, "gamma": 1.0, "max_side_px": 600},
            "style": {"kind": kind, "levels": 5, "outline_overlay": False, **style},
            "optimize": {"group_levels": group}, "layout": {"paper": "a4", "margin_mm": 5}}
    return raster.build_raster(data, "t", opts)


def level_sequence(layers, info):
    """Mức (0..3) của từng nét theo thứ tự vẽ, suy từ vị trí ngang trên ảnh chuyển sắc trắng → đen (bỏ nét sát ranh giới)."""
    width = info["page_mm"]["w"]
    seq = []
    for layer in layers:
        for s in layer.strokes:
            x = float(np.mean([p[0] for p in s])) / width
            if not any(abs(x - e) < 0.04 for e in EDGES):
                seq.append(sum(x > e for e in EDGES))
    return seq


def changes(seq):
    return sum(1 for a, b in zip(seq, seq[1:]) if a != b)


def total_length(layers):
    return sum(math.dist(a, b) for l in layers for s in l.strokes for a, b in zip(s, s[1:]))


def test_default_is_on_and_can_be_turned_off():
    assert spec.parse("optimize", {}).group_levels is True
    assert spec.parse("optimize", {"group_levels": False}).group_levels is False


def test_spiral_draws_one_level_after_another_light_to_dark():
    layers, _, info, _ = build(gradient_png(), group=True)
    seq = level_sequence(layers, info)
    assert len(seq) > 100 and seq == sorted(seq)                          # mức chỉ tăng dần: nhạt → đậm
    assert changes(seq) == len(set(seq)) - 1                              # mỗi mức một lần liền, không quay lại


def test_without_grouping_levels_are_interleaved_like_before():
    layers, _, info, _ = build(gradient_png(), group=False)
    assert changes(level_sequence(layers, info)) > 20                     # vpype xáo trộn các mức để rút ngắn quãng nhấc bút


def test_grouping_changes_order_not_content():
    on, _, _, _ = build(gradient_png(), group=True)
    off, _, _, _ = build(gradient_png(), group=False)
    assert abs(total_length(on) - total_length(off)) / total_length(off) < 0.02    # cùng nét vẽ, chỉ khác thứ tự
    assert len(on) == len(off) == 1


@pytest.mark.parametrize("kind", ["zigzag", "wave"])
def test_other_styles_also_keep_level_order(kind):
    layers, _, info, _ = build(gradient_png(), kind=kind, group=True)
    seq = level_sequence(layers, info)
    assert seq and seq == sorted(seq)


def test_outline_overlay_is_drawn_last():
    dark = np.zeros((200, 300), dtype=np.float32)
    dark[60:140, 90:210] = 0.9                                            # một khối đậm có viền rõ
    f = Field(dark, 60.0, 40.0, np.stack([np.where(dark > 0, 20, 255).astype("uint8")] * 3, axis=-1))
    style = spec.parse("style", {"kind": "spiral", "levels": 5, "outline_overlay": True})
    groups = styles.fill_groups(f, style, 0.4)
    edge = styles.outline(f, style, 0.4)
    assert len(groups) >= 2 and edge and groups[-1] == edge               # nhóm cuối = viền
    assert styles.fill(f, style, 0.4) == [s for g in groups for s in g]   # fill() vẫn là bản phẳng của nhóm


def test_multi_colour_keeps_one_layer_per_colour_with_grouping():
    w, h = 400, 300
    rgb = np.zeros((h, w, 3), dtype="uint8")
    rgb[:, :200] = (230, 40, 40)                                          # nửa đỏ, nửa xanh, mỗi nửa chuyển đậm dần
    rgb[:, 200:] = (40, 60, 220)
    shade = np.tile(np.linspace(1.0, 0.25, w), (h, 1))[..., None]
    buf = io.BytesIO()
    Image.fromarray((rgb * shade).astype("uint8")).save(buf, "PNG")
    out = {}
    for group in (True, False):
        opts = {"raster": {"pen_width_mm": 0.4, "max_side_px": 400}, "style": {"kind": "spiral", "levels": 4, "outline_overlay": False},
                "palette": {"mode": "multi", "colors": 2}, "optimize": {"group_levels": group}, "layout": {"paper": "a5"}}
        layers, _, info, _ = raster.build_raster(buf.getvalue(), "t", opts)
        out[group] = [(l.id, len(l.strokes) > 0) for l in layers]
        assert info["layers"] and all(m["color"] for m in info["layers"])     # mã màu vẫn gắn đúng lớp
    assert out[True] == out[False] and len(out[True]) == 2 and all(ok for _, ok in out[True])
