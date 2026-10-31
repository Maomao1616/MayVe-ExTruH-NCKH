import math

import cv2
import numpy as np
import pytest

from app.services.drawing import spec, styles
from app.services.drawing.hatch import Field


def field(dark, w=60.0, h=40.0):
    return Field(np.asarray(dark, dtype=np.float32), w, h)


def style(**kw):
    return spec.parse("style", kw)


def length(strokes):
    return sum(math.dist(a, b) for s in strokes for a, b in zip(s, s[1:]))


def gradient(h=200, w=300):
    return np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))


@pytest.mark.parametrize("kind", ["zigzag", "wave", "spiral"])
def test_blank_gives_nothing_black_gives_lines(kind):
    assert styles.fill(field(np.zeros((100, 150))), style(kind=kind), 0.4) == []
    black = styles.fill(field(np.ones((100, 150))), style(kind=kind), 0.4)
    assert black and length(black) > 500


@pytest.mark.parametrize("kind", ["zigzag", "wave", "spiral"])
def test_strokes_stay_inside_box(kind):
    f = field(gradient())
    for s in styles.fill(f, style(kind=kind), 0.4):
        assert len(s) >= 2
        for x, y in s:
            assert 0 <= x <= f.width_mm and 0 <= y <= f.height_mm


@pytest.mark.parametrize("kind", ["zigzag", "wave", "spiral"])
def test_darker_side_gets_more_ink(kind):
    f = field(gradient())
    strokes = styles.fill(f, style(kind=kind), 0.4)
    left = sum(math.dist(a, b) for s in strokes for a, b in zip(s, s[1:]) if a[0] < 30 and b[0] < 30)
    right = sum(math.dist(a, b) for s in strokes for a, b in zip(s, s[1:]) if a[0] >= 30 and b[0] >= 30)
    assert right > 3 * max(left, 1)


def test_more_levels_more_ink():
    f = field(gradient())
    a = length(styles.fill(f, style(levels=3), 0.4))
    b = length(styles.fill(f, style(levels=5), 0.4))
    assert b > a


def test_zigzag_joins_lines_into_few_strokes():
    f = field(np.ones((100, 150)))
    one_pass = styles.fill(f, style(levels=3), 0.4)
    # 60x40 mm đặc, khoảng cách 0,8 mm: hàng chục dòng mà ít nét (nối đi-về)
    assert len(one_pass) < 20


def test_spacing_controls_density():
    f = field(np.ones((100, 150)))
    wide = length(styles.fill(f, style(spacing_mm=2.0), 0.4))
    tight = length(styles.fill(f, style(spacing_mm=0.5), 0.4))
    assert tight > 2.5 * wide


def test_unknown_style_is_error():
    from app.services.drawing import DrawError
    from app.services.drawing.registry import FILLERS
    with pytest.raises(DrawError):
        FILLERS.get("nope")


# --- viền (edges.py: nét mực + ranh giới mảng + nối khe hở) ------------------------------
def ring_field(size=300, w=60.0, h=60.0, band=(92.5, 95.5)):
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx - size / 2, yy - size / 2)
    d = ((r > band[0]) & (r < band[1])).astype(np.float32)   # vòng tròn mảnh ~3 điểm ảnh
    return Field(d, w, h)


def test_outline_traces_one_centerline_per_ring():
    f = ring_field()
    strokes = styles.fill(f, style(kind="outline"), 0.4)
    assert 1 <= len(strokes) <= 3
    # bán kính đường giữa ≈ 94 điểm ảnh = 18,8 mm; chu vi ≈ 118 mm (một đường, không phải hai viền song song)
    assert 100 < length(strokes) < 135
    cx = cy = 30.0
    for s in strokes:
        for x, y in s:
            assert 17 < math.hypot(x - cx, y - cy) < 21


def test_outline_of_a_thick_ink_line_is_one_centerline():
    f = ring_field(band=(86, 102))                          # nét mực dày 3,2 mm (viền hoạt hình): MỘT đường giữa
    strokes = styles.fill(f, style(kind="outline"), 0.4)
    radii = [math.hypot(x - 30, y - 30) for s in strokes for x, y in s]
    assert 17.6 < min(radii) and max(radii) < 20.4 and 100 < length(strokes) < 140


