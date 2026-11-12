"""Tối ưu nét bằng vpype: nối nét gần nhau, đơn giản hóa, bỏ nét ngắn, sắp xếp giảm quãng bút nâng.
Dùng `vpype_cli.execute(chuỗi lệnh, Document)`. Chuỗi lệnh dựng bằng hàm thuần `build_pipeline` (test được
mà không cần vpype)."""
from __future__ import annotations

import math

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


BRIDGE_PEN = 4.0          # nối nét gần: đầu nét sau cách cuối nét trước ≤ 4 × bề rộng nét (Sakura 0,5: 2 mm) thì vẽ luôn
                          # đoạn nối thay vì nhấc bút. Đo 12/11/2026 (ảnh mẫu A5, bút 0,5): 55–80 % lần nhấc bút chỉ bay ≤ 2–3 mm
BRIDGE_MIN_DARK = 0.2     # ... và mọi điểm trên đoạn nối có độ đậm ≥ 0,2 (mức nhạt nhất được tô ~0,11): không kẻ ngang giấy trắng


def bridge(strokes: list, dark, width_mm: float, height_mm: float, max_mm: float,
           min_dark: float = BRIDGE_MIN_DARK) -> tuple[list, int]:
    """Nối nét liền sau vào nét trước (giữ nguyên thứ tự đã sắp) khi đoạn nối ngắn và nằm trong vùng đậm.

    `dark`: ảnh độ đậm 0..1 phủ khung (0, 0)–(width_mm, height_mm), cùng hệ tọa độ với nét. Trả (nét mới, số chỗ nối)."""
    import numpy as np
    h, w = dark.shape
    sx, sy = w / width_mm, h / height_mm
    out: list[list] = []
    joined = 0
    for s in strokes:
        if out:
            (ax, ay), (bx, by) = out[-1][-1], s[0]
            gap = math.hypot(bx - ax, by - ay)
            if gap <= max_mm:
                n = max(2, int(math.ceil(gap * max(sx, sy))) + 1)
                t = np.linspace(0.0, 1.0, n)
                xs = np.clip(((ax + (bx - ax) * t) * sx).astype(int), 0, w - 1)
                ys = np.clip(((ay + (by - ay) * t) * sy).astype(int), 0, h - 1)
                if float(dark[ys, xs].min()) >= min_dark:
                    out[-1].extend(s[1:] if gap == 0 else s)
                    joined += 1
                    continue
        out.append(list(s))
    return out, joined


def layers_to_document(layers):
    """Lớp (mm) -> vpype Document (px), để chạy cùng dây chuyền tối ưu như SVG."""
    import numpy as np
    import vpype
    from .svg_in import PX_PER_MM
    doc = vpype.Document()
    for i, layer in enumerate(layers, start=1):
        lc = vpype.LineCollection()
        for s in layer.strokes:
            a = np.asarray(s, dtype=float) * PX_PER_MM
            lc.append(a[:, 0] + 1j * a[:, 1])
        doc.add(lc, i)
    return doc
