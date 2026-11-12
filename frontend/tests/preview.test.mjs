// Kiểm views/preview.js phần thuần: makeTransform (mapX / mapY phải khớp toScreen, vì vòng lặp vẽ tệp dùng mapX / mapY
// để khỏi tạo mảng cho từng đoạn). Chạy: node --test frontend/tests/preview.test.mjs
import test from "node:test";
import assert from "node:assert/strict";

globalThis.window ??= { addEventListener() {}, dispatchEvent() {}, matchMedia: () => ({ matches: false, addEventListener() {} }) };
globalThis.document ??= { addEventListener() {}, getElementById: () => null, documentElement: { lang: "vi" } };
globalThis.localStorage ??= { getItem: () => null, setItem() {}, removeItem() {} };

const { makeTransform, createTrail } = await import("../js/views/preview.js");

test("mapX / mapY cho đúng số như toScreen, kể cả khi lật trục và có thu phóng, kéo", () => {
    for (const [flipX, flipY] of [[false, false], [true, false], [false, true], [true, true]]) {
        const T = makeTransform(800, 600, 285, 318, 1.7, 23, -41, flipX, flipY);
        for (const [x, y] of [[0, 0], [285, 318], [120.5, 33.25], [-5, 400]]) {
            const [px, py] = T.toScreen(x, y);
            assert.equal(T.mapX(x), px);
            assert.equal(T.mapY(y), py);
        }
    }
});

test("toWorld là hàm ngược của toScreen", () => {
    const T = makeTransform(640, 480, 285, 318, 2, 10, 5, true, false);
    const [px, py] = T.toScreen(100, 50);
    const [x, y] = T.toWorld(px, py);
    assert.ok(Math.abs(x - 100) < 1e-9 && Math.abs(y - 50) < 1e-9);
});

test("vết bút bỏ điểm quá gần và không vượt giới hạn", () => {
    const trail = createTrail(10, 0.05);
    trail.add(0, 0, true);
    trail.add(0.01, 0, true);                       // dưới minStep: bỏ
    assert.equal(trail.size, 1);
    for (let i = 1; i <= 30; i++) trail.add(i, 0, true);
    assert.ok(trail.size <= 10);
});
