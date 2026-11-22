"""Chữ trong trang -> nét vẽ. Hai cách, chọn bằng `text_mode`:

1. "single" (nét đơn, khuyên dùng): vẽ LẠI chữ bằng font nét đơn (fontdata.py + viet.py), đặt đúng vị trí, cỡ, đậm / nghiêng mà Word đã
   dàn trang (đọc từ PDF). Đặt THEO TỪ: chữ cái trong một từ cách nhau đều theo nhịp riêng của font nét đơn, rồi cả từ được co / giãn
   ĐỀU cho vừa bề rộng từ trong PDF (dòng căn đều hai bên vẫn đúng). Không co từng chữ theo ô chữ của Times, vì như vậy chữ này rộng
   chữ kia hẹp, nhìn "run". Nét ít, sạch, dấu tiếng Việt rõ; ký tự lạ (công thức, ký hiệu) rơi về cách 2 cho riêng ký tự đó.
2. "skeleton": kết xuất vùng chữ thành ảnh, nhị phân hóa, làm mảnh (skeleton) lấy đường giữa nét rồi dò nét (`drawing/trace.py`). Giữ đúng
   hình chữ gốc nhưng với chữ Times nhỏ (< 17 pt) chân chữ sinh râu, nét mảnh đứt, dấu thanh dính: hợp tiêu đề lớn.
   "mixed" = chữ từ `mixed_min_pt` trở lên đi cách 2, còn lại cách 1.
Thứ tự vẽ: từng dòng từ trên xuống, trong dòng từ trái sang phải, rồi nối các nét kề nhau (pathing.join) để bớt nhấc bút.
"""
from __future__ import annotations

import dataclasses
import math
from functools import lru_cache

from ..drawing import trace
from . import fontdata, pathing, viet
from .reader import PT_MM, Char

FIT_MIN = 0.55                   # co ngang tối đa của một chữ đứng riêng (gạch dài, ký tự lẻ)
WORD_FIT_MIN = 0.55              # một từ co tối đa mức này so với nhịp tự nhiên của font nét đơn
WORD_FIT_MAX = 1.25              # ... và giãn tối đa mức này (từ có kerning rộng hoặc font Times đậm)
CONNECT_UNITS = 10.0             # font viết tay: đuôi một thân chữ cách đầu thân chữ kế ≤ mức này (đơn vị Hershey) thì nối liền bằng đoạn thẳng
BODY_TOL = 1.6                   # nét nối tiếp thân chữ: đầu cách cuối thân ≤ mức này (đơn vị Hershey) thì gộp vào thân
DOT_MIN = 0.5                    # nét phụ ngắn hơn mức này (chấm của i) kéo thành đoạn ngắn để bút chấm được
ATTACH_TOL = 6.5                 # nét phụ của chữ cái (vòm của n, m, h; đuôi của d, g, p, q…) có một đầu cách thân ≤ mức này thì nối vào thân
ATTACH_MIN_LEN = 5.0             # ... nhưng nét phụ ngắn hơn mức này (chấm của i, j dài 3,9; gạch ngang của t dài 6,0 thì nối) vẫn để riêng
LINE_TOL = 0.45                  # hai ký tự cùng dòng nếu đường cơ sở lệch không quá mức này × cỡ chữ
RUN_GAP_EM = 1.5                 # khoảng trống rộng hơn mức này × cỡ chữ cắt dòng thành các đoạn (ô bảng khác nhau)
SKEL_PAD_MM = 0.4                # lề thêm quanh vùng cắt để làm skeleton
SKEL_ASCENT = 0.95               # vùng cắt quanh đường cơ sở: lên 0,95 em, xuống 0,32 em
SKEL_DESCENT = 0.32
SKEL_MIN_LEN_MM = 0.3            # bỏ nét skeleton ngắn hơn mức này (râu, bụi)
BLUR_THRESHOLD_DROP = 20         # hạ ngưỡng mực khi có làm mịn (nét mảnh bị nhạt đi)
STRETCH = "–—−"   # gạch ngang dài: kéo giãn cho vừa ô chữ

# Ký tự Unicode thường gặp trong Word -> ASCII mà font nét đơn có. Giá trị nhiều ký tự thì chia đều bề rộng.
CHAR_MAP = {
    "‘": "'", "’": "'", "‚": ",", "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-",
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    "…": "...", "·": ".", "•": "*", "×": "x", "÷": "/", "⁄": "/",
}


def expand(c: Char) -> list[Char]:
    """Chuẩn hóa ký tự (ngoặc cong, gạch dài, …); một ký tự thành nhiều thì chia đều hộp."""
    s = CHAR_MAP.get(c.ch, c.ch)
    if len(s) == 1:
        return [dataclasses.replace(c, ch=s, line=c.line)] if s != c.ch else [c]
    n = len(s)
    w = c.x1 - c.x0
    return [dataclasses.replace(c, ch=one, x0=c.x0 + w * i / n, x1=c.x0 + w * (i + 1) / n) for i, one in enumerate(s)]


