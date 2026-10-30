"""Tài liệu và công cụ xuất mã không được mục: gói xuất phải trỏ tới tệp có thật, liên kết trong docs phải sống."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_tool():
    spec = importlib.util.spec_from_file_location("export_context", ROOT / "tools" / "export_context.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_bundle_matches_real_files_and_html_sections():
    tool = load_tool()
    files = tool.tracked()
    page = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    for name, bundle in tool.BUNDLES.items():
        for pattern in bundle["files"]:
            assert tool.match([pattern], files), f"gói {name}: mẫu '{pattern}' không khớp tệp nào"
        for section in bundle.get("html", []):
            assert tool.html_section(page, section), f"gói {name}: index.html không có khối {section}"


def test_export_builds_a_bundle_and_reports_tokens():
    tool = load_tool()
    text, sizes = tool.build(tool.match(tool.BUNDLES["docs"]["files"], tool.tracked()), [], "docs", False)
    assert sizes and text.startswith("# Xuất mã nguồn") and all(n > 0 for _, n in sizes)


def test_markdown_links_between_docs_resolve():
    broken = []
    for doc in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        for target in re.findall(r"\]\(([^)#\s]+)\)", doc.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (doc.parent / target).resolve().exists():
                broken.append(f"{doc.name} -> {target}")
    assert not broken, broken


def test_core_docs_exist_and_old_names_are_gone():
    for name in ("AI_START", "STATUS", "ARCHITECTURE", "CODEMAP", "DECISIONS", "MACHINE", "EXPORT_FOR_AI", "PLAN_ONLINE"):
        assert (ROOT / "docs" / f"{name}.md").is_file(), name
    for old in ("PROJECT_MAP", "HANDOVER"):
        assert not (ROOT / "docs" / f"{old}.md").exists(), old
