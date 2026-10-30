// views/drawing/tonepreview.js — khung "ảnh gốc" của tab Tạo bản vẽ: xem ảnh gốc hoặc ảnh SAU chỉnh sáng
// (tự cân sáng, mức đen/trắng, gamma, đảo) ngay khi kéo ô thông số, không cần hỏi backend.
// Chủ ghi của #original-image-stage. Bản tính chính thức vẫn ở backend (tone.py); đây chỉ để xem trước
// (không có CLAHE / khử nhiễu).
import { grayFromRgba, toneMap } from "../../lib/imageprep.js";

const THUMB_SIDE = 480;

let stage = null;
let toggle = null;
let readSettings = () => ({});
let url = null;
let image = null;                // <img> của ảnh gốc
let gray = null;                 // Uint8Array của bản thu nhỏ
let size = null;
let canvas = null;
let frame = 0;

export function initTonePreview({ stageEl, toggleEl, read }) {
    stage = stageEl;
    toggle = toggleEl;
    readSettings = read;
    toggle?.addEventListener("change", render);
}

export async function setFile(file) {
    if (!stage) return;
    if (url) URL.revokeObjectURL(url);
    url = URL.createObjectURL(file);
    gray = null;
    canvas = null;
    image = document.createElement("img");
    image.alt = file.name;
    image.src = url;
    const isSvg = file.name.toLowerCase().endsWith(".svg");
    if (toggle) toggle.disabled = isSvg;
    stage.replaceChildren(image);
    if (isSvg) return;
    try {
        await image.decode();
        const k = Math.min(1, THUMB_SIDE / Math.max(image.naturalWidth, image.naturalHeight));
        size = { w: Math.max(1, Math.round(image.naturalWidth * k)), h: Math.max(1, Math.round(image.naturalHeight * k)) };
        const scratch = document.createElement("canvas");
        scratch.width = size.w;
        scratch.height = size.h;
        const ctx = scratch.getContext("2d", { willReadFrequently: true });
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(image, 0, 0, size.w, size.h);
        gray = grayFromRgba(ctx.getImageData(0, 0, size.w, size.h).data);
        canvas = document.createElement("canvas");
        canvas.width = size.w;
        canvas.height = size.h;
        canvas.className = "drawing-tone-canvas";
        render();
    } catch {
        gray = null;                                   // không đọc được: cứ để ảnh gốc
    }
}

// Gọi mỗi khi ô sáng/tối đổi (gộp theo khung hình để kéo thanh trượt mượt).
export function refresh() {
    if (frame) return;
    frame = requestAnimationFrame(() => { frame = 0; render(); });
}

function render() {
    if (!stage || !image) return;
    if (!gray || !canvas || toggle?.checked === false) {
        if (stage.firstChild !== image) stage.replaceChildren(image);
        return;
    }
    const pixels = toneMap(gray, readSettings());
    const out = canvas.getContext("2d").createImageData(size.w, size.h);
    for (let i = 0, j = 0; i < pixels.length; i++, j += 4) {
        out.data[j] = out.data[j + 1] = out.data[j + 2] = pixels[i];
        out.data[j + 3] = 255;
    }
    canvas.getContext("2d").putImageData(out, 0, 0);
    if (stage.firstChild !== canvas) stage.replaceChildren(canvas);
}
