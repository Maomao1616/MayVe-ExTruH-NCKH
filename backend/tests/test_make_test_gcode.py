"""tools/make_test_gcode.py: các tệp bài thử tốc độ phải qua bộ làm sạch G-code của backend và nằm trong vùng máy."""
import importlib.util
import re
from pathlib import Path

from app.services.job import clean_gcode

ROOT = Path(__file__).resolve().parents[2]


def load_tool():
    spec = importlib.util.spec_from_file_location("make_test_gcode", ROOT / "tools" / "make_test_gcode.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_test_file_passes_the_backend_cleaner_and_stays_in_the_work_area():
    tool = load_tool()
    files = tool.build_all(5.0, 0.0, 3000.0, 3000.0)
    assert len(files) >= 7
    for name, text in files.items():
        cleaned = clean_gcode(text.splitlines())
        assert cleaned, name
        xs = [float(v) for v in re.findall(r"X(-?[\d.]+)", text)]
        ys = [float(v) for v in re.findall(r"Y(-?[\d.]+)", text)]
        assert min(xs) >= 0 and max(xs) <= tool.WORK_W, name
        assert min(ys) >= 0 and max(ys) <= tool.WORK_H, name
        assert not re.search(r"\$|G10|G92|G28|G53|G5[5-9]", text), name       # không đổi gốc, không Home


def test_lift_cost_has_100_strokes_and_the_requested_delay():
    tool = load_tool()
    text = tool.lift_cost(5.0, 0.0, 3000.0, 3000.0, delay=0.05)
    assert text.count("G1 Z0") == 100 and text.count("G4 P0.05") >= 200
    low = tool.lift_cost(5.0, 0.0, 3000.0, 3000.0, delay=0.1, up_z=2.0)
    assert "G1 Z2 " in low and "G1 Z5 " not in low.split("\n", 3)[3]


def test_lost_steps_draws_the_same_cross_twice():
    tool = load_tool()
    text = tool.lost_steps(5.0, 0.0, 3000.0, 3000.0)
    assert text.count("G0 X8 Y15") == 2 and text.count("G0 X15 Y8") == 2