@lru_cache(maxsize=4096)
def _glyph(ch: str, bold: bool, italic: bool, family: str):
    return viet.build(ch, bold, italic, family)


def glyph_strokes(c: Char, fit: float, family: str = "times"):
    """Nét (mm, tọa độ trang) của MỘT ký tự đặt vào ô chữ của nó (căn giữa, co ngang nếu rộng hơn ô); [] cho dấu cách; None nếu font
    chưa có (đi đường dự phòng). Dùng cho gạch dài và ký tự đứng riêng; chữ trong từ đi qua `word_strokes`."""
    g = _glyph(c.ch, c.bold, c.italic, family)
    if g is None:
        return None
    if not g.strokes:
        return []
    unit = c.size_mm / fontdata.EM_UNITS                       # mm mỗi đơn vị Hershey
    xs = [x for s in g.strokes for x, _ in s]
    xmin, xmax = min(xs), max(xs)
    body, adv = (xmax - xmin) * unit, c.x1 - c.x0
    sx = 1.0
    if body > 0 and adv > 0:
        if c.ch in STRETCH:
            sx = adv * fit / body                              # gạch dài: kéo cho kín ô
        elif body > adv * fit:
            sx = max(FIT_MIN, adv * fit / body)                # chữ rộng hơn ô: co lại
    cx_glyph, cx_cell = (xmin + xmax) / 2, (c.x0 + c.x1) / 2
    return [[(cx_cell + (x - cx_glyph) * unit * sx, c.baseline + y * unit) for x, y in s] for s in g.strokes]


def _nearest_on(poly, p):
    """(khoảng cách, chỉ số đoạn, điểm gần nhất) từ p tới đường gấp khúc poly."""
    best = (float("inf"), 0, poly[0])
    for i in range(len(poly) - 1):
        a, b = poly[i], poly[i + 1]
        abx, aby = b[0] - a[0], b[1] - a[1]
        denom = abx * abx + aby * aby
        t = 0.0 if denom == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / denom))
        q = (a[0] + t * abx, a[1] + t * aby)
        d = math.dist(p, q)
        if d < best[0]:
            best = (d, i, q)
    return best


def _attach_side_strokes(body, leftovers, forced=()):
    """Nối các nét phụ của chữ cái (vòm, đuôi) và râu / gạch đ vào thân bằng một chuyến "đi ra rồi quay lại" tại điểm chạm: pen không nhấc,
    đầu và cuối thân giữ nguyên (để còn nối sang chữ kế), mực chồng đúng lên nét cũ. `forced` = các nét (theo chỉ số trong leftovers) luôn
    thử nối dù ngắn. Trả (thân mới, nét còn lại)."""
    rest = list(leftovers)
    force_ids = {id(leftovers[i]) for i in forced}
    progress = True
    while progress:
        progress = False
        for orig in list(rest):
            e = orig
            if pathing.length(e) < ATTACH_MIN_LEN and id(orig) not in force_ids:
                continue
            ds, i_s, q_s = _nearest_on(body, e[0])
            de, i_e, q_e = _nearest_on(body, e[-1])
            if min(ds, de) > ATTACH_TOL:
                continue
            if de < ds:
                e, i, q = e[::-1], i_e, q_e                        # đầu gần thân nhất đi trước
            else:
                i, q = i_s, q_s
            body = body[:i + 1] + [q] + e + e[-2::-1] + [q] + body[i + 1:]
            rest.remove(orig)
            progress = True
            break
    return body, rest


def _split_body(strokes, n_base: int, n_join: int = 0):
    """(thân, nét phụ) của một glyph. Thân = nét dài nhất cộng các nét nối tiếp nó (đầu / cuối chạm nhau) và các nét phụ của chữ cái sát
    thân (`_attach_side_strokes`); nét phụ còn lại = chấm của i, gạch ngang của t, dấu thanh, dấu mũ… Nét phụ được viết SAU khi xong cả từ,
    như người viết tay."""
    base = [list(s) for s in (strokes if n_base < 0 else strokes[:n_base])]
    marks = [] if n_base < 0 else [list(s) for s in strokes[n_base:]]
    joinable, extras = marks[:n_join], marks[n_join:]
    if not base:
        return [], joinable + extras
    body = base.pop(max(range(len(base)), key=lambda i: pathing.length(base[i])))
    changed = True
    while changed and base:
        changed = False
        for s in list(base):
            if math.dist(body[-1], s[0]) <= BODY_TOL:
                body = body + s[1:]
            elif math.dist(s[-1], body[0]) <= BODY_TOL:
                body = s[:-1] + body
            elif math.dist(body[-1], s[-1]) <= BODY_TOL:
                body = body + s[::-1][1:]
            else:
                continue
            base.remove(s)
            changed = True
    candidates = base + joinable
    body, rest = _attach_side_strokes(body, candidates, forced=range(len(base), len(candidates)))
    return body, rest + extras


