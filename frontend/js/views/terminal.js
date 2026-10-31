// views/terminal.js — CHỦ SỞ HỮU DUY NHẤT của #terminal-output và các nút an toàn.
// Quy ước đã chốt:
//  - Nội dung terminal: tiếng Anh nguyên gốc, không dùng i18n.
//  - Terminal chỉ THÊM dòng mới (theo seq), không bao giờ vẽ lại toàn bộ.
//  - Lỗi từ firmware hiện ở bảng trạng thái (dịch i18n), không phải ở đây.

import { api, ApiError } from "../core/api.js";
import { state, subscribe, isConnected, isStale } from "../core/state.js";
import { t } from "../core/i18n.js";

const MAX_LINES = 500;

// Dòng trạng thái tự tạo ở trình duyệt (backend KHÔNG ghi báo cáo trạng thái vào log).
const STATUS_ECHO = {
    enabled: true,          // false = tắt hẳn dòng trạng thái trong terminal
    intervalMs: 1000,       // tối đa 1 dòng mỗi giây
    onlyWhenChanged: false   // false = cứ đủ 1 giây là in, kể cả khi không đổi
};

const SHOW_TIME = false;   // true = hiện [hh:mm:ss] đầu mỗi dòng



// Lỗi gọi API hiển thị trong terminal (tiếng Anh, theo ApiError.code).
const API_ERRORS = {
    backend_unreachable: "Backend unreachable.",
    already_connected: "Already connected.",
    not_connected: "Not connected to the controller.",
    bad_request: "Invalid command.",
    motion_locked: "Blocked: machine is in read-only mode.",
    link_error: "Serial link error.",
    pyserial_missing: "pyserial is not installed on the backend.",
    validation_error: "Invalid input.",
    http_error: "Request failed.",
    job_running: "Blocked: a job is running. Only ? ! ~ and the stop buttons work now.",
    not_idle: "The machine must be Idle.",
    bad_gcode: "Invalid G-code.",
    empty_job: "The file has no G-code lines.",
    no_job: "No job is running.",
    stopping: "Blocked: safe stop in progress (hold/reset/pen lift). Wait for it to finish.",
    stop_superseded: "Safe stop is no longer valid (connection changed).",
    bad_host: "Blocked: request host is not allowed.",
    bad_origin: "Blocked: request came from another site.",
    too_large: "Request is too large.",
    busy: "Busy reading/writing the machine configuration. Try again in a moment.",
    device_error: "The controller rejected the command.",
    timeout: "The controller did not answer in time.",
    no_resume: "There is no stopped job to resume.",
    empty_drawing: "The file has no drawing moves.",
    file_too_large: "The file is too large.",
    wco_changed: "The work origin (Zero) changed since the job stopped.",
    not_resumable: "This job cannot be resumed safely; start it from the beginning.",
};

