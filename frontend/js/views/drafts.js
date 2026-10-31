// views/drafts.js — danh sách bản thảo ở HAI nơi (cùng dữ liệu từ stores/draftstore.js):
//   · tab Tạo bản vẽ: #drawing-draft-list
//   · tab Điều khiển, Hàng đợi công việc: #jobs-table-body (+ nút làm mới)
// và hộp thoại xem ảnh nháp (#custom-draft-modal). Mỗi phần tử HTML chỉ có một chủ ghi: file này.
import { ApiError } from "../core/api.js";
import { t } from "../core/i18n.js";
import { draftTotals, formatWhen, summaryLine } from "../lib/drafts.js";
import { drafts, loadIntoControl, pinDraft, refreshDrafts, removeDraft, renameDraft, reorderDrafts, subscribeDrafts } from "../stores/draftstore.js";

const $ = (id) => document.getElementById(id);
const message = (text) => window.dispatchEvent(new CustomEvent("extruxy:message", { detail: { text } }));
const REFRESH_MS = 15000;           // làm mới định kỳ (bản thảo có thể được tạo từ máy khác)

let armedDelete = null;             // id bản đang chờ bấm Xóa lần hai
let armedTimer = 0;
let editing = null;                 // { id, where, value, original } đang đổi tên: giữ ô nhập qua các lần vẽ lại
let drag = null;                    // đang kéo đổi thứ tự: không vẽ lại danh sách giữa chừng
let renderPending = false;

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
        // Tên lớp dạng "2-31254d" = số lớp + mã màu; hiện số lớp và vệt màu để chọn đúng bút.
        const m = /^(\d+)-([0-9a-f]{6})$/i.exec(file.layer ?? "");
        const text = files.length > 1 ? `${t("drawing.drafts.load")} ${m ? `${m[1]} · #${m[2]}` : file.layer}` : t("drawing.drafts.load");
        const el = button(text, () => load(draft, file, goToControl), { title: t("drawing.drafts.loadHelp") });
        if (m) el.style.borderLeft = `6px solid #${m[2]}`;
        out.push(el);
    }
    out.push(button(draft.pinned ? t("drawing.drafts.unpin") : t("drawing.drafts.pin"),
        () => act(() => pinDraft(draft.id, !draft.pinned))));
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
        li.dataset.id = draft.id;
        li.dataset.pinned = draft.pinned ? "1" : "0";
        const name = titleOf(draft, "list");
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
        tr.dataset.id = draft.id;
        tr.dataset.pinned = draft.pinned ? "1" : "0";
        const cell = (content) => {
            const td = document.createElement("td");
            if (typeof content === "string") td.textContent = content; else td.append(...content);
            tr.append(td);
        };
        cell([titleOf(draft, "queue")]);
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
    if (drag) {                                    // đang kéo: vẽ lại sẽ làm rơi dòng đang cầm
        renderPending = true;
        return;
    }
    renderPending = false;
    const list = drafts.list;
    renderList(list);
    renderQueue(list);
    restoreEditFocus();
}

/* ==================== tên: tay kéo ☰ + tên + nút đổi tên ✎ ==================== */
// `where` = "list" (tab vẽ) | "queue" (Hàng đợi): cùng một bản hiện ở cả hai nơi, chỉ nơi bấm ✎ mới thành ô nhập.
function titleOf(draft, where) {
    const box = document.createElement("div");
    box.className = "draft-title";
    const handle = document.createElement("span");
    handle.className = "drag-handle";
    handle.textContent = "☰";
    handle.title = t("drawing.drafts.dragHelp");
    handle.setAttribute("aria-label", t("drawing.drafts.dragHelp"));
    handle.addEventListener("pointerdown", (event) => startDrag(event, handle));
    box.append(handle);

    if (editing?.id === draft.id && editing.where === where) {
        const input = document.createElement("input");
        input.className = "draft-rename-input";
        input.maxLength = 80;
        input.value = editing.value;
        input.dataset.editing = "1";
        input.addEventListener("input", () => { if (editing) editing.value = input.value; });
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") { event.preventDefault(); finishRename(true); }
            if (event.key === "Escape") { event.preventDefault(); finishRename(false); }
        });
        input.addEventListener("blur", () => finishRename(true));
        box.append(input);
        return box;
    }
    const name = document.createElement("span");
    name.className = "draft-item-name";
    name.textContent = `${draft.pinned ? "★ " : ""}${draft.name}`;
    name.title = draft.name;
    const rename = document.createElement("button");
    rename.type = "button";
    rename.className = "draft-rename-btn";
    rename.textContent = "✎";
    rename.title = t("drawing.drafts.rename");
    rename.setAttribute("aria-label", t("drawing.drafts.rename"));
    rename.addEventListener("click", () => {
        editing = { id: draft.id, where, value: draft.name, original: draft.name };
        render();
    });
    box.append(name, rename);
    return box;
}

function restoreEditFocus() {
    const input = document.querySelector("input[data-editing]");
    if (input && document.activeElement !== input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    }
}

async function finishRename(save) {
    if (!editing) return;
    const { id, value, original } = editing;
    editing = null;
    const name = value.trim();
    if (save && name && name !== original) await act(() => renameDraft(id, name));
    else render();
}

