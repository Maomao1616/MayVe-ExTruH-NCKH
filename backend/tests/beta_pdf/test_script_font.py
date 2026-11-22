"""Font chữ viết tay nối nét (family "script"): cả từ là một nét liền, chấm / dấu viết sau, đậm nghiêng bị bỏ, kích thước đo từ glyph."""
import pytest

from app.services.beta_pdf import fontdata, pathing, text
from app.services.beta_pdf.reader import Char


def ch(c, x0, x1, bold=False, italic=False, size=5.0):
    return Char(c, x0, x1, 20.0, size, bold, italic, 1)


def test_a_script_word_is_written_as_one_continuous_stroke():
    strokes = text.word_strokes([ch("m", 0, 4), ch("o", 4, 7), ch("n", 7, 11)], "script")
    total = sum(pathing.length(s) for s in strokes)
    assert len(strokes) <= 2
    assert max(pathing.length(s) for s in strokes) > 0.8 * total        # gần như toàn bộ nằm trong một nét
    simplex = text.word_strokes([ch("m", 0, 4), ch("o", 4, 7), ch("n", 7, 11)], "simplex")
    assert len(simplex) > len(strokes)                                   # chữ rời thì nhiều nét hơn


def test_dots_and_vietnamese_marks_are_written_after_the_word():
    plain = text.word_strokes([ch("n", 0, 4), ch("i", 4, 6)], "script")
    assert len(plain) == 2 and pathing.length(plain[0]) > pathing.length(plain[1])    # nét liền trước, chấm của i sau
    marked = text.word_strokes([ch("n", 0, 4), ch("ế", 4, 8)], "script")
    body, extras = marked[0], marked[1:]
    assert extras                                                        # dấu mũ và dấu sắc là nét riêng
    assert min(y for s in extras for _, y in s) < min(y for _, y in body) - 0.3      # nằm trên đỉnh chữ
    assert all(pathing.length(s) > 0 for s in marked)


def test_script_font_ignores_bold_and_italic_only_the_size_differs():
    a = text.word_strokes([ch("t", 0, 3), ch("o", 3, 6)], "script")
    b = text.word_strokes([ch("t", 0, 3, bold=True, italic=True), ch("o", 3, 6, bold=True, italic=True)], "script")
    assert a == b
    small = text.word_strokes([ch("t", 0, 3, size=4.0), ch("o", 3, 6, size=4.0)], "script")
    big = text.word_strokes([ch("t", 0, 3, size=8.0), ch("o", 3, 6, size=8.0)], "script")
    h = lambda st: max(y for s in st for _, y in s) - min(y for s in st for _, y in s)
    assert h(big) == pytest.approx(2 * h(small), rel=0.05)


def test_script_metrics_are_measured_from_its_own_glyphs():
    m = fontdata.metrics("script")
    assert m.x_height == pytest.approx(9 * 1.1, abs=0.3)               # chữ thường của font viết tay thấp hơn Times (14)
    assert m.cap_height > m.x_height and m.ascender > m.x_height
    t = fontdata.metrics("times")
    assert (t.x_height, t.cap_height, t.ascender) == pytest.approx((14, 21, 21), abs=0.5)


def test_a_dot_stroke_is_never_zero_length():
    strokes = text.word_strokes([ch("i", 0, 3)], "script")
    assert all(pathing.length(s) > 0 for s in strokes)


def test_capitals_and_digits_are_written_as_separate_print_letters():
    height = lambda st: max(y for s in st for _, y in s) - min(y for s in st for _, y in s)
    cap = text.word_strokes([ch("N", 0, 5)], "script")
    low = text.word_strokes([ch("n", 0, 4)], "script")
    assert 1.5 < height(cap) / height(low) < 2.4                          # chữ hoa kiểu in cao ~1,9 lần chữ thường viết tay
    assert len(text.word_strokes([ch("S", 0, 4), ch("S", 4, 8)], "script")) >= 2        # hai chữ in không dính thành một nét
    word = text.word_strokes([ch("A", 0, 4), ch("b", 4, 7), ch("a", 7, 10)], "script")
    assert len(word) >= 3                                                 # chữ A in (nhiều nét) rồi "ba" liền một nét
    digits = text.word_strokes([ch("1", 0, 3), ch("2", 3, 6)], "script")
    assert len(digits) >= 2
    assert fontdata.glyph(False, False, "S", "script").solo and not fontdata.glyph(False, False, "s", "script").solo


def test_vietnamese_capital_keeps_its_marks_at_the_print_cap_height():
    m = fontdata.metrics("script")
    assert m.cap_height == pytest.approx(21 * fontdata.PRINT_SCALE, abs=0.3)          # đo từ chính chữ H in
    strokes = text.word_strokes([ch("Ê", 0, 5)], "script")
    assert min(y for s in strokes for _, y in s) < -m.cap_height * (5.0 / fontdata.EM_UNITS) + 20.0 - 0.01          # dấu mũ nằm trên đỉnh chữ hoa
