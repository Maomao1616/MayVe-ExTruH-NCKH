import json

import numpy as np
import pytest

from app.services.drawing import optimize, svg_in
from app.services.drawing.errors import DrawError
from app.services.drawing.shapes import Layer
from app.services.drawing.store import TASKS


class FakeLC:
    def __init__(self, lines):
        self.lines = lines


class FakeDoc:
    def __init__(self, layers, page=None):
        self.layers = layers
        self.page_size = page


def seg(*pts):
    return np.array([complex(x, y) for x, y in pts])


def test_px_to_mm_and_layer_order():
    doc = FakeDoc({2: FakeLC([seg((0, 0), (96, 0))]), 1: FakeLC([seg((0, 0), (0, 96))])})
    layers, meta = svg_in.document_to_layers(doc)
    assert [l.id for l in layers] == ["1", "2"]                       # theo id lớp tăng dần
    assert layers[1].strokes[0][1] == (pytest.approx(25.4), pytest.approx(0))    # 96 px = 1 inch = 25,4 mm
    assert [m["id"] for m in meta] == ["1", "2"]


def test_empty_layers_and_single_point_lines_are_skipped():
    doc = FakeDoc({1: FakeLC([]), 2: FakeLC([seg((1, 1))]), 3: FakeLC([seg((0, 0), (1, 1))])})
    layers, _ = svg_in.document_to_layers(doc)
    assert [l.id for l in layers] == ["3"]


def test_layer_stats_counts_draw_and_pen_up():
    layers = [Layer("1", [[(0, 0), (10, 0)], [(10, 5), (20, 5)]])]
    st = svg_in.layer_stats(layers)
    assert st == {"strokes": 2, "points": 4, "draw_mm": 20.0, "pen_up_mm": 5.0}


def test_svg_is_validated_before_vpype_is_touched():
    for data, code in ((b"hello", "bad_svg"), (b"\xff\xfe\x00", "bad_svg"),
                       (b'<!DOCTYPE x [<!ENTITY a "b">]><svg></svg>', "bad_svg")):
        with pytest.raises(DrawError) as e:
            svg_in.read_svg(data, 0.1)
        assert e.value.code == code


def test_too_big_file_is_413(monkeypatch):
    monkeypatch.setattr(svg_in, "MAX_SVG_BYTES", 10)
    with pytest.raises(DrawError) as e:
        svg_in.read_svg(b"<svg>" + b"x" * 20, 0.1)
    assert e.value.code == "file_too_large" and e.value.status == 413


def test_import_glue_with_fake_vpype(monkeypatch):
    doc = FakeDoc({1: FakeLC([seg((0, 0), (96, 0)), seg((0, 48), (96, 48))])}, page=(960, 480))
    monkeypatch.setattr(svg_in, "read_svg", lambda data, q: doc)
    monkeypatch.setattr(optimize, "run", lambda d, p: d)
    r = svg_in.import_svg(b"<svg/>", {"frame": "page"}, {})
    src = r["source"]
    assert src["page_mm"] == {"w": pytest.approx(254.0), "h": pytest.approx(127.0)}
    assert src["frame"] == "page"
    assert src["optimize"]["before"]["strokes"] == 2 == src["optimize"]["after"]["strokes"]
    assert src["bounds"]["w"] == pytest.approx(25.4)
    parsed = TASKS.get(r["task"])
    assert parsed.frame.w == pytest.approx(254.0) and len(parsed.layers) == 1
    json.dumps(r)                                                     # phải trả được qua JSON


def test_frame_page_without_page_size_falls_back_with_warning(monkeypatch):
    doc = FakeDoc({1: FakeLC([seg((0, 0), (96, 0))])}, page=None)
    monkeypatch.setattr(svg_in, "read_svg", lambda data, q: doc)
    monkeypatch.setattr(optimize, "run", lambda d, p: d)
    r = svg_in.import_svg(b"<svg/>", {"frame": "page"}, {})
    assert r["source"]["frame"] == "content" and r["warnings"] == [{"code": "no_page_size", "count": 1}]


def test_empty_svg_and_empty_after_optimize(monkeypatch):
    monkeypatch.setattr(svg_in, "read_svg", lambda data, q: FakeDoc({1: FakeLC([])}))
    with pytest.raises(DrawError) as e:
        svg_in.import_svg(b"<svg/>")
    assert e.value.code == "empty_drawing"
    full = FakeDoc({1: FakeLC([seg((0, 0), (96, 0))])})
    monkeypatch.setattr(svg_in, "read_svg", lambda data, q: full)
    monkeypatch.setattr(optimize, "run", lambda d, p: FakeDoc({1: FakeLC([])}))
    with pytest.raises(DrawError) as e:
        svg_in.import_svg(b"<svg/>")
    assert e.value.code == "empty_drawing"


# ---- Dùng vpype THẬT (chạy ở máy bạn; bị bỏ qua nếu chưa cài) ----
SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100">
<rect x="10" y="10" width="80" height="80" fill="none" stroke="black"/>
<line x1="0" y1="50" x2="20" y2="50" stroke="black"/>
<line x1="20" y1="50" x2="40" y2="50" stroke="black"/>
</svg>"""


def test_real_vpype_reads_svg_in_mm():
    pytest.importorskip("vpype")
    doc = svg_in.read_svg(SVG, 0.1)
    layers, _ = svg_in.document_to_layers(doc)
    assert layers and sum(len(l.strokes) for l in layers) >= 2
    xs = [p[0] for l in layers for s in l.strokes for p in s]
    assert max(xs) == pytest.approx(90, abs=0.5)           # viewBox 100 đơn vị cho 100 mm -> 1 đơn vị = 1 mm


def test_real_vpype_optimize_merges_touching_lines():
    pytest.importorskip("vpype_cli")
    r = svg_in.import_svg(SVG, {"frame": "page"}, {})
    opt = r["source"]["optimize"]
    assert opt["after"]["strokes"] < opt["before"]["strokes"]       # hai đoạn thẳng hàng nối thành một
    assert r["source"]["page_mm"]["w"] == pytest.approx(100, abs=0.5)
    TASKS.drop(r["task"])
