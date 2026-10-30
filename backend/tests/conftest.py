import os

# TestClient gửi Host "testserver"; phải đặt trước khi app.main được import.
# Xử lý ảnh chạy ngay trong tiến trình test (nhanh); test_isolated.py bật lại chế độ tiến trình riêng.
os.environ.setdefault("EXTRUXY_DRAW_INPROC", "1")
os.environ.setdefault("EXTRUXY_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")


import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Mọi test ghi dữ liệu (bản thảo, sao lưu, hồ sơ, điểm dừng, macro) vào thư mục tạm, không đụng backend/data."""
    from app import paths
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
