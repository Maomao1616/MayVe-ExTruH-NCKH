"""TelnetLink: kết nối FluidNC qua Wi-Fi bằng telnet (TCP thô, cổng 23), cùng giao diện với SerialLink.

Telnet của FluidNC (src/WebUI/TelnetClient.cpp) nhận G-code và ký tự tức thời (? ! ~ Ctrl-X) y như USB, chỉ bỏ
các chuỗi điều khiển telnet bắt đầu bằng byte 0xFF (không lệnh nào của ta dùng). KHÔNG có mật khẩu: chỉ dùng trong
mạng riêng. Mất kết nối thì mạch không tự dừng, không nâng bút: chạy hết lệnh đã nhận rồi đứng.

CHƯA thử trên mạch thật. Quy chuẩn, rủi ro, việc còn phải làm: docs/07_MANG_KET_NOI_TRIEN_KHAI.md mục 3, 11.
"""
from __future__ import annotations

import select
import socket
import threading
import time

from .base import BaseLink, LinkError

DEFAULT_PORT = 23            # cổng telnet mặc định của FluidNC ($Telnet/Port)
CONNECT_TIMEOUT_S = 5.0      # chờ mở kết nối tối đa
LINK_SILENT_S = 3.0          # không nhận byte nào trong 3 s thì coi là mất sóng. Máy chủ hỏi `?` 10 lần/giây
                             # (machine.POLL_S) nên mạch luôn trả lời; 3 s ~ 30 lần liền im lặng. Ngắn hơn: mạng
                             # điện thoại khựng là dừng oan; dài hơn: máy vẽ tiếp lúc ta không điều khiển được.
READ_WAIT_S = 0.5            # luồng đọc thức dậy ít nhất mỗi 0,5 s (để kiểm im lặng và lệnh đóng)
WRITE_TIMEOUT_S = LINK_SILENT_S   # ghi kẹt lâu hơn ngưỡng mất sóng mới báo lỗi (mạng khựng ngắn không làm dừng oan)

# Chuỗi điều khiển telnet (RFC 854): IAC = 0xFF, rồi một byte lệnh. WILL/WONT/DO/DONT (0xFB-0xFE) kèm thêm một byte
# tùy chọn; SB (0xFA) mở đoạn thương lượng kéo tới IAC SE (0xFF 0xF0); IAC IAC = một byte 0xFF thật (bỏ luôn, FluidNC
# chỉ gửi chữ ASCII). FluidNC không chủ động gửi các chuỗi này; lọc để một thiết bị / proxy chen giữa không làm rác dòng.
IAC, SB, SE = 0xFF, 0xFA, 0xF0
_OPTION_CMDS = range(0xFB, 0xFF)   # WILL, WONT, DO, DONT: thêm 1 byte tùy chọn


class TelnetFilter:
    """Bỏ chuỗi điều khiển telnet khỏi luồng byte. Giữ trạng thái giữa các lần recv (chuỗi có thể bị cắt đôi)."""

    def __init__(self) -> None:
        self._state = "data"      # data | iac | option | sub | sub_iac

    def feed(self, chunk: bytes) -> bytes:
        out = bytearray()
        state = self._state
        for b in chunk:
            if state == "data":
                if b == IAC:
                    state = "iac"
                else:
                    out.append(b)
            elif state == "iac":
                if b == SB:
                    state = "sub"
                elif b in _OPTION_CMDS:
                    state = "option"
                else:                       # IAC IAC hoặc lệnh 2 byte (NOP, GA, ...): bỏ
                    state = "data"
            elif state == "option":         # byte tùy chọn của WILL/WONT/DO/DONT
                state = "data"
            elif state == "sub":
                if b == IAC:
                    state = "sub_iac"
            elif state == "sub_iac":
                state = "data" if b == SE else "sub"
        self._state = state
        return bytes(out)


class TelnetLink(BaseLink):
    kind = "wifi"

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._write_lock = threading.Lock()
        self._lost_lock = threading.Lock()     # luồng đọc và luồng ghi có thể cùng phát hiện mất kết nối

    @property
    def is_open(self) -> bool:
        return self._sock is not None

    def open(self) -> None:
        if self.is_open:
            return
        try:
            sock = socket.create_connection((self.host, self.port), timeout=CONNECT_TIMEOUT_S)
        except OSError as exc:
            raise LinkError(f"Cannot connect to {self.host}:{self.port}: {exc}")
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # gửi ngay từng dòng ngắn, không gom
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.settimeout(WRITE_TIMEOUT_S)   # áp cho sendall; luồng đọc chờ bằng select nên không bị ảnh hưởng
        self._sock = sock
        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, name="telnet-reader", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None

    def _lost(self, reason: str) -> None:
        with self._lost_lock:                 # chỉ báo một lần dù hai luồng cùng phát hiện
            if self._stop.is_set():
                return
            self._stop.set()
        self._emit_closed(reason)
        self.close()

    def _read_loop(self) -> None:
        sock = self._sock
        telnet = TelnetFilter()
        buffer = bytearray()
        last_rx = time.monotonic()
        while not self._stop.is_set():
            try:
                ready, _, _ = select.select([sock], [], [], READ_WAIT_S)
                if not ready:
                    if time.monotonic() - last_rx > LINK_SILENT_S:
                        self._lost(f"Wi-Fi: no data from controller for {LINK_SILENT_S:g} s (signal lost?)")
                        return
                    continue
                chunk = sock.recv(4096)
            except (OSError, ValueError) as exc:          # ValueError: socket đã bị close() ở luồng khác
                self._lost(f"Wi-Fi connection lost: {exc}")
                return
            if not chunk:
                self._lost("Wi-Fi: controller closed the connection")
                return
            last_rx = time.monotonic()
            buffer.extend(telnet.feed(chunk))
            while b"\n" in buffer:
                raw, _, rest = bytes(buffer).partition(b"\n")
                buffer = bytearray(rest)
                line = raw.decode("utf-8", errors="replace").strip("\r")
                if line.strip():
                    self._emit(line)

    def write_line(self, text: str) -> None:
        self._write((text.strip() + "\n").encode("utf-8"))

    def write_realtime(self, data: bytes) -> None:
        self._write(data)

    def _write(self, data: bytes) -> None:
        sock = self._sock
        if sock is None:
            raise LinkError("Wi-Fi link is not open")
        try:
            with self._write_lock:
                sock.sendall(data)      # dòng ngắn vào thẳng bộ đệm gửi của hệ điều hành, chỉ kẹt khi mạng treo lâu
        except OSError as exc:
            # Ghi quá WRITE_TIMEOUT_S hoặc lỗi socket: coi là mất kết nối NGAY (dừng tác vụ, khóa lại),
            # không chờ luồng đọc phát hiện ở chu kỳ sau.
            self._lost(f"Wi-Fi write failed: {exc}")
            raise LinkError(f"Wi-Fi write failed: {exc}")
