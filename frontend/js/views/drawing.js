// views/drawing.js — Tab Tạo bản vẽ: điều phối. Luồng (docs/05_TAB_TAO_BAN_VE.md mục 4):
//   chọn tệp -> POST /draw/import (tác vụ nền, hỏi tiến trình, hủy được) -> GET preview (nét nháp)
//   -> canvas: kéo / co giãn / xoay khung ngay trên tờ giấy (không gọi mạng, công thức ở lib/paper.js)
//   -> POST /draw/gcode (debounce, chỉ lấy số liệu) -> Lưu bản thảo / Chuyển sang Điều khiển.
// Các ô thông số do ./drawing/params.js giữ; canvas do ./drawing/canvas.js; danh sách bản thảo do views/drafts.js.
// Ảnh raster: chọn tệp chỉ HIỆN ảnh (cắt, sáng / tối chạy ngay trong trình duyệt); máy chủ chỉ tạo nét khi bấm "Tạo nét"
// (MiniPC không chạy nét cho những lần chỉnh dở). SVG nhẹ nên vẫn tạo nét ngay.
// Đổi bố trí (giấy, lề, xoay, kéo khung) KHÔNG nạp lại; đổi kiểu nét / tiền xử lý / tối ưu thì phải bấm "Tạo lại nét".
import { api, ApiError } from "../core/api.js";
import { isAdmin } from "../core/auth.js";
import { MACHINE } from "../core/config.js";
import { t } from "../core/i18n.js";
import { subscribe } from "../core/state.js";
import { formatDuration } from "../lib/gcode.js";
import { plan as planLayout, fitBox, innerArea, rotatedSize } from "../lib/paper.js";
import { loadIntoControl, refreshDrafts } from "../stores/draftstore.js";
import { buildPath, createCanvas } from "./drawing/canvas.js";
import * as params from "./drawing/params.js";
import { presetValues } from "./drawing/presets.js";
import { forget as forgetImage, imageSize, prepareForUpload } from "../lib/imageprep.js";
import * as crop from "./drawing/crop.js";
import { initCustomer } from "./customer.js";
import { initTonePreview, refresh as refreshTone, setFile as showOriginal } from "./drawing/tonepreview.js";

const $ = (id) => document.getElementById(id);
// Ảnh tải từ mạng về Windows hay có đuôi .jfif (= JPEG). Backend nhận dạng bằng nội dung tệp, không tin đuôi.
const EXTENSIONS = [".svg", ".png", ".jpg", ".jpeg", ".jfif", ".jpe", ".webp", ".bmp", ".gif", ".avif"];
const ACCEPT = `${EXTENSIONS.join(",")},image/png,image/jpeg,image/webp,image/bmp,image/gif,image/avif,image/svg+xml`;
const MAX_BYTES = { svg: 20 * 1024 * 1024, raster: 40 * 1024 * 1024 };
const POLL_MS = 350;
const GCODE_DEBOUNCE_MS = 400;
// Kéo khung to / nhỏ hơn ngần này so với lúc tạo nét thì tạo lại nét: khoảng cách gạch tính theo mm,
// nếu chỉ phóng hình học thì gạch thưa ra (hoặc dày đặc lại) so với bề rộng bút.
const RETRACE_TOLERANCE = 0.12;
const RETRACE_DELAY_MS = 800;

const floor2 = (v) => Math.floor(v * 100 + 1e-9) / 100;
const round2 = (v) => Math.round(v * 100) / 100;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

const S = {
    file: null, fileName: "",
    jobId: null, taskId: null, importSeq: 0, pollTimer: 0, busy: false,
    preview: null, src: null, layers: [], source: null, importWarnings: [],
    plan: null, result: null, resultError: null, generating: false, genSeq: 0, genTimer: 0,
    savedDraft: null, savedKey: null, importDirty: false,
    importKeep: false, lastQuality: "final", applyingPreset: false, retraceTimer: 0,
    status: { key: "drawing.progress.idle", extra: "", error: false }
};

let canvas = null;
let schemaLoaded = false;

