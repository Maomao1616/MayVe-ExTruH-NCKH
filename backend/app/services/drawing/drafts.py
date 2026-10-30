"""Bản thảo trên đĩa: G-code từng lớp + ảnh minh họa + meta.json, mỗi bản một thư mục con.

    <thư mục bản thảo>/<yyyymmdd-hhmmss>-<tên>/
        meta.json   draw[-<lớp>].gcode   preview.svg

Thư mục gốc đặt ở Cài đặt (draw_settings.json). Tên thư mục và tên tệp kiểm bằng regex, đường dẫn không
bao giờ ghép từ chuỗi người dùng gửi lên. Ghi nguyên tử (thư mục tạm rồi đổi tên). Vượt hạn mức thì xóa
bản CŨ NHẤT không ghim.
"""
from __future__ import annotations

import json
import math
import re
import shutil
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from .errors import DrawError
from .preview import build as build_preview
from .shapes import Layer

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
SETTINGS_PATH = DATA_DIR / "draw_settings.json"
DEFAULT_DIR = DATA_DIR / "drafts"

DEFAULTS = {"draft_dir": "", "max_count": 50, "max_mb": 500}
LIMITS = {"max_count": (1, 1000), "max_mb": (10, 100000)}

ID_RE = re.compile(r"^\d{8}-\d{6}-[a-z0-9-]{1,40}$")
LAYER_FILE_RE = re.compile(r"^draw(-[A-Za-z0-9_-]{1,40})?$")
PALETTE = ("#222222", "#c0392b", "#2471a3", "#1e8449", "#b9770e")      # màu minh họa các lớp (nền giấy sáng)

_lock = threading.RLock()


# --- cài đặt -------------------------------------------------------------------------
def validate_settings(data: dict) -> dict:
    out: dict = {}
    folder = data.get("draft_dir", DEFAULTS["draft_dir"])
    if not isinstance(folder, str) or len(folder) > 500 or "\x00" in folder:
        raise DrawError("bad_param", "draft_dir: phải là đường dẫn thư mục.")
    folder = folder.strip()
    if folder:
        path = Path(folder)
        if not path.is_absolute() or ".." in path.parts:
            raise DrawError("bad_param", "draft_dir: phải là đường dẫn tuyệt đối, không chứa '..'.")
    out["draft_dir"] = folder
    for key, (lo, hi) in LIMITS.items():
        v = data.get(key, DEFAULTS[key])
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v != int(v):
            raise DrawError("bad_param", f"{key}: phải là số nguyên.")
        if not lo <= v <= hi:
            raise DrawError("bad_param", f"{key}: ngoài khoảng {lo}–{hi}.")
        out[key] = int(v)
    return out


def load_settings() -> dict:
    with _lock:
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            return validate_settings(data if isinstance(data, dict) else {})
        except (OSError, ValueError, DrawError):
            return dict(DEFAULTS)


def save_settings(data: dict) -> dict:
    clean = validate_settings(data)
    root = Path(clean["draft_dir"]) if clean["draft_dir"] else DEFAULT_DIR
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DrawError("bad_param", f"draft_dir: không tạo/ghi được thư mục ({exc.strerror}).") from exc
    with _lock:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(clean, indent=2), encoding="utf-8")
        tmp.replace(SETTINGS_PATH)
    return clean


def root_dir() -> Path:
    s = load_settings()
    return Path(s["draft_dir"]) if s["draft_dir"] else DEFAULT_DIR


# --- tên / đường dẫn an toàn ---------------------------------------------------------
def slug(name: str) -> str:
    text = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40].strip("-")
    return text or "ban-ve"


def _dir(draft_id: str) -> Path:
    if not ID_RE.match(draft_id or ""):
        raise DrawError("unknown_draft", "Bản thảo không tồn tại.", 404)
    path = root_dir() / draft_id
    if not path.is_dir():
        raise DrawError("unknown_draft", "Bản thảo không tồn tại.", 404)
    return path


def _read_meta(path: Path) -> dict | None:
    try:
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        return meta if isinstance(meta, dict) else None
    except (OSError, ValueError):
        return None


def _write_meta(path: Path, meta: dict) -> None:
    tmp = path / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path / "meta.json")


def _size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


# --- ảnh minh họa --------------------------------------------------------------------
def preview_svg(placed: list[Layer], machine_w: float, machine_h: float, paper: dict) -> str:
    data = build_preview(placed, tol=0.1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {machine_w:g} {machine_h:g}" '
             f'width="{machine_w:g}mm" height="{machine_h:g}mm">',
             '<rect width="100%" height="100%" fill="#141414"/>',
             f'<rect x="{paper["x"]:g}" y="{paper["y"]:g}" width="{paper["w"]:g}" height="{paper["h"]:g}" '
             'fill="#fafafa"/>']
    for i, layer in enumerate(data["layers"]):
        color = PALETTE[i % len(PALETTE)]
        d = " ".join("M" + " L".join(f"{x:g} {y:g}" for x, y in s) for s in layer["strokes"] if len(s) >= 2)
        parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="0.3" '
                     'stroke-linecap="round" stroke-linejoin="round"/>')
    parts.append("</svg>")
    return "\n".join(parts)


