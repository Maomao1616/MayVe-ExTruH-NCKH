// Kiểm lib/subject.js: node --test frontend/tests/subject.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { boxFromDrag, clampRegion, DEFAULT_REGION, MIN_SIZE, payloadOf } from "../js/lib/subject.js";

test("không chọn hình thì không gửi gì; hình lạ cũng vậy", () => {
    assert.deepEqual(payloadOf("none", DEFAULT_REGION, 0.5), {});
    assert.deepEqual(payloadOf("triangle", DEFAULT_REGION, 0.5), {});
    assert.deepEqual(payloadOf("ellipse", null, 0.5), {});
});

test("payload khớp tên tham số backend và làm tròn 4 chữ số", () => {
    assert.deepEqual(payloadOf("rect", { x: 0.123456, y: 0.2, w: 0.5, h: 0.6 }, 0.3), {
        subject_shape: "rect", subject_x: 0.1235, subject_y: 0.2, subject_w: 0.5, subject_h: 0.6, subject_outside: 0.3
    });
});

test("vùng bị ép vào trong ảnh, cạnh không nhỏ hơn mức tối thiểu", () => {
    const r = clampRegion({ x: 0.9, y: -0.2, w: 0.5, h: 0.001 });
    assert.ok(r.x >= 0 && r.x + r.w <= 1 + 1e-9 && r.y >= 0 && r.y + r.h <= 1 + 1e-9);
    assert.ok(r.h >= MIN_SIZE);
    assert.deepEqual(clampRegion({ x: NaN, y: 0, w: 1, h: 1 }), { ...DEFAULT_REGION });
});

test("kéo chuột theo hướng nào cũng ra cùng một hộp", () => {
    const a = boxFromDrag(0.2, 0.3, 0.6, 0.8);
    const b = boxFromDrag(0.6, 0.8, 0.2, 0.3);
    assert.deepEqual(a, b);
    assert.ok(Math.abs(a.x - 0.2) < 1e-9 && Math.abs(a.w - 0.4) < 1e-9 && Math.abs(a.h - 0.5) < 1e-9);
});

test("outside lạ về mặc định 0,5 và bị kẹp trong 0..1", () => {
    assert.equal(payloadOf("ellipse", DEFAULT_REGION, NaN).subject_outside, 0.5);
    assert.equal(payloadOf("ellipse", DEFAULT_REGION, 3).subject_outside, 1);
    assert.equal(payloadOf("ellipse", DEFAULT_REGION, -1).subject_outside, 0);
});
