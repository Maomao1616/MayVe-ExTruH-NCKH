"""SimLink phải khớp hành vi đã thấy trên board thật (MACHINE.md, 29/10/2026)."""
import math
import time

import pytest

from app.links.sim_link import SimLink
from app.links.protocol import parse_status
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

    def unlock(self):
        self.link.write_line("$X")
        self.wait_idle()

    def close(self):
        self.link.close()


@pytest.fixture
def rig():
    r = Rig()
    yield r
    r.close()


@pytest.fixture
def idle_rig():
    r = Rig()
    r.unlock()
    yield r
    r.close()


# --- bật máy, $X ----------------------------------------------------------------
def test_boot_banner_then_alarm_14(rig):
    # Thật: Grbl 4.1 [...] / [MSG:INFO: ALARM: Unhomed] / ALARM:14 / trạng thái Alarm
    assert rig.lines[0].startswith("Grbl ")
    assert rig.lines[1:3] == ["[MSG:INFO: ALARM: Unhomed]", "ALARM:14"]
    st = rig.status()
    assert st["state"] == "Alarm" and st["mpos"] == [0.0, 0.0, 0.0]


def test_gcode_in_boot_alarm_is_error_9(rig):
    rig.link.write_line("G0 Z3")
    assert wait_for(lambda: "error:9" in rig.lines)


def test_jog_in_alarm_state_is_locked(rig):
    rig.link.write_line("$J=G91 X1 F100")
    assert wait_for(lambda: "error:9" in rig.lines)


def test_unlock_then_gcode_runs_without_homing(rig):
    # Thật: sau $X mọi G-code chạy được kể cả khi chưa Home (A3).
    rig.link.write_line("$X")
    assert wait_for(lambda: "[MSG:INFO: Caution: Unlocked]" in rig.lines)
    rig.link.write_line("G0 X10 Z3")
    assert wait_for(lambda: rig.count("ok") >= 2)
    rig.wait_idle()
    assert rig.status()["mpos"] == [pytest.approx(10.0), 0.0, pytest.approx(3.0)]
    assert rig.count("ALARM:14") == 1                 # chỉ lần bật máy


def test_no_must_home_boots_idle():
    r = Rig(must_home=False)
    try:
        assert r.status()["state"] == "Idle" and "ALARM:14" not in r.lines
    finally:
        r.close()


# --- Home -----------------------------------------------------------------------
def test_homing_reports_homed_msg_then_ok(rig):
    rig.link.write_line("$H")
    assert wait_for(lambda: "[MSG:Homed:XY]" in rig.lines)
    i = rig.lines.index("[MSG:Homed:XY]")
    assert wait_for(lambda: "ok" in rig.lines[i + 1:])
    assert rig.lines[i + 1] == "ok"                  # thật: [MSG:Homed:XY] rồi ok
    rig.wait_idle()


def test_homing_then_move(rig):
    rig.link.write_line("$H")
    assert wait_for(lambda: rig.status()["state"] == "Idle" and rig.count("ok") >= 1)
    rig.link.write_line("G90")
    rig.link.write_line("G1 X50 Y40 F6000")
    assert wait_for(lambda: rig.count("ok") >= 3)
    rig.wait_idle()
    assert rig.status()["mpos"][:2] == [pytest.approx(50.0), pytest.approx(40.0)]


def test_per_axis_homing_reports_axis(rig):
    rig.link.write_line("$HX")
    assert wait_for(lambda: "[MSG:Homed:X]" in rig.lines)


# --- giới hạn -------------------------------------------------------------------
def test_jog_beyond_travel_is_error_15(idle_rig):
    idle_rig.link.write_line("$J=G90 X999 F1000")
    assert wait_for(lambda: "error:15" in idle_rig.lines)


def test_jog_without_feed_is_error_16(idle_rig):
    idle_rig.link.write_line("$J=G91 X1")
    assert wait_for(lambda: "error:16" in idle_rig.lines)


def test_soft_limit_sends_ok_before_alarm_2(idle_rig):
    # Thật: `g0 x1000` -> [MSG:INFO: Soft limit ...] / ok / [MSG:INFO: ALARM: Soft Limit] / ALARM:2
    idle_rig.link.write_line("G0 X1000")
    assert wait_for(lambda: "ALARM:2" in idle_rig.lines)
    assert idle_rig.lines.index("ok") < idle_rig.lines.index("ALARM:2")
    assert idle_rig.status()["state"] == "Alarm"


