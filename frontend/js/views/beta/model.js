// views/beta/model.js — hàm thuần của tab Beta (có test: frontend/tests/beta.test.mjs). Không đụng DOM, không gọi mạng.
// Tên tham số khớp backend services/beta_pdf/options.py (GET /api/beta/pdf/schema).

export const LIFT_SECONDS = 0.25;              // thời gian mỗi lần nhấc + hạ bút (cấu hình máy hiện tại, docs/02)
export const DRAW_FEED = 8000;                  // mm/phút (core/config.js MACHINE)

// [id ô, tên tham số backend, kiểu]. Kiểu: "str" | "num" | "int" | "bool".
export const FIELDS = Object.freeze([
    ["beta-text-mode", "text_mode", "str"],
    ["beta-font", "font", "str"],
    ["beta-mixed-min", "mixed_min_pt", "num"],
    ["beta-pen", "pen_mm", "num"],
    ["beta-frame", "frame", "bool"],
    ["beta-thick", "thick_double", "bool"],
    ["beta-images", "images", "bool"],
    ["beta-image-kind", "image_kind", "str"],
    ["beta-image-pen", "image_pen_mm", "num"],
    ["beta-lineart-text", "lineart_with_text", "bool"],
    ["beta-image-dpi", "image_dpi", "num"],
    ["beta-skel-dpi", "skeleton_dpi", "num"],
    ["beta-skel-thr", "skeleton_threshold", "int"],
    ["beta-join", "join_mm", "num"],
    ["beta-fit", "glyph_fit", "num"]
]);

// Giá trị các ô (id -> chuỗi hoặc boolean) -> tùy chọn gửi backend. Ô trống hoặc không phải số thì bỏ qua (backend dùng mặc định).
export function optionsFromValues(values, page) {
    const out = { page: clampPage(page, Number.MAX_SAFE_INTEGER) };
    for (const [id, name, kind] of FIELDS) {
        const raw = values[id];
        if (raw === undefined || raw === null || raw === "") continue;
        if (kind === "bool") out[name] = Boolean(raw);
        else if (kind === "str") out[name] = String(raw);
        else {
            const n = Number(raw);
            if (!Number.isFinite(n)) continue;
            out[name] = kind === "int" ? Math.round(n) : n;
        }
    }
    return out;
}

// Zoom của hai khung xem trước (trang gốc và nét sinh ra): các mức cố định, ảnh trang gốc tải lại ở độ phân giải đủ nét theo mức zoom.
export const ZOOMS = Object.freeze([1, 1.5, 2, 3, 4, 6, 8]);
export const BASE_PREVIEW_DPI = 70;
export const MAX_PREVIEW_DPI = 300;                       // khớp giới hạn backend (api/beta_pdf.py)

// Mức zoom kế tiếp theo hướng (+1 phóng, −1 thu); đứng yên ở hai đầu. Giá trị lạ thì về mức gần nhất.
export function stepZoom(current, direction) {
    let i = 0;
    for (let k = 0; k < ZOOMS.length; k++) if (Math.abs(ZOOMS[k] - current) < Math.abs(ZOOMS[i] - current)) i = k;
    return ZOOMS[Math.min(ZOOMS.length - 1, Math.max(0, i + Math.sign(direction)))];
}

export const previewDpi = (zoom) => Math.round(Math.min(MAX_PREVIEW_DPI, Math.max(BASE_PREVIEW_DPI, BASE_PREVIEW_DPI * zoom)));

export const clampPage = (value, pages) => {
    const n = Math.round(Number(value));
    if (!Number.isFinite(n)) return 1;
    return Math.min(Math.max(1, n), Math.max(1, pages));
};

// "M x y L x y …" cho một lớp nét (tọa độ mm). Bỏ nét dưới 2 điểm; làm tròn 2 chữ số để SVG gọn.
export function strokesPath(strokes) {
    const r = (v) => Math.round(v * 100) / 100;
    let d = "";
    for (const s of strokes) {
        if (!Array.isArray(s) || s.length < 2) continue;
        d += `M${r(s[0][0])} ${r(s[0][1])}`;
        for (let i = 1; i < s.length; i++) d += `L${r(s[i][0])} ${r(s[i][1])}`;
    }
    return d;
}

// Số liệu hiển thị từ `source` (kết quả backend): số nét, độ dài, ước thời gian vẽ (cộng nhấc bút).
export function summarize(source) {
    const layers = source?.layers ?? [];
    const sum = (key) => layers.reduce((a, l) => a + (Number(l[key]) || 0), 0);
    const strokes = sum("strokes");
    const drawMm = sum("draw_mm");
    const travelMm = sum("pen_up_mm");
    const seconds = strokes * LIFT_SECONDS + ((drawMm + travelMm) / DRAW_FEED) * 60;
    const text = source?.beta?.text ?? {};
    return {
        strokes, drawMm, travelMm, minutes: Math.round(seconds / 60 * 10) / 10,
        layers: layers.map((l) => ({ name: l.name, color: l.color, strokes: l.strokes })),
        chars: text.chars ?? 0, fallback: text.fallback ?? 0, lines: text.lines ?? 0
    };
}