export function initDrawing() {
    const canvasEl = $("drawing-canvas");
    const stage = $("drawing-canvas-stage");
    if (!canvasEl || !stage || !$("drawing-file")) return;

    canvas = createCanvas({ canvas: canvasEl, stage, zoomLabel: $("drawing-canvas-zoom"), onBox });
    params.initParams(onParamChange);
    initTonePreview({ stageEl: $("original-image-holder") ?? $("original-image-stage"), toggleEl: $("preview-tone-toggle"), read: params.toneSettings });
    // Cắt ảnh: áp dụng = nạp lại như tệp mới (tỷ lệ ảnh đổi nên khung vừa lại phần trong lề).
    crop.initCrop({
        apply: () => {
            if (S.file && S.taskId) startImport("final", { fresh: true });        // đã tạo nét: tạo lại với vùng cắt mới
            else if (S.file) guestFrame();                                         // chưa: chỉ nhớ vùng cắt (khách: cập nhật khung)
        },
        ratio: () => { const b = params.innerBox(); return b.w > 0 && b.h > 0 ? b.w / b.h : null; }
    });
    initFile();
    initButtons();
    initCustomer({
        snapshot: () => ({ file: S.file, params: { ...params.customerSnapshot(), crop: crop.current() ?? undefined } }),
        open: openCustomerItem
    });
    loadSchemaWhenOnline();

    // Hồ sơ máy (Cài đặt) đổi Z bút -> cập nhật hai ô Z và tạo lại G-code.
    window.addEventListener("extruxy:profile-changed", () => {
        params.setPenZ(MACHINE.gcodeUpZ, MACHINE.penDownZ);
        invalidateResult();
        scheduleGcode();
    });
    window.addEventListener("extruxy:gcode-timing", (event) => {           // từ Cài đặt → tờ nhấc bút → "Dùng hàng N"
        params.setTiming(event.detail.delay, event.detail.downFeed);
        invalidateResult();
        scheduleGcode();
    });
    window.addEventListener("extruxy:language-changed", renderAll);

    refreshScene();
    renderAll();
}

/* ==================== schema ==================== */
function loadSchemaWhenOnline() {
    const unsubscribe = subscribe(async (state) => {
        if (schemaLoaded || !state.backendOnline) return;
        schemaLoaded = true;                 // chặn gọi chồng; thất bại thì mở lại ở lần sau
        try {
            params.applySchema(await api.drawSchema());
            refreshScene();
        } catch {
            schemaLoaded = false;
        }
        if (schemaLoaded) unsubscribe?.();
    });
}

/* ==================== chọn tệp ==================== */
function initFile() {
    const input = $("drawing-file");
    input.accept = ACCEPT;
    input.addEventListener("change", () => {
        const chosen = input.files?.[0];
        input.value = "";                    // cho phép chọn lại đúng tệp đó
        if (chosen) acceptFile(chosen);
    });
    const zone = document.querySelector("#panel-drawing .upload-zone");
    if (zone) {
        zone.addEventListener("dragover", (event) => { event.preventDefault(); zone.classList.add("is-drag"); });
        zone.addEventListener("dragleave", () => zone.classList.remove("is-drag"));
        zone.addEventListener("drop", (event) => {
            event.preventDefault();
            zone.classList.remove("is-drag");
            const dropped = event.dataTransfer?.files?.[0];
            if (dropped) acceptFile(dropped);
        });
    }
}

function acceptFile(file) {      // trả Promise xong khi đã biết cỡ ảnh (vùng cắt dùng được)
    const name = file.name.toLowerCase();
    // Đuôi lạ / tên bị cắt mất đuôi nhưng trình duyệt vẫn biết là ảnh (file.type) thì vẫn nhận như ảnh.
    const ext = EXTENSIONS.find((e) => name.endsWith(e))
        ?? (file.type.startsWith("image/") && file.type !== "image/svg+xml" ? ".png" : null);
    if (!ext) return void setStatus("drawing.error.bad_image", "", true);
    const limit = ext === ".svg" ? MAX_BYTES.svg : MAX_BYTES.raster;
    if (file.size > limit) return void setStatus("drawing.error.file_too_large", "", true);

    forgetImage();
    S.file = file;
    S.fileName = file.name;
    $("drawing-file-name").removeAttribute("data-i18n");
    $("drawing-file-name").textContent = `${file.name} · ${file.size < 1024 * 1024 ? (file.size / 1024).toFixed(1) + " KB" : (file.size / 1048576).toFixed(1) + " MB"}`;
    showOriginal(file);
    crop.setImage(null);
    window.dispatchEvent(new CustomEvent("extruxy:draw-file", { detail: { file } }));
    if (ext === ".svg") { startImport("final", { fresh: true }); return Promise.resolve(); }
    clearTrace();                                            // ảnh: chỉ hiện ảnh, chờ người dùng bấm "Tạo nét"
    setStatus(isAdmin() ? "drawing.progress.waitTrace" : "auth.guestPreview");
    return imageSize(file).then((size) => {
        if (S.file !== file) return;
        crop.setImage(size);
        guestFrame();
    });
}