def test_default_travel_matches_config():
    # ConfigNCKH-16 ($130-$132): X 285, Y 318, Z 5.
    r = Rig(must_home=False)
    try:
        r.link.write_line("G1 Y318 F6000")
        assert wait_for(lambda: r.count("ok") == 1)
        assert r.count("ALARM:2") == 0
        r.link.write_line("G1 Y318.5 F6000")
        assert wait_for(lambda: r.count("ALARM:2") == 1)
    finally:
        r.link.close()


def test_hard_limit_needs_reset_before_unlock(idle_rig):
    # Thật: ALARM:1 / [MSG:ERR: Reset to continue]; $X -> ok nhưng vẫn Alarm;
    # Reset -> ALARM:14 (chưa Home); $X -> Idle.
    idle_rig.link.simulate_hard_limit()
    assert "[MSG:ERR: Reset to continue]" in idle_rig.lines
    idle_rig.link.write_line("$X")
    assert wait_for(lambda: idle_rig.count("ok") >= 2)
    assert idle_rig.status()["state"] == "Alarm"
    idle_rig.link.write_realtime(b"\x18")
    assert idle_rig.count("ALARM:14") == 2
    idle_rig.unlock()


# --- Hold, Jog, Reset -----------------------------------------------------------
def test_hold_and_resume_during_run():
    r = Rig(speed=2)  # chậm để kịp chen vào giữa chuyển động
    try:
        r.unlock()
        r.link.write_line("G1 X100 F6000")
        assert wait_for(lambda: r.status()["state"] == "Run")
        r.link.write_realtime(b"!")
        assert r.status()["substate"] == "1"            # thật: Hold:1 rồi Hold:0
        assert wait_for(lambda: r.status()["state"] == "Hold" and r.status()["substate"] == "0")
        x1 = r.status()["mpos"][0]
        time.sleep(0.2)
        assert r.status()["mpos"][0] == pytest.approx(x1)
        r.link.write_realtime(b"~")
        assert wait_for(lambda: r.status()["state"] in ("Run", "Idle"))
        r.wait_idle(timeout=6.0)
        assert r.status()["mpos"][0] == pytest.approx(100.0)
    finally:
        r.close()


def test_feed_hold_during_jog_cancels_jog():
    # Thật (A5): `!` khi Jog -> hủy jog ngay, về Idle tại chỗ, không resume được.
    r = Rig(speed=2)
    try:
        r.unlock()
        r.link.write_line("$J=G91 X100 F6000")
        assert wait_for(lambda: r.status()["state"] == "Jog")
        r.link.write_realtime(b"!")
        st = r.status()
        assert st["state"] == "Idle" and 0 < st["mpos"][0] < 100
        r.link.write_realtime(b"~")
        time.sleep(0.2)
        assert r.status()["mpos"][0] == pytest.approx(st["mpos"][0])
    finally:
        r.close()


def test_reset_during_run_gives_alarm_3_and_banner():
    r = Rig(speed=2)
    try:
        r.unlock()
        r.link.write_line("G1 X100 F6000")
        assert wait_for(lambda: r.status()["state"] == "Run")
        r.link.write_realtime(b"\x18")
        assert "ALARM:3" in r.lines
        assert r.lines[-1].startswith("Grbl ")
        assert r.status()["state"] == "Alarm"
    finally:
        r.close()


def test_reset_at_hold_complete_returns_idle_without_alarm():
    # Thật (Test 4a): Reset khi Hold:0 -> không lỗi.
    r = Rig(speed=2)
    try:
        r.unlock()
        r.link.write_line("G1 X100 F6000")
        assert wait_for(lambda: r.status()["state"] == "Run")
        r.link.write_realtime(b"!")
        assert wait_for(lambda: r.status()["substate"] == "0")
        r.link.write_realtime(b"\x18")
        assert "ALARM:3" not in r.lines
        assert r.status()["state"] == "Idle"
    finally:
        r.close()


def test_planner_fills_and_holds_back_ok():
    r = Rig(speed=1)
    try:
        r.unlock()
        for i in range(40):
            r.link.write_line(f"G1 X{(i % 2) * 100 + 5} F600")
        assert wait_for(lambda: r.status()["planner_free"] == 0)
        assert r.count("ok") < 41  # chưa thể ok hết khi planner đầy
    finally:
        r.close()


