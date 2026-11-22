"""Tab Beta từ đầu đến cuối với PDF thật (cần PyMuPDF; thiếu thì bỏ qua): đọc trang, dựng lớp, lưu bản vẽ, API tải / xem / nạp."""
import io
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

pymupdf = pytest.importorskip("pymupdf")

from app.main import app
from app.services.beta_pdf import service
from app.services.beta_pdf.reader import PdfDoc
from app.services.drawing.errors import DrawError
from app.services.drawing.store import TASKS


def gradient_png() -> bytes:
    arr = np.tile(np.linspace(255, 0, 120, dtype=np.uint8), (80, 1))
    b = io.BytesIO(); Image.fromarray(arr, "L").save(b, "PNG")
    return b.getvalue()


def make_pdf(text=True, rect=True, image=False, pages=1) -> bytes:
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page(width=420, height=595)
        if text:
            page.insert_text((50, 100), "Hello world 123 Café", fontname="helv", fontsize=14)
            page.insert_text((50, 140), "Tiêu đề", fontname="hebo", fontsize=18)
        if rect:
            page.draw_rect(pymupdf.Rect(40, 200, 300, 260), color=(0, 0, 0), width=1.0)
            page.draw_line((40, 300), (300, 300), color=(0, 0, 0), width=0.5)
        if image:
            page.insert_image(pymupdf.Rect(60, 350, 260, 470), stream=gradient_png())
    return doc.tobytes()


def test_reader_finds_characters_lines_and_sizes():
    with PdfDoc(make_pdf()) as doc:
        c = doc.read_page(0)
    assert 140 < c.width_mm < 150 and 205 < c.height_mm < 215          # 420 × 595 pt ≈ A5
    assert "".join(ch.ch for ch in c.chars).startswith("Hello world 123 Caf")
    big = [ch for ch in c.chars if ch.size_mm > 6]
    assert big and all(ch.bold for ch in big)                           # hebo = Helvetica đậm, 18 pt
    assert len(c.segments) >= 2                                         # hình chữ nhật + đường thẳng


def test_page_builds_one_layer_with_text_and_frame_and_a_task_is_stored():
    result = service.import_page(make_pdf(), "mau.pdf", {})
    assert set(result) == {"task", "source", "warnings"}
    info = result["source"]
    assert info["mode"] == "beta_pdf" and [m["name"] for m in info["layers"]] == ["Chữ và đường kẻ"]
    assert info["beta"]["text"]["single"] > 20 and info["beta"]["frame_strokes"] >= 2
    parsed = TASKS.get(result["task"])
    assert parsed.frame.w == pytest.approx(info["page_mm"]["w"], abs=0.01)
    assert all(len(s) >= 2 for layer in parsed.layers for s in layer.strokes)
    assert info["layers"][0]["id"].startswith("1-")                     # mã lớp có màu như các lớp khác


def test_accented_letter_outside_ascii_is_composed_not_dropped():
    layers, _, info, warn = service.build(make_pdf(rect=False), "x.pdf", {})
    assert info["beta"]["text"]["fallback"] == 0 and info["beta"]["text"]["missing"] == 0
    assert not [w for w in warn if w["code"] in ("beta_fallback_chars", "beta_missing_chars")]


def test_options_change_the_result():
    pdf = make_pdf()
    gon = service.build(pdf, "x", {"font": "simplex"})[2]["layers"][0]["strokes"]
    times = service.build(pdf, "x", {"font": "times"})[2]["layers"][0]["strokes"]
    assert times > gon                                                  # Times nhiều nét kép hơn
    no_frame = service.build(pdf, "x", {"frame": False})[2]
    assert no_frame["beta"]["frame_strokes"] == 0
    skeleton = service.build(pdf, "x", {"text_mode": "skeleton"})[2]
    assert skeleton["beta"]["text"]["skeleton"] > 20 and skeleton["beta"]["text"]["single"] == 0


def test_picture_becomes_its_own_second_layer():
    layers, _, info, _ = service.build(make_pdf(text=False, rect=False, image=True), "x.pdf", {"image_dpi": 100})
    assert [m["name"] for m in info["layers"]] == ["Ảnh"] and info["layers"][0]["id"].startswith("1-") is False
    both, _, info2, _ = service.build(make_pdf(image=True), "x.pdf", {"image_dpi": 100})
    assert [m["name"] for m in info2["layers"]] == ["Chữ và đường kẻ", "Ảnh"]
    ys = [y for s in both[1].strokes for _, y in s]
    assert min(ys) >= 350 * 25.4 / 72 - 1 and max(ys) <= 470 * 25.4 / 72 + 1      # nét ảnh nằm trong khung ảnh trên trang


