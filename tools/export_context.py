#!/usr/bin/env python3
"""Xuất mã nguồn thành MỘT tệp markdown gọn để đưa cho AI khác, tiết kiệm token.

Dùng thư viện chuẩn của Python, không cần bật venv. Chạy từ bất kỳ đâu:

    python tools/export_context.py --list                  # xem các gói và số token ước tính
    python tools/export_context.py control                 # xuất gói "control" -> export/control-<ngày>.md
    python tools/export_context.py draw-backend draw-frontend --budget 30000
    python tools/export_context.py --files backend/app/services/job.py frontend/js/views/control.js
    python tools/export_context.py control --html panel-control   # thêm đúng một khối của index.html
    python tools/export_context.py --map                   # viết lại docs/CODEMAP.md (bản đồ mã nguồn)

Hướng dẫn đầy đủ: docs/EXPORT_FOR_AI.md. Chỉ lấy tệp đang được Git theo dõi (không .venv, không dữ liệu máy).
"""
from __future__ import annotations

import argparse
import ast
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARS_PER_TOKEN = 3.2           # ước lượng cho tiếng Việt + mã; chỉ để so sánh, không phải con số chính xác
MAX_FILE_BYTES = 200_000
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".pyc", ".bat", ".gcode"}
SKIP_PARTS = {".vscode", "export", "samples", "fixtures"}
LANG = {".py": "python", ".js": "javascript", ".mjs": "javascript", ".css": "css", ".html": "html",
        ".json": "json", ".md": "markdown", ".txt": "", ".yaml": "yaml", ".yml": "yaml"}

# Gói theo việc cần làm. Mẫu glob tính từ gốc dự án; "html" = các khối index.html lấy theo id (tiết kiệm: index.html rất lớn).
BUNDLES: dict[str, dict] = {
    "docs": {
        "desc": "Tài liệu cốt lõi: vào đây trước khi đọc mã",
        "files": ["docs/AI_START.md", "docs/ARCHITECTURE.md", "docs/STATUS.md", "docs/DECISIONS.md"],
    },
    "codemap": {
        "desc": "Bản đồ mã nguồn tự sinh: route API + vai trò và token từng tệp (dùng để chọn gói)",
        "files": ["docs/CODEMAP.md"],
    },
    "machine-facts": {
        "desc": "Sự thật máy thật đã xác nhận + hợp đồng tab vẽ (đọc trước khi đụng phần cứng / tab vẽ)",
        "files": ["docs/MACHINE.md", "docs/DRAW_ROADMAP.md"],
    },
    "frontend-core": {
        "desc": "Nền tảng frontend: vào cửa, api, trạng thái, cấu hình, dịch, lưu trữ chung",
        "files": ["frontend/js/app.js", "frontend/js/core/*.js", "frontend/js/stores/jobstore.js", "frontend/js/stores/macros.js"],
    },
    "control": {
        "desc": "Tab Điều khiển: trạng thái, jog, bút, tệp G-code, khung 2D, terminal, dock, đầu trang",
        "files": ["frontend/js/views/control.js", "frontend/js/views/preview.js", "frontend/js/views/terminal.js",
                  "frontend/js/views/header.js", "frontend/js/views/dock.js", "frontend/js/lib/gcode.js",
                  "frontend/js/core/*.js", "frontend/js/stores/jobstore.js"],
        "html": ["panel-control"],
    },
    "machine-backend": {
        "desc": "Điều khiển máy phía backend: kết nối, giao thức, chạy G-code, hủy an toàn, máy giả",
        "files": ["backend/app/main.py", "backend/app/api/machine.py", "backend/app/api/__init__.py",
                  "backend/app/services/machine.py", "backend/app/services/job.py", "backend/app/links/base.py",
                  "backend/app/links/protocol.py", "backend/app/links/serial_link.py"],
    },
    "sim": {
        "desc": "Máy giả SimLink (lớn; chỉ lấy khi sửa hành vi giả lập)",
        "files": ["backend/app/links/sim_link.py"],
    },
    "draw-backend": {
        "desc": "Tab Tạo bản vẽ phía backend: ảnh/SVG → nét → G-code → bản thảo",
        "files": ["backend/app/api/draw.py", "backend/app/services/drawing/*.py"],
    },
    "draw-frontend": {
        "desc": "Tab Tạo bản vẽ phía frontend: form, canvas, bản thảo, xem trước độ sáng, thu nhỏ ảnh",
        "files": ["frontend/js/views/drawing.js", "frontend/js/views/drawing/*.js", "frontend/js/views/drafts.js",
                  "frontend/js/stores/draftstore.js", "frontend/js/lib/paper.js", "frontend/js/lib/imageprep.js",
                  "frontend/js/lib/drafts.js", "frontend/css/drawing.css"],
        "html": ["panel-drawing"],
    },
    "settings": {
        "desc": "Tab Cài đặt: kết nối, hoạt động, cấu hình máy, bản thảo",
        "files": ["frontend/js/views/settings.js", "backend/app/api/config.py", "backend/app/services/machine_config.py",
                  "backend/app/services/profile.py"],
        "html": ["panel-settings"],
    },
    "css": {
        "desc": "Toàn bộ giao diện CSS (màu ở tokens.css, tinh chỉnh ở polish.css)",
        "files": ["frontend/assets/css/tokens.css", "frontend/css/*.css"],
    },
    "i18n": {
        "desc": "Hai tệp dịch (rất lớn; chỉ lấy khi sửa chữ hiển thị)",
        "files": ["frontend/locales/vi.json", "frontend/locales/en.json"],
    },
    "tests-machine": {
        "desc": "Test backend phần máy",
        "files": ["backend/tests/*.py"],
    },
    "tests-draw": {
        "desc": "Test backend tab vẽ + test frontend",
        "files": ["backend/tests/draw_test/*.py", "frontend/tests/*.mjs"],
    },
}


