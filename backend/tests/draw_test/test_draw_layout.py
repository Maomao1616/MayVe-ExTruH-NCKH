import pytest

from app.services.drawing import layout as lo, spec
from app.services.drawing.errors import DrawError
from app.services.drawing.shapes import Box, Layer

M = spec.parse("machine", {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000})


def L(**kw):
    return spec.parse("layout", kw)


def code(fn, *a):
    with pytest.raises(DrawError) as e:
        fn(*a)
    return e.value.code


def test_paper_sits_at_machine_origin_top_left():
    pl = lo.plan(Box(0, 0, 10, 10), L(paper="a4"), M)
    assert pl.paper == Box(0, 0, 210, 297)
    assert lo.plan(Box(0, 0, 10, 10), L(paper="a6"), M).paper == Box(0, 0, 105, 148)


def test_default_box_fills_the_paper_inside_margin():
    pl = lo.plan(Box(0, 0, 10, 10), L(paper="a4", margin_mm=5), M)
    assert (pl.box.x, pl.box.y, pl.box.w, pl.box.h) == (5, 5, 200, 287)
    assert pl.sx == pl.sy == pytest.approx(20)          # contain: 200/10 (cạnh ngắn quyết định)


def test_contain_keeps_ratio_and_centers_inside_paper():
    pl = lo.plan(Box(0, 0, 200, 100), L(width_mm=100, height_mm=100), M)
    assert pl.sx == pl.sy == pytest.approx(0.5)
    # khung 100x100 căn giữa phần trong lề của A4 (200x287): góc (55, 98.5); nội dung 100x50 căn giữa theo Y
    assert pl.map(0, 0) == (pytest.approx(55), pytest.approx(123.5))
    assert pl.map(200, 100) == (pytest.approx(155), pytest.approx(173.5))


def test_stretch_fills_box():
    pl = lo.plan(Box(0, 0, 200, 100), L(width_mm=100, height_mm=100, fit="stretch"), M)
    assert (pl.sx, pl.sy) == (pytest.approx(0.5), pytest.approx(1.0))


def test_source_origin_is_subtracted():
    pl = lo.plan(Box(50, 70, 10, 10), L(width_mm=10, height_mm=10), M)
    assert pl.map(50, 70) == (pytest.approx(100), pytest.approx(143.5))


def test_not_centered_uses_offset_from_inner_corner():
    pl = lo.plan(Box(0, 0, 10, 10), L(width_mm=10, height_mm=10, center=False, offset_x_mm=20, offset_y_mm=30), M)
    assert pl.map(0, 0) == (pytest.approx(25), pytest.approx(35))       # 5 (lề) + offset


def test_paper_can_be_moved_on_the_bed():
    pl = lo.plan(Box(0, 0, 10, 10), L(paper="a5", paper_x_mm=50, paper_y_mm=10, margin_mm=0), M)
    assert pl.paper == Box(50, 10, 148, 210)
    assert (pl.box.x, pl.box.y) == (50, 10)


def test_custom_paper_needs_its_size():
    assert code(lo.plan, Box(0, 0, 10, 10), L(paper="custom"), M) == "bad_param"
    pl = lo.plan(Box(0, 0, 10, 10), L(paper="custom", paper_width_mm=100, paper_height_mm=80, margin_mm=0), M)
    assert pl.paper == Box(0, 0, 100, 80)


def test_paper_outside_work_area_is_rejected():
    assert code(lo.plan, Box(0, 0, 10, 10), L(paper="a4", paper_x_mm=100), M) == "paper_out_of_area"
    assert code(lo.plan, Box(0, 0, 10, 10), L(paper="custom", paper_width_mm=300, paper_height_mm=100), M) \
        == "paper_out_of_area"


def test_box_must_stay_inside_the_paper_margin():
    assert code(lo.plan, Box(0, 0, 10, 10), L(width_mm=205, height_mm=100), M) == "box_out_of_paper"
    assert code(lo.plan, Box(0, 0, 10, 10),
                L(width_mm=10, height_mm=10, center=False, offset_x_mm=195), M) == "box_out_of_paper"


def test_margin_larger_than_paper_is_bad_param():
    assert code(lo.plan, Box(0, 0, 10, 10), L(paper="a6", margin_mm=60), M) == "bad_param"


def test_flip_mirrors_inside_the_box():
    pl = lo.plan(Box(0, 0, 10, 10), L(width_mm=10, height_mm=10, flip_x=True), M)
    assert pl.map(0, 0)[0] == pytest.approx(pl.box.x + 10)
    assert pl.map(10, 0)[0] == pytest.approx(pl.box.x)


def test_line_has_zero_height_but_still_scales():
    pl = lo.plan(Box(0, 0, 50, 0), L(width_mm=100, height_mm=100), M)
    assert pl.sx == pl.sy == pytest.approx(2.0)


def test_single_point_is_empty_drawing():
    assert code(lo.plan, Box(5, 5, 0, 0), L(), M) == "empty_drawing"


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
