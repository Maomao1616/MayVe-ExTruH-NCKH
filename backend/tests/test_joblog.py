"""Số liệu từng lần chạy máy (services/joblog.py): ghi CSV khi chạy, tóm tắt, API, dọn bớt, không làm hỏng luồng serial."""
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import joblog
from app.services.machine import MachineService
from tests.helpers import wait_for

# Nét dài vừa đủ để có nhiều báo cáo trạng thái trong lúc chạy (máy giả chạy x20).
LINES = ["G21 G90", "G1 Z5 F3000"] + [
    line for i in range(6) for line in (f"G0 X{10 + i} Y10", "G1 Z0 F2000", f"G1 X{200 + i} Y{10 + i} F6000", "G1 Z5 F3000")
] + ["G0 X0 Y0"]


@pytest.fixture
def svc():
    s = MachineService(allow_motion=False)
    yield s
    s.disconnect()


def homed(svc, speed=20):
    svc.connect("sim", sim_speed=speed)
    svc.send_line("$H")
    assert wait_for(lambda: svc.snapshot()["homed_guess"])
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("state") == "Idle")


def run_job(svc, client=None):
    svc.start_job("thu", LINES, client)
    assert wait_for(lambda: (svc.snapshot()["job"] or {}).get("state") == "done", timeout=30)
    # sau khi tác vụ xong, báo cáo kế tiếp khép nhật ký; tóm tắt được tính ở luồng riêng
    assert wait_for(lambda: bool(joblog.list_logs()) and joblog.list_logs()[0]["state"] == "done", timeout=10)
    return joblog.list_logs()[0]


def test_job_writes_csv_meta_and_summary(svc):
    homed(svc)
    row = run_job(svc, {"est_seconds": 12.5, "draw_mm": 1200.0, "rapids": 6})
    assert row["est_seconds"] == 12.5 and row["total"] == len(LINES) and row["acked"] == len(LINES)
    text = joblog.csv_file(row["id"]).read_text(encoding="utf-8").splitlines()
    assert text[0] == ",".join(joblog.COLUMNS) and len(text) > 5
    detail = joblog.read_log(row["id"])
    s = detail["summary"]
    assert s["samples"] == len(text) - 1 and s["has_bf"] is True        # máy giả mặc định $10=3
    assert 0 < s["run_pct"] <= 100 and s["feed_max"] > 0 and 0 <= s["pen_down_pct"] <= 100
    assert "starved_pct" in s
    ser = detail["series"]
    assert len(ser["t"]) == len(ser["feed"]) == len(ser["bf"]) == len(ser["z_min"])
    assert max(v for v in ser["z_max"] if v is not None) >= 5 - 1e-6     # thấy bút nhấc


def test_no_bf_when_report_mask_is_1_like_the_real_board(svc):
    homed(svc)
    svc.send_line("$10=1")
    assert wait_for(lambda: (svc.snapshot()["machine"] or {}).get("planner_free") is None)
    row = run_job(svc)
    assert row["has_bf"] is False
    s = joblog.read_log(row["id"])["summary"]
    assert s["has_bf"] is False and "starved_pct" not in s


def test_log_is_closed_when_disconnected_midway(svc):
    homed(svc, speed=1)                                  # chậm để tác vụ còn dở khi ngắt
    svc.start_job("dang-do", LINES)
    assert wait_for(lambda: bool(joblog.list_logs()), timeout=10)
    cur = joblog.csv_file(joblog.list_logs()[0]["id"])
    assert wait_for(lambda: len(cur.read_text(encoding="utf-8").splitlines()) >= 6, timeout=10)   # đủ mẫu để được giữ
    svc.disconnect()
    assert wait_for(lambda: joblog.list_logs()[0]["state"] in ("link_lost", "disconnected", "failed"), timeout=10)


