// gcode.js — đọc G-code thành các đoạn đường để xem trước. THUẦN (không DOM, không mạng).
// Phạm vi: G0 G1 G2 G3 (I J hoặc R), G4, G17, G20/G21, G54, G90/G91, F, M2/M30, bút qua trục Z.
// Mọi thứ khác được ghi vào `warnings` thay vì đoán. Tọa độ là tọa độ LÀM VIỆC (mm).

const WORD = /([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))/g;
const PAREN = /\([^)]*\)/g;
const MM_PER_INCH = 25.4;

export const DEFAULT_OPTIONS = {
    penUpZ: 5,           // Z bút lên (giả định, xem config.js)
    penDownZ: 0,         // Z bút xuống
    rapidFeed: 6000,     // mm/phút khi G0
    defaultFeed: 1000,   // dùng khi G1 thiếu F
    arcTolerance: 0.05   // sai số khi chia cung tròn (mm)
};

// Làm sạch một dòng giống backend (services/job.py): bỏ chú thích, rút gọn khoảng trắng.
export function cleanLine(raw) {
    const line = raw.split(";")[0].replace(PAREN, "").trim();
    if (!line || line.startsWith("%")) return "";
    return line.replace(/\s+/g, " ");
}

function arcPoints(start, end, centerOffset, radiusWord, clockwise, tolerance) {
    // Trả về { points: [[x, y], ...] (không gồm điểm đầu), ok }
    let cx, cy;
    const dx = end.x - start.x;
    const dy = end.y - start.y;

    if (radiusWord !== null) {                        // dạng R (theo Grbl 1.1)
        const chord2 = dx * dx + dy * dy;
        if (chord2 === 0) return { ok: false };
        let r = radiusWord;
        let h = 4 * r * r - chord2;
        if (h < 0) return { ok: false };
        h = -Math.sqrt(h) / Math.sqrt(chord2);
        if (!clockwise) h = -h;
        if (r < 0) { h = -h; r = -r; }
        cx = start.x + 0.5 * (dx - dy * h);
        cy = start.y + 0.5 * (dy + dx * h);
    } else {                                           // dạng I J: tâm tương đối so với điểm đầu
        cx = start.x + centerOffset.i;
        cy = start.y + centerOffset.j;
    }

    const radius = Math.hypot(start.x - cx, start.y - cy);
    if (!(radius > 0)) return { ok: false };

    const a1 = Math.atan2(start.y - cy, start.x - cx);
    const a2 = Math.atan2(end.y - cy, end.x - cx);
    let sweep = a2 - a1;
    const EPS = 1e-6;
    if (clockwise) { if (sweep >= -EPS) sweep -= 2 * Math.PI; }
    else if (sweep <= EPS) sweep += 2 * Math.PI;

    const step = 2 * Math.acos(1 - Math.min(tolerance / radius, 1));
    const count = Math.min(720, Math.max(2, Math.ceil(Math.abs(sweep) / (step || 1))));
    const points = [];
    for (let k = 1; k < count; k++) {
        const a = a1 + (sweep * k) / count;
        points.push([cx + radius * Math.cos(a), cy + radius * Math.sin(a)]);
    }
    points.push([end.x, end.y]);
    return { points, ok: true };
}

