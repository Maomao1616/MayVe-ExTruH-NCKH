// Kiểm lib/subject.js: node --test frontend/tests/subject.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { boxFromDrag, clampRegion, DEFAULT_REGION, FREE_MAX_POINTS, MIN_SIZE, payloadOf, simplifyStroke } from "../js/lib/subject.js";

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

test("tự tách (auto) chỉ gửi hình và độ nhạt nền, không cần vùng", () => {
    assert.deepEqual(payloadOf("auto", null, 0.25), { subject_shape: "auto", subject_outside: 0.25 });
    assert.equal(payloadOf("auto", null, 3).subject_outside, 1);
    assert.equal(payloadOf("auto", null, NaN).subject_outside, 0.5);
});


test("vẽ tay (free): gửi đa giác dạng JSON, không có nét thêm thì không gửi gì", () => {
    const square = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]];
    const out = payloadOf("free", { add: [square], sub: [] }, 0.25);
    assert.equal(out.subject_shape, "free");
    assert.equal(out.subject_outside, 0.25);
    assert.deepEqual(JSON.parse(out.subject_poly), { add: [square], sub: [] });
    assert.deepEqual(payloadOf("free", { add: [], sub: [square] }, 0.25), {});
    assert.deepEqual(payloadOf("free", null, 0.25), {});
});

test("simplifyStroke bỏ điểm sát nhau, kẹp 0..1, bỏ nét dưới 3 điểm và bớt nét quá dài", () => {
    assert.equal(simplifyStroke([{ x: 0.1, y: 0.1 }, { x: 0.1005, y: 0.1 }, { x: 0.5, y: 0.5 }]), null);
    const poly = simplifyStroke([{ x: -1, y: 0.2 }, { x: 0.5, y: 0.2 }, { x: 2, y: 0.9 }]);
    assert.deepEqual(poly, [[0, 0.2], [0.5, 0.2], [1, 0.9]]);
    const long = Array.from({ length: 2000 }, (_, i) => ({ x: i / 2000, y: (i % 2) * 0.5 }));
    assert.ok(simplifyStroke(long).length <= FREE_MAX_POINTS);
});
