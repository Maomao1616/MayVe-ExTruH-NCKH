"""Đường dừng an toàn và đường LỖI của MachineService (hủy tác vụ: Feed Hold -> Reset -> mở khóa Alarm -> nâng bút).

Khác tests/test_safe_stop.py (chạy trên SimLink, chỉ đường thuận): ở đây mạch là một KỊCH BẢN viết tay,
nên ép được những chuyện máy giả không tự gây ra: mạch im lặng, lệnh ghi thất bại, Alarm cứng đầu,
phiên bị thay giữa chừng. Mỗi bài kiểm CẢ HAI: kết quả trả về VÀ đúng những lệnh đã gửi xuống mạch
(đặc biệt: không bao giờ jog Z khi chưa xác nhận Idle).
Chỉ kiểm lô-gíc ở máy chủ; KHÔNG chứng minh hành vi trên firmware / máy thật.
"""
import time

import pytest

from app.links.base import LinkError
from app.services.machine import REALTIME, MachineService, ServiceError

WAIT_CAP_S = 0.25          # chờ báo cáo trạng thái: thật là 3-120 s, ở đây rút còn 0,25 s để bài "mạch im lặng" chạy nhanh
LIFT = "$J=G90 G21 Z5 F3000"
NAME_OF = {data: name for name, data in REALTIME.items()}


class ScriptedBoard:
    """Mạch giả: nhận lệnh MachineService gửi xuống, trả trạng thái theo kịch bản `on`."""

    def __init__(self, svc: MachineService):
        self.svc = svc
        self.sent: list[str] = []          # lệnh đã ghi thành công, theo thứ tự ("hold", "reset", "status", "$X", "$J=...")
        self.on: dict = {}                 # khóa lệnh -> hàm chạy ngay khi mạch nhận; không có khóa = mạch im lặng
        self.fail: set[str] = set()        # khóa lệnh mà việc ghi báo LinkError
        self.before_wait: list = []        # chạy trước lần chờ báo cáo kế tiếp (đặt báo cáo "đến giữa lúc đang chờ", chắc chắn thứ tự)

    def report(self, state: str, z: float | None = 0.0, substate: str = "0", error: int | None = None) -> None:
        """Một báo cáo trạng thái MỚI (seq tăng); error = mã lỗi firmware vừa báo."""
        with self.svc._lock:
            self.svc._status = {"state": state, "substate": substate,
                                "wpos": None if z is None else [0.0, 0.0, z]}
            self.svc._status_seq += 1
            if error is not None:
                self.svc._last_error = {"code": error, "name": "kịch bản", "at": time.time()}

    # --- giao diện BaseLink mà MachineService dùng ---
    def write_realtime(self, data: bytes) -> None:
        name = NAME_OF[data]
        self._act(name, name)

    def write_line(self, text: str) -> None:
        self._act("$J" if text.startswith("$J") else text, text)

    def _act(self, key: str, shown: str) -> None:
        if key in self.fail:
            raise LinkError("kịch bản: ghi xuống mạch thất bại")
        self.sent.append(shown)
        handler = self.on.get(key)
        if handler:
            handler()

    def close(self) -> None:
        pass


@pytest.fixture
def rig():
    svc = MachineService(allow_motion=True)
    board = ScriptedBoard(svc)
    svc._link = board
    svc._info["mode"] = "sim"
    token = object()
    svc._stop_token = token
    real_wait = svc._wait_state

    def capped_wait(predicate, timeout, after=None, token=None):
        if board.before_wait:
            board.before_wait.pop(0)()
        return real_wait(predicate, min(timeout, WAIT_CAP_S), after, token)

    svc._wait_state = capped_wait
    yield svc, board, token
    svc._link = None


def logs(svc: MachineService) -> list[str]:
    return [e["text"] for e in svc.log_since(0)["entries"]]


def has_log(svc: MachineService, part: str) -> bool:
    return any(part in text for text in logs(svc))


