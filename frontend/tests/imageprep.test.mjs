// Đối chiếu lib/imageprep.js với backend: node --test frontend/tests/imageprep.test.mjs
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { grayFromRgba, halvingSteps, scaledSize, toneMap, workSidePx } from "../js/lib/imageprep.js";

const fixture = (name) => JSON.parse(fs.readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8"));

test("cạnh làm việc khớp raster_in.work_side_px", () => {
    for (const c of fixture("side_cases.json")) {
        const got = workSidePx({ refW: c.ref[0], refH: c.ref[1], width: c.px[0], height: c.px[1], pen: c.pen, override: c.override });
        assert.equal(got, c.side, JSON.stringify(c));
    }
});

test("độ sáng hiển thị khớp tone.darkness (sai lệch tối đa 1 mức)", () => {
    const { gray, rows } = fixture("tone_cases.json");
    for (const row of rows) {
        const got = toneMap(Uint8Array.from(gray), {
            auto: row.raster.auto_levels ?? true, black: row.raster.black_point ?? 0, white: row.raster.white_point ?? 255,
            gamma: row.raster.gamma ?? 1, invert: row.style.invert ?? false
        });
        let worst = 0;
        got.forEach((v, i) => { worst = Math.max(worst, Math.abs(v - row.display[i])); });
        assert.ok(worst <= 1, `${JSON.stringify(row.raster)} lệch ${worst}`);
    }
});

test("kích thước thu nhỏ giữ tỉ lệ và không dưới 2 điểm", () => {
    assert.deepEqual(scaledSize(4000, 3000, 1000), { width: 1000, height: 750 });
    assert.deepEqual(scaledSize(3000, 4000, 866), { width: 650, height: 866 });
    assert.deepEqual(scaledSize(10000, 10, 100), { width: 100, height: 2 });
});

test("thu nhỏ từng bước, mỗi bước tối đa một nửa, bước cuối đúng đích", () => {
    const steps = halvingSteps(6000, 4000, { width: 650, height: 433 });
    assert.deepEqual(steps.at(-1), { width: 650, height: 433 });
    let prev = { width: 6000, height: 4000 };
    for (const s of steps) {
        assert.ok(s.width >= prev.width / 2 - 1 && s.height >= prev.height / 2 - 1);
        prev = s;
    }
    assert.deepEqual(halvingSteps(900, 600, { width: 650, height: 433 }), [{ width: 650, height: 433 }]);
});

test("xám như Pillow, nền trong suốt thành trắng", () => {
    const px = Uint8ClampedArray.from([255, 0, 0, 255, 0, 0, 0, 0, 10, 20, 30, 255]);
    assert.deepEqual([...grayFromRgba(px)], [76, 255, 18]);      // đỏ -> 76; trong suốt -> 255
});
