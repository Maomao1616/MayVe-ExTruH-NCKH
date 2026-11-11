"""Nạp ảnh: nhận dạng bằng nội dung, tên tệp dài / ký tự lạ không làm hỏng (lỗi thật 11/11/2026: ảnh 200 KB tên dài bị từ chối)."""
import io
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api import draw
from app.main import app
from app.services import customer

client = TestClient(app)
OPTS = '{"raster": {"pen_width_mm": 0.4, "quality": "draft"}, "layout": {"paper": "a6", "margin_mm": 5}}'


def image(fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (120, 90), (90, 90, 90)).save(buf, fmt)
    return buf.getvalue()


def run(name, data):
    r = client.post("/api/draw/import", files={"file": (name, data)}, data={"options": OPTS})
    assert r.status_code == 202, r.text
    token = r.json()["task"]
    end = time.time() + 20
    while time.time() < end:
        body = client.get(f"/api/draw/tasks/{token}").json()
        if body["state"] in ("done", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("quá thời gian")


@pytest.mark.parametrize("name", [
    "a" * 300 + ".jpg",                                         # tên rất dài
    "ảnh mèo ngộ nghĩnh – bản đẹp (1) ⭐🐱.jpg",                  # Unicode, dấu, emoji
    "IMG\u0001_‮9999.jpg",                                 # ký tự điều khiển / đảo chiều
    "tai-ve-tu-mang.jfif",                                      # đuôi .jfif
    "khong-co-duoi", "sai-duoi.txt",                            # đuôi thiếu / sai nhưng nội dung là ảnh
])
def test_any_name_is_accepted_when_content_is_an_image(name):
    done = run(name, image("JPEG"))
    assert done["state"] == "done", done


def test_other_image_formats_by_content():
    for fmt in ("PNG", "WEBP", "BMP", "GIF"):
        assert run(f"x.{fmt.lower()}", image(fmt))["state"] == "done", fmt


def test_non_image_is_still_refused():
    r = client.post("/api/draw/import", files={"file": ("a.txt", b"hello")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_image"
    done = run("fake.png", b"not really a png")                  # đuôi ảnh nhưng hỏng: báo ở bước giải mã
    assert done["state"] == "failed" and done["error"]["code"] == "bad_image"


def test_svg_by_content_without_extension():
    svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><path d="M0 0L10 10"/></svg>'
    assert run("ve-tay", svg)["state"] == "done"


def test_display_name_is_short_and_clean():
    assert draw.display_name("a" * 300 + ".jpg") == "a" * 60
    assert draw.display_name("  mèo \u0001 xinh\n.PNG ") == "mèo xinh"
    assert draw.display_name(None) == "ban-ve" and draw.display_name("....") == "ban-ve"


def test_customer_stored_filename_keeps_a_valid_image_extension():
    assert customer.stored_filename("b" * 200 + ".png") == "b" * 50 + ".jpg"
    assert customer.stored_filename("ảnh mèo.jfif") == "ảnh mèo.jpg"
    assert customer.stored_filename("") == "anh.jpg"
