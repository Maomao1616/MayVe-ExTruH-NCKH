"""JobRunner: chạy một tệp G-code bằng cách gửi TỪNG DÒNG và chờ `ok`/`error` của firmware.

Vì sao gửi từng dòng chờ `ok` là đủ: FluidNC trả `ok` ngay khi dòng đã vào hàng đợi chuyển
động (planner); khi hàng đợi đầy thì `ok` bị giữ lại. Nhờ vậy hàng đợi luôn đầy mà không cần
đếm ký tự bộ đệm.

Quy ước khóa (tránh khóa chéo): MachineService giữ khóa của nó rồi mới gọi vào JobRunner
(`on_response`, `on_alarm`, `abort`). Luồng chạy của JobRunner KHÔNG BAO GIỜ gọi vào
MachineService khi đang giữ `self._cond`.
"""
from __future__ import annotations

import re
import threading
import time

MAX_LINES = 200_000
MAX_LINE_LEN = 200
RESPONSE_TIMEOUT_S = 120.0     # chờ `ok` tối đa (không tính lúc máy đang Hold)
FINISH_TIMEOUT_S = 6 * 3600.0  # chờ máy chạy nốt hàng đợi

_PAREN = re.compile(r"\([^)]*\)")
_SPACES = re.compile(r"\s+")
_BAD_CHARS = re.compile(r"[^\x20-\x7e]")


class JobError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def clean_gcode(raw_lines: list[str]) -> list[str]:
    """Bỏ chú thích và dòng trống; từ chối mọi thứ không phải G-code thuần.

    Chặn lệnh `$...` (cài đặt, Home, jog) và ký tự realtime (`? ! ~` và Ctrl-X): tệp G-code
    không có quyền đổi cài đặt hay dừng/chạy máy ngoài luồng của tác vụ.
    """
    cleaned: list[str] = []
    for number, raw in enumerate(raw_lines, start=1):
        line = _PAREN.sub("", raw.split(";", 1)[0]).strip()
        if not line or line.startswith("%"):
            continue
        line = _SPACES.sub(" ", line)
        if _BAD_CHARS.search(line) or any(c in line for c in "?!~"):
            raise JobError("bad_gcode", f"Dòng {number}: có ký tự không hợp lệ.")
        if line.startswith("$"):
            raise JobError("bad_gcode", f"Dòng {number}: không cho phép lệnh '$' trong tệp G-code.")
        if not line[0].isalpha():
            raise JobError("bad_gcode", f"Dòng {number}: không phải lệnh G-code.")
        if len(line) > MAX_LINE_LEN:
            raise JobError("bad_gcode", f"Dòng {number}: dài quá {MAX_LINE_LEN} ký tự.")
        cleaned.append(line)
    if len(cleaned) > MAX_LINES:
        raise JobError("bad_gcode", f"Tệp quá dài (tối đa {MAX_LINES} dòng).")
    return cleaned


