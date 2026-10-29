from app.links.protocol import classify_line, is_read_only_command, parse_status


def test_status_idle():
    st = parse_status("<Idle|MPos:1.000,2.500,0.000|Bf:15,128|FS:0,0>")
    assert st["state"] == "Idle" and st["substate"] is None
    assert st["mpos"] == [1.0, 2.5, 0.0]
    assert (st["planner_free"], st["rx_free"]) == (15, 128)
    assert (st["feed"], st["spindle"]) == (0.0, 0.0)


def test_status_hold_substate_and_wco():
    st = parse_status("<Hold:0|MPos:0,0,0|WCO:10.0,20.0,0.0>")
    assert st["state"] == "Hold" and st["substate"] == "0"
    assert st["wco"] == [10.0, 20.0, 0.0]


def test_status_sd_progress():
    st = parse_status("<Run|MPos:0,0,0|SD:42.5,/sd/cat.gcode>")
    assert st["sd"] == {"percent": 42.5, "file": "/sd/cat.gcode"}


def test_status_bad_field_is_ignored():
    st = parse_status("<Idle|MPos:abc|Bf:15,128>")
    assert st["mpos"] is None and st["planner_free"] == 15


def test_not_status():
    assert parse_status("ok") is None


def test_classify():
    assert classify_line("ok")["kind"] == "ok"
    assert classify_line("error:9") == {"kind": "error", "code": 9, "name": "SystemGcLock"}
    assert classify_line("ALARM:14")["name"] == "Unhomed"
    assert classify_line("Grbl 3.9 [FluidNC v4.1.1 (wifi)]")["kind"] == "banner"
    assert classify_line("[MSG:INFO: hello]") == {"kind": "message", "text": "INFO: hello"}
    assert classify_line("<Idle|MPos:0,0,0>")["kind"] == "status"
    assert classify_line("whatever")["kind"] == "other"


def test_read_only_commands():
    for ok in ("$I", "$cmd", "$G", "$SD/ListJSON", "$SD/Status", "$LocalFS/Show=/config.yaml"):
        assert is_read_only_command(ok), ok
    for bad in ("$H", "$X", "$J=G91X10F100", "G0 X10", "$SD/Run=/a.gcode", "$Bye"):
        assert not is_read_only_command(bad), bad
