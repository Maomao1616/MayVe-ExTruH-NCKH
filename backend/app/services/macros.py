"""Macro (nút chạy nhanh) lưu trên máy chủ: mỗi macro một tệp `<thư mục dữ liệu>/macros/<id>.json`.

Lưu ở máy chủ (không phải trình duyệt) để mọi máy/trình duyệt thấy cùng một bộ và để xem được trong
Cài đặt → Lưu trữ. Quy tắc kiểm tra khớp frontend/js/stores/macros.js; backend vẫn là lớp chặn cuối cùng
(G-code còn qua clean_gcode khi chạy). Tên tệp chỉ sinh từ id do máy chủ tạo, không bao giờ từ chuỗi gửi lên.
"""
from __future__ import annotations

import json
import re
import secrets
import threading
import time

from .. import paths

LIMITS = {"name": 40, "lines": 50, "line_len": 200, "count": 30}
ID_RE = re.compile(r"^m_[a-z0-9]{6,12}$")
_PAREN = re.compile(r"\([^)]*\)")
_REALTIME = re.compile(r"[?!~\x18]")
_lock = threading.Lock()


class MacroError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _clean_line(raw: str) -> str:
    line = _PAREN.sub("", str(raw).split(";", 1)[0]).strip()
    if not line or line.startswith("%"):
        return ""
    return re.sub(r"\s+", " ", line)


def validate(data: dict) -> dict:
    """Trả macro đã làm sạch {name, type, lines, needsHome} hoặc ném MacroError(code = khóa lỗi)."""
    name = str(data.get("name", "")).strip()
    if not name or len(name) > LIMITS["name"]:
        raise MacroError("name", "Tên macro phải từ 1 đến 40 ký tự.")
    kind = data.get("type")
    if kind not in ("gcode", "command"):
        raise MacroError("type", "Loại macro phải là gcode hoặc command.")
    raw = data.get("lines", [])
    if isinstance(raw, str):
        raw = raw.splitlines()
    if not isinstance(raw, list):
        raise MacroError("lines_empty", "Nội dung macro không hợp lệ.")
    lines = [c for c in (_clean_line(x) for x in raw) if c]
    if not lines:
        raise MacroError("lines_empty", "Macro chưa có dòng lệnh nào.")
    if len(lines) > LIMITS["lines"]:
        raise MacroError("lines_too_many", f"Tối đa {LIMITS['lines']} dòng.")
    if any(len(x) > LIMITS["line_len"] for x in lines):
        raise MacroError("line_too_long", f"Mỗi dòng tối đa {LIMITS['line_len']} ký tự.")
    if any(_REALTIME.search(x) for x in lines):
        raise MacroError("realtime_char", "Không dùng ký tự ? ! ~ trong macro.")
    if kind == "gcode" and any(x.startswith("$") for x in lines):
        raise MacroError("no_dollar", "Dòng bắt đầu bằng $ chỉ dùng ở loại Lệnh đơn.")
    if kind == "command" and len(lines) > 1:
        raise MacroError("command_one_line", "Lệnh đơn chỉ được một dòng.")
    return {"name": name, "type": kind, "lines": lines, "needsHome": data.get("needsHome") is True}


def _file(macro_id: str):
    if not ID_RE.match(macro_id or ""):
        raise MacroError("not_found", "Không có macro này.", 404)
    return paths.macros_dir() / f"{macro_id}.json"


def _read(path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not ID_RE.match(str(data.get("id", ""))):
            return None
        return {"id": data["id"], "created": data.get("created", ""), **validate(data)}
    except (OSError, ValueError, MacroError):
        return None          # tệp hỏng hoặc sửa tay sai: bỏ qua, không làm hỏng cả danh sách


def list_macros() -> list[dict]:
    folder = paths.macros_dir()
    if not folder.is_dir():
        return []
    items = [m for m in (_read(p) for p in folder.glob("m_*.json")) if m]
    items.sort(key=lambda m: (m["created"], m["id"]))
    return items


def _write(macro: dict) -> None:
    folder = paths.macros_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        target = _file(macro["id"])
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(macro, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(target)
    except OSError as exc:
        raise MacroError("storage", f"Không ghi được macro ({exc.strerror}).", 500) from exc


def _check_name_free(name: str, own_id: str | None, existing: list[dict]) -> None:
    if any(m["id"] != own_id and m["name"].lower() == name.lower() for m in existing):
        raise MacroError("name_taken", "Đã có macro cùng tên.")


def create(data: dict) -> dict:
    clean = validate(data)
    with _lock:
        existing = list_macros()
        if len(existing) >= LIMITS["count"]:
            raise MacroError("too_many", f"Tối đa {LIMITS['count']} macro.")
        _check_name_free(clean["name"], None, existing)
        macro_id = "m_" + secrets.token_hex(4)
        macro = {"id": macro_id, "created": time.strftime("%Y-%m-%dT%H:%M:%S"), **clean}
        _write(macro)
    return macro


def update(macro_id: str, data: dict) -> dict:
    clean = validate(data)
    with _lock:
        old = _read(_file(macro_id))
        if old is None:
            raise MacroError("not_found", "Không có macro này.", 404)
        _check_name_free(clean["name"], macro_id, list_macros())
        macro = {"id": macro_id, "created": old["created"], **clean}
        _write(macro)
    return macro


def delete(macro_id: str) -> None:
    with _lock:
        try:
            _file(macro_id).unlink()
        except FileNotFoundError:
            raise MacroError("not_found", "Không có macro này.", 404) from None
        except OSError as exc:
            raise MacroError("storage", f"Không xóa được macro ({exc.strerror}).", 500) from exc