def _connected_word(chars, glyphs, units, s: float) -> list:
    """Font viết tay: nối thân các chữ cái trong từ thành MỘT nét liền (đoạn thẳng nối khi đuôi và đầu cách nhau ≤ CONNECT_UNITS), rồi viết
    các nét phụ (chấm, gạch ngang, dấu) sau cùng."""
    chains: list = []
    chain: list = []
    extras: list = []
    x = chars[0].x0
    for g, c, u in zip(glyphs, chars, units):
        origin = x - g.lt * u * s

        def place(stroke):
            return [(origin + gx * u * s, c.baseline + gy * u) for gx, gy in stroke]

        if g.solo:                                             # chữ in (hoa, số): các nét đứng riêng, ngắt nối với chữ trước và sau
            if chain:
                chains.append(chain)
                chain = []
            base = g.strokes if g.n_base < 0 else g.strokes[:g.n_base]
            marks = [] if g.n_base < 0 else g.strokes[g.n_base:]
            chains += [place(list(s)) for s in base]
            extras += [place(list(m)) for m in marks]
            x += (g.rt - g.lt) * u * s
            continue
        body, extra = _split_body(g.strokes, g.n_base, g.n_join)
        for e in extra:
            if pathing.length(e) < DOT_MIN:                    # chấm: kéo thành đoạn ngắn để bút chạm giấy
                cx, cy = e[0]
                e = [(cx - DOT_MIN / 2, cy), (cx + DOT_MIN / 2, cy)]
            extras.append(place(e))
        if body:
            pts = place(body)
            if chain and math.dist(chain[-1], pts[0]) <= CONNECT_UNITS * u * s:
                chain.extend(pts)
            else:
                if chain:
                    chains.append(chain)
                chain = list(pts)
        x += (g.rt - g.lt) * u * s
    if chain:
        chains.append(chain)
    return chains + extras


def word_strokes(chars, family: str = "simplex") -> list:
    """Nét (mm) của một TỪ (các ký tự liền nhau, không dấu cách, font nào cũng có glyph). Chữ cái cách nhau theo bề rộng tự nhiên của
    font; cả từ co / giãn đều (WORD_FIT_MIN..MAX) cho vừa khoảng từ ký tự đầu đến ký tự cuối trong PDF. Đường cơ sở và cỡ chữ lấy theo
    từng ký tự (chỉ số trên / dưới vẫn đúng chỗ)."""
    glyphs = [_glyph(c.ch, c.bold, c.italic, family) for c in chars]
    units = [c.size_mm / fontdata.EM_UNITS for c in chars]
    natural = [(g.rt - g.lt) * u for g, u in zip(glyphs, units)]
    total = sum(natural)
    target = chars[-1].x1 - chars[0].x0
    s = min(WORD_FIT_MAX, max(WORD_FIT_MIN, target / total)) if total > 0 and target > 0 else 1.0
    if family in fontdata.CONNECTED_FAMILIES:
        return _connected_word(chars, glyphs, units, s)
    x = chars[0].x0
    out: list = []
    for g, c, u, w in zip(glyphs, chars, units, natural):
        origin = x - g.lt * u * s
        for stroke in g.strokes:
            out.append([(origin + gx * u * s, c.baseline + gy * u) for gx, gy in stroke])
        x += w * s
    return out


def group_lines(chars) -> list[list[Char]]:
    """Gom ký tự thành dòng (đường cơ sở gần nhau), dòng từ trên xuống, ký tự trong dòng từ trái sang phải."""
    lines: list[list[Char]] = []
    base = None
    for c in sorted(chars, key=lambda c: (c.baseline, c.x0)):
        if lines and base is not None and abs(c.baseline - base) <= LINE_TOL * c.size_mm:
            lines[-1].append(c)
        else:
            lines.append([c])
            base = c.baseline
    return [sorted(line, key=lambda c: c.x0) for line in lines]


def _words(chars) -> list[list[Char]]:
    """Cắt các ký tự thành từ bằng dấu cách (dấu cách không vào từ)."""
    words: list[list[Char]] = []
    cur: list[Char] = []
    for c in chars:
        if c.ch.isspace():
            if cur:
                words.append(cur)
                cur = []
        else:
            cur.append(c)
    if cur:
        words.append(cur)
    return words


def split_runs(line) -> list[list[Char]]:
    """Cắt dòng thành các đoạn liền nhau: khoảng trống lớn (sang ô bảng khác) là chỗ cắt."""
    runs: list[list[Char]] = []
    for c in line:
        if runs and c.x0 - runs[-1][-1].x1 <= RUN_GAP_EM * c.size_mm:
            runs[-1].append(c)
        else:
            runs.append([c])
    return runs