class JobRunner:
    def __init__(self, service) -> None:
        self._svc = service
        self._cond = threading.Condition()
        self._counter = 0
        self._info: dict | None = None
        self._cancel = False
        self._awaiting = False
        self._response: tuple[str, dict] | None = None

    # --- trạng thái ------------------------------------------------------------
    @property
    def active(self) -> bool:
        with self._cond:
            return self._info is not None and self._info["state"] in ("running", "finishing")

    def reset(self) -> None:
        with self._cond:
            self._info = None
            self._cancel = False
            self._awaiting = False
            self._response = None
            
    def is_live(self, job_id: int) -> bool:
        with self._cond:
            return self._live(job_id)

    def snapshot(self) -> dict | None:
        with self._cond:
            if self._info is None:
                return None
            info = dict(self._info)
        end = info["finished_at"] or time.time()
        info["elapsed_s"] = round(end - info["started_at"], 1)
        return info

    # --- điều khiển ------------------------------------------------------------
    def start(self, name: str, raw_lines: list[str], pre_cleaned: bool = False) -> dict:
        lines = raw_lines if pre_cleaned else clean_gcode(raw_lines)
        if not lines:
            raise JobError("empty_job", "Tệp không có dòng lệnh nào.")
        with self._cond:
            if self._info is not None and self._info["state"] in ("running", "finishing"):
                raise JobError("job_running", "Đang có tác vụ chạy.", 409)
            self._counter += 1
            self._cancel = False
            self._awaiting = False
            self._response = None
            self._info = {"id": self._counter, "name": name, "mode": "stream",
                          "state": "running", "total": len(lines), "sent": 0, "acked": 0,
                          "started_at": time.time(), "finished_at": None, "error": None}
            job_id = self._counter
        threading.Thread(target=self._run, args=(job_id, lines),
                         name=f"job-{job_id}", daemon=True).start()
        return self.snapshot()

    def cancel(self) -> None:
        # Đồng bộ với thời điểm ghi thực tế, không chỉ với lần kiểm tra _live()
        # ở đầu vòng lặp. Nếu writer còn đang ghi, cancel đợi vùng ghi kết thúc.
        with self._svc._job_write_lock:
            with self._cond:
                if self._info is None or self._info["state"] not in ("running", "finishing"):
                    raise JobError("no_job", "Không có tác vụ đang chạy.", 409)
                self._cancel = True
                self._finish("cancelled")
                self._cond.notify_all()

    def abort(self, code: str, message: str = "") -> None:
        """Dừng tác vụ vì lý do bên ngoài (mất kết nối...). Không làm gì nếu không có tác vụ."""
        with self._cond:
            if self._info is not None and self._info["state"] in ("running", "finishing"):
                self._fail(code, message or code)
                self._cond.notify_all()

    # --- được MachineService gọi khi nhận dòng từ máy ------------------------------
    def on_response(self, kind: str, info: dict) -> bool:
        """Trả True nếu `ok` này thuộc về tác vụ (không cần ghi vào nhật ký)."""
        with self._cond:
            if not self._awaiting:
                return False
            self._awaiting = False
            self._response = (kind, info)
            self._cond.notify_all()
            return kind == "ok"

    def on_alarm(self, code: int) -> None:
        with self._cond:
            if self._info is not None and self._info["state"] in ("running", "finishing") \
                    and not self._cancel:
                self._fail("alarm", f"ALARM:{code}", device_code=code)
                self._cond.notify_all()

    # --- nội bộ (gọi khi đang giữ self._cond) --------------------------------------
    def _finish(self, state: str) -> None:
        self._info["state"] = state
        self._info["finished_at"] = time.time()
        self._awaiting = False      # thêm
        self._response = None       # thêm

    def _fail(self, code: str, text: str, line: int | None = None,
              device_code: int | None = None) -> None:
        self._info["error"] = {"code": code, "text": text, "line": line,
                               "device_code": device_code}
        self._finish("failed")

    def _live(self, job_id: int) -> bool:
        return (self._info is not None and self._info["id"] == job_id
                and self._info["state"] in ("running", "finishing") and not self._cancel)

    # --- luồng chạy ------------------------------------------------------------
    def _run(self, job_id: int, lines: list[str]) -> None:
        self._svc.log_system(f"Job started: {self._info['name']} ({len(lines)} lines)")

        for index, line in enumerate(lines, start=1):
            with self._cond:
                if not self._live(job_id):
                    return
                self._awaiting, self._response = True, None
                self._info["sent"] = index
            try:
                self._svc.job_write(line, job_id)
            except Exception as exc:                      # mất kết nối, serial lỗi...
                with self._cond:
                    if self._live(job_id):
                        self._fail("link_error", str(exc), line=index)
                return

            response = self._wait_response(job_id, index)
            if response is None:
                return
            kind, info = response
            with self._cond:
                if not self._live(job_id):
                    return
                self._info["acked"] = index
                if kind == "error":
                    self._fail("device_error", f"error:{info.get('code')}", line=index,
                               device_code=info.get("code"))
            if kind == "error":
                # Dòng bị từ chối: dừng cấp lệnh và giữ máy lại, không để nó chạy tiếp một mình.
                self._svc.job_hold()
                return

        self._wait_finish(job_id)

    def _wait_response(self, job_id: int, index: int):
        deadline = time.monotonic() + RESPONSE_TIMEOUT_S
        while True:
            with self._cond:
                if not self._live(job_id):
                    return None
                if self._response is not None:
                    response, self._response = self._response, None
                    return response
                self._cond.wait(0.1)
            state, _ = self._svc.machine_state()           # ngoài self._cond
            now = time.monotonic()
            if state == "Hold":
                deadline = now + RESPONSE_TIMEOUT_S         # đang tạm dừng: không tính timeout
            elif now > deadline:
                with self._cond:
                    failed = self._live(job_id)
                    if failed:
                        self._fail("timeout", "Máy không phản hồi.", line=index)
                if failed:
                    self._svc.job_hold()      # ngoài self._cond
                return None

    def _wait_finish(self, job_id: int) -> None:
        with self._cond:
            if not self._live(job_id):
                return
            self._info["state"] = "finishing"
        last_ok = time.time()
        deadline = time.monotonic() + FINISH_TIMEOUT_S
        while True:
            with self._cond:
                if not self._live(job_id):
                    return
                self._cond.wait(0.1)
            state, updated_at = self._svc.machine_state()
            if state == "Idle" and updated_at is not None and updated_at > last_ok:
                with self._cond:
                    if self._live(job_id):
                        self._finish("done")
                return
            if time.monotonic() > deadline:
                with self._cond:
                    if self._live(job_id):
                        self._fail("timeout", "Máy không về trạng thái Idle.")
                return
