// paper.js — bố trí bản vẽ trên tờ giấy. THUẦN (không DOM, không mạng).
// Là bản JS của backend/app/services/drawing/layout.py (rotate_layers + plan + Placement.map) để canvas kéo
// thả mượt mà không gọi mạng. Backend vẫn là nơi quyết định: POST /api/draw/gcode trả `box` và `paper`.
// frontend/tests/paper.test.mjs đối chiếu từng số với backend; sửa một bên phải sửa bên kia.
//
// Quy ước: mm, gốc trên trái, Y xuống. Tờ giấy neo ở gốc máy O(0,0) (dịch được bằng paperX/paperY).

export const EPS = 1e-6;

export const ROTATIONS = [0, 90, 180, 270];

// Kích thước nguồn sau khi xoay (xoay 90/270 đổi chỗ rộng và cao).
export function rotatedSize(src, rotate) {
    return rotate === 90 || rotate === 270 ? { w: src.h, h: src.w } : { w: src.w, h: src.h };
}

// Phần trong lề của tờ giấy.
export function innerArea(paper, margin) {
    return { x: paper.x + margin, y: paper.y + margin, w: paper.w - 2 * margin, h: paper.h - 2 * margin };
}

// Khung vẽ vừa khít phần trong lề, giữ tỷ lệ nội dung (contain) — kích thước ban đầu khi nạp bản vẽ mới.
export function fitBox(src, rotate, inner) {
    const r = rotatedSize(src, rotate);
    if (r.w <= EPS && r.h <= EPS) return { w: inner.w, h: inner.h };
    const rx = r.w > EPS ? inner.w / r.w : Infinity;
    const ry = r.h > EPS ? inner.h / r.h : Infinity;
    const s = Math.min(rx, ry);
    return { w: r.w * s, h: r.h * s };
}

// layout: { paperW, paperH, paperX, paperY, margin, width, height (null = lấp đầy), fit: "contain"|"stretch",
//           center, offsetX, offsetY, flipX, flipY, rotate }; machine: { workW, workH }
// Trả { ok: true, ... } hoặc { ok: false, code } với code trùng mã lỗi của backend.
export function plan(src, layout, machine) {
    const rotate = layout.rotate ?? 0;
    const rs = rotatedSize(src, rotate);
    const paper = { x: layout.paperX ?? 0, y: layout.paperY ?? 0, w: layout.paperW, h: layout.paperH };
    if (paper.x + paper.w > machine.workW + EPS || paper.y + paper.h > machine.workH + EPS) {
        return { ok: false, code: "paper_out_of_area" };
    }
    const m = layout.margin;
    const inner = innerArea(paper, m);
    if (inner.w <= EPS || inner.h <= EPS) return { ok: false, code: "bad_param" };
    const w = layout.width ?? inner.w;
    const h = layout.height ?? inner.h;
    const bx = layout.center ? inner.x + (inner.w - w) / 2 : inner.x + layout.offsetX;
    const by = layout.center ? inner.y + (inner.h - h) / 2 : inner.y + layout.offsetY;
    if (w > inner.w + EPS || h > inner.h + EPS || bx < inner.x - EPS || by < inner.y - EPS ||
        bx + w > inner.x + inner.w + EPS || by + h > inner.y + inner.h + EPS) {
        return { ok: false, code: "box_out_of_paper", paper, inner, box: { x: bx, y: by, w, h } };
    }
    if (rs.w <= EPS && rs.h <= EPS) return { ok: false, code: "empty_drawing" };
    const rx = rs.w > EPS ? w / rs.w : null;
    const ry = rs.h > EPS ? h / rs.h : null;
    let sx, sy;
    if (layout.fit === "stretch") {
        sx = rx ?? 1;
        sy = ry ?? 1;
    } else {
        sx = sy = Math.min(...[rx, ry].filter((v) => v !== null));
    }
    return {
        ok: true, src, rotate, rs, paper, inner,
        box: { x: bx, y: by, w, h },
        sx, sy,
        ox: bx + (w - rs.w * sx) / 2,
        oy: by + (h - rs.h * sy) / 2,
        flipX: !!layout.flipX, flipY: !!layout.flipY
    };
}

// Xoay thuận chiều kim đồng hồ (Y xuống) quanh góc trên trái của hộp nguồn — như layout.rotate_layers.
function turn(src, rotate, x, y) {
    const u = x - src.x;
    const v = y - src.y;
    if (rotate === 90) return [src.x + (src.h - v), src.y + u];
    if (rotate === 180) return [src.x + (src.w - u), src.y + (src.h - v)];
    if (rotate === 270) return [src.x + v, src.y + (src.w - u)];
    return [x, y];
}

// Điểm nguồn -> điểm trên máy (như Placement.map sau rotate_layers).
export function mapPoint(pl, x, y) {
    const [rx, ry] = turn(pl.src, pl.rotate, x, y);
    let nx = pl.ox + (rx - pl.src.x) * pl.sx;
    let ny = pl.oy + (ry - pl.src.y) * pl.sy;
    if (pl.flipX) nx = 2 * (pl.box.x + pl.box.w / 2) - nx;
    if (pl.flipY) ny = 2 * (pl.box.y + pl.box.h / 2) - ny;
    return [nx, ny];
}

// Cùng phép biến đổi dưới dạng ma trận [a, b, c, d, e, f] của canvas (x' = a·x + c·y + e, y' = b·x + d·y + f),
// để vẽ một Path2D nguồn bằng ctx.transform thay vì ánh xạ từng điểm.
export function matrix(pl) {
    // thử ba điểm: gốc, +x, +y — phép biến đổi là affine nên đủ xác định ma trận
    const [x0, y0] = mapPoint(pl, 0, 0);
    const [x1, y1] = mapPoint(pl, 1, 0);
    const [x2, y2] = mapPoint(pl, 0, 1);
    return [x1 - x0, y1 - y0, x2 - x0, y2 - y0, x0, y0];
}

// Tỷ lệ dài trung bình của phép biến đổi (để đổi độ rộng bút mm sang đơn vị nguồn khi vẽ).
export function meanScale(pl) {
    return Math.sqrt(Math.abs(pl.sx * pl.sy));
}