# --- tạo / liệt kê / sửa / xóa -------------------------------------------------------
def create(name: str, result: dict, placed: list[Layer], machine: dict, params: dict) -> dict:
    root = root_dir()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DrawError("draft_dir_unwritable", f"Không ghi được thư mục bản thảo ({exc.strerror}).", 500) from exc
    now = datetime.now()
    with _lock:
        base = f"{now:%Y%m%d-%H%M%S}-{slug(name)}"
        draft_id, n = base, 1
        while (root / draft_id).exists():
            n += 1
            draft_id = f"{base[:60]}-{n}"
        tmp = root / f".tmp-{draft_id}"
        tmp.mkdir()
        try:
            for f in result["files"]:
                (tmp / f"{f['name']}.gcode").write_text(f["gcode"], encoding="utf-8", newline="\n")
            (tmp / "preview.svg").write_text(
                preview_svg(placed, machine["work_w"], machine["work_h"], result["paper"]), encoding="utf-8")
            meta = {"id": draft_id, "name": name or "Bản vẽ", "created": now.isoformat(timespec="seconds"),
                    "pinned": False, "priority": 0,
                    "files": [{"layer": f["layer"], "name": f["name"], "stats": f["stats"]} for f in result["files"]],
                    "paper": result["paper"], "box": result["box"], "warnings": result["warnings"],
                    "params": params}
            _write_meta(tmp, meta)
            tmp.rename(root / draft_id)
        except OSError as exc:
            shutil.rmtree(tmp, ignore_errors=True)
            raise DrawError("draft_dir_unwritable", f"Không ghi được bản thảo ({exc.strerror}).", 500) from exc
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        _prune(root, draft_id)
    return meta


def list_drafts() -> list[dict]:
    root = root_dir()
    out = []
    if root.is_dir():
        for path in root.iterdir():
            if path.is_dir() and ID_RE.match(path.name):
                meta = _read_meta(path)
                if meta:
                    out.append(meta)
    out.sort(key=lambda m: (m.get("created", ""), m["id"]), reverse=True)        # mới nhất trước
    out.sort(key=lambda m: (bool(m.get("pinned")), int(m.get("priority", 0))), reverse=True)  # ghim, ưu tiên lên đầu
    return out


def get(draft_id: str) -> dict:
    meta = _read_meta(_dir(draft_id))
    if meta is None:
        raise DrawError("unknown_draft", "Bản thảo hỏng (thiếu meta.json).", 404)
    return meta


def read_gcode(draft_id: str, layer_file: str) -> str:
    if not LAYER_FILE_RE.match(layer_file or ""):
        raise DrawError("unknown_draft", "Không có tệp G-code này.", 404)
    path = _dir(draft_id) / f"{layer_file}.gcode"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        raise DrawError("unknown_draft", "Không có tệp G-code này.", 404) from None


def read_preview(draft_id: str) -> str:
    try:
        return (_dir(draft_id) / "preview.svg").read_text(encoding="utf-8")
    except OSError:
        raise DrawError("unknown_draft", "Bản thảo không có ảnh minh họa.", 404) from None


def update(draft_id: str, name: str | None, pinned: bool | None, priority: int | None) -> dict:
    with _lock:
        path = _dir(draft_id)
        meta = get(draft_id)
        if name is not None:
            name = name.strip()
            if not name or len(name) > 80:
                raise DrawError("bad_param", "name: 1–80 ký tự.")
            meta["name"] = name
        if pinned is not None:
            meta["pinned"] = bool(pinned)
        if priority is not None:
            if not -1000 <= priority <= 1000:
                raise DrawError("bad_param", "priority: ngoài khoảng -1000..1000.")
            meta["priority"] = int(priority)
        _write_meta(path, meta)
    return meta


def delete(draft_id: str) -> None:
    with _lock:
        shutil.rmtree(_dir(draft_id), ignore_errors=True)


def _prune(root: Path, keep_id: str) -> None:
    """Giữ trong hạn mức: xóa bản cũ nhất không ghim. Bản ghim không tính vào hạn mức và không bị xóa;
    bản vừa tạo (`keep_id`) cũng không bị xóa."""
    s = load_settings()
    loose = sorted((m for m in list_drafts() if not m.get("pinned")), key=lambda m: m.get("created", ""))
    total = sum(_size(root / m["id"]) for m in loose)
    count = len(loose)
    for m in loose:
        if count <= s["max_count"] and total <= s["max_mb"] * 1024 * 1024:
            break
        if m["id"] == keep_id:
            continue
        path = root / m["id"]
        total -= _size(path)
        count -= 1
        shutil.rmtree(path, ignore_errors=True)
