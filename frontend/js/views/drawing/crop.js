// views/drawing/crop.js — cắt ảnh ngay trên khung "ảnh gốc" của tab Tạo bản vẽ.
// Kéo trong ảnh để vẽ vùng mới, kéo khung để dời, kéo góc / cạnh để co giãn; khóa tỷ lệ tùy chọn.
// Vùng cắt là tỷ lệ 0..1 của ảnh gốc (đã xoay EXIF), đúng tham số crop_x/y/w/h của backend (raster_in.py).
// Chỉ cho ảnh raster (SVG không cắt). Bấm "Áp dụng" mới tính (drawing.js tạo lại nét); "Hủy" bỏ phần đang sửa.
// Chủ ghi của #crop-overlay, #crop-panel, #crop-info; ảnh bên dưới do tonepreview.js vẽ.
import { t } from "../../core/i18n.js";

const $ = (id) => document.getElementById(id);
const FULL = Object.freeze({ x: 0, y: 0, w: 1, h: 1 });
const MIN = 0.03;                    // cạnh vùng cắt nhỏ nhất (3% ảnh)
const FULL_EPS = 0.002;              // gần bằng cả ảnh: coi như không cắt

let applied = { ...FULL };           // vùng đã áp dụng (gửi backend)
let draft = null;                    // vùng đang sửa (null = không sửa)
let natural = null;                  // { w, h } điểm ảnh gốc; null = chưa có ảnh / SVG
let onApply = () => {};
let paperRatio = () => null;
let drag = null;

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const fill = (template, vars) => Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, String(v)), template);
const isFull = (r) => r.x < FULL_EPS && r.y < FULL_EPS && r.w > 1 - FULL_EPS && r.h > 1 - FULL_EPS;

export function initCrop({ apply, ratio }) {
    onApply = apply;
    paperRatio = ratio;
    const overlay = $("crop-overlay");
    if (!overlay) return;
    $("crop-edit-btn")?.addEventListener("click", startEdit);
    $("crop-cancel-btn")?.addEventListener("click", () => { draft = null; render(); });
    $("crop-reset-btn")?.addEventListener("click", () => { if (draft) { draft = fitRatio({ ...FULL }); render(); } });
    $("crop-apply-btn")?.addEventListener("click", applyDraft);
    $("crop-aspect")?.addEventListener("change", () => { if (draft) { draft = fitRatio(draft); render(); } });
    overlay.addEventListener("pointerdown", onDown);
    overlay.addEventListener("pointermove", onMove);
    overlay.addEventListener("pointerup", onUp);
    overlay.addEventListener("pointercancel", onUp);
    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && draft) { draft = null; render(); }
    });
    window.addEventListener("extruxy:language-changed", render);
    render();
}

// Ảnh mới: bỏ vùng cắt cũ. size = { width, height } (điểm ảnh) hoặc null nếu không cắt được (SVG, lỗi đọc).
export function setImage(size) {
    natural = size?.width > 1 && size?.height > 1 ? { w: size.width, h: size.height } : null;
    applied = { ...FULL };
    draft = null;
    render();
}

// Vùng đã áp dụng (tỷ lệ 0..1), null = dùng cả ảnh.
export function current() {
    return natural && !isFull(applied) ? { ...applied } : null;
}

// Tham số gửi kèm nhóm `raster` của POST /api/draw/import.
export function payload() {
    const c = current();
    if (!c) return {};
    const r = (v) => Math.round(v * 10000) / 10000;
    return { crop_x: r(c.x), crop_y: r(c.y), crop_w: r(c.w), crop_h: r(c.h) };
}

/* ---------- sửa vùng cắt ---------- */

function startEdit() {
    if (!natural) return;
    draft = { ...applied };
    render();
}

function applyDraft() {
    if (!draft) return;
    const next = isFull(draft) ? { ...FULL } : draft;
    const changed = JSON.stringify(next) !== JSON.stringify(applied);
    applied = next;
    draft = null;
    render();
    if (changed) onApply();
}

// Tỷ lệ rộng/cao trong KHÔNG GIAN TỶ LỆ 0..1 (ảnh không vuông nên khác tỷ lệ điểm ảnh), null = tự do.
function lockK() {
    const value = $("crop-aspect")?.value ?? "free";
    if (!natural || value === "free") return null;
    const r = value === "paper" ? paperRatio() : Number(value);
    return r > 0 ? (r * natural.h) / natural.w : null;
}

// Ép vùng theo tỷ lệ đang chọn: giữ tâm, lấy cỡ lớn nhất vừa trong vùng cũ (hoặc cả ảnh nếu vùng quá nhỏ).
function fitRatio(r) {
    const k = lockK();
    if (!k) return r;
    let w = r.w;
    let h = w / k;
    if (h > r.h) { h = r.h; w = h * k; }
    if (w < MIN || h < MIN) { w = Math.min(1, k); h = w / k; if (h > 1) { h = 1; w = k; } }
    const cx = r.x + r.w / 2;
    const cy = r.y + r.h / 2;
    return { x: clamp(cx - w / 2, 0, 1 - w), y: clamp(cy - h / 2, 0, 1 - h), w, h };
}

