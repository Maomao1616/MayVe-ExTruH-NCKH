"""Ảnh khách gửi (services/customer.py, api/customer.py): lưu ảnh đã giải mã lại, thông số sạch, giới hạn, tự xóa, phân quyền."""
import io
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import paths
from app.main import app
from app.services import customer
from app.services.drawing import drafts

PIN = "abcd1234"


@pytest.fixture(autouse=True)
def fresh():
    customer.reset_rate_limit()
    yield
    customer.reset_rate_limit()


@pytest.fixture
def guest(monkeypatch):
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", PIN)
    return TestClient(app)


@pytest.fixture
def admin(guest):
    assert guest.post("/api/auth/login", json={"pin": PIN}).status_code == 200
    return guest


def png(w=300, h=200, mode="RGB", color=(200, 30, 30)):
    out = io.BytesIO()
    Image.new(mode, (w, h), color).save(out, "PNG")
    return out.getvalue()


def send(client, data=None, meta=None, filename="anh.png", headers=None):
    return client.post("/api/customer", files={"file": (filename, data if data is not None else png(), "image/png")},
                       data={"meta": json.dumps(meta if meta is not None else {"name": "An", "note": "tranh nhỏ"})},
                       headers=headers or {})


def test_guest_can_send_and_gets_only_id_and_expiry(guest):
    r = send(guest, meta={"name": "  Lan   Anh ", "note": "xin cảm ơn", "params": {"draw-preset": "portrait", "drawing-margin": "10",
                                                                                      "crop": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}}})
    assert r.status_code == 201
    item = r.json()["item"]
    assert set(item) == {"id", "expires"}                               # khách không thấy danh sách / thông số của người khác
    folder = paths.DATA_DIR / "customer" / item["id"]
    assert (folder / "image.jpg").read_bytes()[:2] == b"\xff\xd8"       # luôn là JPEG ghi lại, không phải tệp gốc
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    assert meta["name"] == "Lan Anh" and meta["note"] == "xin cảm ơn" and meta["params"]["crop"]["w"] == 0.5


def test_image_is_reencoded_downscaled_and_transparent_png_gets_white_background(guest):
    big = send(guest, png(4000, 3000), headers={"cf-connecting-ip": "big"})        # ảnh lớn nhưng nén nhỏ: vẫn nhận, thu về <= 1600
    assert big.status_code == 201
    assert max(Image.open(paths.DATA_DIR / "customer" / big.json()["item"]["id"] / "image.jpg").size) <= customer.LIMITS["max_side"]
    out = io.BytesIO()
    Image.new("RGBA", (2400, 1200), (0, 0, 0, 0)).save(out, "PNG")        # trong suốt hoàn toàn
    r = send(guest, out.getvalue())
    assert r.status_code == 201
    folder = paths.DATA_DIR / "customer" / r.json()["item"]["id"]
    im = Image.open(folder / "image.jpg")
    assert max(im.size) <= customer.LIMITS["max_side"] and im.getpixel((10, 10))[0] > 240       # trắng, không đen


def test_rejects_bad_files_and_bad_params(guest):
    assert send(guest, b"not an image at all").json()["error"]["code"] == "bad_image"
    assert send(guest, b"").status_code in (400, 422)
    text = send(guest, b"<?xml version='1.0'?><svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", filename="a.svg")
    assert text.status_code == 400
    too_big = send(guest, b"\x89PNG" + b"0" * (customer.LIMITS["image_bytes"] + 10))
    assert too_big.status_code == 413 and too_big.json()["error"]["code"] == "file_too_large"
    for bad in ({"params": {"../x": "1"}}, {"params": {"a": {"b": 1}}}, {"params": {"a": [1]}}, {"params": ["x"]},
                {"params": {"k": "x" * 41}}, {"params": {f"k{i}": "y" * 40 for i in range(300)}}):
        assert send(guest, meta=bad).status_code == 400, bad
    assert guest.post("/api/customer", files={"file": ("a.png", png(), "image/png")}, data={"meta": "{không phải json"}).status_code == 400
    assert not list((paths.DATA_DIR / "customer").glob(".tmp-*"))                  # lỗi giữa chừng không để lại thư mục dở


