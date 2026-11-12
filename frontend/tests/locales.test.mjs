// Kiểm tệp dịch: không trùng khóa (JSON.parse nuốt âm thầm, khóa sau đè khóa trước: từng làm tờ hiệu chỉnh tông hiện chữ của
// khối Thang xám), vi / en cùng bộ khóa, mọi khóa data-i18n trong index.html đều có bản dịch.
// Chạy: node --test frontend/tests/locales.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const path = (name) => fileURLToPath(new URL(`../${name}`, import.meta.url));
const read = (name) => readFileSync(path(name), "utf8");

// Khóa ở đầu dòng: "ten.khoa": ...  (tệp dịch của dự án mỗi khóa một dòng)
const keysOf = (text) => [...text.matchAll(/^\s*"([^"\\]+)"\s*:/gm)].map((m) => m[1]);

const LOCALES = { vi: read("locales/vi.json"), en: read("locales/en.json") };

for (const [lang, text] of Object.entries(LOCALES)) {
    test(`${lang}.json không có khóa trùng`, () => {
        const seen = new Set();
        const dup = [];
        for (const key of keysOf(text)) {
            if (seen.has(key)) dup.push(key);
            seen.add(key);
        }
        assert.deepEqual(dup, []);
    });
}

test("vi.json và en.json cùng bộ khóa", () => {
    const vi = new Set(keysOf(LOCALES.vi));
    const en = new Set(keysOf(LOCALES.en));
    assert.deepEqual([...vi].filter((k) => !en.has(k)), [], "có trong vi, thiếu trong en");
    assert.deepEqual([...en].filter((k) => !vi.has(k)), [], "có trong en, thiếu trong vi");
});

test("mọi khóa data-i18n trong index.html đều có bản dịch", () => {
    const vi = JSON.parse(LOCALES.vi);
    const html = read("index.html");
    const missing = new Set();
    for (const match of html.matchAll(/data-i18n="([^"]+)"/g)) {
        for (const part of match[1].split(";")) {
            const key = part.trim().replace(/^\[[^\]]+\]/, "");          // "[title]khóa" → "khóa"
            if (key && !(key in vi)) missing.add(key);
        }
    }
    assert.deepEqual([...missing], []);
});
