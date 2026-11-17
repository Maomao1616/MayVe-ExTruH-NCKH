// Kiểm lib/notify.js (phần thuần): node --test frontend/tests/notify.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { flashTitle, notifyJob, playTones, tonePlan } from "../js/lib/notify.js";

test("xong: ba nốt đi lên; lỗi: nốt trầm lặp, khác hẳn tiếng xong", () => {
    const done = tonePlan("done");
    assert.equal(done.length, 3);
    assert.ok(done[0].hz < done[1].hz && done[1].hz < done[2].hz);
    const failed = tonePlan("failed");
    assert.ok(failed.length >= 4 && failed.every((n) => n.hz < done[0].hz));
});

test("hủy hoặc trạng thái khác không kêu", () => {
    for (const kind of ["cancelled", "running", "queued", undefined]) assert.deepEqual(tonePlan(kind), []);
});

test("không có trình duyệt (node) thì các hàm báo không ném lỗi", () => {
    assert.doesNotThrow(() => playTones(tonePlan("done")));
    assert.doesNotThrow(() => flashTitle("x"));
    assert.doesNotThrow(() => notifyJob("done", "x"));
    assert.doesNotThrow(() => notifyJob("failed", "x", { sound: false }));
});
