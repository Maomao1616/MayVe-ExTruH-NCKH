import pytest

from app.services.drawing import optimize, spec
from app.services.drawing.errors import DrawError


def P(**kw):
    return spec.parse("optimize", kw)


def test_default_pipeline_runs_all_four_steps_in_order():
    assert optimize.build_pipeline(P()) == (
        "linemerge --tolerance 0.1mm linesimplify --tolerance 0.05mm filter --min-length 0.5mm "
        "linesort --two-opt --passes 50")


def test_two_opt_is_skipped_above_the_stroke_limit_or_when_off():
    big = optimize.TWO_OPT_MAX_STROKES + 1
    assert optimize.build_pipeline(P(), strokes=big).endswith("linesort")
    assert optimize.build_pipeline(P(two_opt=False)).endswith("linesort")
    assert "--passes 200" in optimize.build_pipeline(P(passes=200))


def test_zero_turns_a_step_off():
    assert optimize.build_pipeline(P(merge_tolerance_mm=0, simplify_tolerance_mm=0, min_length_mm=0, sort=False)) == ""
    assert optimize.build_pipeline(P(merge_tolerance_mm=0, min_length_mm=0, sort=False)) == \
        "linesimplify --tolerance 0.05mm"


def test_numbers_have_no_scientific_notation():
    assert "0.0001mm" in optimize.build_pipeline(P(merge_tolerance_mm=0.0001))
    assert "e-" not in optimize.build_pipeline(P(merge_tolerance_mm=0.0001))
    assert "2.5mm" in optimize.build_pipeline(P(min_length_mm=2.5))


def test_empty_pipeline_does_not_need_vpype():
    doc = object()
    assert optimize.run(doc, P(merge_tolerance_mm=0, simplify_tolerance_mm=0, min_length_mm=0, sort=False)) is doc


def test_bad_values_are_rejected():
    for bad in ({"merge_tolerance_mm": -1}, {"min_length_mm": 1000}, {"sort": "yes"}, {"typo": 1}):
        with pytest.raises(DrawError):
            P(**bad)


# --- nối nét gần (optimize.bridge) ------------------------------------------------------------------------------
def _dark(value, w=100, h=100):
    import numpy as np
    return np.full((h, w), value, dtype="float32")


def test_bridge_joins_close_strokes_inside_dark_area():
    strokes = [[(10, 10), (50, 10)], [(50, 11), (10, 11)], [(10, 12), (50, 12)]]
    out, n = optimize.bridge(strokes, _dark(0.6), 100, 100, max_mm=2.0)
    assert n == 2 and len(out) == 1
    assert out[0] == [(10, 10), (50, 10), (50, 11), (10, 11), (10, 12), (50, 12)]    # giữ đúng thứ tự, không mất điểm


def test_bridge_keeps_pen_lift_when_gap_is_long_or_crosses_white_paper():
    far = [[(10, 10), (50, 10)], [(50, 15), (10, 15)]]                                # cách 5 mm > 2 mm
    assert optimize.bridge(far, _dark(0.6), 100, 100, max_mm=2.0)[1] == 0
    dark = _dark(0.6)
    dark[10:12, 49:52] = 0.0                                                          # khe trắng nằm giữa đoạn nối
    near = [[(10, 10), (50, 10)], [(50, 11.5), (10, 11.5)]]
    assert optimize.bridge(near, dark, 100, 100, max_mm=2.0)[1] == 0


def test_bridge_is_on_by_default_and_cuts_pen_lifts_on_a_photo_like_image():
    import io
    import numpy as np
    from PIL import Image
    from app.services.drawing import raster
    assert P().bridge is True
    yy, xx = np.mgrid[0:300, 0:400]
    img = (255 * (0.5 + 0.5 * np.sin(xx / 25.0) * np.cos(yy / 30.0))).astype("uint8")   # mảng sáng tối uốn lượn
    buf = io.BytesIO(); Image.fromarray(img).save(buf, "PNG")

    def lifts(bridge):
        opts = {"raster": {"pen_width_mm": 0.5}, "style": {"kind": "crosshatch", "outline_overlay": False},
                "optimize": {"bridge": bridge}, "layout": {"paper": "a6", "margin_mm": 5}}
        layers, _, info, _ = raster.build_raster(buf.getvalue(), "t", opts)
        return sum(len(l.strokes) for l in layers), info["optimize"]["bridged"]
    (off, b0), (on, b1) = lifts(False), lifts(True)
    assert b0 == 0 and b1 > 0 and on == off - b1 and on < 0.7 * off
