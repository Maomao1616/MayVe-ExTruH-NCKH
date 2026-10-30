// views/storage.js — Cài đặt → Lưu trữ dữ liệu: XEM (không sửa) nội dung thư mục dữ liệu của máy chủ.
// Cần vì MiniPC không có màn hình để mở thư mục. Ba thư mục cố định: bản thảo, sao lưu cấu hình, macro,
// cộng các tệp lẻ ở gốc. Tải về qua liên kết thường tới GET /api/storage/file (không dùng fetch).
// Hiển thị kiểu cây: lúc đầu chỉ thấy thư mục; mở thư mục nào mới thấy tệp bên trong thư mục đó.
import { api } from "../core/api.js";
import { t } from "../core/i18n.js";
import { formatWhen } from "../lib/drafts.js";

const $ = (id) => document.getElementById(id);
const REFRESH_MS = 20000;

let data = null;
let drawnSignature = "";            // dữ liệu lần vẽ trước: không đổi thì không vẽ lại (giữ vị trí cuộn, đang mở gì giữ nguyên)
const opened = new Set();           // khóa thư mục đang mở: "drafts" hoặc "drafts/20261030-120000-hinh"

export function initStorage() {
    if (!$("storage-areas")) return;
    $("storage-refresh-btn")?.addEventListener("click", load);
    window.addEventListener("extruxy:language-changed", () => { drawnSignature = ""; render(); });
    window.addEventListener("focus", load);
    // Chỉ làm mới khi đang mở tab Cài đặt: tab khác không cần hỏi máy chủ.
    setInterval(() => { if (!document.hidden && !$("panel-settings")?.hidden) load(); }, REFRESH_MS);
    $("tab-settings")?.addEventListener("click", load);
    load();
}

async function load() {
    const status = $("storage-status");
    try {
        data = await api.storage();
        status?.classList.remove("is-error");
        if (status) status.textContent = "";
    } catch {
        if (status) {
            status.textContent = t("settings.storage.error");
            status.classList.add("is-error");
        }
        return;
    }
    render();
}

export function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const fill = (template, vars) => Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, String(v)), template);

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function downloadLink(area, path) {
    const a = el("a", "storage-download", t("settings.storage.download"));
    a.href = `/api/storage/file?area=${encodeURIComponent(area)}&path=${encodeURIComponent(path)}`;
    a.download = "";
    return a;
}

// Một thư mục có thể thu gọn: <details> + tiêu đề (tên, ghi chú, mũi tên) + phần thân.
function folder(key, className, name, note) {
    const details = el("details", `storage-folder ${className}`);
    details.open = opened.has(key);
    details.addEventListener("toggle", () => {
        if (details.open) opened.add(key); else opened.delete(key);
    });
    const summary = el("summary", "storage-summary");
    const chevron = el("span", "drawing-section-chevron", t("common.icon.chevron"));
    chevron.setAttribute("aria-hidden", "true");
    summary.append(el("span", "storage-name", name), el("small", "storage-note", note), chevron);
    const body = el("div", "storage-body");
    details.append(summary, body);
    return { details, body };
}

function fileRow(name, size, modified, areaKey, path) {
    const li = el("li", "storage-file");
    li.append(el("span", "storage-file-name", name), el("span", "storage-meta", formatSize(size)));
    if (modified) li.append(el("span", "storage-meta", formatWhen(modified)));
    if (areaKey) li.append(downloadLink(areaKey, path));
    return li;
}

function entryNode(areaKey, entry) {
    if (entry.kind === "file") {
        return fileRow(entry.name, entry.size, entry.modified, areaKey, entry.name);
    }
    const count = entry.files.length + entry.more;
    const { details, body } = folder(`${areaKey}/${entry.name}`, "storage-subfolder", entry.name,
        `${fill(t("settings.storage.files"), { n: count })} · ${formatSize(entry.size)} · ${formatWhen(entry.modified)}`);
    const list = el("ul", "storage-files");
    for (const file of entry.files) {
        list.append(fileRow(file.name, file.size, null, areaKey, `${entry.name}/${file.name}`));
    }
    if (entry.more > 0) list.append(el("li", "storage-meta", fill(t("settings.storage.more"), { n: entry.more })));
    body.append(list);
    const li = el("li", "storage-entry");
    li.append(details);
    return li;
}

function areaNode(area) {
    const note = area.exists
        ? fill(t("settings.storage.items"), { n: area.count, size: formatSize(area.bytes) })
        : t("settings.storage.missing");
    const { details, body } = folder(area.key, "storage-area", t(`settings.storage.area.${area.key}`), note);
    body.append(el("p", "help-text", t(`settings.storage.areaDesc.${area.key}`)),
        el("p", "storage-path", area.path));
    if (area.count === 0) {
        body.append(el("p", "muted-text", t("settings.storage.empty")));
        return details;
    }
    const list = el("ul", "storage-list");
    for (const entry of area.entries) list.append(entryNode(area.key, entry));
    if (area.more > 0) list.append(el("li", "storage-meta", fill(t("settings.storage.more"), { n: area.more })));
    body.append(list);
    return details;
}

function render() {
    if (!data) return;
    const signature = JSON.stringify(data);
    if (signature === drawnSignature) return;
    drawnSignature = signature;

    const root = $("storage-root");
    if (root) root.textContent = data.root;
    const total = $("storage-total");
    if (total) total.textContent = formatSize(data.areas.reduce((sum, a) => sum + a.bytes, 0));
    $("storage-areas")?.replaceChildren(...data.areas.map(areaNode));

    const loose = $("storage-loose");
    const list = $("storage-loose-list");
    if (loose && list) {
        loose.hidden = data.files.length === 0;
        list.replaceChildren(...data.files.map((file) => fileRow(file.name, file.size, file.modified, null, "")));
    }
}
