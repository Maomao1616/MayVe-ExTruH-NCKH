// views/drawing/params.js — các ô thông số của tab Tạo bản vẽ <-> dữ liệu gửi backend.
// Tên nhóm / tham số khớp services/drawing/spec.py; min/max lấy từ GET /api/draw/schema (applySchema).
// Chủ ghi của các ô này là file này (và drawing.js qua setLayoutFields); canvas chỉ đọc.
import { MACHINE } from "../../core/config.js";

const $ = (id) => document.getElementById(id);

// Khổ giấy dự phòng khi chưa tải được schema (backend là nguồn chính: spec.PAPERS).
const PAPERS_FALLBACK = { a4: { w: 210, h: 297 }, a5: { w: 148, h: 210 }, a6: { w: 105, h: 148 }, letter: { w: 215.9, h: 279.4 } };
const FORM_KEY = "extruxy-draw-form-v1";

// [id ô, nhóm, tên tham số, kiểu]  kiểu: num | int | bool | str | optnum | optint (trống = bỏ qua, backend tự tính)
const FIELDS = [
    ["drawing-margin", "layout", "margin_mm", "num"],
    ["drawing-fit-mode", "layout", "fit", "str"],
    ["drawing-center", "layout", "center", "bool"],
    ["drawing-flip-x", "layout", "flip_x", "bool"],
    ["drawing-flip-y", "layout", "flip_y", "bool"],
    ["drawing-reverse", "layout", "reverse", "bool"],
    ["drawing-rotate", "layout", "rotate", "int"],
    ["drawing-offset-x", "layout", "offset_x_mm", "num"],
    ["drawing-offset-y", "layout", "offset_y_mm", "num"],
    ["drawing-width", "layout", "width_mm", "optnum"],
    ["drawing-height", "layout", "height_mm", "optnum"],
    ["draw-feed", "gcode", "draw_feed", "num"],
    ["travel-feed", "gcode", "travel_feed", "num"],
    ["draw-pen-up-z", "gcode", "pen_up_z", "num"],
    ["draw-pen-down-z", "gcode", "pen_down_z", "num"],
    ["pen-delay-down", "gcode", "delay_down_s", "num"],
    ["pen-delay-up", "gcode", "delay_up_s", "num"],
    ["simplify-tolerance", "optimize", "simplify_tolerance_mm", "num"],
    ["merge-tolerance", "optimize", "merge_tolerance_mm", "num"],
    ["min-path-length", "optimize", "min_length_mm", "num"],
    ["optimize-order", "optimize", "sort", "bool"],
    ["optimize-two-opt", "optimize", "two_opt", "bool"],
    ["optimize-passes", "optimize", "passes", "int"],
    ["image-black-point", "raster", "black_point", "int"],
    ["image-white-point", "raster", "white_point", "int"],
    ["image-gamma", "raster", "gamma", "num"],
    ["image-max-side", "raster", "max_side_px", "optint"],
    ["image-clahe", "raster", "clahe", "bool"],
    ["image-denoise", "raster", "denoise", "bool"],
    ["style-kind", "style", "kind", "str"],
    ["style-outline", "style", "outline_overlay", "bool"],
    ["style-invert", "style", "invert", "bool"],
    ["style-levels", "style", "levels", "int"],
    ["style-angle", "style", "angle", "num"],
    ["style-spacing", "style", "spacing_mm", "optnum"],
    ["style-amplitude", "style", "amplitude_mm", "optnum"],
    ["palette-mode", "palette", "mode", "str"],
    ["palette-colors", "palette", "colors", "int"]
];

// Các ô thuộc từng bản vẽ cụ thể (vị trí/khung): không nhớ giữa các lần mở trang.
const PER_DRAWING = new Set(["drawing-offset-x", "drawing-offset-y", "drawing-width", "drawing-height",
    "drawing-rotate", "drawing-center", "drawing-flip-x", "drawing-flip-y", "drawing-reverse"]);

let schema = null;

function read(id, type) {
    const el = $(id);
    if (!el) return undefined;
    if (type === "bool") return el.checked;
    if (type === "str") return el.value;
    if (el.value.trim() === "") return undefined;        // trống: bỏ qua, backend dùng mặc định / tự tính
    const v = Number(el.value);
    if (!Number.isFinite(v)) return undefined;
    return type === "int" || type === "optint" ? Math.round(v) : v;
}

