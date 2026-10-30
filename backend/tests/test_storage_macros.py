"""Macro lưu ở máy chủ + xem/tải nội dung thư mục dữ liệu qua API."""
import json

import pytest
from fastapi.testclient import TestClient

from app import paths
from app.main import app

client = TestClient(app)
OK = {"name": "Nâng bút", "type": "gcode", "lines": ["G90", "G1 Z5 F3000 ; lên"], "needsHome": False}


def create(**over):
    r = client.post("/api/macros", json={**OK, **over})
    return r


def test_macro_crud_roundtrip_and_file_on_disk():
    assert client.get("/api/macros").json()["macros"] == []
    r = create()
    assert r.status_code == 201
    macro = r.json()["macro"]
    assert macro["lines"] == ["G90", "G1 Z5 F3000"] and macro["id"].startswith("m_")   # chú thích bị bỏ
    assert (paths.macros_dir() / f"{macro['id']}.json").is_file()

    r = client.put(f"/api/macros/{macro['id']}", json={**OK, "name": "Lên bút", "needsHome": True})
    assert r.status_code == 200 and r.json()["macro"]["needsHome"] is True
    assert [m["name"] for m in client.get("/api/macros").json()["macros"]] == ["Lên bút"]

    assert client.delete(f"/api/macros/{macro['id']}").status_code == 200
    assert client.get("/api/macros").json()["macros"] == []
    assert client.delete(f"/api/macros/{macro['id']}").status_code == 404


@pytest.mark.parametrize("over,code", [
    ({"name": "  "}, "name"),
    ({"name": "x" * 41}, "name"),
    ({"type": "python"}, "type"),
    ({"lines": []}, "lines_empty"),
    ({"lines": ["; chỉ chú thích"]}, "lines_empty"),
    ({"lines": ["G1 X1 ?"]}, "realtime_char"),
    ({"lines": ["$H"]}, "no_dollar"),
    ({"type": "command", "lines": ["$I", "$G"]}, "command_one_line"),
    ({"lines": ["G1 X" + "9" * 250]}, "line_too_long"),
    ({"lines": ["G1 X1"] * 51}, "lines_too_many"),
])
def test_macro_validation(over, code):
    r = create(**over)
    assert r.status_code == 400 and r.json()["error"]["code"] == code


def test_command_macro_may_use_dollar_and_names_are_unique():
    assert create(name="Home", type="command", lines=["$H"]).status_code == 201
    r = create(name="home", type="command", lines=["$X"])
    assert r.status_code == 400 and r.json()["error"]["code"] == "name_taken"


def test_macro_count_limit():
    for i in range(30):
        assert create(name=f"m{i}").status_code == 201
    r = create(name="thua")
    assert r.status_code == 400 and r.json()["error"]["code"] == "too_many"


def test_macro_ids_cannot_escape_the_folder():
    assert client.delete("/api/macros/..%2Fprofile").status_code in (404, 405)
    assert client.put("/api/macros/m_../x", json=OK).status_code in (404, 405)
    assert client.put("/api/macros/m_zzzzzz", json=OK).status_code == 404       # id hợp lệ nhưng chưa có


def test_damaged_macro_file_is_skipped(tmp_path):
    folder = paths.macros_dir()
    folder.mkdir(parents=True)
    (folder / "m_abcdef12.json").write_text("{hong", encoding="utf-8")
    (folder / "m_abcdef13.json").write_text(json.dumps({"id": "m_abcdef13", "name": "ok", "type": "gcode",
                                                         "lines": ["G90"]}), encoding="utf-8")
    assert [m["id"] for m in client.get("/api/macros").json()["macros"]] == ["m_abcdef13"]


# --- xem thư mục dữ liệu ----------------------------------------------------------------------
def test_overview_lists_three_fixed_areas_even_when_empty():
    data = client.get("/api/storage").json()
    assert [a["key"] for a in data["areas"]] == ["drafts", "config_backups", "macros"]
    assert all(a["exists"] is False and a["count"] == 0 for a in data["areas"])
    assert data["root"] == str(paths.DATA_DIR) and data["files"] == []


def test_overview_shows_entries_sizes_and_loose_files():
    create()
    backups = paths.backups_dir()
    backups.mkdir(parents=True)
    (backups / "20261029-221804_ConfigNCKH-16.yaml").write_bytes(b"name: x\n")
    draft = paths.drafts_dir() / "20261030-120000-hinh"
    draft.mkdir(parents=True)
    (draft / "meta.json").write_bytes(b"{}")
    (draft / "draw.gcode").write_bytes(b"G90\n")
    paths.data_file("profile.json").write_text("{}", encoding="utf-8")

    data = client.get("/api/storage").json()
    by_key = {a["key"]: a for a in data["areas"]}
    assert by_key["macros"]["count"] == 1 and by_key["config_backups"]["entries"][0]["kind"] == "file"
    [entry] = by_key["drafts"]["entries"]
    assert entry["kind"] == "dir" and sorted(f["name"] for f in entry["files"]) == ["draw.gcode", "meta.json"]
    assert entry["size"] == 6          # "{}" + "G90\n"
    assert [f["name"] for f in data["files"]] == ["profile.json"]


def test_download_file_and_path_checks():
    backups = paths.backups_dir()
    backups.mkdir(parents=True)
    (backups / "20261029-221804_ConfigNCKH-16.yaml").write_bytes(b"name: x\n")
    draft = paths.drafts_dir() / "20261030-120000-hinh"
    draft.mkdir(parents=True)
    (draft / "draw.gcode").write_bytes(b"G90\n")
    paths.data_file("profile.json").write_text("{}", encoding="utf-8")

    r = client.get("/api/storage/file", params={"area": "config_backups", "path": "20261029-221804_ConfigNCKH-16.yaml"})
    assert r.status_code == 200 and r.text == "name: x\n"
    r = client.get("/api/storage/file", params={"area": "drafts", "path": "20261030-120000-hinh/draw.gcode"})
    assert r.status_code == 200 and r.text == "G90\n"

    for area, path in [("drafts", "../profile.json"), ("drafts", "20261030-120000-hinh/../../profile.json"),
                       ("drafts", "a/b/c"), ("drafts", "/etc/passwd"), ("drafts", "..\\profile.json"),
                       ("khac", "x.json"), ("drafts", "")]:
        r = client.get("/api/storage/file", params={"area": area, "path": path})
        assert r.status_code in (400, 404), (area, path, r.status_code)
    assert client.get("/api/storage/file", params={"area": "drafts", "path": "profile.json"}).status_code == 404
