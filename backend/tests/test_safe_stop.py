"""Hồi quy cho đợt tối ưu backend 29/10/2026 (cac_van_de_can_toi_uu_backend.txt).
Chỉ kiểm bằng SimLink: KHÔNG chứng minh hành vi trên firmware/máy thật."""
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.links.protocol import parse_status
from app.services import job as job_module
from app.services.machine import MachineService, ServiceError, _num, machine
from tests.helpers import wait_for


def homed_service(speed=20):
    svc = MachineService(allow_motion=True)
    svc.connect("sim", sim_speed=speed)
    assert wait_for(lambda: svc._status is not None, 3.0)
    svc.send_line("$H")
    assert wait_for(lambda: svc._homed_guess, 8.0), "sim không Home xong"
    assert wait_for(lambda: (svc._status or {}).get("state") == "Idle", 3.0)
    return svc


def texts(svc):
    return [e["text"] for e in svc.log_since(0)["entries"]]


def has_log(svc, part):
    return any(part in t for t in texts(svc))


def long_job():
    return ["G1 X10 F600", "G1 X20 F600"] * 60


# --- 1. không cho job/lệnh khác chen vào lúc đang dừng ------------------------------
def test_new_job_and_motion_blocked_while_stopping():
    svc = homed_service()
    try:
        svc.start_job("t", long_job())
        assert wait_for(lambda: (svc._status or {}).get("state") == "Run", 3.0)
        svc.cancel_job("hard", lift_z=5.0, lift_feed=3000.0)
        # Ngay khi cancel trả về (luồng dừng có thể chưa chạy) đã phải chặn.
        assert svc.snapshot()["stopping"] is True
        for call in (lambda: svc.start_job("x", ["G1 X1 F100"]),
                     lambda: svc.send_line("G0 X1"),
                     lambda: svc.send_realtime("resume"),
                     lambda: svc.cancel_job("soft")):
            with pytest.raises(ServiceError) as e:
                call()
            assert e.value.code == "stopping"
        svc.send_line("$I")                 # lệnh chỉ đọc vẫn được
        svc.send_realtime("status")         # hold/reset/status luôn được (an toàn)
        assert wait_for(lambda: not svc.snapshot()["stopping"], 15.0), texts(svc)[-8:]
        assert has_log(svc, "pen lift confirmed")
        svc.start_job("after", ["G1 X1 F600"])    # xong trình tự dừng thì chạy lại được
    finally:
        svc.disconnect()


def test_stopping_flag_cleared_when_cancel_has_no_job():
    svc = homed_service()
    try:
        with pytest.raises(ServiceError) as e:
            svc.cancel_job("hard", lift_z=5.0)
        assert e.value.code == "no_job"
        assert svc.snapshot()["stopping"] is False
    finally:
        svc.disconnect()


# --- 2. xác nhận nâng bút thật sự --------------------------------------------------
def test_pen_lift_rejected_is_not_reported_as_done():
    svc = homed_service()
    try:
        svc.start_job("t", long_job())
        assert wait_for(lambda: (svc._status or {}).get("state") == "Run", 3.0)
        svc.cancel_job("hard", lift_z=50.0, lift_feed=3000.0)   # vượt hành trình Z 5 mm của sim
        assert wait_for(lambda: not svc.snapshot()["stopping"], 15.0), texts(svc)[-8:]
        assert has_log(svc, "pen lift rejected by firmware (error:15)")
        assert not has_log(svc, "pen lift confirmed")
    finally:
        svc.disconnect()


def test_soft_stop_confirms_pen_position():
    svc = homed_service()
    try:
        svc.start_job("t", long_job())
        assert wait_for(lambda: (svc._status or {}).get("state") == "Run", 3.0)
        svc.cancel_job("soft", lift_z=5.0, lift_feed=3000.0)
        assert wait_for(lambda: has_log(svc, "pen lift confirmed (Z5)"), 20.0), texts(svc)[-8:]
    finally:
        svc.disconnect()


def test_gcode_numbers_never_use_exponent():
    assert _num(1e-5) == "0"
    assert _num(-0.00001) == "0"
    assert _num(1234567.0) == "1234567"
    assert _num(5.0) == "5" and _num(2.5) == "2.5"


def test_cancel_rejects_non_finite_lift():
    svc = homed_service()
    try:
        svc.start_job("t", long_job())
        for bad in ({"lift_z": float("nan")}, {"lift_feed": float("inf")}, {"lift_feed": 0}):
            with pytest.raises(ServiceError) as e:
                svc.cancel_job("hard", **{"lift_z": 5.0, **bad})
            assert e.value.code == "bad_request"
        assert svc._job.active                    # tham số sai: không hủy nửa vời
        svc.cancel_job()
    finally:
        svc.disconnect()


