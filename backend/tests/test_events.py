"""Luồng SSE /api/events: trạng thái cho mọi người, nhật ký chỉ cho quản lý, nhịp tim, đóng khi ngắt / hết phiên, giới hạn kết nối."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.api import events
from app.auth import auth
from app.main import app
from app.services.machine import MachineService
from tests.helpers import wait_for

PIN = "abcd1234"


def parse(frame: str) -> tuple[str, dict]:
    lines = frame.strip().splitlines()
    return lines[0].split(": ", 1)[1], json.loads(lines[1].split(": ", 1)[1])


async def take(stream, n, timeout=5.0):
    out = []
    async with asyncio.timeout(timeout):
        async for item in stream:
            out.append(item)
            if len(out) >= n:
                break
    return out


@pytest.fixture
def machine_sim(monkeypatch):
    svc = MachineService(allow_motion=False)
    monkeypatch.setattr(events, "machine", svc)
    svc.connect("sim", sim_speed=100)
    assert wait_for(lambda: svc.snapshot()["machine"] is not None)
    yield svc
    svc.disconnect()


@pytest.fixture(autouse=True)
def clean_auth():
    auth.reset()
    yield
    auth.reset()


def never_disconnected():
    async def f():
        return False
    return f


def test_admin_stream_sends_retry_status_and_log(machine_sim):
    async def run():
        stream = events.event_stream(None, 0, never_disconnected(), poll_s=0.02)        # chưa đặt PIN: ai cũng là quản lý
        frames = await take(stream, 3)
        await stream.aclose()
        return frames
    frames = asyncio.run(run())
    assert frames[0].startswith("retry:")
    kinds = [parse(f)[0] for f in frames[1:]]
    assert "status" in kinds and "log" in kinds
    status = next(parse(f)[1] for f in frames[1:] if parse(f)[0] == "status")
    assert status["connection"]["connected"] is True and status["machine"] is not None
    log = next(parse(f)[1] for f in frames[1:] if parse(f)[0] == "log")
    assert log["last_seq"] >= 1 and any("Connected" in e["text"] for e in log["entries"])


def test_guest_gets_status_but_never_the_log(machine_sim, monkeypatch):
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", PIN)

    async def run():
        stream = events.event_stream(None, 0, never_disconnected(), poll_s=0.02, heartbeat_s=0.05)
        frames = await take(stream, 6)
        await stream.aclose()
        return frames
    kinds = [parse(f)[0] for f in asyncio.run(run())[1:]]
    assert kinds and set(kinds) == {"status"}


def test_log_continues_from_since_without_repeating(machine_sim):
    machine_sim.log_system("dong-moi-1")
    last = machine_sim.log_since(0)["last_seq"]

    async def run():
        stream = events.event_stream(None, last, never_disconnected(), poll_s=0.02)
        first = await take(stream, 2)                                  # retry + status: chưa có dòng nhật ký mới
        machine_sim.log_system("dong-moi-2")
        more = await take(stream, 2)
        await stream.aclose()
        return first, more
    first, more = asyncio.run(run())
    assert all(parse(f)[0] != "log" for f in first[1:])
    logs = [parse(f)[1] for f in more if f.startswith("event: log")]
    assert logs and [e["text"] for e in logs[0]["entries"]] == ["dong-moi-2"]


def test_heartbeat_resends_status_when_nothing_changed(machine_sim):
    async def run():
        stream = events.event_stream(None, 0, never_disconnected(), poll_s=0.02, heartbeat_s=0.1)
        frames = await take(stream, 8, timeout=4)
        await stream.aclose()
        return frames
    statuses = [f for f in asyncio.run(run()) if f.startswith("event: status")]
    assert len(statuses) >= 3                                          # đều đặn dù máy đứng yên


def test_stream_ends_when_client_disconnects_and_releases_the_slot(machine_sim):
    before = events._streams
    calls = {"n": 0}

    async def disconnected():
        calls["n"] += 1
        return calls["n"] > 3

    async def run():
        return [f async for f in events.event_stream(None, 0, disconnected, poll_s=0.01)]
    frames = asyncio.run(run())
    assert frames and events._streams == before
    assert not machine_sim._change_listeners                          # gỡ hàm đánh thức khi luồng đóng


def test_new_log_line_is_pushed_at_once_not_on_the_next_poll(machine_sim):
    # nhịp dự phòng 5 s, nhịp tim 10 s: dòng mới tới được trong < 0,5 s nghĩa là máy đã đánh thức luồng ngay
    async def run():
        stream = events.event_stream(None, machine_sim.log_since(0)["last_seq"], never_disconnected(),
                                     poll_s=5.0, heartbeat_s=10.0)
        await take(stream, 2)                                          # retry + trạng thái đầu
        machine_sim.log_system("day-ngay")
        t0 = asyncio.get_running_loop().time()
        async with asyncio.timeout(0.5):
            async for f in stream:
                if f.startswith("event: log") and "day-ngay" in f:
                    break
        waited = asyncio.get_running_loop().time() - t0
        await stream.aclose()
        return waited
    assert asyncio.run(run()) < 0.5


def test_change_listener_errors_do_not_break_the_machine(machine_sim):
    def bad():
        raise RuntimeError("Event loop is closed")
    machine_sim.add_change_listener(bad)
    try:
        machine_sim.log_system("van-ghi-duoc")
        assert any(e["text"] == "van-ghi-duoc" for e in machine_sim.log_since(0)["entries"])
    finally:
        machine_sim.remove_change_listener(bad)


def test_stream_closes_when_the_admin_session_expires(machine_sim, monkeypatch):
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", PIN)
    token = auth.login(PIN)
    monkeypatch.setattr(events, "AUTH_RECHECK_S", 0.0)

    async def run():
        stream = events.event_stream(token, 0, never_disconnected(), poll_s=0.02)
        await take(stream, 3)
        auth.logout(token)                                             # phiên bị hủy giữa chừng
        rest = []
        async with asyncio.timeout(3):
            async for f in stream:
                rest.append(f)
        return rest                                                    # vòng lặp tự kết thúc: không treo mãi
    asyncio.run(run())
    assert events._streams == 0


def test_too_many_streams_is_refused(monkeypatch):
    monkeypatch.setattr(events, "_streams", events.MAX_STREAMS)
    r = TestClient(app).get("/api/events")
    assert r.status_code == 503 and r.json()["error"]["code"] == "too_many_streams"


def test_events_route_exists_and_is_allowed_for_guests(monkeypatch):      # (không kiểm header luồng: bài đó cần mở luồng thật)
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", PIN)
    paths = {(m.upper(), p) for p, ms in app.openapi()["paths"].items() for m in ms}
    assert ("GET", "/api/events") in paths
    from app.auth import GUEST_ROUTES
    assert ("GET", "/api/events") in GUEST_ROUTES
