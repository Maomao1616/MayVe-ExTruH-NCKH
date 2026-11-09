"""Tờ thử máy thành bản thảo (services/drawing/testsheets.py, POST /api/draw/testsheet)."""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.drawing import drafts, testgcode
from app.services.job import clean_gcode

MACHINE = {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 8000}
GCODE = {"pen_up_z": 3, "pen_down_z": 0, "pen_feed": 3000, "draw_feed": 5000, "pen_down_feed": 2000}


@pytest.fixture
def client():
    return TestClient(app)


def post(client, kind, options=None, machine=None, gcode=None):
    return client.post("/api/draw/testsheet", json={"kind": kind, "machine": machine or MACHINE,
                                                    "gcode": gcode or GCODE, "options": options or {}})


def test_lift_sheet_rows_are_the_product_and_in_order(client):
    r = post(client, "lift", {"ups": [5, 1, 3], "delays": [0.1, 0.05], "down_feeds": [2000, 1000]})
    assert r.status_code == 201
    rows = r.json()["rows"]
    assert len(rows) == 12 and [x["n"] for x in rows] == list(range(1, 13))
    assert (rows[0]["up"], rows[0]["delay"], rows[0]["down_feed"]) == (1, 0.05, 1000)      # đã sắp xếp tăng dần
    assert (rows[-1]["up"], rows[-1]["delay"], rows[-1]["down_feed"]) == (5, 0.1, 2000)
    assert all(x["est_s"] > 0 for x in rows)
    assert rows[0]["est_s"] < rows[-1]["est_s"]                                            # nhấc cao + chờ lâu = chậm hơn
    draft = r.json()["draft"]
    assert draft["params"]["source"]["mode"] == "testsheet" and draft["params"]["source"]["rows"] == rows
    assert drafts.get(draft["id"])["name"] == "Tờ thử nhấc bút (12 hàng)"


def test_lift_sheet_gcode_uses_each_rows_own_parameters(client):
    r = post(client, "lift", {"ups": [1, 5], "delays": [0.05], "down_feeds": [1000, 2000]})
    gcode = drafts.read_gcode(r.json()["draft"]["id"], "draw")
    assert "G1 Z1 F3000" in gcode and "G1 Z5 F3000" in gcode           # nhấc 1 và nhấc 5
    assert "G1 Z0 F1000" in gcode and "G1 Z0 F2000" in gcode           # hạ chậm / nhanh theo hàng
    assert gcode.count("G4 P0.05") >= 4 * 20 * 2
    assert clean_gcode(gcode.splitlines())                             # qua bộ làm sạch của tác vụ


def test_lift_sheet_preview_separates_pen_up_from_pen_down_even_with_low_lifts(client):
    """Z nhấc 1 trộn Z nhấc 5 trong một tệp: bút xuống = sát Z thấp nhất, không phải dưới trung điểm 2,5."""
    r = post(client, "lift", {"ups": [1, 5], "delays": [0.05], "down_feeds": [2000]})
    stats = r.json()["draft"]["files"][0]["stats"]
    # 2 hàng × 20 gạch + chấm đánh số (1 + 2 chấm) = 43 nét vẽ; nếu nhấc Z1 bị coi là bút xuống sẽ ra ít nét hơn rất nhiều
    assert stats["strokes"] == 2 * 20 + 3


def test_every_kind_is_inside_the_work_area_and_clean(client):
    for kind in ("lift", "lost", "accel", "speed", "drag"):
        r = post(client, kind)
        assert r.status_code == 201, (kind, r.text)
        text = drafts.read_gcode(r.json()["draft"]["id"], "draw")
        xs = [float(v) for v in re.findall(r"X(-?[\d.]+)", text)]
        ys = [float(v) for v in re.findall(r"Y(-?[\d.]+)", text)]
        assert min(xs) >= 0 and max(xs) <= 285 and min(ys) >= 0 and max(ys) <= 318, kind
        assert not re.search(r"\$|G10|G92|G28|G53|G5[5-9]", text), kind


def test_speed_strips_follow_the_requested_speeds_and_machine_cap(client):
    r = post(client, "speed", {"speeds": [4000, 8000]})
    text = drafts.read_gcode(r.json()["draft"]["id"], "draw")
    assert "F4000" in text and "F8000" in text
    too_fast = post(client, "speed", {"speeds": [9000]})                # vượt rapid_feed 8000 của máy
    assert too_fast.status_code == 400 and too_fast.json()["error"]["code"] == "bad_param"


@pytest.mark.parametrize("options", [
    {"ups": [1, 2, 3, 4, 5], "delays": [0.05, 0.1, 0.2], "down_feeds": [1000, 2000]},     # 30 hàng > 24
    {"ups": []}, {"ups": [0.1]}, {"ups": [9]}, {"delays": [-1]}, {"down_feeds": [50]},
    {"ups": ["a"]}, {"ups": [True]}, {"ups": "3"}, {"ups": [None]},
])
def test_lift_sheet_rejects_bad_options(client, options):
    r = post(client, "lift", options)
    assert r.status_code in (400, 422), (options, r.text)


def test_unknown_kind_and_too_small_machine_are_rejected(client):
    assert post(client, "nope").status_code == 400
    small = post(client, "lost", machine={**MACHINE, "work_w": 100, "work_h": 100})
    assert small.status_code == 400 and small.json()["error"]["code"] == "out_of_area"


def test_guest_cannot_create_test_sheets(monkeypatch):
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", "abcd1234")
    r = TestClient(app).post("/api/draw/testsheet", json={"kind": "lift", "machine": MACHINE, "gcode": GCODE})
    assert r.status_code == 401


def test_tool_wrapper_and_backend_share_the_same_generators():
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("make_test_gcode", root / "tools" / "make_test_gcode.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    assert tool.build_all(3.0, 0.0, 3000.0, 5000.0, 2000.0) == testgcode.build_all(3.0, 0.0, 3000.0, 5000.0, 2000.0)