# --- 3. luồng dừng cũ không được gửi lệnh vào phiên mới ----------------------------
def test_old_stop_thread_never_writes_to_new_session():
    svc = homed_service(speed=1)
    try:
        svc.start_job("slow", ["G90", "G1 F200 X100"])           # soft stop sẽ chờ rất lâu
        assert wait_for(lambda: (svc._status or {}).get("state") == "Run", 5.0)
        svc.cancel_job("soft", lift_z=5.0, lift_feed=3000.0)
        time.sleep(0.2)
        svc.disconnect()
        svc.connect("sim", sim_speed=20)                          # nối lại ngay
        sent = []
        link = svc._link
        write_line, write_rt = link.write_line, link.write_realtime
        link.write_line = lambda line: (sent.append(line), write_line(line))[1]
        link.write_realtime = lambda data: (sent.append(data) if data != b"?" else None,
                                            write_rt(data))[1]
        assert svc.snapshot()["stopping"] is False
        assert wait_for(lambda: not any(t.name == "safe-stop" for t in threading.enumerate()), 3.0)
        time.sleep(0.3)
        assert sent == []
        assert has_log(svc, "safe stop abandoned")
    finally:
        svc.disconnect()


# --- 5. timeout / mất status lúc chờ máy chạy nốt ----------------------------------
def capture_realtime(svc):
    sent = []
    original = svc.send_realtime
    svc.send_realtime = lambda action: (sent.append(action), original(action))[1]
    return sent


def test_finish_timeout_puts_machine_on_hold(monkeypatch):
    monkeypatch.setattr(job_module, "FINISH_TIMEOUT_S", 0.5)
    svc = homed_service(speed=1)
    try:
        sent = capture_realtime(svc)
        svc.start_job("slow", ["G90", "G1 F200 X50"])
        assert wait_for(lambda: (svc._job.snapshot() or {}).get("state") == "failed", 5.0)
        assert svc._job.snapshot()["error"]["code"] == "timeout"
        assert "hold" in sent
        assert wait_for(lambda: has_log(svc, "Feed Hold confirmed"), 5.0)
        assert (svc._status or {}).get("state") == "Hold"
    finally:
        svc.disconnect()


def test_lost_status_while_finishing_fails_and_holds(monkeypatch):
    monkeypatch.setattr(job_module, "STATUS_STALE_S", 0.6)
    svc = homed_service(speed=1)
    try:
        sent = capture_realtime(svc)
        svc.start_job("slow", ["G90", "G1 F200 X50"])
        assert wait_for(lambda: (svc._job.snapshot() or {}).get("state") == "finishing", 5.0)
        svc._poll_stop.set()                                      # ngừng báo cáo trạng thái
        assert wait_for(lambda: (svc._job.snapshot() or {}).get("state") == "failed", 5.0)
        assert svc._job.snapshot()["error"]["code"] == "status_lost"
        assert "hold" in sent
        assert wait_for(lambda: has_log(svc, "stop is NOT confirmed"), 5.0)
    finally:
        svc.disconnect()


def test_single_idle_report_does_not_finish_job():
    svc = homed_service()
    try:
        svc.start_job("t", ["G1 X1 F600"])
        assert wait_for(lambda: (svc._job.snapshot() or {}).get("state") in ("finishing", "done"), 3.0)
        assert wait_for(lambda: svc._job.snapshot()["state"] == "done", 5.0)
        assert svc._status["state"] == "Idle"
    finally:
        svc.disconnect()


# --- 7. parser ---------------------------------------------------------------------
def test_non_finite_coordinates_are_dropped():
    st = parse_status("<Idle|MPos:nan,0,0|WCO:0,inf,0|FS:0,0>")
    assert st["mpos"] is None and st["wco"] is None and st["state"] == "Idle"


def test_wpos_not_computed_when_axis_count_differs():
    svc = MachineService(allow_motion=True)
    with svc._lock:
        svc._update_status(parse_status("<Idle|MPos:1,2,3|WCO:0,0,0>"))
        svc._update_status(parse_status("<Idle|MPos:1,2>"))
    assert svc._status["wpos"] is None


# --- 6. bảo vệ API -----------------------------------------------------------------
@pytest.fixture
def client():
    machine.disconnect()
    yield TestClient(app)
    machine.disconnect()


def test_foreign_host_is_rejected(client):
    r = client.get("/api/status", headers={"host": "evil.example"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "bad_host"
    assert client.get("/api/status", headers={"host": "127.0.0.1:8000"}).status_code == 200


def test_cross_origin_post_is_rejected(client):
    r = client.post("/api/disconnect", headers={"origin": "http://evil.example"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "bad_origin"
    r = client.post("/api/jobs/cancel", headers={"origin": "null"})
    assert r.status_code == 403
    r = client.post("/api/disconnect", headers={"origin": "http://testserver"})
    assert r.status_code == 200


def test_cancel_route_rejects_nan(client):
    r = client.post("/api/jobs/cancel", content='{"mode": "soft", "lift_z": NaN}',
                    headers={"content-type": "application/json"})
    assert r.status_code == 422