# ---------------------------------------------------------------------------------- tệp
def tracked() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        names = [n for n in out.decode("utf-8").split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        names = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and ".venv" not in p.parts]
    result = []
    for n in names:
        p = Path(n)
        if p.suffix.lower() in SKIP_SUFFIXES or SKIP_PARTS & set(p.parts):
            continue
        full = ROOT / p
        if full.is_file() and full.stat().st_size <= MAX_FILE_BYTES:
            result.append(p)
    return sorted(result)


def match(patterns: list[str], files: list[Path]) -> list[Path]:
    picked: list[Path] = []
    for pat in patterns:
        hits = [f for f in files if f.match(pat) and (f.as_posix() == pat or "*" in pat)]
        if not hits and (ROOT / pat).is_file():
            hits = [Path(pat)]                            # tệp chưa add vào Git vẫn cho chọn đích danh
        for h in hits:
            if h not in picked:
                picked.append(h)
    return picked


def read(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def tokens(text: str) -> int:
    return round(len(text) / CHARS_PER_TOKEN)


def compact(text: str, drop_comments: bool, suffix: str) -> str:
    lines = [l.rstrip() for l in text.split("\n")]
    if drop_comments and suffix in (".py", ".js", ".mjs"):
        mark = "#" if suffix == ".py" else "//"
        keep = []
        for l in lines:
            s = l.strip()
            if s.startswith(mark) and not s.startswith(("#!", "# noqa", "# type:", "// eslint")):
                continue
            keep.append(l)
        lines = keep
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip("\n")
    return out + "\n"


def html_section(text: str, section_id: str) -> str | None:
    m = re.search(rf'<section\b[^>]*\bid="{re.escape(section_id)}"[^>]*>', text)
    if not m:
        return None
    end = text.find("</section>", m.end())
    return text[m.start(): end + len("</section>")] if end >= 0 else None


# ---------------------------------------------------------------------------------- xuất
def build(files: list[Path], html_ids: list[str], title: str, drop_comments: bool) -> tuple[str, list[tuple[str, int]]]:
    parts: list[tuple[str, str]] = []
    for f in files:
        suffix = f.suffix.lower()
        text = read(f)
        if suffix == ".md":
            text = text.strip("\n") + "\n"
        else:
            text = compact(text, drop_comments, suffix)
        parts.append((f.as_posix(), text))
    if html_ids:
        page = read(Path("frontend/index.html"))
        for sid in html_ids:
            block = html_section(page, sid)
            if block is None:
                print(f"! không thấy khối index.html id={sid}", file=sys.stderr)
                continue
            parts.append((f"frontend/index.html#{sid}", compact(block, False, ".html")))
    sizes = [(name, tokens(text)) for name, text in parts]
    head = [f"# Xuất mã nguồn: {title}", "",
            f"Tạo ngày {datetime.date.today().isoformat()} bằng tools/export_context.py. Ước tính ~{sum(s for _, s in sizes):,} token.",
            "Nếu mã khác với tài liệu thì **mã mới là sự thật**.", "", "Mục lục:"]
    head += [f"- `{name}` (~{n:,})" for name, n in sizes]
    body = []
    for name, text in parts:
        lang = LANG.get(Path(name.split("#")[0]).suffix.lower(), "")
        fence = "````" if "```" in text else "```"
        body.append(f"\n## {name}\n\n{fence}{lang}\n{text}{fence}")
    return "\n".join(head) + "\n" + "\n".join(body) + "\n", sizes


# ---------------------------------------------------------------------------------- bản đồ
def first_line(path: Path) -> str:
    text = read(path)
    suffix = path.suffix.lower()
    if suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text))
        except SyntaxError:
            doc = None
        return (doc or "").strip().split("\n")[0][:110]
    if suffix in (".js", ".mjs", ".css"):
        for l in text.split("\n")[:8]:
            s = l.strip()
            if s.startswith("//"):
                s = s.lstrip("/ ").strip()
                s = re.sub(r"^[\w/.\-]+\.(js|mjs)\s+[—–-]\s+", "", s)
                if s:
                    return s[:110]
            if s.startswith("/*"):
                s = s.strip("/* =").strip()
                if s:
                    return s[:110]
    return ""


