"""Tiếp tục từ dòng N: chọn dòng bắt đầu lại an toàn (hàm thuần) + ghi điểm dừng khi hủy/lỗi (máy giả)."""
import pytest

from app.services import resume
from app.services.machine import MachineService, ServiceError
from tests.helpers import wait_for

# Hai nét; bút lên = Z5, xuống = Z0. Chỉ số dòng (từ 0) ghi bên phải.
LINES = [
    "G90 G21",            # 0
    "G1 Z5 F3000",        # 1
    "G0 X10 Y10",         # 2
    "G1 Z0",              # 3
    "G1 X20 Y10 F1500",   # 4
    "G1 X20 Y20",         # 5
    "G1 Z5",              # 6
    "G0 X30 Y30",         # 7
    "G1 Z0",              # 8
    "G1 X40 Y30",         # 9
    "G1 X40 Y40",         # 10
    "G1 Z5",              # 11
]


# --- plan(): hàm thuần -----------------------------------------------------------------
def test_plan_restarts_at_a_pen_up_line_and_rebuilds_state():
    p = resume.plan(LINES, done=10, pen_feed=3000, margin=1)
    # lùi 1 dòng -> chỉ số 9, bút đang xuống; lùi tiếp tới chỗ bút nhấc gần nhất (trước dòng 8 "G1 Z0")
    assert p["start"] == 8 and p["rewound"] == 2
    assert p["prefix"] == ["G90 G21", "G1 Z5 F3000", "G0 X30 Y30", "G1 F1500"]


def test_plan_margin_larger_than_done_restarts_from_the_beginning():
    p = resume.plan(LINES, done=5, pen_feed=3000)         # biên 64 dòng > số dòng đã chạy
    assert p == {"start": 0, "prefix": [], "rewound": 5, "pen_known": True}


def test_plan_without_progress_is_a_full_restart():
    assert resume.plan(LINES, done=0, pen_feed=3000)["start"] == 0


def test_plan_file_without_z_resumes_right_at_the_margin():
    lines = ["G90 G21", "G1 X10 Y0 F1000", "G1 X10 Y10", "G1 X0 Y10", "G1 X0 Y0"]
    p = resume.plan(lines, done=4, pen_feed=3000, margin=1)
    assert p["start"] == 3 and not p["pen_known"]
    assert p["prefix"] == ["G90 G21", "G0 X10 Y10", "G1 F1000"]      # không có Z nào -> không thêm dòng nâng bút


def test_plan_keeps_inches():
    lines = ["G20 G90", "G1 Z0.2 F100", "G0 X1 Y1", "G1 Z0", "G1 X2", "G1 Z0.2"]
    p = resume.plan(lines, done=5, pen_feed=3000, margin=1)
    assert p["prefix"][0] == "G90 G20"


@pytest.mark.parametrize("bad", ["G91", "G92 X0 Y0", "G10 L20 P1 X0", "G28", "G53 G0 X0", "G55", "M3 S100"])
def test_plan_refuses_state_it_cannot_rebuild(bad):
    lines = ["G90 G21", "G1 Z5 F3000", bad, "G0 X10 Y10", "G1 Z0", "G1 X20", "G1 Z5", "G0 X30", "G1 Z0", "G1 X40"]
    with pytest.raises(resume.ResumeError) as info:
        resume.plan(lines, done=9, pen_feed=3000, margin=1)
    assert info.value.code == "not_resumable"


def test_plan_ignores_unsafe_lines_after_the_restart_point():
    lines = LINES + ["G92 X0 Y0"]                         # chỉ nằm SAU điểm bắt đầu lại: không ảnh hưởng
    assert resume.plan(lines, done=10, pen_feed=3000, margin=1)["start"] == 8


# --- lưu / đọc ------------------------------------------------------------------------------
def test_save_load_clear_and_describe():
    assert resume.load() is None and resume.describe(None, 3000) == {"available": False}
    resume.save("hinh", LINES, 10, "cancelled", None, [0.0, 0.0, 0.0])
    info = resume.describe([0.0, 0.0, 0.0], 3000)
    assert info["available"] and info["total"] == 12 and info["done"] == 10
    assert info["resumable"] and info["resume_line"] == 1 and info["wco_changed"] is False   # biên 64 -> từ đầu
    assert "lines" not in info
    assert resume.describe([5.0, 0.0, 0.0], 3000)["wco_changed"] is True
    assert resume.describe(None, 3000)["wco_changed"] is False                              # chưa biết thì không chặn
    resume.clear()
    assert resume.load() is None


def test_load_rejects_damaged_file(tmp_path):
    from app import paths
    path = paths.data_file(resume.FILE_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{khong phai json", encoding="utf-8")
    assert resume.load() is None
    path.write_text('{"version": 1, "lines": []}', encoding="utf-8")
    assert resume.load() is None


# --- với máy giả -----------------------------------------------------------------------------
@pytest.fixture
def svc():
    s = MachineService(allow_motion=False)
    yield s
    s.disconnect()


def homed(svc):
    svc.connect("sim", sim_speed=1)                 # tốc độ thật để còn kịp hủy giữa chừng
    svc.send_line("$H")
    assert wait_for(lambda: svc.snapshot()["homed_guess"])
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Idle")


SLOW = ["G90 G21", "G1 Z5 F3000", "G0 X10 Y10", "G1 Z0", "G1 X200 F200", "G1 X0"]


def test_cancel_records_a_resume_point_and_resume_restarts_the_job(svc):
    homed(svc)
    svc.start_job("hinh", SLOW)
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Run", timeout=5)
    svc.cancel_job()
    assert wait_for(lambda: resume.load() is not None, timeout=5)
    info = svc.resume_info()
    assert info["available"] and info["name"] == "hinh" and info["state"] == "cancelled"
    assert info["total"] == len(SLOW) and info["resume_line"] == 1

    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Alarm", timeout=5)
    svc.send_line("$X")
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Idle", timeout=5)
    job = svc.resume_job()
    assert job["state"] == "running" and "tiếp từ dòng 1" in job["name"] and job["total"] == len(SLOW)
    svc.cancel_job()
    assert wait_for(lambda: svc.snapshot()["job"]["state"] == "cancelled")
    assert wait_for(lambda: resume.load() is not None)       # điểm dừng mới thay điểm cũ, vẫn tính theo tệp gốc
    assert resume.load()["name"] == "hinh" and resume.load()["total"] == len(SLOW)


def test_finishing_a_job_clears_the_resume_point(svc):
    resume.save("cu", SLOW, 3, "cancelled", None, None)
    svc.connect("sim", sim_speed=100)
    svc.send_line("$H")
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Idle")
    svc.start_job("ngan", ["G90 G21", "G0 X1 Y1"])
    assert wait_for(lambda: svc.snapshot()["job"]["state"] == "done", timeout=10)
    assert resume.load() is None


def test_resume_without_record_and_with_changed_origin(svc):
    svc.connect("sim", sim_speed=100)
    with pytest.raises(ServiceError) as info:
        svc.resume_job()
    assert info.value.code == "no_resume"

    resume.save("hinh", SLOW, 3, "cancelled", None, [1.0, 2.0, 0.0])       # gốc làm việc lúc dừng
    svc._wco = [0.0, 0.0, 0.0]                                             # bây giờ gốc đã khác
    with pytest.raises(ServiceError) as info:
        svc.resume_job()
    assert info.value.code == "wco_changed"


def test_discard_resume(svc):
    resume.save("hinh", SLOW, 3, "failed", None, None)
    assert svc.discard_resume() == {"ok": True}
    assert svc.resume_info() == {"available": False}
