"""Đường Wi-Fi (telnet): mạch giả là máy chủ TCP trên máy này, bọc SimLink. Không chạm máy thật."""
import socket
import threading

import pytest

from app.links import telnet_link
from app.links.sim_link import SimLink
from app.services.machine import MachineService, ServiceError
from tests.helpers import wait_for

SQUARE = ["G21 G90", "G0 X10 Y10", "G1 F6000", "G1 X20", "G1 Y20", "G1 X10", "G1 Y10", "G0 X0 Y0"]
REALTIME_BYTES = {0x3F, 0x21, 0x7E, 0x18}          # ? ! ~ Ctrl-X; byte >= 0x80 cũng là lệnh tức thời


class FakeBoard:
    """Giống telnet của FluidNC: TCP thô, dòng kết thúc bằng \\n, ký tự tức thời xử lý ngay."""

    def __init__(self, sim_speed=100.0):
        self.server = socket.create_server(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        self.sim_speed = sim_speed
        self.client = None
        self.sim = None
        self.mute = False                            # True: mạch "im lặng" (sóng mất mà TCP chưa báo đứt)
        self.lines = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _send(self, line):
        if self.mute or self.client is None:
            return
        try:
            self.client.sendall((line + "\r\n").encode())
        except OSError:
            pass

    def _serve(self):
        try:
            self.client, _ = self.server.accept()
        except OSError:
            return
        self.sim = SimLink(speed=self.sim_speed)
        self.sim.add_listener(self._send)
        self.sim.open()
        buf = bytearray()
        while True:
            try:
                data = self.client.recv(4096)
            except OSError:
                return
            if not data:
                return
            for b in data:
                if b in REALTIME_BYTES or b >= 0x80:
                    self.sim.write_realtime(bytes([b]))
                elif b == 0x0A:
                    line = buf.decode().strip()
                    buf.clear()
                    if line:
                        self.lines.append(line)
                        self.sim.write_line(line)
                elif b != 0x0D:
                    buf.append(b)

    def drop(self):
        """Mất sóng kiểu TCP đóng hẳn."""
        if self.client is not None:
            self.client.close()

    def close(self):
        self.drop()
        self.server.close()
        if self.sim is not None:
            self.sim.close()


@pytest.fixture
def board():
    b = FakeBoard()
    yield b
    b.close()


def make_svc(allow_motion):
    return MachineService(allow_motion=allow_motion)


@pytest.fixture
def svc():
    s = make_svc(False)
    yield s
    s.disconnect()


@pytest.fixture
def live():
    s = make_svc(True)
    yield s
    s.disconnect()


def homed_over_wifi(svc, board):
    svc.connect("wifi", host="127.0.0.1", tcp_port=board.port)
    svc.send_line("$H")
    assert wait_for(lambda: svc.snapshot()["homed_guess"], timeout=5)
    assert wait_for(lambda: not svc._relifting, timeout=5)
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Idle", timeout=5)


def test_connect_over_wifi_gets_status(svc, board):
    info = svc.connect("wifi", host="127.0.0.1", tcp_port=board.port)
    assert info["connected"] and info["mode"] == "wifi"
    assert info["host"] == "127.0.0.1" and info["tcp_port"] == board.port and info["port"] is None
    assert wait_for(lambda: svc.snapshot()["machine"] is not None)
    assert svc.snapshot()["machine"]["state"] == "Alarm"        # mạch giả bật lên là Alarm như máy thật


def test_wifi_is_a_real_machine_so_motion_stays_locked(svc, board):
    """An toàn: Wi-Fi là máy thật, khóa chuyển động phải áp y như USB."""
    info = svc.connect("wifi", host="127.0.0.1", tcp_port=board.port)
    assert info["motion_unlocked"] is False
    svc.send_line("$X")                                           # mở Alarm: không chuyển động, được phép
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Idle")
    with pytest.raises(ServiceError) as e:
        svc.send_line("G0 X10")
    assert e.value.code == "motion_locked"
    with pytest.raises(ServiceError) as e:
        svc.start_job("vuong", SQUARE)
    assert e.value.code == "motion_locked"
    assert "G0 X10" not in board.lines


def test_job_runs_to_the_end_over_wifi(live, board):
    homed_over_wifi(live, board)
    live.start_job("vuong", SQUARE)
    assert wait_for(lambda: live.snapshot()["job"]["state"] == "done", timeout=10)
    assert [l for l in board.lines if l in SQUARE] == SQUARE


def test_connection_drop_mid_job_stops_job_and_locks(live, board):
    homed_over_wifi(live, board)
    board.sim._speed = 0.5                                        # chậm lại để tác vụ còn dở khi mất sóng
    live.start_job("dang-do", SQUARE * 5)
    assert wait_for(lambda: live.snapshot()["job"]["state"] == "running")
    board.drop()
    assert wait_for(lambda: not live.snapshot()["connection"]["connected"], timeout=5)
    snap = live.snapshot()
    assert snap["job"]["state"] != "done"
    assert "Wi-Fi" in (snap["connection"]["lost_reason"] or "")
    assert live.resume_info()["available"]                       # chạy tiếp được từ chỗ dừng


def test_silence_counts_as_signal_lost(svc, board, monkeypatch):
    monkeypatch.setattr(telnet_link, "LINK_SILENT_S", 0.6)
    svc.connect("wifi", host="127.0.0.1", tcp_port=board.port)
    assert wait_for(lambda: svc.snapshot()["machine"] is not None)
    board.mute = True                                             # TCP còn mở nhưng không còn dữ liệu về
    assert wait_for(lambda: not svc.snapshot()["connection"]["connected"], timeout=5)
    assert "no data" in svc.snapshot()["connection"]["lost_reason"]


def test_unreachable_host_is_a_clean_error(svc):
    s = socket.create_server(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                                                     # cổng đã đóng: nối sẽ bị từ chối ngay
    with pytest.raises(ServiceError) as e:
        svc.connect("wifi", host="127.0.0.1", tcp_port=port)
    assert e.value.code == "link_error"
    assert svc.connection_info()["connected"] is False


def test_wifi_needs_host(svc):
    with pytest.raises(ServiceError) as e:
        svc.connect("wifi")
    assert e.value.code == "bad_request"


# --- lớp TelnetLink đứng riêng (DeepSeek quét 26/11 thấy thiếu) -------------------------
def raw_link(board):
    link = telnet_link.TelnetLink("127.0.0.1", board.port)
    lines = []
    link.add_listener(lines.append)
    link.open()
    assert wait_for(lambda: board.client is not None)
    return link, lines


def test_write_after_close_raises_and_close_twice_is_safe(board):
    link, _ = raw_link(board)
    link.close()
    link.close()                                                  # gọi lần hai không lỗi
    assert not link.is_open
    with pytest.raises(telnet_link.LinkError):
        link.write_line("$I")


def test_telnet_control_sequences_are_dropped(board):
    link, lines = raw_link(board)
    # IAC WILL ECHO + IAC DO SGA + IAC NOP + IAC IAC + đoạn thương lượng IAC SB ... IAC SE, chen giữa chữ
    board.client.sendall(b"\xff\xfb\x01ok\xff\xfd\x03-co\xff\xf1-iac\xff\xff\xff\xfa\x18\x00abc\xff\xf0\r\n")
    assert wait_for(lambda: "ok-co-iac" in lines)
    junk = ("abc", "\x01", "\x03", "\x18", "�")              # byte tùy chọn / thương lượng không được lọt vào dòng
    assert not any(j in line for line in lines for j in junk)
    link.close()


@pytest.mark.parametrize("cut", range(1, 12))
def test_telnet_filter_keeps_state_across_reads(cut):
    data = b"A\xff\xfb\x01B\xff\xfa\x18xy\xff\xf0C\xff\xff"
    f = telnet_link.TelnetFilter()
    assert f.feed(data[:cut]) + f.feed(data[cut:]) == b"ABC"     # chuỗi bị cắt đôi ở mọi chỗ vẫn lọc đúng


class _FailingSendSocket:
    """Bọc socket thật; sendall báo hết giờ như mạng treo (luồng đọc vẫn dùng socket thật)."""

    def __init__(self, real):
        self._real = real

    def sendall(self, data):
        raise TimeoutError("timed out")

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_write_timeout_reports_lost_at_once_and_only_once(board):
    link, _ = raw_link(board)
    reasons = []
    link.add_close_listener(reasons.append)
    link._sock = _FailingSendSocket(link._sock)
    with pytest.raises(telnet_link.LinkError):
        link.write_line("G1 X1")
    assert len(reasons) == 1 and "write failed" in reasons[0]      # báo ngay, không chờ 3 s im lặng
    assert not link.is_open
    with pytest.raises(telnet_link.LinkError):                     # ghi tiếp: lỗi gọn, không báo mất lần hai
        link.write_line("G1 X2")
    assert len(reasons) == 1


def test_write_failure_mid_job_disconnects_at_once(live, board):
    homed_over_wifi(live, board)
    board.sim._speed = 0.5
    live.start_job("ghi-loi", SQUARE * 5)
    assert wait_for(lambda: live.snapshot()["job"]["state"] == "running")
    live._link._sock = _FailingSendSocket(live._link._sock)       # mạng treo: lần ghi tiếp theo hết giờ
    assert wait_for(lambda: not live.snapshot()["connection"]["connected"], timeout=2)   # < 3 s im lặng
    snap = live.snapshot()
    assert snap["job"]["state"] != "done"
    assert "write failed" in (snap["connection"]["lost_reason"] or "")
    assert live.resume_info()["available"]


def test_long_line_split_across_reads(board):
    link, lines = raw_link(board)
    long = "[MSG:" + "x" * 10000 + "]"                            # dài hơn một lần đọc 4096 byte
    board.client.sendall(long.encode() + b"\r\n")
    assert wait_for(lambda: long in lines)
    link.close()