def jogs(board: ScriptedBoard) -> list[str]:
    return [s for s in board.sent if s.startswith("$J")]


# ============================ _hard_stop_sequence ============================
def test_hard_stop_from_run_holds_then_resets_then_confirms_idle(rig):
    svc, board, token = rig
    board.report("Run")
    board.on = {"hold": lambda: board.report("Hold"),
                "reset": lambda: board.report("Idle"),
                "status": lambda: board.report("Idle")}
    assert svc._hard_stop_sequence(token) is True
    assert board.sent == ["hold", "reset", "status"]
    assert has_log(svc, "Hard stop: fresh Idle status confirmed")


def test_feed_hold_write_failure_still_goes_on_to_reset(rig):
    svc, board, token = rig
    board.report("Run")
    board.fail = {"hold"}
    board.on = {"reset": lambda: board.report("Idle"), "status": lambda: board.report("Idle")}
    assert svc._hard_stop_sequence(token) is True
    assert board.sent == ["reset", "status"]
    assert has_log(svc, "Feed Hold failed (link_error); attempting Reset")


def test_feed_hold_not_confirmed_still_goes_on_to_reset(rig):
    svc, board, token = rig
    board.report("Run")                                     # mạch im lặng sau Hold
    board.on = {"reset": lambda: board.report("Idle"), "status": lambda: board.report("Idle")}
    assert svc._hard_stop_sequence(token) is True
    assert board.sent == ["hold", "reset", "status"]
    assert has_log(svc, "Feed Hold completion not confirmed; attempting Reset")


def test_reset_write_failure_stops_the_sequence(rig):
    svc, board, token = rig
    board.report("Idle")
    board.fail = {"reset"}
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == []
    assert has_log(svc, "Reset command failed (link_error)")


def test_no_fresh_status_after_reset_is_a_failure(rig):
    svc, board, token = rig
    board.report("Idle")                                    # Reset gửi được nhưng mạch không báo gì lại
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == ["reset"]
    assert has_log(svc, "no fresh Idle/Alarm status after Reset")


def test_alarm_is_cleared_with_dollar_x_and_no_second_reset(rig):
    svc, board, token = rig
    board.report("Alarm")
    board.on = {"$X": lambda: board.report("Idle"), "status": lambda: board.report("Idle")}
    assert svc._hard_stop_sequence(token) is True
    assert board.sent == ["$X", "status"]


def test_alarm_that_demands_reset_first_gets_reset_then_unlock(rig):
    svc, board, token = rig
    board.report("Alarm")
    svc._reset_required = True                              # ALARM:1 của firmware: "Reset to continue"
    board.on = {"reset": lambda: board.report("Alarm"),     # sau Reset vẫn Alarm, cần $X
                "$X": lambda: board.report("Idle"),
                "status": lambda: board.report("Idle")}
    assert svc._hard_stop_sequence(token) is True
    assert board.sent == ["reset", "$X", "status"]
    assert has_log(svc, "firmware needs Reset before $X")


def test_stubborn_alarm_gets_one_reset_retry_then_gives_up(rig):
    svc, board, token = rig
    board.report("Alarm")
    board.on = {"$X": lambda: board.report("Alarm"), "reset": lambda: board.report("Alarm")}
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == ["$X", "reset", "$X"]              # đúng MỘT lần thử lại, không lặp vô hạn
    assert has_log(svc, "Idle was not confirmed after $X; the pen was NOT lifted")


def test_unlock_write_failure_stops_the_sequence(rig):
    svc, board, token = rig
    board.report("Idle")
    board.fail = {"$X"}
    board.on = {"reset": lambda: board.report("Alarm")}
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == ["reset"]
    assert has_log(svc, "unlock failed (link_error)")


