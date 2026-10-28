// macros.js — dữ liệu macro dùng chung (Dock đọc/ghi, không import view nào).
// Hàm thuần + kho localStorage. Muốn đổi nơi lưu (backend, flash) chỉ sửa readAll/writeAll.
import { cleanLine } from "./gcode.js";

export const LIMITS = { name: 40, lines: 50, lineLen: 200, count: 30 };
const STORAGE_KEY = "extruxy-macros-v1";
const REALTIME = /[?!~\x18]/;

/* ---------- kiểm tra hợp lệ (thuần) ---------- */
// Trả { ok, errors: [mã], macro: bản đã làm sạch }. Backend vẫn là lớp chặn cuối.
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

export function newId() {
    return `m_${Math.random().toString(36).slice(2, 8)}`;
}

/* ---------- kho lưu (localStorage) ---------- */
function readAll() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return [];
        const data = JSON.parse(raw);
        if (data?.version !== 1 || !Array.isArray(data.macros)) return [];
        return data.macros
            .map(validateMacro)
            .filter((result) => result.ok)
            .map((result) => ({ ...result.macro, id: result.macro.id ?? newId() }));
    } catch {
        return [];   // dữ liệu hỏng hoặc bị chặn: coi như chưa có macro
    }
}

function writeAll(list) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, macros: list }));
    } catch {
        return false;
    }
    if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("extruxy:macros-changed"));
    }
    return true;
}

export const loadMacros = readAll;

// Thêm mới (macro.id rỗng) hoặc cập nhật (theo id). Trả { ok, errors, macro }.
export function saveMacro(input) {
    const result = validateMacro(input);
    const list = readAll();
    const errors = [...result.errors];
    const id = result.macro.id;

    const taken = list.some(
        (item) => item.id !== id && item.name.toLowerCase() === result.macro.name.toLowerCase()
    );
    if (taken) errors.push("name_taken");
    if (!id && list.length >= LIMITS.count) errors.push("too_many");
    if (errors.length) return { ok: false, errors, macro: result.macro };

    const macro = { ...result.macro, id: id ?? newId() };
    const index = list.findIndex((item) => item.id === macro.id);
    if (index >= 0) list[index] = macro; else list.push(macro);
    if (!writeAll(list)) return { ok: false, errors: ["storage"], macro };
    return { ok: true, errors: [], macro };
}

export function deleteMacro(id) {
    return writeAll(readAll().filter((item) => item.id !== id));
}
