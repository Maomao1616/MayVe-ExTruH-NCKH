// views/beta/index.js — Tab Beta "In trang PDF" (docs/10_TAB_BETA_PDF.md). Luồng:
//   chọn PDF -> POST /beta/pdf/upload (tải một lần, nhận mã `doc`) -> chọn trang, xem trang gốc (ảnh từ backend)
//   -> POST /beta/pdf/import (tác vụ nền, cùng cơ chế với tab Tạo bản vẽ) -> hỏi tiến trình -> xem nét sinh ra ngay tại tab này
//   -> "Mở ở Tạo bản vẽ": phát sự kiện `extruxy:beta-task`, views/drawing.js nhận bản vẽ đã nạp (bố trí giấy, G-code, bản thảo dùng lại).
// Chủ ghi của mọi phần tử #beta-*. Không import view khác. Hàm thuần: ./model.js. Gỡ tính năng: xem docs/10 mục "Cách gỡ".
import { api, ApiError } from "../../core/api.js";
import { isAdmin } from "../../core/auth.js";
import { t } from "../../core/i18n.js";
import { clampPage, FIELDS, optionsFromValues, previewDpi, stepZoom, strokesPath, summarize, ZOOMS } from "./model.js";

const $ = (id) => document.getElementById(id);
const POLL_MS = 300;
const MAX_BYTES = 40 * 1024 * 1024;
const B = { doc: null, name: "", pages: 0, sizes: [], page: 1, view: null, task: null, busy: false, seq: 0, timer: 0, zoom: 1 };

export function initBeta() {
    const panel = $("panel-beta");
    if (!panel) return;
    if (!isAdmin()) {                                           // chỉ quản lý dùng tab này (route backend cũng chỉ cho quản lý)
        $("tab-beta")?.setAttribute("hidden", "");
        panel.setAttribute("hidden", "");
        return;
    }
    $("beta-file").addEventListener("change", onFile);
    $("beta-page").addEventListener("change", () => setPage($("beta-page").value));
    $("beta-prev").addEventListener("click", () => setPage(B.page - 1));
    $("beta-next").addEventListener("click", () => setPage(B.page + 1));
    $("beta-run-btn").addEventListener("click", run);
    $("beta-cancel-btn").addEventListener("click", cancel);
    $("beta-open-btn").addEventListener("click", openInDrawing);
    $("beta-text-mode").addEventListener("change", syncVisibility);
    $("beta-images").addEventListener("change", syncVisibility);
    $("beta-image-kind").addEventListener("change", syncVisibility);
    for (const [id] of FIELDS) $(id)?.addEventListener("change", markStale);
    initZoom();
    initViewToggle();
    syncVisibility();
    render();
}

/* ---------- zoom: hai khung cuộn cùng nhau ---------- */
function sheets() {
    return [...document.querySelectorAll(".beta-sheet")];
}

// Khung đang nhìn thấy (trên điện thoại chỉ một khung hiện; khung ẩn có kích thước 0 nên không dùng để tính zoom).
function visibleSheet() {
    return sheets().find((s) => s.offsetParent !== null) ?? sheets()[0];
}

// Điện thoại: hai khung chuyển qua lại bằng nút (CSS chỉ ẩn một khung dưới 760 px); máy tính vẫn hiện cả hai.
function showView(which) {
    const box = document.querySelector(".beta-compare");
    if (!box || box.dataset.show === which) return;
    const from = visibleSheet();
    const fx = from && from.scrollWidth ? from.scrollLeft / from.scrollWidth : 0;
    const fy = from && from.scrollHeight ? from.scrollTop / from.scrollHeight : 0;
    box.dataset.show = which;
    for (const b of document.querySelectorAll("[data-beta-view]")) {
        const on = b.dataset.betaView === which;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", String(on));
    }
    const to = visibleSheet();
    if (to) {                                              // giữ nguyên chỗ đang xem khi đổi khung
        to.scrollLeft = fx * to.scrollWidth;
        to.scrollTop = fy * to.scrollHeight;
    }
}

function initViewToggle() {
    for (const b of document.querySelectorAll("[data-beta-view]")) {
        b.addEventListener("click", () => showView(b.dataset.betaView));
    }
}

