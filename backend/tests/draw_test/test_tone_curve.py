"""Đường cong tông (styles.TONE_CURVES, đo 13/11/2026) (kiểu lai đan chéo + theo dáng đã xóa 17/11/2026)."""
import numpy as np
import pytest

from app.services.drawing import spec, styles

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


def test_ui_style_list_matches_spec():
    """Ô Kiểu tô ở index.html hiện đúng spec.UI_STYLES (zigzag / sóng / đan 3 / theo dáng thuần đã ẩn 13/11/2026)."""
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parents[3] / "frontend" / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<select id="style-kind">(.*?)</select>', html, re.S).group(1)
    assert tuple(re.findall(r'value="([^"]+)"', block)) == spec.UI_STYLES
    assert set(spec.UI_STYLES) <= set(spec.STYLES)
