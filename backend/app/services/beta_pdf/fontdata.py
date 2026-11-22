"""Font nét đơn kiểu Times (Hershey `timesr`, `timesrb`, `timesi`, `timesib`) lấy từ gói vpype (MIT, đã cài sẵn).

Dữ liệu gốc: mỗi ký tự ASCII 32..127 là các đường gấp khúc, y HƯỚNG XUỐNG, đường cơ sở ở y = 9, chiều cao chữ thường 14,
chữ hoa 21, chân chữ (g, p, y) sâu thêm 7 đơn vị. Ở đây đổi y thành "so với đường cơ sở" (âm = phía trên) để ghép dấu cho dễ.
Font KHÔNG có chữ tiếng Việt: dấu do `viet.py` ghép lên chữ gốc.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BASELINE = 9.0                   # y của đường cơ sở trong dữ liệu Hershey
CAP_HEIGHT = 21.0                # chiều cao chữ hoa (đơn vị Hershey)
X_HEIGHT = 14.0                  # chiều cao chữ thường
TIMES_CAP_RATIO = 0.662          # chiều cao chữ hoa / cỡ chữ của Times New Roman (OS/2 sCapHeight 1356 / 2048)
EM_UNITS = CAP_HEIGHT / TIMES_CAP_RATIO     # cỡ chữ (em) tính bằng đơn vị Hershey ≈ 31,7

# Họ font -> {(đậm, nghiêng): tên tệp font trong vpype}. "times": giống Times New Roman nhưng nhiều nét kép (đặc); "simplex": nét đơn kiểu
# sans (futural / futuram), ít nét hơn nhiều; font simplex không có chữ nghiêng nên nghiêng bằng cách xô ngang SIMPLEX_SLANT.
FAMILIES = {
    "times": {(False, False): "timesr", (True, False): "timesrb", (False, True): "timesi", (True, True): "timesib"},
    "simplex": {(False, False): "futural", (True, False): "futuram", (False, True): "futural", (True, True): "futuram"},
    # "script": chữ viết tay nối nét (Hershey `cursive`): mỗi chữ cái là MỘT nét liền, vào và ra ở mép chữ ngang cùng độ cao nên ghép sát là
    # nối liền cả từ. Một kiểu duy nhất: đậm / nghiêng của Word bị bỏ, chỉ còn khác cỡ chữ (yêu cầu chủ dự án 22/11/2026).
    "script": {(False, False): "cursive", (True, False): "cursive", (False, True): "cursive", (True, True): "cursive"},
}
SIMPLEX_SLANT = 0.2
FAMILY_SCALE = {"script": (0.85, 1.1)}      # (ngang, dọc): chữ thường của font viết tay chỉ cao 9 (Times 14); chọn 0,85 × 1,1 sau khi so 4 mức trên PDF thật (1,0 × 1,45 chồng dòng, 0,8 × 1,0 nhỏ)
PRINT_FAMILY = {"script": "simplex"}        # họ viết tay: chữ HOA và chữ SỐ viết kiểu in như chữ tiếng Anh (yêu cầu chủ dự án), lấy từ họ này
PRINT_SCALE = 0.9                           # chữ in co 0,9 để chữ hoa cao ~1,9 lần chữ thường (chữ in gốc cao 2,1 lần chữ thường của font viết tay)
CONNECTED_FAMILIES = ("script",)            # họ font mà chữ cái trong một từ được nối thành một nét liền (text.word_strokes)


@dataclass(frozen=True)
class Glyph:
    strokes: tuple                  # các nét, mỗi nét là ((x, y), ...); y so với đường cơ sở, âm = phía trên
    lt: float                       # mép trái / phải theo dữ liệu gốc (độ rộng "ô chữ" của Hershey)
    rt: float
    n_base: int = -1                # số nét đầu thuộc chữ gốc; các nét sau là dấu ghép thêm (viet.py). -1 = toàn bộ là chữ gốc
    n_join: int = 0                 # trong các nét ghép thêm, số nét đầu DÍNH vào chữ (râu ơ ư, gạch đ): nối vào thân khi viết liền; còn lại là dấu rời
    solo: bool = False              # chữ in đứng riêng (chữ hoa, chữ số của họ viết tay): không nối với chữ kế bên


def _font_dir() -> Path:
    import vpype.text as vt
    return Path(vt.__file__).parent / "fonts"


@lru_cache(maxsize=8)
def _load(name: str) -> tuple:
    with open(_font_dir() / f"{name}.pickle", "rb") as fp:
        return tuple(pickle.load(fp))


def glyph(bold: bool, italic: bool, ch: str, family: str = "times") -> Glyph | None:
    """Glyph của một ký tự ASCII in được; None nếu font không có. Dấu cách trả Glyph không nét."""
    if len(ch) != 1 or not 32 <= ord(ch) < 128:
        return None
    if family in PRINT_FAMILY and (ch.isupper() or ch.isdigit()):          # chữ hoa / số của họ viết tay: kiểu in, đứng riêng
        p = glyph(False, False, ch, PRINT_FAMILY[family])
        return Glyph(tuple(tuple((x * PRINT_SCALE, y * PRINT_SCALE) for x, y in s) for s in p.strokes), p.lt * PRINT_SCALE, p.rt * PRINT_SCALE, solo=True)
    lt, rt, lines = _load(FAMILIES[family][(bool(bold), bool(italic))])[ord(ch) - 32]
    shear = SIMPLEX_SLANT if family == "simplex" and italic else 0.0
    sx, sy = FAMILY_SCALE.get(family, (1.0, 1.0))
    strokes = tuple(s for s in (tuple(((float(x) - (float(y) - BASELINE) * shear) * sx, (float(y) - BASELINE) * sy) for x, y in line)
                                for line in lines) if s)
    return Glyph(strokes, float(lt) * sx, float(rt) * sx)


@dataclass(frozen=True)
class Metrics:
    x_height: float                  # chiều cao chữ thường (x), chữ hoa (H), chữ có đuôi lên (d) của họ font này, đơn vị Hershey
    cap_height: float
    ascender: float


@lru_cache(maxsize=8)
def metrics(family: str) -> Metrics:
    """Đo từ chính glyph x, H, d của họ font (viet.py dựng dấu theo các số này; Times / simplex ra 14, 21, 21 như hằng số ở trên)."""
    def height(ch: str) -> float:
        g = glyph(False, False, ch, family)
        return -min(y for s in g.strokes for _, y in s)
    return Metrics(height("x"), height("H"), height("d"))
