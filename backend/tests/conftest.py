import os

# TestClient gửi Host "testserver"; phải đặt trước khi app.main được import.
# Xử lý ảnh chạy ngay trong tiến trình test (nhanh); test_isolated.py bật lại chế độ tiến trình riêng.
os.environ.setdefault("EXTRUXY_DRAW_INPROC", "1")
os.environ.setdefault("EXTRUXY_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
