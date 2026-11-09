// lib/chart.js — phần THUẦN của biểu đồ số liệu chạy máy (không DOM, không mạng): chia vạch trục, bảng so sánh hai lần chạy.
// Dữ liệu vào là kết quả GET /api/joblogs/{id} (backend/app/services/joblog.py). Kiểm thử: frontend/tests/chart.test.mjs.

// Vạch "tròn" cho trục: trả { min, max, ticks } bao trùm [lo, hi] với khoảng 1 / 2 / 5 × 10^k.
export function niceTicks(lo, hi, count = 5) {
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) return { min: 0, max: 1, ticks: [0, 1] };
    if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
    const raw = (hi - lo) / Math.max(1, count);
    const pow = 10 ** Math.floor(Math.log10(raw));
    const frac = raw / pow;
    const step = (frac <= 1 ? 1 : frac <= 2 ? 2 : frac <= 5 ? 5 : 10) * pow;
    const min = Math.floor(lo / step) * step;
    const max = Math.ceil(hi / step) * step;
    const ticks = [];
    for (let v = min; v <= max + step * 1e-6; v += step) ticks.push(Number(v.toFixed(10)));
    return { min, max, ticks };
}

// Chỉ số cột gần giây `t` nhất (t tăng dần), hoặc -1 nếu rỗng.
export function indexAt(times, t) {
    if (!times?.length) return -1;
    let lo = 0, hi = times.length - 1;
    while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (times[mid] < t) lo = mid + 1; else hi = mid;
    }
    return lo > 0 && Math.abs(times[lo - 1] - t) <= Math.abs(times[lo] - t) ? lo - 1 : lo;
}

// Các dòng bảng tóm tắt. `better`: "low" = số nhỏ hơn là tốt hơn, "high" = lớn hơn tốt hơn, null = chỉ so sánh.
export const SUMMARY_ROWS = [
    { key: "elapsed_s", unit: "s", better: "low", get: (d) => d.meta?.elapsed_s ?? d.summary?.duration_s },
    { key: "est_seconds", unit: "s", better: null, get: (d) => d.meta?.client?.est_seconds },
    { key: "est_ratio", unit: "×", better: null, digits: 2,
      get: (d) => ratio(d.meta?.elapsed_s ?? d.summary?.duration_s, d.meta?.client?.est_seconds) },
    { key: "rapids", unit: "", better: "low", get: (d) => d.meta?.client?.rapids },
    { key: "draw_mm", unit: "mm", better: null, digits: 0, get: (d) => d.meta?.client?.draw_mm },
    { key: "travel_mm", unit: "mm", better: "low", digits: 0, get: (d) => d.meta?.client?.travel_mm },
    { key: "run_pct", unit: "%", better: "high", digits: 1, get: (d) => d.summary?.run_pct },
    { key: "pen_down_pct", unit: "%", better: "high", digits: 1, get: (d) => d.summary?.pen_down_pct },
    { key: "feed_drawing_avg", unit: "mm/min", better: "high", digits: 0, get: (d) => d.summary?.feed_drawing_avg },
    { key: "feed_max", unit: "mm/min", better: null, digits: 0, get: (d) => d.summary?.feed_max },
    { key: "starved_pct", unit: "%", better: "low", digits: 1, get: (d) => d.summary?.starved_pct }
];

function ratio(a, b) {
    return Number.isFinite(a) && Number.isFinite(b) && b > 0 ? a / b : null;
}

// Bảng so sánh: [{ key, unit, digits, a, b, delta (% so với A, null nếu thiếu), verdict: "better"|"worse"|"same"|null }]
export function summaryRows(a, b = null) {
    return SUMMARY_ROWS.map((row) => {
        const va = num(row.get(a));
        const vb = b ? num(row.get(b)) : null;
        let delta = null;
        let verdict = null;
        if (va !== null && vb !== null) {
            delta = va === 0 ? (vb === 0 ? 0 : null) : ((vb - va) / Math.abs(va)) * 100;
            if (row.better && delta !== null) {
                verdict = Math.abs(delta) < 1 ? "same"
                    : (row.better === "low") === (vb < va) ? "better" : "worse";
            }
        }
        return { key: row.key, unit: row.unit, digits: row.digits ?? (row.unit === "s" ? 1 : 0), a: va, b: vb, delta, verdict };
    });
}

const num = (value) => (Number.isFinite(value) ? value : null);
