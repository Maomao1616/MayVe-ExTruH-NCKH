// views/jobchart.js — Biểu đồ số liệu chạy máy, nằm trong "Khung nhìn 2D" của tab Điều khiển (nút chuyển [Đường vẽ | Biểu đồ]).
// Dữ liệu: GET /api/joblogs (backend/app/services/joblog.py ghi mỗi báo cáo trạng thái khi máy chạy tệp).
//   - tốc độ thật (`FS:`), hàng đợi chuyển động (`Bf:`; 0 khối = máy "đói lệnh"), độ cao bút Z;
//   - bảng tóm tắt + so sánh hai lần chạy (thời gian thật / ước tính, số lần nhấc bút, % thời gian vẽ...);
//   - đang chạy thì tự làm mới mỗi 2 giây. Chỉ quản lý dùng (route /api/joblogs cần đăng nhập).
// Tự vẽ bằng canvas: không thư viện ngoài (bản demo không có Internet). Phần tính nằm ở lib/chart.js.

import { api, ApiError } from "../core/api.js";
import { isAdmin } from "../core/auth.js";
import { t } from "../core/i18n.js";
import { formatDuration } from "../lib/gcode.js";
import { niceTicks, indexAt, summaryRows } from "../lib/chart.js";

const $ = (id) => document.getElementById(id);
const POLL_MS = 2000;
const PAD = { left: 50, right: 10, top: 8, bottom: 20 };

const S = { logs: [], runId: null, compareId: null, a: null, b: null, liveId: null, hoverT: null, timer: null, busy: false };

export function initJobChart() {
    const panel = document.querySelector(".preview-panel");
    const view = $("job-chart-view");
    if (!panel || !view) return;
    if (!isAdmin()) {                                    // khách không có quyền gọi /api/joblogs
        $("preview-view-switch")?.setAttribute("hidden", "");
        return;
    }
    panel.dataset.view = "path";

    for (const button of document.querySelectorAll("#preview-view-switch [data-view]")) {
        button.addEventListener("click", () => setView(button.dataset.view));
    }
    $("chart-run").addEventListener("change", () => { S.runId = $("chart-run").value; S.liveId = null; load(); });
    $("chart-compare").addEventListener("change", () => { S.compareId = $("chart-compare").value || null; load(); });
    $("chart-refresh-btn").addEventListener("click", () => refreshList());
    $("chart-delete-btn").addEventListener("click", deleteRun);

    let resizeTimer = null;
    window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(draw, 120); });
    window.addEventListener("extruxy:language-changed", () => { if (isOpen()) { fillSelects(); render(); } });
    for (const id of ["chart-speed", "chart-buffer", "chart-pen"]) {
        const canvas = $(id);
        canvas.addEventListener("mousemove", (e) => hover(e, canvas));
        canvas.addEventListener("mouseleave", () => { S.hoverT = null; draw(); hoverText(); });
    }
}

const isOpen = () => $("job-chart-view")?.offsetParent !== null;

function setView(name) {
    const panel = document.querySelector(".preview-panel");
    panel.dataset.view = name;
    for (const button of document.querySelectorAll("#preview-view-switch [data-view]")) {
        const on = button.dataset.view === name;
        button.setAttribute("aria-selected", String(on));
        button.classList.toggle("is-active", on);
    }
    $("job-chart-view").hidden = name !== "chart";
    clearInterval(S.timer);
    S.timer = null;
    if (name === "chart") {
        refreshList();
        S.timer = setInterval(tick, POLL_MS);
    }
}

// Đang xem thì làm mới: có lần chạy đang ghi thì kéo danh sách + số liệu mới; không thì thôi (đỡ tốn máy chủ).
async function tick() {
    if (document.hidden || !isOpen() || S.busy) return;
    if (S.liveId || S.a?.meta?.state === "running") await refreshList();
    else if (S.logs.length === 0 || S.logs[0]?.live) await refreshList();
}

/* ---------- tải dữ liệu ---------- */
async function refreshList() {
    if (S.busy) return;
    try {
        S.logs = (await api.joblogs()).logs;
    } catch (error) {
        return say(errorText(error), true);
    }
    const live = S.logs.find((l) => l.live);
    if (live && live.id !== S.liveId && live.id !== S.runId) { S.runId = live.id; }      // lần chạy mới bắt đầu: tự chuyển sang
    S.liveId = live?.id ?? null;
    if (!S.logs.some((l) => l.id === S.runId)) S.runId = S.logs[0]?.id ?? null;
    if (!S.logs.some((l) => l.id === S.compareId)) S.compareId = null;
    fillSelects();
    await load();
}