function group(name) {
    const out = {};
    for (const [id, g, key, type] of FIELDS) {
        if (g !== name) continue;
        const v = read(id, type);
        if (v !== undefined) out[key] = v;
    }
    return out;
}

/* ---------- đọc dữ liệu để gửi ---------- */

export function papers() {
    return schema?.papers ?? PAPERS_FALLBACK;
}

export function penWidthMm() {
    const select = $("draw-pen-width");
    if (select?.value === "custom") {
        const v = Number($("draw-pen-width-custom")?.value);
        return Number.isFinite(v) && v > 0 ? v : 0.4;
    }
    return Number(select?.value) || 0.4;
}

export function paperSize() {
    const name = $("drawing-paper")?.value ?? "a4";
    if (name === "custom") {
        const w = Number($("drawing-paper-width")?.value);
        const h = Number($("drawing-paper-height")?.value);
        return { name, w: w > 0 ? w : 210, h: h > 0 ? h : 297 };
    }
    const p = papers()[name] ?? PAPERS_FALLBACK.a4;
    return { name, w: p.w, h: p.h };
}

// Dữ liệu cho lib/paper.js (canvas). width/height null = lấp đầy phần trong lề.
export function layoutInput() {
    const p = paperSize();
    const num = (id, fallback = 0) => { const v = Number($(id)?.value); return Number.isFinite(v) ? v : fallback; };
    const opt = (id) => { const raw = $(id)?.value.trim(); const v = Number(raw); return raw && Number.isFinite(v) ? v : null; };
    return {
        paperW: p.w, paperH: p.h, paperX: 0, paperY: 0,
        margin: num("drawing-margin", 5),
        width: opt("drawing-width"), height: opt("drawing-height"),
        fit: $("drawing-fit-mode")?.value ?? "contain",
        center: $("drawing-center")?.checked ?? true,
        offsetX: num("drawing-offset-x"), offsetY: num("drawing-offset-y"),
        flipX: $("drawing-flip-x")?.checked ?? false, flipY: $("drawing-flip-y")?.checked ?? false,
        rotate: Number($("drawing-rotate")?.value) || 0
    };
}

export function machineInput() {
    return { workW: MACHINE.travelX, workH: MACHINE.travelY };
}

// Nhóm `layout` gửi backend (đúng tên spec.LAYOUT).
export function layoutPayload() {
    const out = group("layout");
    const p = paperSize();
    out.paper = p.name;
    if (p.name === "custom") {
        out.paper_width_mm = p.w;
        out.paper_height_mm = p.h;
    }
    return out;
}

export function gcodePayload() {
    return { ...group("gcode"), pen_feed: MACHINE.penFeed };
}

export function machinePayload() {
    return {
        work_w: MACHINE.travelX, work_h: MACHINE.travelY,
        z_travel: MACHINE.travelZ ?? 5, rapid_feed: MACHINE.rapidFeed ?? 6000
    };
}

export function importOptions(quality) {
    return {
        optimize: group("optimize"),
        raster: { ...group("raster"), pen_width_mm: penWidthMm(), quality },
        style: group("style"),
        palette: group("palette")
    };
}

/* ---------- ghi vào ô ---------- */

const round2 = (v) => Math.round(v * 100) / 100;
const floor2 = (v) => Math.floor(v * 100 + 1e-9) / 100;     // không bao giờ vượt phần trong lề do làm tròn

export function setLayoutFields({ width, height, offsetX, offsetY, center, rotate } = {}) {
    const set = (id, v) => { const el = $(id); if (el && v !== undefined) el.value = String(v); };
    if (width !== undefined) set("drawing-width", floor2(width));
    if (height !== undefined) set("drawing-height", floor2(height));
    if (offsetX !== undefined) set("drawing-offset-x", round2(offsetX));
    if (offsetY !== undefined) set("drawing-offset-y", round2(offsetY));
    if (center !== undefined && $("drawing-center")) $("drawing-center").checked = center;
    if (rotate !== undefined && $("drawing-rotate")) $("drawing-rotate").value = String(rotate);
    syncVisibility();
}

export function setPenZ(upZ, downZ) {
    if ($("draw-pen-up-z")) $("draw-pen-up-z").value = String(upZ);
    if ($("draw-pen-down-z")) $("draw-pen-down-z").value = String(downZ);
}

