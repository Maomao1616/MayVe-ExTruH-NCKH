import pytest

from app.services.drawing import optimize, spec
from app.services.drawing.errors import DrawError


def P(**kw):
    return spec.parse("optimize", kw)


def test_default_pipeline_runs_all_four_steps_in_order():
    assert optimize.build_pipeline(P()) == (
        "linemerge --tolerance 0.1mm linesimplify --tolerance 0.05mm filter --min-length 0.5mm linesort")


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
