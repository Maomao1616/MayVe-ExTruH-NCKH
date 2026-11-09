// Kiểm lib/chart.js (vạch trục, tìm cột theo thời gian, bảng so sánh). Chạy: node --test frontend/tests/chart.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { niceTicks, indexAt, summaryRows } from "../js/lib/chart.js";

test("niceTicks chọn bước 1/2/5 và bao trùm khoảng dữ liệu", () => {
    assert.deepEqual(niceTicks(0, 97, 5), { min: 0, max: 100, ticks: [0, 20, 40, 60, 80, 100] });
    const t = niceTicks(0, 6000, 4);
    assert.equal(t.min, 0); assert.equal(t.max, 6000); assert.deepEqual(t.ticks, [0, 2000, 4000, 6000]);
    const flat = niceTicks(5, 5);                     // dữ liệu phẳng không chia cho 0
    assert.ok(flat.min < 5 && flat.max > 5 && flat.ticks.length >= 2);
    assert.deepEqual(niceTicks(NaN, 1).ticks, [0, 1]);
});

test("indexAt tìm cột gần nhất, chịu danh sách rỗng", () => {
    const t = [0, 1, 2, 4];
    assert.equal(indexAt(t, -3), 0);
    assert.equal(indexAt(t, 1.4), 1);
    assert.equal(indexAt(t, 1.6), 2);
    assert.equal(indexAt(t, 3.1), 3);
    assert.equal(indexAt(t, 99), 3);
    assert.equal(indexAt([], 1), -1);
});

const run = (elapsed, est, rapids, extra = {}) => ({
    meta: { elapsed_s: elapsed, client: { est_seconds: est, rapids, draw_mm: 1000, travel_mm: 400 } },
    summary: { run_pct: 90, pen_down_pct: 60, feed_drawing_avg: 5000, starved_pct: 2, ...extra }
});

test("summaryRows: một lần chạy thì chỉ có A; hai lần thì có delta % và nhận xét tốt / xấu", () => {
    const only = summaryRows(run(100, 80, 50));
    assert.equal(only.find((r) => r.key === "elapsed_s").a, 100);
    assert.equal(only.find((r) => r.key === "elapsed_s").b, null);
    assert.equal(only.find((r) => r.key === "est_ratio").a, 1.25);

    const rows = summaryRows(run(100, 80, 50), run(80, 80, 40, { feed_drawing_avg: 4000, starved_pct: 2 }));
    const by = Object.fromEntries(rows.map((r) => [r.key, r]));
    assert.equal(by.elapsed_s.delta, -20);  assert.equal(by.elapsed_s.verdict, "better");    // nhanh hơn
    assert.equal(by.rapids.delta, -20);     assert.equal(by.rapids.verdict, "better");       // ít nhấc bút hơn
    assert.equal(by.feed_drawing_avg.delta, -20); assert.equal(by.feed_drawing_avg.verdict, "worse"); // chậm hơn
    assert.equal(by.starved_pct.verdict, "same");
    assert.equal(by.draw_mm.verdict, null);                                                   // chỉ so sánh, không đánh giá
});

test("summaryRows chịu thiếu số liệu (máy không gửi Bf, không có ước tính)", () => {
    const bare = { meta: { elapsed_s: 10, client: {} }, summary: { run_pct: 50 } };
    const rows = summaryRows(bare, bare);
    const by = Object.fromEntries(rows.map((r) => [r.key, r]));
    assert.equal(by.starved_pct.a, null); assert.equal(by.starved_pct.delta, null);
    assert.equal(by.est_ratio.a, null);
    assert.equal(by.elapsed_s.delta, 0); assert.equal(by.elapsed_s.verdict, "same");
});
