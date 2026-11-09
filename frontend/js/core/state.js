// state.js — NƠI DUY NHẤT nhận dữ liệu từ backend. Không đụng vào DOM.
// Cách chính: luồng SSE /api/events (backend đẩy trạng thái ~10 lần/giây + nhật ký khi có), một kết nối cho cả hai.
// Dự phòng (tự quay về khi SSE hỏng / chưa nối được / trình duyệt không hỗ trợ): hỏi lặp /api/status mỗi POLL.statusMs
// và /api/log?since=... mỗi POLL.logMs. Nhật ký lấy theo seq nên hỏi thưa hay nối lại đều không mất, không lặp dòng nào.

import { api } from "./api.js";
import { isAdmin } from "./auth.js";
import { POLL } from "./config.js";

const MAX_LOGS = 500;
// SSE coi là "khỏe" nếu trong chừng này mili giây có ít nhất một sự kiện (backend gửi lại trạng thái mỗi ~2 giây dù máy đứng yên).
const SSE_HEALTHY_MS = 5000;
const SSE_CHECK_MS = 1000;           // SSE khỏe: vòng hỏi lặp chỉ kiểm tra lại mỗi chừng này, không gọi mạng
const SSE_RETRY_MS = 3000;
// Tab bị ẩn thì ngừng thăm dò, nhưng vẫn báo "trang còn mở" để bản đóng gói không tự tắt server (backend/app/idle.py).
const HIDDEN_PING_MS = 30000;

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
let pingId = null;
let lastBackendStamp = null;   // status.updated_at của lần trước
let lastLogAt = 0;             // giờ trình duyệt của lần lấy /api/log gần nhất
let logNow = false;            // refreshNow(): lấy nhật ký ngay, không chờ tới lượt
let forcePoll = false;         // refreshNow(): hỏi thẳng một lần dù SSE đang khỏe
let sse = null;                // EventSource đang mở
let sseLastEventAt = 0;
let sseFailures = 0;
let sseRetryId = null;

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

// "FluidNC v4.1.1 (esp32-wifi)" lấy từ banner `Grbl 4.1 [FluidNC ...]` hoặc dòng `[VER:...]`
// của lệnh $I. Chưa có thì trả null.
export function firmwareLabel() {
    const banner = state.status?.banner;
    if (!banner) return null;
    const match = banner.match(/FluidNC\s+v[\w.-]+(?:\s*\([^)]*\))?/i);
    return match ? match[0] : banner;
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

/* ---------- luồng SSE ---------- */

const sseHealthy = () => sse !== null && Date.now() - sseLastEventAt < SSE_HEALTHY_MS;

function closeSse() {
    clearTimeout(sseRetryId);
    sseRetryId = null;
    if (sse) { sse.close(); sse = null; }
}

function startSse() {
    if (typeof EventSource === "undefined" || sse || !polling || document.hidden) return;
    const source = new EventSource(api.eventsUrl(state.lastLogSeq));
    sse = source;
    const alive = () => { sseLastEventAt = Date.now(); sseFailures = 0; };
    source.addEventListener("status", (event) => {
        let status;
        try { status = JSON.parse(event.data); } catch { return; }
        alive();
        applyStatus(status);
        state.backendOnline = true;
        state.error = null;
        state.lastPollAt = Date.now();
        notify();
    });
    source.addEventListener("log", (event) => {
        let result;
        try { result = JSON.parse(event.data); } catch { return; }
        alive();
        const before = state.logResetCount;
        applyLog(result);
        notify();
        // Backend khởi động lại: seq quay về nhỏ. Nối lại từ đầu (since=0) để lấy lại toàn bộ nhật ký mới.
        if (state.logResetCount !== before) { closeSse(); startSse(); }
    });
    // Lỗi / mất kết nối: tự đóng và nối lại sau vài giây (nối lại bằng since mới, không lặp dòng); trong lúc đó hỏi lặp lo.
    source.onerror = () => {
        if (sse !== source) return;
        closeSse();
        sseFailures += 1;
        sseRetryId = window.setTimeout(startSse, Math.min(SSE_RETRY_MS * sseFailures, 15000));
    };
}

/* ---------- vòng thăm dò (dự phòng khi SSE không khỏe) ---------- */

async function pollOnce() {
    if (!polling || requestInProgress || document.hidden) return;

    // SSE đang đẩy dữ liệu: không gọi mạng, chỉ kiểm tra lại sau ít lâu (SSE im thì lần kiểm tra sau sẽ hỏi lặp).
    if (sseHealthy() && !forcePoll) {
        timerId = window.setTimeout(pollOnce, SSE_CHECK_MS);
        return;
    }
    forcePoll = false;

    requestInProgress = true;

    try {
        const status = await api.status();
        if (!polling) return;

        let logResult = null;
        // Terminal chỉ dành cho quản lý: khách gọi /api/log sẽ bị 401 và tưởng backend hỏng.
        if (isAdmin() && (logNow || Date.now() - lastLogAt >= POLL.logMs)) {
            logResult = await api.log(state.lastLogSeq);
            if (!polling) return;
            lastLogAt = Date.now();
            logNow = false;
        }

        applyStatus(status);
        if (logResult) applyLog(logResult);

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
        closeSse();                       // tab ẩn: không giữ luồng (bản đóng gói còn tự tắt khi không còn trang)
        if (timerId !== null) {
            window.clearTimeout(timerId);
            timerId = null;
        }
        if (polling && pingId === null) {
            pingId = window.setInterval(() => api.health().catch(() => {}), HIDDEN_PING_MS);
        }
        return;
    }
    stopPing();
    startSse();

    if (polling && timerId === null && !requestInProgress) {
        pollOnce();
    }
}

function stopPing() {
    if (pingId !== null) {
        window.clearInterval(pingId);
        pingId = null;
    }
}

export function startPolling() {
    if (polling) return;

    polling = true;
    document.addEventListener("visibilitychange", handleVisibilityChange);

    if (document.hidden) handleVisibilityChange();   // mở trang ở tab nền: chỉ báo "còn mở"
    else {
        startSse();                                  // hỏi lặp một lần ngay cho nhanh có hình, SSE nối xong thì nó nghỉ
        pollOnce();
    }
}

// Đổi nhịp cập nhật terminal (Cài đặt → Hoạt động). Tọa độ / trạng thái vẫn theo POLL.statusMs.
export function setPollInterval(ms) {
    const value = Number(ms);
    if (Number.isFinite(value) && value >= 100) POLL.logMs = value;
}

// Hỏi backend ngay (nút ↻). Trả Promise xong khi lần hỏi đó kết thúc.
export async function refreshNow() {
    if (!polling || requestInProgress) return;
    logNow = true;
    forcePoll = true;
    if (timerId !== null) {
        window.clearTimeout(timerId);
        timerId = null;
    }
    await pollOnce();
}

export function stopPolling() {
    polling = false;
    stopPing();
    closeSse();

    if (timerId !== null) {
        window.clearTimeout(timerId);
        timerId = null;
    }
    document.removeEventListener("visibilitychange", handleVisibilityChange);
}