def test_reset_write_failure_inside_unlock_stops(rig):
    svc, board, token = rig
    board.report("Alarm")
    svc._reset_required = True
    board.fail = {"reset"}
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == []
    assert has_log(svc, "Reset command failed (link_error)")


def test_silent_board_after_reset_inside_unlock_stops(rig):
    svc, board, token = rig
    board.report("Alarm")
    svc._reset_required = True
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == ["reset"]
    assert has_log(svc, "no fresh status after Reset")


def test_final_status_query_write_failure_is_a_failure(rig):
    svc, board, token = rig
    board.report("Idle")
    board.fail = {"status"}
    board.on = {"reset": lambda: board.report("Idle")}
    assert svc._hard_stop_sequence(token) is False
    assert has_log(svc, "status query failed (link_error)")


def test_final_idle_not_confirmed_is_a_failure(rig):
    svc, board, token = rig
    board.report("Idle")
    board.on = {"reset": lambda: board.report("Idle")}      # câu hỏi "?" cuối không được trả lời
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == ["reset", "status"]
    assert has_log(svc, "fresh Idle status was not confirmed; pen was NOT lifted")


def test_hard_stop_with_stale_token_sends_nothing(rig):
    svc, board, token = rig
    board.report("Run")
    assert svc._hard_stop_sequence(object()) is False
    assert board.sent == []
    assert has_log(svc, "Hard stop: link unavailable or session changed")


def test_session_replaced_after_hold_aborts_before_reset(rig):
    svc, board, token = rig
    board.report("Run")
    board.on = {"hold": lambda: setattr(svc, "_stop_token", None)}   # người dùng nối lại giữa chừng
    assert svc._hard_stop_sequence(token) is False
    assert board.sent == ["hold"]                           # luồng dừng cũ KHÔNG được gửi Reset vào phiên mới
    assert has_log(svc, "link lost or session changed before Reset")


# ============================ _send_pen_lift ============================
def test_pen_lift_is_refused_unless_machine_is_idle(rig):
    svc, board, token = rig
    board.report("Run")
    assert svc._send_pen_lift(token, 5.0, 3000.0) is False
    assert board.sent == []                                 # không jog Z khi chưa Idle
    assert has_log(svc, "machine is not confirmed Idle; cannot lift the pen")


def test_pen_lift_confirmed_only_when_z_arrives(rig):
    svc, board, token = rig
    board.report("Idle", z=0.0)
    board.on = {"$J": lambda: board.report("Idle", z=5.0)}
    assert svc._send_pen_lift(token, 5.0, 3000.0) is True
    assert board.sent == [LIFT]
    assert has_log(svc, "pen lift confirmed (Z5)")


def test_pen_lift_with_unknown_z_still_needs_confirmation(rig):
    svc, board, token = rig
    board.report("Idle", z=None)                            # báo cáo chưa có WPos
    board.on = {"$J": lambda: board.report("Idle", z=5.0)}
    assert svc._send_pen_lift(token, 5.0, 3000.0) is True


def test_pen_lift_write_failure_is_reported(rig):
    svc, board, token = rig
    board.report("Idle")
    board.fail = {"$J"}
    assert svc._send_pen_lift(token, 5.0, 3000.0) is False
    assert has_log(svc, "pen lift command failed (link_error); the pen may still be DOWN")


def test_pen_lift_without_any_answer_is_not_confirmed(rig):
    svc, board, token = rig
    board.report("Idle")
    assert svc._send_pen_lift(token, 5.0, 3000.0) is False
    assert has_log(svc, "pen lift NOT confirmed")


def test_pen_lift_stuck_at_wrong_z_is_not_confirmed(rig):
    svc, board, token = rig
    board.report("Idle", z=0.0)
    board.on = {"$J": lambda: board.report("Idle", z=2.0)}  # lên được nửa đường rồi đứng
    assert svc._send_pen_lift(token, 5.0, 3000.0) is False
    assert has_log(svc, "pen lift NOT confirmed")


