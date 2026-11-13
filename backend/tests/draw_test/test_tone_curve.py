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
    for kind in ("zigzag", "wave", "wave_am", "flow"):
        assert np.array_equal(styles.tone_cover(d, kind), d)
    monkeypatch.setattr(styles, "USE_TONE_CURVE", False)
    assert np.array_equal(styles.tone_cover(d, "crosshatch"), d)


def _ink(strokes, f, line_w=PEN):
    return float(styles.ink_cover(strokes, f, line_w).mean())


def portrait_like(h=240, w=200):
    """Nền nhạt, mặt tròn trung bình, mắt đậm: có viền rõ để kiểu lai đặt đường theo dáng."""
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


def test_crosshatch_flow_adds_shape_lines_and_keeps_total_ink():
    f = portrait_like()
    groups = styles.fill_groups(f, style(kind="crosshatch_flow"), PEN)
    curves = groups[-1]
    assert len(curves) >= 3 and sum(len(s) for s in curves) > 100        # có đường theo dáng (ảnh giả: mép mặt + 2 mắt)
    plain = styles.fill(f, style(kind="crosshatch"), PEN)
    hybrid = [s for g in groups for s in g]
    assert _ink(hybrid, f) == pytest.approx(_ink(plain, f), rel=0.12)   # lớp đan thưa đi bù cho đường theo dáng
    band = styles.edge_band(f)
    pts = np.concatenate([np.asarray(s) for s in curves])
    r = np.clip((pts[:, 1] / f.height_mm * f.h).astype(int), 0, f.h - 1)
    c = np.clip((pts[:, 0] / f.width_mm * f.w).astype(int), 0, f.w - 1)
    assert np.mean(band[r, c] > 0.05) > 0.9                             # đường theo dáng nằm trong dải viền


def test_ui_style_list_matches_spec():
    """Ô Kiểu tô ở index.html hiện đúng spec.UI_STYLES (zigzag / sóng / đan 3 / theo dáng thuần đã ẩn 13/11/2026)."""
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parents[3] / "frontend" / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<select id="style-kind">(.*?)</select>', html, re.S).group(1)
    assert tuple(re.findall(r'value="([^"]+)"', block)) == spec.UI_STYLES
    assert set(spec.UI_STYLES) <= set(spec.STYLES)