// Hiện/ẩn các ô phụ thuộc lựa chọn khác.
export function syncVisibility() {
    const center = $("drawing-center")?.checked ?? true;
    if ($("drawing-offset-row")) $("drawing-offset-row").hidden = center;
    if ($("drawing-paper-custom")) $("drawing-paper-custom").hidden = $("drawing-paper")?.value !== "custom";
    const customPen = $("draw-pen-width")?.value === "custom";
    const penLabel = $("draw-pen-width-custom")?.closest("label");
    if (penLabel) penLabel.hidden = !customPen;
    const kind = $("style-kind")?.value;
    const amp = $("style-amplitude")?.closest("label");
    if (amp) amp.hidden = kind !== "wave";                        // biên độ chỉ dùng cho kiểu Sóng
    const multi = $("palette-mode")?.value === "multi";
    const colors = $("palette-colors")?.closest("label");
    if (colors) colors.hidden = !multi;
    const lock = $("drawing-lock-ratio")?.checked;
    document.body.classList.toggle("draw-lock-ratio", Boolean(lock));
}

/* ---------- schema, nhớ giá trị ---------- */

export function applySchema(data) {
    schema = data;
    for (const [id, g, key] of FIELDS) {
        const row = data.params?.[g]?.find((p) => p.name === key);
        const el = $(id);
        if (!row || !el || el.type !== "number") continue;
        if (row.min !== null && row.min !== undefined) el.min = String(row.min);
        if (row.max !== null && row.max !== undefined) el.max = String(row.max);
    }
    // Tốc độ trần theo máy (G0 chạy ở rapid_feed): nhỏ hơn trần của schema.
    const cap = String(MACHINE.rapidFeed ?? 6000);
    for (const id of ["draw-feed", "travel-feed"]) if ($(id)) $(id).max = cap;
}

function saveForm() {
    const values = {};
    for (const [id, , , type] of FIELDS) {
        if (PER_DRAWING.has(id) || id === "draw-pen-up-z" || id === "draw-pen-down-z") continue;
        const el = $(id);
        if (el) values[id] = type === "bool" ? el.checked : el.value;
    }
    for (const id of ["drawing-paper", "drawing-paper-width", "drawing-paper-height", "draw-pen-width",
        "draw-pen-width-custom", "drawing-lock-ratio"]) {
        const el = $(id);
        if (el) values[id] = el.type === "checkbox" ? el.checked : el.value;
    }
    try { localStorage.setItem(FORM_KEY, JSON.stringify(values)); } catch { /* bị chặn */ }
}

function restoreForm() {
    let values = null;
    try { values = JSON.parse(localStorage.getItem(FORM_KEY) ?? "null"); } catch { /* hỏng */ }
    if (!values || typeof values !== "object") return;
    for (const [id, v] of Object.entries(values)) {
        const el = $(id);
        if (!el) continue;
        if (el.type === "checkbox") el.checked = Boolean(v);
        else if (el.tagName !== "SELECT" || [...el.options].some((o) => o.value === String(v))) el.value = String(v);
    }
}

// `onChange(kind, id)` kind: "layout" (chỉ bố trí lại) | "import" (phải vector hóa lại) | "gcode" (chỉ tạo lại G-code)
export function initParams(onChange) {
    restoreForm();
    setPenZ(MACHINE.penUpZ, MACHINE.penDownZ);
    syncVisibility();

    const watch = (id, kind, eventName) => {
        $(id)?.addEventListener(eventName, () => {
            syncVisibility();
            saveForm();
            onChange(kind, id);
        });
    };
    for (const [id, g, , type] of FIELDS) {
        const kind = g === "layout" ? "layout" : g === "gcode" ? "gcode" : "import";
        watch(id, kind, type === "bool" || id.endsWith("kind") || id.endsWith("mode") || id === "drawing-rotate"
            ? "change" : "input");
    }
    for (const id of ["drawing-paper", "drawing-paper-width", "drawing-paper-height"]) {
        watch(id, "layout", id === "drawing-paper" ? "change" : "input");
    }
    for (const id of ["draw-pen-width", "draw-pen-width-custom"]) watch(id, "import", id === "draw-pen-width" ? "change" : "input");
    $("drawing-lock-ratio")?.addEventListener("change", () => { syncVisibility(); saveForm(); });
}
