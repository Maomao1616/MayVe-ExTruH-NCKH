"""Ghép chữ tiếng Việt từ chữ Latin nét đơn: chữ gốc + dấu mũ / trăng / râu / gạch đ + dấu thanh.

Font nét đơn (fontdata.py) chỉ có ASCII, nên mỗi chữ như ấ, ặ, ữ, Đ được dựng từ:
  chữ gốc (a, e, i, o, u, y, d)  +  dấu phụ (mũ ^, trăng ˘, râu ơ ư, gạch ngang đ)  +  dấu thanh (sắc, huyền, hỏi, ngã, nặng).
Quy ước vị trí theo cách viết tay / sắp chữ tiếng Việt:
  - dấu mũ, trăng nằm ngay trên chữ; dấu thanh đặt TRÊN dấu đó (ắ ằ ẳ ẵ), riêng với dấu mũ thì lệch sang phải (sắc, hỏi) hoặc trái
    (huyền) và nhích lên (ấ ầ ẩ ẫ);
  - dấu nặng nằm dưới chân chữ; ị giữ chấm trên đầu i, còn ì í ỉ ĩ bỏ chấm đó để dấu thanh thay chỗ.
Mọi kích thước tính bằng đơn vị Hershey (chiều cao chữ thường 14, chữ hoa 21), hằng số HOA bên dưới chỉnh được.
"""
from __future__ import annotations

import math
import unicodedata

from . import fontdata
from .fontdata import Glyph

TONES = {"̀": "grave", "́": "acute", "̉": "hook", "̃": "tilde", "̣": "dot"}
MODS = {"̂": "circ", "̆": "breve", "̛": "horn"}
ABOVE_TONES = ("grave", "acute", "hook", "tilde")

SLANT = 0.2                      # độ nghiêng của font nghiêng: dấu phải dịch theo cùng độ nghiêng
MARK_LEVEL1 = 3.2                # tâm dấu mũ / trăng cách đỉnh chữ (đơn vị Hershey)
TONE_PLAIN = {"acute": (0.8, 3.8), "grave": (-0.8, 3.8), "hook": (0.0, 4.8), "tilde": (0.0, 4.0)}      # (lệch x, cao) trên chữ thường
TONE_CIRC = {"acute": (3.6, 6.2), "grave": (-3.6, 6.2), "hook": (0.4, 7.4), "tilde": (0.0, 7.2)}       # trên dấu mũ: ấ ầ ẩ ẫ
TONE_BREVE = {"acute": (0.6, 6.6), "grave": (-0.6, 6.6), "hook": (0.0, 7.4), "tilde": (0.0, 7.0)}     # trên dấu trăng: ắ ằ ẳ ẵ
DOT_BELOW = 3.2                  # tâm dấu nặng cách chân chữ
TITTLE_CLEAR = 1.0               # nét nằm hẳn trên đỉnh chữ i cao hơn mức này là chấm của i
HORN = ((-1.2, 2.0), (1.2, 0.4), (2.2, -2.0))          # râu ơ ư: điểm so với (mép phải chữ, đỉnh chữ)
HORN_EXTRA = 2.0                # râu nhô ra bên phải: ô chữ rộng thêm chừng này
D_BAR = (0.786, -6.5, 1.2)       # gạch đ: (độ cao = tỷ lệ × chiều cao nét đứng của d: 16,5 / 21 ở Times, từ xmax+…, đến xmax+…)
# gạch Đ nằm giữa chiều cao chữ hoa (tính theo từng họ font)


def _tilde():
    return [(-3.0 + 6.0 * i / 8, -1.0 * math.sin(2 * math.pi * i / 8)) for i in range(9)]


MARKS = {                         # hình dấu, tâm ở (0, 0), y xuống
    "acute": [[(-1.6, 1.6), (1.6, -1.8)]],
    "grave": [[(-1.6, -1.8), (1.6, 1.6)]],
    "hook": [[(-1.4, -1.6), (-0.6, -2.3), (0.6, -2.3), (1.3, -1.4), (1.1, -0.4), (0.0, 0.4), (0.0, 1.6)]],
    "tilde": [_tilde()],
    "circ": [[(-2.6, 1.3), (0.0, -1.5), (2.6, 1.3)]],
    "breve": [[(-2.6, -1.0), (-1.6, 0.5), (0.0, 1.2), (1.6, 0.5), (2.6, -1.0)]],
    "dot": [[(0.0, -0.4), (0.0, 0.4)]],
}


