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

async function request(method, path, body, { text = false } = {}) {
    const isForm = body instanceof FormData;       // tải tệp lên: để trình duyệt tự đặt Content-Type
    let response;
    try {
        response = await fetch(BASE + path, {
            method,
            headers: body && !isForm ? { "Content-Type": "application/json" } : undefined,
            body: body ? (isForm ? body : JSON.stringify(body)) : undefined
        });
    } catch {
        throw new ApiError("backend_unreachable", "Không gọi được backend", 0);
    }

    if (text && response.ok) return response.text();      // G-code / SVG: nội dung thô
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
    log: (since = 0) => request("GET", `/log?since=${since}`),
    motion: (on, pin = null) => request("POST", "/motion", { on, pin }),
    jobCancel: (mode = "reset", liftZ = null, liftFeed = 1000) =>
        request("POST", "/jobs/cancel", { mode, lift_z: liftZ, lift_feed: liftFeed }),
    jobResumeInfo: () => request("GET", "/jobs/resume"),
    jobResume: (acceptWcoChange = false) => request("POST", "/jobs/resume", { accept_wco_change: acceptWcoChange }),
    jobResumeDiscard: () => request("DELETE", "/jobs/resume"),
    machineConfig: () => request("GET", "/machine/config"),
    machineConfigApply: (values) => request("POST", "/machine/config", { values }),
    machineConfigSave: () => request("POST", "/machine/config/save"),
    machineConfigBackups: () => request("GET", "/machine/config/backups"),
    machineConfigBackup: (name) => request("GET", `/machine/config/backups/${encodeURIComponent(name)}`),
    profile: () => request("GET", "/profile"),
    profileSave: (profile) => request("PUT", "/profile", profile),

    // --- lưu trữ trên máy chủ: macro, xem thư mục dữ liệu ---
    macros: () => request("GET", "/macros"),
    macroCreate: (macro) => request("POST", "/macros", macro),
    macroUpdate: (id, macro) => request("PUT", `/macros/${id}`, macro),
    macroDelete: (id) => request("DELETE", `/macros/${id}`),
    storage: () => request("GET", "/storage"),

    // --- tab Tạo bản vẽ (docs/DRAW_ROADMAP.md mục 3) ---
    drawSchema: () => request("GET", "/draw/schema"),
    drawImport: (file, options = {}) => {
        const form = new FormData();
        form.append("file", file);
        form.append("options", JSON.stringify(options));
        return request("POST", "/draw/import", form);
    },
    drawTask: (task) => request("GET", `/draw/tasks/${task}`),
    drawTaskCancel: (task) => request("POST", `/draw/tasks/${task}/cancel`),
    drawTaskDrop: (task) => request("DELETE", `/draw/tasks/${task}`),
    drawPreview: (task, tol = 0.3) => request("GET", `/draw/tasks/${task}/preview?tol=${tol}`),
    drawGcode: (payload) => request("POST", "/draw/gcode", payload),
    drawDraftCreate: (payload) => request("POST", "/draw/drafts", payload),
    drawDrafts: () => request("GET", "/draw/drafts"),
    drawDraftGcode: (id, file) => request("GET", `/draw/drafts/${id}/gcode/${file}`, null, { text: true }),
    drawDraftPreview: (id) => request("GET", `/draw/drafts/${id}/preview.svg`, null, { text: true }),
    drawDraftUpdate: (id, patch) => request("PATCH", `/draw/drafts/${id}`, patch),
    drawDraftDelete: (id) => request("DELETE", `/draw/drafts/${id}`),
    drawGcodeImport: (name, lines, workW, workH) => {
        const form = new FormData();
        form.append("file", new File([lines.join("\n") + "\n"], name, { type: "text/plain" }));
        form.append("work_w", String(workW));
        form.append("work_h", String(workH));
        return request("POST", "/draw/drafts/import-gcode", form);
    },
    drawCalibration: (payload) => request("POST", "/draw/calibration", payload),
    drawSettings: () => request("GET", "/draw/settings"),
    drawSettingsSave: (settings) => request("PUT", "/draw/settings", settings),
};