export function parseGcode(text, options = {}) {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    const rawLines = text.split(/\r\n|\r|\n/);
    const hasZ = /(^|[^A-Z])Z\s*[-+]?[\d.]/i.test(rawLines.map(cleanLine).join("\n"));
    const penThreshold = (opts.penUpZ + opts.penDownZ) / 2;

    const warnings = [];
    const warn = (line, key, detail = "") => warnings.push({ line, key, detail });

    const lines = [];       // dòng đã làm sạch, đúng thứ tự sẽ gửi cho máy
    const segments = [];
    const pos = { x: 0, y: 0, z: hasZ ? opts.penUpZ : 0 };
    let absolute = true;
    let unit = 1;           // 1 = mm, 25.4 = inch
    let feed = 0;           // mm/phút
    let motion = null;      // 0, 1, 2, 3
    let penDown = !hasZ;    // không có Z nào: coi mọi G1 là nét vẽ
    let time = 0;
    let ended = false;
    const features = { arcs: 0, hasZ };

    let seq = 0;            // số thứ tự dòng thực sự gửi đi (khớp job.sent/acked của backend)
    const push = (segment) => {
        segment.seq = seq;
        segment.t0 = time;
        time += segment.dur;
        segments.push(segment);
    };

    rawLines.forEach((raw, index) => {
        const lineNo = index + 1;
        const line = cleanLine(raw);
        if (!line || ended) return;     // sau M2/M30 chương trình đã kết thúc: không gửi, không vẽ
        lines.push(line);
        seq = lines.length;

        const words = [...line.toUpperCase().matchAll(WORD)].map((m) => [m[1], Number(m[2])]);
        const vals = {};
        let dwell = null;
        let skipMotion = false;     // dòng có lệnh G không hỗ trợ: không suy đoán chuyển động

        for (const [letter, num] of words) {
            if (letter === "G") {
                const g = Math.round(num * 10) / 10;
                if (g === 0 || g === 1 || g === 2 || g === 3) motion = g;
                else if (g === 4) dwell = true;
                else if (g === 20) unit = MM_PER_INCH;
                else if (g === 21) unit = 1;
                else if (g === 90) absolute = true;
                else if (g === 91) absolute = false;
                else if (g === 17 || g === 54 || g === 94) { /* chấp nhận, không ảnh hưởng */ }
                else { warn(lineNo, "unsupported_g", `G${g}`); skipMotion = true; }
            } else if (letter === "M") {
                const m = Math.round(num);
                if (m === 2 || m === 30) ended = true;
                else if (m === 0 || m === 1) warn(lineNo, "program_pause", `M${m}`);
                else if (![3, 4, 5, 6, 7, 8, 9].includes(m)) warn(lineNo, "unsupported_m", `M${m}`);
            } else if (letter === "F") {
                feed = num * unit;
            } else if ("XYZIJKRP".includes(letter)) {
                vals[letter] = num;
            }
        }

        if (dwell && vals.P !== undefined) {
            push({ kind: "dwell", x0: pos.x, y0: pos.y, x1: pos.x, y1: pos.y, dur: vals.P, line: lineNo });
            return;
        }

        const hasAxis = ["X", "Y", "Z"].some((a) => vals[a] !== undefined);
        const arcLike = (motion === 2 || motion === 3) &&
            (vals.I !== undefined || vals.J !== undefined || vals.R !== undefined);
        if (skipMotion || (!hasAxis && !arcLike) || motion === null) return;

        const target = {
            x: vals.X === undefined ? pos.x : (absolute ? vals.X * unit : pos.x + vals.X * unit),
            y: vals.Y === undefined ? pos.y : (absolute ? vals.Y * unit : pos.y + vals.Y * unit),
            z: vals.Z === undefined ? pos.z : (absolute ? vals.Z * unit : pos.z + vals.Z * unit)
        };

        const rapid = motion === 0;
        let speed = rapid ? opts.rapidFeed : feed;
        if (!rapid && !(speed > 0)) {
            warn(lineNo, "missing_feed");
            speed = opts.defaultFeed;
        }
        if (hasZ && vals.Z !== undefined) penDown = target.z <= penThreshold;

        const kind = rapid ? "rapid" : (penDown ? "draw" : "travel");
        const xyMoved = target.x !== pos.x || target.y !== pos.y || arcLike;   // arcLike: cả vòng tròn đầy
        const timeFor = (length) => (length / speed) * 60;

        if (!xyMoved) {
            // Chỉ đổi Z (nâng/hạ bút).
            const length = Math.abs(target.z - pos.z);
            if (length > 0) {
                push({ kind: "z", x0: pos.x, y0: pos.y, x1: pos.x, y1: pos.y,
                       dur: timeFor(length), line: lineNo, penDown });
            }
        } else if (motion === 2 || motion === 3) {
            features.arcs += 1;
            const radiusWord = vals.R !== undefined ? vals.R * unit : null;
            const hasCenter = vals.I !== undefined || vals.J !== undefined;
            const arc = (radiusWord !== null || hasCenter)
                ? arcPoints(pos, target,
                            { i: (vals.I ?? 0) * unit, j: (vals.J ?? 0) * unit },
                            radiusWord, motion === 2, opts.arcTolerance)
                : { ok: false };
            const pts = arc.ok ? arc.points : [[target.x, target.y]];
            if (!arc.ok) warn(lineNo, "arc_params");
            let px = pos.x, py = pos.y;
            for (const [x, y] of pts) {
                const length = Math.hypot(x - px, y - py);
                push({ kind: penDown ? "draw" : "travel", x0: px, y0: py, x1: x, y1: y,
                       dur: timeFor(length), line: lineNo, penDown });
                px = x; py = y;
            }
        } else {
            const length = Math.hypot(target.x - pos.x, target.y - pos.y, target.z - pos.z);
            push({ kind, x0: pos.x, y0: pos.y, x1: target.x, y1: target.y,
                   dur: timeFor(length), line: lineNo, penDown });
        }

        pos.x = target.x; pos.y = target.y; pos.z = target.z;
    });

    // Thống kê
    let drawLength = 0, travelLength = 0;
    const bboxDraw = emptyBox(), bboxAll = emptyBox();
    for (const s of segments) {
        if (s.kind === "dwell" || s.kind === "z") continue;
        const length = Math.hypot(s.x1 - s.x0, s.y1 - s.y0);
        if (s.kind === "draw") { drawLength += length; extend(bboxDraw, s); }
        else travelLength += length;
        extend(bboxAll, s);
    }

    return {
        lines, lineCount: lines.length, segments, seconds: time,
        drawLength, travelLength, warnings, features,
        bbox: finishBox(bboxDraw), bboxAll: finishBox(bboxAll)
    };
}

