"""Địa chỉ + QR để mở giao diện từ máy khác (docs/13)."""
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import share


def decode(rows: list[str]) -> str:
    n = len(rows)
    img = np.array([[0 if c == "1" else 255 for c in r] for r in rows], dtype=np.uint8)
    img = cv2.copyMakeBorder(cv2.resize(img, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST), 40, 40, 40, 40,
                             cv2.BORDER_CONSTANT, value=255)
    return cv2.QRCodeDetector().detectAndDecode(img)[0]


def test_qr_roundtrip_for_public_url():
    url = "https://plotter.example.com"
    rows = share.qr_rows(url)
    assert len(rows) == len(rows[0]) and set("".join(rows)) <= {"0", "1"}
    assert decode(rows) == url


def test_items_only_from_valid_env(monkeypatch):
    monkeypatch.setenv("EXTRUXY_PUBLIC_URL", "https://a.example")
    monkeypatch.setenv("EXTRUXY_LAN_URL", "javascript:alert(1)")           # không phải http(s): bỏ
    items = share.share_items()
    assert [i["kind"] for i in items] == ["public"] and items[0]["url"] == "https://a.example"
    monkeypatch.setenv("EXTRUXY_PUBLIC_URL", "https://" + "a" * 300)       # quá dài: bỏ
    assert share.share_items() == []


@pytest.fixture
def client():
    return TestClient(app)


def test_api_share_returns_items(client, monkeypatch):
    monkeypatch.setenv("EXTRUXY_LAN_URL", "http://192.168.1.5:8000")
    r = client.get("/api/share")
    assert r.status_code == 200 and r.json()["items"][0]["kind"] == "lan"


def test_guest_sees_only_public_address_admin_sees_both(monkeypatch):
    from app.auth import auth
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", "2468")
    monkeypatch.setenv("EXTRUXY_PUBLIC_URL", "https://plotter.example.com")
    monkeypatch.setenv("EXTRUXY_LAN_URL", "http://192.168.1.5:8000")
    auth.reset()
    try:
        guest = TestClient(app)
        assert [i["kind"] for i in guest.get("/api/share").json()["items"]] == ["public"]
        admin = TestClient(app)
        assert admin.post("/api/auth/login", json={"pin": "2468"}).status_code == 200
        assert [i["kind"] for i in admin.get("/api/share").json()["items"]] == ["public", "lan"]
    finally:
        auth.reset()
