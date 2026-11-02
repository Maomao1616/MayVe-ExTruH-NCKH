"""Phân quyền khách / quản lý bằng PIN (app/auth.py, docs/PLAN_ONLINE.md mục 2)."""
import time

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.auth import COOKIE, GUEST_ROUTES, LOCK_S, MAX_FAILS, auth
from app.main import app
from app.services.machine import machine

PIN = "2468"


@pytest.fixture(autouse=True)
def clean_auth():
    auth.reset()
    yield
    auth.reset()


@pytest.fixture
def pin_set(monkeypatch):
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", PIN)


@pytest.fixture
def guest():
    return TestClient(app)


@pytest.fixture
def admin(pin_set):
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"pin": PIN}).status_code == 200
    return client


def code(response):
    return response.json()["error"]["code"]


def test_without_pin_everyone_is_admin_like_before(guest, monkeypatch):
    monkeypatch.delenv("EXTRUXY_ADMIN_PIN", raising=False)
    assert guest.get("/api/auth/me").json() == {"role": "admin", "pin_set": False}
    assert guest.get("/api/profile").status_code == 200
    assert code(guest.post("/api/auth/login", json={"pin": "x"})) == "pin_not_set"


def test_blank_pin_counts_as_not_set(guest, monkeypatch):
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", "   ")
    assert guest.get("/api/auth/me").json()["pin_set"] is False


def test_guest_is_blocked_everywhere_except_the_whitelist(guest, pin_set):
    """Quét MỌI route của app: thêm route mới mà quên chặn thì test này đỏ."""
    checked = 0
    for path, methods in app.openapi()["paths"].items():
        for method in methods:
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            if (method.upper(), path) in GUEST_ROUTES:
                continue
            url = path.replace("{", "").replace("}", "")      # {token} -> token: chỉ cần khớp dạng đường dẫn
            response = guest.request(method.upper(), url)
            assert response.status_code == 401 and code(response) == "auth_required", f"{method.upper()} {path}"
            checked += 1
    assert checked >= 40        # có thật nhiều route được kiểm, không phải vòng lặp rỗng


def test_unknown_api_path_and_trailing_slash_are_denied_for_guest(guest, pin_set):
    assert guest.get("/api/does-not-exist").status_code == 401
    assert guest.get("/api/status/", follow_redirects=False).status_code == 401
    assert guest.get("/api/draw/schema/x").status_code == 401


def test_guest_can_use_whitelisted_routes(guest, pin_set):
    for path in ("/api/health", "/api/status", "/api/connection", "/api/draw/schema"):
        assert guest.get(path).status_code == 200, path
    assert guest.get("/api/auth/me").json() == {"role": "guest", "pin_set": True}


def test_static_frontend_stays_public(guest, pin_set):
    assert guest.get("/").status_code == 200


def test_guest_cannot_touch_the_machine(guest, pin_set):
    calls = []
    original = machine.send_line
    machine.send_line = lambda line: calls.append(line)
    try:
        for method, path, body in [("POST", "/api/command", {"line": "$H"}),
                                   ("POST", "/api/motion", {"on": True, "pin": PIN}),
                                   ("POST", "/api/jobs", {"name": "x", "lines": ["G0 X1"]}),
                                   ("POST", "/api/realtime", {"action": "reset"}),
                                   ("GET", "/api/log", None)]:
            response = guest.request(method, path, json=body)
            assert response.status_code == 401, path
        assert calls == []
    finally:
        machine.send_line = original


def test_wrong_pin_is_rejected_and_sets_no_cookie(guest, pin_set):
    response = guest.post("/api/auth/login", json={"pin": "0000"})
    assert response.status_code == 401 and code(response) == "bad_pin"
    assert COOKIE not in response.cookies
    assert guest.get("/api/profile").status_code == 401


def test_right_pin_gives_admin_cookie_with_safe_flags(guest, pin_set):
    response = guest.post("/api/auth/login", json={"pin": PIN})
    assert response.status_code == 200 and response.json() == {"role": "admin", "pin_set": True}
    header = response.headers["set-cookie"].lower()
    assert "httponly" in header and "samesite=strict" in header and "secure" not in header   # http thường
    assert guest.get("/api/auth/me").json()["role"] == "admin"
    assert guest.get("/api/profile").status_code == 200
    assert guest.get("/api/log").status_code == 200


def test_cookie_is_secure_behind_https_proxy(guest, pin_set):
    response = guest.post("/api/auth/login", json={"pin": PIN}, headers={"x-forwarded-proto": "https"})
    assert "secure" in response.headers["set-cookie"].lower()


def test_login_in_one_browser_does_not_open_another(admin, pin_set):
    other = TestClient(app)
    assert other.get("/api/auth/me").json()["role"] == "guest"
    assert other.get("/api/profile").status_code == 401
    assert admin.get("/api/profile").status_code == 200


def test_forged_cookie_is_rejected(guest, pin_set):
    guest.cookies.set(COOKIE, "not-a-real-token")
    assert guest.get("/api/profile").status_code == 401
    assert guest.get("/api/auth/me").json()["role"] == "guest"


def test_session_expires(admin):
    token = admin.cookies.get(COOKIE)
    auth._sessions[token] = time.time() - 1
    assert admin.get("/api/profile").status_code == 401
    assert admin.get("/api/auth/me").json()["role"] == "guest"


def test_lockout_after_repeated_wrong_pins_even_for_the_right_one(guest, pin_set, monkeypatch):
    for _ in range(MAX_FAILS):
        assert code(guest.post("/api/auth/login", json={"pin": "bad"})) == "bad_pin"
    response = guest.post("/api/auth/login", json={"pin": PIN})
    assert response.status_code == 429 and code(response) == "login_locked"
    # hết thời gian khóa thì đăng nhập lại được
    monkeypatch.setattr(auth_module.time, "time", lambda real=time.time: real() + LOCK_S + 1)
    assert guest.post("/api/auth/login", json={"pin": PIN}).status_code == 200


def test_success_resets_the_failure_counter(guest, pin_set):
    for _ in range(MAX_FAILS - 1):
        guest.post("/api/auth/login", json={"pin": "bad"})
    assert guest.post("/api/auth/login", json={"pin": PIN}).status_code == 200
    for _ in range(MAX_FAILS - 1):
        assert code(guest.post("/api/auth/login", json={"pin": "bad"})) == "bad_pin"


def test_logout_ends_session_and_relocks_motion(admin, monkeypatch):
    locked = []
    monkeypatch.setattr(machine, "set_motion", lambda on, pin=None: locked.append(on) or {})
    assert admin.post("/api/auth/logout").json()["role"] == "guest"
    assert locked == [False]
    assert admin.get("/api/profile").status_code == 401


def test_guest_logout_does_not_relock_motion(guest, pin_set, monkeypatch):
    locked = []
    monkeypatch.setattr(machine, "set_motion", lambda on, pin=None: locked.append(on) or {})
    guest.post("/api/auth/logout")
    assert locked == []