def decompose(ch: str):
    """(chữ gốc ASCII, dấu phụ hoặc None, dấu thanh hoặc None); None nếu không ghép được (dấu lạ, chữ không Latin)."""
    if ch == "đ":
        return "d", "stroke", None
    if ch == "Đ":
        return "D", "stroke", None
    parts = unicodedata.normalize("NFD", ch)
    base, marks = parts[0], parts[1:]
    if not (base.isascii() and base.isalpha()):
        return None
    mod = tone = None
    for m in marks:
        if m in MODS and mod is None:
            mod = MODS[m]
        elif m in TONES and tone is None:
            tone = TONES[m]
        else:
            return None
    return base, mod, tone


def _shift(strokes, dx_of_y, dx=0.0, dy=0.0):
    return [[(x + dx + dx_of_y(y + dy), y + dy) for x, y in s] for s in strokes]


def build(ch: str, bold: bool = False, italic: bool = False, family: str = "times") -> Glyph | None:
    """Glyph của ký tự (ASCII hoặc chữ Việt); None nếu chưa có (người gọi dùng đường dự phòng)."""
    if len(ch) == 1 and 32 <= ord(ch) < 127:                     # chữ không dấu, chữ số, dấu câu: lấy thẳng từ font
        return fontdata.glyph(bold, italic, ch, family)
    parts = decompose(ch)
    if parts is None:
        return None
    base, mod, tone = parts
    g = fontdata.glyph(bold, italic, base, family)
    if g is None:
        return None
    if mod is None and tone is None:
        return g
    strokes = [list(s) for s in g.strokes]
    xs = [x for s in strokes for x, _ in s]
    ys = [y for s in strokes for _, y in s]
    xmin, xmax, bottom = min(xs), max(xs), max(max(ys), 0.0)
    cx = (xmin + xmax) / 2
    m = fontdata.metrics(family)
    top = -(m.cap_height if base.isupper() else m.x_height)
    slant = SLANT if italic and family != "script" else 0.0      # font viết tay chỉ có một kiểu: không xô dấu
    follow = lambda y: -(y - top / 2) * slant                  # dấu ở càng cao càng lệch phải theo độ nghiêng

    if base == "i" and tone in ABOVE_TONES:                      # ì í ỉ ĩ: bỏ chấm của i
        strokes = [s for s in strokes if max(y for _, y in s) >= top - TITTLE_CLEAR]

    out = strokes
    n_base = len(strokes)                                        # các nét thêm sau đây là dấu
    n_join = 1 if mod in ("stroke", "horn") else 0                # gạch đ và râu dính vào chữ, các dấu khác rời
    if mod == "stroke":
        if base == "d":
            y = -D_BAR[0] * m.ascender
            out.append(_shift([[(xmax + D_BAR[1], y), (xmax + D_BAR[2], y)]], follow)[0])
        else:
            y = -m.cap_height / 2
            out.append(_shift([[(xmin - 2.5, y), (xmin + 6.0, y)]], follow)[0])
    elif mod == "horn":
        pts = [(xmax + dx, top + dy) for dx, dy in HORN]
        out.append(_shift([pts], follow)[0])
    elif mod in ("circ", "breve"):
        out += _shift(MARKS[mod], follow, cx, top - MARK_LEVEL1)
    if tone == "dot":
        out += _shift(MARKS["dot"], follow, cx, bottom + DOT_BELOW)
    elif tone:
        table = TONE_CIRC if mod == "circ" else TONE_BREVE if mod == "breve" else TONE_PLAIN
        dx, up = table[tone]
        out += _shift(MARKS[tone], follow, cx + dx, top - up)
    return Glyph(tuple(tuple(s) for s in out), g.lt, g.rt + (HORN_EXTRA if mod == "horn" else 0.0), n_base, n_join, g.solo)
