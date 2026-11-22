"""Đọc một trang PDF thành 3 loại nội dung: KÝ TỰ (có vị trí, cỡ, đậm / nghiêng), ĐƯỜNG KẺ (bảng, khung) và KHUNG ẢNH.

Chỉ tệp này (và `service.py`) biết tới PyMuPDF (giấy phép AGPL-3.0 / thương mại): đề tài nghiên cứu nên dùng được, nhưng nếu
sau này đóng gói bán thì thay bằng bộ đọc khác chỉ cần viết lại tệp này, giữ nguyên các lớp `Char`, `Segment`, `ImageBox`,
`PageContent`. Tọa độ trả về đều là mm, gốc ở góc TRÊN TRÁI trang, Y xuống (cùng quy ước với phần còn lại của dự án).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..drawing.errors import DrawError

PT_MM = 25.4 / 72.0              # 1 pt = 0,3528 mm
MAX_PDF_BYTES = 40 * 1024 * 1024
MAX_PAGES = 500
THIN_RECT_PT = 2.0               # hình chữ nhật tô đặc mỏng hơn mức này (pt) là một ĐƯỜNG KẺ (Word / trình duyệt vẽ viền bảng kiểu này)
WHITE_LEVEL = 0.92               # màu sáng hơn mức này (mọi kênh) coi là trắng: nền / viền trắng không vẽ
CURVE_STEPS = 10                 # số đoạn thẳng thay một cung Bézier
FILL_MIN_AREA_PT2 = 4.0          # khối tô đặc nhỏ hơn mức này (pt²) bỏ qua (bụi); lớn hơn thì ghi "khối tô" vào thống kê


@dataclass
class Char:
    ch: str
    x0: float                    # hộp ký tự (mm); x0..x1 = bề rộng thật (đã gồm cách chữ) trong PDF
    x1: float
    baseline: float              # y của đường cơ sở (mm)
    size_mm: float               # cỡ chữ (em) mm
    bold: bool
    italic: bool
    line: int = 0                # số thứ tự dòng PyMuPDF (dùng nhóm dòng)


@dataclass
class Segment:
    pts: list                    # [(x, y)] mm
    width_mm: float = 0.0        # bề dày nét trong PDF (0 = không rõ)
    closed: bool = False


@dataclass
class ImageBox:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class PageContent:
    width_mm: float
    height_mm: float
    chars: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    images: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _engine():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz as pymupdf                        # tên cũ của cùng gói
            return pymupdf
        except ImportError as exc:
            raise DrawError("pdf_engine_missing", "Thiếu thư viện PyMuPDF để đọc PDF: chạy `pip install pymupdf` rồi khởi động lại phần mềm.", 501) from exc


def _is_white(color) -> bool:
    return color is not None and len(color) >= 1 and all(c >= WHITE_LEVEL for c in color)


_LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}


class PdfDoc:
    """Một tệp PDF đã mở. Đóng bằng close() (hoặc with)."""

    def __init__(self, data: bytes) -> None:
        if len(data) > MAX_PDF_BYTES:
            raise DrawError("file_too_large", f"PDF lớn hơn {MAX_PDF_BYTES // (1024 * 1024)} MB.", 413)
        if not data.lstrip()[:5].startswith(b"%PDF"):
            raise DrawError("bad_pdf", "Tệp không phải PDF.")
        pm = _engine()
        self._pm = pm
        try:
            self._doc = pm.open(stream=data, filetype="pdf")
        except Exception as exc:                          # PyMuPDF báo nhiều kiểu lỗi khác nhau
            raise DrawError("bad_pdf", "Không mở được PDF (tệp hỏng?).") from exc
        if self._doc.needs_pass:
            self._doc.close()
            raise DrawError("pdf_encrypted", "PDF có mật khẩu: hãy xuất bản không mật khẩu.")
        if self._doc.page_count > MAX_PAGES:
            self._doc.close()
            raise DrawError("too_many_pages", f"PDF quá {MAX_PAGES} trang.")

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._doc.close()

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def page_sizes(self) -> list[tuple[float, float]]:
        out = []
        for i in range(self._doc.page_count):
            r = self._doc[i].rect
            out.append((round(r.width * PT_MM, 2), round(r.height * PT_MM, 2)))
        return out

    def _page(self, index: int):
        if not 0 <= index < self._doc.page_count:
            raise DrawError("bad_param", f"Trang {index + 1} không có (PDF có {self._doc.page_count} trang).")
        return self._doc[index]

    # ---------- nội dung ----------
    def read_page(self, index: int) -> PageContent:
        page = self._page(index)
        rect = page.rect
        content = PageContent(rect.width * PT_MM, rect.height * PT_MM)
        content.stats = {"rotated_chars": 0, "filled_areas": 0, "page_rotation": int(page.rotation)}
        self._read_text(page, content)
        self._read_drawings(page, content)
        for info in page.get_image_info():
            x0, y0, x1, y1 = info["bbox"]
            if (x1 - x0) * (y1 - y0) > 4.0:
                content.images.append(ImageBox(x0 * PT_MM, y0 * PT_MM, x1 * PT_MM, y1 * PT_MM))
        return content

    def _read_text(self, page, content: PageContent) -> None:
        raw = page.get_text("rawdict")
        line_no = 0
        for block in raw["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                line_no += 1
                dx, dy = line.get("dir", (1.0, 0.0))
                upright = abs(dy) < 0.02 and dx > 0
                for span in line["spans"]:
                    font = span.get("font", "")
                    flags = span.get("flags", 0)
                    bold = bool(flags & 16) or bool(re.search(r"bold|black|heavy|semibold", font, re.I))
                    italic = bool(flags & 2) or bool(re.search(r"italic|oblique", font, re.I))
                    for c in span["chars"]:
                        ch = _LIGATURES.get(c["c"], c["c"])
                        if not upright:
                            content.stats["rotated_chars"] += 1
                            continue
                        x0, y0, x1, y1 = c["bbox"]
                        _, oy = c["origin"]
                        n = len(ch)
                        for k, one in enumerate(ch):      # ligature tách thành nhiều ký tự chia đều bề rộng
                            content.chars.append(Char(one, (x0 + (x1 - x0) * k / n) * PT_MM, (x0 + (x1 - x0) * (k + 1) / n) * PT_MM,
                                                      oy * PT_MM, span["size"] * PT_MM, bold, italic, line_no))

    def _read_drawings(self, page, content: PageContent) -> None:
        for d in page.get_drawings():
            kind = d.get("type") or ""
            stroke, fill = d.get("color"), d.get("fill")
            width_pt = float(d.get("width") or 0.0)
            has_stroke = "s" in kind and stroke is not None and not _is_white(stroke)
            has_fill = "f" in kind and fill is not None and not _is_white(fill)
            if not has_stroke and not has_fill:
                continue
            chain: list = []                              # đường gấp khúc đang nối

            def flush(closed=False):
                if len(chain) >= 2:
                    content.segments.append(Segment([(x * PT_MM, y * PT_MM) for x, y in chain], width_pt * PT_MM, closed))
                chain.clear()

            for item in d["items"]:
                op = item[0]
                if op == "re":
                    flush()
                    r = item[1]
                    w, h = r.width, r.height
                    if has_stroke:
                        content.segments.append(Segment([(r.x0 * PT_MM, r.y0 * PT_MM), (r.x1 * PT_MM, r.y0 * PT_MM), (r.x1 * PT_MM, r.y1 * PT_MM),
                                                         (r.x0 * PT_MM, r.y1 * PT_MM)], width_pt * PT_MM, True))
                    elif has_fill and min(w, h) <= THIN_RECT_PT:
                        t = min(w, h) * PT_MM
                        if w >= h:
                            ym = (r.y0 + r.y1) / 2 * PT_MM
                            content.segments.append(Segment([(r.x0 * PT_MM, ym), (r.x1 * PT_MM, ym)], t))
                        else:
                            xm = (r.x0 + r.x1) / 2 * PT_MM
                            content.segments.append(Segment([(xm, r.y0 * PT_MM), (xm, r.y1 * PT_MM)], t))
                    elif has_fill and w * h >= FILL_MIN_AREA_PT2:
                        content.stats["filled_areas"] += 1
                elif op == "l":
                    p1, p2 = item[1], item[2]
                    if chain and (abs(chain[-1][0] - p1.x) > 0.01 or abs(chain[-1][1] - p1.y) > 0.01):
                        flush()
                    if not chain:
                        chain.append((p1.x, p1.y))
                    chain.append((p2.x, p2.y))
                elif op == "c":
                    p1, c1, c2, p2 = item[1], item[2], item[3], item[4]
                    if chain and (abs(chain[-1][0] - p1.x) > 0.01 or abs(chain[-1][1] - p1.y) > 0.01):
                        flush()
                    if not chain:
                        chain.append((p1.x, p1.y))
                    for k in range(1, CURVE_STEPS + 1):
                        t = k / CURVE_STEPS
                        a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
                        chain.append((a * p1.x + b * c1.x + c * c2.x + e * p2.x, a * p1.y + b * c1.y + c * c2.y + e * p2.y))
                elif op == "qu":
                    flush()
                    q = item[1]
                    pts = [(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)]
                    if has_stroke:
                        content.segments.append(Segment([(x * PT_MM, y * PT_MM) for x, y in pts], width_pt * PT_MM, True))
                    elif has_fill:
                        content.stats["filled_areas"] += 1
            flush(closed=bool(d.get("closePath")) and has_stroke)

    # ---------- kết xuất ----------
    def render_gray(self, index: int, bbox_mm: tuple, dpi: float):
        """Ảnh xám numpy (h, w) của hình chữ nhật `bbox_mm` = (x0, y0, x1, y1) trên trang."""
        import numpy as np
        pix = self._clip_pixmap(index, bbox_mm, dpi, gray=True)
        return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()

    def render_png(self, index: int, bbox_mm: tuple | None, dpi: float) -> bytes:
        """PNG (màu) của một vùng, hoặc cả trang nếu bbox_mm là None."""
        return self._clip_pixmap(index, bbox_mm, dpi, gray=False).tobytes("png")

    def _clip_pixmap(self, index: int, bbox_mm, dpi: float, gray: bool):
        pm = self._pm
        page = self._page(index)
        k = dpi / 72.0
        clip = None
        if bbox_mm is not None:
            x0, y0, x1, y1 = (v / PT_MM for v in bbox_mm)
            clip = pm.Rect(x0, y0, x1, y1) & page.rect
        return page.get_pixmap(matrix=pm.Matrix(k, k), clip=clip, colorspace=pm.csGRAY if gray else pm.csRGB, alpha=False)
