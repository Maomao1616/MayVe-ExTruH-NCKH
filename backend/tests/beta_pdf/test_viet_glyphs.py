"""Ghép chữ tiếng Việt nét đơn (beta_pdf/viet.py + fontdata.py): đủ chữ, dấu đúng chỗ, ì í ỉ ĩ bỏ chấm, dấu nặng dưới chân."""
import pytest

from app.services.beta_pdf import fontdata, viet

LOWER = "aăâeêioôơuưyđ" "áàảãạ" "ắằẳẵặ" "ấầẩẫậ" "éèẻẽẹ" "ếềểễệ" "íìỉĩị" "óòỏõọ" "ốồổỗộ" "ớờởỡợ" "úùủũụ" "ứừửữự" "ýỳỷỹỵ"
UPPER = LOWER.upper().replace("Đ", "Đ")


def ys(glyph):
    return [y for s in glyph.strokes for _, y in s]


def xs(glyph):
    return [x for s in glyph.strokes for x, _ in s]


@pytest.mark.parametrize("family", ["times", "simplex", "script"])
@pytest.mark.parametrize("bold,italic", [(False, False), (True, False), (False, True), (True, True)])
def test_every_vietnamese_letter_can_be_built(family, bold, italic):
    for ch in LOWER + UPPER:
        g = viet.build(ch, bold, italic, family)
        assert g is not None and g.strokes, ch


def test_ascii_digits_and_punctuation_come_straight_from_the_font():
    for ch in "0123456789.,:;!?()-/\"'":
        assert viet.build(ch).strokes, ch
    assert viet.build(" ").strokes == ()                      # dấu cách không có nét


def test_decompose_splits_letter_modifier_and_tone():
    assert viet.decompose("ế") == ("e", "circ", "acute")
    assert viet.decompose("ặ") == ("a", "breve", "dot")
    assert viet.decompose("ữ") == ("u", "horn", "tilde")
    assert viet.decompose("đ") == ("d", "stroke", None)
    assert viet.decompose("Đ") == ("D", "stroke", None)
    assert viet.decompose("q") == ("q", None, None)
    assert viet.decompose("ü") is None                        # diaeresis: không phải dấu tiếng Việt
    assert viet.decompose("中") is None


def test_tone_marks_sit_above_the_letter_and_dot_below_the_foot():
    plain = viet.build("a")
    assert min(ys(viet.build("á"))) < min(ys(plain)) - 1.0     # dấu sắc nằm trên đỉnh chữ
    assert max(ys(viet.build("ạ"))) > max(ys(plain)) + 1.0     # dấu nặng nằm dưới chân
    top_circ = min(ys(viet.build("â")))
    assert min(ys(viet.build("ấ"))) < top_circ - 1.0           # dấu thanh nằm TRÊN dấu mũ


def test_circumflex_tone_marks_lean_away_from_the_hat():
    centre = sum(xs(viet.build("a"))) / len(xs(viet.build("a")))
    acute = [x for s in viet.build("ấ").strokes[-1:] for x, _ in s]
    grave = [x for s in viet.build("ầ").strokes[-1:] for x, _ in s]
    assert sum(acute) / len(acute) > centre + 1.0              # sắc lệch phải
    assert sum(grave) / len(grave) < centre - 1.0              # huyền lệch trái


def test_i_with_a_tone_loses_its_dot_but_i_with_dot_below_keeps_it():
    n_i = len(viet.build("i").strokes)
    assert len(viet.build("ì").strokes) == n_i                 # bỏ chấm, thêm dấu huyền
    assert len(viet.build("ị").strokes) == n_i + 1             # giữ chấm, thêm chấm dưới chân


def test_stroke_through_d_and_horn_extend_the_glyph():
    d, dd = viet.build("d"), viet.build("đ")
    assert len(dd.strokes) == len(d.strokes) + 1
    assert max(xs(viet.build("ơ"))) > max(xs(viet.build("o"))) + 1.0     # râu nhô ra bên phải


def test_italic_shifts_marks_right_like_the_slanted_letter():
    upright = viet.build("á", False, False, "simplex")
    slanted = viet.build("á", False, True, "simplex")
    assert max(xs(slanted)) > max(xs(upright))


def test_font_dimensions_match_the_documented_constants():
    h = fontdata.glyph(False, False, "H")
    x = fontdata.glyph(False, False, "x")
    assert -min(ys(h)) == pytest.approx(fontdata.CAP_HEIGHT, abs=0.5)
    assert -min(ys(x)) == pytest.approx(fontdata.X_HEIGHT, abs=0.5)
