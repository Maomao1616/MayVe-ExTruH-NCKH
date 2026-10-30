"""Đọc / sửa / lưu cấu hình FluidNC (machine_config.py) và hồ sơ phần mềm (profile.py).
Cú pháp lệnh theo log board thật 29/10/2026; ở đây chạy trên SimLink."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import machine_config as mc
from app.services import profile
from app.services.machine import MachineService, ServiceError, machine
from tests.helpers import wait_for

# Trích từ `$CD` thật (MKS DLC32): khóa trục viết hoa, số 6 chữ số thập phân.
REAL_DUMP = """board: MKS DLC32 V2.1
axes:
  X:
    max_rate_mm_per_min: 6000.000000
    acceleration_mm_per_sec2: 600.000000
    max_travel_mm: 285.000000
    homing:
      feed_mm_per_min: 150.000000
      seek_mm_per_min: 1000.000000
  Z:
    motor0:
      rc_servo:
        output_pin: gpio.32
        min_pulse_us: 1350
        max_pulse_us: 1950
NoSpindle:
junction_deviation_mm: 0.010000
""".splitlines()


@pytest.fixture
def svc(tmp_path, monkeypatch):
    s = MachineService(allow_motion=True)
    s.connect("sim", sim_speed=50)
    assert wait_for(lambda: s._status is not None, 3.0)
    yield s
    s.disconnect()


# --- hàm thuần ---------------------------------------------------------------------
def test_extract_reads_real_dump_case_insensitively():
    values = mc.extract(mc.parse_yaml(REAL_DUMP))
    assert values["axes/x/max_rate_mm_per_min"] == 6000.0
    assert values["axes/x/homing/seek_mm_per_min"] == 1000.0
    assert values["axes/z/motor0/rc_servo/min_pulse_us"] == 1350.0
    assert values["junction_deviation_mm"] == 0.01
    assert values["axes/y/max_rate_mm_per_min"] is None      # không có trong đoạn trích


def test_validate_rejects_unknown_out_of_range_and_bad_servo():
    with pytest.raises(mc.ConfigError):
        mc.validate({"axes/x/motor0/stepstick/step_pin": 1}, {})       # chân GPIO: cấm
    with pytest.raises(mc.ConfigError):
        mc.validate({"axes/x/max_rate_mm_per_min": 0}, {})
    with pytest.raises(mc.ConfigError):
        mc.validate({"axes/z/motor0/rc_servo/min_pulse_us": 2000},
                    {"axes/z/motor0/rc_servo/max_pulse_us": 1950.0})
    assert mc.validate({"axes/z/motor0/rc_servo/min_pulse_us": 1400.4}, {}) == \
        {"axes/z/motor0/rc_servo/min_pulse_us": 1400.0}


def test_fmt_never_uses_exponent():
    assert mc.fmt(0.0001) == "0.0001" and mc.fmt(6000.0) == "6000" and mc.fmt(1350, True) == "1350"


# --- với máy (SimLink) ---------------------------------------------------------------
def test_read_config_from_sim(svc):
    cfg = mc.read_config(svc)
    assert cfg["file"] == "ConfigNCKH-16.yaml"
    assert cfg["values"]["axes/y/max_travel_mm"] == 318.0
    assert cfg["unsaved"] == []
    # Không đổ ~hàng chục dòng $CD vào nhật ký
    assert not any(e["text"].startswith("max_rate") for e in svc.log_since(0)["entries"])


def test_apply_changes_ram_and_marks_unsaved_then_save_clears_it(svc, tmp_path):
    cfg = mc.apply_values(svc, {"axes/x/max_rate_mm_per_min": 5500})
    assert cfg["failed"] == []
    assert cfg["values"]["axes/x/max_rate_mm_per_min"] == 5500.0
    assert cfg["unsaved"] == ["axes/x/max_rate_mm_per_min"]

    result = mc.save_to_board(svc)
    assert result["verified"] is True
    backups = list((tmp_path / "data" / "config_backups").iterdir())
    assert len(backups) == 1 and "6000" in backups[0].read_text(encoding="utf-8")  # bản GỐC
    assert mc.read_config(svc)["unsaved"] == []


def test_real_machine_locked_can_read_but_not_write(svc):
    svc.allow_motion = False
    svc._motion_permanent = False
    svc._info["mode"] = "serial"                 # chỉ để thử khóa, vẫn là SimLink
    assert mc.read_config(svc)["file"] == "ConfigNCKH-16.yaml"
    with pytest.raises(ServiceError) as e:
        mc.apply_values(svc, {"axes/x/max_rate_mm_per_min": 5500})
    assert e.value.code == "motion_locked"


def test_terminal_and_jobs_wait_while_query_in_progress(svc):
    with svc._lock:
        svc._capture = {"lines": [], "done": None, "result": None}
    try:
        for call in (lambda: svc.send_line("$I"), lambda: svc.start_job("x", ["G1 X1 F100"])):
            with pytest.raises(ServiceError) as e:
                call()
            assert e.value.code == "busy"
        svc.send_realtime("hold")                # lệnh dừng vẫn luôn đi được
    finally:
        svc._capture = None


def test_device_error_is_reported(svc):
    with pytest.raises(ServiceError) as e:
        svc.query("$/axes/x/khong_co")
    assert e.value.code == "device_error"


# --- API ---------------------------------------------------------------------------
@pytest.fixture
def client(tmp_path, monkeypatch):
    machine.disconnect()
    yield TestClient(app)
    machine.disconnect()
    with machine._lock:              # ngắt kết nối vẫn giữ báo cáo cuối: dọn cho test sau
        machine._clear_machine()


def test_config_route_needs_connection(client):
    r = client.get("/api/machine/config")
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_connected"


def test_config_routes_with_sim(client, tmp_path, monkeypatch):
    client.post("/api/connect", json={"mode": "sim", "sim_speed": 50})
    assert wait_for(lambda: client.get("/api/status").json()["machine"] is not None)
    assert client.get("/api/machine/config").json()["file"] == "ConfigNCKH-16.yaml"
    r = client.post("/api/machine/config", json={"values": {"axes/x/max_travel_mm": 9999}})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"
    r = client.post("/api/machine/config", json={"values": {"axes/x/max_travel_mm": 280}})
    assert r.status_code == 200 and r.json()["unsaved"] == ["axes/x/max_travel_mm"]
    assert client.post("/api/machine/config/save").json()["verified"] is True


def test_profile_defaults_save_and_order_check(client, tmp_path):
    assert client.get("/api/profile").json()["profile"]["pen_mid_z"] == 2.5
    body = {"pen_up_z": 4, "pen_mid_z": 2, "pen_down_z": 0, "pen_feed": 2000, "jog_max_step": 10}
    assert client.put("/api/profile", json=body).json()["profile"]["pen_up_z"] == 4.0
    assert client.get("/api/profile").json()["profile"]["jog_max_step"] == 10.0
    r = client.put("/api/profile", json={**body, "pen_mid_z": 5})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_param"


def test_query_right_after_a_terminal_command_does_not_take_its_ok(svc):
    # Lỗi có thể xảy ra: giao diện gửi $I lúc vừa kết nối, panel cấu hình đọc ngay sau;
    # `ok` của $I về trễ sẽ bị query() nhận nhầm nếu không chờ.
    svc.send_line("$I")
    assert mc.config_filename(svc) == "ConfigNCKH-16.yaml"
    assert svc._pending_acks == 0


def test_backups_list_and_read(svc, tmp_path):
    assert mc.list_backups() == []
    mc.apply_values(svc, {"axes/x/max_rate_mm_per_min": 5500})
    mc.save_to_board(svc)                       # sao lưu bản gốc (6000) rồi ghi 5500
    [item] = mc.list_backups()
    backup = mc.read_backup(item["name"])
    assert backup["values"]["axes/x/max_rate_mm_per_min"] == 6000.0
    for bad in ("../profile.json", "x.yaml", "20261029-120000_..\a.yaml"):
        with pytest.raises(mc.ConfigError):
            mc.read_backup(bad)


def test_backup_routes(client, tmp_path, monkeypatch):
    assert client.get("/api/machine/config/backups").json() == {"backups": []}
    r = client.get("/api/machine/config/backups/20261029-120000_ConfigNCKH-16.yaml")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
