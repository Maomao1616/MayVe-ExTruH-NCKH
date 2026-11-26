"""Vùng chủ thể (tone.apply_subject, 17/11/2026): ngoài vùng nhạt đi, trong vùng giữ nguyên, tính đúng khi ảnh bị cắt."""
import numpy as np
import pytest

from app.services.drawing import DrawError, spec, tone


def raster(**kw):
    return spec.parse("raster", kw)


def test_no_shape_or_full_keep_returns_the_same_array():
    d = np.full((40, 60), 0.8, np.float32)
    assert tone.apply_subject(d, raster()) is d
    assert tone.apply_subject(d, raster(subject_shape="ellipse", subject_outside=1.0)) is d


def test_ellipse_keeps_inside_and_fades_outside():
    d = np.full((100, 100), 0.8, np.float32)
    out = tone.apply_subject(d, raster(subject_shape="ellipse", subject_x=0.25, subject_y=0.25,
                                       subject_w=0.5, subject_h=0.5, subject_outside=0.25))
    assert out[50, 50] == pytest.approx(0.8)                 # tâm vùng: giữ nguyên
    assert out[2, 2] == pytest.approx(0.8 * 0.25)            # góc ảnh (ngoài elip): còn 25 %
    assert out[50, 5] == pytest.approx(0.8 * 0.25)           # cùng hàng với tâm nhưng ngoài vùng
    assert out.dtype == np.float32


def test_ellipse_corner_of_its_box_is_outside_but_rect_corner_is_inside():
    d = np.ones((100, 100), np.float32)
    kw = dict(subject_x=0.2, subject_y=0.2, subject_w=0.6, subject_h=0.6, subject_outside=0.0)
    ell = tone.apply_subject(d, raster(subject_shape="ellipse", **kw))
    rect = tone.apply_subject(d, raster(subject_shape="rect", **kw))
    assert ell[24, 24] == pytest.approx(0.0) and rect[24, 24] == pytest.approx(1.0)


def test_edge_is_soft_not_a_hard_step():
    d = np.ones((50, 200), np.float32)
    out = tone.apply_subject(d, raster(subject_shape="rect", subject_x=0.25, subject_y=0.0,
                                       subject_w=0.5, subject_h=1.0, subject_outside=0.0))
    row = out[25]
    assert 0.0 < row[50] < 1.0 or 0.0 < row[49] < 1.0         # có điểm chuyển tiếp ở mép trái vùng (cột 50)
    assert np.all(np.diff(row[:100]) >= -1e-6)                # tăng dần từ ngoài vào trong


def test_region_is_mapped_through_the_crop():
    """Vùng tính theo ảnh gốc: cắt nửa phải ảnh thì vùng ở nửa trái gốc nằm hẳn ngoài phần đã cắt (toàn ảnh nhạt đi)."""
    d = np.ones((40, 40), np.float32)
    left_only = raster(subject_shape="rect", subject_x=0.0, subject_y=0.0, subject_w=0.4, subject_h=1.0,
                       subject_outside=0.3, crop_x=0.5, crop_w=0.5)
    assert np.allclose(tone.apply_subject(d, left_only), 0.3)
    centered = raster(subject_shape="rect", subject_x=0.5, subject_y=0.0, subject_w=0.5, subject_h=1.0,
                      subject_outside=0.3, crop_x=0.5, crop_w=0.5)
    assert np.allclose(tone.apply_subject(d, centered)[20, 5:35], 1.0)      # vùng trùng đúng phần đã cắt: giữ nguyên


def test_parameters_are_validated():
    for bad in ({"subject_shape": "triangle"}, {"subject_outside": 1.5}):
        with pytest.raises(DrawError) as e:
            raster(**bad)
        assert e.value.code == "bad_param", bad


def _scene(h=160, w=240):
    """Cảnh tổng hợp: nền nâu có nhiễu nhẹ, ở giữa một khối sáng vàng cam (chủ thể rõ so với nền)."""
    rng = np.random.default_rng(3)
    img = np.empty((h, w, 3), np.uint8)
    img[:] = (70, 55, 45)
    img = np.clip(img.astype(np.int16) + rng.integers(-8, 9, img.shape), 0, 255).astype(np.uint8)
    img[40:120, 80:160] = (235, 200, 90)
    return img


