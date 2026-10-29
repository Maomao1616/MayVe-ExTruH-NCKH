import os

# TestClient gửi Host "testserver"; phải đặt trước khi app.main được import.
os.environ.setdefault("EXTRUXY_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