// Khách không tạo nét được: vẫn cho thấy KHUNG ảnh trên tờ giấy (theo cỡ ảnh sau khi cắt) để chọn khổ, lề, kích thước, xoay.
async function guestFrame() {
    if (isAdmin() || !S.file || S.file.name.toLowerCase().endsWith(".svg")) return;
    const size = await imageSize(S.file);
    if (!size || S.taskId) return;
    const c = crop.current() ?? { x: 0, y: 0, w: 1, h: 1 };
    S.src = { x: 0, y: 0, w: size.width * c.w, h: size.height * c.h };
    refit();
    refreshScene();
}

// Quản lý mở một ảnh khách gửi: nạp ảnh, điền lại thông số và vùng cắt khách đã chọn (chỉ các ô an toàn); chưa tạo nét.
async function openCustomerItem(file, saved) {
    await acceptFile(file);
    params.customerRestore(saved);
    crop.restore(saved.crop);
    refreshTone();
    onParamChange("layout", "drawing-paper");                // tính lại khung theo khổ giấy khách chọn
    setStatus("drawing.progress.waitTrace");
}

// Bỏ nét / bản vẽ của tệp trước (và hủy tác vụ đang chạy) khi nạp tệp mới: không để canvas còn hình cũ.
function clearTrace() {
    clearTimeout(S.pollTimer);
    clearTimeout(S.retraceTimer);
    S.importSeq += 1;                                        // kết quả của tác vụ đang chạy (nếu có) bị bỏ
    if (S.busy && S.jobId) api.drawTaskCancel(S.jobId).catch(() => {});
    if (S.taskId) api.drawTaskDrop(S.taskId).catch(() => {});
    Object.assign(S, { taskId: null, jobId: null, busy: false, preview: null, src: null, layers: [], source: null,
                       importWarnings: [], savedDraft: null, savedKey: null, importDirty: false, importKeep: false });
    setProgress(0);
    invalidateResult();
    refreshScene();
}

/* ==================== tác vụ nền: nạp + tiến trình ==================== */
// fresh = tệp mới (khung = phần trong lề); ngược lại giữ khung hiện tại và nạp theo đúng cỡ đang vẽ.
async function startImport(quality, { fresh = false, box = null } = {}) {
    if (!S.file) return;
    // Khách chỉ xem trước ảnh trong trình duyệt (xám, sáng/tối, cắt); tạo nét là việc của quản lý.
    // Một cổng này chặn cả 4 chỗ tự tạo nét (chọn tệp, áp vùng cắt, đổi preset, kéo khung).
    if (!isAdmin()) return setStatus("auth.guestPreview");
    clearTimeout(S.pollTimer);
    clearTimeout(S.retraceTimer);
    if (!fresh && !box && S.plan?.ok) box = currentSourceBox();
    S.importKeep = !fresh && Boolean(S.plan?.ok);
    S.lastQuality = quality;
    const seq = ++S.importSeq;
    S.importDirty = false;
    S.busy = true;
    setProgress(0);
    setStatus("drawing.progress.queued");
    setButtons();
    let job;
    try {
        const frameBox = box ?? params.innerBox();
        let upload = S.file;
        const isSvg = S.file.name.toLowerCase().endsWith(".svg");
        if (!isSvg) {
            // Thu nhỏ ảnh ngay trong trình duyệt tới đúng cỡ backend cần: gửi nhẹ hơn, MiniPC khỏi giải mã ảnh lớn.
            setStatus("drawing.progress.prepare");
            upload = (await prepareForUpload(S.file, {
                box: frameBox, pen: params.penWidthMm(), override: params.maxSideOverride(), crop: crop.current()
            })).file;
            if (seq !== S.importSeq) return;
        }
        const options = params.importOptions(quality, frameBox);
        if (!isSvg) Object.assign(options.raster, crop.payload());
        job = await api.drawImport(upload, options);
    } catch (error) {
        return failImport(seq, error);
    }
    if (seq !== S.importSeq) return;
    S.jobId = job.task;
    poll(job.task, seq);
}