def test_rate_limit_per_source_per_hour(guest):
    for _ in range(customer.LIMITS["per_hour"]):
        assert send(guest, headers={"cf-connecting-ip": "1.2.3.4"}).status_code == 201
    blocked = send(guest, headers={"cf-connecting-ip": "1.2.3.4"})
    assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "too_many_sends"
    assert send(guest, headers={"cf-connecting-ip": "5.6.7.8"}).status_code == 201     # nguồn khác không bị ảnh hưởng


def test_inbox_full_stops_new_sends(guest, monkeypatch):
    monkeypatch.setitem(customer.LIMITS, "max_items", 2)
    assert send(guest, headers={"cf-connecting-ip": "a"}).status_code == 201
    assert send(guest, headers={"cf-connecting-ip": "b"}).status_code == 201
    full = send(guest, headers={"cf-connecting-ip": "c"})
    assert full.status_code == 507 and full.json()["error"]["code"] == "inbox_full"


def test_old_items_are_purged_after_the_configured_days(guest, admin):
    first = send(guest).json()["item"]["id"]
    folder = paths.DATA_DIR / "customer" / first
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    meta["created_ts"] = time.time() - 6 * 86400                                  # 6 ngày trước, hạn mặc định 5 ngày
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    fresh_one = send(guest, headers={"cf-connecting-ip": "z"}).json()["item"]["id"]
    ids = [i["id"] for i in admin.get("/api/customer").json()["items"]]
    assert ids == [fresh_one] and not folder.exists()
    drafts.save_settings({"max_count": 50, "max_mb": 500, "customer_days": 1})
    assert admin.get("/api/draw/settings").json()["settings"]["customer_days"] == 1
    assert customer.purge(now=time.time() + 2 * 86400) == 1                       # giữ 1 ngày: sau 2 ngày mục mới cũng hết hạn


def test_customer_days_setting_is_validated_and_old_settings_files_still_load(admin):
    paths.data_file("draw_settings.json").parent.mkdir(parents=True, exist_ok=True)
    paths.data_file("draw_settings.json").write_text('{"max_count": 50, "max_mb": 10000}', encoding="utf-8")   # tệp cũ chưa có khóa mới
    assert admin.get("/api/draw/settings").json()["settings"]["customer_days"] == 5
    assert admin.put("/api/draw/settings", json={"max_count": 50, "max_mb": 500, "customer_days": 0}).status_code == 400
    assert admin.put("/api/draw/settings", json={"max_count": 50, "max_mb": 500, "customer_days": 31}).status_code == 400
    assert admin.put("/api/draw/settings", json={"max_count": 50, "max_mb": 500, "customer_days": 3}).json()["settings"]["customer_days"] == 3


def test_only_admin_can_list_view_mark_and_delete(guest, admin):
    item = send(guest).json()["item"]["id"]
    anon = TestClient(app)
    for method, url in (("get", "/api/customer"), ("get", f"/api/customer/{item}/image"),
                        ("post", f"/api/customer/{item}/seen"), ("delete", f"/api/customer/{item}")):
        assert getattr(anon, method)(url).status_code == 401, url
    listing = admin.get("/api/customer").json()
    assert listing["days"] == 5 and listing["items"][0]["id"] == item and listing["items"][0]["seen"] is False
    assert admin.get(f"/api/customer/{item}/image").headers["content-type"] == "image/jpeg"
    assert admin.post(f"/api/customer/{item}/seen").json()["item"]["seen"] is True
    assert admin.delete(f"/api/customer/{item}").status_code == 200
    assert admin.get("/api/customer").json()["items"] == []
    assert admin.delete(f"/api/customer/{item}").status_code == 404


@pytest.mark.parametrize("bad_id", ["..", "..%2Fprofile", "20260101-000000-zzzzzzzz", "x", "20260101-000000-abcdef12/../.."])
def test_item_ids_cannot_escape_the_folder(admin, bad_id):
    for method, url in (("get", f"/api/customer/{bad_id}/image"), ("delete", f"/api/customer/{bad_id}")):
        assert getattr(admin, method)(url).status_code in (404, 405)
