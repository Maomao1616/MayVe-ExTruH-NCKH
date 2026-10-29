// views/header.js — chỉ báo ở đầu trang: backend / máy / công việc, ô trạng thái trên
// thanh tab, thanh cảnh báo và nút ↻.
// Chủ ghi DUY NHẤT của: backend-status-*, machine-state, machine-status-dot, job-status-dot,
// toolbar-machine-state, toolbar-machine-hint, toolbar-status-dot, system-alert*,
// refresh-status-btn. (Chữ của job-state vẫn do control.js ghi.)

import { t } from "../core/i18n.js";
import { subscribe, isConnected, isStale, refreshNow } from "../core/state.js";

const $ = (id) => document.getElementById(id);
const DOT_CLASSES = ["is-online", "is-offline", "is-pending"];

let dismissedAlert = null;      // nội dung cảnh báo người dùng đã bấm ×

function setDot(id, cls) {
    const dot = $(id);
    if (!dot) return;
    dot.classList.remove(...DOT_CLASSES);
    if (cls) dot.classList.add(cls);
}

function setText(id, value) {
    const element = $(id);
    if (element) element.textContent = value;
}

function jobActive(state) {
    const job = state.status?.job?.state;
    return job === "running" || job === "finishing";
}

// Ô trạng thái trên thanh tab: trạng thái máy + một dòng gợi ý quyền điều khiển.
function toolbarInfo(state) {
    if (!state.backendOnline) {
        return { text: t("header.backend.offline"), hint: t("toolbar.controlsLocked"), dot: "is-offline" };
    }
    if (!isConnected()) {
        return { text: t("common.status.disconnected"), hint: t("toolbar.controlsLocked"), dot: null };
    }
    if (isStale()) {
        return { text: t("header.machine.stale"), hint: t("toolbar.controlsLocked"), dot: "is-pending" };
    }
    const status = state.status;
    const connection = status.connection ?? {};
    const machineState = status.machine?.state ?? "—";

    let hint;
    if (status.stopping) hint = t("toolbar.hint.stopping");
    else if (jobActive(state)) hint = t("toolbar.hint.jobRunning");
    else if (connection.mode === "sim") hint = t("toolbar.hint.sim");
    else if (connection.motion_unlocked) hint = t("toolbar.hint.live");
    else hint = t("toolbar.hint.readOnly");

    const dot = machineState === "Alarm" ? "is-offline"
        : machineState === "Idle" ? "is-online" : "is-pending";
    return { text: machineState, hint, dot };
}

// Một cảnh báo quan trọng nhất ở thời điểm hiện tại, hoặc null.
function currentAlert(state) {
    if (!state.backendOnline && state.lastPollAt !== null) return t("alert.backendOffline");
    if (!state.backendOnline) return null;               // đang khởi động, chưa từng gọi được
    const connection = state.status?.connection;
    if (connection?.connected && isStale()) return t("alert.stale");
    if (!connection?.connected && connection?.lost_reason) {
        return `${t("alert.linkLost")} ${connection.lost_reason}`;
    }
    return null;
}

function renderAlert(state) {
    const box = $("system-alert");
    if (!box) return;
    const text = currentAlert(state);
    if (text !== dismissedAlert) dismissedAlert = null;   // cảnh báo mới: hiện lại
    setText("system-alert-text", text ?? "");
    box.hidden = !text || text === dismissedAlert;
}

function render(state) {
    // 1) Backend: đang kiểm tra (chưa có phản hồi nào) / sống / mất.
    let backendKey = "header.backend.offline";
    let backendDot = "is-offline";
    if (state.backendOnline) {
        backendKey = "header.backend.online";
        backendDot = "is-online";
    } else if (state.lastPollAt === null && !state.error) {
        backendKey = "header.backend.checking";
        backendDot = "is-pending";
    }
    setText("backend-status-text", t(backendKey));
    setDot("backend-status-dot", backendDot);

    // 2) Máy: chưa kết nối / dữ liệu cũ / trạng thái firmware báo.
    let machineText = "—";
    let machineDot = null;
    if (state.backendOnline) {
        if (!isConnected()) {
            machineText = t("common.status.disconnected");
        } else if (isStale()) {
            machineText = t("header.machine.stale");
            machineDot = "is-pending";
        } else {
            machineText = state.status?.machine?.state ?? "—";
            machineDot = "is-online";
        }
    }
    setText("machine-state", machineText);
    setDot("machine-status-dot", machineDot);

    // 3) Công việc: chỉ chấm màu (chữ do control.js ghi).
    const jobState = state.status?.job?.state;
    setDot("job-status-dot",
        jobActive(state) ? "is-online" : jobState === "failed" ? "is-offline" : null);

    // 4) Ô trạng thái trên thanh tab.
    const info = toolbarInfo(state);
    setText("toolbar-machine-state", info.text);
    setText("toolbar-machine-hint", info.hint);
    setDot("toolbar-status-dot", info.dot);

    // 5) Thanh cảnh báo.
    renderAlert(state);
}

export function initHeader() {
    $("dismiss-alert-btn")?.addEventListener("click", () => {
        dismissedAlert = $("system-alert-text")?.textContent || null;
        const box = $("system-alert");
        if (box) box.hidden = true;
    });

    const refresh = $("refresh-status-btn");
    refresh?.addEventListener("click", async () => {
        refresh.classList.add("is-spinning");
        refresh.disabled = true;
        try {
            await refreshNow();
        } finally {
            // giữ vòng quay một nhịp ngắn để người dùng thấy đã bấm
            setTimeout(() => {
                refresh.classList.remove("is-spinning");
                refresh.disabled = false;
            }, 400);
        }
    });

    subscribe(render);
}
