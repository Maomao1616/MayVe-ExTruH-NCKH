"""API điều khiển máy: kết nối, trạng thái, lệnh, tác vụ, mở khóa. Mỏng: logic ở MachineService."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services.machine import ServiceError, machine

router = APIRouter(prefix="/api")


class ConnectRequest(BaseModel):
    mode: Literal["sim", "serial"]
    port: str | None = None
    baud: int = Field(115200, ge=9600, le=2_000_000)
    sim_speed: float = Field(1.0, gt=0, le=100)


class CommandRequest(BaseModel):
    line: str = Field(min_length=1, max_length=200)


class JobStartRequest(BaseModel):
    name: str = Field("gcode", max_length=120)
    # Dòng thô có thể kèm chú thích dài; sau khi làm sạch vẫn bị giới hạn 200 ký tự (job.py).
    lines: list[Annotated[str, Field(max_length=4096)]] = Field(min_length=1, max_length=200_000)


class ResumeRequest(BaseModel):
    accept_wco_change: bool = False


class RealtimeRequest(BaseModel):
    action: Literal["status", "hold", "resume", "reset", "jog_cancel",
                    "feed_reset", "feed_plus10", "feed_minus10", "feed_plus1", "feed_minus1"]


class MotionRequest(BaseModel):
    on: bool
    pin: str | None = Field(None, max_length=64)


class CancelRequest(BaseModel):
    mode: Literal["reset", "soft", "hard"] = "reset"
    # Chỉ chặn giá trị vô nghĩa (nan/inf, feed <= 0). Giới hạn hành trình Z do firmware
    # kiểm (soft limit -> error:15), không tự đặt giới hạn giả định ở đây.
    lift_z: float | None = Field(None, allow_inf_nan=False)
    lift_feed: float = Field(1000.0, gt=0, allow_inf_nan=False)


@router.post("/motion")
def motion(req: MotionRequest):
    return machine.set_motion(req.on, req.pin)


@router.get("/health")
def health():
    return {"ok": True, "service": "extruxy-backend", "version": "0.2.0"}


@router.get("/ports")
def ports():
    try:
        from ..links.serial_link import list_ports
        return {"ports": list_ports()}
    except ImportError as exc:
        raise ServiceError("pyserial_missing", f"Chưa cài pyserial: {exc}", 500) from exc


@router.get("/connection")
def connection():
    return machine.connection_info()


@router.post("/connect")
def connect(req: ConnectRequest):
    return machine.connect(req.mode, req.port, req.baud, req.sim_speed)


@router.post("/disconnect")
def disconnect():
    return machine.disconnect()


@router.get("/status")
def status():
    return machine.snapshot()


@router.post("/command")
def command(req: CommandRequest):
    return machine.send_line(req.line)


@router.post("/realtime")
def realtime(req: RealtimeRequest):
    return machine.send_realtime(req.action)


@router.get("/log")
def log(since: int = 0):
    return machine.log_since(since)


@router.post("/jobs")
def start_job(req: JobStartRequest):
    return machine.start_job(req.name, req.lines)


@router.get("/jobs/resume")
def resume_info():
    return machine.resume_info()


@router.post("/jobs/resume")
def resume_job(req: ResumeRequest = ResumeRequest()):
    return machine.resume_job(req.accept_wco_change)


@router.delete("/jobs/resume")
def resume_discard():
    return machine.discard_resume()


@router.post("/jobs/cancel")
def cancel_job(req: CancelRequest = CancelRequest()):
    return machine.cancel_job(req.mode, req.lift_z, req.lift_feed)
