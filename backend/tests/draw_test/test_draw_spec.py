import pytest

from app.services.drawing import spec
from app.services.drawing.errors import DrawError

MACHINE = {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000}


def code(fn, *a):
    with pytest.raises(DrawError) as e:
        fn(*a)
    return e.value.code


def test_defaults_are_filled():
    p = spec.parse("layout", {})
    assert (p.paper, p.width_mm, p.height_mm, p.margin_mm, p.fit, p.center) == ("a4", None, None, 5.0, "contain", True)
    assert (p.paper_x_mm, p.paper_y_mm) == (0.0, 0.0)
    assert p.flip_x is False and p.reverse is False


def test_machine_fields_are_required_no_hidden_defaults():
    assert code(spec.parse, "machine", {"work_w": 285}) == "bad_param"
    assert spec.parse("machine", MACHINE).invert_y is False


def test_unknown_key_is_rejected_to_catch_typos():
    assert code(spec.parse, "layout", {"widht_mm": 50}) == "bad_param"


def test_type_and_range_checks():
    assert code(spec.parse, "layout", {"width_mm": "100"}) == "bad_param"
    assert code(spec.parse, "layout", {"paper": "a3"}) == "bad_param"
    assert code(spec.parse, "layout", {"width_mm": True}) == "bad_param"
    assert code(spec.parse, "layout", {"width_mm": float("nan")}) == "bad_param"
    assert code(spec.parse, "layout", {"width_mm": 0}) == "bad_param"
    assert code(spec.parse, "layout", {"fit": "zoom"}) == "bad_param"
    assert code(spec.parse, "layout", {"center": 1}) == "bad_param"
    assert code(spec.parse, "gcode", {"pen_up_z": 5, "pen_down_z": 0, "precision": 2.5}) == "bad_param"


def test_none_means_use_default():
    assert spec.parse("layout", {"margin_mm": None}).margin_mm == 5.0


def test_params_are_immutable():
    p = spec.parse("layout", {})
    with pytest.raises(AttributeError):
        p.width_mm = 5


def test_describe_lists_every_param_once():
    d = spec.describe()
    names = {g: [r["name"] for r in rows] for g, rows in d["params"].items()}
    assert "pen_up_z" in names["gcode"] and "work_w" in names["machine"]
    assert all(len(v) == len(set(v)) for v in names.values())
    assert d["papers"]["a4"] == {"w": 210.0, "h": 297.0} and d["papers"]["a6"] == {"w": 105.0, "h": 148.0}
    assert d["limits"]["max_lines"] == 200_000