function emptyBox() { return { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }; }
function extend(box, s) {
    box.minX = Math.min(box.minX, s.x0, s.x1); box.maxX = Math.max(box.maxX, s.x0, s.x1);
    box.minY = Math.min(box.minY, s.y0, s.y1); box.maxY = Math.max(box.maxY, s.y0, s.y1);
}
function finishBox(box) {
    return box.minX === Infinity ? null
        : { ...box, width: box.maxX - box.minX, height: box.maxY - box.minY };
}

// Vùng bao (cộng độ lệch gốc làm việc) có nằm trong vùng làm việc [0..travel] không?
export function outOfRange(bbox, travelX, travelY, offset = [0, 0, 0], margin = 0.001) {
    if (!bbox) return false;
    const [ox, oy] = offset;
    return bbox.minX + ox < -margin || bbox.minY + oy < -margin ||
           bbox.maxX + ox > travelX + margin || bbox.maxY + oy > travelY + margin;
}

// Vị trí đầu bút tại thời điểm t (giây, theo ước tính). Dùng cho phần xem lại.
export function positionAt(segments, t) {
    if (segments.length === 0) return null;
    let lo = 0, hi = segments.length - 1;
    while (lo < hi) {                       // tìm đoạn cuối cùng có t0 <= t
        const mid = (lo + hi + 1) >> 1;
        if (segments[mid].t0 <= t) lo = mid; else hi = mid - 1;
    }
    const s = segments[lo];
    const f = s.dur > 0 ? Math.min(1, Math.max(0, (t - s.t0) / s.dur)) : 1;
    return {
        index: lo,
        x: s.x0 + (s.x1 - s.x0) * f,
        y: s.y0 + (s.y1 - s.y0) * f,
        penDown: s.kind === "draw" || (s.kind === "z" && s.penDown)
    };
}

export function formatDuration(seconds) {
    if (!Number.isFinite(seconds)) return "—";
    const total = Math.round(seconds);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return h > 0
        ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
        : `${m}:${String(s).padStart(2, "0")}`;
}
