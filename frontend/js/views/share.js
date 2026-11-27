// views/share.js — nút QR trên header: hiện địa chỉ để mở giao diện từ máy khác (mạng nhà và/hoặc Internet) kèm mã QR.
// Địa chỉ do launcher đặt (docs/07); ở đây chỉ lấy từ GET /api/share và vẽ.
// Chủ ghi DUY NHẤT của: #share-btn, #share-dialog, #share-list.
import { api } from "../core/api.js";
import { t } from "../core/i18n.js";

const $ = (id) => document.getElementById(id);
const CELL_PX = 6;           // mỗi ô QR vẽ 6 điểm ảnh
const QUIET = 4;             // viền trắng quanh mã (ô), chuẩn QR

export function initShare() {
    const dialog = $("share-dialog");
    if (!dialog || typeof dialog.showModal !== "function") return;
    $("share-btn")?.addEventListener("click", open);
    $("share-close-btn")?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });   // bấm nền để đóng
}

async function open() {
    const list = $("share-list");
    if ($("share-dialog").open) return;
    list.replaceChildren();
    $("share-dialog").showModal();
    try {
        const { items } = await api.share();
        if (!items.length) { list.append(line(t("share.none"), "share-none")); return; }
        for (const item of items) if (Array.isArray(item.qr)) list.append(card(item));
    } catch {
        list.append(line(t("share.error"), "share-none"));
    }
}

function line(text, cls) {
    const p = document.createElement("p");
    p.className = cls;
    p.textContent = text;
    return p;
}

function card({ kind, url, qr }) {
    const box = document.createElement("div");
    box.className = "share-card";
    const frame = document.createElement("div");
    frame.className = "share-frame";
    frame.append(canvas(qr));
    box.append(line(t(kind === "public" ? "share.public" : "share.lan"), "share-kind"), frame);
    const link = document.createElement("a");
    link.href = url;
    link.textContent = url;
    link.target = "_blank";
    link.rel = "noopener";
    link.className = "share-url";
    box.append(link);
    return box;
}

// Luôn đen trên nền trắng (không theo giao diện sáng / tối) để điện thoại quét được.
function canvas(rows) {
    const n = rows.length;
    const size = (n + 2 * QUIET) * CELL_PX;
    const c = document.createElement("canvas");
    c.width = c.height = size;
    c.className = "share-qr";
    c.setAttribute("role", "img");
    const g = c.getContext("2d");
    g.fillStyle = "#fff";
    g.fillRect(0, 0, size, size);
    g.fillStyle = "#000";
    rows.forEach((row, y) => {
        for (let x = 0; x < row.length; x++) if (row[x] === "1") g.fillRect((x + QUIET) * CELL_PX, (y + QUIET) * CELL_PX, CELL_PX, CELL_PX);
    });
    return c;
}
