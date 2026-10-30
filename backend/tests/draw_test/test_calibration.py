"""Tờ mẫu hiệu chỉnh bút: tạo được bản thảo, tỷ lệ 1:1, nằm trong tờ A5, G-code hợp lệ."""
from fastapi.testclient import TestClient

from app import paths
from app.main import app
from app.services.drawing import calibration

client = TestClient(app)
MACHINE = {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000}
GCODE = {"pen_up_z": 5, "pen_down_z": 0}


def test_bands_have_the_pitch_of_pen_times_factor():
    [layer] = calibration.layers(0.4)
    bands = layer.strokes[-len(calibration.BAND_FACTORS):]
    for stroke, factor in zip(bands, calibration.BAND_FACTORS):
        ys = sorted({round(y, 4) for _, y in stroke})
        assert abs((ys[1] - ys[0]) - 0.4 * factor) < 1e-3
        assert min(x for x, _ in stroke) == 0 and max(x for x, _ in stroke) == calibration.WIDTH_MM


def test_calibration_draft_is_one_to_one_and_inside_a5():
    r = client.post("/api/draw/calibration", json={"machine": MACHINE, "gcode": GCODE, "pen_width_mm": 0.4})
    assert r.status_code == 201, r.text
    draft = r.json()["draft"]
    assert draft["name"] == "Mẫu hiệu chỉnh bút" and draft["params"]["source"]["mode"] == "calibration"
    assert draft["paper"]["w"] == 148 and draft["paper"]["h"] == 210
    [f] = draft["files"]
    b = f["stats"]["bounds"]
    assert abs((b["x1"] - b["x0"]) - calibration.WIDTH_MM) < 0.01              # đúng 130 mm, không co giãn
    box = draft["box"]
    assert b["x0"] >= box["x"] - 0.01 and b["x1"] <= box["x"] + box["w"] + 0.01
    gcode = client.get(f"/api/draw/drafts/{draft['id']}/gcode/{f['name']}").text
    assert gcode.splitlines()[0] == "G90 G21" and len(gcode.splitlines()) == f["stats"]["lines"]
    assert (paths.drafts_dir() / draft["id"] / "preview.svg").is_file()


def test_calibration_rejects_bad_pen_width():
    for bad in (0.01, 5):
        r = client.post("/api/draw/calibration", json={"machine": MACHINE, "gcode": GCODE, "pen_width_mm": bad})
        assert r.status_code == 400