async function load() {
    if (!S.runId) { S.a = S.b = null; return render(); }
    S.busy = true;
    try {
        S.a = await api.joblog(S.runId);
        S.b = S.compareId ? await api.joblog(S.compareId) : null;
        say("");
    } catch (error) {
        S.a = S.b = null;
        say(errorText(error), true);
    } finally {
        S.busy = false;
    }
    render();
}

async function deleteRun() {
    if (!S.runId || !window.confirm(t("chart.confirmDelete"))) return;
    try {
        await api.joblogDelete(S.runId);
        S.runId = null;
        await refreshList();
    } catch (error) {
        say(errorText(error), true);
    }
}

/* ---------- giao diện ---------- */
function runLabel(log) {
    const when = log.started_at ? new Date(log.started_at * 1000).toLocaleString() : "?";
    const took = Number.isFinite(log.elapsed_s) ? formatDuration(log.elapsed_s) : "…";
    const live = log.live ? "● " : "";
    return `${live}${when} · ${log.name || "?"} · ${t(`chart.state.${log.state}`) !== `chart.state.${log.state}` ? t(`chart.state.${log.state}`) : log.state} · ${took}`;
}

function fillSelects() {
    const run = $("chart-run"), compare = $("chart-compare");
    run.replaceChildren(...S.logs.map((l) => new Option(runLabel(l), l.id)));
    run.value = S.runId ?? "";
    compare.replaceChildren(new Option(t("chart.noCompare"), ""),
        ...S.logs.filter((l) => l.id !== S.runId && !l.live).map((l) => new Option(runLabel(l), l.id)));
    compare.value = S.compareId ?? "";
    const has = S.logs.length > 0;
    for (const id of ["chart-run", "chart-compare", "chart-delete-btn"]) $(id).disabled = !has;
    const link = $("chart-csv-link");
    link.toggleAttribute("hidden", !S.runId);
    if (S.runId) link.href = api.joblogCsvUrl(S.runId);
}

function say(text, isError = false) {
    const notice = $("chart-notice");
    notice.hidden = !text;
    notice.textContent = text;
    notice.classList.toggle("is-error", isError);
}

const errorText = (error) => {
    const key = error instanceof ApiError ? `chart.error.${error.code}` : "";
    return key && t(key) !== key ? t(key) : (error?.message ?? String(error));
};

function render() {
    const empty = !S.a;
    $("chart-empty").hidden = !empty;
    $("chart-plots").hidden = empty;
    $("chart-summary").hidden = empty;
    if (empty) { $("chart-summary").replaceChildren(); if (!S.logs.length) say(""); return; }
    if (S.a.summary?.has_bf === false) say(t("chart.noBf"));
    else if (S.a.meta?.state === "running") say(t("chart.live"));
    else say("");
    renderSummary();
    draw();
}

function fmtValue(row, value) {
    if (value === null) return "—";
    if (row.key === "elapsed_s" || row.key === "est_seconds") return formatDuration(value);
    return `${value.toFixed(row.digits)}${row.unit ? ` ${row.unit}` : ""}`;
}

function renderSummary() {
    const rows = summaryRows(S.a, S.b);
    const table = $("chart-summary");
    const head = document.createElement("tr");
    const th = (text, cls) => { const e = document.createElement("th"); e.textContent = text; if (cls) e.className = cls; return e; };
    head.append(th(t("chart.row.metric")), th(t("chart.col.main")));
    if (S.b) head.append(th(t("chart.col.compare")), th(t("chart.col.delta")));
    const body = rows.filter((r) => r.a !== null || r.b !== null).map((row) => {
        const tr = document.createElement("tr");
        const label = document.createElement("td");
        label.textContent = t(`chart.row.${row.key}`);
        label.title = t(`chart.hint.${row.key}`) === `chart.hint.${row.key}` ? "" : t(`chart.hint.${row.key}`);
        const a = document.createElement("td");
        a.textContent = fmtValue(row, row.a);
        tr.append(label, a);
        if (S.b) {
            const b = document.createElement("td");
            b.textContent = fmtValue(row, row.b);
            const d = document.createElement("td");
            d.textContent = row.delta === null ? "—" : `${row.delta > 0 ? "+" : ""}${row.delta.toFixed(1)} %`;
            if (row.verdict) d.className = `is-${row.verdict}`;
            tr.append(b, d);
        }
        return tr;
    });
    table.replaceChildren(head, ...body);
}

