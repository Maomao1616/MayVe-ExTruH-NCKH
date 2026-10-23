from fastapi import FastAPI

app = FastAPI(title="ExtruXY Backend", version="0.1.0")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "extruxy-backend", "version": "0.1.0"}


@app.get("/api/status")
def status():
    # Tạm thời là dữ liệu giả; sẽ nối với SimLink/SerialLink ở các bước sau.
    return {
        "connection": {"connected": False, "mode": None},
        "machine": {"state": "Unknown"},
    }
