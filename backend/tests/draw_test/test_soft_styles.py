"""Chuyển mức mềm (soft_levels), gạch chéo chồng lớp (crosshatch), sóng biến thiên (wave_am). Đo bằng mô phỏng mực:
vẽ lại các nét với bề rộng nét thật rồi làm mờ như mắt nhìn xa."""
import cv2
import numpy as np
import pytest

from app.services.drawing import hatch, spec, styles
from app.services.drawing.hatch import Field

PEN = 0.4
SC = 20                                         # mô phỏng 20 điểm / mm


def style(**kw):
    return spec.parse("style", kw)


def ink(strokes, w_mm, h_mm):
    canvas = np.zeros((int(h_mm * SC), int(w_mm * SC)), np.uint8)
    width = max(1, int(round(styles.LINE_WIDTH_RATIO * PEN * SC)))
    for s in strokes:
        cv2.polylines(canvas, [(np.asarray(s) * SC).astype(np.int32).reshape(-1, 1, 2)], False, 255, width, cv2.LINE_AA)
    return canvas.astype(np.float32) / 255.0


def ramp(w_mm=60.0, h_mm=30.0, px=0.2):
    w, h = int(w_mm / px), int(h_mm / px)
    return Field(np.tile(np.linspace(0.0, 0.9, w, dtype=np.float32), (h, 1)), w_mm, h_mm)


def biggest_jump(strokes, f):
    """Tông nhìn ở ~1 mm, so với mong muốn: chỗ nhảy lệch lớn nhất giữa hai cột cách 1 mm (ranh giới mức lộ rõ = lớn)."""
    got = cv2.GaussianBlur(ink(strokes, f.width_mm, f.height_mm), (0, 0), SC)[3 * SC:-3 * SC].mean(axis=0)[::SC]
    want = np.linspace(0.0, 0.9, len(got))
    return float(np.abs(np.diff(got) - np.diff(want))[3:-3].max())        # bỏ 3 mm hai mép (mép ảnh, chỗ quay đầu)


def test_dither_offsets_are_spread_evenly_and_neighbours_differ():
    off = hatch.dither_offsets(0.1)
    assert len(off) == hatch.DITHER_RANKS
    assert sorted(off) == pytest.approx(list(np.linspace(-0.0875, 0.0875, 8)))
    assert sum(off) == pytest.approx(0.0)
    assert all(abs(a - b) >= 0.04 for a, b in zip(off, off[1:]))          # hai dòng kề nhau lệch xa nhau


def test_soft_levels_is_the_default_and_can_be_turned_off():
    assert style().soft_levels is True
    f = ramp()
    soft = list(styles._passes(f, style(), PEN, None))
    hard = list(styles._passes(f, style(soft_levels=False), PEN, None))
    assert all(isinstance(m, list) and len(m) == 8 for m, _, _ in soft)
    assert all(isinstance(m, np.ndarray) for m, _, _ in hard)


@pytest.mark.parametrize("kind", ["zigzag", "wave"])
def test_soft_levels_smooth_the_steps_between_levels(kind):
    f = ramp()
    hard = biggest_jump(styles.fill(f, style(kind=kind, soft_levels=False), PEN), f)
    soft = biggest_jump(styles.fill(f, style(kind=kind), PEN), f)
    assert soft < 0.75 * hard, (soft, hard)


def test_soft_zigzag_still_joins_lines_into_long_strokes():
    f = ramp()
    strokes = styles.fill(f, style(kind="zigzag"), PEN)
    lengths = [float(np.hypot(*np.diff(np.asarray(s), axis=0).T).sum()) for s in strokes]
    assert np.median(lengths) > 15                                         # không vỡ thành từng đoạn dòng lẻ


def test_cross_split_keeps_the_total_tone():
    t = np.linspace(0.0, 1.0, 101, dtype=np.float32)
    a, b = styles.cross_split(t)
    total = 1 - (1 - a) * (1 - b)
    assert total == pytest.approx(np.minimum(t, styles.MAX_COVERAGE), abs=1e-5)
    assert (b[t <= styles.CROSS_START] == 0).all()                         # tông nhạt: chỉ một hướng
    assert a.max() < 0.75 and b.max() < 0.75                               # mỗi lớp thưa hơn một lớp đặc (0,9)


def test_crosshatch_adds_a_perpendicular_layer_only_in_dark_areas():
    light = Field(np.full((150, 150), 0.3, np.float32), 30.0, 30.0)
    dark = Field(np.full((150, 150), 0.9, np.float32), 30.0, 30.0)
    st = style(kind="crosshatch", angle=0)

    def directions(strokes):
        out = set()
        for s in strokes:
            for p, q in zip(s, s[1:]):
                dx, dy = q[0] - p[0], q[1] - p[1]
                if np.hypot(dx, dy) > 3:                                   # chỉ đoạn dài (bỏ chỗ quay đầu)
                    out.add("x" if abs(dx) > abs(dy) else "y")
        return out

    assert directions(styles.fill(light, st, PEN)) == {"x"}
    assert directions(styles.fill(dark, st, PEN)) == {"x", "y"}