def test_pen_lift_alarm_is_a_failure(rig):
    svc, board, token = rig
    board.report("Idle")
    board.on = {"$J": lambda: board.report("Alarm")}
    assert svc._send_pen_lift(token, 5.0, 3000.0) is False
    assert has_log(svc, "ALARM during pen lift")


def test_pen_lift_rejected_by_firmware_is_a_failure(rig):
    svc, board, token = rig
    board.report("Idle")
    board.on = {"$J": lambda: board.report("Idle", z=0.0, error=15)}
    assert svc._send_pen_lift(token, 5.0, 3000.0) is False
    assert has_log(svc, "pen lift rejected by firmware (error:15)")


# ============================ _stop_sequence (điều phối) ============================
def test_stop_with_dead_session_does_nothing(rig):
    svc, board, token = rig
    board.report("Run")
    svc._stop_sequence(object(), "hard", 5.0, 3000.0)
    assert board.sent == []
    assert has_log(svc, "link unavailable or session changed; machine stop is NOT confirmed")
    assert svc._stop_token is token                         # token của phiên khác không bị xóa nhầm


def test_hard_stop_then_lift_sends_commands_in_the_safe_order(rig):
    svc, board, token = rig
    board.report("Run")
    board.on = {"hold": lambda: board.report("Hold"),
                "reset": lambda: board.report("Idle"),
                "status": lambda: board.report("Idle"),
                "$J": lambda: board.report("Idle", z=5.0)}
    svc._stop_sequence(token, "hard", 5.0, 3000.0)
    assert board.sent == ["hold", "reset", "status", LIFT]
    assert has_log(svc, "pen lift confirmed")
    assert svc._stop_token is None                          # xong thì mở lại cho lệnh khác


def test_failed_hard_stop_never_lifts_the_pen(rig):
    svc, board, token = rig
    board.report("Idle")                                    # Reset không được trả lời
    svc._stop_sequence(token, "hard", 5.0, 3000.0)
    assert jogs(board) == []
    assert has_log(svc, "Idle was not confirmed. The pen was NOT lifted")
    assert svc._stop_token is None


def test_stop_without_lift_request_sends_no_jog(rig):
    svc, board, token = rig
    board.report("Idle")
    board.on = {"reset": lambda: board.report("Idle"), "status": lambda: board.report("Idle")}
    svc._stop_sequence(token, "hard", None, 3000.0)
    assert jogs(board) == []
    assert has_log(svc, "done (no pen lift requested)")


def test_soft_stop_on_a_held_machine_falls_back_to_hard(rig):
    svc, board, token = rig
    board.report("Hold")
    board.on = {"reset": lambda: board.report("Idle"),
                "status": lambda: board.report("Idle"),
                "$J": lambda: board.report("Idle", z=5.0)}
    svc._stop_sequence(token, "soft", 5.0, 3000.0)
    assert has_log(svc, "Soft stop: machine is Hold; falling back to hard stop")
    assert board.sent == ["reset", "status", LIFT]


def test_soft_stop_waits_for_idle_then_lifts_without_reset(rig):
    svc, board, token = rig
    board.report("Run")
    board.before_wait = [lambda: board.report("Idle")]      # máy chạy nốt rồi Idle
    board.on = {"$J": lambda: board.report("Idle", z=5.0)}
    svc._stop_sequence(token, "soft", 5.0, 3000.0)
    assert board.sent == [LIFT]                             # soft stop: không Hold, không Reset
    assert has_log(svc, "Soft stop: fresh Idle status confirmed")


def test_soft_stop_that_times_out_falls_back_to_hard(rig):
    svc, board, token = rig
    board.report("Run")                                     # không bao giờ Idle
    board.on = {"hold": lambda: board.report("Hold"),
                "reset": lambda: board.report("Idle"),
                "status": lambda: board.report("Idle"),
                "$J": lambda: board.report("Idle", z=5.0)}
    svc._stop_sequence(token, "soft", 5.0, 3000.0)
    assert has_log(svc, "timed out or status was lost; falling back to hard stop")
    assert board.sent == ["hold", "reset", "status", LIFT]


