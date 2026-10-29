"""Kiểm tra lớp HTTP: đường dẫn, mã trạng thái, hình dạng JSON mà frontend dựa vào."""
import time 
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.machine import machine
from tests.helpers import wait_for


@pytest.fixture
def client():
    machine.disconnect()
    yield TestClient(app)
    machine.disconnect()


def err_code(response):
    return response.json()["error"]["code"]


def test_health(client: TestClient):
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["service"] == "extruxy-backend"


def test_status_when_disconnected(client: TestClient):
    body = client.get("/api/status").json()
    assert body["connection"]["connected"] is False
    assert body["machine"] is None and body["updated_at"] is None
    assert body["homed_guess"] is False


def test_command_needs_connection(client: TestClient):
    r = client.post("/api/command", json={"line": "$I"})
    assert r.status_code == 409 and err_code(r) == "not_connected"


def test_realtime_needs_connection(client: TestClient):
    r = client.post("/api/realtime", json={"action": "hold"})
    assert r.status_code == 409 and err_code(r) == "not_connected"


def test_connect_validation(client: TestClient):
    assert client.post("/api/connect", json={"mode": "banana"}).status_code == 422
    r = client.post("/api/connect", json={"mode": "serial"})
    assert r.status_code == 400 and err_code(r) == "bad_request"


def test_connect_sim_status_shape_and_double_connect(client: TestClient):
    r = client.post("/api/connect", json={"mode": "sim", "sim_speed": 100})
    assert r.status_code == 200
    assert r.json()["connected"] is True and r.json()["motion_unlocked"] is True
    assert wait_for(lambda: client.get("/api/status").json()["machine"] is not None)

    body = client.get("/api/status").json()
    assert set(body) == {"connection", "machine", "homed_guess", "last_alarm",
                         "last_error", "banner", "updated_at", "stopping", "job"}
    assert body["job"] is None
    assert body["machine"]["state"] == "Alarm"          # board thật bật lên ở Alarm 14
    assert isinstance(body["updated_at"], float)

    again = client.post("/api/connect", json={"mode": "sim"})
    assert again.status_code == 409 and err_code(again) == "already_connected"


def test_command_validation(client: TestClient):
    client.post("/api/connect", json={"mode": "sim"})
    assert client.post("/api/command", json={"line": ""}).status_code == 422
    r = client.post("/api/command", json={"line": "G0 X1\nG0 X2"})
    assert r.status_code == 400 and err_code(r) == "bad_request"
    assert client.post("/api/realtime", json={"action": "explode"}).status_code == 422


def test_log_since(client: TestClient):
    client.post("/api/connect", json={"mode": "sim", "sim_speed": 100})
    client.post("/api/command", json={"line": "$I"})
    assert wait_for(lambda: any(e["text"] == "ok" for e in client.get("/api/log").json()["entries"]))
    full = client.get("/api/log").json()
    assert {"seq", "t", "dir", "source", "text"} <= set(full["entries"][0])
    assert client.get(f"/api/log?since={full['last_seq']}").json()["entries"] == []


def test_boot_alarm_unhomed_via_api(client: TestClient):
    client.post("/api/connect", json={"mode": "sim", "sim_speed": 100})
    assert wait_for(lambda: client.get("/api/status").json()["last_alarm"] is not None)
    body = client.get("/api/status").json()
    assert body["last_alarm"]["code"] == 14
    assert wait_for(lambda: (client.get("/api/status").json()["machine"] or {}).get("state") == "Alarm")

def test_disconnect_clears_machine(client: TestClient):
    assert client.post("/api/disconnect").json()["connected"] is False
    body = client.get("/api/status").json()
    assert body["connection"]["connected"] is False
    t0 = body["updated_at"]
    time.sleep(0.4)  # lâu hơn POLL_S: nếu poller còn chạy thì updated_at sẽ đổi
    assert client.get("/api/status").json()["updated_at"] == t0

def test_job_routes_validation(client):
    assert client.post("/api/jobs", json={"name": "x", "lines": []}).status_code == 422
    r = client.post("/api/jobs", json={"name": "x", "lines": ["G0 X1"]})
    assert r.status_code == 409 and err_code(r) == "not_connected"
    r = client.post("/api/jobs/cancel")
    assert r.status_code == 409 and err_code(r) == "no_job"


def test_job_rejects_dollar_lines_via_api(client):
    client.post("/api/connect", json={"mode": "sim", "sim_speed": 100})
    assert wait_for(lambda: client.get("/api/status").json()["machine"] is not None)
    r = client.post("/api/jobs", json={"name": "x", "lines": ["G21", "$H"]})
    assert r.status_code == 400 and err_code(r) == "bad_gcode"


def test_job_runs_via_api(client):
    client.post("/api/connect", json={"mode": "sim", "sim_speed": 100})
    client.post("/api/command", json={"line": "$H"})
    assert wait_for(lambda: client.get("/api/status").json()["homed_guess"])
    assert wait_for(lambda: (client.get("/api/status").json()["machine"] or {}).get("state") == "Idle")
    r = client.post("/api/jobs", json={"name": "t", "lines": ["G90", "G1 F6000", "G1 X10 Y10"]})
    assert r.status_code == 200 and r.json()["state"] == "running"
    assert wait_for(lambda: (client.get("/api/status").json()["job"] or {}).get("state") == "done",
                    timeout=10)
    r = client.post("/api/command", json={"line": "$I"})
    assert r.status_code == 200          # xong tác vụ thì gửi lệnh lại được