def test_old_logs_are_pruned(monkeypatch):
    monkeypatch.setattr(joblog, "KEEP_FILES", 3)
    log = joblog.JobLog()
    for n in range(1, 7):
        job = {"id": n, "name": f"j{n}", "state": "running", "total": 1, "sent": 0, "acked": 0,
               "started_at": time.time() - 100 + n}           # id có giờ khác nhau: sắp theo tên = theo thời gian
        for _ in range(4):                                    # đủ mẫu để không bị coi là lần chạy rỗng
            log.observe(job, {"state": "Run", "wpos": [1, 2, 0], "feed": 100.0, "planner_free": 15, "rx_free": 128})
        log.observe({**job, "state": "done", "finished_at": time.time()}, None)
    assert wait_for(lambda: len(list(joblog.logs_dir().glob("*.csv"))) == 3, timeout=5)
    assert {r["name"] for r in joblog.list_logs()} == {"j4", "j5", "j6"}


def test_logging_errors_never_reach_the_serial_reader(monkeypatch):
    log = joblog.JobLog()
    monkeypatch.setattr(joblog, "logs_dir", lambda: (_ for _ in ()).throw(OSError("đĩa đầy")))
    job = {"id": 1, "name": "x", "state": "running", "total": 1, "sent": 0, "acked": 0, "started_at": time.time()}
    log.observe(job, {"state": "Run", "wpos": [0, 0, 0], "feed": 1.0})          # không được ném lỗi
    assert log.current_id is None


# --- API ------------------------------------------------------------------------------
def test_api_list_read_csv_delete_and_bad_ids(svc, monkeypatch):
    from app.services import machine as machine_module
    monkeypatch.setattr(machine_module, "machine", svc)
    import app.api.machine as api
    monkeypatch.setattr(api, "machine", svc)
    homed(svc)
    row = run_job(svc)
    client = TestClient(app)
    listing = client.get("/api/joblogs").json()["logs"]
    assert listing[0]["id"] == row["id"]
    detail = client.get(f"/api/joblogs/{row['id']}?points=100").json()
    assert detail["meta"]["name"] == "thu" and len(detail["series"]["t"]) <= 100
    csv_response = client.get(f"/api/joblogs/{row['id']}/csv")
    assert csv_response.status_code == 200 and csv_response.text.startswith("t,state")
    for bad in ("..%2Fprofile", "abc", "20260101-000000-1x"):
        assert client.get(f"/api/joblogs/{bad}").status_code in (400, 404)
    assert client.delete(f"/api/joblogs/{row['id']}").status_code == 200
    assert client.get(f"/api/joblogs/{row['id']}").status_code == 404
    assert client.delete("/api/joblogs/20260101-000000-9").status_code == 404


def test_api_requires_admin(monkeypatch):
    monkeypatch.setenv("EXTRUXY_ADMIN_PIN", "abcd1234")
    guest = TestClient(app)
    assert guest.get("/api/joblogs").status_code == 401


# --- cửa sổ thời gian + đọc tăng dần ------------------------------------------------------
def _fake_log(n=600, with_bf=True, job_id=7):
    """Một lần chạy giả: n mẫu cách nhau 0,1 giây, ghi thẳng qua JobLog như MachineService làm."""
    log = joblog.JobLog()
    t0 = time.time() - n * 0.1
    job = {"id": job_id, "name": "gia", "state": "running", "total": 10, "sent": 0, "acked": 0, "started_at": t0}
    log.observe(job, None, {"pen_down_z": 0.0})
    log_id = log.current_id
    for i in range(n):
        # ghi trực tiếp để giờ mẫu xác định (không phụ thuộc đồng hồ thật)
        st = {"state": "Run", "wpos": [i * 0.1, 0.0, 0.0 if i % 4 else 3.0], "feed": 3000.0 if i % 4 else 1000.0,
              "planner_free": 10 if with_bf else None, "rx_free": 128}
        with log._lock:
            log._t0 = time.time() - i * 0.1
            log._sample(job, st)
    log.observe({**job, "state": "done", "finished_at": time.time()}, None)
    assert wait_for(lambda: any(r["id"] == log_id and r["state"] == "done" for r in joblog.list_logs()), timeout=5)
    return log_id


