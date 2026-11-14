"""Đường cong tông (styles.TONE_CURVES, đo 13/11/2026) và kiểu Đan chéo + theo dáng (crosshatch_flow)."""
import math

import numpy as np
import pytest

from app.services.drawing import spec, styles
from app.services.drawing.hatch import Field

PEN = 0.5


def style(**kw):
    kw.setdefault("outline_overlay", False)
    return spec.parse("style", kw)


def test_tone_cover_keeps_ends_and_darkens_mid_tones():
    d = np.linspace(0, 1, 101, dtype=np.float32)
    for kind in ("crosshatch", "spiral"):
        c = styles.tone_cover(d, kind)
        assert c[0] == 0 and np.all(np.diff(c) >= -1e-6)                    # tăng dần
        assert c[90] == pytest.approx(styles.MAX_COVERAGE, abs=1e-3)        # đậm nhất vẫn là độ phủ đậm nhất
    cross = styles.tone_cover(np.array([0.45], np.float32), "crosshatch")[0]
    assert 0.55 < cross < 0.65              # 45 % đậm mắt thấy cần ~60 % độ phủ (phủ 50 % chỉ trông 0,39)
    spiral = styles.tone_cover(np.array([0.45], np.float32), "spiral")[0]
    assert spiral < cross                   # xoắn ốc đậm nhanh hơn: cần ít độ phủ hơn


def test_styles_without_a_table_and_switch_off_keep_old_mapping(monkeypatch):
    d = np.linspace(0, 1, 11, dtype=np.float32)
    for kind in ("zigzag", "wave", "wave_am"):
        assert np.array_equal(styles.tone_cover(d, kind), d)
    monkeypatch.setattr(styles, "USE_TONE_CURVE", False)
    assert np.array_equal(styles.tone_cover(d, "crosshatch"), d)


def _ink(strokes, f, line_w=PEN):
    return float(styles.ink_cover(strokes, f, line_w).mean())


def portrait_like(h=240, w=200):
    """Nền nhạt, mặt tròn trung bình, mắt đậm: có viền rõ."""
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.full((h, w), 0.15, np.float32)
    img[(xx - 100) ** 2 + (yy - 120) ** 2 < 70 ** 2] = 0.5
    for ex in (75, 125):
        img[(xx - ex) ** 2 + (yy - 105) ** 2 < 10 ** 2] = 0.9
    return Field(img, 50.0, 60.0)


def test_edge_band_marks_edges_not_flat_areas():
    f = portrait_like()
    band = styles.edge_band(f)
    assert band[120, 30] > 0.5 and band[120, 100] < 0.1 and band[5, 5] < 0.1   # mép mặt / giữa mặt / nền phẳng


def _near_contour(strokes, contour, f, mm=0.25, mask=styles.stroke_mask):
    """Tỷ lệ chiều dài nét nằm cách tim đường viền dưới `mm` (lấy mẫu dày mỗi 0,05 mm)."""
    import cv2
    line = mask(contour, f, f.px_mm)
    dist = cv2.distanceTransform((~line).astype(np.uint8), cv2.DIST_L2, 5) * f.px_mm
    pts = []
    for s in strokes:
        a = np.asarray(s)
        for p, q in zip(a[:-1], a[1:]):
            pts.append(p + (q - p) * np.linspace(0, 1, max(2, int(np.hypot(*(q - p)) / 0.05)))[:, None])
    d = np.concatenate(pts)
    r = np.clip((d[:, 1] / f.height_mm * f.h).astype(int), 0, f.h - 1)
    c = np.clip((d[:, 0] / f.width_mm * f.w).astype(int), 0, f.w - 1)
    return float(np.mean(dist[r, c] < mm))


def test_crosshatch_flow_contour_fences_the_hatching(monkeypatch):
    """14/11/2026: nhóm cuối là MỘT đường viền bao khối (mặt + 2 mắt); dòng gạch dừng ở viền thay vì chạy qua."""
    f = portrait_like()
    groups = styles.fill_groups(f, style(kind="crosshatch_flow"), PEN)
    contour, hatching = groups[-1], [s for g in groups[:-1] for s in g]
    assert len(contour) >= 3                                             # mép mặt + 2 mắt (mắt là khối đậm: lấy vành)
    fenced = _near_contour(hatching, contour, f)
    monkeypatch.setattr(styles, "stroke_mask", lambda s, ff, w: np.zeros((ff.h, ff.w), bool))
    loose = [s for g in styles.fill_groups(f, style(kind="crosshatch_flow"), PEN)[:-1] for s in g]
    assert fenced < 0.3 * _near_contour(loose, contour, f)               # chỉ còn vòng quay đầu chạm viền


def test_crosshatch_flow_overlay_does_not_draw_contour_twice():
    f = portrait_like()
    plain = styles.fill_groups(f, style(kind="crosshatch_flow"), PEN)
    over = styles.fill_groups(f, style(kind="crosshatch_flow", outline_overlay=True), PEN)
    assert len(over) == len(plain)


def test_ui_style_list_matches_spec():
    """Ô Kiểu tô ở index.html hiện đúng spec.UI_STYLES (zigzag / sóng / đan 3 / theo dáng thuần đã ẩn 13/11/2026)."""
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parents[3] / "frontend" / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<select id="style-kind">(.*?)</select>', html, re.S).group(1)
    assert tuple(re.findall(r'value="([^"]+)"', block)) == spec.UI_STYLES
    assert set(spec.UI_STYLES) <= set(spec.STYLES)
