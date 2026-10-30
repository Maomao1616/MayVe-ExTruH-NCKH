// views/dock.js — khối tiện ích bên trái, luôn có mặt ở mọi tab.
//  - Macro: nút chạy nhanh + thêm/sửa/xóa ngay tại đây (lưu qua macros.js).
//  - Tệp nhanh: các bản thảo đã GHIM (ghim ở tab Tạo bản vẽ); bấm để nạp sang tab Điều khiển.
//    Nạp xong vẫn phải Xem trước + xác nhận mới chạy được.
// Chạy macro đi qua api.js: loại gcode = tác vụ (có tiến trình ở tab Điều khiển),
// loại command = một lệnh đơn. Backend vẫn là lớp chặn cuối cùng.

import { api } from "../core/api.js";
import { t } from "../core/i18n.js";
import { subscribe, isConnected, isStale } from "../core/state.js";
import { loadMacros, saveMacro, deleteMacro, refreshMacros } from "../stores/macros.js";
import { drafts, loadIntoControl, subscribeDrafts } from "../stores/draftstore.js";

const $ = (id) => document.getElementById(id);
const OPEN_KEY = "extruxy-dock-open";

const message = (detail) =>
    window.dispatchEvent(new CustomEvent("extruxy:message", { detail }));

let lastState = null;
let editingId = null;      // null = đang thêm macro mới

export function initDock() {
    if (!$("dock")) return;
    initToggle();
    initMacroForm();
    renderMacros();
    window.addEventListener("extruxy:macros-changed", renderMacros);
    window.addEventListener("focus", refreshMacros);
    window.addEventListener("extruxy:language-changed", renderQuickFiles);
    refreshMacros();
    subscribeDrafts(renderQuickFiles);
    subscribe((state) => {
        lastState = state;
        updateMacroButtons();
    });
}

/* ---------- mở / thu ---------- */
function initToggle() {
    const panel = $("dock-panel");
    const toggle = $("dock-toggle");
    const close = $("dock-close");
    if (!panel || !toggle) return;

    const setOpen = (open) => {
        panel.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        try { localStorage.setItem(OPEN_KEY, open ? "1" : "0"); } catch { /* bỏ qua */ }
    };
    let saved = false;
    try { saved = localStorage.getItem(OPEN_KEY) === "1"; } catch { /* bỏ qua */ }
    setOpen(saved);

    toggle.addEventListener("click", () => setOpen(panel.hidden));
    close?.addEventListener("click", () => setOpen(false));
}

/* ---------- danh sách macro ---------- */
function renderMacros() {
    const list = $("dock-macro-list");
    const empty = $("macro-empty");
    if (!list) return;

    const macros = loadMacros();
    list.replaceChildren();
    if (empty) empty.hidden = macros.length > 0;

    for (const macro of macros) {
        const row = document.createElement("div");
        row.className = "dock-row";

        const run = document.createElement("button");
        run.type = "button";
        run.className = "secondary-button dock-run";
        run.textContent = macro.name;
        run.dataset.macroId = macro.id;
        run.addEventListener("click", () => runMacro(macro));

        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "icon-button dock-edit";
        edit.textContent = "✎";
        edit.title = t("dock.macro.edit");
        edit.setAttribute("aria-label", t("dock.macro.edit"));
        edit.addEventListener("click", () => openForm(macro));

        row.append(run, edit);
        list.append(row);
    }
    updateMacroButtons();
}

// Lý do chưa chạy được (khóa dịch) hoặc null nếu chạy được.
function whyNotRunnable(macro, state) {
    const status = state?.status;
    if (!isConnected() || isStale()) return "dock.why.offline";
    if (status?.connection?.motion_unlocked === false) return "dock.why.locked";

    const job = status?.job?.state;
    if (job === "running" || job === "finishing") return "dock.why.busy";

    const machineState = status?.machine?.state;
    const okStates = macro.type === "command" ? ["Idle", "Alarm"] : ["Idle"];
    if (!okStates.includes(machineState)) return "dock.why.busy";

    if (macro.needsHome && status?.homed_guess !== true) return "dock.why.needsHome";
    return null;
}