/* ==================== kéo thả đổi thứ tự (chuột và cảm ứng: Pointer Events) ==================== */
// Giữ ☰ rồi kéo: dòng TRÔI theo con trỏ (transform, không chèn lại DOM nên không khựng), các dòng cùng nhóm
// trượt ra nhường chỗ (CSS transition). Chỉ đổi chỗ trong cùng nhóm (ghim / không ghim) vì máy chủ luôn xếp bản
// ghim lên trên. Thả ra: dòng trượt vào khe rồi mới đổi thứ tự thật (một lần POST /drafts/reorder).
const EDGE_PX = 40;                                // gần mép khung cuộn thì tự cuộn
const SCROLL_MAX = 14;                             // px mỗi khung hình khi sát mép
const SETTLE_MS = 160;                             // thời gian trượt vào khe khi thả (= transition trong CSS)

function startDrag(event, handle) {
    if (event.button > 0 || editing || drag) return;
    const item = handle.closest("[data-id]");
    const container = item?.parentElement;
    if (!item || !container) return;
    event.preventDefault();
    try { handle.setPointerCapture(event.pointerId); } catch { /* con trỏ đã nhả */ }
    const group = item.dataset.pinned;
    const items = [...container.children].filter((el) => el.dataset.pinned === group);
    const scroller = container.closest(".draft-list, #jobs-table-container") ?? container;
    // Vị trí từng dòng theo tọa độ NỘI DUNG (không đổi khi khung cuộn): chụp một lần lúc bắt đầu
    const base = scroller.getBoundingClientRect().top - scroller.scrollTop;
    const slots = items.map((el) => {
        const r = el.getBoundingClientRect();
        return { top: r.top - base, height: r.height };
    });
    const from = items.indexOf(item);
    drag = {
        item, container, items, slots, from, to: from, scroller,
        startY: event.clientY, startScroll: scroller.scrollTop, y: event.clientY, frame: 0, settling: false
    };
    container.classList.add("is-sorting");
    item.classList.add("is-dragging");
    document.body.classList.add("is-reordering");

    const move = (e) => { if (drag) { drag.y = e.clientY; schedule(); } };
    const end = () => {
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", end);
        handle.removeEventListener("pointercancel", end);
        dropDrag();
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", end);
    schedule();
}

// Gộp mọi cập nhật vào một khung hình; khi đang sát mép thì tự gọi lại để cuộn đều.
function schedule() {
    if (drag && !drag.frame) drag.frame = requestAnimationFrame(frameDrag);
}

function frameDrag() {
    if (!drag || drag.settling) return;
    drag.frame = 0;
    const { item, items, slots, from, scroller } = drag;
    const box = scroller.getBoundingClientRect();
    let speed = 0;
    if (drag.y < box.top + EDGE_PX) speed = -SCROLL_MAX * (1 - Math.max(0, drag.y - box.top) / EDGE_PX);
    else if (drag.y > box.bottom - EDGE_PX) speed = SCROLL_MAX * (1 - Math.max(0, box.bottom - drag.y) / EDGE_PX);
    if (speed) scroller.scrollTop += speed;

    const dy = drag.y - drag.startY + (scroller.scrollTop - drag.startScroll);
    item.style.transform = `translateY(${dy}px)`;

    // Khe đích: số dòng cùng nhóm có tâm nằm trên tâm dòng đang kéo
    const center = slots[from].top + dy + slots[from].height / 2;
    let to = 0;
    slots.forEach((s, i) => { if (i !== from && s.top + s.height / 2 < center) to += 1; });
    if (to !== drag.to) {
        drag.to = to;
        const shift = step(slots, from);
        items.forEach((el, i) => {
            if (i === from) return;
            const offset = from < to && i > from && i <= to ? -shift : from > to && i >= to && i < from ? shift : 0;
            el.style.transform = offset ? `translateY(${offset}px)` : "";
        });
    }
    if (speed) schedule();
}

// Khoảng một dòng chiếm (cao + khe giữa hai dòng): các dòng khác trượt đúng chừng này.
function step(slots, i) {
    const s = slots[i];
    const gap = i + 1 < slots.length ? slots[i + 1].top - (s.top + s.height)
        : i > 0 ? s.top - (slots[i - 1].top + slots[i - 1].height) : 0;
    return s.height + Math.max(0, gap);
}

function dropDrag() {
    if (!drag || drag.settling) return;
    if (drag.frame) cancelAnimationFrame(drag.frame);
    drag.settling = true;
    const { item, items, slots, from, to, container } = drag;
    // Trượt dòng đang cầm vào khe đích rồi mới đổi DOM (vẽ lại theo thứ tự mới trùng đúng chỗ, không nhảy)
    const target = to > from ? slots[to].top + slots[to].height - slots[from].height : slots[to].top;
    const offset = target - slots[from].top;          // dòng nằm trong nội dung nên tự theo khung cuộn
    const current = parseFloat(/-?[\d.]+/.exec(item.style.transform)?.[0] ?? "0");
    item.classList.add("is-settling");
    item.style.transform = `translateY(${offset}px)`;
    const finish = () => {
        const order = items.map((el) => el.dataset.id);
        const [moved] = order.splice(from, 1);
        order.splice(to, 0, moved);
        for (const el of items) el.style.transform = "";
        item.classList.remove("is-dragging", "is-settling");
        container.classList.remove("is-sorting");
        document.body.classList.remove("is-reordering");
        drag = null;
        if (to !== from) act(() => reorderDrafts(order));
        else if (renderPending) render();
    };
    if (Math.abs(current - offset) < 1) finish();
    else setTimeout(finish, SETTLE_MS);
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
