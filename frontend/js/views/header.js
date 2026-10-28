// views/header.js — chỉ báo ở đầu trang: backend / máy / công việc.
// Chủ ghi DUY NHẤT của: backend-status-*, machine-state, machine-status-dot, job-status-dot.
// (Chữ của job-state vẫn do control.js ghi.) Chỉ đọc từ state.js, không gọi mạng.

import { t } from "../i18n.js";
import { subscribe, isConnected, isStale } from "../state.js";

const $ = (id) => document.getElementById(id);
const DOT_CLASSES = ["is-online", "is-offline", "is-pending"];

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
        jobState === "running" || jobState === "finishing" ? "is-online"
            : jobState === "failed" ? "is-offline" : null);
}

export function initHeader() {
    subscribe(render);
}