# --- tọa độ làm việc, lệnh $ ----------------------------------------------------
def test_zero_sets_work_offset_and_reports_wco(idle_rig):
    idle_rig.link.write_line("$J=G91 G21 X10 F6000")
    assert wait_for(lambda: idle_rig.count("ok") >= 2)
    idle_rig.wait_idle()
    idle_rig.link.write_line("G10 L20 P1 X0")
    assert wait_for(lambda: idle_rig.count("ok") >= 3)
    st = idle_rig.status()
    assert st["wco"] == [pytest.approx(10.0), 0.0, 0.0]
    assert st["mpos"][0] == pytest.approx(10.0)  # Zero không làm máy chuyển động


def test_absolute_jog_uses_work_coordinates(idle_rig):
    idle_rig.link.write_line("$J=G91 G21 X10 F6000")
    assert wait_for(lambda: idle_rig.count("ok") >= 2)
    idle_rig.wait_idle()
    idle_rig.link.write_line("G10 L20 P1 X0")
    idle_rig.link.write_line("$J=G90 G21 X5 F6000")
    assert wait_for(lambda: idle_rig.count("ok") >= 4)
    idle_rig.wait_idle()
    assert idle_rig.status()["mpos"][0] == pytest.approx(15.0)  # work X5 = máy X15


def test_other_g10_forms_are_unsupported(idle_rig):
    idle_rig.link.write_line("G10 L2 P1 X0")
    assert wait_for(lambda: "error:20" in idle_rig.lines)


def test_settings_dump_matches_board(rig):
    rig.link.write_line("$$")
    assert wait_for(lambda: rig.count("ok") >= 1)
    for setting in ("$130=285.000", "$131=318.000", "$132=5.000", "$112=3000.000"):
        assert setting in rig.lines


# --- cung tròn và ghi đè tốc độ (đợt 29/10/2026) --------------------------------
def _track(rig, condition, timeout=6.0):
    """Lấy mẫu vị trí trong lúc máy chạy, tới khi condition() đúng."""
    import time as _t
    points, end = [], _t.monotonic() + timeout
    while _t.monotonic() < end:
        st = rig.status()
        points.append(st["mpos"])
        if condition(st):
            return points
        _t.sleep(0.01)
    raise AssertionError("hết giờ")


def test_arc_follows_the_circle_not_the_chord():
    # Lỗi cũ: G2/G3 đi thẳng tới điểm cuối, khung 2D thấy đường chéo thay vì cung.
    r = Rig(speed=2)
    try:
        r.unlock()
        r.link.write_line("G90 G1 X50 Y50 F6000")
        assert wait_for(lambda: r.status()["mpos"][:2] == [50.0, 50.0], 6.0)   # Idle ngay lúc đầu nên chờ vị trí
        r.link.write_line("G3 X70 Y50 I10 J0 F3000")    # nửa vòng tròn tâm (60,50), R10, đi qua phía Y−
        pts = _track(r, lambda st: st["state"] == "Idle" and st["mpos"][0] > 69.9)
        mid = [p for p in pts if 55 < p[0] < 65]
        assert mid, pts
        for x, y, _ in pts:
            assert abs(math.hypot(x - 60, y - 50) - 10) < 0.2      # luôn nằm trên đường tròn
        assert min(p[1] for p in mid) < 42                         # thật sự cong ra xa dây cung
    finally:
        r.close()


def test_arc_with_radius_word_and_bad_radius():
    r = Rig()
    try:
        r.unlock()
        r.link.write_line("G90 G1 X10 Y10 F6000")
        r.link.write_line("G2 X30 Y10 R10")                      # nửa vòng, tâm (20,10)
        assert wait_for(lambda: r.status()["mpos"][:2] == [30.0, 10.0], 3.0), r.status()
        r.link.write_line("G2 X80 Y10 R5")                       # R quá nhỏ: không với tới
        assert wait_for(lambda: "error:33" in r.lines)
    finally:
        r.close()


def test_feed_override_scales_file_feed_and_is_reported():
    r = Rig()
    try:
        r.unlock()
        for byte in (b"\x92", b"\x92", b"\x94"):                 # -10, -10, -1 => 79 %
            r.link.write_realtime(byte)
        assert r.status()["overrides"] == [79, 100, 100]
        for _ in range(20):
            r.link.write_realtime(b"\x91")                       # +10 x20: chặn ở 200 %
        assert r.status()["overrides"][0] == 200
        r.link.write_realtime(b"\x18")                           # Reset: về 100 %
        r.link.write_realtime(b"\x90")
        assert r.status()["overrides"][0] == 100
    finally:
        r.close()
