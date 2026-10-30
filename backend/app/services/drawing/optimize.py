"""Tối ưu nét bằng vpype: nối nét gần nhau, đơn giản hóa, bỏ nét ngắn, sắp xếp giảm quãng bút nâng.
Dùng `vpype_cli.execute(chuỗi lệnh, Document)`. Chuỗi lệnh dựng bằng hàm thuần `build_pipeline` (test được
mà không cần vpype)."""
from __future__ import annotations

from .errors import DrawError
from .spec import Params


def _mm(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".") + "mm"


TWO_OPT_MAX_STROKES = 15_000      # 2-opt tăng theo bình phương số nét: quá ngưỡng thì chỉ sắp xếp thường


def build_pipeline(p: Params, strokes: int | None = None) -> str:
    parts: list[str] = []
    if p.merge_tolerance_mm > 0:
        parts.append(f"linemerge --tolerance {_mm(p.merge_tolerance_mm)}")
    if p.simplify_tolerance_mm > 0:
        parts.append(f"linesimplify --tolerance {_mm(p.simplify_tolerance_mm)}")
    if p.min_length_mm > 0:
        parts.append(f"filter --min-length {_mm(p.min_length_mm)}")
    if p.sort:
        two_opt = p.two_opt and (strokes is None or strokes <= TWO_OPT_MAX_STROKES)
        parts.append(f"linesort --two-opt --passes {p.passes}" if two_opt else "linesort")
    return " ".join(parts)


def run(document, p: Params):
    strokes = sum(len(lc) for lc in document.layers.values()) if hasattr(document, "layers") else None
    pipeline = build_pipeline(p, strokes)
    if not pipeline:
        return document
    import vpype_cli
    try:
        return vpype_cli.execute(pipeline, document)
    except Exception as exc:        # vpype báo lỗi bằng nhiều kiểu khác nhau
        raise DrawError("optimize_failed", f"vpype không chạy được '{pipeline}': {exc}", 500) from exc
