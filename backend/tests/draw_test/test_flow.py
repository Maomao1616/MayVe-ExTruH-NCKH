"""Kiểu tô "Theo dáng ảnh" (flow.py, bản thô): nét dọc theo dáng ảnh, khoảng cách theo độ đậm, không râu vụn."""
import math
from types import SimpleNamespace

import numpy as np

from app.services.drawing import flow, styles
from app.services.drawing.hatch import Field

STYLE = SimpleNamespace(kind="flow", angle=45.0, spacing_mm=None, levels=5, soft_levels=True, amplitude_mm=None)


def _strokes(dark: np.ndarray, w_mm: float, h_mm: float, pen: float = 0.5):
    return [np.asarray(s) for g in styles.GROUPERS["flow"](Field(dark.astype(np.float32), w_mm, h_mm), STYLE, pen) for s in g]


def _directions(strokes):
    """Góc (độ, 0..180) của từng đoạn."""
    out = []
    for s in strokes:
        d = np.diff(s, axis=0)
        out += list(np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 180.0)
    return np.array(out)


def test_white_gives_no_strokes_and_flat_gray_follows_the_default_angle():
    assert _strokes(np.zeros((200, 200)), 40, 40) == []
    gray = _strokes(np.full((200, 200), 0.4), 40, 40)
    assert gray
    a = _directions(gray)
    assert np.median(np.abs(a - 45.0)) < 5.0                       # mặt phẳng không có hướng: theo góc mặc định


def test_lines_follow_the_iso_lines_of_a_ramp_and_space_by_darkness():
    w, h = 300, 200                                                # 60 × 40 mm, đậm dần theo X
    dark = np.tile(np.linspace(0.15, 0.85, w), (h, 1))
    strokes = _strokes(dark, 60, 40)
    a = _directions(strokes)
    assert np.mean(np.abs(a - 90.0) < 15.0) > 0.8                  # nét dọc (theo đường cùng độ đậm), không chéo 45°
    xs_light = [s[:, 0].mean() for s in strokes if s[:, 0].mean() < 20]
    xs_dark = [s[:, 0].mean() for s in strokes if s[:, 0].mean() > 40]
    assert len(xs_dark) > 1.5 * len(xs_light)                      # vùng đậm nhiều đường hơn hẳn (14/11: đường cong tông nâng đầu nhạt nên còn ~2×)


def test_ring_gives_circular_strokes_and_none_shorter_than_three_spacings():
    n = 300                                                        # 60 × 60 mm, vành tròn đậm quanh tâm
    yy, xx = np.mgrid[0:n, 0:n] / n * 60.0
    r = np.hypot(xx - 30, yy - 30)
    dark = np.clip(1 - np.abs(r - 18) / 8, 0, 1) * 0.8
    strokes = _strokes(dark, 60, 60)
    assert strokes
    tangent = []                                                   # hướng nét so với bán kính: phải gần vuông góc
    for s in strokes:
        for p, q in zip(s[:-1], s[1:]):
            mid = (p + q) / 2 - 30
            d = q - p
            if np.hypot(*mid) > 1 and np.hypot(*d) > 0:
                tangent.append(abs(np.dot(mid, d)) / (np.hypot(*mid) * np.hypot(*d)))
    assert np.median(tangent) < 0.3                                # cos(góc với bán kính) nhỏ = đi vòng quanh tâm
    for s in strokes:
        length = float(np.hypot(*np.diff(s, axis=0).T).sum())
        assert length >= flow.FLOW_MIN_LEN_SEPS * flow.FLOW_MIN_SEP_LINES * 0.5 - 1e-6


def test_strokes_stay_inside_and_turn_no_sharper_than_min_radius():
    rng = np.random.default_rng(1)
    dark = np.clip(cv2_blur(rng.random((200, 300)).astype(np.float32), 6) * 2 - 0.5, 0, 1)
    strokes = _strokes(dark, 60, 40)
    max_turn = math.degrees(flow.FLOW_STEP_MM / flow.FLOW_MIN_RADIUS_MM) + 1.0
    for s in strokes:
        assert s[:, 0].min() >= 0 and s[:, 0].max() <= 60 and s[:, 1].min() >= 0 and s[:, 1].max() <= 40
        d = np.diff(s, axis=0)
        ang = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
        turn = np.abs((np.diff(ang) + 180) % 360 - 180)
        assert turn.size == 0 or turn.max() <= max_turn


def cv2_blur(img, sigma):
    import cv2
    return cv2.GaussianBlur(img, (0, 0), sigma)
