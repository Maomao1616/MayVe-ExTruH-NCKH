// views/preview.js — Khung nhìn 2D. Chủ sở hữu của #preview-canvas và thanh phát lại.
// Ba lớp, vẽ theo tọa độ MÁY (vùng làm việc 0..travel):
//   1. đường của tệp G-code (cộng độ lệch gốc làm việc), có thể phát lại ("Xem trước");
//   2. vết bút thật (theo vị trí máy báo về khi bút xuống);
//   3. đầu máy (vị trí máy báo về) và đầu bút phát lại.
// Xem trước chỉ đọc G-code ở trình duyệt, không gửi gì cho máy.

import { t } from "../core/i18n.js";
import { MACHINE, VIEW } from "../core/config.js";
import { subscribe, isConnected } from "../core/state.js";
import { subscribeStore } from "../stores/jobstore.js";
import { positionAt, formatDuration } from "../lib/gcode.js";

const MARGIN = 14;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 20;
const SPEEDS = [1, 5, 20, 100, 500, 2000];

/* ---------- phần thuần (có thể kiểm thử) ---------- */

export function makeTransform(width, height, travelX, travelY, zoom, panX, panY,
                              flipX = false, flipY = false) {
    const base = Math.min((width - 2 * MARGIN) / travelX, (height - 2 * MARGIN) / travelY);
    const scale = Math.max(base, 0.0001) * zoom;
    const ox = (width - travelX * scale) / 2 + panX;
    const oy = (height - travelY * scale) / 2 + panY;
    return {
        scale,
        toScreen: (x, y) => [
            ox + (flipX ? travelX - x : x) * scale,
            oy + (flipY ? travelY - y : y) * scale
        ],
        toWorld: (px, py) => {
            const x = (px - ox) / scale;
            const y = (py - oy) / scale;
            return [flipX ? travelX - x : x, flipY ? travelY - y : y];
        }
    };
}

// Vết bút: nhiều đoạn gấp khúc, mỗi đoạn là một lần hạ bút.
export function createTrail(limit = 50000, minStep = 0.05) {
    const lines = [];
    let current = null;
    let count = 0;
    return {
        lines,
        add(x, y, penDown) {
            if (!penDown) { current = null; return; }
            if (!current) { current = [[x, y]]; lines.push(current); count += 1; return; }
            const [lx, ly] = current[current.length - 1];
            if (Math.hypot(x - lx, y - ly) < minStep) return;
            current.push([x, y]);
            count += 1;
            while (count > limit) {
                if (lines.length > 1) { count -= lines[0].length; lines.shift(); }
                else { current.shift(); count -= 1; }
            }
        },
        clear() { lines.length = 0; current = null; count = 0; },
        get size() { return count; }
    };
}

// Điểm gần (x, y) nhất trên đoạn s (x0,y0)->(x1,y1): { x, y, d }.
export function nearestOnSegment(s, x, y) {
    const dx = s.x1 - s.x0, dy = s.y1 - s.y0;
    const len2 = dx * dx + dy * dy;
    const f = len2 > 0 ? Math.min(1, Math.max(0, ((x - s.x0) * dx + (y - s.y0) * dy) / len2)) : 0;
    const px = s.x0 + dx * f, py = s.y0 + dy * f;
    return { x: px, y: py, d: Math.hypot(x - px, y - py) };
}

// Tìm đoạn máy đang đi trên đường của tệp.
// Chỉ xét từ đoạn đã tới trở về sau (tiến độ không lùi) và chỉ các dòng máy đã nhận (`acked`):
// máy không thể ở sau dòng chưa gửi. Lấy đoạn ĐẦU TIÊN đi qua vị trí máy (sai số onPathMm).
export function trackProgress(segments, from, acked, x, y, { window = 400, onPathMm = 0.5 } = {}) {
    let best = null;
    const start = Math.max(0, from);
    for (let i = start; i < segments.length && i < start + window; i++) {
        const s = segments[i];
        if (s.seq > acked) break;
        if (s.kind === "dwell" || s.kind === "z") continue;
        const p = nearestOnSegment(s, x, y);
        if (!best || p.d < best.d) best = { index: i, x: p.x, y: p.y, d: p.d };
        if (p.d <= onPathMm) break;
    }
    return best;
}

