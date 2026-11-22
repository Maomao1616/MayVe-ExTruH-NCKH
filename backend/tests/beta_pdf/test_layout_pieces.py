"""Phần thuần của tab Beta không cần PDF thật: tham số, tiện ích nét, đường kẻ, xếp chữ (dùng đối tượng giả cho kết xuất)."""
import math

import numpy as np
import pytest

from app.services.beta_pdf import frame, options, pathing, text
from app.services.beta_pdf.reader import Char, PageContent, Segment
from app.services.drawing.errors import DrawError


# ---------- tham số ----------
def test_defaults_and_validation():
    o = options.parse(None)
    assert (o.page, o.text_mode, o.font, o.pen_mm, o.frame, o.images) == (1, "single", "script", 0.5, True, True)
    with pytest.raises(DrawError):
        options.parse({"bogus": 1})
    with pytest.raises(DrawError):
        options.parse({"text_mode": "magic"})
    with pytest.raises(DrawError):
        options.parse({"pen_mm": 9})
    with pytest.raises(DrawError):
        options.parse({"page": 1.5})
    with pytest.raises(DrawError):
        options.parse({"frame": "yes"})
    assert {p["name"] for p in options.describe()} == set(options.BY_NAME)


# ---------- nét ----------
def test_join_merges_touching_strokes_and_reverses_when_needed():
    out = pathing.join([[(0, 0), (1, 0)], [(1.1, 0), (2, 0)], [(3, 0), (2.1, 0)]], 0.25)
    assert len(out) == 1 and out[0][0] == (0, 0) and out[0][-1] == (3, 0)
    assert len(pathing.join([[(0, 0), (1, 0)], [(5, 0), (6, 0)]], 0.25)) == 2


def test_order_nearest_walks_to_the_closest_end_and_flips():
    out = pathing.order_nearest([[(10, 0), (11, 0)], [(0, 0), (1, 0)], [(5, 0), (4, 0)]], start=(0, 0))
    assert [s[0] for s in out] == [(0, 0), (4, 0), (10, 0)]    # nét giữa bị đảo chiều để vào từ đầu gần


def test_stats_counts_strokes_and_pen_up_travel():
    s = pathing.stats([[(0, 0), (3, 4)], [(3, 4), (3, 6)]])
    assert s["strokes"] == 2 and s["draw_mm"] == 7.0 and s["pen_up_mm"] == 0.0


# ---------- đường kẻ ----------
def seg(*pts, w=0.0, closed=False):
    return Segment(list(pts), w, closed)


def total(strokes):
    return sum(pathing.length(s) for s in strokes)


def test_duplicate_and_overlapping_lines_merge_into_one():
    o = options.parse(None)
    out = frame.build([seg((0, 10), (50, 10)), seg((0, 10.1), (50, 10.1)), seg((40, 10), (90, 10))], o)
    assert len(out) == 1 and total(out) == pytest.approx(90, abs=0.3)


def test_closed_rectangle_becomes_one_continuous_stroke_with_square_corners():
    o = options.parse(None)
    out = frame.build([seg((0, 0), (40, 0), (40, 20), (0, 20), closed=True)], o)
    assert len(out) == 1
    assert total(out) == pytest.approx(120, abs=0.6)
    for (x, y) in out[0]:                                      # mọi điểm nằm đúng trên chu vi
        assert x in (pytest.approx(0, abs=0.01), pytest.approx(40, abs=0.01)) or y in (pytest.approx(0, abs=0.01), pytest.approx(20, abs=0.01))


def test_grid_lines_are_chained_without_losing_any_length():
    o = options.parse(None)
    segs = [seg((0, y), (60, y)) for y in (0, 20, 40)] + [seg((x, 0), (x, 40)) for x in (0, 30, 60)]
    out = frame.build(segs, o)
    assert total(out) == pytest.approx(3 * 60 + 3 * 40, abs=1.0)
    assert len(out) < 6                                        # nối bớt: ít hơn 6 lần hạ bút


