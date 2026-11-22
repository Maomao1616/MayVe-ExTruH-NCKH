// lib/subject.js — vùng chủ thể (hàm thuần, có test): hình elip / chữ nhật theo tỷ lệ 0..1 của ảnh gốc.
// Backend: tone.apply_subject (ngoài vùng độ đậm nhân với `outside`). Giao diện kéo thả: views/drawing/subject.js.

export const SHAPES = Object.freeze(["none", "ellipse", "rect", "auto", "free"]);     // auto = backend tự tách; free = vẽ tay (đa giác)
export const FREE_MIN_STEP = 0.004;                                        // khoảng cách tối thiểu giữa hai điểm của một nét tay
export const FREE_MAX_POINTS = 400;                                        // một nét tối đa bấy nhiêu điểm (bớt đều nếu dài hơn)
export const FREE_MAX_SHAPES = 40;
export const MIN_SIZE = 0.05;                                             // cạnh nhỏ nhất của vùng (5 % ảnh)
export const DEFAULT_REGION = Object.freeze({ x: 0.15, y: 0.08, w: 0.7, h: 0.84 });   // khung đặt sẵn: gần cả ảnh, chừa lề

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

// Ép một vùng vào trong ảnh: cạnh ≥ MIN_SIZE, không lòi ra ngoài. Số lạ thì dùng khung mặc định.
export function clampRegion(r) {
    if (!r || ![r.x, r.y, r.w, r.h].every(Number.isFinite)) return { ...DEFAULT_REGION };
    const w = clamp(r.w, MIN_SIZE, 1);
    const h = clamp(r.h, MIN_SIZE, 1);
    return { x: clamp(r.x, 0, 1 - w), y: clamp(r.y, 0, 1 - h), w, h };
}

// Hộp của một lần kéo chuột từ (ax, ay) tới (px, py), mọi số 0..1.
export function boxFromDrag(ax, ay, px, py) {
    return clampRegion({ x: Math.min(ax, px), y: Math.min(ay, py), w: Math.abs(px - ax), h: Math.abs(py - ay) });
}

const round4 = (v) => Math.round(v * 10000) / 10000;

// Tham số gửi kèm nhóm `raster` của POST /api/draw/import. Không chọn hình thì không gửi gì (backend dùng mặc định "none").
// outside: 0..1, phần độ đậm giữ lại ở NGOÀI vùng (1 = không nhạt đi).
// Một nét tay -> đa giác gọn: bỏ điểm quá sát nhau, bớt đều nếu quá dài, kẹp 0..1. Dưới 3 điểm thì bỏ (trả null).
export function simplifyStroke(points) {
    const out = [];
    for (const p of points) {
        if (!Number.isFinite(p?.x) || !Number.isFinite(p?.y)) continue;
        const q = [clamp(p.x, 0, 1), clamp(p.y, 0, 1)];
        const last = out[out.length - 1];
        if (!last || Math.hypot(q[0] - last[0], q[1] - last[1]) >= FREE_MIN_STEP) out.push(q);
    }
    if (out.length < 3) return null;
    if (out.length <= FREE_MAX_POINTS) return out;
    const step = out.length / FREE_MAX_POINTS;
    return Array.from({ length: FREE_MAX_POINTS }, (_, i) => out[Math.floor(i * step)]);
}

export function payloadOf(shape, region, outside) {
    if (!SHAPES.includes(shape) || shape === "none") return {};
    if (shape === "free") {
        const pack = (list) => (Array.isArray(list) ? list : []).slice(0, FREE_MAX_SHAPES).map((poly) => poly.map(([x, y]) => [round4(x), round4(y)]));
        const add = pack(region?.add);
        if (!add.length) return {};
        return {
            subject_shape: "free",
            subject_poly: JSON.stringify({ add, sub: pack(region?.sub) }),
            subject_outside: round4(clamp(Number.isFinite(outside) ? outside : 0.5, 0, 1))
        };
    }
    if (shape === "auto") return { subject_shape: "auto", subject_outside: round4(clamp(Number.isFinite(outside) ? outside : 0.5, 0, 1)) };
    if (!region) return {};
    const r = clampRegion(region);
    return {
        subject_shape: shape,
        subject_x: round4(r.x), subject_y: round4(r.y), subject_w: round4(r.w), subject_h: round4(r.h),
        subject_outside: round4(clamp(Number.isFinite(outside) ? outside : 0.5, 0, 1))
    };
}
