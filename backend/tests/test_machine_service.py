import time

import pytest

from app.links.base import BaseLink
from app.services.machine import MachineService, ServiceError
from tests.helpers import wait_for


@pytest.fixture
def svc():
    s = MachineService(allow_motion=False)
    yield s
    s.disconnect()


def test_connect_sim_and_status(svc):
    info = svc.connect("sim", sim_speed=100)
    assert info["connected"] and info["mode"] == "sim"
    assert wait_for(lambda: svc.snapshot()["machine"] is not None)
    assert svc.snapshot()["machine"]["state"] == "Idle"


def test_double_connect_is_rejected(svc):
    svc.connect("sim")
    with pytest.raises(ServiceError) as e:
        svc.connect("sim")
    assert e.value.code == "already_connected"


def test_commands_need_connection(svc):
    with pytest.raises(ServiceError) as e:
        svc.send_line("$I")
    assert e.value.code == "not_connected"


def test_wpos_is_computed_from_wco(svc):
    svc.connect("sim", sim_speed=100)
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("wpos") is not None)
    assert svc.snapshot()["machine"]["wpos"] == [0.0, 0.0, 0.0]


def test_homed_guess_after_homing(svc):
    svc.connect("sim", sim_speed=100)
    assert svc.snapshot()["homed_guess"] is False
    svc.send_line("$H")
    assert wait_for(lambda: svc.snapshot()["homed_guess"])


def test_alarm_is_recorded(svc):
    svc.connect("sim", sim_speed=100)
    svc.send_line("G0 X10")
    assert wait_for(lambda: svc.snapshot()["last_alarm"] is not None)
    assert svc.snapshot()["last_alarm"]["name"] == "Unhomed"


def test_log_has_tx_and_rx(svc):
    svc.connect("sim", sim_speed=100)
    svc.send_line("$I")
    assert wait_for(lambda: any(e["text"] == "ok" for e in svc.log_since(0)["entries"]))
    texts = [(e["dir"], e["text"]) for e in svc.log_since(0)["entries"]]
    assert ("tx", "$I") in texts


def test_bad_lines_rejected(svc):
    svc.connect("sim")
    for bad in ("", "  ", "G0 X1\nG0 X2"):
        with pytest.raises(ServiceError):
            svc.send_line(bad)


class FakeSerial(BaseLink):
    kind = "serial"
    def __init__(self): super().__init__(); self.sent = []; self._o = True
    is_open = property(lambda self: self._o)
    def open(self): pass
    def close(self): self._o = False
    def write_line(self, text): self.sent.append(text)
    def write_realtime(self, data): self.sent.append(data)


def test_real_machine_is_read_only_by_default(svc):
    fake = FakeSerial()
    svc._link, svc._info = fake, {"mode": "serial", "port": "COM9", "baud": 115200}
    svc.send_line("$I")
    with pytest.raises(ServiceError) as e:
        svc.send_line("$H")
    assert e.value.code == "motion_locked" and e.value.status == 403
    svc.send_realtime("hold")  # lệnh dừng luôn được phép
    assert fake.sent == ["$I", b"!"]
    svc._link = None


def test_reset_clears_pending_home_guess(svc):
    svc.connect("sim")  # tốc độ thật: $H mất 1,5 giây, kịp reset giữa chừng
    svc.send_line("$H")
    svc.send_realtime("reset")
    svc.send_line("$I")
    assert wait_for(lambda: sum(1 for e in svc.log_since(0)["entries"] if e["text"] == "ok") >= 1)
    assert svc.snapshot()["homed_guess"] is False


def test_per_axis_homing_needs_both_axes(svc):
    svc.connect("sim", sim_speed=100)
    svc.send_line("$HX")
    assert wait_for(lambda: any(e["text"] == "ok" for e in svc.log_since(0)["entries"]))
    time.sleep(0.6)  # đủ vài báo cáo trạng thái để chắc chắn không bật nhầm
    assert svc.snapshot()["homed_guess"] is False
    svc.send_line("$HY")
    assert wait_for(lambda: svc.snapshot()["homed_guess"])


def test_alarm_14_keeps_axes_already_homed(svc):
    svc.connect("sim", sim_speed=100)
    svc.send_line("$HX")
    assert wait_for(lambda: any(e["text"] == "ok" for e in svc.log_since(0)["entries"]))
    svc.send_line("G0 X1")                       # mới Home X: sim báo ALARM:14
    assert wait_for(lambda: svc.snapshot()["last_alarm"] is not None)
    svc.send_line("$X")
    svc.send_line("$HY")
    assert wait_for(lambda: svc.snapshot()["homed_guess"])