/* ---------- giao diện ---------- */

export function initPreview() {
    const $ = (id) => document.getElementById(id);
    const container = $("preview-canvas-container");
    const canvas = $("preview-canvas");
    if (!container || !canvas) return;

    const ctx = canvas.getContext("2d");
    const el = {
        empty: $("preview-empty"), dims: $("preview-dimensions"), zoomLabel: $("preview-zoom"),
        zoomIn: $("zoom-in-btn"), zoomOut: $("zoom-out-btn"), fit: $("fit-preview-btn"),
        grid: $("show-grid"), travel: $("show-travel"),
        playback: $("preview-playback"), play: $("preview-play-btn"),
        restart: $("preview-restart-btn"), progress: $("preview-progress"),
        speed: $("preview-speed"), time: $("preview-time"), clearTrail: $("clear-trail-btn")
    };

    container.classList.add("is-canvas");   // CSS ẩn khung HTML tĩnh, canvas tự vẽ vùng làm việc

    // Hành trình đọc lại mỗi lần vẽ: Cài đặt → Cấu hình máy cập nhật MACHINE.travelX/Y theo YAML.
    let travelX = MACHINE.travelX, travelY = MACHINE.travelY;
    const view = { zoom: 1, panX: 0, panY: 0 };
    const trail = createTrail();

    let width = 0, height = 0, dpr = 1;
    let file = null;
    let total = 0;
    let clock = 0;                   // thời điểm phát lại (giây, theo ước tính)
    let playing = false;
    let speed = 20;
    let lastTick = 0;
    let lastToken = 0;
    let live = null;                 // { x, y } vị trí máy
    // Tiến độ tác vụ trên đường của tệp. Vết nối các lần hỏi vị trí (0,5 giây/lần) biến cung tròn
    // thành đa giác, nên khi đang chạy đúng tệp này thì vẽ lại chính đường của tệp tới chỗ máy đang ở.
    const progress = { jobId: null, index: -1, x: 0, y: 0, done: false, hidden: false };
    let wco = [0, 0, 0];
    let lastJobId = null;
    let frame = 0;

    /* --- vẽ --- */
    const requestDraw = () => {
        if (frame) return;
        frame = requestAnimationFrame(() => { frame = 0; draw(); });
    };

    const color = (css, name, fallback) => css.getPropertyValue(name).trim() || fallback;

    function draw() {
        if (!ctx || width === 0) return;
        travelX = MACHINE.travelX;
        travelY = MACHINE.travelY;
        const css = getComputedStyle(container);
        const c = {
            border: color(css, "--border", "#2a3038"),
            muted: color(css, "--text-muted", "#7a8494"),
            path: color(css, "--path-color", color(css, "--accent-text", "#00b6bd")),
            live: color(css, "--live-color", color(css, "--success", "#00b27a")),
            head: color(css, "--head-color", color(css, "--warning", "#e0b013"))
        };
        const T = makeTransform(width, height, travelX, travelY,
                                view.zoom, view.panX, view.panY, VIEW.flipX, VIEW.flipY);

        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, width, height);

        // vùng làm việc
        const [ax, ay] = T.toScreen(0, 0);
        const [bx, by] = T.toScreen(travelX, travelY);
        const rx = Math.min(ax, bx), ry = Math.min(ay, by);
        const rw = Math.abs(bx - ax), rh = Math.abs(by - ay);
        ctx.fillStyle = "rgba(255,255,255,0.03)";
        ctx.fillRect(rx, ry, rw, rh);

        if (el.grid?.checked) drawGrid(T, c);

        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = c.muted;
        ctx.lineWidth = 1;
        ctx.strokeRect(rx, ry, rw, rh);
        ctx.setLineDash([]);
        ctx.fillStyle = c.muted;
        ctx.font = "11px sans-serif";
        ctx.fillText("O (0, 0)", ax + (ax <= bx ? 6 : -50), ay + (ay <= by ? 14 : -6));
        ctx.fillText(`${travelX} × ${travelY} mm`, bx + (bx >= ax ? -86 : 6), by + (by >= ay ? -6 : 14));

        if (file) drawFile(T, c);
        drawTrail(T, c);
        drawHeads(T, c);
        updateLabels();
    }

    function drawGrid(T, c) {
        ctx.lineWidth = 1;
        const levels = [[10, 0.08], [50, 0.16]];
        for (const [step, alpha] of levels) {
            if (T.scale * step < 7) continue;
            ctx.strokeStyle = c.muted;
            ctx.globalAlpha = alpha;
            ctx.beginPath();
            for (let x = 0; x <= travelX; x += step) {
                const [p, q] = T.toScreen(x, 0), [, r] = T.toScreen(x, travelY);
                ctx.moveTo(p, q); ctx.lineTo(p, r);
            }
            for (let y = 0; y <= travelY; y += step) {
                const [p, q] = T.toScreen(0, y), [r] = T.toScreen(travelX, y);
                ctx.moveTo(p, q); ctx.lineTo(r, q);
            }
            ctx.stroke();
        }
        ctx.globalAlpha = 1;
    }

    function strokeSegments(T, segments, kinds, limit) {
        const [ox, oy] = wco;
        ctx.beginPath();
        const end = limit === undefined ? segments.length : limit;
        for (let i = 0; i < end; i++) {
            const s = segments[i];
            if (!kinds.has(s.kind)) continue;
            const [x0, y0] = T.toScreen(s.x0 + ox, s.y0 + oy);
            const [x1, y1] = T.toScreen(s.x1 + ox, s.y1 + oy);
            ctx.moveTo(x0, y0); ctx.lineTo(x1, y1);
        }
        ctx.stroke();
    }

    function drawFile(T, c) {
        const { segments } = file.parsed;
        const replay = clock > 0 || playing;
        const where = replay ? positionAt(segments, clock) : null;

        if (el.travel?.checked) {
            ctx.setLineDash([3, 4]);
            ctx.strokeStyle = c.muted;
            ctx.lineWidth = 1;
            ctx.globalAlpha = replay ? 0.35 : 0.7;
            strokeSegments(T, segments, new Set(["rapid", "travel"]));
            ctx.setLineDash([]);
        }
        ctx.strokeStyle = c.path;
        ctx.lineWidth = 1.6;
        ctx.globalAlpha = replay ? 0.25 : 1;
        strokeSegments(T, segments, new Set(["draw"]));
        if (replay && where) {
            ctx.globalAlpha = 1;
            strokeSegments(T, segments, new Set(["draw"]), where.index + 1);
        }
        ctx.globalAlpha = 1;
        drawProgress(T, c, segments);

        if (where) {                          // đầu bút phát lại
            const [px, py] = T.toScreen(where.x + wco[0], where.y + wco[1]);
            ctx.strokeStyle = c.head;
            ctx.fillStyle = where.penDown ? c.head : "transparent";
            ctx.lineWidth = 2;
            ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2);
            ctx.fill(); ctx.stroke();
        }
    }

    // Phần máy đã vẽ của tác vụ, theo đúng hình học của tệp (cung tròn vẫn tròn).
    function drawProgress(T, c, segments) {
        if (progress.hidden || progress.index < 0) return;
        const end = progress.done ? segments.length : progress.index;
        ctx.strokeStyle = c.live;
        ctx.lineWidth = 2;
        ctx.lineJoin = "round";
        strokeSegments(T, segments, new Set(["draw"]), end);
        const s = segments[progress.index];
        if (!progress.done && s?.kind === "draw") {          // đoạn đang vẽ dở
            const [ox, oy] = wco;
            const [x0, y0] = T.toScreen(s.x0 + ox, s.y0 + oy);
            const [x1, y1] = T.toScreen(progress.x + ox, progress.y + oy);
            ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
        }
    }

    // Đang chạy đúng tệp đang nạp? (cùng tên và cùng số dòng gửi đi)
    const tracksFile = (job) => Boolean(file && job &&
        job.name === file.name && job.total === file.parsed.lines.length);

    function updateProgress(job, machine) {
        if (progress.jobId !== job.id) {
            Object.assign(progress, { jobId: job.id, index: -1, done: false, hidden: false });
        }
        if (job.state === "done") { progress.done = true; return; }
        const wpos = Array.isArray(machine?.wpos) ? machine.wpos
            : Array.isArray(machine?.mpos) ? machine.mpos.map((m, i) => m - (wco[i] ?? 0)) : null;
        if (!wpos || !(job.state === "running" || job.state === "finishing")) return;
        const hit = trackProgress(file.parsed.segments, progress.index, job.acked, wpos[0], wpos[1]);
        if (hit) Object.assign(progress, { index: hit.index, x: hit.x, y: hit.y });
    }

    function drawTrail(T, c) {
        ctx.strokeStyle = c.live;
        ctx.lineWidth = 2;
        ctx.lineJoin = "round";
        for (const line of trail.lines) {
            if (line.length < 2) continue;
            ctx.beginPath();
            line.forEach(([x, y], i) => {
                const [px, py] = T.toScreen(x, y);
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            });
            ctx.stroke();
        }
    }

    function drawHeads(T, c) {
        if (!live) return;
        const [px, py] = T.toScreen(live.x, live.y);
        ctx.strokeStyle = c.live;
        ctx.fillStyle = c.live;
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(px, py, 4, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath();
        ctx.moveTo(px - 9, py); ctx.lineTo(px + 9, py);
        ctx.moveTo(px, py - 9); ctx.lineTo(px, py + 9);
        ctx.stroke();
    }

    function updateLabels() {
        if (el.dims) el.dims.textContent = `${t("control.preview.workArea")}: ${travelX} × ${travelY} mm`;
        if (el.zoomLabel) el.zoomLabel.textContent = `${Math.round(view.zoom * 100)}%`;
        if (el.empty) el.empty.style.display = file ? "none" : "";
        if (el.time) el.time.textContent = `${formatDuration(clock)} / ${formatDuration(total)}`;
        if (el.progress && total > 0) el.progress.value = String(Math.round((clock / total) * 1000));
        if (el.play) el.play.textContent = playing ? "⏸" : "▶";
    }

    /* --- kích thước --- */
    function resize() {
        const rect = container.getBoundingClientRect();
        width = Math.max(1, Math.floor(rect.width));
        height = Math.max(1, Math.floor(rect.height));
        dpr = window.devicePixelRatio || 1;
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        requestDraw();
    }
    if (typeof ResizeObserver !== "undefined") new ResizeObserver(resize).observe(container);
    window.addEventListener("resize", resize);
    resize();

    /* --- phóng to / kéo --- */
    const transformNow = () => makeTransform(width, height, travelX, travelY,
        view.zoom, view.panX, view.panY, VIEW.flipX, VIEW.flipY);

    function zoomAt(factor, px = width / 2, py = height / 2) {
        const [wx, wy] = transformNow().toWorld(px, py);
        view.zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, view.zoom * factor));
        const [nx, ny] = transformNow().toScreen(wx, wy);
        view.panX += px - nx;
        view.panY += py - ny;
        requestDraw();
    }
    const fitView = () => { view.zoom = 1; view.panX = 0; view.panY = 0; requestDraw(); };

    el.zoomIn?.addEventListener("click", () => zoomAt(1.25));
    el.zoomOut?.addEventListener("click", () => zoomAt(0.8));
    el.fit?.addEventListener("click", fitView);
    el.grid?.addEventListener("change", requestDraw);
    el.travel?.addEventListener("change", requestDraw);

    canvas.addEventListener("wheel", (event) => {
        // Chỉ phóng to/thu nhỏ khi người dùng giữ phím Shift
        if (!event.shiftKey) return; 
        
        event.preventDefault();
        const rect = canvas.getBoundingClientRect();
        zoomAt(event.deltaY < 0 ? 1.15 : 1 / 1.15, event.clientX - rect.left, event.clientY - rect.top);
    }, { passive: false });

    let drag = null;
    canvas.addEventListener("pointerdown", (event) => {
        drag = { x: event.clientX, y: event.clientY };
        canvas.setPointerCapture?.(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
        if (!drag) return;
        view.panX += event.clientX - drag.x;
        view.panY += event.clientY - drag.y;
        drag = { x: event.clientX, y: event.clientY };
        requestDraw();
    });
    const endDrag = () => { drag = null; };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    /* --- phát lại --- */
    function tick(now) {
        if (!playing) return;
        clock = Math.min(total, clock + ((now - lastTick) / 1000) * speed);
        lastTick = now;
        if (clock >= total) playing = false;
        draw();
        if (playing) requestAnimationFrame(tick);
    }
    function play() {
        if (!file || total <= 0) return;
        if (clock >= total) clock = 0;
        playing = true;
        lastTick = performance.now();
        requestAnimationFrame(tick);
    }
    const pause = () => { playing = false; requestDraw(); };

    el.play?.addEventListener("click", () => (playing ? pause() : play()));
    el.restart?.addEventListener("click", () => { clock = 0; play(); });
    el.progress?.addEventListener("input", () => {
        clock = (Number(el.progress.value) / 1000) * total;
        requestDraw();
    });
    el.speed?.addEventListener("change", () => { speed = Number(el.speed.value) || speed; });
    el.clearTrail?.addEventListener("click", () => {
        trail.clear();
        progress.hidden = true;              // ẩn tới khi có tác vụ mới
        requestDraw();
    });

    function pickDefaultSpeed() {
        // Chọn tốc độ phát lại để cả bản vẽ xem hết trong khoảng 30 giây.
        speed = SPEEDS.find((s) => total / s <= 30) ?? SPEEDS[SPEEDS.length - 1];
        if (el.speed) el.speed.value = String(speed);
    }

    /* --- nguồn dữ liệu --- */
    subscribeStore((store) => {
        const changed = store.file !== file;
        file = store.file;
        total = file ? file.parsed.seconds : 0;
        if (changed) {
            clock = 0;
            playing = false;
            Object.assign(progress, { jobId: null, index: -1, done: false, hidden: false });
            if (el.playback) el.playback.hidden = !file;
            if (file) pickDefaultSpeed();
            fitView();
        }
        if (store.previewToken !== lastToken) {
            lastToken = store.previewToken;
            if (file) { clock = 0; play(); }
        }
        requestDraw();
    });

    subscribe((snapshot) => {
        const machine = snapshot.status?.machine;
        const job = snapshot.status?.job;

        if (Array.isArray(machine?.wco)) wco = machine.wco;
        else if (Array.isArray(machine?.mpos) && Array.isArray(machine?.wpos)) {
            wco = machine.mpos.map((m, i) => m - machine.wpos[i]);
        }

        if (job?.id !== lastJobId) {          // tác vụ mới: bắt đầu vết mới
            lastJobId = job?.id ?? null;
            if (job) trail.clear();
        }

        const following = tracksFile(job);
        if (following) updateProgress(job, machine);

        if (isConnected() && Array.isArray(machine?.mpos)) {
            const [x, y, z] = machine.mpos;
            live = { x, y };
            // Đang chạy đúng tệp: vết lấy từ đường của tệp (drawProgress), không nối điểm hỏi.
            // Ngoài tác vụ (jog tay): vẽ khi Z dưới trung điểm nấc Xuống–Giữa.
            trail.add(x, y, !following && z < (MACHINE.penDownZ + MACHINE.penMidZ) / 2);
        } else {
            live = null;
            trail.add(0, 0, false);           // ngắt vết, không nối qua lúc mất dữ liệu
        }
        requestDraw();
    });

    draw();
}