function setZoom(next, anchor) {
    const a = visibleSheet();
    if (!a || next === B.zoom) return;
    // giữ nguyên điểm đang nhìn (tâm khung, hoặc vị trí con trỏ) khi đổi mức zoom
    const rect = a.getBoundingClientRect();
    const px = anchor ? anchor.x - rect.left : a.clientWidth / 2;
    const py = anchor ? anchor.y - rect.top : a.clientHeight / 2;
    const fx = (a.scrollLeft + px) / a.scrollWidth;
    const fy = (a.scrollTop + py) / a.scrollHeight;
    B.zoom = next;
    document.querySelector(".beta-compare").style.setProperty("--beta-zoom", String(next));
    $("beta-zoom-value").textContent = `${Math.round(next * 100)} %`;
    for (const s of sheets()) {
        s.scrollLeft = fx * s.scrollWidth - px;
        s.scrollTop = fy * s.scrollHeight - py;
    }
    render();                                              // ảnh trang gốc tải lại ở độ phân giải hợp với mức zoom
}

function initZoom() {
    $("beta-zoom-in").addEventListener("click", () => setZoom(stepZoom(B.zoom, 1)));
    $("beta-zoom-out").addEventListener("click", () => setZoom(stepZoom(B.zoom, -1)));
    $("beta-zoom-fit").addEventListener("click", () => setZoom(ZOOMS[0]));
    let syncing = false;
    for (const sheet of sheets()) {
        sheet.addEventListener("scroll", () => {                // khung này cuộn thì khung kia cuộn theo (cùng tỷ lệ)
            if (syncing) return;
            syncing = true;
            for (const other of sheets()) {
                if (other === sheet) continue;
                other.scrollLeft = (sheet.scrollLeft / Math.max(1, sheet.scrollWidth - sheet.clientWidth)) * (other.scrollWidth - other.clientWidth);
                other.scrollTop = (sheet.scrollTop / Math.max(1, sheet.scrollHeight - sheet.clientHeight)) * (other.scrollHeight - other.clientHeight);
            }
            syncing = false;
        });
        sheet.addEventListener("wheel", (event) => {            // Ctrl + cuộn: zoom tại con trỏ; cuộn thường để trình duyệt xử lý
            if (!event.ctrlKey) return;
            event.preventDefault();
            setZoom(stepZoom(B.zoom, event.deltaY < 0 ? 1 : -1), { x: event.clientX, y: event.clientY });
        }, { passive: false });
        let pan = null;
        sheet.addEventListener("pointerdown", (event) => {      // kéo để di chuyển
            if (event.button > 0) return;
            pan = { x: event.clientX, y: event.clientY, left: sheet.scrollLeft, top: sheet.scrollTop, id: event.pointerId };
            sheet.setPointerCapture(event.pointerId);
            sheet.classList.add("is-panning");
        });
        sheet.addEventListener("pointermove", (event) => {
            if (!pan || event.pointerId !== pan.id) return;
            sheet.scrollLeft = pan.left - (event.clientX - pan.x);
            sheet.scrollTop = pan.top - (event.clientY - pan.y);
        });
        const stop = (event) => {
            if (pan && event.pointerId === pan.id) { pan = null; sheet.classList.remove("is-panning"); }
        };
        sheet.addEventListener("pointerup", stop);
        sheet.addEventListener("pointercancel", stop);
    }
}

/* ---------- đọc ô nhập ---------- */
function values() {
    const out = {};
    for (const [id, , kind] of FIELDS) {
        const el = $(id);
        if (el) out[id] = kind === "bool" ? el.checked : el.value;
    }
    return out;
}

function syncVisibility() {
    const mode = $("beta-text-mode").value;
    $("beta-mixed-min").closest("label").hidden = mode !== "mixed";
    $("beta-font").closest("label").hidden = mode === "skeleton";               // skeleton thuần không dùng font nét đơn
    const images = $("beta-images").checked;
    $("beta-image-kind").closest("label").hidden = !images;
    $("beta-image-pen").closest("label").hidden = !images;
    const kind = $("beta-image-kind").value;
    $("beta-lineart-text").closest("label").hidden = !images || !(kind === "auto" || kind === "lineart");     // chỉ có nghĩa khi có hình vẽ nét
}