def test_window_returns_only_the_requested_seconds_but_summary_stays_whole():
    log_id = _fake_log(600)
    full = joblog.read_log(log_id, 5000)
    assert len(full["series"]["t"]) == 600 and full["range"]["from"] == 0.0
    win = joblog.read_log(log_id, 5000, window_s=10)
    assert 95 <= len(win["series"]["t"]) <= 105                  # ~10 giây × 10 mẫu/giây
    assert abs(win["range"]["to"] - full["range"]["duration"]) < 0.01
    assert win["range"]["to"] - win["range"]["from"] == pytest.approx(10, abs=0.02)
    assert win["summary"] == full["summary"]                    # bảng tóm tắt luôn tính cả lần chạy
    mid = joblog.read_log(log_id, 5000, window_s=10, end_s=30)  # kéo cửa sổ về giữa lần chạy
    assert mid["range"]["to"] == 30 and mid["range"]["from"] == 20
    assert all(20 <= t <= 30 for t in mid["series"]["t"])
    past_end = joblog.read_log(log_id, 5000, window_s=10, end_s=10_000)
    assert past_end["range"]["to"] == past_end["range"]["duration"]


def test_incremental_read_matches_full_read_and_survives_partial_last_line(tmp_path):
    log_id = _fake_log(50)
    path = joblog.csv_file(log_id)
    joblog._CACHE.clear()
    first = joblog._read_rows(log_id)
    assert len(first) == 50
    with open(path, "a", encoding="utf-8") as fh:               # thêm 3 dòng + một dòng ghi dở (chưa có xuống dòng)
        fh.write("99.00,Run,1,2,0,500,5,128,3,3\n99.10,Run,1,2,0,500,5,128,3,3\n99.20,Run,1,2,0,500,5,128,3,3\n99.30,Ru")
    grown = joblog._read_rows(log_id)
    assert len(grown) == 53 and grown[-1]["t"] == 99.2           # dòng dở chưa tính
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("n,1,2,0,500,5,128,3,3\n")                      # hoàn tất dòng dở
    assert len(joblog._read_rows(log_id)) == 54
    joblog._CACHE.clear()
    assert len(joblog._read_rows(log_id)) == 54                  # đọc lại từ đầu ra đúng số dòng


def test_cache_is_bounded():
    ids = [_fake_log(5, job_id=k) for k in range(1, 6)]
    for log_id in ids:
        joblog._read_rows(log_id)
    assert len(joblog._CACHE) <= joblog._CACHE_MAX


def test_trivial_runs_are_not_kept():
    """Bấm Chạy rồi ngắt ngay (1-2 mẫu) không để lại nhật ký rác kiểu "0:00"."""
    log = joblog.JobLog()
    job = {"id": 3, "name": "t", "state": "running", "total": 1, "sent": 0, "acked": 0, "started_at": time.time()}
    log.observe(job, {"state": "Run", "wpos": [0, 0, 0], "feed": 1.0})
    log.observe({**job, "state": "failed", "finished_at": time.time()}, None)
    assert wait_for(lambda: not list(joblog.logs_dir().glob("*.csv")) and not list(joblog.logs_dir().glob("*.json")), timeout=5)
    assert joblog.list_logs() == []


def test_delete_while_summary_is_still_running_leaves_no_orphan_files(monkeypatch):
    """Xóa đúng lúc luồng tóm tắt đang chạy: không được tạo lại .json / .csv mồ côi (kiểu "t · 0:00")."""
    real = joblog.summarize

    def slow(rows, meta):
        time.sleep(0.6)                                  # kéo dài phần tóm tắt để kịp xóa giữa chừng
        return real(rows, meta)

    monkeypatch.setattr(joblog, "summarize", slow)
    log = joblog.JobLog()
    job = {"id": 9, "name": "xoa-giua-chung", "state": "running", "total": 1, "sent": 0, "acked": 0,
           "started_at": time.time() - 5}
    for _ in range(5):
        log.observe(job, {"state": "Run", "wpos": [0, 0, 0], "feed": 10.0, "planner_free": 4, "rx_free": 1})
    log_id = log.current_id
    log.observe({**job, "state": "done", "finished_at": time.time()}, None)   # luồng tóm tắt bắt đầu (đang ngủ)
    assert log.current_id is None                                             # không còn là lần chạy đang ghi
    joblog.delete_log(log_id)                                                 # người dùng bấm Xóa đúng lúc này
    time.sleep(1.2)                                                           # chờ luồng tóm tắt chạy xong
    assert list(joblog.logs_dir().glob("*")) == []
    assert joblog.list_logs() == []
