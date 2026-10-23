"""SerialLink: kết nối FluidNC thật qua USB/serial (CH340).

CHƯA được thử trên board thật. Thử ở Bước 4 chỉ với lệnh đọc.
"""
from __future__ import annotations

import threading

from .base import BaseLink, LinkError


def list_ports() -> list[dict]:
    from serial.tools import list_ports as lp

    return [
        {"device": p.device, "description": p.description, "hwid": p.hwid}
        for p in sorted(lp.comports(), key=lambda p: p.device)
    ]


class SerialLink(BaseLink):
    kind = "serial"

    def __init__(self, port: str, baud: int = 115200) -> None:
        super().__init__()
        self.port = port
        self.baud = baud
        self._ser = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._write_lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def open(self) -> None:
        import serial  # nhập muộn để phần còn lại chạy được khi chưa cài pyserial

        if self.is_open:
            return
        ser = serial.Serial()  # tạo nhưng chưa mở
        ser.port = self.port
        ser.baudrate = self.baud
        ser.timeout = 0.1
        ser.write_timeout = 2
        # Tắt DTR/RTS TRƯỚC khi mở để hạn chế việc ESP32 bị reset khi mở cổng.
        ser.dtr = False
        ser.rts = False
        try:
            ser.open()
        except (serial.SerialException, OSError) as exc:
            raise LinkError(f"Không mở được {self.port}: {exc}") from exc
        self._ser = ser
        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, name="serial-reader", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None
        ser, self._ser = self._ser, None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def _read_loop(self) -> None:
        import serial

        buffer = bytearray()
        try:
            while not self._stop.is_set():
                chunk = self._ser.read(self._ser.in_waiting or 1)
                if not chunk:
                    continue
                buffer.extend(chunk)
                while b"\n" in buffer:
                    raw, _, rest = bytes(buffer).partition(b"\n")
                    buffer = bytearray(rest)
                    line = raw.decode("utf-8", errors="replace").strip("\r")
                    if line.strip():
                        self._emit(line)
        except (serial.SerialException, OSError, AttributeError) as exc:
            if not self._stop.is_set():
                self._emit_closed(f"Mất kết nối serial: {exc}")
                self.close()

    def write_line(self, text: str) -> None:
        self._write((text.strip() + "\n").encode("utf-8"))

    def write_realtime(self, data: bytes) -> None:
        self._write(data)

    def _write(self, data: bytes) -> None:
        if not self.is_open:
            raise LinkError("Cổng serial chưa mở")
        try:
            with self._write_lock:
                self._ser.write(data)
        except Exception as exc:
            raise LinkError(f"Ghi serial thất bại: {exc}") from exc
