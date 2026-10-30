// views/drawing/canvas.js — canvas khung vẽ: tờ giấy (A6/A5/A4 như khung dán thật trên bàn), lề, nét xem nháp
// với độ rộng bút thật, khung vẽ có 8 tay nắm (kéo / co giãn / hít vào lề và tâm), thu phóng, kéo nền.
// Không gọi mạng, không biết gì về form: nhận `scene` từ drawing.js và báo khung mới qua `onBox`.
import { matrix, meanScale } from "../../lib/paper.js";

const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
const CURSORS = { nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize",
    n: "ns-resize", s: "ns-resize", e: "ew-resize", w: "ew-resize" };
const HANDLE_PX = 7;          // bán kính vùng bắt tay nắm (px màn hình)
const SNAP_PX = 6;            // hít vào lề/tâm khi cách dưới ngần này px
const MIN_BOX_MM = 5;
const LAYER_COLORS = ["", "#ff9f5a", "#7ad66b", "#e0c24a", "#c58bff"];     // "" = màu nhấn của giao diện
const REFERENCE = [["a6", "A6"], ["a5", "A5"], ["a4", "A4"]];             // khung vẽ sẵn trên bàn máy

const token = (name, fallback) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;

// Dựng Path2D từ các nét [[x, y], ...] (tọa độ nguồn, mm).
export function buildPath(strokes) {
    const path = new Path2D();
    for (const stroke of strokes) {
        if (stroke.length < 2) continue;
        path.moveTo(stroke[0][0], stroke[0][1]);
        for (let i = 1; i < stroke.length; i++) path.lineTo(stroke[i][0], stroke[i][1]);
    }
    return path;
}

