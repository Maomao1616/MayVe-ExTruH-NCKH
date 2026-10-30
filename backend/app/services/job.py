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

from . import resume

MAX_LINES = 200_000
MAX_LINE_LEN = 200
RESPONSE_TIMEOUT_S = 120.0     # chờ `ok` tối đa (không tính lúc máy đang Hold)
FINISH_TIMEOUT_S = 6 * 3600.0  # chờ máy chạy nốt hàng đợi
STATUS_STALE_S = 10.0          # quá lâu không có báo cáo trạng thái: coi như mất phản hồi
FINISH_IDLE_REPORTS = 2        # cần ngần này báo cáo Idle MỚI liên tiếp mới coi là xong

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
        self._lines: list[str] | None = None       # dòng của tác vụ hiện tại (để ghi điểm dừng)
        self._origin: dict | None = None           # tác vụ tiếp tục: {lines, base, prefix}

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
    def start(self, name: str, raw_lines: list[str], pre_cleaned: bool = False,
              origin: dict | None = None) -> dict:
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
            self._lines, self._origin = lines, origin
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
        """Trả True nếu `ok`/`error` này thuộc về dòng tác vụ đang chờ."""
        with self._cond:
            if not self._awaiting:
                return False
            self._awaiting = False
            self._response = (kind, info)
            self._cond.notify_all()
            return True

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
        self._awaiting = False
        self._response = None
        self._record_stop(state)

    def _record_stop(self, state: str) -> None:
        """Xong trọn vẹn: xóa điểm dừng. Hủy / lỗi / mất kết nối: ghi điểm dừng (xem services/resume.py)."""
        if state == "done":
            resume.clear()
            return
        if state not in ("cancelled", "failed") or self._lines is None:
            return
        info, error = self._info, self._info["error"]
        acked = info["acked"] - (1 if error and error.get("code") == "device_error" else 0)
        lines, origin = self._lines, self._origin
        if origin is not None:
            done = origin["base"] + max(0, acked - origin["prefix"])
            lines = origin["lines"]
        else:
            done = max(0, acked)
        name = origin["name"] if origin is not None else info["name"]
        # Ghi tệp ở luồng riêng: đang giữ khóa của tác vụ, không để ổ đĩa chậm làm kẹt việc dừng máy.
        threading.Thread(target=self._persist_stop, args=(name, lines, done, state, error),
                         name="resume-save", daemon=True).start()

    def _persist_stop(self, name, lines, done, state, error) -> None:
        wco = None
        getter = getattr(self._svc, "work_offset", None)
        if getter is not None:
            wco = getter()
        resume.save(name, lines, done, state, error, wco)

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
            state, _, age = self._svc.machine_state()     # ngoài self._cond
            now = time.monotonic()
            # Chỉ tin "đang Hold" khi báo cáo còn mới; mất status thì vẫn tính timeout.
            if state == "Hold" and age is not None and age < STATUS_STALE_S:
                deadline = now + RESPONSE_TIMEOUT_S         # đang tạm dừng: không tính timeout
            elif now > deadline:
                self._fail_and_hold(job_id, "timeout", "Máy không phản hồi.", line=index)
                return None

    def _wait_finish(self, job_id: int) -> None:
        with self._cond:
            if not self._live(job_id):
                return
            self._info["state"] = "finishing"
        # Mốc lấy SAU `ok` cuối: chỉ báo cáo đến sau mốc này mới phản ánh hàng đợi cuối cùng.
        _, last_seq, _ = self._svc.machine_state()
        idle_reports = 0
        deadline = time.monotonic() + FINISH_TIMEOUT_S
        while True:
            with self._cond:
                if not self._live(job_id):
                    return
                self._cond.wait(0.1)
            state, seq, age = self._svc.machine_state()
            if seq != last_seq:
                last_seq = seq
                # Một báo cáo Idle đơn lẻ có thể được tạo ngay trước khi khối cuối bắt đầu chạy.
                idle_reports = idle_reports + 1 if state == "Idle" else 0
                if idle_reports >= FINISH_IDLE_REPORTS:
                    with self._cond:
                        if self._live(job_id):
                            self._finish("done")
                    return
            if age is None or age > STATUS_STALE_S:
                self._fail_and_hold(job_id, "status_lost",
                                    "Mất báo cáo trạng thái; chưa xác nhận máy đã dừng.")
                return
            if time.monotonic() > deadline:
                self._fail_and_hold(job_id, "timeout",
                                    "Máy không về trạng thái Idle; chưa xác nhận máy đã dừng.")
                return

    def _fail_and_hold(self, job_id: int, code: str, text: str, line: int | None = None) -> None:
        """Đánh dấu lỗi rồi Feed Hold. `failed` không có nghĩa là máy đã dừng chuyển động."""
        with self._cond:
            failed = self._live(job_id)
            if failed:
                self._fail(code, text, line=line)
        if failed:
            self._svc.job_hold()      # ngoài self._cond
