import io

import numpy as np
import pytest
from PIL import Image

from app.services.drawing import DrawError, raster_in, spec, tone


def png(w, h, fill=128, mode="L", fmt="PNG"):
    im = Image.new(mode, (w, h), fill)
    b = io.BytesIO()
    im.save(b, fmt)
    return b.getvalue()


def rp(**kw):
    return spec.parse("raster", kw)


def test_small_image_is_upscaled_only_to_what_the_frame_needs():
    r = raster_in.load(png(300, 200), rp(), 180, 277)
    assert max(r.gray.shape) == 585                       # 180 mm / 0,4 × 1,3: đủ cho khung, không hơn
    assert r.width_mm == pytest.approx(180) and r.height_mm == pytest.approx(120)


def test_upscale_is_capped_at_720px():
    r = raster_in.load(png(100, 100), rp(pen_width_mm=0.2), 285, 318)
    assert max(r.gray.shape) == raster_in.UPSCALE_TO_PX


def test_small_frame_uses_the_minimum_working_side():
    r = raster_in.load(png(300, 200), rp(), 40, 40)       # khung nhỏ: chạm sàn MIN_SIDE_PX
    assert max(r.gray.shape) == 400                        # sàn MIN_SIDE_PX


def test_downscale_to_pen_resolution():
    r = raster_in.load(png(6000, 4000), rp(pen_width_mm=0.4), 200, 287)
    assert max(r.gray.shape) == round(200 / 0.4 * 1.3)  # 650 -> chạm sàn 400 nên là 650
    r2 = raster_in.load(png(6000, 4000), rp(pen_width_mm=0.2), 200, 287)
    assert max(r2.gray.shape) > max(r.gray.shape)


def test_draft_is_smaller_than_final():
    d = raster_in.load(png(6000, 4000), rp(quality="draft"), 285, 318)
    f = raster_in.load(png(6000, 4000), rp(quality="final"), 285, 318)
    assert max(d.gray.shape) < max(f.gray.shape)


def test_crop_changes_aspect_and_size():
    r = raster_in.load(png(1000, 1000), rp(crop_w=0.5, crop_h=1.0), 200, 200)
    assert r.gray.shape[1] * 2 == pytest.approx(r.gray.shape[0], abs=2)
    assert r.width_mm == pytest.approx(100) and r.height_mm == pytest.approx(200)


def test_transparent_becomes_white():
    im = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    b = io.BytesIO(); im.save(b, "PNG")
    r = raster_in.load(b.getvalue(), rp(), 100, 100)
    assert r.gray.min() == 255


def test_bad_data_is_draw_error():
    with pytest.raises(DrawError) as e:
        raster_in.load(b"not an image", rp(), 100, 100)
    assert e.value.code == "bad_image"


def test_exif_rotation_swaps_axes():
    im = Image.new("L", (400, 200), 200)
    exif = Image.Exif(); exif[0x0112] = 6
    b = io.BytesIO(); im.save(b, "JPEG", exif=exif)
    r = raster_in.load(b.getvalue(), rp(), 100, 100)
    assert r.gray.shape[0] > r.gray.shape[1]


def test_tone_levels_and_invert():
    g = np.array([[0, 128, 255]], dtype=np.uint8)
    d = tone.darkness(g, rp(), spec.parse("style", {}))
    assert d[0, 0] == pytest.approx(1.0) and d[0, 2] == pytest.approx(0.0)
    d2 = tone.darkness(g, rp(), spec.parse("style", {"invert": True}))
    assert d2[0, 0] == pytest.approx(0.0)
    d3 = tone.darkness(g, rp(black_point=100, white_point=200), spec.parse("style", {}))
    assert d3[0, 0] == pytest.approx(1.0) and d3[0, 2] == pytest.approx(0.0)


def test_auto_levels_stretches_a_dull_photo():
    g = np.tile(np.linspace(100, 160, 200, dtype=np.uint8), (50, 1))       # chỉ dùng 60/255 mức xám
    on = tone.darkness(g, rp(), spec.parse("style", {}))
    off = tone.darkness(g, rp(auto_levels=False), spec.parse("style", {}))
    assert on.max() - on.min() > 0.9 and off.max() - off.min() < 0.3


def test_auto_levels_leaves_flat_images_alone():
    g = np.full((20, 20), 128, dtype=np.uint8)
    d = tone.darkness(g, rp(), spec.parse("style", {}))
    assert np.ptp(d) == 0


def test_reference_box_uses_the_real_frame_when_given():
    from app.services.drawing import raster
    assert raster.reference_box({"paper": "a4", "margin_mm": 5}) == (200.0, 287.0)
    assert raster.reference_box({"paper": "a4", "margin_mm": 5, "width_mm": 80, "height_mm": 60}) == (80.0, 60.0)