function layerColor(layer, index, fallback) {
    const hex = /^#([0-9a-f]{6})$/i.exec(layer.color ?? "");
    if (hex) {
        const n = parseInt(hex[1], 16);
        const lum = (0.2126 * (n >> 16) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
        if (lum > 0.35 && lum < 0.95) return layer.color;            // màu đen/trắng khó thấy trên nền: dùng màu mặc định
    }
    return LAYER_COLORS[index % LAYER_COLORS.length] || fallback;
}

// Co giãn một khung theo tay nắm. Trả null nếu kết quả ra ngoài phần trong lề (giữ khung cũ).
export function resizeRect(handle, b, p, inner, lock, min = MIN_BOX_MM) {
    const clampX = (v) => Math.min(inner.x + inner.w, Math.max(inner.x, v));
    const clampY = (v) => Math.min(inner.y + inner.h, Math.max(inner.y, v));
    let x0 = b.x, y0 = b.y, x1 = b.x + b.w, y1 = b.y + b.h;
    if (handle.includes("w")) x0 = Math.min(clampX(p.x), x1 - min);
    if (handle.includes("e")) x1 = Math.max(clampX(p.x), x0 + min);
    if (handle.includes("n")) y0 = Math.min(clampY(p.y), y1 - min);
    if (handle.includes("s")) y1 = Math.max(clampY(p.y), y0 + min);
    let w = x1 - x0;
    let h = y1 - y0;
    if (lock && b.h > 0) {
        const a = b.w / b.h;
        if (handle.length === 2) {                              // góc: phóng theo cạnh lớn hơn
            if (w / a > h) h = w / a; else w = h * a;
            if (handle.includes("w")) x0 = x1 - w; else x1 = x0 + w;
            if (handle.includes("n")) y0 = y1 - h; else y1 = y0 + h;
        } else if (handle === "e" || handle === "w") {          // cạnh trái/phải: cao đổi theo, giữ tâm dọc
            h = w / a;
            const cy = b.y + b.h / 2;
            y0 = cy - h / 2; y1 = cy + h / 2;
            if (handle === "w") x0 = x1 - w; else x1 = x0 + w;
        } else {                                                // cạnh trên/dưới: rộng đổi theo, giữ tâm ngang
            w = h * a;
            const cx = b.x + b.w / 2;
            x0 = cx - w / 2; x1 = cx + w / 2;
            if (handle === "n") y0 = y1 - h; else y1 = y0 + h;
        }
        const e = 1e-9;
        if (x0 < inner.x - e || y0 < inner.y - e || x1 > inner.x + inner.w + e || y1 > inner.y + inner.h + e) return null;
    }
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}

// scene: { machine:{W,H}, paper:{w,h,name}, papers:{a4:{w,h},...}, plan (kết quả paper.plan), box (khung khi plan lỗi),
//          error (mã lỗi hoặc null), layers:[{path, color}], penMm, lock }
// onBox(rect {x,y,w,h} mm, { final }) được gọi khi người dùng kéo/co giãn khung.
export function createCanvas({ canvas, stage, zoomLabel, onBox }) {
    const ctx = canvas.getContext("2d");
    let scene = null;
    let dpr = 1;
    let view = { s: 1, tx: 0, ty: 0 };
    let baseScale = 1;
    let userView = false;               // người dùng đã thu phóng/kéo nền: đừng tự fit lại khi đổi cỡ cửa sổ
    let drag = null;
    let hover = null;                   // vị trí chuột (mm) để hiện tọa độ

    canvas.tabIndex = 0;                // nhận phím mũi tên khi đang chọn khung

    const world = () => scene?.machine ?? { W: 285, H: 318 };
    const activeBox = () => scene?.plan?.ok ? scene.plan.box : scene?.box ?? null;
    const innerArea = () => scene?.plan?.inner ?? scene?.inner ?? null;

    function fit() {
        const { W, H } = world();
        const pad = 14;
        const w = canvas.width / dpr;
        const h = canvas.height / dpr;
        baseScale = Math.max(0.1, Math.min((w - 2 * pad) / W, (h - 2 * pad) / H));
        view = { s: baseScale, tx: (w - W * baseScale) / 2, ty: (h - H * baseScale) / 2 };
        userView = false;
    }

    function resize() {
        dpr = window.devicePixelRatio || 1;
        const w = Math.max(50, stage.clientWidth);
        const h = Math.max(50, stage.clientHeight);
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        if (!userView) fit();
        draw();
    }

    const toScreen = (x, y) => [view.tx + x * view.s, view.ty + y * view.s];
    const fromEvent = (e) => {
        const r = canvas.getBoundingClientRect();
        const px = (e.clientX - r.left) * (canvas.width / dpr / r.width);
        const py = (e.clientY - r.top) * (canvas.height / dpr / r.height);
        return { px, py, x: (px - view.tx) / view.s, y: (py - view.ty) / view.s };
    };

    /* ---------- vẽ ---------- */
    function draw() {
        if (!canvas.width) return;
        const bg = token("--bg-main", "#0e0e0e");
        const grid = token("--border", "#2a2a2a");
        const accent = token("--accent-text", "#3cc8d4");
        const muted = token("--text-muted", "#999");
        const danger = token("--danger", "#e5484d");
        const { W, H } = world();

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        // vùng máy + lưới 10 mm (đậm hơn mỗi 50 mm)
        ctx.save();
        ctx.translate(view.tx, view.ty);
        ctx.scale(view.s, view.s);
        ctx.lineWidth = 1 / view.s;
        ctx.strokeStyle = grid;
        for (let x = 0; x <= W; x += 10) {
            ctx.globalAlpha = x % 50 === 0 ? 0.55 : 0.2;
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        }
        for (let y = 0; y <= H; y += 10) {
            ctx.globalAlpha = y % 50 === 0 ? 0.55 : 0.2;
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
        }
        ctx.globalAlpha = 1;
        ctx.setLineDash([4 / view.s, 3 / view.s]);
        ctx.strokeStyle = muted;
        ctx.strokeRect(0, 0, W, H);
        ctx.setLineDash([]);

        // tờ giấy đang chọn
        const paper = scene?.paper;
        if (paper) {
            ctx.fillStyle = "rgba(255,255,255,0.07)";
            ctx.fillRect(0, 0, paper.w, paper.h);
        }
        // khung giấy dán sẵn trên bàn máy (A6 / A5 / A4)
        ctx.strokeStyle = accent;
        ctx.globalAlpha = 0.45;
        for (const [key] of REFERENCE) {
            const p = scene?.papers?.[key];
            if (p) ctx.strokeRect(0, 0, p.w, p.h);
        }
        ctx.globalAlpha = 1;
        if (paper) {
            ctx.strokeStyle = accent;
            ctx.lineWidth = 1.6 / view.s;
            ctx.strokeRect(0, 0, paper.w, paper.h);
            const inner = innerArea();
            if (inner) {
                ctx.lineWidth = 1 / view.s;
                ctx.setLineDash([3 / view.s, 3 / view.s]);
                ctx.globalAlpha = 0.6;
                ctx.strokeRect(inner.x, inner.y, inner.w, inner.h);
                ctx.globalAlpha = 1;
                ctx.setLineDash([]);
            }
        }

        // nét vẽ, bề rộng = độ rộng bút thật (tối thiểu ~1 px để vẫn thấy khi thu nhỏ)
        const plan = scene?.plan;
        if (plan?.ok && scene.layers?.length) {
            const m = matrix(plan);
            ctx.save();
            ctx.transform(m[0], m[1], m[2], m[3], m[4], m[5]);
            const mean = meanScale(plan) || 1;
            ctx.lineWidth = Math.max(scene.penMm ?? 0.4, 1 / view.s) / mean;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.globalAlpha = 0.92;
            scene.layers.forEach((layer, i) => {
                ctx.strokeStyle = layerColor(layer, i, accent);
                ctx.stroke(layer.path);
            });
            ctx.restore();
        }
        ctx.restore();

        // chữ và tay nắm vẽ ở toạ độ màn hình để luôn rõ nét
        ctx.font = "11px system-ui, sans-serif";
        ctx.fillStyle = muted;
        const [ox, oy] = toScreen(0, 0);
        ctx.textBaseline = "top";
        ctx.fillText("O (0, 0)", ox + 6, oy + 5);
        ctx.textAlign = "right";
        const [mx, my] = toScreen(W, H);
        ctx.textBaseline = "bottom";
        ctx.fillText(`${W} × ${H} mm`, mx - 6, my - 5);
        ctx.textAlign = "left";
        ctx.fillStyle = accent;
        for (const [key, label] of REFERENCE) {
            const p = scene?.papers?.[key];
            if (!p) continue;
            const [lx, ly] = toScreen(p.w, p.h);
            ctx.textAlign = "right";
            ctx.fillText(label, lx - 5, ly - 4);
        }
        ctx.textAlign = "left";

        const box = activeBox();
        if (box) {
            const [bx, by] = toScreen(box.x, box.y);
            const bw = box.w * view.s;
            const bh = box.h * view.s;
            const bad = Boolean(scene.error);
            const color = bad ? danger : accent;
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.2;
            ctx.setLineDash([6, 4]);
            ctx.strokeRect(bx, by, bw, bh);
            ctx.setLineDash([]);
            ctx.fillStyle = color;
            ctx.textBaseline = "bottom";
            ctx.fillText(`${box.w.toFixed(1)} × ${box.h.toFixed(1)} mm`, bx, by - 4);
            ctx.textBaseline = "alphabetic";
            ctx.fillStyle = bg;
            for (const h of HANDLES) {
                const [hx, hy] = handlePos(h, bx, by, bw, bh);
                ctx.beginPath();
                ctx.rect(hx - 4, hy - 4, 8, 8);
                ctx.fill();
                ctx.stroke();
            }
        }
        updateLabel();
    }

    function handlePos(h, bx, by, bw, bh) {
        const x = h.includes("w") ? bx : h.includes("e") ? bx + bw : bx + bw / 2;
        const y = h.includes("n") ? by : h.includes("s") ? by + bh : by + bh / 2;
        return [x, y];
    }

    function updateLabel() {
        if (!zoomLabel) return;
        const zoom = `${Math.round((view.s / baseScale) * 100)}%`;
        zoomLabel.textContent = hover ? `${hover.x.toFixed(1)}, ${hover.y.toFixed(1)} mm · ${zoom}` : zoom;
    }

    /* ---------- chuột / cảm ứng ---------- */
    function hit(e) {
        const box = activeBox();
        if (!box) return { type: "pan" };
        const [bx, by] = toScreen(box.x, box.y);
        const bw = box.w * view.s;
        const bh = box.h * view.s;
        for (const h of HANDLES) {
            const [hx, hy] = handlePos(h, bx, by, bw, bh);
            if (Math.hypot(e.px - hx, e.py - hy) <= HANDLE_PX + 3) return { type: "resize", handle: h };
        }
        if (e.px >= bx && e.px <= bx + bw && e.py >= by && e.py <= by + bh) return { type: "move" };
        return { type: "pan" };
    }

    function snapMove(box0, dx, dy) {
        const inner = innerArea();
        let x = box0.x + dx;
        let y = box0.y + dy;
        if (!inner) return { x, y };
        const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
        x = clamp(x, inner.x, inner.x + inner.w - box0.w);
        y = clamp(y, inner.y, inner.y + inner.h - box0.h);
        const snap = (v, cands) => {
            for (const c of cands) if (Math.abs(v - c) * view.s < SNAP_PX) return c;
            return v;
        };
        x = snap(x, [inner.x, inner.x + (inner.w - box0.w) / 2, inner.x + inner.w - box0.w]);
        y = snap(y, [inner.y, inner.y + (inner.h - box0.h) / 2, inner.y + inner.h - box0.h]);
        return { x, y };
    }

    canvas.addEventListener("pointerdown", (event) => {
        const e = fromEvent(event);
        const h = hit(e);
        const box = activeBox();
        if (h.type === "pan" && view.s <= baseScale * 1.001) return;      // chưa phóng to thì khóa cứng, không kéo nền
        drag = h.type === "pan"
            ? { type: "pan", cx: event.clientX, cy: event.clientY, tx: view.tx, ty: view.ty }
            : { ...h, start: e, box0: { ...box }, moved: false };
        canvas.setPointerCapture(event.pointerId);
        canvas.focus({ preventScroll: true });
        event.preventDefault();
    });

    canvas.addEventListener("pointermove", (event) => {
        const e = fromEvent(event);
        hover = { x: e.x, y: e.y };
        if (!drag) {
            const h = hit(e);
            const zoomed = view.s > baseScale * 1.001;
            canvas.style.cursor = h.type === "resize" ? CURSORS[h.handle] : h.type === "move" ? "move" : zoomed ? "grab" : "default";
            updateLabel();
            return;
        }
        if (drag.type === "pan") {
            const r = canvas.getBoundingClientRect();
            const k = canvas.width / dpr / r.width;
            view.tx = drag.tx + (event.clientX - drag.cx) * k;
            view.ty = drag.ty + (event.clientY - drag.cy) * k;
            userView = true;
            draw();
            return;
        }
        let rect = null;
        if (drag.type === "move") {
            const { x, y } = snapMove(drag.box0, e.x - drag.start.x, e.y - drag.start.y);
            rect = { x, y, w: drag.box0.w, h: drag.box0.h };
        } else {
            const inner = innerArea();
            if (inner) rect = resizeRect(drag.handle, drag.box0, { x: e.x, y: e.y }, inner, scene.lock);
        }
        if (rect) {
            drag.moved = true;
            onBox(rect, { final: false });
        }
    });

    const finish = (event) => {
        if (!drag) return;
        const wasEdit = drag.type !== "pan" && drag.moved;
        drag = null;
        try { canvas.releasePointerCapture(event.pointerId); } catch { /* đã nhả */ }
        if (wasEdit) onBox(null, { final: true });
    };
    canvas.addEventListener("pointerup", finish);
    canvas.addEventListener("pointercancel", finish);
    canvas.addEventListener("pointerleave", () => { hover = null; updateLabel(); });

    // Khóa thu phóng: chỉ Shift + cuộn mới phóng to/nhỏ; cuộn thường để trang cuộn bình thường
    // (khung vẽ không "nuốt" con lăn khi người dùng chỉ định kéo xuống xem phần dưới).
    canvas.addEventListener("wheel", (event) => {
        if (!event.shiftKey) return;
        event.preventDefault();
        const e = fromEvent(event);
        const delta = event.deltaY || event.deltaX;          // Shift + cuộn có trình duyệt đổi sang cuộn ngang
        const factor = Math.exp(-delta * 0.0015);
        const next = Math.min(baseScale * 14, Math.max(baseScale * 0.6, view.s * factor));
        view.tx = e.px - (e.px - view.tx) * (next / view.s);
        view.ty = e.py - (e.py - view.ty) * (next / view.s);
        view.s = next;
        userView = true;
        draw();
    }, { passive: false });

    canvas.addEventListener("dblclick", () => { fit(); draw(); });

    // Mũi tên nhích khung 1 mm (Shift: 10 mm) khi canvas đang được chọn.
    canvas.addEventListener("keydown", (event) => {
        const box = activeBox();
        const step = event.shiftKey ? 10 : 1;
        const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[event.key];
        if (!box || !d) return;
        event.preventDefault();
        const inner = innerArea();
        if (!inner) return;
        const x = Math.min(inner.x + inner.w - box.w, Math.max(inner.x, box.x + d[0]));
        const y = Math.min(inner.y + inner.h - box.h, Math.max(inner.y, box.y + d[1]));
        onBox({ x, y, w: box.w, h: box.h }, { final: false });
        onBox(null, { final: true });
    });

    new ResizeObserver(resize).observe(stage);
    resize();

    return {
        setScene(next) { scene = next; draw(); },
        redraw: draw,
        resetView() { fit(); draw(); }
    };
}