ROUTE = re.compile(r'@router\.(get|post|put|patch|delete)\(\s*"([^"]*)"')
PREFIX = re.compile(r'APIRouter\(([^)]*)\)')


def routes() -> list[tuple[str, str, str]]:
    out = []
    for f in sorted((ROOT / "backend/app/api").glob("*.py")):
        text = f.read_text(encoding="utf-8")
        pm = PREFIX.search(text)
        prefix = ""
        if pm:
            m = re.search(r'prefix="([^"]*)"', pm.group(1))
            prefix = m.group(1) if m else ""
        for m in ROUTE.finditer(text):
            out.append((m.group(1).upper(), prefix + m.group(2), f.name))
    return out


def write_map() -> Path:
    files = tracked()
    rows: dict[str, list[str]] = {}
    total = 0
    for f in files:
        if f.suffix.lower() not in (".py", ".js", ".mjs", ".css", ".html", ".md", ".json"):
            continue
        n = tokens(read(f))
        total += n
        desc = first_line(f)
        if not desc and n < 120:                     # tệp rỗng / tí hon không cần một dòng trong bản đồ
            continue
        folder = f.parent.as_posix()
        rows.setdefault(folder, []).append(f"| `{f.name}` | ~{n:,} | {desc} |")
    lines = [
        "# CODEMAP — bản đồ mã nguồn (SINH TỰ ĐỘNG)", "",
        "Không sửa tay: chạy `python tools/export_context.py --map` để tạo lại. Cột token là ước tính (ký tự ÷ 3,2) để",
        "chọn đọc tệp nào; dòng mô tả lấy từ chú thích đầu tệp. Muốn đọc nhanh: xem bản đồ này, rồi chỉ lấy gói cần",
        f"(`python tools/export_context.py --list`). Toàn bộ dự án ~{total:,} token nếu đọc hết.", "",
        "## API backend (đọc từ `backend/app/api/*.py`)", "", "| Phương thức | Đường dẫn | Tệp |", "|---|---|---|",
    ]
    lines += [f"| {m} | `{p}` | {f} |" for m, p, f in routes()]
    lines += ["", "## Tệp theo thư mục", ""]
    for folder in sorted(rows):
        lines += [f"### `{folder}/`", "", "| Tệp | Token | Vai trò |", "|---|---|---|"] + rows[folder] + [""]
    target = ROOT / "docs" / "CODEMAP.md"
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return target


