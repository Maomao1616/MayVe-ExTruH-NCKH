import pytest

from app.services.drawing import layout as lo, spec
from app.services.drawing.errors import DrawError
from app.services.drawing.types import Box, Layer

M = spec.parse("machine", {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000})


def L(**kw):
    return spec.parse("layout", kw)


def test_contain_keeps_ratio_and_centers_in_box():
    pl = lo.plan(Box(0, 0, 200, 100), L(width_mm=100, height_mm=100), M)
    assert pl.sx == pl.sy == pytest.approx(0.5)
    # khung 100x100 ở giữa vùng 285x318 -> góc trên trái (92.5, 109); nội dung 100x50 căn giữa theo Y
    assert pl.map(0, 0) == (pytest.approx(92.5), pytest.approx(134.0))
    assert pl.map(200, 100) == (pytest.approx(192.5), pytest.approx(184.0))


def test_stretch_fills_box():
    pl = lo.plan(Box(0, 0, 200, 100), L(width_mm=100, height_mm=100, fit="stretch"), M)
    assert (pl.sx, pl.sy) == (pytest.approx(0.5), pytest.approx(1.0))


def test_source_origin_is_subtracted():
    pl = lo.plan(Box(50, 70, 10, 10), L(width_mm=10, height_mm=10), M)
    assert pl.map(50, 70) == (pytest.approx(137.5), pytest.approx(154.0))


def test_not_centered_uses_offset():
    pl = lo.plan(Box(0, 0, 10, 10), L(width_mm=10, height_mm=10, center=False, offset_x_mm=20, offset_y_mm=30), M)
    assert pl.map(0, 0) == (pytest.approx(20), pytest.approx(30))


def test_flip_mirrors_inside_the_box():
    pl = lo.plan(Box(0, 0, 10, 10), L(width_mm=10, height_mm=10, flip_x=True), M)
    assert pl.map(0, 0)[0] == pytest.approx(pl.box.x + 10)
    assert pl.map(10, 0)[0] == pytest.approx(pl.box.x)


def test_box_must_respect_margin():
    with pytest.raises(DrawError) as e:
        lo.plan(Box(0, 0, 10, 10), L(width_mm=10, height_mm=10, center=False, offset_x_mm=2, offset_y_mm=20), M)
    assert e.value.code == "box_out_of_area"          # lề 5 mặc định, offset_x=2 < 5


def test_box_bigger_than_work_area_is_rejected():
    with pytest.raises(DrawError) as e:
        lo.plan(Box(0, 0, 10, 10), L(width_mm=300, height_mm=100), M)
    assert e.value.code == "box_out_of_area"


def test_a4_portrait_fits_machine_with_margin():
    lo.plan(Box(0, 0, 10, 10), L(width_mm=210 - 10, height_mm=297 - 10), M)


def test_line_has_zero_height_but_still_scales():
    pl = lo.plan(Box(0, 0, 50, 0), L(width_mm=100, height_mm=100), M)
    assert pl.sx == pl.sy == pytest.approx(2.0)


def test_single_point_is_empty_drawing():
    with pytest.raises(DrawError) as e:
        lo.plan(Box(5, 5, 0, 0), L(), M)
    assert e.value.code == "empty_drawing"


def test_empty_layers_are_rejected():
    with pytest.raises(DrawError):
        lo.content_bounds([Layer("1", [])])


def test_all_layers_share_one_placement():
    a = Layer("a", [[(0, 0), (10, 0)]])
    b = Layer("b", [[(0, 0), (0, 10)], [(10, 10), (20, 20)]])
    box = lo.content_bounds([a, b])
    assert box == Box(0, 0, 20, 20)
    out = lo.place_layers([a, b], lo.plan(box, L(width_mm=100, height_mm=100), M), reverse=False)
    assert out[0].strokes[0][0] == out[1].strokes[0][0]      # cùng gốc (0,0) -> cùng chỗ


def test_reverse_reverses_stroke_order_only():
    a = Layer("a", [[(0, 0), (1, 0)], [(5, 5), (6, 5)]])
    pl = lo.plan(lo.content_bounds([a]), L(width_mm=60, height_mm=50), M)
    fwd = lo.place_layers([a], pl, False)[0].strokes
    rev = lo.place_layers([a], pl, True)[0].strokes
    assert rev == fwd[::-1]
