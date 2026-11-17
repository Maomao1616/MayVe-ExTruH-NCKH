// views/drawing/subject.js — khoanh vùng chủ thể trên ảnh gốc (elip / chữ nhật). Ngoài vùng bản vẽ nhạt đi (backend
// tone.apply_subject), chủ thể nổi. Cùng cách kéo thả với crop.js: kéo trong ảnh để vẽ vùng mới, kéo khung để dời, kéo góc /
// cạnh để co giãn. Vùng là tỷ lệ 0..1 của ảnh GỐC (như vùng cắt), nên đổi vùng cắt không làm lệch chủ thể.
// Chủ ghi của #subject-overlay, #subject-panel, #subject-shape, #subject-edit-btn. Hàm thuần: lib/subject.js.
import { boxFromDrag, clampRegion, DEFAULT_REGION, payloadOf } from "../../lib/subject.js";

const $ = (id) => document.getElementById(id);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

let shape = "none";                  // hình đã áp dụng
let applied = null;                  // vùng đã áp dụng (null = chưa có)
let draft = null;                    // vùng đang sửa
let outside = 0.5;                   // độ đậm giữ lại ngoài vùng
let natural = false;                 // có ảnh raster để khoanh
let onApply = () => {};
let drag = null;

export function initSubject({ apply }) {
    onApply = apply;
    const overlay = $("subject-overlay");
    if (!overlay) return;
    $("subject-shape")?.addEventListener("change", onShapeChange);
    $("subject-edit-btn")?.addEventListener("click", () => startEdit(applied ?? DEFAULT_REGION));
    $("subject-reset-btn")?.addEventListener("click", clearRegion);
    $("subject-cancel-btn")?.addEventListener("click", cancelEdit);
    $("subject-apply-btn")?.addEventListener("click", applyDraft);
    $("subject-outside")?.addEventListener("input", () => {
        outside = clamp(Number($("subject-outside").value) / 100, 0, 1);
        render();
    });
    overlay.addEventListener("pointerdown", onDown);
    overlay.addEventListener("pointermove", onMove);
    overlay.addEventListener("pointerup", onUp);
    overlay.addEventListener("pointercancel", onUp);
    window.addEventListener("keydown", (event) => { if (event.key === "Escape" && draft) cancelEdit(); });
    window.addEventListener("extruxy:crop-edit", () => { if (draft) cancelEdit(); });    // không sửa hai khung cùng lúc
    render();
}

// Ảnh mới: bỏ vùng cũ. ok = có ảnh raster (SVG không khoanh).
export function setImage(ok) {
    natural = Boolean(ok);
    shape = "none";
    applied = null;
    draft = null;
    render();
}

// Tham số gửi kèm nhóm `raster` ({} nếu không khoanh).
export function payload() {
    return natural ? payloadOf(shape, applied, outside) : {};
}

/* ---------- sửa vùng ---------- */

function onShapeChange() {
    const value = $("subject-shape").value;
    if (!natural) { $("subject-shape").value = "none"; return; }
    if (value === "none") { clearRegion(); return; }
    shape = value;                                   // đổi elip ↔ chữ nhật giữ nguyên vùng đã chọn
    if (applied && !draft) { render(); onApply(); return; }
    startEdit(draft ?? DEFAULT_REGION);
}

function startEdit(region) {
    if (!natural) return;
    if ($("subject-shape").value === "none") { shape = "ellipse"; $("subject-shape").value = "ellipse"; }
    window.dispatchEvent(new Event("extruxy:subject-edit"));
    draft = clampRegion(region);
    render();
}

function cancelEdit() {
    draft = null;
    if (!applied) shape = "none";                    // chưa từng áp dụng: bỏ hẳn
    render();
}

function applyDraft() {
    if (!draft) return;
    applied = draft;
    draft = null;
    render();
    onApply();
}

