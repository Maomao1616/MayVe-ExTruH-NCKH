
import { api } from "./api.js";

const POLL_INTERVAL = 400;

export const state = {
  backendOnline: false,
  status: null,
  logs: [],
  lastLogSeq: 0,
  error: null,
  lastUpdatedAt: null,
};

const listeners = new Set();

let polling = false;
let timerId = null;
let requestInProgress = false;

export function subscribe(listener) {
  listeners.add(listener);

  // Cho người đăng ký nhận ngay trạng thái hiện tại.
  listener(state);

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

async function pollOnce() {
  if (!polling || requestInProgress || document.hidden) return;

  requestInProgress = true;

  try {
    const status = await api.status();

    if (!polling) return;

    state.status = status;
    state.backendOnline = true;
    state.error = null;
    state.lastUpdatedAt = Date.now();

    // Chỉ đọc nhật ký mới sau lần đọc trước.
    const logResult = await api.log(state.lastLogSeq);

    if (!polling) return;

    const entries = Array.isArray(logResult?.entries)
      ? logResult.entries
      : [];

    if (entries.length > 0) {
      state.logs.push(...entries);
      state.logs = state.logs.slice(-500);
    }

    if (Number.isFinite(logResult?.last_seq)) {
      state.lastLogSeq = Math.max(
        state.lastLogSeq,
        logResult.last_seq
      );
    } else if (entries.length > 0) {
      state.lastLogSeq = Math.max(
        state.lastLogSeq,
        ...entries.map((entry) => Number(entry.seq) || 0)
      );
    }

    notify();
  } catch (error) {
    if (!polling) return;

    state.backendOnline = false;
    state.error = error;
    state.lastUpdatedAt = null;

    // Không xóa dữ liệu cũ, nhưng backendOnline=false
    // cho giao diện biết rằng không được coi dữ liệu đó là hiện hành.
    notify();

    console.error("Không thể cập nhật trạng thái:", error);
  } finally {
    requestInProgress = false;

    if (polling && !document.hidden) {
      timerId = window.setTimeout(pollOnce, POLL_INTERVAL);
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
  document.addEventListener(
    "visibilitychange",
    handleVisibilityChange
  );

  if (!document.hidden) {
    pollOnce();
  }
}

export function stopPolling() {
  polling = false;

  if (timerId !== null) {
    window.clearTimeout(timerId);
    timerId = null;
  }

  document.removeEventListener(
    "visibilitychange",
    handleVisibilityChange
  );
}
