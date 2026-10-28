// DUY NHẤT nơi gọi fetch. Chỉ dùng các endpoint có trong backend v0.2.0.

const BASE = "/api";

// Lỗi chuẩn hóa: code ổn định để i18n dịch, không hiển thị thẳng message.
export class ApiError extends Error {
    constructor(code, message, status) {
        super(message || code);
        this.code = code;
        this.status = status;
    }
}

async function request(method, path, body) {
    let response;
    try {
        response = await fetch(BASE + path, {
            method,
            headers: body ? { "Content-Type": "application/json" } : undefined,
            body: body ? JSON.stringify(body) : undefined
        });
    } catch {
        throw new ApiError("backend_unreachable", "Không gọi được backend", 0);
    }

    let data = null;
    try { data = await response.json(); } catch { /* không có JSON */ }

    if (!response.ok) {
        if (data?.error) throw new ApiError(data.error.code, data.error.message, response.status);
        if (data?.detail) throw new ApiError("validation_error", "Dữ liệu không hợp lệ", response.status);
        throw new ApiError("http_error", `HTTP ${response.status}`, response.status);
    }
    return data;
}

export const api = {
    health: () => request("GET", "/health"),
    ports: () => request("GET", "/ports"),
    connection: () => request("GET", "/connection"),
    connect: (mode, port = null, baud = 115200, simSpeed = 1) =>
        request("POST", "/connect", { mode, port, baud, sim_speed: simSpeed }),
    disconnect: () => request("POST", "/disconnect"),
    status: () => request("GET", "/status"),
    command: (line) => request("POST", "/command", { line }),
    realtime: (action) => request("POST", "/realtime", { action }),
    jobStart: (name, lines) => request("POST", "/jobs", { name, lines }),
    jobCancel: () => request("POST", "/jobs/cancel"),
    log: (since = 0) => request("GET", `/log?since=${since}`),
    motion: (on, pin = null) => request("POST", "/motion", { on, pin }),
};
