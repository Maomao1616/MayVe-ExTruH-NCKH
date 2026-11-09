"""Số liệu thật của từng lần chạy máy: mỗi báo cáo trạng thái ghi một dòng vào data/job_logs/<id>.csv.

Dùng để vẽ biểu đồ (tốc độ thật, bộ đệm, Z) và so sánh các lần chạy: biết máy có "đói lệnh" không, thời gian thật
so với ước tính, bao nhiêu thời gian là vẽ / nhấc bút. Mỗi lần chạy gồm hai tệp cùng tên:
    <id>.csv    cột: t (giây từ lúc bắt đầu), state, x, y, z (tọa độ làm việc), feed (mm/phút thật, `FS:`),
                bf_planner (khối còn trống trong hàng đợi chuyển động, `Bf:`), bf_rx, sent, acked (dòng đã gửi / đã `ok`)
    <id>.json   thông tin chạy (tên, giờ, số dòng, ước tính của giao diện) + tóm tắt khi xong
<id> = YYYYmmdd-HHMMSS-<số tác vụ>. Giữ KEEP_FILES lần gần nhất (và không quá KEEP_BYTES).

Quy tắc an toàn: ghi nhật ký KHÔNG BAO GIỜ được làm hỏng việc đọc / ghi serial. Mọi lỗi đĩa chỉ tắt nhật ký của lần chạy đó.
Báo cáo trạng thái tới ~10 lần/giây; `Bf:` chỉ có khi `$10` có bit 2 (máy thật đang để `$10=1` nên phải đặt `$10=3`).
"""
from __future__ import annotations

import csv
import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from .. import paths

COLUMNS = ("t", "state", "x", "y", "z", "feed", "bf_planner", "bf_rx", "sent", "acked")
KEEP_FILES = 30
KEEP_BYTES = 150 * 1024 * 1024
FLUSH_S = 2.0
PEN_DOWN_TOL = 0.5               # mm: Z cách Z xuống không quá chừng này = bút xuống (như lib/gcode.js)
ID_RE = re.compile(r"\d{8}-\d{6}-\d{1,9}")
_ACTIVE = ("running", "finishing")


class JobLogError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def logs_dir() -> Path:
    return paths.DATA_DIR / "job_logs"


def _num(value, digits: int) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def _meta_path(log_id: str) -> Path:
    return logs_dir() / f"{log_id}.json"


def _csv_path(log_id: str) -> Path:
    return logs_dir() / f"{log_id}.csv"


def _check_id(log_id: str) -> str:
    if not ID_RE.fullmatch(log_id or ""):
        raise JobLogError("bad_param", "Mã nhật ký không hợp lệ.")
    return log_id


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


class JobLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fh = None
        self._writer = None
        self._id: str | None = None
        self._job_id: int | None = None
        self._meta: dict = {}
        self._t0 = 0.0
        self._last_flush = 0.0

    # --- được MachineService gọi mỗi khi có báo cáo trạng thái / ngắt kết nối --------------
    def observe(self, job: dict | None, status: dict | None, extra: dict | None = None) -> None:
        try:
            with self._lock:
                active = job is not None and job.get("state") in _ACTIVE
                if self._job_id is not None and (job is None or job.get("id") != self._job_id or not active):
                    self._end(job if job is not None and job.get("id") == self._job_id else None)
                if active and self._job_id is None:
                    self._begin(job, status, extra or {})
                if self._job_id is not None and active and status is not None:
                    self._sample(job, status)
        except Exception:          # noqa: BLE001 — nhật ký không được làm hỏng luồng đọc serial
            self._drop()

    def close(self, reason: str = "disconnected") -> None:
        """Mất kết nối / tắt máy chủ: khép nhật ký đang mở."""
        try:
            with self._lock:
                if self._job_id is not None:
                    self._end(None, reason)
        except Exception:          # noqa: BLE001
            self._drop()

    @property
    def current_id(self) -> str | None:
        with self._lock:
            return self._id

    # --- nội bộ (đang giữ self._lock) -------------------------------------------------------
    def _begin(self, job: dict, status: dict | None, extra: dict) -> None:
        directory = logs_dir()
        directory.mkdir(parents=True, exist_ok=True)
        started = float(job.get("started_at") or time.time())
        self._id = f"{datetime.fromtimestamp(started):%Y%m%d-%H%M%S}-{int(job['id'])}"
        self._job_id = job["id"]
        self._t0 = started
        self._meta = {
            "id": self._id, "name": str(job.get("name", "")), "mode": extra.get("mode"),
            "started_at": started, "finished_at": None, "state": "running",
            "total": job.get("total"), "acked": 0,
            "pen_down_z": extra.get("pen_down_z", 0.0),
            "has_bf": False,
            "client": extra.get("client") or {},        # ước tính / số liệu G-code do giao diện gửi kèm
        }
        _write_json(_meta_path(self._id), self._meta)
        self._fh = open(_csv_path(self._id), "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._writer.writerow(COLUMNS)
        self._last_flush = time.monotonic()
        self._prune()

    def _sample(self, job: dict, status: dict) -> None:
        if self._writer is None:
            return
        wpos = status.get("wpos") or status.get("mpos") or []
        coords = [wpos[i] if len(wpos) > i else None for i in range(3)]
        bf = status.get("planner_free")
        if bf is not None:
            self._meta["has_bf"] = True
        self._writer.writerow([
            _num(time.time() - self._t0, 2), status.get("state") or "",
            _num(coords[0], 3), _num(coords[1], 3), _num(coords[2], 3),
            _num(status.get("feed"), 0), "" if bf is None else bf,
            "" if status.get("rx_free") is None else status["rx_free"],
            job.get("sent", ""), job.get("acked", ""),
        ])
        now = time.monotonic()
        if now - self._last_flush >= FLUSH_S:
            self._fh.flush()
            self._last_flush = now

    def _end(self, job: dict | None, reason: str | None = None) -> None:
        log_id, meta = self._id, dict(self._meta)
        try:
            if self._fh is not None:
                self._fh.flush()
                self._fh.close()
        finally:
            self._fh = self._writer = None
            self._id = self._job_id = None
        if job is not None:
            meta["state"] = job.get("state") or "done"
            meta["acked"] = job.get("acked", meta.get("acked"))
            meta["finished_at"] = job.get("finished_at") or time.time()
        else:
            meta["state"] = reason or "aborted"
            meta["finished_at"] = time.time()
        meta["elapsed_s"] = round(meta["finished_at"] - meta["started_at"], 1)
        # Tóm tắt đọc lại cả tệp: làm ở luồng riêng để không chặn luồng đọc serial.
        threading.Thread(target=_finalize, args=(log_id, meta), name="joblog-summary", daemon=True).start()

    def _drop(self) -> None:
        try:
            if self._fh is not None:
                self._fh.close()
        except OSError:
            pass
        self._fh = self._writer = None
        self._id = self._job_id = None

    def _prune(self) -> None:
        files = sorted(logs_dir().glob("*.csv"))
        keep = [f for f in files if f.stem == self._id]
        old = [f for f in files if f.stem != self._id]
        total = sum(f.stat().st_size for f in files)
        while old and (len(old) + len(keep) > KEEP_FILES or total > KEEP_BYTES):
            victim = old.pop(0)                    # tên bắt đầu bằng ngày giờ: sắp theo tên = từ cũ tới mới
            total -= victim.stat().st_size
            for path in (victim, victim.with_suffix(".json")):
                try:
                    path.unlink()
                except OSError:
                    pass


def _finalize(log_id: str, meta: dict) -> None:
    try:
        meta["summary"] = summarize(_read_rows(log_id), meta)
    except Exception:              # noqa: BLE001
        meta["summary"] = None
    try:
        _write_json(_meta_path(log_id), meta)
    except OSError:
        pass


# --- đọc lại, tóm tắt, rút gọn để vẽ ---------------------------------------------------------
def _f(text: str):
    try:
        return float(text) if text != "" else None
    except ValueError:
        return None


def _read_rows(log_id: str) -> list[dict]:
    rows: list[dict] = []
    with open(_csv_path(log_id), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append({"t": _f(r.get("t", "")), "state": r.get("state", ""),
                         "z": _f(r.get("z", "")), "feed": _f(r.get("feed", "")),
                         "bf": _f(r.get("bf_planner", "")), "sent": _f(r.get("sent", "")),
                         "acked": _f(r.get("acked", ""))})
    return [r for r in rows if r["t"] is not None]


def summarize(rows: list[dict], meta: dict) -> dict:
    """Con số để so sánh các lần chạy. `starved_pct` chỉ có khi máy gửi `Bf:`."""
    n = len(rows)
    out: dict = {"samples": n, "duration_s": round(rows[-1]["t"], 1) if n else 0.0}
    if not n:
        return out
    total = meta.get("total") or 0
    down_z = float(meta.get("pen_down_z") or 0.0) + PEN_DOWN_TOL
    running = [r for r in rows if r["state"].startswith("Run")]
    out["run_pct"] = round(100 * len(running) / n, 1)
    z_rows = [r for r in rows if r["z"] is not None]
    if z_rows:
        out["pen_down_pct"] = round(100 * sum(1 for r in z_rows if r["z"] <= down_z) / len(z_rows), 1)
    drawing = [r["feed"] for r in rows if r["feed"] and r["z"] is not None and r["z"] <= down_z]
    if drawing:
        out["feed_drawing_avg"] = round(sum(drawing) / len(drawing))
    feeds = [r["feed"] for r in rows if r["feed"] is not None]
    if feeds:
        out["feed_max"] = round(max(feeds))
    bfs = [r["bf"] for r in rows if r["bf"] is not None]
    out["has_bf"] = bool(bfs)
    if bfs:
        top = max(bfs)                              # hàng đợi trống hoàn toàn = số khối trống lớn nhất từng thấy
        feeding = [r for r in running if r["bf"] is not None and (not total or (r["acked"] or 0) < total)]
        if feeding:
            starved = sum(1 for r in feeding if r["bf"] >= top)
            out["starved_pct"] = round(100 * starved / len(feeding), 1)
        out["planner_blocks_max"] = int(top)
    return out


def read_log(log_id: str, max_points: int = 3000) -> dict:
    """Số liệu để vẽ: tối đa `max_points` cột; mỗi cột gom nhiều mẫu (tốc độ trung bình / lớn nhất, số khối TRỐNG nhiều
    nhất trong hàng đợi để không bỏ sót lúc đói lệnh, Z nhỏ nhất / lớn nhất để thấy từng lần nhấc bút)."""
    _check_id(log_id)
    max_points = max(100, min(int(max_points), 20000))
    meta = get_meta(log_id)
    try:
        rows = _read_rows(log_id)
    except OSError:
        raise JobLogError("not_found", "Không có nhật ký này.", 404) from None
    n = len(rows)
    step = max(1, -(-n // max_points))
    series = {k: [] for k in ("t", "feed", "feed_max", "bf", "z_min", "z_max", "run", "acked")}
    for i in range(0, n, step):
        chunk = rows[i:i + step]
        feeds = [r["feed"] for r in chunk if r["feed"] is not None]
        bfs = [r["bf"] for r in chunk if r["bf"] is not None]
        zs = [r["z"] for r in chunk if r["z"] is not None]
        series["t"].append(chunk[0]["t"])
        series["feed"].append(round(sum(feeds) / len(feeds)) if feeds else None)
        series["feed_max"].append(round(max(feeds)) if feeds else None)
        series["bf"].append(max(bfs) if bfs else None)        # trống nhiều nhất = hàng đợi vắng nhất trong cột
        series["z_min"].append(min(zs) if zs else None)
        series["z_max"].append(max(zs) if zs else None)
        series["run"].append(round(sum(1 for r in chunk if r["state"].startswith("Run")) / len(chunk), 2))
        series["acked"].append(chunk[-1]["acked"])
    return {"meta": meta, "summary": meta.get("summary") or summarize(rows, meta), "series": series}


def get_meta(log_id: str) -> dict:
    _check_id(log_id)
    try:
        return json.loads(_meta_path(log_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise JobLogError("not_found", "Không có nhật ký này.", 404) from None


def list_logs(current: str | None = None) -> list[dict]:
    out = []
    for path in sorted(logs_dir().glob("*.json"), reverse=True) if logs_dir().exists() else []:
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        csv_file = path.with_suffix(".csv")
        out.append({
            "id": meta.get("id", path.stem), "name": meta.get("name"), "started_at": meta.get("started_at"),
            "state": meta.get("state"), "elapsed_s": meta.get("elapsed_s"), "total": meta.get("total"),
            "acked": meta.get("acked"), "est_seconds": (meta.get("client") or {}).get("est_seconds"),
            "has_bf": meta.get("has_bf"), "live": path.stem == current,
            "size": csv_file.stat().st_size if csv_file.exists() else 0,
        })
    return out


def csv_file(log_id: str) -> Path:
    _check_id(log_id)
    path = _csv_path(log_id)
    if not path.exists():
        raise JobLogError("not_found", "Không có nhật ký này.", 404)
    return path


def delete_log(log_id: str, current: str | None = None) -> None:
    _check_id(log_id)
    if log_id == current:
        raise JobLogError("in_use", "Lần chạy này đang được ghi.", 409)
    found = False
    for path in (_csv_path(log_id), _meta_path(log_id)):
        try:
            path.unlink()
            found = True
        except OSError:
            pass
    if not found:
        raise JobLogError("not_found", "Không có nhật ký này.", 404)
