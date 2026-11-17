"""Vùng chủ thể (tone.apply_subject, 17/11/2026): ngoài vùng nhạt đi, trong vùng giữ nguyên, tính đúng khi ảnh bị cắt."""
import numpy as np
import pytest

from app.services.drawing import spec, tone


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
    with pytest.raises(Exception):
        raster(subject_shape="triangle")
    with pytest.raises(Exception):
        raster(subject_outside=1.5)
