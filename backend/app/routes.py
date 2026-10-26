"""API HTTP của backend. Giữ mỏng: mọi logic nằm trong MachineService."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .services.machine import ServiceError, machine

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
    lines: list[str] = Field(min_length=1, max_length=200_000)


class RealtimeRequest(BaseModel):
    action: Literal["status", "hold", "resume", "reset", "jog_cancel"]


@router.get("/health")
def health():
    return {"ok": True, "service": "extruxy-backend", "version": "0.2.0"}


@router.get("/ports")
def ports():
    try:
        from .links.serial_link import list_ports
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


@router.post("/jobs")
def start_job(req: JobStartRequest):
    return machine.start_job(req.name, req.lines)


@router.post("/jobs/cancel")
def cancel_job():
    return machine.cancel_job()


@router.get("/log")
def log(since: int = 0):
    return machine.log_since(since)
