"""Hợp đồng API của tab vẽ: nạp nền + tiến trình + hủy, nét nháp, bản thảo trên đĩa, xoay."""
import io
import time

import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.services.drawing import drafts, layout as lo, raster, spec
from app.services.drawing.shapes import Box, Layer

MACHINE = {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 6000}
GCODE = {"pen_up_z": 5, "pen_down_z": 0}
SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100">'
       b'<path d="M0 0 L100 0 L100 100 Z" stroke="black" fill="none"/></svg>')


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts, "SETTINGS_PATH", tmp_path / "draw_settings.json")
    monkeypatch.setattr(drafts, "DEFAULT_DIR", tmp_path / "drafts")
    return TestClient(app)


def png_bytes(w=300, h=200):
    arr = np.tile(np.linspace(255, 0, w, dtype=np.uint8), (h, 1))
    b = io.BytesIO(); Image.fromarray(arr, "L").save(b, "PNG")
    return b.getvalue()


def slow_import(monkeypatch):
    """Thay dây chuyền ảnh bằng tác vụ chậm có điểm hủy, để thử hủy / thay thế tác vụ."""
    def slow(data, name, opts, token=None, ctx=None):
        for i in range(30):
            ctx.step("style", i / 30, "chậm")
            time.sleep(0.02)
        return {"task": token, "source": {}, "warnings": []}
    monkeypatch.setattr(raster, "import_raster", slow)       # INPROC: run_import gọi thẳng hàm này


