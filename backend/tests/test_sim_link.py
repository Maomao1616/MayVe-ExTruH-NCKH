import pytest

from app.links.sim_link import SimLink
from app.protocol import classify_line, parse_status
from tests.helpers import wait_for


class Rig:
    def __init__(self, **kw):
        self.lines = []
        self.link = SimLink(speed=kw.pop("speed", 100), **kw)
        self.link.add_listener(self.lines.append)
        self.link.open()

    def status(self):
        n = len(self.lines)
        self.link.write_realtime(b"?")
        # `?` được trả lời ngay trong cùng luồng gọi
        for line in reversed(self.lines[n:]):
            st = parse_status(line)
            if st:
                return st
        raise AssertionError("không có báo cáo trạng thái")

    def count(self, text):
        return sum(1 for ln in self.lines if ln == text)

    def wait_idle(self, timeout=3.0):
        assert wait_for(lambda: self.status()["state"] == "Idle", timeout), self.lines[-5:]

    def close(self):
        self.link.close()


@pytest.fixture
def rig():
    r = Rig()
    yield r
    r.close()


def test_banner_on_open(rig):
    assert rig.lines[0].startswith("Grbl ")


def test_status_idle_at_start(rig):
    st = rig.status()
    assert st["state"] == "Idle" and st["mpos"] == [0.0, 0.0, 0.0]


def test_motion_before_homing_gives_alarm_14(rig):
    rig.link.write_line("G0 X10")
    assert wait_for(lambda: "ALARM:14" in rig.lines)
    assert rig.status()["state"] == "Alarm"


def test_unlock_then_jog_works_unhomed(rig):
    rig.link.write_line("G0 X10")
    assert wait_for(lambda: "ALARM:14" in rig.lines)
    rig.link.write_line("$X")
    rig.link.write_line("$J=G91 X10 F6000")
    assert wait_for(lambda: rig.count("ok") >= 2)
    rig.wait_idle()
    assert rig.status()["mpos"][0] == pytest.approx(10.0)


def test_jog_in_alarm_state_is_locked(rig):
    rig.link.write_line("G0 X10")
    assert wait_for(lambda: "ALARM:14" in rig.lines)
    rig.link.write_line("$J=G91 X1 F100")
    assert wait_for(lambda: "error:9" in rig.lines)


def test_homing_then_move(rig):
    rig.link.write_line("$H")
    assert wait_for(lambda: rig.status()["state"] == "Idle" and rig.count("ok") >= 1)
    rig.link.write_line("G90")
    rig.link.write_line("G1 X50 Y40 F6000")
    assert wait_for(lambda: rig.count("ok") >= 3)
    rig.wait_idle()
    assert rig.status()["mpos"][:2] == [pytest.approx(50.0), pytest.approx(40.0)]


def test_jog_beyond_travel_is_error_15(rig):
    rig.link.write_line("$J=G90 X999 F1000")
    assert wait_for(lambda: "error:15" in rig.lines)


def test_jog_without_feed_is_error_16(rig):
    rig.link.write_line("$J=G91 X1")
    assert wait_for(lambda: "error:16" in rig.lines)


def test_gcode_soft_limit_alarm(rig):
    rig.link.write_line("$H")
    assert wait_for(lambda: rig.count("ok") >= 1)
    rig.link.write_line("G1 X999 F1000")
    assert wait_for(lambda: "ALARM:2" in rig.lines)


def test_hold_and_resume():
    r = Rig(speed=2)  # chậm để kịp chen vào giữa chuyển động
    try:
        r.link.write_line("$X"); r.link.write_line("$J=G91 X100 F6000")
        assert wait_for(lambda: r.status()["state"] == "Jog")
        r.link.write_realtime(b"!")
        assert wait_for(lambda: r.status()["state"] == "Hold" and r.status()["substate"] == "0")
        x1 = r.status()["mpos"][0]
        import time; time.sleep(0.2)
        assert r.status()["mpos"][0] == pytest.approx(x1)
        r.link.write_realtime(b"~")
        assert wait_for(lambda: r.status()["state"] in ("Jog", "Idle"))
        r.wait_idle(timeout=6.0)
        assert r.status()["mpos"][0] == pytest.approx(100.0)
    finally:
        r.close()


def test_soft_reset_during_motion_gives_alarm_3_and_banner():
    r = Rig(speed=2)
    try:
        r.link.write_line("$X"); r.link.write_line("$J=G91 X100 F6000")
        assert wait_for(lambda: r.status()["state"] == "Jog")
        r.link.write_realtime(b"\x18")
        assert "ALARM:3" in r.lines
        assert r.lines[-1].startswith("Grbl ")
        assert r.status()["state"] == "Alarm"
    finally:
        r.close()


def test_planner_fills_and_holds_back_ok():
    r = Rig(speed=1)
    try:
        r.link.write_line("$H")
        assert wait_for(lambda: r.count("ok") >= 1, timeout=5.0)
        for i in range(40):
            r.link.write_line(f"G1 X{(i % 2) * 100 + 5} F600")
        assert wait_for(lambda: r.status()["planner_free"] == 0)
        oks_now = r.count("ok")
        assert oks_now < 41  # chưa thể ok hết khi planner đầy
    finally:
        r.close()


def test_default_travel_matches_config_14():
    # ConfigNCKH-14.yaml: X 285, Y 318, Z 5. Tắt must_home để thử biên mà không cần Home.
    r = Rig(must_home=False)
    try:
        r.link.write_line("G1 Y318 F6000")
        assert wait_for(lambda: r.count("ok") == 1)
        assert r.count("ALARM:2") == 0
        r.link.write_line("G1 Y318.5 F6000")
        assert wait_for(lambda: r.count("ALARM:2") == 1)
    finally:
        r.link.close()


def test_zero_sets_work_offset_and_reports_wco(rig):
    rig.link.write_line("$J=G91 G21 X10 F6000")
    assert wait_for(lambda: rig.count("ok") >= 1)
    rig.wait_idle()
    rig.link.write_line("G10 L20 P1 X0")
    assert wait_for(lambda: rig.count("ok") >= 2)
    st = rig.status()
    assert st["wco"] == [pytest.approx(10.0), 0.0, 0.0]
    assert st["mpos"][0] == pytest.approx(10.0)  # Zero không làm máy chuyển động


def test_absolute_jog_uses_work_coordinates(rig):
    rig.link.write_line("$J=G91 G21 X10 F6000")
    assert wait_for(lambda: rig.count("ok") >= 1)
    rig.wait_idle()
    rig.link.write_line("G10 L20 P1 X0")
    rig.link.write_line("$J=G90 G21 X5 F6000")
    assert wait_for(lambda: rig.count("ok") >= 3)
    rig.wait_idle()
    assert rig.status()["mpos"][0] == pytest.approx(15.0)  # work X5 = máy X15


def test_other_g10_forms_are_unsupported(rig):
    rig.link.write_line("G10 L2 P1 X0")
    assert wait_for(lambda: "error:20" in rig.lines)


def test_per_axis_homing_needs_both_axes_for_gcode(rig):
    rig.link.write_line("$HX")
    assert wait_for(lambda: rig.count("ok") >= 1)
    rig.link.write_line("G0 X1")
    assert wait_for(lambda: "ALARM:14" in rig.lines)   # mới Home trục X
    rig.link.write_line("$X")
    rig.link.write_line("$HY")
    assert wait_for(lambda: rig.count("ok") >= 3)
    rig.link.write_line("G0 X1")
    assert wait_for(lambda: rig.count("ok") >= 4)
    assert rig.count("ALARM:14") == 1