export function initTerminal() {
    const form = document.getElementById("terminal-form");
    const input = document.getElementById("terminal-command");
    const sendButton = document.getElementById("terminal-send-btn");
    const output = document.getElementById("terminal-output");
    const clearButton = document.getElementById("clear-terminal-btn");
    const connectionLabel = document.getElementById("terminal-connection-label");
    const jogCancelButton = document.getElementById("jog-cancel-btn");
    const pauseButton = document.getElementById("pause-btn");
    const resumeButton = document.getElementById("resume-btn");
    const resetButton = document.getElementById("reset-btn");
    const unlockButton = document.getElementById("unlock-btn");

    if (!form || !input || !sendButton || !output) {
        console.warn("Terminal: thiếu phần tử HTML cần thiết.");
        return;
    }

    let renderedSeq = 0;        // seq lớn nhất đã vẽ
    let seenResetCount = 0;     // so với state.logResetCount
    let sending = false;
    let wasOnline = null;       // null = chưa biết
    let lastEcho = { at: 0, text: "" };

    output.replaceChildren();   // bỏ chữ giữ chỗ trong HTML

    /* ---------- vẽ dòng ---------- */

    function timeLabel(ms) {
        const date = Number.isFinite(ms) ? new Date(ms) : new Date();
        return date.toLocaleTimeString("en-GB");
    }

    // kind: tx | rx | err | sys | app | status  (khớp lớp CSS term-<kind>)
    function addLine(kind, text, whenMs) {
        const line = document.createElement("div");
        line.className = `term-line term-${kind}`;
        line.textContent = SHOW_TIME ? `[${timeLabel(whenMs)}] ${text}` : text;

        // Chỉ tự cuộn xuống khi người dùng đang ở cuối; đang đọc phía trên thì giữ nguyên.
        const nearBottom =
            output.scrollHeight - output.scrollTop - output.clientHeight < 24;

        output.appendChild(line);

        while (output.childElementCount > MAX_LINES) {
            output.firstElementChild.remove();
        }

        if (nearBottom) output.scrollTop = output.scrollHeight;
    }

    function renderEntry(entry) {
        const text = String(entry.text ?? "");

        // Lớp phòng thủ: backend đã không ghi báo cáo trạng thái "<Idle|MPos:...>".
        if (text.startsWith("<")) return;

        const when = Number(entry.t) * 1000;

        if (entry.dir === "tx") {
            addLine("tx", entry.source === "realtime"
                ? `> [realtime] ${text}`
                : `> ${text}`, when);
        } else if (entry.dir === "rx") {
            const isError = /^(error:|ALARM:)/i.test(text);
            addLine(isError ? "err" : "rx", text, when);
        } else {
            addLine("sys", `# ${text}`, when);
        }
    }

    function syncLogs(snapshot) {
        // Backend khởi động lại: seq bắt đầu lại từ đầu, xóa màn hình và vẽ lại.
        if (snapshot.logResetCount !== seenResetCount) {
            seenResetCount = snapshot.logResetCount;
            renderedSeq = 0;
            output.replaceChildren();
        }

        for (const entry of snapshot.logs) {
            const seq = Number(entry.seq) || 0;
            if (seq <= renderedSeq) continue;
            renderEntry(entry);
            renderedSeq = seq;
        }
    }

    function echoStatus(snapshot) {
        if (!STATUS_ECHO.enabled) return;

        const machine = snapshot.status?.machine;
        if (!machine || !isConnected() || isStale()) return;

        const now = Date.now();
        if (now - lastEcho.at < STATUS_ECHO.intervalMs) return;

        const mpos = Array.isArray(machine.mpos)
            ? machine.mpos.map((v) => Number(v).toFixed(3)).join(",")
            : "-";
        const sub = machine.substate == null ? "" : `:${machine.substate}`;
        const wpos = Array.isArray(machine.wpos)
            ? machine.wpos.map((v) => Number(v).toFixed(3)).join(",")
            : null;
        const pins = machine.pins ? `  Pn:${machine.pins}` : "";
        const text = `${machine.state}${sub}  MPos ${mpos}` +
            `${wpos ? `  WPos ${wpos}` : ""}  F${machine.feed ?? 0}${pins}`;

        if (STATUS_ECHO.onlyWhenChanged && text === lastEcho.text) return;

        lastEcho = { at: now, text };
        addLine("status", `~ ${text}`);
    }

    function reportBackendTransition(snapshot) {
        const online = snapshot.backendOnline;

        if (online && wasOnline === false) {
            addLine("app", "Backend reachable again.");
        }
        if (!online && snapshot.error && wasOnline !== false) {
            addLine("app", "Backend unreachable. Waiting for connection...");
        }
        if (online || snapshot.error) wasOnline = online;
    }

    /* ---------- bật/tắt điều khiển ---------- */

    function updateControls(snapshot) {
        const connected = isConnected();
        const stale = isStale();
        const canSend = connected && !stale;
        const machineState = snapshot.status?.machine?.state;

        // Không khóa ô nhập khi đang chạy tác vụ: lúc đó vẫn gõ được ? ! ~ (backend
        // gửi như ký tự tức thời); dòng khác backend sẽ từ chối với mã job_running.
        input.disabled = !canSend || sending;
        sendButton.disabled = !canSend || sending;

        if (connectionLabel) {
            connectionLabel.textContent = !snapshot.backendOnline
                ? t("terminal.backendOffline")
                : !connected
                    ? t("terminal.notConnected")
                    : stale
                        ? t("terminal.statusStale")
                        : t("terminal.connected");
        }

        if (pauseButton) {
            pauseButton.disabled = !canSend || machineState !== "Run";
        }
        if (jogCancelButton) {
            jogCancelButton.disabled = !canSend || machineState !== "Jog";
        }
        if (resumeButton) {
            resumeButton.disabled = !canSend || machineState !== "Hold";
        }
        if (resetButton) {
            resetButton.disabled = !connected;
        }
        // $X không làm máy chuyển động: backend cho gửi cả khi máy thật đang khóa.
        if (unlockButton) {
            unlockButton.disabled = !canSend || machineState !== "Alarm";
        }
    }

    /* ---------- gửi lệnh ---------- */

    function describeError(error) {
        if (error instanceof ApiError) {
            // bad_gcode: máy chủ nêu rõ dòng nào, lệnh gì (tiếng Việt) -> hiện nguyên văn để sửa tệp
            if (error.code === "bad_gcode" && error.message && error.message !== error.code) {
                return `${API_ERRORS.bad_gcode} ${error.message}`;
            }
            return API_ERRORS[error.code] ?? `Request failed (${error.code}).`;
        }
        return "Request failed.";
    }

    // Trả về true nếu backend nhận lệnh. Lệnh và phản hồi sẽ hiện qua log của backend.
    async function sendCommand(line) {
        if (!isConnected()) {
            addLine("app", "Not connected to the controller.");
            return false;
        }
        if (isStale()) {
            addLine("app", "No fresh data from the controller. Command not sent.");
            return false;
        }

        sending = true;
        updateControls(state);

        try {
            await api.command(line);
            return true;
        } catch (error) {
            addLine("app", describeError(error));
            return false;
        } finally {
            sending = false;
            updateControls(state);
        }
    }

    async function sendRealtime(action) {
        try {
            await api.realtime(action);
        } catch (error) {
            addLine("app", describeError(error));
        }
    }

    /* ---------- sự kiện ---------- */

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const line = input.value.trim();
        if (!line) return;

        if (await sendCommand(line)) input.value = "";
        input.focus();    // ô nhập bị khóa lúc gửi nên phải trả lại tiêu điểm
    });

    // Nút Xóa chỉ xóa phần hiển thị; log ở backend không đổi.
    clearButton?.addEventListener("click", () => {
        renderedSeq = state.lastLogSeq;
        output.replaceChildren();
    });

    pauseButton?.addEventListener("click", () => sendRealtime("hold"));
    resumeButton?.addEventListener("click", () => sendRealtime("resume"));
    jogCancelButton?.addEventListener("click", () => sendRealtime("jog_cancel"));
    // ĐOẠN CODE MỚI: TÍCH HỢP BẢNG THÔNG BÁO KÍNH
