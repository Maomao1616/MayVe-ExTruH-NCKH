import pytest

from app.services.drawing import make_gcode
from app.services.drawing.errors import DrawError
from app.services.drawing.shapes import Layer

MACHINE = {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000}
GCODE = {"pen_up_z": 5, "pen_down_z": 0}
SQ = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]


def run(layers=None, layout=None, gcode=None, machine=None, **kw):
    layers = layers if layers is not None else [Layer("1", [SQ])]
    return make_gcode(layers, machine or MACHINE, layout, {**GCODE, **(gcode or {})}, **kw)


def code(**kw):
    with pytest.raises(DrawError) as e:
        run(**kw)
    return e.value.code


def test_single_layer_end_to_end():
    r = run(layout={"width_mm": 100, "height_mm": 100})
    f = r["files"][0]
    assert f["name"] == "draw" and f["gcode"].startswith("G90 G21\n") and f["gcode"].endswith("\n")
    assert f["stats"]["draw_mm"] == 400.0
    assert r["box"]["w"] == 100 and r["box"]["scale_x"] == pytest.approx(10)
    assert r["paper"] == {"x": 0, "y": 0, "w": 210.0, "h": 297.0}      # tờ giấy A4 ở gốc O(0,0)
    assert r["box"]["x"] == pytest.approx(55) and r["box"]["y"] == pytest.approx(98.5)


def test_two_layers_give_two_files_in_one_frame():
    a = Layer("dark", [[(0, 0), (20, 0)]])
    b = Layer("light", [[(0, 20), (20, 20)]])
    r = run(layers=[a, b], layout={"width_mm": 40, "height_mm": 40})
    assert [f["layer"] for f in r["files"]] == ["dark", "light"]
    ya = r["files"][0]["stats"]["bounds"]["y0"]
    yb = r["files"][1]["stats"]["bounds"]["y0"]
    assert yb - ya == pytest.approx(40)          # hai lớp cùng khung: cách nhau đúng 20 * 2


def test_empty_layer_is_skipped_but_not_all_empty():
    r = run(layers=[Layer("x", []), Layer("1", [SQ])])
    assert len(r["files"]) == 1
    assert code(layers=[Layer("x", [])]) == "empty_drawing"
    assert code(layers=[]) == "empty_drawing"


def test_bad_layer_ids_and_values():
    assert code(layers=[Layer("1", [SQ]), Layer("1", [SQ])]) == "bad_param"
    assert code(layers=[Layer("", [SQ])]) == "bad_param"
    assert code(layers=[Layer("1", [[(0, 0), (float("nan"), 1)]])]) == "bad_param"


def test_pen_z_rules():
    assert code(gcode={"pen_up_z": 3, "pen_down_z": 3}) == "bad_param"
    assert code(gcode={"pen_up_z": 6}) == "bad_param"          # vượt hành trình Z 5
    assert code(gcode={"pen_up_z": None}) == "bad_param"


def test_box_or_paper_outside_is_an_error_not_a_clip():
    assert code(layout={"width_mm": 285, "height_mm": 100}) == "box_out_of_paper"
    assert code(layout={"paper_x_mm": 100}) == "paper_out_of_area"


def test_source_bounds_keep_image_margins():
    r = run(layers=[Layer("1", [[(40, 40), (60, 60)]])], source_bounds=(0, 0, 100, 100),
            layout={"width_mm": 100, "height_mm": 100})
    b = r["files"][0]["stats"]["bounds"]
    assert b["x0"] == pytest.approx(55 + 40) and b["x1"] == pytest.approx(55 + 60)


def test_bad_source_bounds():
    assert code(source_bounds=(10, 10, 0, 0)) == "bad_param"


def test_too_many_points(monkeypatch):
    from app.services.drawing import service
    monkeypatch.setattr(service, "MAX_POINTS", 3)
    assert code(layers=[Layer("1", [SQ])]) == "too_many_points"


def test_typo_in_params_is_reported():
    assert code(gcode={"drawfeed": 1}) == "bad_param"