function poll(task, seq) {
    const tick = async () => {
        let view;
        try {
            view = await api.drawTask(task);
        } catch (error) {
            return failImport(seq, error);
        }
        if (seq !== S.importSeq) return;
        setProgress(view.progress);
        if (view.state === "done") return finishImport(view, seq);
        if (view.state === "failed") return failImport(seq, new ApiError(view.error?.code ?? "internal_error", view.error?.message, 0));
        if (view.state === "cancelled") {
            S.busy = false;
            setStatus("drawing.progress.cancelled");
            setProgress(0);
            return setButtons();
        }
        const stepKey = `drawing.progress.step.${view.step}`;
        setStatus(t(stepKey) === stepKey ? "drawing.progress.running" : stepKey);
        S.pollTimer = setTimeout(tick, POLL_MS);
    };
    tick();
}

function failImport(seq, error) {
    if (seq !== S.importSeq) return;
    S.busy = false;
    S.importKeep = false;
    setProgress(0);
    setStatus(errorKey(error), errorDetail(error), true);
    setButtons();
}

async function finishImport(view, seq) {
    let preview;
    try {
        preview = await api.drawPreview(view.task, 0.3);
    } catch (error) {
        return failImport(seq, error);
    }
    if (seq !== S.importSeq) return;
    const previous = S.taskId;
    S.taskId = view.task;
    S.source = view.source;
    S.importWarnings = view.warnings ?? [];
    S.preview = preview;
    S.layers = preview.layers.map((l) => ({ path: buildPath(l.strokes), color: l.color }));
    S.src = preview.frame ?? preview.bounds;
    S.savedDraft = null;
    S.savedKey = null;
    S.busy = false;
    if (!S.importKeep) refit();
    setProgress(1);
    const tm = view.source?.timings;                         // giây từng bước (xử lý ảnh chạy ở tiến trình riêng)
    setStatus("drawing.progress.done", tm ? ` · ${tm.total.toFixed(1)} s` : "");
    const label = $("drawing-progress-text");
    if (label) {
        label.title = tm ? Object.entries(tm).filter(([k]) => k !== "total")
            .map(([k, v]) => `${t(`drawing.progress.step.${k}`).replace("…", "")}: ${v.toFixed(1)} s`).join("\n") : "";
    }
    refreshScene();
    invalidateResult();
    scheduleGcode(0);
    scheduleRetrace();
    if (previous && previous !== view.task) api.drawTaskDrop(previous).catch(() => {});
}

/* ==================== bố trí (canvas <-> ô số) ==================== */
function paperBox() {
    const L = params.layoutInput();
    return { L, paper: { x: 0, y: 0, w: L.paperW, h: L.paperH } };
}

// Khung vừa khít phần trong lề, giữ tỷ lệ nội dung, căn giữa — khi nạp bản vẽ mới hoặc đổi giấy / lề / xoay.
function refit() {
    if (!S.src) return;
    const { L, paper } = paperBox();
    const inner = innerArea(paper, L.margin);
    if (inner.w <= 0 || inner.h <= 0) return;
    const box = fitBox(S.src, L.rotate, inner);
    params.setLayoutFields({ width: box.w, height: box.h, center: true, offsetX: 0, offsetY: 0 });
}

// Khóa tỉ lệ: đổi rộng thì cao theo (và ngược lại), luôn nằm trong phần trong lề.
function keepRatio(changed) {
    if (!S.src || !$("drawing-lock-ratio")?.checked) return;
    const { L, paper } = paperBox();
    const inner = innerArea(paper, L.margin);
    const rs = rotatedSize(S.src, L.rotate);
    if (rs.w <= 0 || rs.h <= 0 || inner.w <= 0 || inner.h <= 0) return;
    let w = L.width ?? inner.w;
    let h = L.height ?? inner.h;
    if (changed === "drawing-width") h = (w * rs.h) / rs.w;
    else w = (h * rs.w) / rs.h;
    const k = Math.min(1, inner.w / w, inner.h / h);
    params.setLayoutFields({ width: w * k, height: h * k });
}

// Cỡ ảnh đang vẽ trên giấy, theo hướng ảnh gốc (kích thước nét lúc tạo × tỉ lệ bố trí hiện tại).
function currentSourceBox() {
    return { w: S.src.w * S.plan.sx, h: S.src.h * S.plan.sy };
}

// Ảnh raster: kéo khung lệch quá RETRACE_TOLERANCE so với cỡ lúc tạo nét thì tự tạo lại nét theo cỡ mới.
function scheduleRetrace() {
    clearTimeout(S.retraceTimer);
    if (!S.file || S.source?.mode !== "raster" || S.busy || !S.plan?.ok || S.importDirty) return;
    S.retraceTimer = setTimeout(() => {
        if (S.busy || !S.plan?.ok) return;
        const off = Math.max(Math.abs(S.plan.sx - 1), Math.abs(S.plan.sy - 1));
        if (off > RETRACE_TOLERANCE) startImport(S.lastQuality);
    }, RETRACE_DELAY_MS);
}

