import pytest

from app.services.drawing import gcode as gc, spec
from app.services.drawing.errors import DrawError
from app.services.job import MAX_LINE_LEN, clean_gcode

M = spec.parse("machine", {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000})


def G(**kw):
    kw.setdefault("pen_up_z", 5)
    kw.setdefault("pen_down_z", 0)
    return spec.parse("gcode", kw)


SQUARE = [[(10, 10), (60, 10), (60, 60), (10, 60), (10, 10)]]


def build(strokes=SQUARE, machine=M, **kw):
    return gc.build_gcode(strokes, G(**kw), machine)


def test_fmt_trims_zeros_and_negative_zero():
    assert gc.fmt(5.0, 3) == "5" and gc.fmt(100.0, 3) == "100" and gc.fmt(1.2500, 3) == "1.25"
    assert gc.fmt(-0.0001, 3) == "0" and gc.fmt(-1.5, 3) == "-1.5"


def test_header_pen_up_first_and_ends_pen_up():
    lines, _, _ = build()
    assert lines[0] == "G90 G21"
    assert lines[1].startswith("G1 Z5")
    last_z = [l for l in lines if " Z" in l][-1]
    assert last_z.startswith("G1 Z5")            # kết thúc bằng bút lên


def test_pen_goes_down_only_after_travel_and_up_before_next_travel():
    lines, _, _ = build([[(0, 0), (5, 0)], [(20, 20), (30, 20)]])
    seq = [l.split()[0] + (" Z" if " Z" in l else "") for l in lines if not l.startswith("G4")]
    # G90, [pen up], G0, down, G1, up, G0, down, G1, up
    zs = [l for l in lines if " Z" in l]
    assert [z.split()[1] for z in zs] == ["Z5", "Z0", "Z5", "Z0", "Z5"]
    assert sum(1 for l in lines if l.startswith("G0")) == 2


def test_feed_present_on_first_g1_and_only_when_changed():
    lines, _, _ = build(draw_feed=1500, pen_feed=3000)
    g1 = [l for l in lines if l.startswith("G1")]
    assert " F" in g1[0]
    assert any("F1500" in l for l in g1)
    assert any("F3000" in l for l in g1)
    # cùng giá trị liên tiếp không lặp F
    draws = [l for l in g1 if " Z" not in l]
    assert sum("F1500" in l for l in draws) == 1


def test_travel_uses_g0_at_machine_rapid_else_g1_with_feed():
    lines, _, _ = build(travel_feed=6000)
    assert any(l.startswith("G0 ") for l in lines)
    lines, _, _ = build(travel_feed=2000)
    assert not any(l.startswith("G0") for l in lines)
    assert any("F2000" in l for l in lines)


def test_zero_delay_removes_g4():
    lines, _, _ = build(delay_up_s=0, delay_down_s=0)
    assert not any(l.startswith("G4") for l in lines)
    lines, _, _ = build(delay_up_s=0.5, delay_down_s=0.25)
    assert "G4 P0.5" in lines and "G4 P0.25" in lines


def test_duplicate_points_and_tiny_strokes_are_dropped_with_warning():
    lines, stats, warns = build([[(0, 0), (0, 0), (5, 0)], [(9, 9), (9.0001, 9)], [(1, 1)]], precision=3)
    assert stats["strokes"] == 1
    assert warns == [{"code": "dropped_strokes", "count": 2}]
    assert not any("X0 Y0" in l and l.startswith("G1 X") for l in lines[3:])   # không có G1 dài 0


def test_everything_dropped_is_empty_drawing():
    with pytest.raises(DrawError) as e:
        build([[(1, 1), (1, 1)]])
    assert e.value.code == "empty_drawing"


def test_precision_controls_decimals():
    lines, _, _ = build([[(0, 0), (1.23456, 0)]], precision=2)
    assert "X1.23" in " ".join(lines) and "1.234" not in " ".join(lines)


def test_invert_y_flips_only_in_to_machine():
    m = spec.parse("machine", {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000, "invert_y": True})
    lines, stats, _ = build([[(10, 10), (20, 10)]], machine=m)
    assert "Y308" in " ".join(lines)                 # 318 - 10
    assert stats["bounds"]["y0"] == 10               # thống kê vẫn theo tọa độ bản vẽ


def test_stats_for_a_square():
    _, stats, _ = build(SQUARE, draw_feed=3000, travel_feed=6000)
    assert stats["draw_mm"] == 200.0 and stats["strokes"] == 1 and stats["pen_lifts"] == 1
    assert stats["bounds"] == {"x0": 10, "y0": 10, "x1": 60, "y1": 60}
    assert stats["travel_mm"] == pytest.approx(14.14, abs=0.01)
    assert stats["est_seconds"] > 4


def test_feed_above_machine_rapid_warns():
    _, _, warns = build(draw_feed=9000)
    assert {"code": "feed_above_rapid", "count": 1} in warns


def test_output_passes_the_job_runner_cleaner_unchanged():
    lines, _, _ = build([[(i, (i * 7) % 50) for i in range(200)]])
    assert clean_gcode(lines) == lines
    assert max(len(l) for l in lines) <= MAX_LINE_LEN
    assert not any("$" in l or ";" in l for l in lines)


def test_too_many_lines_is_rejected(monkeypatch):
    monkeypatch.setattr(gc, "MAX_LINES", 10)
    with pytest.raises(DrawError) as e:
        build([[(i, 0) for i in range(30)]])
    assert e.value.code == "too_many_lines"
