// views/drafts.js — danh sách bản thảo ở HAI nơi (cùng dữ liệu từ stores/draftstore.js):
//   · tab Tạo bản vẽ: #drawing-draft-list
//   · tab Điều khiển, Hàng đợi công việc: #jobs-table-body (+ nút làm mới)
// và hộp thoại xem ảnh nháp (#custom-draft-modal). Mỗi phần tử HTML chỉ có một chủ ghi: file này.
import { ApiError } from "../core/api.js";
import { t } from "../core/i18n.js";
import { draftTotals, formatWhen, summaryLine } from "../lib/drafts.js";
import { bringToTop, drafts, loadIntoControl, pinDraft, refreshDrafts, removeDraft, subscribeDrafts } from "../stores/draftstore.js";

const $ = (id) => document.getElementById(id);
const message = (text) => window.dispatchEvent(new CustomEvent("extruxy:message", { detail: { text } }));
const REFRESH_MS = 15000;           // làm mới định kỳ (bản thảo có thể được tạo từ máy khác)

let armedDelete = null;             // id bản đang chờ bấm Xóa lần hai
let armedTimer = 0;

export function initDrafts() {
    subscribeDrafts(render);
    window.addEventListener("extruxy:language-changed", render);
    $("draft-queue-refresh-btn")?.addEventListener("click", () => refreshDrafts());
    window.addEventListener("focus", () => refreshDrafts());
    setInterval(() => { if (!document.hidden) refreshDrafts(); }, REFRESH_MS);
    initModal();
    refreshDrafts();
}

const labels = () => ({ strokes: t("drawing.info.strokes"), lifts: t("drawing.info.liftsShort"), layers: t("drawing.info.layers") });

async function act(action) {
    try {
        await action();
    } catch (error) {
        const key = error instanceof ApiError ? `drawing.error.${error.code}` : "drawing.error.internal_error";
        message(t(key) === key ? String(error.message ?? key) : t(key));
    }
}

async function load(draft, file, goToControl) {
    await act(async () => {
        await loadIntoControl(draft, file);
        message(`${t("drawing.sent")} ${draft.name}`);
        if (goToControl) $("tab-control")?.click();
    });
}

function button(text, onClick, { title, danger = false } = {}) {
    const el = document.createElement("button");
    el.type = "button";
    el.textContent = text;
    if (title) el.title = title;
    if (danger) el.classList.add("danger-button");
    el.addEventListener("click", onClick);
    return el;
}

// Nút thao tác của một bản thảo (dùng cho cả danh sách ở tab vẽ và bảng Hàng đợi).
function actionsOf(draft, { goToControl }) {
    const out = [];
    out.push(button(t("drawing.drafts.open"), () => openModal(draft)));
    const files = draft.files ?? [];
    for (const file of files) {
        const text = files.length > 1 ? `${t("drawing.drafts.load")} ${file.layer}` : t("drawing.drafts.load");
        out.push(button(text, () => load(draft, file, goToControl), { title: t("drawing.drafts.loadHelp") }));
    }
    out.push(button(draft.pinned ? t("drawing.drafts.unpin") : t("drawing.drafts.pin"),
        () => act(() => pinDraft(draft.id, !draft.pinned))));
    out.push(button(t("drawing.drafts.top"), () => act(() => bringToTop(draft.id)), { title: t("drawing.drafts.topHelp") }));
    const armed = armedDelete === draft.id;
    out.push(button(armed ? t("drawing.drafts.confirmDelete") : t("drawing.drafts.delete"), () => {
        if (armedDelete === draft.id) {
            armedDelete = null;
            return act(() => removeDraft(draft.id));
        }
        armedDelete = draft.id;
        clearTimeout(armedTimer);
        armedTimer = setTimeout(() => { armedDelete = null; render(); }, 3000);
        render();
    }, { danger: true }));
    return out;
}

function renderList(list) {
    const ul = $("drawing-draft-list");
    if (!ul) return;
    $("drawing-draft-empty").hidden = list.length > 0;
    ul.replaceChildren(...list.map((draft) => {
        const li = document.createElement("li");
        li.className = `draft-item${draft.pinned ? " is-pinned" : ""}`;
        const name = document.createElement("span");
        name.className = "draft-item-name";
        name.textContent = `${draft.pinned ? "★ " : ""}${draft.name}`;
        name.title = draft.id;
        const meta = document.createElement("span");
        meta.className = "draft-item-meta";
        meta.textContent = `${formatWhen(draft.created)} · ${summaryLine(draft, labels())}`;
        const actions = document.createElement("div");
        actions.className = "draft-item-actions";
        actions.append(...actionsOf(draft, { goToControl: true }));
        li.append(name, meta, actions);
        return li;
    }));
}

function renderQueue(list) {
    const body = $("jobs-table-body");
    if (!body) return;
    $("jobs-empty-state").hidden = list.length > 0;
    $("jobs-table-container").hidden = list.length === 0;
    body.replaceChildren(...list.map((draft) => {
        const tr = document.createElement("tr");
        if (draft.pinned) tr.classList.add("is-pinned");
        const cell = (content) => {
            const td = document.createElement("td");
            if (typeof content === "string") td.textContent = content; else td.append(...content);
            tr.append(td);
        };
        cell(`${draft.pinned ? "★ " : ""}${draft.name}`);
        cell(formatWhen(draft.created));
        cell(summaryLine(draft, labels()));
        const wrap = document.createElement("div");
        wrap.className = "draft-item-actions";
        wrap.append(...actionsOf(draft, { goToControl: false }));
        cell([wrap]);
        return tr;
    }));
}

function render() {
    const list = drafts.list;
    renderList(list);
    renderQueue(list);
}

/* ==================== hộp thoại xem ảnh nháp ==================== */
function initModal() {
    const modal = $("custom-draft-modal");
    if (!modal) return;
    const close = () => modal.setAttribute("hidden", "");
    $("draft-modal-close-btn")?.addEventListener("click", close);
    modal.addEventListener("click", (event) => { if (event.target === modal) close(); });
    window.addEventListener("keydown", (event) => { if (event.key === "Escape" && !modal.hidden) close(); });
}

function openModal(draft) {
    const modal = $("custom-draft-modal");
    if (!modal) return;
    $("draft-modal-title").textContent = draft.name;
    const total = draftTotals(draft);
    $("draft-modal-meta").textContent = `${formatWhen(draft.created)} · ${summaryLine(draft, labels())} · ${total.drawMm.toFixed(0)} mm`;
    const img = $("draft-modal-img");
    img.alt = draft.name;
    img.src = `/api/draw/drafts/${encodeURIComponent(draft.id)}/preview.svg`;      // ảnh minh họa do backend vẽ sẵn
    modal.removeAttribute("hidden");
}
