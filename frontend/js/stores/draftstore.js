// stores/draftstore.js — danh sách bản thảo (GET /api/draw/drafts), dùng chung cho tab Tạo bản vẽ và Hàng đợi
// ở tab Điều khiển. Chỉ giữ dữ liệu + gọi api; không đụng DOM.
import { api } from "../core/api.js";
import { MACHINE } from "../core/config.js";
import { parseGcode } from "../lib/gcode.js";
import { setFile } from "./jobstore.js";

export const drafts = {
    list: [],          // backend đã sắp: ghim / ưu tiên trước, rồi mới nhất trước
    loaded: false,
    error: null        // ApiError của lần tải gần nhất, null nếu ổn
};

const listeners = new Set();

function notify() {
    for (const listener of listeners) {
        try { listener(drafts); } catch (error) { console.error("Draft store listener:", error); }
    }
}

export function subscribeDrafts(listener) {
    listeners.add(listener);
    listener(drafts);
    return () => listeners.delete(listener);
}

export async function refreshDrafts() {
    try {
        drafts.list = (await api.drawDrafts()).drafts;
        drafts.error = null;
    } catch (error) {
        drafts.error = error;
    }
    drafts.loaded = true;
    notify();
}

async function change(action) {
    try {
        await action();
    } finally {
        await refreshDrafts();
    }
}

export const pinDraft = (id, pinned) => change(() => api.drawDraftUpdate(id, { pinned }));
export const removeDraft = (id) => change(() => api.drawDraftDelete(id));

export const renameDraft = (id, name) => change(() => api.drawDraftUpdate(id, { name }));

// Kéo thả đổi thứ tự: `ids` là một nhóm (bản ghim, hoặc bản không ghim) theo thứ tự mới, lưu trong một lần gọi.
// Đổi ngay danh sách đang giữ để hai nơi hiển thị không nhảy về thứ tự cũ trong lúc chờ máy chủ.
export function reorderDrafts(ids) {
    const rank = new Map(ids.map((id, i) => [id, i]));
    const moved = drafts.list.filter((d) => rank.has(d.id)).sort((a, b) => rank.get(a.id) - rank.get(b.id));
    let k = 0;
    drafts.list = drafts.list.map((d) => (rank.has(d.id) ? moved[k++] : d));
    notify();
    return change(() => api.drawDraftReorder(ids));
}

// Nạp G-code của một lớp trong bản thảo vào tab Điều khiển (còn phải Xem trước + xác nhận mới chạy được).
export async function loadIntoControl(draft, file) {
    const text = await api.drawDraftGcode(draft.id, file.name);
    const parsed = parseGcode(text, {
        penUpZ: MACHINE.penUpZ,
        penDownZ: MACHINE.penDownZ,
        rapidFeed: MACHINE.rapidFeed ?? 6000
    });
    const layered = (draft.files?.length ?? 0) > 1 ? ` · ${file.layer}` : "";
    setFile({ name: `${draft.name}${layered}.gcode`, parsed });
    return parsed;
}
