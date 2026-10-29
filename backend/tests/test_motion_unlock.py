import time

import pytest

from app.services.machine import MachineService, ServiceError


def serial_like(monkeypatch=None, **env):
    """Máy ở chế độ 'serial' giả: dùng SimLink nhưng coi như máy thật để áp dụng khóa."""
    svc = MachineService(allow_motion=False)
    svc.connect("sim", sim_speed=50)
    svc._info["mode"] = "serial"          # chỉ để thử khóa
    return svc


def test_unlock_and_manual_lock():
    svc = serial_like()
    try:
        assert svc.connection_info()["motion_unlocked"] is False
        info = svc.set_motion(True)
        assert info["motion_unlocked"] is True and info["unlock_seconds_left"] > 0
        info = svc.set_motion(False)
        assert info["motion_unlocked"] is False
    finally:
        svc.disconnect()


def test_relock_on_disconnect():
    svc = serial_like()
    svc.set_motion(True)
    svc.disconnect()
    assert svc.allow_motion is False


def test_idle_timeout_relocks_but_busy_does_not():
    svc = serial_like()
    try:
        svc._unlock_minutes = 0.01            # 0,6 giây
        svc.set_motion(True)
        svc._status = {"state": "Run"}
        svc._motion_activity = time.time() - 5
        svc._check_relock()
        assert svc.allow_motion is True       # đang Run: không khóa
        svc._status = {"state": "Idle"}
        svc._motion_activity = time.time() - 5
        svc._check_relock()
        assert svc.allow_motion is False
    finally:
        svc.disconnect()


def test_permanent_unlock_cannot_be_relocked_or_timed_out():
    svc = MachineService(allow_motion=True)
    svc.connect("sim")
    try:
        svc._unlock_minutes = 0.01
        svc._motion_activity = time.time() - 100
        svc._check_relock()
        assert svc.allow_motion is True
        with pytest.raises(ServiceError) as e:
            svc.set_motion(False)
        assert e.value.code == "unlock_permanent"
    finally:
        svc.disconnect()


def test_pin_and_forbidden(monkeypatch):
    monkeypatch.setenv("EXTRUXY_UNLOCK_PIN", "1234")
    svc = MachineService(allow_motion=False)
    with pytest.raises(ServiceError) as e:
        svc.set_motion(True, "0000")
    assert e.value.code == "bad_pin"
    assert svc.set_motion(True, "1234")["motion_unlocked"] is True
    monkeypatch.setenv("EXTRUXY_NO_UNLOCK", "1")
    svc2 = MachineService(allow_motion=False)
    with pytest.raises(ServiceError) as e:
        svc2.set_motion(True)
    assert e.value.code == "unlock_forbidden"


def test_route_motion():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.post("/api/motion", json={"on": True})
    assert r.status_code == 200 and "motion_unlocked" in r.json()
    c.post("/api/motion", json={"on": False})
