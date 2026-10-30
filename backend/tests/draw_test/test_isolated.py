"""Xử lý ảnh trong tiến trình riêng: kết quả như chạy thẳng, hủy / quá giờ / sập đều gọn."""
import io
import sys
import time

import numpy as np
import pytest
from PIL import Image

from app.services.drawing import DrawError, isolated, raster
from app.services.drawing.store import TASKS
from app.services.drawing.tasks import Cancelled


def png(w=300, h=200):
    arr = np.tile(np.linspace(255, 0, w, dtype=np.uint8), (h, 1))
    b = io.BytesIO(); Image.fromarray(arr, "L").save(b, "PNG")
    return b.getvalue()


class Ctx:
    def __init__(self, cancel_after=None):
        self.steps, self.cancel_after, self.t0 = [], cancel_after, time.time()

    def step(self, name, progress, message=""):
        self.steps.append((name, progress))
        self.check()

    def check(self):
        if self.cancel_after is not None and time.time() - self.t0 > self.cancel_after:
            raise Cancelled()


@pytest.fixture
def subprocess_mode(monkeypatch):
    monkeypatch.delenv("EXTRUXY_DRAW_INPROC", raising=False)


OPTS = {"raster": {"quality": "draft"}, "layout": {"paper": "a5"}}


def test_subprocess_gives_the_same_drawing_as_in_process(subprocess_mode, monkeypatch):
    ctx = Ctx()
    out = isolated.run_import(png(), "x.png", OPTS, "tok-sub", ctx)
    monkeypatch.setenv("EXTRUXY_DRAW_INPROC", "1")
    ref = isolated.run_import(png(), "x.png", OPTS, "tok-ref", Ctx())
    a, b = TASKS.get("tok-sub"), TASKS.get("tok-ref")
    assert [l.strokes for l in a.layers] == [l.strokes for l in b.layers]
    assert out["source"]["layers"][0]["strokes"] == ref["source"]["layers"][0]["strokes"]
    assert {s for s, _ in ctx.steps} >= {"read", "tone", "style", "optimize"}
    assert out["source"]["timings"]["total"] > 0


def test_domain_errors_cross_the_process_boundary(subprocess_mode):
    with pytest.raises(DrawError) as e:
        isolated.run_import(b"not an image", "x.png", OPTS, "tok-bad", Ctx())
    assert e.value.code == "bad_image"


def test_cancel_kills_the_child_quickly(subprocess_mode, monkeypatch):
    seen = {}
    real_popen = isolated.subprocess.Popen

    def spy(*a, **k):
        seen["proc"] = real_popen(*a, **k)
        return seen["proc"]
    monkeypatch.setattr(isolated.subprocess, "Popen", spy)
    t0 = time.time()
    with pytest.raises(Cancelled):
        isolated.run_import(png(3000, 2000), "x.png", {"raster": {"pen_width_mm": 0.2}, "layout": {"paper": "a4"}},
                            "tok-cancel", Ctx(cancel_after=0.3))
    assert time.time() - t0 < 6
    assert seen["proc"].poll() is not None                  # tiến trình con đã chết, không để mồ côi


def test_timeout_stops_the_child(subprocess_mode, monkeypatch):
    monkeypatch.setenv("EXTRUXY_DRAW_TIMEOUT_S", "1")
    with pytest.raises(DrawError) as e:
        isolated.run_import(png(3000, 2000), "x.png", {"raster": {"pen_width_mm": 0.2}, "layout": {"paper": "a4"}},
                            "tok-slow", Ctx())
    assert e.value.code == "worker_timeout"


def test_child_crash_is_reported(subprocess_mode, monkeypatch):
    monkeypatch.setattr(isolated, "BACKEND_DIR", isolated.BACKEND_DIR / "nonexistent-dir-for-test")
    with pytest.raises(DrawError) as e:
        isolated.run_import(png(), "x.png", OPTS, "tok-crash", Ctx())
    assert e.value.code in ("worker_crashed",)


def test_inproc_switch_runs_without_a_child(monkeypatch):
    monkeypatch.setenv("EXTRUXY_DRAW_INPROC", "1")
    monkeypatch.setattr(isolated.subprocess, "Popen", lambda *a, **k: pytest.fail("không được tạo tiến trình"))
    assert isolated.run_import(png(), "x.png", OPTS, "tok-inproc", Ctx())["task"] == "tok-inproc"
