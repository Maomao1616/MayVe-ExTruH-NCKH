"""Nhập một tệp G-code có sẵn thành một bản thảo."""
import pytest
from fastapi.testclient import TestClient

from app import paths
from app.main import app
from app.services.drawing import gcode_import

client = TestClient(app)

TWO_STROKES = """; do phan mem khac
G90 G21
G1 Z5 F3000
G0 X10 Y10
G1 Z0
G1 X20 Y10 F1500 (ve)
G1 X20 Y20
G1 Z5
G0 X30 Y30
G1 Z0
G1 X40 Y30
G1 Z5
"""


def upload(text, name="hinh.gcode", **form):
    return client.post("/api/draw/drafts/import-gcode", files={"file": (name, text.encode("utf-8"))},
                       data={"work_w": "285", "work_h": "318", **form})


def test_analyse_counts_strokes_and_lengths():
    strokes, stats, warnings = gcode_import.analyse(
        ["G90 G21", "G1 Z5 F3000", "G0 X10 Y10", "G1 Z0", "G1 X20 Y10 F1500", "G1 X20 Y20", "G1 Z5",
         "G0 X30 Y30", "G1 Z0", "G1 X40 Y30", "G1 Z5"])
    assert strokes == [[(10, 10), (20, 10), (20, 20)], [(30, 30), (40, 30)]]
    assert stats["strokes"] == 2 and stats["pen_lifts"] == 2 and stats["draw_mm"] == 30.0
    assert stats["bounds"] == {"x0": 10, "y0": 10, "x1": 40, "y1": 30}
    assert warnings == []


def test_file_without_z_draws_every_g1_and_breaks_at_g0():
    strokes, stats, _ = gcode_import.analyse(["G90", "G0 X0 Y0", "G1 X10 F600", "G1 Y10", "G0 X50 Y50", "G1 X60"])
    assert [len(s) for s in strokes] == [3, 2] and stats["pen_lifts"] == 2


def test_arcs_are_approximated_with_a_warning():
    _, _, warnings = gcode_import.analyse(["G90", "G0 X10 Y0", "G2 X-10 Y0 I-10 J0 F600"])
    assert warnings == [{"code": "arcs_approximated", "count": 1}]


def test_import_creates_one_draft_per_file():
    r = upload(TWO_STROKES)
    assert r.status_code == 201, r.text
    draft = r.json()["draft"]
    assert draft["name"] == "hinh" and draft["params"]["source"]["mode"] == "gcode_import"
    [f] = draft["files"]
    assert f["stats"]["strokes"] == 2 and f["name"] == "draw"
    folder = paths.drafts_dir() / draft["id"]
    assert (folder / "draw.gcode").read_text(encoding="utf-8").splitlines()[0] == "G90 G21"   # chú thích đã bỏ
    assert "; do phan mem" not in (folder / "draw.gcode").read_text(encoding="utf-8")
    assert (folder / "preview.svg").is_file()
    assert client.get(f"/api/draw/drafts/{draft['id']}/gcode/draw").text.count("\n") == f["stats"]["lines"]
    second = upload(TWO_STROKES, name="khac.gcode").json()["draft"]
    assert second["id"] != draft["id"] and len(client.get("/api/draw/drafts").json()["drafts"]) == 2


@pytest.mark.parametrize("text,code", [
    ("G90\n$H\nG1 X5 F100\n", "bad_gcode"),
    ("G90\nG1 X5 ?\n", "bad_gcode"),
    ("; chi chu thich\n", "empty_job"),
    ("G90\nG21\nG4 P1\n", "empty_drawing"),
    ("G90\nG1 Z5 F100\nG0 X5 Y5\nG1 Z0\nG1 Z5\n", "empty_drawing"),
])
def test_import_rejects_bad_files(text, code):
    r = upload(text)
    assert r.status_code == 400 and r.json()["error"]["code"] == code
    assert client.get("/api/draw/drafts").json()["drafts"] == []


def test_import_rejects_bad_machine_size():
    assert upload(TWO_STROKES, work_w="0").status_code == 400