// Chọn bộ thông số dựng sẵn: điền các ô rồi tạo lại nét nếu đã có ảnh.
function onPreset() {
    const values = presetValues($("draw-preset").value);
    if (!values) return;
    S.applyingPreset = true;
    params.setValues(values);
    S.applyingPreset = false;
    refreshTone();
    if (S.file && S.taskId) startImport("final");                                     // đã có nét: tạo lại theo preset mới
    else setStatus(S.file ? "drawing.progress.waitTrace" : "drawing.progress.stale");  // chưa tạo nét: chỉ đặt thông số
}

function onParamChange(kind, id) {
    // Ô số đang gõ dở hoặc ngoài khoảng (vd. gõ "4" trên đường tới "4000"): chờ giá trị hợp lệ, không báo lỗi chớp.
    const el = id ? $(id) : null;
    if (el?.type === "number" && (el.validity.badInput || el.validity.rangeUnderflow || el.validity.rangeOverflow)) return;
    if (kind === "import" && /^(image|style)-/.test(id ?? "")) refreshTone();
    if (kind === "import" && !S.applyingPreset && /^(image|style|palette)-/.test(id ?? "") && $("draw-preset")) {
        $("draw-preset").value = "custom";
    }
    if (kind === "import") {
        if (id?.startsWith("draw-pen-width")) refreshScene();            // bề dày nét vẽ trên canvas
        if (S.taskId) {
            S.importDirty = true;
            setStatus("drawing.progress.stale");
        }
        return setButtons();
    }
    if (kind === "gcode") {
        invalidateResult();
        return scheduleGcode();
    }
    if (["drawing-paper", "drawing-paper-width", "drawing-paper-height", "drawing-margin", "drawing-rotate"].includes(id)) {
        refit();
    } else if (id === "drawing-width" || id === "drawing-height") {
        keepRatio(id);
    } else if (id === "drawing-center" && !$("drawing-center").checked && S.plan?.ok) {
        // bỏ căn giữa: giữ nguyên vị trí hiện tại, không để khung nhảy về góc
        const { L, paper } = paperBox();
        const inner = innerArea(paper, L.margin);
        const box = S.plan.box;
        params.setLayoutFields({ offsetX: clamp(box.x - inner.x, 0, inner.w), offsetY: clamp(box.y - inner.y, 0, inner.h) });
    }
    refreshScene();
    invalidateResult();
    scheduleGcode();
    scheduleRetrace();
}

// Canvas báo khung mới (mm). rect = null chỉ để báo "xong thao tác".
function onBox(rect, { final }) {
    if (rect) {
        const { L, paper } = paperBox();
        const inner = innerArea(paper, L.margin);
        const w = floor2(rect.w);
        const h = floor2(rect.h);
        const maxX = Math.max(0, floor2(inner.w - w));
        const maxY = Math.max(0, floor2(inner.h - h));
        let ox = clamp(round2(rect.x - inner.x), 0, maxX);
        let oy = clamp(round2(rect.y - inner.y), 0, maxY);
        const centered = Math.abs(ox - (inner.w - w) / 2) < 0.05 && Math.abs(oy - (inner.h - h) / 2) < 0.05;
        if (centered) { ox = 0; oy = 0; }
        params.setLayoutFields({ width: w, height: h, offsetX: ox, offsetY: oy, center: centered });
        refreshScene();
    }
    if (final) {
        invalidateResult();
        scheduleGcode();
        renderInfo();
        scheduleRetrace();
    }
}

function refreshScene() {
    S.plan = S.src ? planLayout(S.src, params.layoutInput(), params.machineInput()) : null;
    const bad = S.plan && !S.plan.ok;
    const paper = params.paperSize();
    canvas?.setScene({
        machine: { W: MACHINE.travelX, H: MACHINE.travelY },
        paper, papers: params.papers(),
        plan: S.plan, box: bad ? S.plan.box : undefined, inner: bad ? S.plan.inner : undefined,
        error: bad ? S.plan.code : null,
        layers: S.layers, penMm: params.penWidthMm(),
        lock: Boolean($("drawing-lock-ratio")?.checked)
    });
    const empty = $("drawing-canvas-empty");
    if (empty) empty.hidden = Boolean(S.src);
    renderWarnings();
    setButtons();
}

