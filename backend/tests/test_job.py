"""Tác vụ G-code: làm sạch dòng, chạy từng dòng chờ ok, lỗi, hủy, chặn lệnh khác."""
import pytest

from app.services.job import JobError, clean_gcode
from app.services.machine import MachineService, ServiceError
from tests.helpers import wait_for

SQUARE = ["G21 G90", "G0 X10 Y10", "G1 F6000", "G1 X20", "G1 Y20", "G1 X10", "G1 Y10", "G0 X0 Y0"]


@pytest.fixture
def svc():
    s = MachineService(allow_motion=False)
    yield s
    s.disconnect()


def homed(svc, speed=100):
    svc.connect("sim", sim_speed=speed)
    svc.send_line("$H")
    assert wait_for(lambda: svc.snapshot()["homed_guess"])
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Idle")


def job_state(svc):
    job = svc.snapshot()["job"]
    return job["state"] if job else None


# --- làm sạch -------------------------------------------------------------------
def test_clean_removes_comments_and_blanks():
    raw = ["%", "( header )", "G21 ; mm", "", "  G1   X1  Y2 (move) F100  ", "M30"]
    assert clean_gcode(raw) == ["G21", "G1 X1 Y2 F100", "M30"]


@pytest.mark.parametrize("bad", ["$H", "$X", "G1 X1 ?", "G0 !", "~", "G1 X1\x18", "1234", "G1 X" + "9" * 300])
def test_clean_rejects_dangerous_or_invalid(bad):
    with pytest.raises(JobError) as info:
        clean_gcode(["G21", bad])
    assert info.value.code == "bad_gcode"
    assert "dòng 2" in info.value.message


@pytest.mark.parametrize("bad", ["G92 X0 Y0", "G10 L20 P1 X0", "G28", "G28.1", "G30", "G53 G0 X0",
                                 "G55", "G59.1", "G38.2 Z-5 F100", "g92x0", "G0 X1 G92 Y0"])
def test_clean_blocks_coordinate_changes(bad):
    with pytest.raises(JobError) as info:
        clean_gcode(["G21", "G1 X1 F100", bad])
    assert info.value.code == "bad_gcode"
    assert "dòng 3" in info.value.message


@pytest.mark.parametrize("ok", ["G54", "G90 G21", "G91", "G20", "G17 G94", "G4 P0.2", "M3 S1000", "M5",
                                "M0", "G2 X1 Y1 I0.5 J0", "G1 X10 ; G92 trong chu thich",
                                "(G28 trong ngoac) G0 X1", "G0 X92", "G1 X10 F2800", "N10 G1 X1"])
def test_clean_keeps_normal_commands(ok):
    assert len(clean_gcode(["G21", ok])) == 2


def test_clean_reports_all_problems_with_line_numbers():
    raw = ["G21", "G28", "G1 X1 F100", "$H", "G92 X0"] + ["G10 L20 P1 X0"] * 4
    with pytest.raises(JobError) as info:
        clean_gcode(raw)
    msg = info.value.message
    assert "Tệp có 7 dòng" in msg
    assert "dòng 2: G28" in msg and "dòng 4:" in msg and "dòng 5: G92" in msg
    assert "và 2 dòng khác" in msg


# --- chạy -----------------------------------------------------------------------
def test_job_runs_to_done_without_flooding_log(svc):
    homed(svc)
    before = svc.log_since(0)["last_seq"]
    job = svc.start_job("square", SQUARE)
    assert job["state"] == "running" and job["total"] == len(SQUARE)
    assert wait_for(lambda: job_state(svc) == "done", timeout=10)
    final = svc.snapshot()["job"]
    assert final["acked"] == final["total"] == len(SQUARE) and final["error"] is None
    assert svc.snapshot()["machine"]["state"] == "Idle"
    new = [e for e in svc.log_since(before)["entries"]]
    assert not any(e["dir"] == "tx" for e in new)            # không ghi từng dòng đã gửi
    assert not any(e["text"] == "ok" for e in new)           # và không ghi từng `ok`
    assert any("Job started" in e["text"] for e in new)


def test_job_reports_soft_limit_alarm(svc):
    homed(svc)
    svc.start_job("too-far", ["G90", "G0 X1000"])     # máy thật: ok trước, ALARM:2 sau
    assert wait_for(lambda: job_state(svc) == "failed")
    error = svc.snapshot()["job"]["error"]
    assert error["code"] == "alarm" and error["device_code"] == 2


def test_job_stops_on_device_error_and_reports_line(svc):
    homed(svc)
    svc.start_job("bad", ["G21", "G1 F6000", "G2 X50 Y0 R1", "G1 X5"])   # R không với tới: firmware báo error:33
    assert wait_for(lambda: job_state(svc) == "failed")
    job = svc.snapshot()["job"]
    assert job["error"]["code"] == "device_error" and job["error"]["line"] == 3
    assert job["error"]["device_code"] == 33 and job["acked"] == 3


def test_arcs_are_accepted_by_sim(svc):
    homed(svc)
    svc.start_job("arc", ["G90", "G1 F6000", "G2 X10 Y10 I5 J0"])
    assert wait_for(lambda: job_state(svc) == "done", timeout=10)


def test_cancel_stops_job_and_machine(svc):
    homed(svc, speed=1)                       # tốc độ thật để còn kịp hủy giữa chừng
    svc.start_job("slow", ["G90", "G1 F200", "G1 X200", "G1 X0"])
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Run", timeout=5)
    result = svc.cancel_job()
    assert result["state"] == "cancelled"
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Alarm", timeout=5)
    assert svc.snapshot()["job"]["state"] == "cancelled"      # Alarm 3 do hủy không đổi kết quả


def test_other_commands_blocked_while_running(svc):
    homed(svc, speed=1)
    svc.start_job("slow", ["G90", "G1 F200", "G1 X100"])
    with pytest.raises(ServiceError) as info:
        svc.send_line("$I")
    assert info.value.code == "job_running"
    svc.cancel_job()


def test_cannot_start_two_jobs(svc):
    homed(svc, speed=1)
    svc.start_job("slow", ["G90", "G1 F200", "G1 X100"])
    with pytest.raises(ServiceError) as info:
        svc.start_job("again", ["G1 X1"])
    assert info.value.code in ("job_running", "not_idle")
    svc.cancel_job()


def test_start_requires_connection_and_idle(svc):
    with pytest.raises(ServiceError) as info:
        svc.start_job("x", ["G0 X1"])
    assert info.value.code == "not_connected"
    svc.connect("sim", sim_speed=100)
    assert wait_for(lambda: svc.snapshot()["machine"] is not None)
    # Board thật: bật lên đã ở Alarm 14 (must_home).
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Alarm")
    with pytest.raises(ServiceError) as info:
        svc.start_job("x", ["G0 X1"])
    assert info.value.code == "not_idle"


def test_start_rejects_bad_gcode_and_empty(svc):
    homed(svc)
    with pytest.raises(ServiceError) as info:
        svc.start_job("x", ["G21", "$H"])
    assert info.value.code == "bad_gcode"
    with pytest.raises(ServiceError) as info:
        svc.start_job("x", ["( chỉ có chú thích )", ""])
    assert info.value.code == "empty_job"


def test_disconnect_aborts_job(svc):
    homed(svc, speed=1)
    svc.start_job("slow", ["G90", "G1 F200", "G1 X100"])
    svc.disconnect()
    assert svc.snapshot()["job"]["state"] == "failed"
    assert svc.snapshot()["job"]["error"]["code"] == "disconnected"
