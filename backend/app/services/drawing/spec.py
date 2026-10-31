"""Khai báo tham số MỘT chỗ: tên, kiểu, mặc định, giới hạn. Dùng để kiểm tra đầu vào VÀ để trả cho
frontend qua /api/draw/schema (frontend không rải số cứng).

Thêm/sửa một tham số = sửa đúng một dòng trong LAYOUT / GCODE / MACHINE bên dưới.
Tham số `required=True` không có mặc định: frontend phải gửi (lấy từ MACHINE trong config.js),
backend không tự đặt số riêng của máy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from .errors import DrawError
from .registry import VECTORIZERS


@dataclass(frozen=True)
class Param:
    name: str
    kind: str                      # "float" | "int" | "bool" | "choice"
    default: Any = None
    min: float | None = None
    max: float | None = None
    choices: tuple[str, ...] = ()
    unit: str = ""
    required: bool = False


# Khổ giấy dựng sẵn (mm, đặt đứng). Frontend dùng để điền rộng/cao; backend không phụ thuộc.
PAPERS = {"a4": (210.0, 297.0), "a5": (148.0, 210.0), "a6": (105.0, 148.0), "letter": (215.9, 279.4)}

# Tờ giấy + khung vẽ. Tờ giấy đặt ở GỐC máy O(0,0) (góc trên trái, Y xuống) rồi mới dịch bằng paper_x/y.
# Khung vẽ nằm TRONG tờ giấy (trừ lề); "căn giữa" = căn khung vẽ giữa phần trong lề của tờ giấy.
LAYOUT = (
    Param("paper", "choice", "a4", choices=tuple(PAPERS) + ("custom",)),
    Param("paper_width_mm", "float", None, 1, 5000, unit="mm"),    # chỉ dùng khi paper = custom
    Param("paper_height_mm", "float", None, 1, 5000, unit="mm"),
    Param("paper_x_mm", "float", 0.0, 0, 5000, unit="mm"),         # góc trên trái tờ giấy trên máy
    Param("paper_y_mm", "float", 0.0, 0, 5000, unit="mm"),
    Param("margin_mm", "float", 5.0, 0, 500, unit="mm"),           # lề an toàn, tính từ mép TỜ GIẤY
    Param("width_mm", "float", None, 1, 5000, unit="mm"),          # None = lấp đầy phần trong lề
    Param("height_mm", "float", None, 1, 5000, unit="mm"),
    Param("fit", "choice", "contain", choices=("contain", "stretch")),
    Param("center", "bool", True),                                 # căn giữa khung vẽ trong tờ giấy
    Param("offset_x_mm", "float", 0.0, 0, 5000, unit="mm"),        # khi center=false: tính từ góc trong lề
    Param("offset_y_mm", "float", 0.0, 0, 5000, unit="mm"),
    Param("flip_x", "bool", False),
    Param("flip_y", "bool", False),
    Param("reverse", "bool", False),                               # đảo thứ tự các nét
    Param("rotate", "choice", 0, choices=(0, 90, 180, 270), unit="°"),  # xoay thuận chiều kim đồng hồ
)

# Thông số vẽ (khớp các ô trong tab).
GCODE = (
    Param("draw_feed", "float", 3000.0, 10, 20000, unit="mm/min"),
    Param("travel_feed", "float", 6000.0, 10, 20000, unit="mm/min"),
    Param("pen_up_z", "float", required=True, min=0, max=1000, unit="mm"),
    Param("pen_down_z", "float", required=True, min=0, max=1000, unit="mm"),
    Param("pen_feed", "float", 3000.0, 10, 20000, unit="mm/min"),
    Param("delay_up_s", "float", 0.2, 0, 60, unit="s"),
    Param("delay_down_s", "float", 0.2, 0, 60, unit="s"),
    Param("precision", "int", 3, 1, 4),
)

# Giới hạn phần cứng: LẤY TỪ MACHINE trong config.js, backend không tự đặt.
MACHINE = (
    Param("work_w", "float", required=True, min=1, max=5000, unit="mm"),
    Param("work_h", "float", required=True, min=1, max=5000, unit="mm"),
    Param("z_travel", "float", required=True, min=0, max=1000, unit="mm"),
    Param("rapid_feed", "float", required=True, min=10, max=100000, unit="mm/min"),
    # Điểm DUY NHẤT đảo chiều Y khi chưa kiểm chứng hướng trục thật (giả định C5).
    Param("invert_y", "bool", False),
)

# Tối ưu nét (vpype). 0 = tắt bước đó.
OPTIMIZE = (
    Param("merge_tolerance_mm", "float", 0.1, 0, 10, unit="mm"),      # nối các nét có đầu cuối gần nhau
    Param("simplify_tolerance_mm", "float", 0.05, 0, 10, unit="mm"),  # đơn giản hóa (bỏ điểm thừa)
    Param("min_length_mm", "float", 0.5, 0, 100, unit="mm"),          # bỏ nét ngắn hơn mức này
    Param("sort", "bool", True),                                      # sắp xếp để giảm quãng bút nâng
    Param("two_opt", "bool", True),                                   # 2-opt: giảm thêm ~25% quãng nhấc bút (chậm hơn)
    Param("passes", "int", 50, 10, 2000),                             # số lượt 2-opt; 50 là đủ (200 gần như không hơn)
)

# Nạp SVG.
SVG = (
    Param("quantization_mm", "float", 0.1, 0.01, 5, unit="mm"),       # sai số khi chia đường cong thành đoạn thẳng
    Param("frame", "choice", "content", choices=("content", "page")), # co theo hộp bao nét hay theo trang SVG
)

# Ảnh raster (độ phân giải xử lý tự tính từ khung vẽ ÷ độ rộng bút; max_side_px chỉ để ghi đè).
RASTER = (
    Param("pen_width_mm", "float", 0.4, 0.1, 2, unit="mm"),           # bút dựng sẵn: 0,2 / 0,4 (xem PENS)
    Param("max_side_px", "int", None, 400, 4000, unit="px"),          # None = tự tính
    Param("quality", "choice", "final", choices=("draft", "final")),  # nháp (nhỏ, nhanh) hay chính thức
    Param("crop_x", "float", 0.0, 0, 1), Param("crop_y", "float", 0.0, 0, 1),   # cắt ảnh: tỷ lệ 0..1 của ảnh gốc
    Param("crop_w", "float", 1.0, 0.01, 1), Param("crop_h", "float", 1.0, 0.01, 1),
    Param("gamma", "float", 1.0, 0.3, 3.0),
    Param("black_point", "int", 0, 0, 254),
    Param("white_point", "int", 255, 1, 255),
    Param("auto_levels", "bool", True),                               # kéo giãn 1–99% độ sáng: ảnh chụp thiếu tương phản vẫn ra nét
    Param("clahe", "bool", False),                                    # cân bằng sáng cục bộ (ảnh tối/sáng lệch)
    Param("denoise", "bool", False),                                  # khử nhiễu NLM: chậm, chỉ cho ảnh thiếu sáng
)

# Kiểu tô. spacing_mm/amplitude_mm None = tự tính từ độ rộng bút.
STYLE = (
    Param("kind", "choice", "zigzag", choices=("outline", "zigzag", "wave", "spiral")),
    Param("outline_overlay", "bool", False),                          # thêm lớp viền phác họa lên kiểu tô
    Param("outline_detail", "choice", "medium", choices=("low", "medium", "high")),  # viền: ít = khối chính, nhiều = cả nét nhạt
    Param("levels", "int", 4, 3, 5),                                  # số mức sáng tối
    Param("angle", "float", 45.0, 0, 179, unit="°"),
    Param("spacing_mm", "float", None, 0.1, 20, unit="mm"),
    Param("amplitude_mm", "float", None, 0.05, 10, unit="mm"),
    Param("invert", "bool", False),                                   # đảo sáng/tối
)

# Đa màu: tối đa 2-4 màu, chỉ để thử mô hình.
PALETTE = (
    Param("mode", "choice", "mono", choices=("mono", "multi")),
    Param("colors", "int", 3, 2, 4),
    Param("skip_background", "bool", True),
)

PENS = (0.2, 0.4)
STYLES = ("outline", "zigzag", "wave", "spiral")

GROUPS = {"layout": LAYOUT, "gcode": GCODE, "machine": MACHINE, "optimize": OPTIMIZE, "svg": SVG,
          "raster": RASTER, "style": STYLE, "palette": PALETTE}


class Params:
    """Tham số đã kiểm tra, truy cập bằng thuộc tính, không sửa được."""
    __slots__ = ("_v",)

    def __init__(self, values: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_v", dict(values))

    def __getattr__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, "_v")[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Params là bất biến")

    def as_dict(self) -> dict[str, Any]:
        return dict(self._v)


def _coerce(group: str, p: Param, v: Any) -> Any:
    where = f"{group}.{p.name}"
    if p.kind == "bool":
        if not isinstance(v, bool):
            raise DrawError("bad_param", f"{where}: phải là true hoặc false")
        return v
    if p.kind == "choice":
        if v not in p.choices:
            raise DrawError("bad_param", f"{where}: chỉ nhận {', '.join(map(str, p.choices))}")
        return v
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise DrawError("bad_param", f"{where}: phải là số")
    if not math.isfinite(v):
        raise DrawError("bad_param", f"{where}: không phải số hữu hạn")
    if p.kind == "int":
        if float(v) != int(v):
            raise DrawError("bad_param", f"{where}: phải là số nguyên")
        v = int(v)
    else:
        v = float(v)
    if (p.min is not None and v < p.min) or (p.max is not None and v > p.max):
        raise DrawError("bad_param", f"{where}: ngoài khoảng {p.min}..{p.max} {p.unit}".strip())
    return v


def parse(group: str, raw: Mapping[str, Any] | None) -> Params:
    """Điền mặc định, từ chối tham số lạ (bắt lỗi gõ sai tên), kiểm kiểu và khoảng giá trị."""
    specs = GROUPS[group]
    raw = dict(raw or {})
    unknown = sorted(set(raw) - {p.name for p in specs})
    if unknown:
        raise DrawError("bad_param", f"{group}: tham số lạ: {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for p in specs:
        if raw.get(p.name) is not None:
            values[p.name] = _coerce(group, p, raw[p.name])
        elif p.required:
            raise DrawError("bad_param", f"{group}.{p.name}: thiếu (bắt buộc)")
        else:
            values[p.name] = p.default
    return Params(values)


def describe() -> dict:
    """Nội dung cho GET /api/draw/schema."""
    from .service import MAX_POINTS
    from ..job import MAX_LINES

    def row(p: Param) -> dict:
        return {"name": p.name, "kind": p.kind, "default": p.default, "min": p.min, "max": p.max,
                "choices": list(p.choices), "unit": p.unit, "required": p.required}

    return {
        "papers": {k: {"w": w, "h": h} for k, (w, h) in PAPERS.items()},
        "pens": list(PENS),
        "styles": list(STYLES),
        "params": {g: [row(p) for p in specs] for g, specs in GROUPS.items()},
        "vectorizers": VECTORIZERS.names(),
        "limits": {"max_lines": MAX_LINES, "max_points": MAX_POINTS},
    }