/* ==================== G-code (chỉ để lấy số liệu; bản thật nằm trong bản thảo) ==================== */
function invalidateResult() {
    clearTimeout(S.genTimer);
    S.genSeq += 1;
    S.result = null;
    S.resultError = null;
    S.generating = false;
    const confirm = $("drawing-confirm");
    if (confirm) confirm.checked = false;
    renderInfo();
    setButtons();
}

function scheduleGcode(delay = GCODE_DEBOUNCE_MS) {
    clearTimeout(S.genTimer);
    if (!S.taskId || !S.plan?.ok) return renderInfo();
    S.generating = true;
    renderInfo();
    S.genTimer = setTimeout(generate, delay);
}

async function generate() {
    if (!S.taskId || !S.plan?.ok) return;
    const seq = ++S.genSeq;
    S.generating = true;
    renderInfo();
    let result;
    try {
        result = await api.drawGcode({
            task: S.taskId, machine: params.machinePayload(),
            layout: params.layoutPayload(), gcode: params.gcodePayload()
        });
    } catch (error) {
        if (seq !== S.genSeq) return;
        S.generating = false;
        S.result = null;
        S.resultError = error;
        renderInfo();
        renderWarnings();
        return setButtons();
    }
    if (seq !== S.genSeq) return;
    S.generating = false;
    S.result = result;
    S.resultError = null;
    renderInfo();
    renderWarnings();
    setButtons();
}

/* ==================== nút bấm ==================== */
function initButtons() {
    $("final-run-btn")?.addEventListener("click", () => startImport("final"));
    $("regenerate-gcode-btn")?.addEventListener("click", () => { invalidateResult(); generateNow(); });
    $("draw-preset")?.addEventListener("change", onPreset);
    $("drawing-cancel-btn")?.addEventListener("click", async () => {
        if (!S.jobId) return;
        try { await api.drawTaskCancel(S.jobId); } catch { /* tác vụ đã xong */ }
    });
    $("drawing-fit-btn")?.addEventListener("click", () => canvas?.resetView());
    $("drawing-rotate-btn")?.addEventListener("click", () => {
        const select = $("drawing-rotate");
        select.value = String((Number(select.value) + 90) % 360);
        select.dispatchEvent(new Event("change"));
    });
    $("drawing-confirm")?.addEventListener("change", setButtons);
    $("save-draft-btn")?.addEventListener("click", () => run(saveDraft));
    $("send-to-control-btn")?.addEventListener("click", () => run(sendToControl));
    window.addEventListener("extruxy:tone-ramp", (event) => {                     // nút nằm ở Cài đặt → Tờ thử / hiệu chỉnh
        const paper = event.detail?.paper;
        const select = $("drawing-paper");
        if (paper && select && [...select.options].some((o) => o.value === paper)) {
            select.value = paper;
            select.dispatchEvent(new Event("change"));                            // đặt khổ giấy TRƯỚC khi nạp: khung vừa lề khổ đó
            const rotate = $("drawing-rotate");
            if (rotate) { rotate.value = "0"; rotate.dispatchEvent(new Event("change")); }    // ảnh thang tông dọc như giấy
        }
        run(loadToneRamp);
    });
}

function generateNow() {
    clearTimeout(S.genTimer);
    if (!S.taskId || !S.plan?.ok) return;
    generate();
}

async function run(action) {
    try {
        await action();
    } catch (error) {
        setStatus(errorKey(error), errorDetail(error), true);
    }
    setButtons();
}

// Ảnh thử preset: tên bản thảo ghi kèm preset đang chọn để tờ in ra biết là của preset nào.
const baseName = () => {
    if (S.fileName === RAMP_NAME) {
        const preset = $("draw-preset")?.value ?? "custom";
        return `${t("drawing.toneRamp.draftName")} · ${t(`drawing.preset.${preset}`)}`;
    }
    return S.fileName.replace(/\.[^.]+$/, "") || "Bản vẽ";
};