/* ---------- vẽ ---------- */
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";

function draw() {
    if (!S.a || !isOpen()) return;
    const a = S.a.series, b = S.b?.series ?? null;
    const colors = { a: css("--accent-text"), b: css("--highlight"), muted: css("--text-muted"), grid: css("--border"),
                     text: css("--text-main"), bad: css("--danger"), ok: css("--success") };
    const tMax = Math.max(a.t.at(-1) ?? 1, b?.t.at(-1) ?? 0, 1);
    const top = S.a.summary?.planner_blocks_max ?? null;
    const hasBf = S.a.summary?.has_bf !== false && top !== null;

    plot($("chart-speed"), { tMax, yMin: 0, yUnit: "", colors, layers: [
        { kind: "area", t: a.t, y: a.feed, color: colors.a + "33" },
        { kind: "line", t: a.t, y: a.feed_max, color: colors.muted, width: 1 },
        { kind: "line", t: a.t, y: a.feed, color: colors.a, width: 1.6 },
        ...(b ? [{ kind: "line", t: b.t, y: b.feed, color: colors.b, width: 1.2, dash: [5, 3] }] : []),
        ...(S.a.summary?.feed_drawing_avg ? [{ kind: "hline", y: S.a.summary.feed_drawing_avg, color: colors.ok }] : [])
    ] });

    // Hàng đợi: số khối ĐANG CÓ (= tối đa − trống). 0 khi máy đang chạy = đói lệnh (đánh dấu đỏ).
    const filled = (series) => series.bf.map((v) => (v === null || top === null ? null : top - v));
    const fa = hasBf ? filled(a) : [];
    plot($("chart-buffer"), { tMax, yMin: 0, yMaxMin: Math.max(top ?? 1, 1), colors, empty: hasBf ? null : t("chart.noBfShort"), layers: hasBf ? [
        { kind: "area", t: a.t, y: fa, color: colors.a + "33" },
        { kind: "line", t: a.t, y: fa, color: colors.a, width: 1.4 },
        { kind: "marks", t: a.t, on: fa.map((v, i) => v === 0 && a.run[i] > 0.5), color: colors.bad },
        ...(b && S.b.summary?.has_bf !== false ? [{ kind: "line", t: b.t, y: filled(b), color: colors.b, width: 1.1, dash: [5, 3] }] : [])
    ] : [] });

    plot($("chart-pen"), { tMax, yMin: 0, yMaxMin: 5, colors, layers: [
        { kind: "line", t: a.t, y: a.z_max, color: colors.a + "88", width: 1 },
        { kind: "band", t: a.t, lo: a.z_min, hi: a.z_max, color: colors.a },
        ...(b ? [{ kind: "line", t: b.t, y: b.z_max, color: colors.b, width: 1, dash: [4, 3] }] : [])
    ] });
}