def test_outline_of_a_wide_band_follows_both_edges():
    f = ring_field(band=(70, 110))                          # mảng đậm 8 mm (rộng hơn INK_MAX_MM): viền hai phía
    strokes = styles.fill(f, style(kind="outline"), 0.4)
    radii = [math.hypot(x - 30, y - 30) for s in strokes for x, y in s]
    assert min(radii) < 14.6 and max(radii) > 21.4 and length(strokes) > 170


def test_outline_finds_boundary_between_colours_of_equal_brightness():
    rgb = np.zeros((200, 200, 3), np.uint8)
    rgb[:] = (200, 60, 60)                                  # đỏ
    rgb[:, 100:] = (60, 130, 60)                            # xanh lá, gần cùng độ sáng
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    d = 1.0 - gray.astype(np.float32) / 255.0
    plain = styles.fill(Field(d, 40.0, 40.0), style(kind="outline"), 0.4)
    coloured = styles.fill(Field(d, 40.0, 40.0, rgb), style(kind="outline"), 0.4)
    near_seam = [s for s in coloured if all(abs(x - 20.0) < 1.0 for x, _ in s)]
    assert not [s for s in plain if all(abs(x - 20.0) < 1.0 for x, _ in s)]
    assert near_seam and max(abs(s[0][1] - s[-1][1]) for s in near_seam) > 30


def test_outline_bridges_small_gaps():
    d = np.zeros((200, 300), np.float32)
    d[98:102, 20:140] = 1.0                                 # nét mực bị đứt khe 0,6 mm (3 px) ở giữa
    d[98:102, 143:280] = 1.0
    strokes = styles.fill(Field(d, 60.0, 40.0), style(kind="outline"), 0.4)
    assert len(strokes) == 1 and length(strokes) > 50


def test_outline_detail_low_keeps_fewer_strokes():
    rng = np.random.default_rng(3)
    d = np.clip(rng.normal(0.5, 0.3, (300, 300)), 0, 1).astype(np.float32)
    d = cv2.normalize(cv2.GaussianBlur(d, (0, 0), 1.2), None, 0, 1, cv2.NORM_MINMAX)   # kết cấu như lông / vân gỗ
    low = styles.fill(Field(d, 60.0, 60.0), style(kind="outline", outline_detail="low"), 0.4)
    high = styles.fill(Field(d, 60.0, 60.0), style(kind="outline", outline_detail="high"), 0.4)
    assert len(low) < len(high)


def test_outline_on_blank_is_empty():
    assert styles.fill(field(np.zeros((100, 100))), style(kind="outline"), 0.4) == []


def test_outline_overlay_adds_strokes_after_the_fill():
    f = ring_field()
    plain = styles.fill(f, style(kind="zigzag"), 0.4)
    both = styles.fill(f, style(kind="zigzag", outline_overlay=True), 0.4)
    assert len(both) > len(plain) and both[:len(plain)] == plain


# --- ngân sách điểm của sóng, nối khe xoắn ốc -------------------------------------------
def points(strokes):
    return sum(len(s) for s in strokes)


def test_wave_gets_longer_wavelength_instead_of_exceeding_the_point_budget(monkeypatch):
    f = field(np.ones((100, 150)), 100.0, 150.0)
    normal = points(styles.fill(f, style(kind="wave"), 0.4))
    monkeypatch.setattr("app.services.drawing.hatch.WAVE_POINT_BUDGET", normal // 4)
    squeezed = points(styles.fill(f, style(kind="wave"), 0.4))
    assert squeezed < normal / 2.5


def test_spiral_bridges_short_white_gaps_to_save_pen_lifts():
    d = np.ones((150, 150), dtype=np.float32)
    d[:, 70:73] = 0.0                                         # dải trắng hẹp (≈ 1 mm) cắt ngang
    f = Field(d, 60.0, 60.0)
    strokes = styles.fill(f, style(kind="spiral", levels=3), 0.4)
    gap_free = styles.fill(Field(np.ones((150, 150), dtype=np.float32), 60.0, 60.0), style(kind="spiral", levels=3), 0.4)
    assert len(strokes) <= len(gap_free) + 2                  # khe hẹp không làm tăng số lần nhấc bút