// Ảnh thang tông (13/11/2026, gộp "thang xám" + "tờ hiệu chỉnh tông"): 16 ô xám độ đậm TONE_STEPS xếp 4 × 4, 3 ô mốc
// đen ở góc (trên phải, dưới trái, dưới phải), chữ F ở góc trên trái. Hình học GIỐNG HỆT tờ tông A6 của backend
// (calibration.tone_layers: ô 20 mm, khe 3 mm, phần đầu 24 mm, mốc 4 mm) để AI đo ảnh chụp bằng cùng công cụ.
// Vẽ ngay trong trình duyệt rồi nạp như tệp người dùng chọn; bút / kiểu tô / preset chọn ở tab này như ảnh thường.
// Ô vẽ ra đi qua đường cong tông của kiểu tô (backend styles.TONE_CURVES): đo được kết quả cuối cùng mắt thấy.
const RAMP_NAME = "thang-tong.png";
const TONE_STEPS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9];
async function loadToneRamp() {
    const K = 12, PATCH = 20, GAP = 3, TOP = 24, MARK = 4, GRID = 4;      // K điểm ảnh / mm
    const wMm = GRID * PATCH + (GRID - 1) * GAP;
    const hMm = TOP + GRID * PATCH + (GRID - 1) * GAP + 3 + MARK;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(wMm * K);
    canvas.height = Math.round(hMm * K);
    const g = canvas.getContext("2d");
    g.fillStyle = "#fff";
    g.fillRect(0, 0, canvas.width, canvas.height);
    const rect = (x, y, w, h, dark) => {
        const v = Math.round(255 * (1 - dark));
        g.fillStyle = `rgb(${v},${v},${v})`;
        g.fillRect(Math.round(x * K), Math.round(y * K), Math.round(w * K), Math.round(h * K));
    };
    TONE_STEPS.forEach((dark, i) => {
        const row = Math.floor(i / GRID), col = i % GRID;
        rect(col * (PATCH + GAP), TOP + row * (PATCH + GAP), PATCH, PATCH, dark);
    });
    for (const [x, y] of [[wMm - MARK, 0], [0, hMm - MARK], [wMm - MARK, hMm - MARK]]) rect(x, y, MARK, MARK, 1);
    const bar = 1.5;                                                        // chữ F nét 1,5 mm (đủ dày để tô được)
    rect(2, 2, bar, 20, 1);
    rect(2, 2, 12, bar, 1);
    rect(2, 11.25, 9, bar, 1);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) throw new Error("canvas");
    acceptFile(new File([blob], RAMP_NAME, { type: "image/png" }));
}

async function ensureDraft() {
    const layout = params.layoutPayload();
    const gcode = params.gcodePayload();
    const key = JSON.stringify([S.taskId, layout, gcode]);
    if (S.savedDraft && S.savedKey === key) return S.savedDraft;
    const { draft } = await api.drawDraftCreate({
        task: S.taskId, name: baseName(), machine: params.machinePayload(), layout, gcode
    });
    S.savedDraft = draft;
    S.savedKey = key;
    await refreshDrafts();
    return draft;
}

async function saveDraft() {
    if (!S.result) return;
    await ensureDraft();
    setStatus("drawing.drafts.saved");
}

async function sendToControl() {
    if (!S.result || !$("drawing-confirm")?.checked) return;
    const draft = await ensureDraft();
    await loadIntoControl(draft, draft.files[0]);
    const layers = draft.files.length;
    setStatus(layers > 1 ? "drawing.sent.layers" : "drawing.sent", layers > 1 ? ` (${layers})` : "");
    document.getElementById("tab-control")?.click();
}

/* ==================== hiển thị ==================== */
function setProgress(value) {
    const bar = $("drawing-progress-bar");
    if (bar) bar.value = Number.isFinite(value) ? value : 0;
}

function setStatus(key, extra = "", error = false) {
    S.status = { key, extra, error };
    renderStatus();
}

function renderStatus() {
    const el = $("drawing-progress-text");
    if (!el) return;
    el.removeAttribute("data-i18n");
    const text = t(S.status.key);
    el.textContent = `${text === S.status.key ? S.status.key : text}${S.status.extra}`;
    el.classList.toggle("is-error", S.status.error);
}

function errorKey(error) {
    return error instanceof ApiError ? `drawing.error.${error.code}` : "drawing.error.internal_error";
}

function errorDetail(error) {
    // bad_param: backend nêu rõ tham số nào sai -> hiện kèm cho người dùng sửa
    return error instanceof ApiError && error.code === "bad_param" && error.message ? ` — ${error.message}` : "";
}

function describe(key, fallback, count) {
    const text = t(key);
    const base = text === key ? fallback : text;
    return count > 1 ? `${base} (×${count})` : base;
}