def wait_state(client, token, states=("done", "failed", "cancelled"), timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        body = client.get(f"/api/draw/tasks/{token}").json()
        if body["state"] in states:
            return body
        time.sleep(0.02)
    raise AssertionError(body)


def import_svg(client):
    r = client.post("/api/draw/import", files={"file": ("a.svg", SVG)}, data={"options": '{"svg": {"frame": "page"}}'})
    assert r.status_code == 202
    return r.json()["task"]


def test_schema_has_the_new_groups(client):
    body = client.get("/api/draw/schema").json()
    assert {"raster", "style", "palette"} <= set(body["params"])
    assert body["pens"] == [0.2, 0.4] and "spiral" in body["styles"]
    layout = {r["name"]: r for r in body["params"]["layout"]}
    assert layout["rotate"]["choices"] == [0, 90, 180, 270]


def test_import_svg_runs_in_background_and_feeds_preview_and_gcode(client):
    token = import_svg(client)
    done = wait_state(client, token)
    assert done["state"] == "done" and done["progress"] == 1.0 and done["source"]["layers"]
    pv = client.get(f"/api/draw/tasks/{token}/preview").json()
    assert pv["layers"][0]["strokes"] and pv["bounds"]["w"] > 0
    assert pv["frame"]["w"] == pytest.approx(100, abs=0.5)        # frame=page: khung là trang SVG
    r = client.post("/api/draw/gcode", json={"task": token, "machine": MACHINE, "gcode": GCODE})
    assert r.status_code == 200 and r.json()["files"][0]["stats"]["strokes"] >= 1


def test_import_image_traces_strokes_and_feeds_preview_and_gcode(client):
    r = client.post("/api/draw/import", files={"file": ("p.png", png_bytes())},
                    data={"options": '{"raster": {"pen_width_mm": 0.4, "quality": "draft"}, "style": {"kind": "wave"},'
                                     ' "layout": {"paper": "a5", "margin_mm": 5}}'})
    done = wait_state(client, r.json()["task"])
    assert done["state"] == "done" and done["warnings"] == []
    src = done["source"]
    assert src["mode"] == "raster" and src["layers"][0]["strokes"] > 0
    assert src["page_mm"]["w"] <= 138 + 1e-6 and src["page_mm"]["h"] <= 200 + 1e-6   # gọn trong A5 trừ lề
    pv = client.get(f"/api/draw/tasks/{r.json()['task']}/preview").json()
    assert pv["frame"]["w"] == pytest.approx(src["page_mm"]["w"], abs=0.01)
    g = client.post("/api/draw/gcode", json={"task": r.json()["task"], "machine": MACHINE, "gcode": GCODE,
                                             "layout": {"paper": "a5"}})
    assert g.status_code == 200


def test_import_image_bad_data_fails_with_bad_image(client):
    r = client.post("/api/draw/import", files={"file": ("p.png", b"not a png")})
    done = wait_state(client, r.json()["task"])
    assert done["state"] == "failed" and done["error"]["code"] == "bad_image"


def test_import_rejects_bad_input(client):
    r = client.post("/api/draw/import", files={"file": ("a.txt", b"x")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_image"
    r = client.post("/api/draw/import", files={"file": ("a.png", b"x")}, data={"options": '{"style": {"kind": "x"}}'})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"
    r = client.post("/api/draw/import", files={"file": ("a.png", b"x")}, data={"options": '{"nope": 1}'})
    assert r.status_code == 400


def test_failed_job_reports_the_error_code(client):
    token = client.post("/api/draw/import", files={"file": ("a.svg", b"<svg></svg>")}).json()["task"]
    done = wait_state(client, token)
    assert done["state"] == "failed" and done["error"]["code"] == "empty_drawing"


def test_new_request_cancels_the_running_one(client, monkeypatch):
    slow_import(monkeypatch)
    first = client.post("/api/draw/import", files={"file": ("a.png", b"x")}).json()["task"]
    second = client.post("/api/draw/import", files={"file": ("b.png", b"x")}).json()["task"]
    assert wait_state(client, first)["state"] == "cancelled"
    assert wait_state(client, second)["state"] == "done"


def test_cancel_route_and_unknown_task(client, monkeypatch):
    slow_import(monkeypatch)
    token = client.post("/api/draw/import", files={"file": ("a.png", b"x")}).json()["task"]
    assert client.post(f"/api/draw/tasks/{token}/cancel").json() == {"ok": True}
    assert wait_state(client, token)["state"] == "cancelled"
    r = client.get("/api/draw/tasks/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_task"
    assert client.get("/api/draw/tasks/nope/preview").status_code == 404


# --- bản thảo ---------------------------------------------------------------------------
def make_draft(client, name="Nhà xinh"):
    token = import_svg(client)
    wait_state(client, token)
    r = client.post("/api/draw/drafts", json={"task": token, "name": name, "machine": MACHINE, "gcode": GCODE,
                                              "layout": {"paper": "a5"}})
    assert r.status_code == 201, r.text
    return r.json()["draft"]


def test_draft_roundtrip(client):
    d = make_draft(client)
    assert d["id"].endswith("-nha-xinh") and d["pinned"] is False
    listing = client.get("/api/draw/drafts").json()["drafts"]
    assert [x["id"] for x in listing] == [d["id"]]
    gcode = client.get(f"/api/draw/drafts/{d['id']}/gcode/{d['files'][0]['name']}")
    assert gcode.status_code == 200 and gcode.text.startswith("G90 G21")
    svg = client.get(f"/api/draw/drafts/{d['id']}/preview.svg")
    assert svg.headers["content-type"].startswith("image/svg+xml") and "<path" in svg.text
    r = client.patch(f"/api/draw/drafts/{d['id']}", json={"pinned": True, "priority": 5, "name": "Đổi tên"})
    assert r.json()["draft"]["pinned"] is True and r.json()["draft"]["name"] == "Đổi tên"
    assert client.delete(f"/api/draw/drafts/{d['id']}").json() == {"ok": True}
    assert client.get("/api/draw/drafts").json()["drafts"] == []


def test_draft_ids_and_files_are_validated(client):
    d = make_draft(client)
    for bad in ("..", "x", "20260101-000000-%2e%2e", d["id"].upper()):
        assert client.get(f"/api/draw/drafts/{bad}").status_code == 404
    for bad in ("meta", "..%2Fmeta", "draw-../x", "preview"):
        assert client.get(f"/api/draw/drafts/{d['id']}/gcode/{bad}").status_code == 404


def test_pinned_and_priority_come_first_and_pruning_keeps_pinned(client):
    a = make_draft(client, "a")
    time.sleep(1.1)                          # tên thư mục tính theo giây
    b = make_draft(client, "b")
    assert [x["id"] for x in client.get("/api/draw/drafts").json()["drafts"]] == [b["id"], a["id"]]
    client.patch(f"/api/draw/drafts/{a['id']}", json={"pinned": True})
    assert client.get("/api/draw/drafts").json()["drafts"][0]["id"] == a["id"]
    r = client.put("/api/draw/settings", json={"draft_dir": "", "max_count": 1, "max_mb": 100})
    assert r.status_code == 200
    time.sleep(1.1)
    c = make_draft(client, "c")
    ids = [x["id"] for x in client.get("/api/draw/drafts").json()["drafts"]]
    assert a["id"] in ids and c["id"] in ids and b["id"] not in ids      # bản ghim ở lại, bản cũ không ghim bị dọn


def test_settings_validation_and_custom_folder(client, tmp_path):
    for bad in ({"draft_dir": "relative/path", "max_count": 5, "max_mb": 100},
                {"draft_dir": str(tmp_path / ".." / "x"), "max_count": 5, "max_mb": 100},
                {"draft_dir": "", "max_count": 0, "max_mb": 100},
                {"draft_dir": "", "max_count": 5, "max_mb": 1}):
        assert client.put("/api/draw/settings", json=bad).status_code == 400
    folder = tmp_path / "ban-thao"
    r = client.put("/api/draw/settings", json={"draft_dir": str(folder), "max_count": 5, "max_mb": 100})
    assert r.status_code == 200 and folder.is_dir()
    d = make_draft(client)
    assert (folder / d["id"] / "meta.json").is_file()
    assert client.get("/api/draw/settings").json()["settings"]["draft_dir"] == str(folder)


# --- xoay ----------------------------------------------------------------------------------
def test_rotate_layers_turns_clockwise_and_swaps_the_box():
    src = Box(10, 20, 40, 10)
    layer = Layer("1", [[(10, 20), (50, 30)]])
    out, box = lo.rotate_layers([layer], src, 90)
    assert (box.w, box.h) == (10, 40)
    assert out[0].strokes[0] == [(20, 20), (10, 60)]             # góc trên trái -> góc trên phải
    out, box = lo.rotate_layers([layer], src, 180)
    assert (box.w, box.h) == (40, 10) and out[0].strokes[0] == [(50, 30), (10, 20)]
    out, box = lo.rotate_layers([layer], src, 270)
    assert out[0].strokes[0] == [(10, 60), (20, 20)]
    assert lo.rotate_layers([layer], src, 0)[0] is not None


def test_gcode_with_rotate_changes_the_box_shape(client):
    body = {"layers": [{"id": "1", "strokes": [[[0, 0], [100, 0], [100, 20]]]}], "machine": MACHINE,
            "gcode": GCODE, "layout": {"paper": "a4", "margin_mm": 0}}
    flat = client.post("/api/draw/gcode", json=body).json()["box"]
    body["layout"]["rotate"] = 90
    turned = client.post("/api/draw/gcode", json=body).json()["box"]
    assert flat["w"] == 210 and turned["h"] == 297
    assert client.post("/api/draw/gcode", json={**body, "layout": {"rotate": 45}}).status_code == 400