def test_empty_page_and_bad_page_number_are_clear_errors():
    with pytest.raises(DrawError) as e:
        service.build(make_pdf(text=False, rect=False), "x.pdf", {})
    assert e.value.code == "empty_drawing"
    with pytest.raises(DrawError) as e:
        service.build(make_pdf(), "x.pdf", {"page": 3})
    assert e.value.code == "bad_param"
    with pytest.raises(DrawError) as e:
        service.page_info(b"khong phai pdf")
    assert e.value.code == "bad_pdf"


# ---------- API ----------
@pytest.fixture
def client():
    return TestClient(app)


def upload(client, data, name="mau.pdf"):
    return client.post("/api/beta/pdf/upload", files={"file": (name, data, "application/pdf")})


def wait(client, task, seconds=20):
    end = time.time() + seconds
    while time.time() < end:
        view = client.get(f"/api/draw/tasks/{task}").json()
        if view["state"] in ("done", "failed", "cancelled"):
            return view
        time.sleep(0.05)
    raise AssertionError("tác vụ không xong")


def test_api_upload_preview_import_and_use_the_normal_task_endpoints(client):
    r = upload(client, make_pdf(pages=2))
    assert r.status_code == 201
    body = r.json()
    assert body["pages"] == 2 and body["name"] == "mau.pdf" and len(body["sizes"]) == 2
    pv = client.get(f"/api/beta/pdf/{body['doc']}/page/2/preview.png?dpi=40")
    assert pv.status_code == 200 and pv.content[:4] == b"\x89PNG"
    job = client.post("/api/beta/pdf/import", json={"doc": body["doc"], "options": {"page": 2}})
    assert job.status_code == 202
    view = wait(client, job.json()["task"])
    assert view["state"] == "done" and view["source"]["page"] == 2
    gcode = client.post("/api/draw/gcode", json={"task": view["task"], "machine": {"work_w": 285, "work_h": 318, "z_travel": 5, "rapid_feed": 8000},
                                                  "gcode": {"pen_up_z": 5, "pen_down_z": 0}})
    assert gcode.status_code == 200                                     # dùng lại phần tạo G-code của tab Tạo bản vẽ


def test_api_errors(client):
    assert upload(client, b"khong phai pdf").status_code == 400
    assert client.post("/api/beta/pdf/import", json={"doc": "khong-co", "options": {}}).status_code == 404
    doc = upload(client, make_pdf()).json()["doc"]
    assert client.post("/api/beta/pdf/import", json={"doc": doc, "options": {"page": 9}}).status_code == 400
    assert client.post("/api/beta/pdf/import", json={"doc": doc, "options": {"bogus": 1}}).status_code == 400
    assert client.get(f"/api/beta/pdf/{doc}/page/9/preview.png").status_code == 400
    assert client.get("/api/beta/pdf/schema").json()["params"][0]["name"] == "page"


def diagram_png() -> bytes:
    """Sơ đồ giả: khung chữ nhật nét đen 3 điểm ảnh trên nền trắng."""
    arr = np.full((100, 200), 255, np.uint8)
    arr[20:80, 30:34] = 0
    arr[20:80, 166:170] = 0
    arr[20:24, 30:170] = 0
    arr[76:80, 30:170] = 0
    b = io.BytesIO(); Image.fromarray(arr, "L").save(b, "PNG")
    return b.getvalue()


def make_diagram_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=595)
    page.insert_text((50, 100), "So do khoi", fontname="helv", fontsize=14)
    page.insert_image(pymupdf.Rect(60, 150, 360, 300), stream=diagram_png())
    return doc.tobytes()


def test_line_drawing_picture_is_traced_with_the_text_pen_by_default():
    pdf = make_diagram_pdf()
    layers, _, info, warn = service.build(pdf, "x.pdf", {})
    assert [m["name"] for m in info["layers"]] == ["Chữ và đường kẻ"]        # cùng bút, cùng tệp G-code với chữ
    assert info["beta"]["diagram_strokes"] >= 1 and not [w for w in warn if w["code"] == "beta_image_skipped"]
    ys = [y for l in layers for s in l.strokes for _, y in s]
    assert max(ys) > 150 * 25.4 / 72 and min(ys) < 110 * 25.4 / 72          # có nét ở vùng ảnh và cả chữ
    separate = service.build(pdf, "x.pdf", {"lineart_with_text": False})[2]
    assert [m["name"] for m in separate["layers"]] == ["Chữ và đường kẻ", "Ảnh"]
    forced = service.build(pdf, "x.pdf", {"image_kind": "lineart"})[2]
    assert forced["beta"]["diagram_strokes"] >= 1
