// lib/imageprep.js — chuẩn bị ảnh ngay trong trình duyệt TRƯỚC khi gửi, và xem trước độ sáng.
// Đây chỉ là đường nhanh tùy chọn: backend (Python) vẫn là bản chuẩn và vẫn nhận ảnh gốc nếu hàm ở đây
// báo lỗi hay trả lại tệp gốc. Công thức khớp raster_in.py / tone.py, test đối chiếu từng số
// (tests/imageprep.test.mjs, số chuẩn sinh bằng tests/fixtures/make_image_fixtures.py).

const OVERSAMPLE = 1.3;          // = raster_in.OVERSAMPLE
const MIN_SIDE = 400;
const MAX_SIDE = 4000;
const MAX_PIXELS = 150e6;        // quá lớn: đừng giải mã trong trình duyệt, để backend từ chối nhã nhặn

// Cạnh dài (điểm ảnh) mà backend sẽ dùng để xử lý ảnh w × h nằm gọn trong khung refW × refH mm với bút pen mm.
export function workSidePx({ refW, refH, width, height, pen, override = null }) {
    const s = Math.min(refW / width, refH / height);
    const longMm = Math.max(width * s, height * s);
    const cap = Math.max(width, height, 720);                       // 720 = raster_in.UPSCALE_TO_PX
    const wanted = override || Math.min(MAX_SIDE, Math.max(MIN_SIDE, (longMm / pen) * OVERSAMPLE));
    return Math.floor(Math.max(2, Math.min(cap, wanted)));
}

// Kích thước sau khi đưa cạnh dài về `side` (giữ tỉ lệ).
export function scaledSize(width, height, side) {
    const k = side / Math.max(width, height);
    return { width: Math.max(2, Math.round(width * k)), height: Math.max(2, Math.round(height * k)) };
}

// Các bước thu nhỏ: mỗi bước tối đa còn một nửa (tránh răng cưa), bước cuối ra đúng kích thước đích.
export function halvingSteps(width, height, target) {
    const steps = [];
    let w = width;
    let h = height;
    while (w > target.width * 2 && h > target.height * 2) {
        w = Math.ceil(w / 2);
        h = Math.ceil(h / 2);
        steps.push({ width: w, height: h });
    }
    steps.push({ width: target.width, height: target.height });
    return steps;
}

/* ---------- đọc ảnh bằng trình duyệt ---------- */

let cache = { file: null, image: null };

export function forget() {
    cache = { file: null, image: null };
}

async function decode(file) {
    if (cache.file === file && cache.image) return cache.image;
    const url = URL.createObjectURL(file);
    try {
        const image = new Image();
        image.src = url;
        await image.decode();                       // <img> tự xoay theo EXIF
        cache = { file, image };
        return image;
    } finally {
        URL.revokeObjectURL(url);
    }
}

// Kích thước ảnh thật (đã xoay EXIF) hoặc null nếu trình duyệt không đọc được.
export async function imageSize(file) {
    try {
        const image = await decode(file);
        return { width: image.naturalWidth, height: image.naturalHeight };
    } catch {
        return null;
    }
}

// Trả về tệp để gửi: ảnh đã thu nhỏ (PNG) nếu cần, ngược lại chính tệp gốc.
// Chỉ thu nhỏ, không bao giờ phóng to; mọi lỗi → trả tệp gốc để backend tự lo.
export async function prepareForUpload(file, { box, pen, override = null }) {
    try {
        const image = await decode(file);
        const width = image.naturalWidth;
        const height = image.naturalHeight;
        if (!width || !height || width * height > MAX_PIXELS) return { file, scaled: false };
        const side = workSidePx({ refW: box.w, refH: box.h, width, height, pen, override });
        if (Math.max(width, height) <= side) return { file, scaled: false };

        const target = scaledSize(width, height, side);
        let source = image;
        for (const step of halvingSteps(width, height, target)) {
            const canvas = document.createElement("canvas");
            canvas.width = step.width;
            canvas.height = step.height;
            const ctx = canvas.getContext("2d");
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(source, 0, 0, step.width, step.height);
            source = canvas;
        }
        const blob = await new Promise((resolve) => source.toBlob(resolve, "image/png"));
        if (!blob) return { file, scaled: false };
        const name = `${file.name.replace(/\.[^.]+$/, "")}.png`;
        return { file: new File([blob], name, { type: "image/png" }), scaled: true, from: { width, height }, to: target };
    } catch {
        return { file, scaled: false };
    }
}

/* ---------- xem trước độ sáng (khớp tone.py, không có CLAHE / khử nhiễu) ---------- */

// Điểm xám 0..255 như Pillow convert("L"), nền trong suốt coi là trắng. rgba: Uint8ClampedArray.
export function grayFromRgba(rgba) {
    const out = new Uint8Array(rgba.length / 4);
    for (let i = 0, j = 0; i < rgba.length; i += 4, j++) {
        const a = rgba[i + 3];
        const mix = (c) => (a === 255 ? c : (c * a + 255 * (255 - a)) / 255);
        out[j] = (mix(rgba[i]) * 19595 + mix(rgba[i + 1]) * 38470 + mix(rgba[i + 2]) * 7471 + 32768) >> 16;
    }
    return out;
}

// Phân vị q (0..100) kiểu numpy "linear" trên dữ liệu nguyên 0..255, tính qua histogram.
function percentile(hist, total, q) {
    const kth = (k) => {
        let seen = 0;
        for (let v = 0; v < 256; v++) {
            seen += hist[v];
            if (seen > k) return v;
        }
        return 255;
    };
    const pos = ((total - 1) * q) / 100;
    const lo = Math.floor(pos);
    const hi = Math.min(total - 1, lo + 1);
    const a = kth(lo);
    return a + (pos - lo) * (kth(hi) - a);
}

// settings: { auto, black, white, gamma, invert } → Uint8Array độ sáng hiển thị (255 = trắng giấy).
export function toneMap(gray, { auto = true, black = 0, white = 255, gamma = 1, invert = false } = {}) {
    const hist = new Uint32Array(256);
    for (let i = 0; i < gray.length; i++) hist[gray[i]]++;
    let p1 = 0;
    let scale = 0;
    if (auto) {
        p1 = percentile(hist, gray.length, 1);
        const p99 = percentile(hist, gray.length, 99);
        if (p99 - p1 >= 16) scale = 255 / (p99 - p1);        // ảnh phẳng gần một màu: không kéo giãn
    }
    const lo = black;
    const hi = white <= black ? black + 1 : white;
    const lut = new Uint8Array(256);
    for (let v = 0; v < 256; v++) {
        let g = v;
        if (scale) g = Math.floor(Math.min(255, Math.max(0, (v - p1) * scale)));
        let x = Math.min(1, Math.max(0, (g - lo) / (hi - lo)));
        if (gamma !== 1) x = x ** (1 / gamma);
        const brightness = invert ? 1 - x : x;
        lut[v] = Math.round(255 * brightness);
    }
    const out = new Uint8Array(gray.length);
    for (let i = 0; i < gray.length; i++) out[i] = lut[gray[i]];
    return out;
}
