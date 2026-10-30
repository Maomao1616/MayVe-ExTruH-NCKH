"""Chạy việc nặng (ảnh -> nét) trong TIẾN TRÌNH RIÊNG, ưu tiên thấp.

Vì sao: MiniPC yếu vừa phải gửi lệnh cho máy vẽ đều đặn vừa xử lý ảnh. Tiến trình riêng + ưu tiên thấp
nghĩa là xử lý ảnh có chậm cũng không làm giật luồng điều khiển; hủy = kết thúc hẳn tiến trình (sạch,
trả lại toàn bộ RAM); ảnh lạ làm sập hay ngốn RAM chỉ chết tiến trình con, server vẫn sống.

Cách nói chuyện: cha ghi một gói (pickle, có độ dài đứng trước) vào stdin của con; con trả lại từng gói
("step"...) rồi một gói cuối ("done" hoặc "error") qua stdout. Chỉ pickle dữ liệu do chính code này sinh ra.

Biến môi trường (đều tùy chọn):
  EXTRUXY_DRAW_INPROC=1       chạy ngay trong tiến trình này (test, gỡ lỗi)
  EXTRUXY_DRAW_TIMEOUT_S=600  quá giờ thì kết thúc tiến trình con
  EXTRUXY_DRAW_MAX_MB=4096    trần bộ nhớ ảo của tiến trình con (chỉ Linux/macOS)
"""
from __future__ import annotations

import os
import pickle
import queue
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

from .errors import DrawError
from .store import TASKS, Parsed

DEFAULT_TIMEOUT_S = 600
DEFAULT_MAX_MB = 4096
BACKEND_DIR = Path(__file__).resolve().parents[3]            # thư mục chứa gói `app`
BELOW_NORMAL = 0x00004000                                    # cờ ưu tiên thấp của Windows
NO_WINDOW = 0x08000000                                       # không bật cửa sổ console khi đóng gói exe


# --- gói tin ------------------------------------------------------------------------------
def _send(stream, obj) -> None:
    blob = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    stream.write(struct.pack(">I", len(blob)) + blob)
    stream.flush()


def _recv(stream):
    head = stream.read(4)
    if len(head) < 4:
        return None
    (size,) = struct.unpack(">I", head)
    blob = stream.read(size)
    if len(blob) < size:
        return None
    return pickle.loads(blob)


# --- phía cha ------------------------------------------------------------------------------
def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def run_import(data: bytes, name: str, opts: dict, token: str, ctx) -> dict:
    """Thay cho raster.import_raster trong tác vụ nền: cùng kết quả, nhưng chạy ở tiến trình con."""
    if os.environ.get("EXTRUXY_DRAW_INPROC") == "1":
        from . import raster
        return raster.import_raster(data, name, opts, token, ctx)

    env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2",
               PYTHONIOENCODING="utf-8")
    flags = (BELOW_NORMAL | NO_WINDOW) if sys.platform == "win32" else 0
    try:
        proc = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-m", "app.services.drawing.isolated"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=str(BACKEND_DIR), env=env, creationflags=flags)
    except OSError as exc:
        raise DrawError("worker_crashed", f"Không khởi động được tiến trình xử lý ảnh: {exc}", 500) from exc

    inbox: queue.Queue = queue.Queue()
    request = {"data": data, "name": name, "opts": opts,
               "max_mb": _env_int("EXTRUXY_DRAW_MAX_MB", DEFAULT_MAX_MB)}

    def feed() -> None:
        try:
            _send(proc.stdin, request)
            proc.stdin.close()
        except (OSError, ValueError):
            pass                                              # con đã chết: đầu đọc sẽ báo

    def drain() -> None:
        try:
            while (msg := _recv(proc.stdout)) is not None:
                inbox.put(msg)
        except Exception:
            pass
        inbox.put(None)

    threading.Thread(target=feed, daemon=True, name="draw-feed").start()
    threading.Thread(target=drain, daemon=True, name="draw-drain").start()
    deadline = time.monotonic() + _env_int("EXTRUXY_DRAW_TIMEOUT_S", DEFAULT_TIMEOUT_S)
    try:
        while True:
            if time.monotonic() > deadline:
                raise DrawError("worker_timeout", "Xử lý ảnh quá lâu nên đã dừng (thử ảnh nhỏ hơn hoặc nét thưa hơn).", 504)
            try:
                msg = inbox.get(timeout=0.2)
            except queue.Empty:
                ctx.check()                                   # bị hủy -> Cancelled -> finally kết thúc con
                continue
            if msg is None:
                code = proc.wait(timeout=5)
                raise DrawError("worker_crashed", f"Tiến trình xử lý ảnh dừng bất ngờ (mã {code}).", 500)
            kind = msg[0]
            if kind == "step":
                ctx.step(msg[1], msg[2], msg[3])
            elif kind == "error":
                raise DrawError(msg[1], msg[2], msg[3])
            elif kind == "done":
                _, layers, frame, info, warnings = msg
                TASKS.put(Parsed(layers, frame, info), token)
                return {"task": token, "source": info, "warnings": warnings}
    finally:
        if proc.poll() is None:
            proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


# --- phía con ------------------------------------------------------------------------------
class _ChildContext:
    """Cùng giao diện với tasks.Context: báo tiến trình qua stdout; hủy do cha kết thúc tiến trình."""

    def __init__(self, out) -> None:
        self._out = out

    def step(self, name: str, progress: float, message: str = "") -> None:
        _send(self._out, ("step", name, progress, message))

    def check(self) -> None:
        return None


def _lower_priority() -> None:
    if hasattr(os, "nice"):
        try:
            os.nice(10)
        except OSError:
            pass


def _limit_memory(max_mb: int) -> None:
    try:
        import resource
        limit = max_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ImportError, ValueError, OSError):
        pass                                                  # Windows: không có, bỏ qua


def _child_main() -> None:
    out = sys.stdout.buffer
    sys.stdout = sys.stderr                                   # print lỡ tay không được lọt vào đường truyền
    _lower_priority()
    request = _recv(sys.stdin.buffer)
    if request is None:
        return
    _limit_memory(request["max_mb"])
    try:
        from . import raster
        layers, frame, info, warnings = raster.build_raster(request["data"], request["name"], request["opts"],
                                                            _ChildContext(out))
        _send(out, ("done", layers, frame, info, warnings))
    except DrawError as exc:
        _send(out, ("error", exc.code, exc.message, exc.status))
    except MemoryError:
        _send(out, ("error", "out_of_memory", "Hết bộ nhớ khi xử lý ảnh (thử ảnh nhỏ hơn hoặc nét thưa hơn).", 507))
    except Exception as exc:
        _send(out, ("error", "internal_error", f"{type(exc).__name__}: {exc}", 500))


if __name__ == "__main__":
    _child_main()