function renderWarnings() {
    const list = $("drawing-warning-list");
    if (!list) return;
    const items = [];
    if (S.plan && !S.plan.ok) items.push({ error: true, text: describe(`drawing.error.${S.plan.code}`, S.plan.code) });
    if (S.resultError) {
        items.push({ error: true, text: describe(errorKey(S.resultError), S.resultError.code) + errorDetail(S.resultError) });
    }
    for (const w of [...S.importWarnings, ...(S.result?.warnings ?? [])]) {
        items.push({ error: false, text: describe(`drawing.warning.${w.code}`, w.code, w.count) });
    }
    if (S.importDirty) items.push({ error: false, text: t("drawing.progress.stale") });
    const nodes = items.map((item) => {
        const li = document.createElement("li");
        li.textContent = item.text;
        if (item.error) li.classList.add("is-error");
        return li;
    });
    if (!nodes.length) {
        const li = document.createElement("li");
        li.className = "muted-text";
        li.textContent = t("drawing.preview.noWarnings");
        nodes.push(li);
    }
    list.replaceChildren(...nodes);
}

function renderInfo() {
    const set = (id, text) => { const el = $(id); if (el) { el.removeAttribute("data-i18n"); el.textContent = text; } };
    const dash = "—";
    set("drawing-source-info", S.fileName || dash);

    const plan = S.plan?.ok ? S.plan : null;
    set("drawing-size-info", plan ? `${(plan.rs.w * plan.sx).toFixed(1)} × ${(plan.rs.h * plan.sy).toFixed(1)} mm` : dash);
    const strokes = S.preview?.layers.reduce((n, l) => n + l.strokes.length, 0);
    set("drawing-path-count", strokes === undefined ? dash : `${strokes} ${t("drawing.info.strokes")}`);

    const files = S.result?.files ?? [];
    const sum = (pick) => files.reduce((n, f) => n + (pick(f.stats) ?? 0), 0);
    if (S.result) {
        set("drawing-gcode-status", `${sum((s) => s.lines)} ${t("control.gcode.lines")}`);
        const b = files.reduce((acc, f) => ({
            x0: Math.min(acc.x0, f.stats.bounds.x0), y0: Math.min(acc.y0, f.stats.bounds.y0),
            x1: Math.max(acc.x1, f.stats.bounds.x1), y1: Math.max(acc.y1, f.stats.bounds.y1)
        }), { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity });
        set("drawing-bounds-info", `X ${b.x0.toFixed(1)}–${b.x1.toFixed(1)} · Y ${b.y0.toFixed(1)}–${b.y1.toFixed(1)} mm`);
        set("drawing-length-info", `${sum((s) => s.draw_mm).toFixed(0)} · ${sum((s) => s.travel_mm).toFixed(0)} mm`);
        set("drawing-lifts-info", String(sum((s) => s.pen_lifts)));
        set("drawing-eta-info", `~${formatDuration(sum((s) => s.est_seconds))}`);
        const inside = b.x0 >= -1e-6 && b.y0 >= -1e-6 && b.x1 <= MACHINE.travelX + 1e-6 && b.y1 <= MACHINE.travelY + 1e-6;
        set("drawing-in-bounds", t(inside ? "drawing.info.yes" : "drawing.info.no"));
        $("drawing-in-bounds").dataset.state = inside ? "ok" : "bad";
    } else {
        delete $("drawing-in-bounds")?.dataset.state;
        set("drawing-gcode-status", t(S.generating ? "drawing.info.generating" : "drawing.info.notGenerated"));
        for (const id of ["drawing-bounds-info", "drawing-length-info", "drawing-lifts-info", "drawing-eta-info", "drawing-in-bounds"]) set(id, dash);
    }
}

function setButtons() {
    const has = (id, disabled) => { const el = $(id); if (el) el.disabled = disabled; };
    const planOk = Boolean(S.plan?.ok);
    has("final-run-btn", !S.file || S.busy || !isAdmin());
    const traceBtn = $("final-run-btn");
    if (traceBtn) traceBtn.textContent = t(S.taskId ? "drawing.action.final" : "drawing.action.trace");    // "Tạo nét" → "Tạo lại nét"
    has("regenerate-gcode-btn", !S.taskId || S.busy || !planOk);
    has("drawing-cancel-btn", !S.busy);
    has("drawing-rotate-btn", !S.src);
    has("drawing-confirm", !S.result);
    has("save-draft-btn", !S.result);
    has("send-to-control-btn", !S.result || !$("drawing-confirm")?.checked || S.busy);
}

function renderAll() {
    renderStatus();
    renderInfo();
    renderWarnings();
    setButtons();
}