# ---------------------------------------------------------------------------------- dòng lệnh
def main() -> int:
    for stream in (sys.stdout, sys.stderr):          # Windows: bảng mã console mặc định không in được tiếng Việt
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Xuất mã nguồn gọn cho AI (xem docs/EXPORT_FOR_AI.md).")
    ap.add_argument("bundles", nargs="*", help="tên gói (xem --list)")
    ap.add_argument("--list", action="store_true", help="liệt kê gói và token ước tính")
    ap.add_argument("--files", nargs="+", default=[], help="thêm tệp / mẫu glob đích danh")
    ap.add_argument("--html", nargs="+", default=[], help="thêm khối index.html theo id (vd. panel-control)")
    ap.add_argument("--no-comments", action="store_true", help="bỏ dòng chú thích nguyên dòng (mất 'vì sao', chỉ dùng khi thiếu token)")
    ap.add_argument("--budget", type=int, default=0, help="cảnh báo nếu vượt chừng này token")
    ap.add_argument("--out", help="tệp đầu ra (mặc định export/<tên>-<ngày>.md)")
    ap.add_argument("--stdout", action="store_true", help="in ra màn hình thay vì ghi tệp")
    ap.add_argument("--map", action="store_true", help="viết lại docs/CODEMAP.md")
    args = ap.parse_args()

    if args.map:
        print("đã ghi", write_map().relative_to(ROOT))
        return 0
    files = tracked()
    if args.list or not (args.bundles or args.files or args.html):
        for name, b in BUNDLES.items():
            picked = match(b["files"], files)
            n = sum(tokens(read(p)) for p in picked)
            if b.get("html"):
                page = read(Path("frontend/index.html"))
                n += sum(tokens(html_section(page, i) or "") for i in b["html"])
            print(f"{name:16} ~{n:>7,} token  {b['desc']}")
        print("\nVí dụ: python tools/export_context.py control draw-backend --budget 40000")
        return 0

    picked: list[Path] = []
    html_ids = list(args.html)
    for name in args.bundles:
        if name not in BUNDLES:
            print(f"Không có gói '{name}'. Dùng --list.", file=sys.stderr)
            return 2
        for p in match(BUNDLES[name]["files"], files):
            if p not in picked:
                picked.append(p)
        html_ids += [i for i in BUNDLES[name].get("html", []) if i not in html_ids]
    for p in match(args.files, files):
        if p not in picked:
            picked.append(p)
    if not picked and not html_ids:
        print("Không chọn được tệp nào.", file=sys.stderr)
        return 2

    title = ", ".join(args.bundles + (["tệp chọn"] if args.files else [])) or "tuỳ chọn"
    text, sizes = build(picked, html_ids, title, args.no_comments)
    total = sum(n for _, n in sizes)
    if args.stdout:
        sys.stdout.write(text)
    else:
        out = Path(args.out) if args.out else ROOT / "export" / f"{'+'.join(args.bundles) or 'custom'}-{datetime.date.today():%Y%m%d}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"đã ghi {out}  ({len(picked) + len(html_ids)} phần, ~{total:,} token)")
    if args.budget and total > args.budget:
        print(f"! vượt ngân sách {args.budget:,}: bỏ bớt gói, hoặc dùng --files chỉ lấy tệp cần, hoặc --no-comments", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