def test_thick_line_is_drawn_as_two_parallel_lines():
    o = options.parse({"pen_mm": 0.5})
    out = frame.build([seg((0, 10), (50, 10), w=2.0)], o)
    ys = sorted({round(s[0][1], 2) for s in out})
    assert len(out) == 2 and ys == [pytest.approx(9.25, abs=0.01), pytest.approx(10.75, abs=0.01)]
    assert len(frame.build([seg((0, 10), (50, 10), w=2.0)], options.parse({"thick_double": False})) ) == 1


# ---------- xếp chữ ----------
def ch(c, x0, x1, base=20.0, size=5.0, line=1, bold=False, italic=False):
    return Char(c, x0, x1, base, size, bold, italic, line)


def test_glyph_is_centred_in_its_cell_and_squeezed_when_the_cell_is_narrow():
    strokes = text.glyph_strokes(ch("m", 10.0, 12.0), 0.92, "simplex")
    xs = [x for s in strokes for x, _ in s]
    assert min(xs) >= 10.0 - 0.01 and max(xs) <= 12.0 + 0.01      # không tràn ô chữ
    assert (min(xs) + max(xs)) / 2 == pytest.approx(11.0, abs=0.05)
    assert text.glyph_strokes(ch(" ", 0, 1), 0.92) == []
    assert text.glyph_strokes(ch("中", 0, 1), 0.92) is None


def test_word_letters_are_evenly_spaced_and_the_word_fits_its_pdf_span():
    # ba chữ o giống hệt nhau nhưng ô chữ trong PDF lệch nhau (như kerning / căn đều): nhịp chữ vẫn phải đều
    chars = [ch("o", 10.0, 13.0), ch("o", 13.0, 15.0), ch("o", 15.0, 20.0)]
    strokes = text.word_strokes(chars, "simplex")
    per = len(strokes) // 3
    centres = [sum(x for s in strokes[i * per:(i + 1) * per] for x, _ in s) / sum(len(s) for s in strokes[i * per:(i + 1) * per]) for i in range(3)]
    assert centres[1] - centres[0] == pytest.approx(centres[2] - centres[1], abs=0.05)
    xs = [x for s in strokes for x, _ in s]
    assert min(xs) >= 10.0 - 0.6 and max(xs) <= 20.0 + 0.6        # nằm trong khoảng từ ký tự đầu tới ký tự cuối (+ nửa độ hở của glyph)


def test_word_scale_is_uniform_so_wider_pdf_words_get_wider_letters():
    narrow = text.word_strokes([ch("n", 0, 2.5), ch("a", 2.5, 5.0)], "simplex")
    wide = text.word_strokes([ch("n", 0, 5.0), ch("a", 5.0, 10.0)], "simplex")
    width = lambda st: max(x for s in st for x, _ in s) - min(x for s in st for x, _ in s)
    assert width(wide) > width(narrow) * 1.3


def test_a_word_with_an_unknown_character_keeps_the_rest_as_a_word():
    content = PageContent(100, 100, chars=[ch("a", 10, 14), ch("中", 14, 19), ch("b", 19, 23)])
    strokes, st = text.build(content, options.parse({"font": "simplex"}), None)
    assert st["single"] == 2 and st["missing"] == 1 and strokes


def test_glyph_height_follows_the_font_size():
    small = text.glyph_strokes(ch("H", 0, 4, size=4.0), 0.92, "simplex")
    big = text.glyph_strokes(ch("H", 0, 8, size=8.0), 0.92, "simplex")
    h = lambda st: max(y for s in st for _, y in s) - min(y for s in st for _, y in s)
    assert h(big) == pytest.approx(2 * h(small), rel=0.02)
    assert h(small) == pytest.approx(4.0 * 0.662, rel=0.05)    # chiều cao chữ hoa ≈ 0,662 cỡ chữ (Times)


