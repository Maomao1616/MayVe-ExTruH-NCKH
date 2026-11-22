// Kiểm views/beta/model.js: node --test frontend/tests/beta.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { clampPage, FIELDS, optionsFromValues, previewDpi, stepZoom, strokesPath, summarize, ZOOMS } from "../js/views/beta/model.js";

test("tùy chọn gửi backend: đúng tên, đúng kiểu, bỏ ô trống và số hỏng", () => {
    const out = optionsFromValues({
        "beta-text-mode": "mixed", "beta-font": "times", "beta-pen": "0.45", "beta-frame": true, "beta-thick": false,
        "beta-skel-thr": "190.4", "beta-mixed-min": "", "beta-fit": "abc"
    }, 3);
    assert.deepEqual(out, { page: 3, text_mode: "mixed", font: "times", pen_mm: 0.45, frame: true, thick_double: false, skeleton_threshold: 190 });
});

test("mọi ô khai báo đều có tên tham số riêng", () => {
    const names = FIELDS.map((f) => f[1]);
    assert.equal(new Set(names).size, names.length);
    assert.equal(new Set(FIELDS.map((f) => f[0])).size, FIELDS.length);
});

test("số trang luôn nằm trong 1..số trang", () => {
    assert.equal(clampPage(0, 5), 1);
    assert.equal(clampPage(9, 5), 5);
    assert.equal(clampPage("3", 5), 3);
    assert.equal(clampPage("x", 5), 1);
    assert.equal(clampPage(2.6, 5), 3);
});

test("strokesPath: bỏ nét dưới 2 điểm, làm tròn 2 chữ số", () => {
    assert.equal(strokesPath([[[0, 0], [1.2345, 2]], [[5, 5]], [[1, 1], [2, 2], [3, 3]]]), "M0 0L1.23 2M1 1L2 2L3 3");
    assert.equal(strokesPath([]), "");
});

test("summarize cộng các lớp và ước thời gian có cả nhấc bút", () => {
    const s = summarize({
        layers: [{ name: "Chữ", color: "#141414", strokes: 1000, draw_mm: 4000, pen_up_mm: 4000 }, { name: "Ảnh", strokes: 200, draw_mm: 0, pen_up_mm: 0 }],
        beta: { text: { chars: 510, fallback: 1, lines: 15 } }
    });
    assert.equal(s.strokes, 1200);
    assert.equal(s.drawMm, 4000);
    assert.equal(s.minutes, Math.round((1200 * 0.25 + (8000 / 8000) * 60) / 60 * 10) / 10);   // 6 phút
    assert.deepEqual([s.chars, s.fallback, s.lines], [510, 1, 15]);
    assert.deepEqual(summarize(null).layers, []);
});

test("zoom: nhảy theo mức cố định, đứng yên ở hai đầu, giá trị lạ về mức gần nhất", () => {
    assert.equal(stepZoom(1, 1), 1.5);
    assert.equal(stepZoom(1, -1), 1);
    assert.equal(stepZoom(ZOOMS[ZOOMS.length - 1], 1), ZOOMS[ZOOMS.length - 1]);
    assert.equal(stepZoom(2.4, 1), 3);
    assert.equal(stepZoom(2.4, -1), 1.5);
});

test("độ phân giải ảnh trang gốc tăng theo zoom nhưng không vượt giới hạn backend", () => {
    assert.equal(previewDpi(1), 70);
    assert.equal(previewDpi(2), 140);
    assert.equal(previewDpi(8), 300);
    assert.equal(previewDpi(0.2), 70);
});