def test_auto_subject_finds_the_centre_object_and_fades_the_background():
    rgb = _scene()
    w = tone.auto_subject_weight(rgb, 160, 240)
    assert w is not None and w.shape == (160, 240) and w.dtype == np.float32
    assert w[80, 120] > 0.9 and w[5, 5] < 0.1 and w[150, 230] < 0.1      # giữa = chủ thể, góc = nền
    d = np.ones((160, 240), np.float32)
    out = tone.apply_subject(d, raster(subject_shape="auto", subject_outside=0.2), rgb)
    assert out[80, 120] > 0.9 and out[5, 5] < 0.3                          # nền chỉ còn ~20 % độ đậm


def test_auto_subject_gives_the_same_result_every_run():
    rgb = _scene()
    assert np.array_equal(tone.auto_subject_weight(rgb, 160, 240), tone.auto_subject_weight(rgb, 160, 240))


def test_auto_subject_on_a_flat_image_keeps_everything_and_warns():
    flat = np.full((120, 160, 3), 128, np.uint8)
    d = np.ones((120, 160), np.float32)
    warnings: list = []
    out = tone.apply_subject(d, raster(subject_shape="auto", subject_outside=0.0), flat, warnings)
    assert np.array_equal(out, d) and warnings == [{"code": "subject_auto_failed", "count": 1}]
    assert tone.apply_subject(d, raster(subject_shape="auto", subject_outside=0.0)) is d      # thiếu ảnh màu: giữ nguyên


def _poly(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def test_free_subject_keeps_painted_area_and_fades_the_rest():
    import json
    text = json.dumps({"add": [_poly(0.25, 0.25, 0.75, 0.75)], "sub": []})
    d = np.ones((100, 100), np.float32)
    out = tone.apply_subject(d, raster(subject_shape="free", subject_poly=text, subject_outside=0.2))
    assert out[50, 50] > 0.95 and out[5, 5] < 0.25 and out[95, 95] < 0.25


def test_free_subject_paint_out_wins_over_paint_in():
    import json
    text = json.dumps({"add": [_poly(0.1, 0.1, 0.9, 0.9)], "sub": [_poly(0.4, 0.4, 0.6, 0.6)]})
    w = tone.free_subject_weight(text, (0.0, 0.0, 1.0, 1.0), 100, 100)
    assert w[20, 20] > 0.95 and w[50, 50] < 0.05                           # lỗ tô bớt ở giữa


def test_free_subject_follows_the_crop():
    import json
    text = json.dumps({"add": [_poly(0.5, 0.0, 1.0, 1.0)], "sub": []})   # nửa phải ảnh gốc
    w = tone.free_subject_weight(text, (0.5, 0.0, 0.5, 1.0), 40, 40)       # chỉ cắt đúng nửa phải: phủ kín
    assert w.min() > 0.9
    assert tone.free_subject_weight(text, (0.0, 0.0, 0.4, 1.0), 40, 40) is None     # cắt nửa trái: chưa tô gì ở đó


def test_free_subject_bad_input_keeps_everything_and_warns():
    d = np.ones((50, 50), np.float32)
    for bad in ("", "không phải json", "[]", '{"add": []}', '{"add": [[[0, 0], [1, 1]]]}', '{"add": [[["a", "b"], [1, 2], [3, 4]]]}'):
        warnings: list = []
        out = tone.apply_subject(d, raster(subject_shape="free", subject_poly=bad, subject_outside=0.0), None, warnings)
        assert np.array_equal(out, d) and warnings == [{"code": "subject_free_invalid", "count": 1}]


def test_subject_poly_is_a_validated_text_parameter():
    assert raster(subject_poly="x").subject_poly == "x"
    for bad in (5, "x" * 60001):
        with pytest.raises(DrawError) as e:
            raster(subject_poly=bad)
        assert e.value.code == "bad_param", type(bad)
