"""Ảnh khách gửi: khách (không đăng nhập) chọn ảnh + cắt + khổ giấy + kiểu nét "mong muốn" rồi bấm "Gửi ảnh"; quản lý mở từng mục
để tạo nét. Lưu ở data/customer/<id>/ (image.jpg đã thu nhỏ + meta.json), TỰ XÓA sau `customer_days` ngày (mặc định 5).

An toàn (khách là người lạ):
  * ảnh được GIẢI MÃ rồi ghi lại thành JPEG (không bao giờ ghi nguyên tệp khách gửi), tối đa MAX_SIDE điểm ảnh, MAX_IMAGE_BYTES;
  * thông số đi kèm chỉ nhận {khóa chữ thường/số/gạch: chuỗi ngắn / số / bool}, tổng nhỏ: sau này quản lý đổ vào các ô nhập;
  * giới hạn: số lần gửi mỗi giờ theo từng nguồn (CF-Connecting-IP nếu qua Cloudflare), tổng số mục, tổng dung lượng;
  * mã mục sinh ngẫu nhiên, đường dẫn chỉ ghép từ mã đã kiểm bằng biểu thức chính quy (không nhận đường dẫn từ khách).
Dọn bản quá hạn mỗi lần gửi / liệt kê (không có luồng nền).
"""
from __future__ import annotations

import io
import json
import re
import secrets
import shutil
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from .. import paths
from .drawing import drafts
from .drawing.errors import DrawError

ID_RE = re.compile(r"^\d{8}-\d{6}-[a-f0-9]{8}$")
KEY_RE = re.compile(r"^[a-z0-9-]{1,40}$")
LIMITS = {"image_bytes": 3 * 1024 * 1024, "max_items": 100, "max_total_bytes": 300 * 1024 * 1024, "per_hour": 6,
          "name": 40, "note": 200, "params_bytes": 8192, "max_side": 1600, "max_pixels": 60_000_000}

_lock = threading.RLock()
_sent: dict[str, deque] = defaultdict(deque)          # nguồn -> giờ các lần gửi gần đây


def root() -> Path:
    return paths.DATA_DIR / "customer"


def keep_days() -> int:
    return int(drafts.load_settings()["customer_days"])


def _dir(item_id: str) -> Path:
    if not ID_RE.match(item_id or ""):
        raise DrawError("not_found", "Không có mục này.", 404)
    return root() / item_id


