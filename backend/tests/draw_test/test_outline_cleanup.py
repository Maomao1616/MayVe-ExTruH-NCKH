"""Viền nét đơn: cắt râu của nét dày, khép vòng kín."""
import cv2
import numpy as np

from app.services.drawing import edges, trace


def blank(h=60, w=100):
    return np.zeros((h, w), dtype=bool)


def test_prune_spurs_cuts_short_branch_but_keeps_long_lines_and_isolated_stubs():
    sk = blank()
    sk[30, 10:90] = True                       # đường dài nằm ngang
    sk[26:30, 50] = True                       # râu dài 4 điểm ảnh dính vào đường
    sk[5, 10:14] = True                        # nét rời ngắn: là nét thật, giữ
    out = edges.prune_spurs(sk, min_px=8)
    assert not out[26:30, 50].any()            # râu bị cắt
    assert out[30, 10:90].all()                # đường chính còn nguyên
    assert out[5, 10:14].all()                 # nét rời ngắn còn nguyên


def test_prune_spurs_keeps_branch_longer_than_limit():
    sk = blank()
    sk[30, 10:90] = True
    sk[10:30, 50] = True                       # nhánh 20 điểm ảnh > 8: là nét thật (chữ T)
    assert edges.prune_spurs(sk, min_px=8)[10:30, 50].all()


def test_crossing_number_marks_endpoints_and_junctions_not_staircase():
    sk = blank()
    for i in range(20):                        # đường chéo bậc thang
        sk[10 + i, 10 + i] = True
        sk[10 + i, 11 + i] = True
    cn = edges._crossing_number(sk)
    assert (cn[sk] == 2).sum() >= sk.sum() - 4  # giữa nét là 2, chỉ hai đầu khác
    sk[5:10, 30] = True
    sk[10, 25:36] = True
    assert (edges._crossing_number(sk)[10, 30]) >= 3


def test_outline_of_thick_letter_has_no_tiny_whiskers():
    g = np.full((120, 160), 245, np.uint8)
    cv2.putText(g, "T", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, 20, 9, cv2.LINE_AA)
    sk = edges.outline_mask(1.0 - g.astype(np.float32) / 255.0, None, 0.2, "medium")
    cn = edges._crossing_number(sk)
    ends = np.argwhere(sk & (cn == 1))
    junc = np.argwhere(sk & (cn >= 3))
    for e in ends:                              # mọi đầu mút cách ngã ba xa hơn giới hạn râu (1,6 mm = 8 điểm ảnh)
        assert len(junc) == 0 or np.min(np.hypot(*(junc - e).T)) > 6


def test_closed_loop_is_closed_by_to_strokes():
    from skimage.morphology import skeletonize
    img = np.zeros((40, 40), np.uint8)
    cv2.circle(img, (20, 20), 12, 1, 2)
    sk = skeletonize(img > 0)
    strokes = trace.to_strokes(sk, 0.2, 0.2, 1.0)
    ring = max(strokes, key=len)
    assert np.hypot(ring[0][0] - ring[-1][0], ring[0][1] - ring[-1][1]) < 0.05   # khép kín