// Một biểu đồ: trục chung theo thời gian. layers: area | line | band | marks | hline.
function plot(canvas, cfg) {
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth || 600, height = canvas.clientHeight || 150;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const { colors } = cfg;

    let hi = cfg.yMaxMin ?? 1;
    for (const layer of cfg.layers) {
        const ys = layer.y ?? layer.hi ?? [];
        for (const v of (layer.kind === "hline" ? [layer.y] : ys)) if (Number.isFinite(v) && v > hi) hi = v;
    }
    const yt = niceTicks(cfg.yMin ?? 0, hi, 4);
    const xt = niceTicks(0, cfg.tMax, 6);
    const x0 = PAD.left, x1 = width - PAD.right, y0 = height - PAD.bottom, y1 = PAD.top;
    const X = (tt) => x0 + (tt / cfg.tMax) * (x1 - x0);
    const Y = (v) => y0 - ((v - yt.min) / (yt.max - yt.min || 1)) * (y0 - y1);
    canvas._map = { x0, x1, tMax: cfg.tMax };

    ctx.font = "11px system-ui, sans-serif";
    ctx.lineWidth = 1;
    ctx.strokeStyle = colors.grid;
    ctx.fillStyle = colors.muted;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (const v of yt.ticks) {
        ctx.beginPath(); ctx.moveTo(x0, Y(v)); ctx.lineTo(x1, Y(v)); ctx.stroke();
        ctx.fillText(String(v), x0 - 6, Y(v));
    }
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (const v of xt.ticks) {
        if (v > cfg.tMax) break;
        ctx.fillText(formatDuration(v), X(v), y0 + 4);
    }

    if (cfg.empty) {
        ctx.fillStyle = colors.muted;
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(cfg.empty, (x0 + x1) / 2, (y0 + y1) / 2);
    }

    for (const layer of cfg.layers) {
        ctx.save();
        ctx.setLineDash(layer.dash ?? []);
        if (layer.kind === "hline") {
            ctx.strokeStyle = layer.color; ctx.setLineDash([4, 4]);
            ctx.beginPath(); ctx.moveTo(x0, Y(layer.y)); ctx.lineTo(x1, Y(layer.y)); ctx.stroke();
        } else if (layer.kind === "band") {
            ctx.strokeStyle = layer.color; ctx.lineWidth = 1.5;
            ctx.beginPath();
            layer.t.forEach((tt, i) => {
                if (!Number.isFinite(layer.lo[i]) || !Number.isFinite(layer.hi[i])) return;
                ctx.moveTo(X(tt), Y(layer.lo[i])); ctx.lineTo(X(tt), Y(layer.hi[i]) - (layer.hi[i] === layer.lo[i] ? 1 : 0));
            });
            ctx.stroke();
        } else if (layer.kind === "marks") {
            ctx.fillStyle = layer.color;
            layer.t.forEach((tt, i) => { if (layer.on[i]) ctx.fillRect(X(tt) - 1, y0 - 4, 2, 4); });
        } else if (layer.kind === "area" || layer.kind === "line") {
            const area = layer.kind === "area";
            ctx.strokeStyle = layer.color; ctx.fillStyle = layer.color; ctx.lineWidth = layer.width ?? 1.4;
            ctx.beginPath();
            let open = false, lastX = x0;
            layer.t.forEach((tt, i) => {
                const v = layer.y[i];
                if (!Number.isFinite(v)) { if (open && area) { ctx.lineTo(lastX, Y(0)); ctx.closePath(); ctx.fill(); ctx.beginPath(); } open = false; return; }
                if (!open) { if (area) ctx.moveTo(X(tt), Y(0)); else ctx.moveTo(X(tt), Y(v)); open = true; if (area) ctx.lineTo(X(tt), Y(v)); }
                else ctx.lineTo(X(tt), Y(v));
                lastX = X(tt);
            });
            if (area) { if (open) { ctx.lineTo(lastX, Y(0)); ctx.closePath(); ctx.fill(); } } else ctx.stroke();
        }
        ctx.restore();
    }

    if (S.hoverT !== null && S.hoverT <= cfg.tMax) {
        ctx.strokeStyle = colors.text; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
        ctx.beginPath(); ctx.moveTo(X(S.hoverT), y1); ctx.lineTo(X(S.hoverT), y0); ctx.stroke();
    }
}

function hover(event, canvas) {
    const map = canvas._map;
    if (!map || !S.a) return;
    const rect = canvas.getBoundingClientRect();
    const px = event.clientX - rect.left;
    S.hoverT = Math.min(map.tMax, Math.max(0, ((px - map.x0) / (map.x1 - map.x0)) * map.tMax));
    draw();
    hoverText();
}

function hoverText() {
    const box = $("chart-hover");
    if (S.hoverT === null || !S.a) { box.textContent = t("chart.hoverHint"); return; }
    const s = S.a.series, i = indexAt(s.t, S.hoverT);
    if (i < 0) return;
    const top = S.a.summary?.planner_blocks_max;
    const queue = s.bf[i] === null || top === undefined ? "—" : String(top - s.bf[i]);
    const z = s.z_min[i] === null ? "—" : (s.z_min[i] === s.z_max[i] ? s.z_min[i].toFixed(1) : `${s.z_min[i].toFixed(1)}–${s.z_max[i].toFixed(1)}`);
    box.textContent = `${formatDuration(s.t[i])} · ${t("chart.speed")}: ${s.feed[i] ?? "—"} mm/min · ${t("chart.queue")}: ${queue} · Z: ${z} mm · ${t("chart.line")}: ${s.acked[i] ?? "—"}`;
}
