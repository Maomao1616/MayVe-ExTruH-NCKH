"""Lớp HTTP của tab vẽ. Cần fastapi/httpx (chạy ở máy bạn)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

MACHINE = {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000}
BODY = {
    "layers": [{"id": "1", "strokes": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}],
    "machine": MACHINE,
    "layout": {"width_mm": 100, "height_mm": 100},
    "gcode": {"pen_up_z": 5, "pen_down_z": 0},
}


@pytest.fixture
def client():
    return TestClient(app)


def test_schema(client):
    body = client.get("/api/draw/schema").json()
    assert body["papers"]["a4"]["w"] == 210.0 and "a6" in body["papers"]
    assert {r["name"] for r in body["params"]["machine"]} >= {"work_w", "work_h", "z_travel", "rapid_feed"}


def test_gcode_ok(client):
    r = client.post("/api/draw/gcode", json=BODY)
    assert r.status_code == 200
    f = r.json()["files"][0]
    assert f["gcode"].startswith("G90 G21\n") and f["stats"]["strokes"] == 1


def test_draw_error_uses_the_project_error_shape(client):
    r = client.post("/api/draw/gcode", json={**BODY, "layout": {"width_mm": 285, "height_mm": 100}})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "box_out_of_paper"


def test_unknown_param_is_bad_param(client):
    r = client.post("/api/draw/gcode", json={**BODY, "gcode": {"pen_up_z": 5, "pen_down_z": 0, "oops": 1}})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"


def test_body_shape_error_is_422(client):
    assert client.post("/api/draw/gcode", json={"layers": []}).status_code == 422


def test_does_not_touch_the_machine(client):
    from app.services.machine import machine
    machine.disconnect()
    assert client.post("/api/draw/gcode", json=BODY).status_code == 200      # chạy được khi chưa kết nối


SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100">
<rect x="10" y="10" width="80" height="80" fill="none" stroke="black"/></svg>"""


def test_gcode_needs_exactly_one_of_task_or_layers(client):
    r = client.post("/api/draw/gcode", json={**BODY, "task": "abc"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"
    body = {k: v for k, v in BODY.items() if k != "layers"}
    r = client.post("/api/draw/gcode", json=body)
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"


def test_unknown_task_is_404(client):
    body = {k: v for k, v in BODY.items() if k != "layers"}
    r = client.post("/api/draw/gcode", json={**body, "task": "khong-co"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_task"


def test_svg_upload_then_gcode_by_task(client):
    pytest.importorskip("vpype")
    up = client.post("/api/draw/svg", files={"file": ("a.svg", SVG, "image/svg+xml")},
                     data={"options": '{"svg": {"frame": "page"}}'})
    assert up.status_code == 200, up.text
    task = up.json()["task"]
    body = {k: v for k, v in BODY.items() if k != "layers"}
    r = client.post("/api/draw/gcode", json={**body, "task": task})
    assert r.status_code == 200, r.text
    assert r.json()["files"][0]["gcode"].startswith("G90 G21\n")
    assert client.delete(f"/api/draw/tasks/{task}").json() == {"ok": True}


def test_svg_bad_inputs(client):
    r = client.post("/api/draw/svg", files={"file": ("a.svg", b"khong phai svg", "image/svg+xml")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_svg"
    r = client.post("/api/draw/svg", files={"file": ("a.svg", SVG, "image/svg+xml")}, data={"options": "{oops"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"
    r = client.post("/api/draw/svg", files={"file": ("a.svg", SVG, "image/svg+xml")},
                    data={"options": '{"layout": {}}'})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"
