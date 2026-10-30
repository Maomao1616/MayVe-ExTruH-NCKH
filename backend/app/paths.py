"""Thư mục dữ liệu của phần mềm: MỘT gốc, ba thư mục con cố định.

    <gốc>/drafts/          bản thảo (mỗi bản một thư mục)
    <gốc>/config_backups/  bản sao lưu YAML gốc của mạch (trước mỗi lần "Lưu vào mạch")
    <gốc>/macros/          mỗi macro một tệp .json
    <gốc>/profile.json, draw_settings.json, resume.json   tệp lẻ

Gốc mặc định là `backend/data/`; MiniPC đặt khác bằng biến môi trường EXTRUXY_DATA_DIR.
Không có ô nhập đường dẫn trên giao diện (người lạ không được trỏ máy chủ ghi ra chỗ khác).
Thư mục tự được tạo khi cần, nên giải nén zip ở máy mới là chạy được, không phải cài đặt gì.
Test đặt lại `DATA_DIR` (tests/conftest.py) để không đụng dữ liệu thật.
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("EXTRUXY_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")

# khóa -> tên thư mục con (thứ tự hiện trên giao diện)
AREAS = {"drafts": "drafts", "config_backups": "config_backups", "macros": "macros"}


def area_dir(area: str) -> Path:
    return DATA_DIR / AREAS[area]


def drafts_dir() -> Path:
    return area_dir("drafts")


def backups_dir() -> Path:
    return area_dir("config_backups")


def macros_dir() -> Path:
    return area_dir("macros")


def data_file(name: str) -> Path:
    return DATA_DIR / name
