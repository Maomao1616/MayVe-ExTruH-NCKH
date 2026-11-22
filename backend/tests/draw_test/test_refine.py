"""Vòng sửa sai (refine.py, 17/11/2026): dựng mực đúng độ rộng, chỉnh mục tiêu làm sai số nhỏ đi, không thêm nét vào giấy trắng chủ ý."""
import numpy as np
import pytest

from app.services.drawing import refine, spec, styles
from app.services.drawing.hatch import Field

PEN = 0.5


def style(**kw):
    return spec.parse("style", {"kind": "crosshatch", **kw})


def gradient(w_mm=60.0, h_mm=40.0, px=0.25):
    h, w = int(h_mm / px), int(w_mm / px)
    ramp = np.tile(np.linspace(0.0, 0.9, w, dtype=np.float32), (h, 1))
    return Field(ramp, w_mm, h_mm)


def parallel(w_mm, h_mm, spacing, angle_deg):
    """Các đường song song cách `spacing` mm, đủ dài phủ kín khung."""
    a = np.deg2rad(angle_deg)
    d, n = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
    c = np.array([w_mm / 2, h_mm / 2])
    reach = float(np.hypot(w_mm, h_mm))
    return [[tuple(c + n * k * spacing - d * reach), tuple(c + n * k * spacing + d * reach)]
            for k in range(-int(reach / spacing), int(reach / spacing) + 1)]


@pytest.mark.parametrize("angle", [0, 20, 45, 70])
def test_ink_cover_matches_width_over_spacing_at_any_angle(angle):
    # nét 0,5 mm cách 1,3 mm phủ 0,5 / 1,3 = 0,385. Dựng mực bằng OpenCV từng lệch 14-25 % (nét dày hơn yêu cầu, tùy góc)
    cover, _ = refine.ink_cover(parallel(60, 40, 1.3, angle), 60, 40, PEN)
    h, w = cover.shape
    core = cover[h // 4: -h // 4, w // 4: -w // 4]
    assert float(core.mean()) == pytest.approx(PEN / 1.3, rel=0.06)


def test_overlapping_strokes_count_once():
    one = [[(5.0, 20.0), (55.0, 20.0)]]
    twice = one + one
    a, _ = refine.ink_cover(one, 60, 40, PEN)
    b, _ = refine.ink_cover(twice, 60, 40, PEN)
    assert np.allclose(a, b)


def test_coverage_error_is_zero_when_ink_matches_the_target():
    f = Field(np.full((160, 240), 0.385, np.float32), 60.0, 40.0)
    err, emap = refine.coverage_error(parallel(60, 40, 1.3, 45), f.dark, 60, 40, PEN)
    assert err < 0.03
    assert abs(float(emap.mean())) < 0.03


def test_zero_passes_is_the_plain_fill():
    f = gradient()
    sp = style(refine_passes=0)
    assert styles.fill(f, sp, PEN) == styles.fill(f, style(refine_passes=0), PEN)
    report = {}
    styles.fill_groups(f, sp, PEN, report=report)
    assert report == {}                                    # tắt thì không đo gì


def test_refine_lowers_the_error_and_reports_it():
    f = gradient()
    report = {}
    groups = styles.fill_groups(f, style(refine_passes=2), PEN, report=report)
    assert groups and report["passes"] >= 1
    assert report["error_after"] <= report["error_before"]
    assert report["strokes_after"] > 0


def test_refine_never_returns_a_result_worse_than_the_first_fill():
    for kind in ("crosshatch", "wave_am"):
        report = {}
        styles.fill_groups(gradient(), style(kind=kind, refine_passes=3), PEN, report=report)
        assert report["error_after"] <= report["error_before"] + 1e-9


def test_blank_paper_stays_blank():
    # nền dưới REFINE_RAISE_FROM (giấy trắng chủ ý) không được thêm nét dù mực thiếu ở chỗ khác
    d = np.zeros((160, 240), np.float32)
    d[:, 120:] = 0.8
    f = Field(d, 60.0, 40.0)
    groups = styles.fill_groups(f, style(refine_passes=3), PEN)
    xs = [x for g in groups for s in g for x, _ in s]
    assert min(xs) > 25.0                                   # không có nét nào ở nửa trái (x < 30 mm, trừ mép mờ)


def test_flow_and_outline_are_not_refined():
    f = gradient()
    for kind in ("flow", "outline", "spiral"):         # xoắn ốc: sóng dọc một xoắn ốc từ 22/11/2026, không theo đường cong tông
        report = {}
        styles.fill_groups(f, style(kind=kind, refine_passes=3), PEN, report=report)
        assert report == {}


def test_cancel_is_checked_between_passes():
    class Ctx:
        calls = 0

        def check(self):
            self.calls += 1

    ctx = Ctx()
    styles.fill_groups(gradient(), style(refine_passes=2), PEN, ctx=ctx)
    assert ctx.calls >= 2


def test_big_frame_keeps_memory_bounded():
    cover, cell = refine.ink_cover([[(1.0, 1.0), (2000.0, 1500.0)]], 2000.0, 1500.0, PEN)
    assert cover.shape[0] * cover.shape[1] < 1.1 * refine.REFINE_MAX_PIXELS
    assert cell > 0


def test_raster_pipeline_reports_refine_by_default_and_none_when_off():
    import io
    from PIL import Image
    from app.services.drawing import raster
    buf = io.BytesIO()
    Image.fromarray(np.tile(np.linspace(255, 0, 500), (330, 1)).astype("uint8")).save(buf, "PNG")
    opts = {"raster": {"pen_width_mm": 0.5, "max_side_px": 500}, "style": {"kind": "crosshatch", "outline_overlay": False},
            "optimize": {"bridge": False}, "layout": {"paper": "a5", "margin_mm": 5}}
    layers, _, info, _ = raster.build_raster(buf.getvalue(), "g.png", opts, None)
    assert info["refine"]["passes"] >= 1 and info["refine"]["error_after"] <= info["refine"]["error_before"]
    opts["style"]["refine_passes"] = 0
    assert raster.build_raster(buf.getvalue(), "g.png", opts, None)[2]["refine"] is None