def _bbox(chars, page_w: float, page_h: float) -> tuple:
    x0 = min(c.x0 for c in chars) - SKEL_PAD_MM
    x1 = max(c.x1 for c in chars) + SKEL_PAD_MM
    y0 = min(c.baseline - SKEL_ASCENT * c.size_mm for c in chars) - SKEL_PAD_MM
    y1 = max(c.baseline + SKEL_DESCENT * c.size_mm for c in chars) + SKEL_PAD_MM
    return max(0.0, x0), max(0.0, y0), min(page_w, x1), min(page_h, y1)


def skeleton_strokes(doc, page_index: int, bbox, dpi: float, threshold: int, blur_mm: float = 0.0) -> list:
    """Kết xuất `bbox` (mm) -> (làm mịn Gauss `blur_mm`) -> nhị phân -> skeleton -> nét (mm, tọa độ trang). Làm mịn dùng cho ảnh mờ / răng
    cưa (hình vẽ nét trong PDF): bớt râu và nét vụn; làm mịn thì nét nhạt đi nên ngưỡng hạ `BLUR_THRESHOLD_DROP`."""
    x0, y0, x1, y1 = bbox
    if x1 - x0 < 0.3 or y1 - y0 < 0.3:
        return []
    from skimage.morphology import skeletonize
    k = 25.4 / dpi
    gray = doc.render_gray(page_index, bbox, dpi)
    if blur_mm > 0:
        import cv2
        gray = cv2.GaussianBlur(gray, (0, 0), blur_mm / k)
        threshold -= BLUR_THRESHOLD_DROP
    mask = gray < threshold
    if not mask.any():
        return []
    strokes = trace.to_strokes(skeletonize(mask), k, k, SKEL_MIN_LEN_MM)
    return [[(x0 + x, y0 + y) for x, y in s] for s in strokes]


def build(content, o, doc=None, page_index: int = 0):
    """(danh sách nét, thống kê). `doc` = PdfDoc đang mở (cần cho skeleton / ký tự dự phòng); None thì ký tự lạ bị bỏ qua và đếm."""
    stats = {"chars": 0, "single": 0, "skeleton": 0, "fallback": 0, "missing": 0, "lines": 0, "missing_sample": ""}
    chars = [e for c in content.chars for e in expand(c)]
    lines = group_lines(chars)
    out: list = []

    def skeleton(run, key: str) -> list:
        if doc is None:
            stats["missing"] += len(run)
            return []
        stats[key] += sum(1 for c in run if not c.ch.isspace())
        found = skeleton_strokes(doc, page_index, _bbox(run, content.width_mm, content.height_mm), o.skeleton_dpi, o.skeleton_threshold)
        return pathing.order_nearest(found, (min(c.x0 for c in run), run[0].baseline))

    def single_word(word) -> list:
        """Một từ bằng nét đơn; ký tự font không có tách ra vẽ theo hình gốc, phần còn lại của từ vẫn đặt theo từ."""
        found: list = []
        i = 0
        while i < len(word):
            if _glyph(word[i].ch, word[i].bold, word[i].italic, o.font) is None:
                c = word[i]
                if len(stats["missing_sample"]) < 40 and c.ch not in stats["missing_sample"]:
                    stats["missing_sample"] += c.ch
                found += skeleton([c], "fallback")
                i += 1
                continue
            j = i
            while j < len(word) and _glyph(word[j].ch, word[j].bold, word[j].italic, o.font) is not None:
                j += 1
            sub = word[i:j]
            stats["single"] += len(sub)
            if all(c.ch in STRETCH for c in sub):               # gạch dài đứng riêng: kéo kín ô chữ
                for c in sub:
                    found += glyph_strokes(c, o.glyph_fit, o.font) or []
            else:
                found += word_strokes(sub, o.font)
            i = j
        return found

    for line in lines:
        line_strokes: list = []
        for run in split_runs(line):
            stats["chars"] += sum(1 for c in run if not c.ch.isspace())
            big = [c.size_mm / PT_MM >= o.mixed_min_pt for c in run]
            if o.text_mode == "skeleton":
                big = [True] * len(run)
            elif o.text_mode == "single":
                big = [False] * len(run)
            i = 0
            while i < len(run):                                   # đoạn liên tiếp cùng cách vẽ
                j = i
                while j < len(run) and big[j] == big[i]:
                    j += 1
                part = run[i:j]
                if big[i]:
                    line_strokes += skeleton(part, "skeleton")
                else:
                    for word in _words(part):
                        line_strokes += single_word(word)
                i = j
        if line_strokes:
            stats["lines"] += 1
            out += pathing.join(line_strokes, o.join_mm)
    return out, stats
