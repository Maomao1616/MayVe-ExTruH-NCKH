"""Mọi nút và mọi dòng terminal phải tới được board; hành vi theo log MKS DLC32 thật
(MACHINE.md 29/10/2026). Kiểm bằng SimLink đã hiệu chỉnh: KHÔNG thay cho thử máy thật."""
import pytest

from app.links.protocol import homing_axes, is_motion_free_command, is_read_only_command
from app.services.machine import MachineService, ServiceError
from tests.helpers import wait_for
from tests.test_machine_service import FakeSerial


def homed_service(speed=20):
    svc = MachineService(allow_motion=True)
    svc.connect("sim", sim_speed=speed)
    assert wait_for(lambda: svc._status is not None, 3.0)
    svc.send_line("$H")
    assert wait_for(lambda: svc._homed_guess, 8.0)
    assert wait_for(lambda: (svc._status or {}).get("state") == "Idle", 3.0)
    return svc


def state(svc):
    return (svc._status or {}).get("state")


def texts_since(svc, seq):
    return [e["text"] for e in svc.log_since(seq)["entries"]]


# --- terminal -------------------------------------------------------------------
def test_terminal_realtime_chars_work_during_job():
    svc = homed_service(speed=1)
    try:
        svc.start_job("slow", ["G90", "G1 F600 X100"])
        assert wait_for(lambda: state(svc) == "Run", 5.0)
        with pytest.raises(ServiceError) as e:
            svc.send_line("$I")                      # dòng thường vẫn bị chặn khi chạy job
        assert e.value.code == "job_running"
        assert svc.send_line("!") == {"sent": "hold"}
        assert wait_for(lambda: state(svc) == "Hold", 2.0)
        assert svc.send_line("~") == {"sent": "resume"}
        assert wait_for(lambda: state(svc) == "Run", 2.0)
        assert svc._job.active                       # không sinh `ok` lạ làm lệch tác vụ
        svc.cancel_job()
    finally:
        svc.disconnect()


def test_real_machine_lock_still_allows_info_and_unlock():
    svc = MachineService(allow_motion=False)
    fake = FakeSerial()
    svc._link, svc._info = fake, {"mode": "serial", "port": "COM9", "baud": 115200}
    try:
        for line in ("$$", "$E", "$A", "$Errors/List", "$Limits", "$X", "?"):
            svc.send_line(line)
        for line in ("G0 X10", "$H", "$J=G91 X1 F100"):
            with pytest.raises(ServiceError) as e:
                svc.send_line(line)
            assert e.value.code == "motion_locked"
        assert fake.sent == ["$$", "$E", "$A", "$Errors/List", "$Limits", "$X", b"?"]
    finally:
        svc._link = None


def test_command_classification_from_board_cmd_list():
    for ok in ("$Build/Info", "$GrblSettings/List", "$Alarms/List", "$Startup/Show", "$ESP420"):
        assert is_read_only_command(ok), ok
    assert is_motion_free_command("$Alarm/Disable") and not is_read_only_command("$X")
    for bad in ("$Bye", "$System/Control=RESTART", "$Motor/Disable", "$SD/Run=/a.gcode"):
        assert not is_motion_free_command(bad), bad
    assert homing_axes("$Home/X") == "X" and homing_axes("$h") == "XY"
    assert homing_axes("$HZ") is None


# --- Home -----------------------------------------------------------------------
def test_homed_msg_marks_homed_without_status():
    svc = MachineService(allow_motion=True)
    with svc._lock:
        svc._on_line("[MSG:Homed:X]")
        assert svc._homed_guess is False
        svc._on_line("[MSG:Homed:Y]")
        assert svc._homed_guess is True


# --- dừng an toàn theo hành vi board thật ----------------------------------------
def test_hard_stop_from_hold_resets_without_alarm_and_keeps_home():
    # Thật (Test 4a): Reset khi Hold:0 -> không alarm, nên vẫn giữ trạng thái Home.
    svc = homed_service(speed=1)
    try:
        svc.start_job("slow", ["G90", "G1 F600 X100"])
        assert wait_for(lambda: state(svc) == "Run", 5.0)
        svc.send_realtime("hold")
        assert wait_for(lambda: state(svc) == "Hold" and svc._status["substate"] == "0", 3.0)
        before = svc.log_since(0)["last_seq"]
        svc.cancel_job("soft", lift_z=5.0, lift_feed=3000.0)   # đang Hold -> chuyển sang hard
        assert wait_for(lambda: not svc.snapshot()["stopping"], 15.0)
        after = texts_since(svc, before)
        assert any("pen lift confirmed" in t for t in after), after
        assert not any(t.startswith("ALARM:") for t in after)
        assert svc._homed_guess is True
    finally:
        svc.disconnect()


def test_hard_stop_resets_before_unlock_after_hard_limit():
    # Thật: ALARM:1 -> "Reset to continue": $X một mình không thoát được Alarm.
    svc = homed_service(speed=1)
    try:
        svc.start_job("slow", ["G90", "G1 F200 X100"])
        assert wait_for(lambda: state(svc) == "Run", 5.0)
        svc.cancel_job("soft", lift_z=5.0, lift_feed=3000.0)
        svc._link.simulate_hard_limit()
        assert wait_for(lambda: not svc.snapshot()["stopping"], 20.0)
        log = texts_since(svc, 0)
        assert any("needs Reset before $X" in t for t in log), log[-12:]
        assert any("pen lift confirmed" in t for t in log), log[-12:]
        assert state(svc) == "Idle"
    finally:
        svc.disconnect()


def test_reset_required_is_reported_and_cleared():
    svc = homed_service()
    try:
        svc._link.simulate_hard_limit()
        assert wait_for(lambda: (svc.snapshot()["last_alarm"] or {}).get("reset_required"), 2.0)
        svc.send_realtime("reset")
        assert svc._reset_required is False
    finally:
        svc.disconnect()


def test_ver_line_from_dollar_i_is_kept_as_firmware():
    # Board thật không reset khi mở cổng nên thường không có banner; `$I` trả [VER:...].
    svc = MachineService(allow_motion=True)
    with svc._lock:
        svc._on_line("[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]")
    assert svc.snapshot()["banner"] == "[VER:4.1 FluidNC v4.1.1 (esp32-wifi) :]"


def test_feed_override_actions_reach_board_and_status_keeps_last_value():
    svc = MachineService(allow_motion=False)
    fake = FakeSerial()
    svc._link, svc._info = fake, {"mode": "serial", "port": "COM9", "baud": 115200}
    try:
        for action in ("feed_minus10", "feed_plus1", "feed_reset"):
            svc.send_realtime(action)               # máy thật đang khóa vẫn gửi được
        assert fake.sent == [b"\x92", b"\x93", b"\x90"]
        with svc._lock:
            svc._on_line("<Run|MPos:1,2,0|Ov:80,100,100>")
            svc._on_line("<Run|MPos:1,2,0>")         # báo cáo không có Ov: giữ 80
        assert svc.snapshot()["machine"]["overrides"] == [80, 100, 100]
        svc.send_realtime("reset")
        assert svc._overrides == [100, 100, 100]
    finally:
        svc._link = None
