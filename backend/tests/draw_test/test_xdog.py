"""XDoG cho lớp ranh giới mảng (edges.xdog_edges, 13/11/2026): Nét viền tích "Dùng XDoG", lớp viền phủ lên kiểu tô luôn XDoG."""
import numpy as np

from app.services.drawing import edges, spec, styles
from app.services.drawing.hatch import Field

PX_MM = 0.2


def half_dark_with_shapes():
    """Nửa trái sáng, nửa phải tối; mỗi nửa một hình vuông chỉ đậm hơn nền một chút (cạnh yếu)."""
    img = np.full((200, 400), 0.15, np.float32)
    img[:, 200:] = 0.75
    img[70:130, 70:130] += 0.12
    img[70:130, 270:330] += 0.12
    return img


def test_xdog_finds_weak_edges_in_dark_half_where_canny_low_does_not():
    ds = half_dark_with_shapes()
    xd = edges.xdog_edges(ds, PX_MM, "medium")
    lo, hi, *_ = edges.DETAIL["low"]
    canny = edges.region_edges(ds, None, lo, hi)
    box = (slice(60, 140), slice(260, 340))                 # quanh hình vuông ở nửa tối
    assert xd[box].sum() > 50
    assert canny[box].sum() < xd[box].sum()
    assert not xd[150:190, 20:180].any()                    # nền phẳng không ra nét


def test_more_detail_gives_more_edge_pixels():
    ds = half_dark_with_shapes()
    counts = [edges.xdog_edges(ds, PX_MM, d).sum() for d in ("low", "medium", "high")]
    assert counts[0] <= counts[1] <= counts[2]


def _method_used(monkeypatch, **style_kw):
    seen = {}
    real = edges.outline_mask

    def spy(*args, **kwargs):
        seen["method"] = args[5] if len(args) > 5 else kwargs.get("method", "canny")
        return real(*args, **kwargs)

    monkeypatch.setattr(edges, "outline_mask", spy)
    f = Field(half_dark_with_shapes(), 80.0, 40.0)
    styles.fill_groups(f, spec.parse("style", style_kw), 0.5)
    return seen.get("method")


def test_outline_style_keeps_canny_unless_ticked(monkeypatch):
    assert _method_used(monkeypatch, kind="outline") == "canny"
    assert _method_used(monkeypatch, kind="outline", outline_xdog=True) == "xdog"


def test_outline_overlay_on_fill_styles_always_uses_xdog(monkeypatch):
    assert _method_used(monkeypatch, kind="crosshatch", outline_overlay=True) == "xdog"
    assert _method_used(monkeypatch, kind="crosshatch_flow", outline_overlay=True, outline_xdog=False) == "xdog"
