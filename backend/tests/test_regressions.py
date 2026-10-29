"""Hồi quy cho các lỗi đã gặp ở Giai đoạn "xác thực" (28/10/2026).
Mỗi test mô tả lỗi cũ; test này PHẢI fail nếu lỗi quay lại."""
import threading
import time

import pytest

from app.services import job as job_module
from app.services.machine import MachineService
from tests.helpers import wait_for


def homed_service(speed=20):
    svc = MachineService(allow_motion=True)
    svc.connect("sim", sim_speed=speed)
    assert wait_for(lambda: svc._status is not None, 3.0), "chưa có báo cáo trạng thái đầu tiên"
    svc.send_line("$H")
    assert wait_for(lambda: svc._homed_guess, 8.0), "sim không Home xong"
    return svc


def texts(svc):
    return [e["text"] for e in svc.log_since(0)["entries"]]


def long_job_lines(n=60):
    return ["G1 X10 F600", "G1 X20 F600"] * n


def test_ok_after_cancel_is_not_swallowed():
    """Lỗi cũ: _awaiting còn True sau khi hủy nên `ok` đầu tiên của lệnh người dùng bị nuốt."""
    svc = homed_service()
    try:
        svc.start_job("t", long_job_lines())
        time.sleep(0.3)
        svc.cancel_job()
        time.sleep(0.6)
        before = texts(svc).count("ok")
        svc._on_line("ok")
        assert texts(svc).count("ok") == before + 1
    finally:
        svc.disconnect()


def test_error_clears_homing_pending():
    """Lỗi cũ: Home bị từ chối (error) nhưng _homing_pending còn, `ok` sau đó làm homed_guess bật sai."""
    svc = MachineService(allow_motion=True)
    svc.connect("sim")
    try:
        svc._homing_pending = True
        svc._homing_axes = "XY"
        svc._on_line("error:9")
        assert svc._homing_pending is False
        svc._on_line("ok")
        assert svc._homed_guess is False
    finally:
        svc.disconnect()


def test_no_line_written_after_cancel():
    """Lỗi cũ: runner đã kiểm tra 'còn sống' rồi mới ghi, hủy xen giữa thì vẫn lọt 1 dòng ra cổng."""
    svc = homed_service()
    try:
        wrote = []
        link_write = svc._link.write_line
        svc._link.write_line = lambda line: (wrote.append(line), link_write(line))[1]
        original = svc.job_write

        def slow(line, job_id):
            time.sleep(0.2)
            original(line, job_id)

        svc.job_write = slow
        svc.start_job("r", ["G1 X1 F100"] * 5)
        time.sleep(0.05)
        svc._job.cancel()
        time.sleep(0.6)
        assert wrote == []
    finally:
        svc.disconnect()


def test_timeout_puts_machine_on_hold(monkeypatch):
    """Lỗi cũ: timeout chỉ báo failed, không Feed Hold nên máy có thể chạy nốt lệnh đã nằm trong bộ đệm."""
    monkeypatch.setattr(job_module, "RESPONSE_TIMEOUT_S", 0.5, raising=True)
    svc = homed_service()
    try:
        sent = []
        original = svc.send_realtime
        svc.send_realtime = lambda action: (sent.append(action), original(action))[1]
        svc._link.write_line = lambda line: None      # máy "câm": không bao giờ trả ok
        svc.start_job("t", ["G1 X1 F100"])
        assert wait_for(lambda: svc._job.snapshot()["state"] == "failed", 3.0)
        assert "hold" in sent
    finally:
        svc.disconnect()


def test_reconnect_leaves_one_poller():
    """Lỗi cũ: cờ dừng dùng chung nên luồng thăm dò cũ 'sống lại' khi kết nối lại nhanh."""
    svc = MachineService(allow_motion=True)
    for _ in range(5):
        svc.connect("sim", sim_speed=20)
        svc.disconnect()
    time.sleep(0.6)
    names = [t.name for t in threading.enumerate() if t.name == "status-poller"]
    assert names == []
    svc.connect("sim", sim_speed=20)
    try:
        time.sleep(0.3)
        assert len([t for t in threading.enumerate() if t.name == "status-poller"]) == 1
    finally:
        svc.disconnect()


def test_each_connection_gets_its_own_stop_flag():
    """Bản chất của lỗi poller: cờ dừng phải là của RIÊNG từng lần kết nối, và cờ cũ phải giữ trạng thái đã dừng."""
    svc = MachineService(allow_motion=True)
    svc.connect("sim", sim_speed=20)
    first = svc._poll_stop
    svc.disconnect()
    svc.connect("sim", sim_speed=20)
    try:
        assert svc._poll_stop is not first
        assert first.is_set()
    finally:
        svc.disconnect()


def test_reset_clears_stale_error_and_alarm():
    svc = MachineService(allow_motion=True)
    svc.connect("sim")
    try:
        svc._on_line("error:9")
        assert svc._last_error is not None
        svc.send_realtime("reset")
        assert svc._last_error is None and svc._last_alarm is None
    finally:
        svc.disconnect()


# ---- hủy tác vụ an toàn -------------------------------------------------------
def z_of(svc):
    mpos = (svc._status or {}).get("mpos")
    return None if not mpos else mpos[2]


def test_hard_stop_lifts_pen_after_reset():
    svc = homed_service()
    try:
        svc.start_job("t", long_job_lines())
        assert wait_for(lambda: (svc._status or {}).get("state") == "Run", 3.0)
        svc.cancel_job("hard", lift_z=5.0, lift_feed=3000.0)
        assert wait_for(lambda: any("pen lift sent" in x for x in texts(svc)), 12.0), texts(svc)[-8:]
        assert wait_for(lambda: z_of(svc) is not None and abs(z_of(svc) - 5.0) < 0.05, 6.0)
        assert svc._job.snapshot()["state"] == "cancelled"
    finally:
        svc.disconnect()


def test_soft_stop_finishes_queue_then_lifts_without_alarm():
    svc = homed_service()
    try:
        svc.start_job("t", long_job_lines())
        assert wait_for(lambda: (svc._status or {}).get("state") == "Run", 3.0)
        svc.cancel_job("soft", lift_z=5.0, lift_feed=3000.0)
        assert wait_for(lambda: any("pen lift sent" in x for x in texts(svc)), 20.0), texts(svc)[-8:]
        assert wait_for(lambda: z_of(svc) is not None and abs(z_of(svc) - 5.0) < 0.05, 6.0)
        assert not any(x.startswith("ALARM:") for x in texts(svc))
        assert svc._homed_guess is True            # Dừng êm giữ nguyên trạng thái Home
    finally:
        svc.disconnect()


def test_default_cancel_mode_is_plain_reset():
    svc = homed_service()
    try:
        svc.start_job("t", long_job_lines())
        time.sleep(0.3)
        svc.cancel_job()
        assert wait_for(lambda: any(x == "reset" for x in
                                    [e["text"] for e in svc.log_since(0)["entries"]
                                     if e["source"] == "realtime"]), 2.0)
    finally:
        svc.disconnect()


def test_bad_cancel_mode_rejected():
    svc = homed_service()
    try:
        svc.start_job("t", long_job_lines())
        time.sleep(0.2)
        from app.services.machine import ServiceError
        with pytest.raises(ServiceError):
            svc.cancel_job("nonsense")
        svc.cancel_job()
    finally:
        svc.disconnect()
