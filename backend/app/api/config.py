"""API cấu hình máy (YAML trên mạch, services/machine_config.py) và hồ sơ phần mềm
(services/profile.py). Mỏng: logic nằm trong service."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services import machine_config, profile
from ..services.machine import ServiceError, machine

router = APIRouter(prefix="/api")


def _wrap(fn, *args):
    """Lỗi của service cấu hình/hồ sơ -> lỗi chuẩn {"error": {"code", "message"}}."""
    try:
        return fn(*args)
    except (machine_config.ConfigError, profile.ProfileError) as exc:
        raise ServiceError(exc.code, exc.message, exc.status) from exc


# --- cấu hình FluidNC trên mạch (services/machine_config.py) -------------------------
Finite = Annotated[float, Field(allow_inf_nan=False)]


class ConfigApplyRequest(BaseModel):
    values: dict[str, Finite] = Field(min_length=1, max_length=50)


@router.get("/machine/config")
def machine_config_read():
    return _wrap(machine_config.read_config, machine)


@router.post("/machine/config")
def machine_config_apply(req: ConfigApplyRequest):
    return _wrap(machine_config.apply_values, machine, req.values)


@router.post("/machine/config/save")
def machine_config_save():
    return _wrap(machine_config.save_to_board, machine)


# --- hồ sơ phần mềm (services/profile.py) ------------------------------------------
class ProfileRequest(BaseModel):
    pen_up_z: Finite
    pen_mid_z: Finite
    pen_down_z: Finite
    pen_feed: Finite
    jog_max_step: Finite


@router.get("/profile")
def profile_read():
    return {"profile": profile.load(), "limits": profile.LIMITS}


@router.put("/profile")
def profile_write(req: ProfileRequest):
    return {"profile": _wrap(profile.save, req.model_dump()), "limits": profile.LIMITS}