def _read_meta(path: Path) -> dict | None:
    try:
        return json.loads((path / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.glob("*") if f.is_file())


def purge(now: float | None = None) -> int:
    """Xóa mục quá hạn (và thư mục hỏng). Trả số mục đã xóa."""
    base = root()
    if not base.is_dir():
        return 0
    limit = (now if now is not None else time.time()) - keep_days() * 86400
    removed = 0
    with _lock:
        for path in base.iterdir():
            if not path.is_dir():
                continue
            meta = _read_meta(path) if ID_RE.match(path.name) else None
            try:
                stale = meta.get("created_ts", 0) < limit if meta is not None else path.stat().st_mtime < limit
            except OSError:
                continue
            if stale:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
    return removed


def _clean_params(raw) -> dict:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise DrawError("bad_param", "params: phải là đối tượng JSON.")
    out: dict = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not KEY_RE.match(key):
            raise DrawError("bad_param", "params: tên khóa không hợp lệ.")
        if isinstance(value, bool) or isinstance(value, (int, float)):
            out[key] = value
        elif isinstance(value, str) and len(value) <= 40:
            out[key] = value
        elif isinstance(value, dict) and key == "crop":
            crop = {k: float(value[k]) for k in ("x", "y", "w", "h") if isinstance(value.get(k), (int, float))}
            if len(crop) == 4 and all(0 <= v <= 1 for v in crop.values()):
                out[key] = crop
        elif value is None:
            continue
        else:
            raise DrawError("bad_param", f"params.{key}: giá trị không hợp lệ.")
    if len(json.dumps(out)) > LIMITS["params_bytes"]:
        raise DrawError("bad_param", "params: quá dài.")
    return out


def _encode_jpeg(data: bytes) -> tuple[bytes, tuple[int, int]]:
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        if im.width * im.height > LIMITS["max_pixels"]:
            raise DrawError("bad_image", "Ảnh có quá nhiều điểm ảnh.", 413)
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            background = Image.new("RGB", im.size, (255, 255, 255))      # nền trong suốt -> trắng (giấy)
            background.paste(im, mask=im.getchannel("A"))
            im = background
        else:
            im = im.convert("RGB")
    except DrawError:
        raise
    except Exception:
        raise DrawError("bad_image", "Không đọc được ảnh (tệp hỏng hoặc sai định dạng).") from None
    im.thumbnail((LIMITS["max_side"], LIMITS["max_side"]))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue(), im.size


def create(data: bytes, filename: str, name: str, note: str, params, source: str) -> dict:
    if not data:
        raise DrawError("bad_image", "Chưa chọn ảnh.")
    if len(data) > LIMITS["image_bytes"]:
        raise DrawError("file_too_large", f"Ảnh lớn hơn {LIMITS['image_bytes'] // (1024 * 1024)} MB.", 413)
    name = re.sub(r"\s+", " ", (name or "").strip())[: LIMITS["name"]]
    note = re.sub(r"[ \t]+", " ", (note or "").strip())[: LIMITS["note"]]
    clean = _clean_params(params)
    jpeg, size = _encode_jpeg(data)
    purge()
    now = time.time()
    with _lock:
        recent = _sent[source]
        while recent and now - recent[0] > 3600:
            recent.popleft()
        if len(recent) >= LIMITS["per_hour"]:
            raise DrawError("too_many_sends", f"Bạn đã gửi {LIMITS['per_hour']} ảnh trong một giờ. Hãy thử lại sau.", 429)
        base = root()
        base.mkdir(parents=True, exist_ok=True)
        items = [p for p in base.iterdir() if p.is_dir() and ID_RE.match(p.name)]
        if len(items) >= LIMITS["max_items"] or sum(_size(p) for p in items) + len(jpeg) > LIMITS["max_total_bytes"]:
            raise DrawError("inbox_full", "Hộp ảnh khách đang đầy. Báo chủ máy dọn bớt rồi gửi lại.", 507)
        item_id = f"{datetime.fromtimestamp(now):%Y%m%d-%H%M%S}-{secrets.token_hex(4)}"
        tmp = base / f".tmp-{item_id}"
        tmp.mkdir()
        try:
            (tmp / "image.jpg").write_bytes(jpeg)
            meta = {"id": item_id, "created": datetime.fromtimestamp(now).isoformat(timespec="seconds"), "created_ts": now,
                    "name": name, "note": note, "filename": re.sub(r"[^\w.\- ]", "_", filename or "anh")[:60],
                    "width": size[0], "height": size[1], "bytes": len(jpeg), "seen": False, "params": clean}
            (tmp / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            tmp.rename(base / item_id)
        except OSError as exc:
            shutil.rmtree(tmp, ignore_errors=True)
            raise DrawError("inbox_unwritable", f"Không ghi được ảnh ({exc.strerror}).", 500) from exc
        recent.append(now)
    return _public(meta)


def _public(meta: dict) -> dict:
    out = {k: v for k, v in meta.items() if k != "created_ts"}
    out["expires"] = datetime.fromtimestamp(meta["created_ts"] + keep_days() * 86400).isoformat(timespec="minutes")
    return out


def list_items() -> list[dict]:
    purge()
    base = root()
    items = []
    if base.is_dir():
        for path in base.iterdir():
            if path.is_dir() and ID_RE.match(path.name):
                meta = _read_meta(path)
                if meta:
                    items.append(_public(meta))
    items.sort(key=lambda m: m["created"], reverse=True)
    return items


def get(item_id: str) -> dict:
    meta = _read_meta(_dir(item_id))
    if meta is None:
        raise DrawError("not_found", "Không có mục này.", 404)
    return _public(meta)


def image_path(item_id: str) -> Path:
    path = _dir(item_id) / "image.jpg"
    if not path.is_file():
        raise DrawError("not_found", "Không có mục này.", 404)
    return path


def mark_seen(item_id: str) -> dict:
    with _lock:
        path = _dir(item_id)
        meta = _read_meta(path)
        if meta is None:
            raise DrawError("not_found", "Không có mục này.", 404)
        meta["seen"] = True
        (path / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return _public(meta)


def delete(item_id: str) -> None:
    with _lock:
        path = _dir(item_id)
        if not path.is_dir():
            raise DrawError("not_found", "Không có mục này.", 404)
        shutil.rmtree(path, ignore_errors=True)


def reset_rate_limit() -> None:
    """Chỉ cho test."""
    with _lock:
        _sent.clear()
