// Số lăn: chỉ chữ số phần nguyên đổi mới lăn, hướng theo tăng / giảm. node --test frontend/tests/odometer.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { changedDigits } from "../js/lib/odometer.js";

test("chữ số phần nguyên đổi thì lăn, hướng theo tăng / giảm", () => {
    assert.deepEqual(changedDigits("12.345", "13.345"), [{ index: 1, dir: 1 }]);
    assert.deepEqual(changedDigits("12.345", "02.345"), [{ index: 0, dir: -1 }]);
    assert.deepEqual(changedDigits("29.000", "30.000"), [{ index: 0, dir: 1 }, { index: 1, dir: -1 }]);
});

test("phần sau dấu chấm không lăn (đổi quá nhanh)", () => {
    assert.deepEqual(changedDigits("12.345", "12.399"), []);
    assert.deepEqual(changedDigits("12.345", "12.145"), []);
});

test("không so được thì không lăn: khác độ dài, dấu, chuỗi cũ không phải chữ", () => {
    assert.deepEqual(changedDigits("9.999", "10.000"), []);
    assert.deepEqual(changedDigits("—", "1.000"), []);
    assert.deepEqual(changedDigits(undefined, "1.000"), []);
    assert.deepEqual(changedDigits("-1.000", "+1.000"), []);      // ký tự không phải chữ số bỏ qua
});

test("không đổi thì không lăn", () => {
    assert.deepEqual(changedDigits("100.000", "100.000"), []);
});