/* ---------- tệp và trang ---------- */
async function onFile() {
    const file = $("beta-file").files?.[0];
    if (!file) return;
    if (file.size > MAX_BYTES) return fail(new ApiError("file_too_large", "", 413));
    cancel();
    clearResult();
    setProgress(0, "beta.progress.uploading");
    $("beta-file-name").textContent = file.name;
    try {
        const info = await api.betaPdfUpload(file);
        B.doc = info.doc;
        B.name = info.name;
        B.pages = info.pages;
        B.sizes = info.sizes;
        B.page = 1;
    } catch (error) {
        B.doc = null;
        B.pages = 0;
        $("beta-file").value = "";
        fail(error);
        return render();
    }
    setProgress(0, "beta.progress.idle");
    showWarnings([]);
    render();
}

function setPage(value) {
    if (!B.doc) return;
    const page = clampPage(value, B.pages);
    if (page === B.page) { $("beta-page").value = String(page); return; }
    B.page = page;
    cancel();
    clearResult();
    render();
}

function render() {
    const has = Boolean(B.doc);
    $("beta-page-row").hidden = !has;
    $("beta-page").max = String(Math.max(1, B.pages));
    $("beta-page").value = String(B.page);
    $("beta-prev").disabled = !has || B.page <= 1;
    $("beta-next").disabled = !has || B.page >= B.pages;
    $("beta-run-btn").disabled = !has || B.busy;
    $("beta-cancel-btn").disabled = !B.busy;
    $("beta-open-btn").disabled = !B.view || B.busy;
    const img = $("beta-original");
    if (has) {
        const size = B.sizes[B.page - 1];
        $("beta-page-info").textContent = t("beta.info.pages").replace("{n}", String(B.pages)).replace("{w}", String(size?.w ?? "—")).replace("{h}", String(size?.h ?? "—"));
        const src = api.betaPdfPreviewUrl(B.doc, B.page, previewDpi(B.zoom));
        if (img.getAttribute("src") !== src) img.setAttribute("src", src);
        img.hidden = false;
        $("beta-result").setAttribute("viewBox", `0 0 ${size?.w ?? 210} ${size?.h ?? 297}`);
        document.querySelector(".beta-compare").style.setProperty("--beta-aspect", `${size?.w ?? 210} / ${size?.h ?? 297}`);
    } else {
        $("beta-page-info").textContent = "";
        img.hidden = true;
        img.removeAttribute("src");
    }
}

/* ---------- tạo nét ---------- */
function markStale() {
    if (B.view && !B.busy) setProgress(0, "beta.progress.stale");
}

async function run() {
    if (!B.doc || B.busy) return;
    clearTimeout(B.timer);
    const seq = ++B.seq;
    B.busy = true;
    B.view = null;
    showWarnings([]);
    $("beta-stats").hidden = true;
    setProgress(0, "beta.progress.queued");
    render();
    let job;
    try {
        job = await api.betaPdfImport(B.doc, optionsFromValues(values(), B.page));
    } catch (error) {
        return failRun(seq, error);
    }
    if (seq !== B.seq) return;
    B.task = job.task;
    poll(job.task, seq);
}

function poll(task, seq) {
    const tick = async () => {
        let view;
        try {
            view = await api.drawTask(task);
        } catch (error) {
            return failRun(seq, error);
        }
        if (seq !== B.seq) return;
        $("beta-progress-bar").value = view.progress ?? 0;
        if (view.state === "done") return done(view, seq);
        if (view.state === "failed") return failRun(seq, new ApiError(view.error?.code ?? "internal_error", view.error?.message, 0));
        if (view.state === "cancelled") {
            B.busy = false;
            setProgress(0, "beta.progress.cancelled");
            return render();
        }
        const key = `drawing.progress.step.${view.step}`;
        $("beta-progress-text").textContent = t(key) === key ? t("beta.progress.running") : t(key);
        B.timer = setTimeout(tick, POLL_MS);
    };
    tick();
}

