// state.js — NƠI DUY NHẤT nhận dữ liệu từ backend. Không đụng vào DOM.
// Vòng lặp: /api/status rồi /api/log?since=..., mỗi POLL.statusMs. Xong cả hai mới notify().

import { api } from "./api.js";
import { POLL } from "./config.js";

const MAX_LOGS = 500;

export const state = {
    backendOnline: false,   // gọi được backend ở lần thăm dò gần nhất
    status: null,           // nguyên văn /api/status
    logs: [],               // tối đa MAX_LOGS dòng gần nhất (đúng thứ tự seq)
    lastLogSeq: 0,
    logResetCount: 0,       // tăng khi backend khởi động lại (seq quay về nhỏ)
    error: null,            // lỗi của lần thăm dò gần nhất, null nếu ổn
    lastPollAt: null,       // giờ trình duyệt của lần thăm dò thành công gần nhất
    lastUpdatedAt: null     // giờ trình duyệt khi backend nhận báo cáo MỚI từ máy
};

const listeners = new Set();

let polling = false;
let timerId = null;
let requestInProgress = false;
let lastBackendStamp = null;   // status.updated_at của lần trước

/* ---------- hàm tiện ích dùng chung (để các view không tự tính lại) ---------- */

export function isConnected() {
    return state.backendOnline && state.status?.connection?.connected === true;
}

// Dữ liệu cũ: backend sống nhưng máy không gửi báo cáo mới trong POLL.staleMs.
// Chỉ có nghĩa khi đang kết nối; chưa kết nối thì isConnected() đã là false.
export function isStale() {
    if (!state.backendOnline) return true;
    if (state.status?.connection?.connected !== true) return false;
    return state.lastUpdatedAt === null ||
        Date.now() - state.lastUpdatedAt > POLL.staleMs;
}

/* ---------- đăng ký nhận thay đổi ---------- */

export function subscribe(listener) {
    listeners.add(listener);
    listener(state);                 // nhận ngay trạng thái hiện tại
    return () => listeners.delete(listener);
}

function notify() {
    for (const listener of listeners) {
        try {
            listener(state);
        } catch (error) {
            console.error("State listener error:", error);
        }
    }
}

/* ---------- áp dữ liệu nhận được vào state ---------- */

function applyStatus(status) {
    const stamp = status?.updated_at ?? null;

    // updated_at đổi nghĩa là máy vừa gửi báo cáo mới.
    if (stamp !== lastBackendStamp) {
        lastBackendStamp = stamp;
        state.lastUpdatedAt = stamp === null ? null : Date.now();
    }
    state.status = status;
}

function applyLog(result) {
    const entries = Array.isArray(result?.entries) ? result.entries : [];
    const serverLastSeq = Number.isFinite(result?.last_seq)
        ? result.last_seq
        : state.lastLogSeq;

    // seq của backend nhỏ hơn mức đã nhận: backend vừa khởi động lại.
    // Xóa log cũ; lần thăm dò sau sẽ lấy lại từ đầu (since=0).
    if (serverLastSeq < state.lastLogSeq) {
        state.logs = [];
        state.lastLogSeq = 0;
        state.logResetCount += 1;
        return;
    }

    if (entries.length > 0) {
        state.logs = state.logs.concat(entries).slice(-MAX_LOGS);
    }

    const maxEntrySeq = entries.reduce(
        (max, entry) => Math.max(max, Number(entry.seq) || 0), 0
    );
    state.lastLogSeq = Math.max(state.lastLogSeq, serverLastSeq, maxEntrySeq);
}

/* ---------- vòng thăm dò ---------- */

async function pollOnce() {
    if (!polling || requestInProgress || document.hidden) return;

    requestInProgress = true;

    try {
        const status = await api.status();
        if (!polling) return;

        const logResult = await api.log(state.lastLogSeq);
        if (!polling) return;

        applyStatus(status);
        applyLog(logResult);

        state.backendOnline = true;
        state.error = null;
        state.lastPollAt = Date.now();
        notify();
    } catch (error) {
        if (!polling) return;

        // Giữ dữ liệu cũ nhưng đánh dấu offline để giao diện không coi là hiện hành.
        state.backendOnline = false;
        state.error = error;
        notify();
    } finally {
        requestInProgress = false;

        if (polling && !document.hidden) {
            timerId = window.setTimeout(pollOnce, POLL.statusMs);
        }
    }
}

function handleVisibilityChange() {
    if (document.hidden) {
        if (timerId !== null) {
            window.clearTimeout(timerId);
            timerId = null;
        }
        return;
    }

    if (polling && timerId === null && !requestInProgress) {
        pollOnce();
    }
}

export function startPolling() {
    if (polling) return;

    polling = true;
    document.addEventListener("visibilitychange", handleVisibilityChange);

    if (!document.hidden) pollOnce();
}

export function stopPolling() {
    polling = false;

    if (timerId !== null) {
        window.clearTimeout(timerId);
        timerId = null;
    }
    document.removeEventListener("visibilitychange", handleVisibilityChange);
}
