"""Tờ mẫu hiệu chỉnh bút: tạo được bản thảo, tỷ lệ 1:1, nằm trong tờ A5, G-code hợp lệ."""
from fastapi.testclient import TestClient

from app import paths
from app.main import app
from app.services.drawing import calibration

client = TestClient(app)
MACHINE = {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 8000}
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


def test_a6_calibration_fits_the_a6_margin_and_keeps_one_to_one():
    r = client.post("/api/draw/calibration", json={"machine": MACHINE, "gcode": GCODE, "pen_width_mm": 0.4, "paper": "a6"})
    assert r.status_code == 201, r.text
    draft = r.json()["draft"]
    assert draft["name"] == "Mẫu hiệu chỉnh bút A6" and draft["paper"]["w"] == 105 and draft["paper"]["h"] == 148
    assert draft["params"]["source"]["paper"] == "a6"
    [f] = draft["files"]
    b = f["stats"]["bounds"]
    assert abs((b["x1"] - b["x0"]) - 95) < 0.01                               # 105 - 2 × lề 5: không co giãn
    assert b["y1"] - b["y0"] <= 138 + 0.01 and calibration.height_mm("a6") <= 138
    box = draft["box"]
    assert b["x0"] >= box["x"] - 0.01 and b["x1"] <= box["x"] + box["w"] + 0.01
    assert abs(b["y0"] - box["y"]) < 0.5 or b["y0"] >= box["y"] - 0.01


def test_a6_bands_keep_the_same_pitch_rule_and_ruler_is_80mm():
    [layer] = calibration.layers(0.4, "a6")
    bands = layer.strokes[-len(calibration.BAND_FACTORS):]
    for stroke, factor in zip(bands, calibration.BAND_FACTORS):
        ys = sorted({round(y, 4) for _, y in stroke})
        assert abs((ys[1] - ys[0]) - 0.4 * factor) < 1e-3                       # cùng quy tắc: khoảng cách = bút × hệ số
        assert max(x for x, _ in stroke) == 95.0
    ruler = [s for s in layer.strokes if len(s) == 2 and s[0][1] == s[1][1] == 14.0][0]
    assert ruler[1][0] - ruler[0][0] == 80.0


def test_calibration_rejects_unknown_paper():
    r = client.post("/api/draw/calibration", json={"machine": MACHINE, "gcode": GCODE, "pen_width_mm": 0.4, "paper": "a3"})
    assert r.status_code == 400


# --- tờ hiệu chỉnh tông ------------------------------------------------------------------------------------------
def test_tone_cells_follow_the_style_layer_split():
    import numpy as np
    from app.services.drawing import styles
    assert calibration.tone_layer_covers(0.0, "zigzag") == []
    assert calibration.tone_layer_covers(0.3, "zigzag") == [(0.3, 45.0)]
    for style, n_max in (("crosshatch", 2), ("crosshatch3", 3)):
        parts = calibration.tone_layer_covers(0.9, style)
        assert len(parts) == n_max
        total = 1 - np.prod([1 - p for p, _ in parts])
        assert abs(total - 0.9) < 1e-4                                        # đúng độ phủ danh định của ô
    assert {a for _, a in calibration.tone_layer_covers(0.9, "crosshatch3")} == {45.0, 105.0, 165.0}


def test_tone_sheet_spacing_is_pen_over_cover_and_patches_stay_in_their_square():
    [layer], info = calibration.tone_layers(0.5, "a6", "zigzag")
    cells = info["cells"]
    assert [c["cover"] for c in cells] == list(calibration.TONE_STEPS) and cells[0]["layers"] == []
    assert cells[5]["layers"][0]["spacing_mm"] == round(0.5 / 0.25, 4)
    assert info["width"] <= 95 and info["height"] <= 138                     # vừa A6 trừ lề 5 mm
    xs = [x for s in layer.strokes for x, _ in s]
    ys = [y for s in layer.strokes for _, y in s]
    assert min(xs) >= -1e-6 and max(xs) <= info["width"] + 1e-6 and max(ys) <= info["height"] + 1e-6


def test_wave_am_and_spiral_tone_sheets_stay_in_their_squares_and_get_darker():
    for style in ("wave_am", "spiral"):
        [layer], info = calibration.tone_layers(0.5, "a6", style)
        assert [c["cover"] for c in info["cells"]] == list(calibration.TONE_STEPS)
        xs = [x for s in layer.strokes for x, _ in s]
        ys = [y for s in layer.strokes for _, y in s]
        assert min(xs) >= -1e-6 and max(xs) <= info["width"] + 1e-6 and max(ys) <= info["height"] + 1e-6   # không tràn ô
        patch = info["patch_mm"]

        def length(cell: dict) -> float:
            """Tổng chiều dài nét nằm trong ô (mm): ô đậm hơn thì phải vẽ nhiều hơn."""
            x0, y0 = cell["x"], cell["y"]
            total = 0.0
            for s in layer.strokes:
                for (ax, ay), (bx, by) in zip(s, s[1:]):
                    if x0 - 1e-6 <= ax <= x0 + patch + 1e-6 and y0 - 1e-6 <= ay <= y0 + patch + 1e-6:
                        total += ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            return total
        lengths = [length(c) for c in info["cells"]]
        assert lengths[0] == 0.0                                      # ô 0 % = giấy trắng
        assert lengths[-1] > lengths[8] > lengths[4]                  # đậm dần theo độ phủ
        assert info["cells"][8]["layers"][0]["spacing_mm"] > 0


def test_tone_sheet_draft_via_api_is_one_to_one():
    for paper, style in (("a6", "crosshatch3"), ("a5", "zigzag"), ("a6", "wave_am"), ("a6", "spiral")):
        r = client.post("/api/draw/calibration", json={"machine": MACHINE, "gcode": GCODE, "pen_width_mm": 0.5,
                                                       "paper": paper, "sheet": "tone", "style": style})
        assert r.status_code == 201, r.text
        draft = r.json()["draft"]
        src = draft["params"]["source"]
        assert src["sheet"] == "tone" and src["style"] == style and len(src["cells"]) == 16
        b = draft["files"][0]["stats"]["bounds"]
        assert abs((b["x1"] - b["x0"]) - src["width"]) < 0.01                 # không co giãn
    bad = client.post("/api/draw/calibration", json={"machine": MACHINE, "gcode": GCODE, "sheet": "tone", "style": "hexagon"})
    assert bad.status_code == 400
    assert client.post("/api/draw/calibration", json={"machine": MACHINE, "gcode": GCODE, "sheet": "x"}).status_code == 400