const resetBtn = document.getElementById("reset-btn");
const customModal = document.getElementById("custom-reset-modal");
const modalCancelBtn = document.getElementById("modal-cancel-btn");
const modalConfirmBtn = document.getElementById("modal-confirm-btn");

if (resetBtn && customModal) {
    // Hiện bảng thông báo khi bấm Reset
    resetBtn.addEventListener("click", () => {
        customModal.removeAttribute("hidden");
    });

    // Ẩn bảng khi bấm Hủy
    modalCancelBtn.addEventListener("click", () => {
        customModal.setAttribute("hidden", "");
    });

    // Gửi lệnh Reset khi bấm Đồng ý
    modalConfirmBtn.addEventListener("click", async () => {
        customModal.setAttribute("hidden", "");
        try {
            await api.realtime("reset");
        } catch (error) {
            console.error("Lỗi khi gửi lệnh Reset:", error);
        }
    });
}

    unlockButton?.addEventListener("click", () => sendCommand("$X"));

    // Thông báo từ view khác (ví dụ control.js khi gọi API lỗi).
    window.addEventListener("extruxy:message", (event) => {
    const { error, text } = event.detail ?? {};
    addLine("app", error ? describeError(error) : String(text ?? ""));
    });

    subscribe((snapshot) => {
        syncLogs(snapshot);
        reportBackendTransition(snapshot);
        echoStatus(snapshot);
        updateControls(snapshot);
    });
}
