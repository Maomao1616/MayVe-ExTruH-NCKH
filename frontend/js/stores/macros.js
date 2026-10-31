// macros.js — dữ liệu macro dùng chung (Dock đọc/ghi, không import view nào).
// Macro nằm ở MÁY CHỦ (data/macros, mỗi macro một tệp) để mọi trình duyệt thấy cùng một bộ.
// Ở đây giữ một bản sao trong bộ nhớ: `loadMacros()` đọc đồng bộ, `refreshMacros()` tải lại từ máy chủ.
// `validateMacro` là hàm thuần (kiểm nhanh ở trình duyệt); máy chủ vẫn là lớp chặn cuối cùng.
import { api, ApiError } from "../core/api.js";
import { cleanLine } from "../lib/gcode.js";

export const LIMITS = { name: 40, lines: 50, lineLen: 200, count: 30 };
const LEGACY_KEY = "extruxy-macros-v1";      // bản cũ lưu trong trình duyệt: tự chuyển lên máy chủ một lần
const REALTIME = /[?!~\x18]/;

let cache = [];

/* ---------- kiểm tra hợp lệ (thuần) ---------- */
// Trả { ok, errors: [mã], macro: bản đã làm sạch }.
export function validateMacro(input) {
    const errors = [];
    const name = String(input?.name ?? "").trim();
    if (!name || name.length > LIMITS.name) errors.push("name");

    const type = input?.type === "command" || input?.type === "gcode" ? input.type : null;
    if (!type) errors.push("type");

    const rawLines = Array.isArray(input?.lines)
        ? input.lines
        : String(input?.lines ?? "").split(/\r?\n/);
    const lines = rawLines.map((line) => cleanLine(String(line))).filter(Boolean);

    if (lines.length === 0) errors.push("lines_empty");
    if (lines.length > LIMITS.lines) errors.push("lines_too_many");
    if (lines.some((line) => line.length > LIMITS.lineLen)) errors.push("line_too_long");
    if (lines.some((line) => REALTIME.test(line))) errors.push("realtime_char");
    if (type === "gcode" && lines.some((line) => line.startsWith("$"))) errors.push("no_dollar");
    if (type === "command" && lines.length > 1) errors.push("command_one_line");

    return {
        ok: errors.length === 0,
        errors,
        macro: { id: input?.id ?? null, name, type, lines, needsHome: input?.needsHome === true }
    };
}

/* ---------- kho ---------- */
function changed() {
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent("extruxy:macros-changed"));
}

export const loadMacros = () => cache;

// Tải lại từ máy chủ (lỗi mạng: giữ nguyên bản đang có).
export async function refreshMacros() {
    try {
        cache = (await api.macros()).macros;
        if (await migrateLegacy()) cache = (await api.macros()).macros;
    } catch {
        return;
    }
    changed();
}

// Macro cũ trong localStorage -> máy chủ, chỉ khi máy chủ chưa có macro nào. Trả true nếu đã chuyển.
async function migrateLegacy() {
    let legacy = [];
    try {
        const data = JSON.parse(localStorage.getItem(LEGACY_KEY) ?? "null");
        if (data?.version === 1 && Array.isArray(data.macros)) legacy = data.macros;
    } catch { return false; }
    if (legacy.length === 0) return false;
    if (cache.length === 0) {
        for (const item of legacy) {
            const result = validateMacro(item);
            if (result.ok) await api.macroCreate({ ...result.macro, id: undefined });
        }
    }
    try { localStorage.removeItem(LEGACY_KEY); } catch { /* bỏ qua */ }
    return cache.length === 0;
}

// Thêm mới (macro.id rỗng) hoặc cập nhật. Trả Promise<{ ok, errors, macro }>.
export async function saveMacro(input) {
    const result = validateMacro(input);
    if (!result.ok) return { ok: false, errors: result.errors, macro: result.macro };
    const { id, ...body } = result.macro;
    try {
        const saved = id ? await api.macroUpdate(id, body) : await api.macroCreate(body);
        await refreshMacros();
        return { ok: true, errors: [], macro: saved.macro };
    } catch (error) {
        const code = error instanceof ApiError && error.status !== 0 ? error.code : "storage";
        return { ok: false, errors: [code], macro: result.macro };
    }
}

export async function deleteMacro(id) {
    try {
        await api.macroDelete(id);
    } catch {
        return false;
    }
    await refreshMacros();
    return true;
}