async function done(view, seq) {
    let preview;
    try {
        preview = await api.drawPreview(view.task, 0.3);
    } catch (error) {
        return failRun(seq, error);
    }
    if (seq !== B.seq) return;
    B.view = view;
    B.busy = false;
    drawResult(view, preview);
    showStats(view.source);
    showWarnings(view.warnings ?? []);
    const total = view.source?.timings?.total;
    setProgress(1, "beta.progress.done", total ? ` · ${total.toFixed(1)} s` : "");
    showView("result");                                    // điện thoại: tạo xong thì chuyển sang xem nét
    render();
}

function failRun(seq, error) {
    if (seq !== B.seq) return;
    B.busy = false;
    fail(error);
    render();
}

function cancel() {
    clearTimeout(B.timer);
    if (B.busy && B.task) api.drawTaskCancel(B.task).catch(() => {});
    B.seq++;
    B.busy = false;
    render();
}

function openInDrawing() {
    if (!B.view) return;
    window.dispatchEvent(new CustomEvent("extruxy:beta-task", { detail: B.view }));      // views/drawing.js nhận
    $("tab-drawing")?.click();
}

/* ---------- hiển thị ---------- */
function setProgress(value, key, extra = "") {
    $("beta-progress-bar").value = value;
    $("beta-progress-text").textContent = t(key) + extra;
}

function fail(error) {
    const code = error instanceof ApiError ? error.code : "internal_error";
    const key = `drawing.error.${code}`;
    const base = t(key) === key ? (error?.message || code) : t(key);
    const detail = error instanceof ApiError && code === "bad_param" && error.message ? ` — ${error.message}` : "";
    setProgress(0, "beta.progress.failed");
    showWarnings([], `${base}${detail}`);
}

function showWarnings(list, errorText = "") {
    const ul = $("beta-warnings");
    const items = [];
    if (errorText) items.push({ error: true, text: errorText });
    for (const w of list) {
        const key = `drawing.warning.${w.code}`;
        const base = t(key) === key ? w.code : t(key);
        items.push({ error: false, text: `${base}${w.count > 1 ? ` (×${w.count})` : ""}${w.detail ? ` [${w.detail}]` : ""}` });
    }
    ul.replaceChildren(...items.map((item) => {
        const li = document.createElement("li");
        li.textContent = item.text;
        if (item.error) li.classList.add("is-error");
        return li;
    }));
}

const SVG_NS = "http://www.w3.org/2000/svg";

function drawResult(view, preview) {
    const svg = $("beta-result");
    const frame = preview.frame ?? preview.bounds;
    if (frame) svg.setAttribute("viewBox", `${frame.x} ${frame.y} ${frame.w} ${frame.h}`);
    const vals = values();
    const penText = Number(vals["beta-pen"]) || 0.5;
    const penImage = Number(vals["beta-image-pen"]) || 0.4;
    const names = (view.source?.layers ?? []).map((l) => l.name);
    svg.replaceChildren(...preview.layers.map((layer, i) => {
        const path = document.createElementNS(SVG_NS, "path");
        path.setAttribute("d", strokesPath(layer.strokes));
        path.setAttribute("stroke", /^#[0-9a-f]{6}$/i.test(layer.color ?? "") ? layer.color : "#141414");
        path.setAttribute("stroke-width", String(names[i] === "Ảnh" ? penImage : penText));
        return path;
    }));
}

function clearResult() {
    B.view = null;
    $("beta-result").replaceChildren();
    $("beta-stats").hidden = true;
    showWarnings([]);
}

function showStats(source) {
    const s = summarize(source);
    const rows = [
        [t("beta.stats.strokes"), String(s.strokes)],
        [t("beta.stats.draw"), `${(s.drawMm / 1000).toFixed(2)} m`],
        [t("beta.stats.travel"), `${(s.travelMm / 1000).toFixed(2)} m`],
        [t("beta.stats.minutes"), `~${s.minutes} ${t("beta.stats.minutesUnit")}`]
    ];
    if (s.chars) rows.push([t("beta.stats.chars"), `${s.chars} (${s.lines} ${t("beta.stats.lines")})`]);
    const dl = $("beta-stats");
    dl.replaceChildren(...rows.map(([k, v]) => {
        const div = document.createElement("div");
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = k;
        dd.textContent = v;
        div.append(dt, dd);
        return div;
    }));
    dl.hidden = false;
}
