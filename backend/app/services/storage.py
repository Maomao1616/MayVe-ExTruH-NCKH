"""Xem nội dung thư mục dữ liệu qua giao diện (MiniPC không có màn hình để mở thư mục).

Chỉ ĐỌC: liệt kê ba thư mục cố định (bản thảo, sao lưu cấu hình, macro) và các tệp lẻ ở gốc, cho tải một
tệp về. Đường dẫn không bao giờ ghép từ chuỗi người dùng: `area` phải thuộc paths.AREAS, `path` tối đa hai
cấp, mỗi cấp khớp regex và kết quả phải nằm trong thư mục của `area`.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .. import paths

MAX_ENTRIES = 200            # số mục tối đa liệt kê mỗi thư mục (mới nhất trước)
MAX_CHILDREN = 20            # số tệp con tối đa liệt kê trong mỗi thư mục con
_PART = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._\- ]{0,119}$")
_DOWNLOADABLE = {".json", ".gcode", ".svg", ".yaml", ".yml"}


class StorageError(Exception):
    def __init__(self, code: str, message: str, status: int = 404) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _entry(path: Path) -> dict:
    stat = path.stat()
    if path.is_dir():
        files = sorted((f for f in path.iterdir() if f.is_file()), key=lambda f: f.name)
        return {"name": path.name, "kind": "dir", "size": _dir_size(path), "modified": _iso(stat.st_mtime),
                "files": [{"name": f.name, "size": f.stat().st_size} for f in files[:MAX_CHILDREN]],
                "more": max(0, len(files) - MAX_CHILDREN)}
    return {"name": path.name, "kind": "file", "size": stat.st_size, "modified": _iso(stat.st_mtime)}


def _area(key: str) -> dict:
    folder = paths.area_dir(key)
    out = {"key": key, "path": str(folder), "exists": folder.is_dir(), "count": 0, "bytes": 0,
           "entries": [], "more": 0}
    if not out["exists"]:
        return out
    children = [c for c in folder.iterdir() if not c.name.startswith(".")]
    children.sort(key=lambda c: c.stat().st_mtime, reverse=True)
    out["count"] = len(children)
    out["bytes"] = sum(_dir_size(c) if c.is_dir() else c.stat().st_size for c in children)
    out["entries"] = [_entry(c) for c in children[:MAX_ENTRIES]]
    out["more"] = max(0, len(children) - MAX_ENTRIES)
    return out


def overview() -> dict:
    root = paths.DATA_DIR
    loose = []
    if root.is_dir():
        for f in sorted(root.iterdir(), key=lambda f: f.name):
            if f.is_file() and not f.name.endswith(".tmp"):
                loose.append({"name": f.name, "size": f.stat().st_size, "modified": _iso(f.stat().st_mtime)})
    return {"root": str(root), "areas": [_area(k) for k in paths.AREAS], "files": loose}


def resolve_file(area: str, path: str) -> Path:
    """Đường dẫn thật của một tệp trong `area`, hoặc StorageError."""
    if area not in paths.AREAS:
        raise StorageError("unknown_area", "Thư mục không tồn tại.")
    parts = (path or "").split("/")
    if not 1 <= len(parts) <= 2 or not all(_PART.match(p) and ".." not in p for p in parts):
        raise StorageError("bad_path", "Đường dẫn tệp không hợp lệ.", 400)
    base = paths.area_dir(area).resolve()
    target = base.joinpath(*parts).resolve()
    if base not in target.parents or not target.is_file() or target.suffix.lower() not in _DOWNLOADABLE:
        raise StorageError("not_found", "Không có tệp này.")
    return target
