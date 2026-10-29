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