function updateMacroButtons() {
    const byId = new Map(loadMacros().map((macro) => [macro.id, macro]));
    document.querySelectorAll("#dock-macro-list [data-macro-id]").forEach((button) => {
        const macro = byId.get(button.dataset.macroId);
        if (!macro) return;
        const why = whyNotRunnable(macro, lastState);
        button.disabled = why !== null;
        button.title = why ? t(why) : macro.lines.join("\n");
    });
}

async function runMacro(macro) {
    try {
        if (macro.type === "command") {
            await api.command(macro.lines[0]);
        } else {
            await api.jobStart(macro.name, macro.lines);
        }
        message({ text: `Macro started: ${macro.name}` });
    } catch (error) {
        message({ error });
    }
}

/* ---------- form thêm / sửa ---------- */
function initMacroForm() {
    const form = $("macro-form");
    const addButton = $("macro-add-btn");
    if (!form || !addButton) return;

    addButton.addEventListener("click", () => openForm(null));
    $("macro-cancel-btn")?.addEventListener("click", closeForm);

    $("macro-delete-btn")?.addEventListener("click", async () => {
        if (!editingId) return;
        if (!window.confirm(t("dock.macro.deleteConfirm"))) return;
        if (await deleteMacro(editingId)) closeForm();
        else setError(t("dock.macro.err.storage"));
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const result = await saveMacro({
            id: editingId,
            name: $("macro-name").value,
            type: $("macro-type").value,
            lines: $("macro-lines").value,
            needsHome: $("macro-needs-home").checked
        });
        if (!result.ok) {
            const code = result.errors[0];
            setError(t(`dock.macro.err.${code}`));
            return;
        }
        closeForm();
    });
}

/* ---------- Tệp nhanh = bản thảo đã ghim ---------- */
function renderQuickFiles() {
    const list = $("dock-files-list");
    const empty = $("dock-files-empty");
    if (!list) return;
    const pinned = drafts.list.filter((draft) => draft.pinned);
    if (empty) empty.hidden = pinned.length > 0;
    list.replaceChildren();
    for (const draft of pinned) {
        const files = draft.files ?? [];
        for (const file of files) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "secondary-button dock-run";
            const color = /^(\d+)-([0-9a-f]{6})$/i.exec(file.layer ?? "");
            button.textContent = files.length > 1 ? `${draft.name} · ${color ? color[1] : file.layer}` : draft.name;
            button.title = t("dock.files.loadHelp");
            if (color) button.style.borderLeft = `6px solid #${color[2]}`;
            button.addEventListener("click", () => loadQuickFile(draft, file));
            list.append(button);
        }
    }
}

async function loadQuickFile(draft, file) {
    try {
        await loadIntoControl(draft, file);
        message({ text: `${t("drawing.sent")} ${draft.name}` });
        $("tab-control")?.click();
    } catch (error) {
        message({ error });
    }
}

function setError(text) {
    const box = $("macro-form-error");
    if (!box) return;
    box.textContent = text;
    box.hidden = !text;
}

function openForm(macro) {
    editingId = macro?.id ?? null;
    $("macro-name").value = macro?.name ?? "";
    $("macro-type").value = macro?.type ?? "gcode";
    $("macro-lines").value = macro ? macro.lines.join("\n") : "";
    $("macro-needs-home").checked = macro?.needsHome === true;
    $("macro-delete-btn").hidden = editingId === null;
    setError("");
    $("macro-form").hidden = false;
    $("macro-add-btn").hidden = true;
    $("macro-name").focus();
}

function closeForm() {
    editingId = null;
    $("macro-form").hidden = true;
    $("macro-add-btn").hidden = false;
    setError("");
}
