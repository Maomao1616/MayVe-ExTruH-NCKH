"""Luồng sự kiện máy chủ → trình duyệt (SSE, `text/event-stream`): trạng thái máy + nhật ký terminal, thay cho hỏi lặp.

    GET /api/events?since=<seq nhật ký đã có>
      event: status   data = đúng nội dung GET /api/status (gửi khi đổi, và ít nhất mỗi HEARTBEAT_S giây)
      event: log      data = {entries, last_seq} như GET /api/log (chỉ quản lý; khách không nhận nhật ký)

Vì sao SSE chứ không WebSocket (docs/09_QUYET_DINH_THIET_KE.md A6): chạy trên HTTP thường, cookie PIN dùng như cũ, trình duyệt
tự nối lại, qua Cloudflare Tunnel không cần cấu hình. Lệnh điều khiển vẫn là HTTP POST. Hỏi lặp (/api/status, /api/log)
giữ nguyên làm DỰ PHÒNG: giao diện tự quay về khi luồng này hỏng.
Mỗi kết nối chỉ là một vòng lặp `async` nhìn trạng thái (không giữ luồng riêng); giới hạn MAX_STREAMS kết nối cùng lúc.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .. import idle
from ..auth import COOKIE, auth
from ..services.machine import ServiceError, machine

router = APIRouter(prefix="/api")

MAX_STREAMS = 40
POLL_S = 0.1                   # nhìn trạng thái 10 lần/giây (máy báo ~10 lần/giây)
HEARTBEAT_S = 2.0              # không có gì mới thì vẫn gửi lại trạng thái: giao diện biết luồng còn sống (Cloudflare cắt khi im ~100 s)
AUTH_RECHECK_S = 2.0           # phiên quản lý hết hạn giữa chừng thì ngừng gửi nhật ký
IDLE_TOUCH_S = 5.0             # báo "trang còn mở" cho idle.py (bản đóng gói tự tắt khi không còn trang)
RETRY_MS = 3000

_streams = 0


def _frame(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'), default=str)}\n\n"


def _collect(seq: int, admin: bool) -> tuple[str, dict | None]:
    payload = json.dumps(machine.snapshot(), ensure_ascii=False, separators=(",", ":"), default=str)
    return payload, (machine.log_since(seq) if admin else None)


async def event_stream(token: str | None, since: int, disconnected: Callable[[], Awaitable[bool]], *,
                       poll_s: float = POLL_S, heartbeat_s: float = HEARTBEAT_S) -> AsyncIterator[str]:
    global _streams
    _streams += 1
    try:
        yield f"retry: {RETRY_MS}\n\n"
        loop = asyncio.get_running_loop()
        admin = auth.is_admin(token)
        seq = max(0, since)
        last_payload: str | None = None
        last_sent = last_auth = last_idle = 0.0
        while True:
            if await disconnected():
                return
            now = time.monotonic()
            if now - last_idle >= IDLE_TOUCH_S:
                idle.touch()
                last_idle = now
            if admin and now - last_auth >= AUTH_RECHECK_S:
                last_auth = now
                if not auth.is_admin(token):
                    return                                  # hết phiên: đóng luồng, giao diện nối lại (sẽ thành khách)
            # Đọc ở luồng riêng: snapshot() giữ khóa của MachineService (connect() có thể giữ lâu khi mở cổng serial),
            # không được chặn vòng lặp sự kiện của cả máy chủ.
            payload, result = await loop.run_in_executor(None, _collect, seq, admin)
            if payload != last_payload or now - last_sent >= heartbeat_s:
                last_payload, last_sent = payload, now
                yield f"event: status\ndata: {payload}\n\n"
            if result is not None and (result["entries"] or result["last_seq"] != seq):
                seq = result["last_seq"]
                yield _frame("log", result)
            await asyncio.sleep(poll_s)
    finally:
        _streams -= 1


@router.get("/events")
async def events(request: Request, since: int = 0):
    if _streams >= MAX_STREAMS:
        raise ServiceError("too_many_streams", "Quá nhiều kết nối theo dõi cùng lúc.", 503)
    stream = event_stream(request.cookies.get(COOKIE), since, request.is_disconnected)
    return StreamingResponse(stream, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})
