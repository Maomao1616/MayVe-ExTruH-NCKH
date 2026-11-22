"""Tham số của tab Beta (một nơi khai báo, có đơn vị). Tách riêng khỏi `drawing/spec.py` để gỡ tính năng Beta không đụng phần tab Tạo bản vẽ."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..drawing.errors import DrawError

TEXT_MODES = ("single", "skeleton", "mixed")                  # nét đơn (thay font) | giữ hình chữ gốc (skeleton) | chữ lớn skeleton, nhỏ nét đơn
FONTS = ("script", "simplex", "times")
IMAGE_KINDS = ("auto", "lineart", "crosshatch", "flow", "wave_am", "spiral", "outline")     # auto = tự nhận hình vẽ nét (lấy đường giữa nét) hay ảnh chụp (tô); còn lại như tab Tạo bản vẽ


@dataclass(frozen=True)
class Param:
    name: str
    kind: str                     # "int" | "float" | "bool" | "choice"
    default: Any
    lo: float | None = None
    hi: float | None = None
    choices: tuple = ()
    unit: str = ""


PARAMS = (
    Param("page", "int", 1, 1, 500),                                       # trang cần vẽ (đếm từ 1)
    Param("text_mode", "choice", "single", choices=TEXT_MODES),
    Param("font", "choice", "script", choices=FONTS),                        # font nét đơn: script (chữ viết tay nối nét, mặc định) | simplex (gọn, chữ rời) | times (giống Times, nhiều nét kép)
    Param("mixed_min_pt", "float", 17.0, 6, 200, unit="pt"),               # chế độ mixed: chữ từ cỡ này trở lên dùng skeleton
    Param("pen_mm", "float", 0.5, 0.1, 2.0, unit="mm"),                    # bút viết chữ và khung (bút bi 0,5)
    Param("frame", "bool", True),                                          # vẽ đường kẻ bảng / khung
    Param("thick_double", "bool", True),                                   # đường kẻ dày hơn 1,5 × bút thì vẽ 2 đường sát nhau
    Param("images", "bool", True),                                         # vẽ ảnh trong trang
    Param("image_kind", "choice", "auto", choices=IMAGE_KINDS),
    Param("lineart_with_text", "bool", True),                              # hình vẽ nét (sơ đồ, mạch, công thức dạng ảnh) vẽ cùng bút và cùng tệp G-code với chữ
    Param("image_pen_mm", "float", 0.4, 0.1, 2.0, unit="mm"),              # bút tô ảnh (Sakura 0,4): lớp riêng, tệp G-code riêng
    Param("image_dpi", "float", 150.0, 50, 300, unit="dpi"),               # độ phân giải cắt ảnh trong trang trước khi tô
    Param("skeleton_dpi", "float", 600.0, 200, 1200, unit="dpi"),          # độ phân giải làm skeleton (chữ / ký tự dự phòng)
    Param("skeleton_threshold", "int", 190, 40, 250),                      # điểm ảnh xám tối hơn mức này là mực
    Param("join_mm", "float", 0.25, 0.0, 2.0, unit="mm"),                  # nối nét hai đầu gần nhau
    Param("glyph_fit", "float", 0.92, 0.5, 1.2),                           # chữ nét đơn chiếm tối đa tỷ lệ này bề rộng ô chữ trong PDF
)
BY_NAME = {p.name: p for p in PARAMS}


@dataclass(frozen=True)
class Options:
    page: int
    text_mode: str
    font: str
    mixed_min_pt: float
    pen_mm: float
    frame: bool
    thick_double: bool
    images: bool
    image_kind: str
    lineart_with_text: bool
    image_pen_mm: float
    image_dpi: float
    skeleton_dpi: float
    skeleton_threshold: int
    join_mm: float
    glyph_fit: float


def parse(raw: dict | None) -> Options:
    """Điền mặc định, từ chối tham số lạ, kiểm kiểu và khoảng (cùng tinh thần `drawing.spec.parse`)."""
    raw = dict(raw or {})
    unknown = sorted(set(raw) - set(BY_NAME))
    if unknown:
        raise DrawError("bad_param", f"beta: tham số lạ: {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for p in PARAMS:
        v = raw.get(p.name)
        if v is None:
            values[p.name] = p.default
            continue
        where = f"beta.{p.name}"
        if p.kind == "bool":
            if not isinstance(v, bool):
                raise DrawError("bad_param", f"{where}: phải là true hoặc false")
        elif p.kind == "choice":
            if v not in p.choices:
                raise DrawError("bad_param", f"{where}: chỉ nhận {', '.join(p.choices)}")
        else:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise DrawError("bad_param", f"{where}: phải là số")
            if p.kind == "int":
                if float(v) != int(v):
                    raise DrawError("bad_param", f"{where}: phải là số nguyên")
                v = int(v)
            else:
                v = float(v)
            if (p.lo is not None and v < p.lo) or (p.hi is not None and v > p.hi):
                raise DrawError("bad_param", f"{where}: ngoài khoảng {p.lo}..{p.hi} {p.unit}".strip())
        values[p.name] = v
    return Options(**values)


def describe() -> list[dict]:
    """Khai báo tham số cho giao diện (GET /api/beta/pdf/schema)."""
    return [{"name": p.name, "kind": p.kind, "default": p.default, "min": p.lo, "max": p.hi, "choices": list(p.choices), "unit": p.unit}
            for p in PARAMS]