def test_lines_are_grouped_by_baseline_and_sorted_left_to_right():
    chars = [ch("b", 10, 15, 40.0), ch("a", 0, 5, 40.1), ch("c", 0, 5, 20.0)]
    lines = text.group_lines(chars)
    assert [[c.ch for c in line] for line in lines] == [["c"], ["a", "b"]]


def test_runs_split_at_wide_gaps_between_table_cells():
    line = [ch("a", 0, 3), ch("b", 3, 6), ch("c", 60, 63)]
    assert [[c.ch for c in r] for r in text.split_runs(line)] == [["a", "b"], ["c"]]


def test_unknown_characters_are_counted_when_there_is_no_document_for_the_fallback():
    content = PageContent(100, 100, chars=[ch("a", 10, 14), ch("中", 14, 19)])
    strokes, st = text.build(content, options.parse({"font": "simplex"}), None)
    assert strokes and st["single"] == 1 and st["missing"] == 1 and "中" in st["missing_sample"]


class FakeDoc:
    """Kết xuất giả: một thanh đen ngang giữa vùng cắt, để thử đường skeleton không cần PDF."""
    def render_gray(self, index, bbox, dpi):
        w = max(2, int((bbox[2] - bbox[0]) / 25.4 * dpi))
        h = max(2, int((bbox[3] - bbox[1]) / 25.4 * dpi))
        img = np.full((h, w), 255, np.uint8)
        img[h // 2 - 2:h // 2 + 3, 5:w - 5] = 0
        return img


def test_skeleton_mode_traces_the_rendered_ink_into_strokes():
    content = PageContent(100, 100, chars=[ch("a", 10, 14), ch("b", 14, 18)])
    strokes, st = text.build(content, options.parse({"text_mode": "skeleton"}), FakeDoc(), 0)
    assert st["skeleton"] == 2 and st["single"] == 0 and len(strokes) >= 1
    xs = [x for s in strokes for x, _ in s]
    assert min(xs) >= 9.0 and max(xs) <= 19.5                  # nằm đúng vùng chữ trên trang


def test_mixed_mode_sends_only_large_characters_to_skeleton():
    big = ch("H", 10, 16, size=7.5)                            # 7,5 mm ≈ 21 pt
    small = ch("a", 17, 20, size=4.5)                          # ≈ 13 pt
    content = PageContent(100, 100, chars=[big, small])
    _, st = text.build(content, options.parse({"text_mode": "mixed"}), FakeDoc(), 0)
    assert st["skeleton"] == 1 and st["single"] == 1


# ---------- nhận diện ảnh (images.classify) ----------
def test_classify_tells_line_drawings_from_photos():
    from app.services.beta_pdf import images
    white = np.full((60, 100), 255, np.uint8)
    white[30, 10:90] = 0                                             # một nét mảnh trên nền trắng
    assert images.classify(white) == "lineart"
    gradient = np.tile(np.linspace(255, 0, 100, dtype=np.uint8), (60, 1))
    assert images.classify(gradient) == "photo"                      # nhiều xám trung gian
    dark = np.full((60, 100), 40, np.uint8)
    assert images.classify(dark) == "photo"
    assert images.classify(np.zeros((0, 0), np.uint8)) == "photo"
    greek = np.full((40, 40), 255, np.uint8)                         # ký hiệu nhỏ đậm hơn: trắng ~0,78, xám 0,15
    greek[0:6, :] = 120
    greek[6:12, 0:20] = 0
    assert images.classify(greek) == "lineart"


def test_image_kind_and_lineart_option_are_validated():
    assert options.parse(None).image_kind == "auto" and options.parse(None).lineart_with_text is True
    assert options.parse({"image_kind": "lineart", "lineart_with_text": False}).lineart_with_text is False
    with pytest.raises(DrawError):
        options.parse({"image_kind": "magic"})