def test_soft_stop_that_ends_in_alarm_falls_back_to_hard(rig):
    svc, board, token = rig
    board.report("Run")
    board.before_wait = [lambda: board.report("Alarm")]
    board.on = {"$X": lambda: board.report("Idle"),
                "status": lambda: board.report("Idle"),
                "$J": lambda: board.report("Idle", z=5.0)}
    svc._stop_sequence(token, "soft", 5.0, 3000.0)
    assert has_log(svc, "machine entered Alarm; falling back to hard stop")
    assert board.sent == ["$X", "status", LIFT]


def test_soft_stop_is_abandoned_when_the_session_changes(rig):
    svc, board, token = rig
    board.report("Run")
    board.before_wait = [lambda: setattr(svc, "_stop_token", None)]
    svc._stop_sequence(token, "soft", 5.0, 3000.0)
    assert board.sent == []
    assert has_log(svc, "Soft stop: session changed; stop abandoned")


def test_soft_stop_failed_lift_retries_once_after_hard_stop(rig):
    svc, board, token = rig
    board.report("Run")
    board.before_wait = [lambda: board.report("Idle")]
    answers = iter([False, True])                           # lần nâng đầu mạch im lặng, lần hai thành công
    board.on = {"$J": lambda: board.report("Idle", z=5.0) if next(answers) else None,
                "reset": lambda: board.report("Idle"),
                "status": lambda: board.report("Idle")}
    svc._stop_sequence(token, "soft", 5.0, 3000.0)
    assert has_log(svc, "pen lift failed; falling back to hard stop and retrying")
    assert board.sent == [LIFT, "reset", "status", LIFT]


def test_unexpected_errors_in_the_stop_thread_are_logged_not_raised(rig, monkeypatch):
    svc, board, token = rig
    board.report("Run")
    monkeypatch.setattr(svc, "_hard_stop_sequence", lambda t: (_ for _ in ()).throw(RuntimeError("boom")))
    svc._stop_sequence(token, "hard", 5.0, 3000.0)
    assert has_log(svc, "Safe stop failed unexpectedly (RuntimeError). The pen may still be DOWN")
    assert svc._stop_token is None


def test_service_errors_in_the_stop_thread_are_logged_with_their_code(rig, monkeypatch):
    svc, board, token = rig
    board.report("Run")

    def boom(_token):
        raise ServiceError("link_error", "mất cổng", 502)

    monkeypatch.setattr(svc, "_hard_stop_sequence", boom)
    svc._stop_sequence(token, "hard", 5.0, 3000.0)
    assert has_log(svc, "Safe stop failed (link_error). The pen may still be DOWN")
    assert svc._stop_token is None


# ============================ job_hold / _reset_now ============================
def test_job_hold_confirmed_when_board_holds(rig):
    svc, board, token = rig
    board.report("Run")
    board.on = {"hold": lambda: board.report("Hold")}
    svc.job_hold()
    assert has_log(svc, "Job: Feed Hold confirmed")


def test_job_hold_not_confirmed_when_board_is_silent(rig):
    svc, board, token = rig
    board.report("Run")
    svc.job_hold()
    assert has_log(svc, "Job: Feed Hold sent but stop is NOT confirmed")


def test_job_hold_without_connection_says_stop_is_not_confirmed():
    svc = MachineService(allow_motion=True)
    svc.job_hold()
    assert has_log(svc, "Job: Feed Hold failed (not_connected); machine stop is NOT confirmed")


def test_failed_reset_on_cancel_is_logged_loudly():
    svc = MachineService(allow_motion=True)
    svc._reset_now()
    assert has_log(svc, "Cancel: Reset failed (not_connected); machine stop is NOT confirmed")