function clearRegion() {
    const had = Boolean(applied);
    shape = "none";
    applied = null;
    draft = null;
    render();
    if (had) onApply();
}

/* ---------- kéo thả ---------- */

function pointOf(event) {
    const box = $("subject-overlay").getBoundingClientRect();
    return {
        x: clamp((event.clientX - box.left) / Math.max(1, box.width), 0, 1),
        y: clamp((event.clientY - box.top) / Math.max(1, box.height), 0, 1)
    };
}

function onDown(event) {
    if (!draft || event.button > 0) return;
    event.preventDefault();
    const p = pointOf(event);
    const handle = event.target.closest?.("[data-handle]")?.dataset.handle;
    const inside = p.x >= draft.x && p.x <= draft.x + draft.w && p.y >= draft.y && p.y <= draft.y + draft.h;
    drag = { mode: handle ?? (inside ? "move" : "new"), start: { ...draft }, p0: p, id: event.pointerId };
    try { $("subject-overlay").setPointerCapture(event.pointerId); } catch { /* con trỏ đã nhả */ }
}

function onMove(event) {
    if (!drag || event.pointerId !== drag.id) return;
    const p = pointOf(event);
    const s = drag.start;
    const { mode } = drag;
    if (mode === "move") {
        draft = clampRegion({ ...s, x: s.x + p.x - drag.p0.x, y: s.y + p.y - drag.p0.y });
    } else if (mode === "new") {
        if (Math.hypot(p.x - drag.p0.x, p.y - drag.p0.y) < 0.02) return;       // chạm nhẹ: chưa vẽ
        draft = boxFromDrag(drag.p0.x, drag.p0.y, p.x, p.y);
    } else {                                                                    // tay nắm: kéo cạnh / góc, neo phía đối diện
        const left = mode.includes("w") ? p.x : mode.includes("e") ? s.x : null;
        const right = mode.includes("e") ? p.x : mode.includes("w") ? s.x + s.w : null;
        const top = mode.includes("n") ? p.y : mode.includes("s") ? s.y : null;
        const bottom = mode.includes("s") ? p.y : mode.includes("n") ? s.y + s.h : null;
        const x0 = left ?? s.x, x1 = right ?? s.x + s.w, y0 = top ?? s.y, y1 = bottom ?? s.y + s.h;
        draft = boxFromDrag(x0, y0, x1, y1);
    }
    renderRect();
}

function onUp(event) {
    if (!drag || event.pointerId !== drag.id) return;
    drag = null;
    renderRect();
}

/* ---------- hiển thị ---------- */

function renderRect() {
    const rect = $("subject-rect");
    const shown = draft ?? applied;
    if (!rect || !shown) return;
    rect.style.left = `${shown.x * 100}%`;
    rect.style.top = `${shown.y * 100}%`;
    rect.style.width = `${shown.w * 100}%`;
    rect.style.height = `${shown.h * 100}%`;
}

function render() {
    const editing = Boolean(draft);
    const visible = natural && shape !== "none" && Boolean(draft ?? applied);
    const overlay = $("subject-overlay");
    if (overlay) {
        overlay.hidden = !visible;
        overlay.classList.toggle("is-editing", editing);
        overlay.classList.toggle("is-ellipse", shape === "ellipse");
    }
    if ($("subject-panel")) $("subject-panel").hidden = !editing;
    const select = $("subject-shape");
    if (select) { select.disabled = !natural; if (select.value !== shape) select.value = shape; }
    const edit = $("subject-edit-btn");
    if (edit) { edit.disabled = !natural || editing || !applied; edit.classList.toggle("is-active", Boolean(applied)); }
    const slider = $("subject-outside");
    if (slider && Number(slider.value) !== Math.round(outside * 100)) slider.value = String(Math.round(outside * 100));
    const label = $("subject-outside-value");
    if (label) label.textContent = `${Math.round(outside * 100)} %`;
    renderRect();
}
