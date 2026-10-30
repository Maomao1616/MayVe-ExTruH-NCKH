"""Tác vụ nền của tab vẽ: MỘT luồng worker tại một thời điểm, có tiến trình và hủy hợp tác.

Yêu cầu mới hủy yêu cầu cũ (máy yếu: không chạy song song hai tác vụ nặng). Hủy là đặt cờ; các bước
trong tác vụ gọi `ctx.check()` giữa chừng. Mã tác vụ cũng là mã bản vẽ trong `store.TASKS` khi xong.
"""
from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from typing import Any, Callable

from .errors import DrawError

KEEP_JOBS = 8


class Cancelled(Exception):
    """Tác vụ bị hủy (nội bộ, không ra ngoài API)."""


class Context:
    def __init__(self, job: "Job") -> None:
        self._job = job

    def step(self, name: str, progress: float, message: str = "") -> None:
        self.check()
        j = self._job
        j.step, j.progress, j.message = name, max(0.0, min(1.0, progress)), message

    def check(self) -> None:
        if self._job.cancel_flag.is_set():
            raise Cancelled()


class Job:
    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self.state = "queued"            # queued | running | done | failed | cancelled
        self.step = ""
        self.progress = 0.0
        self.message = ""
        self.source: dict | None = None
        self.warnings: list[dict] = []
        self.error: dict | None = None
        self.cancel_flag = threading.Event()
        self.thread: threading.Thread | None = None

    def view(self) -> dict:
        out: dict[str, Any] = {"task": self.id, "state": self.state, "step": self.step,
                               "progress": round(self.progress, 3), "message": self.message}
        if self.state == "done":
            out.update(source=self.source, warnings=self.warnings)
        if self.state == "failed":
            out["error"] = self.error
        return out


class JobManager:
    def __init__(self) -> None:
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()

    def submit(self, work: Callable[[Context, str], dict]) -> Job:
        """`work(ctx, token)` trả {"source": ..., "warnings": [...]} và tự đặt kết quả vào TASKS bằng `token`."""
        job = Job()
        with self._lock:
            previous = [j for j in self._jobs.values() if j.state in ("queued", "running")]
            for old in previous:
                old.cancel_flag.set()
            self._jobs[job.id] = job
            while len(self._jobs) > KEEP_JOBS:
                self._jobs.popitem(last=False)
        job.thread = threading.Thread(target=self._run, args=(job, work, previous), daemon=True,
                                      name=f"draw-{job.id[:6]}")
        job.thread.start()
        return job

    def _run(self, job: Job, work, previous: list[Job]) -> None:
        for old in previous:                      # chờ tác vụ cũ dừng hẳn: không bao giờ chạy hai việc cùng lúc
            if old.thread:
                old.thread.join()
        try:
            if job.cancel_flag.is_set():
                raise Cancelled()
            job.state = "running"
            result = work(Context(job), job.id)
            if job.cancel_flag.is_set():          # hủy đúng lúc vừa xong: coi như đã hủy
                raise Cancelled()
            job.source, job.warnings = result.get("source"), result.get("warnings", [])
            job.step, job.progress, job.state = "done", 1.0, "done"
        except Cancelled:
            job.state = "cancelled"
        except DrawError as exc:
            job.state, job.error = "failed", {"code": exc.code, "message": exc.message}
        except Exception as exc:                  # lỗi lạ: không để luồng chết mà không báo
            job.state, job.error = "failed", {"code": "internal_error", "message": str(exc)}

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise DrawError("unknown_task", "Tác vụ không còn (đã bị dọn hoặc server khởi động lại).", 404)
        return job

    def cancel(self, job_id: str) -> None:
        self.get(job_id).cancel_flag.set()


JOBS = JobManager()