@pytest.mark.parametrize("tone", [0.15, 0.3, 0.5, 0.8])
def test_wave_am_reproduces_flat_tones(tone):
    f = Field(np.full((200, 200), tone, np.float32), 40.0, 40.0)
    strokes = styles.fill(f, style(kind="wave_am"), PEN)
    got = float(ink(strokes, 40.0, 40.0)[5 * SC:-5 * SC, 5 * SC:-5 * SC].mean())
    assert got == pytest.approx(tone, abs=0.1)


def test_wave_am_is_smooth_with_few_pen_lifts_and_white_stays_white():
    f = ramp()
    strokes = styles.fill(f, style(kind="wave_am"), PEN)
    zig = styles.fill(f, style(kind="zigzag", soft_levels=False), PEN)
    assert biggest_jump(strokes, f) < 0.5 * biggest_jump(zig, f)
    assert len(strokes) < 40
    white = Field(np.zeros((100, 100), np.float32), 20.0, 20.0)
    assert styles.fill(white, style(kind="wave_am"), PEN) == []


def test_wave_am_lines_are_parallel_waves_inside_the_frame():
    f = Field(np.full((100, 200), 0.6, np.float32), 40.0, 20.0)
    strokes = styles.fill(f, style(kind="wave_am", angle=0), PEN)
    pts = np.concatenate([np.asarray(s) for s in strokes])
    assert pts[:, 0].min() >= 0 and pts[:, 0].max() <= 40 and pts[:, 1].min() >= 0 and pts[:, 1].max() <= 20
    line_w = styles.LINE_WIDTH_RATIO * PEN
    amp = styles.AM_AMPLITUDE * styles.AM_SPACING_LINES * line_w
    s0 = styles.AM_SPACING_LINES * line_w
    # mọi điểm (trừ chỗ quay đầu ở hai mép) nằm trong dải ±biên độ quanh đường của nó: các đường không lấn sang nhau
    pts = pts[(pts[:, 0] > 3) & (pts[:, 0] < 37)]
    v = pts[:, 1] - s0 / 2
    assert (np.abs(v - np.round(v / s0) * s0) <= amp + 1e-6).all()


def test_join_rows_turn_only_refuses_staircase_links():
    rows = [[np.array([[0.0, 0.0], [10.0, 0.0]])], [np.array([[10.2, 1.0], [20.0, 1.0]])]]
    assert len(hatch.join_rows(rows, 1.0)) == 1                            # nối chéo kiểu bậc thang được phép mặc định
    assert len(hatch.join_rows(rows, 1.0, turn_only=True)) == 2            # sóng: chỉ nối khi quay đầu
    back = [[np.array([[0.0, 0.0], [10.0, 0.0]])], [np.array([[3.0, 1.0], [10.1, 1.0]])]]
    [joined] = hatch.join_rows(back, 1.0, turn_only=True)                  # quay đầu: nửa vòng tròn rồi đi ngược lại
    assert joined[-1][0] == pytest.approx(3.0)
    assert joined[:, 0].max() == pytest.approx(10.05, abs=0.01)            # đỉnh vòng ở giữa hai đầu cũ, không lòi ra ngoài


def test_new_kinds_are_registered_and_accepted():
    for kind in ("crosshatch", "crosshatch3", "wave_am"):
        assert kind in spec.STYLES and kind in styles.FILLERS.names() and kind in styles.GROUPERS
        assert style(kind=kind).kind == kind


def test_cross3_split_keeps_total_coverage_and_adds_layers_in_turn():
    t = np.linspace(0.0, 0.9, 91, dtype=np.float32)
    a, b, c = styles.cross3_split(t)
    total = 1 - (1 - a) * (1 - b) * (1 - c)
    assert np.allclose(total, t, atol=1e-5)                                  # đúng độ phủ mong muốn
    assert (b[t <= styles.CROSS3_START2] == 0).all() and (c[t <= styles.CROSS3_START3] == 0).all()
    assert (np.diff(a) >= -1e-6).all() and (np.diff(b) >= -1e-6).all() and (np.diff(c) >= -1e-6).all()
    assert max(a.max(), b.max(), c.max()) < 0.7                              # mỗi hướng thưa hơn một lớp đặc (đỡ ướt giấy)


def test_crosshatch3_draws_three_directions_only_where_dark():
    f = ramp()
    strokes = styles.crosshatch3(f, style(kind="crosshatch3", angle=0), PEN)
    angles = set()
    for s in strokes:
        a = np.asarray(s)
        d = np.diff(a, axis=0)
        long = np.hypot(d[:, 0], d[:, 1]) > 3.0                             # bỏ đoạn quay đầu
        for dx, dy in d[long]:
            angles.add(int(round(np.degrees(np.arctan2(dy, dx)) % 180.0)) % 180)
    assert {0, 60, 120} <= angles
    light = [s for s in strokes if max(x for x, _ in s) < 0.3 * f.width_mm]   # phần nhạt của dải: chỉ một hướng
    for s in light:
        d = np.diff(np.asarray(s), axis=0)
        long = np.hypot(d[:, 0], d[:, 1]) > 3.0
        assert all(abs(dy) < 1e-6 for _, dy in d[long])