// Vùng từ một điểm neo cố định (ax, ay) tới con trỏ (px, py): dùng khi vẽ mới và khi kéo góc.
function fromAnchor(ax, ay, px, py) {
    const k = lockK();
    const sx = px >= ax ? 1 : -1;
    const sy = py >= ay ? 1 : -1;
    const maxW = sx > 0 ? 1 - ax : ax;
    const maxH = sy > 0 ? 1 - ay : ay;
    let w = Math.abs(px - ax);
    let h = Math.abs(py - ay);
    if (k) {
        if (w / k >= h) h = w / k; else w = h * k;
        const s = Math.min(1, maxW / w || 1, maxH / h || 1);
        w *= s; h *= s;
        if (w < MIN || h < MIN) { const g = Math.max(MIN / w || 1, MIN / h || 1); w *= g; h *= g; }
    } else {
        w = clamp(w, MIN, maxW);
        h = clamp(h, MIN, maxH);
    }
    w = Math.min(w, 1);
    h = Math.min(h, 1);
    return { x: clamp(sx > 0 ? ax : ax - w, 0, 1 - w), y: clamp(sy > 0 ? ay : ay - h, 0, 1 - h), w, h };
}

// Kéo một cạnh: cạnh đối diện đứng yên; khóa tỷ lệ thì chiều kia co theo, giữ nguyên tâm.
function fromEdge(start, dir, p) {
    const k = lockK();
    let { x, y, w, h } = start;
    if (dir === "e") w = clamp(p.x - x, MIN, 1 - x);
    if (dir === "w") { const right = x + w; x = clamp(p.x, 0, right - MIN); w = right - x; }
    if (dir === "s") h = clamp(p.y - y, MIN, 1 - y);
    if (dir === "n") { const bottom = y + h; y = clamp(p.y, 0, bottom - MIN); h = bottom - y; }
    if (k && (dir === "e" || dir === "w")) {
        h = w / k;
        if (h > 1) { h = 1; w = k; if (dir === "w") x = start.x + start.w - w; }
        y = clamp(start.y + start.h / 2 - h / 2, 0, 1 - h);
    } else if (k) {
        w = h * k;
        if (w > 1) { w = 1; h = 1 / k; if (dir === "n") y = start.y + start.h - h; }
        x = clamp(start.x + start.w / 2 - w / 2, 0, 1 - w);
    }
    return { x, y, w, h };
}

function pointOf(event) {
    const box = $("crop-overlay").getBoundingClientRect();
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
    // khung đang phủ cả ảnh thì "dời" vô nghĩa: kéo trong ảnh = vẽ vùng mới
    const mode = handle ?? (inside && !isFull(draft) ? "move" : "new");
    drag = { mode, start: { ...draft }, p0: p, id: event.pointerId };
    try { $("crop-overlay").setPointerCapture(event.pointerId); } catch { /* con trỏ đã nhả */ }
}

function onMove(event) {
    if (!drag || event.pointerId !== drag.id) return;
    const p = pointOf(event);
    const s = drag.start;
    const { mode } = drag;
    if (mode === "move") {
        draft = { ...s, x: clamp(s.x + p.x - drag.p0.x, 0, 1 - s.w), y: clamp(s.y + p.y - drag.p0.y, 0, 1 - s.h) };
    } else if (mode === "new") {
        if (Math.hypot(p.x - drag.p0.x, p.y - drag.p0.y) < 0.01) return;      // chạm nhẹ: chưa vẽ
        draft = fromAnchor(drag.p0.x, drag.p0.y, p.x, p.y);
    } else if (mode.length === 2) {                                           // góc: neo ở góc đối diện
        const ax = mode.includes("w") ? s.x + s.w : s.x;
        const ay = mode.includes("n") ? s.y + s.h : s.y;
        draft = fromAnchor(ax, ay, p.x, p.y);
    } else {
        draft = fromEdge(s, mode, p);
    }
    renderRect();
}

function onUp(event) {
    if (!drag || event.pointerId !== drag.id) return;
    drag = null;
    renderRect();
}

/* ---------- hiển thị ---------- */

function describe(r) {
    if (!natural || isFull(r)) return t("drawing.crop.none");
    return fill(t("drawing.crop.info"), {
        w: Math.round(natural.w * r.w), h: Math.round(natural.h * r.h),
        pw: Math.round(r.w * 100), ph: Math.round(r.h * 100)
    });
}

function renderRect() {
    const rect = $("crop-rect");
    const shown = draft ?? applied;
    if (rect) {
        rect.style.left = `${shown.x * 100}%`;
        rect.style.top = `${shown.y * 100}%`;
        rect.style.width = `${shown.w * 100}%`;
        rect.style.height = `${shown.h * 100}%`;
    }
    const info = $("crop-info");
    if (info) {
        info.removeAttribute("data-i18n");
        info.textContent = describe(shown);
    }
}

function render() {
    const editing = Boolean(draft);
    const overlay = $("crop-overlay");
    if (overlay) {
        overlay.hidden = !natural || (!editing && isFull(applied));
        overlay.classList.toggle("is-editing", editing);
    }
    if ($("crop-panel")) $("crop-panel").hidden = !editing;
    const edit = $("crop-edit-btn");
    if (edit) {
        edit.disabled = !natural || editing;
        edit.classList.toggle("is-active", !isFull(applied));
    }
    renderRect();
}
