"""app/idle.py: tự tắt server khi đóng hết trang (chỉ khi đặt EXTRUXY_IDLE_EXIT_MIN)."""
import threading
import time

from app import idle


class FakeMachine:
    def __init__(self, busy: bool) -> None:
        self.busy = busy
        self.disconnected = False

    def job_active(self) -> bool:
        return self.busy

    def disconnect(self) -> None:
        self.disconnected = True


def run_watch(monkeypatch, machine, minutes="0.0005", wait=0.4):
    exited = threading.Event()
    monkeypatch.setenv("EXTRUXY_IDLE_EXIT_MIN", minutes)
    monkeypatch.setattr(idle, "CHECK_EVERY_S", 0.02)
    monkeypatch.setattr(idle.os, "_exit", lambda code: exited.set())
    idle.touch()
    stop = idle.start(machine)
    exited.wait(wait)
    if stop:
        stop.set()                      # dừng luồng canh trước khi monkeypatch trả os._exit thật
        time.sleep(idle.CHECK_EVERY_S * 3)
    return exited.is_set()


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("EXTRUXY_IDLE_EXIT_MIN", raising=False)
    assert idle.limit_minutes() == 0
    monkeypatch.setenv("EXTRUXY_IDLE_EXIT_MIN", "abc")
    assert idle.limit_minutes() == 0


def test_exits_after_silence_and_disconnects(monkeypatch):
    m = FakeMachine(busy=False)
    assert run_watch(monkeypatch, m)
    assert m.disconnected


def test_never_exits_while_job_runs(monkeypatch):
    m = FakeMachine(busy=True)
    assert not run_watch(monkeypatch, m)


def test_zero_means_off(monkeypatch):
    assert not run_watch(monkeypatch, FakeMachine(busy=False), minutes="0", wait=0.15)
