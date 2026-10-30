// Kiểm lib/gcode.js (bộ đọc G-code quyết định xem trước + cảnh báo). Chạy: node --test frontend/tests/gcode.test.mjs
// Số kỳ vọng tính tay từ hình học (không chép từ kết quả chạy).
import test from "node:test";
import assert from "node:assert/strict";
import { cleanLine, parseGcode, outOfRange, positionAt, formatDuration } from "../js/lib/gcode.js";

const OPTS = { penUpZ: 5, penDownZ: 0, rapidFeed: 6000 };
const near = (actual, expected, tol = 0.01) =>
    assert.ok(Math.abs(actual - expected) <= tol, `${actual} khác ${expected} quá ${tol}`);
const parse = (lines, opts = OPTS) => parseGcode(lines.join("\n"), opts);

test("cleanLine bỏ chú thích, dòng trống và gọn khoảng trắng như backend", () => {
    assert.equal(cleanLine("G1   X1  Y2 (move) F100 ; ghi chú"), "G1 X1 Y2 F100");
    assert.equal(cleanLine("  ; chỉ chú thích"), "");
    assert.equal(cleanLine("%"), "");
    assert.equal(cleanLine(""), "");
});

test("một nét có bút: phân loại rapid / z / draw, vùng bao và thời gian", () => {
    const p = parse(["G90 G21", "G1 Z5 F3000", "G0 X10 Y10", "G1 Z0", "G1 X20 Y10 F1500", "G1 X20 Y20", "G1 Z5"]);
    assert.equal(p.lineCount, 7);
    assert.deepEqual(p.segments.map((s) => s.kind), ["rapid", "z", "draw", "draw", "z"]);
    near(p.drawLength, 20);
    near(p.travelLength, 14.142);                  // G0 tính vào quãng đường không vẽ (kind = rapid)
    assert.equal(p.bbox.minX, 10); assert.equal(p.bbox.maxX, 20);
    assert.equal(p.bbox.minY, 10); assert.equal(p.bbox.maxY, 20);
    // G0 14,142 mm @6000 + Z xuống 5 mm @3000 + 2 × 10 mm @1500 + Z lên 5 mm @1500 (F là modal: dòng cuối không ghi F)
    near(p.seconds, 14.142 / 6000 * 60 + 5 / 3000 * 60 + 2 * (10 / 1500 * 60) + 5 / 1500 * 60);
    assert.equal(p.warnings.length, 0);
});

test("chỉ số dòng của đoạn khớp thứ tự dòng thực sự gửi (bỏ dòng trống, chú thích)", () => {
    const p = parse(["; đầu", "G90", "", "(x)", "G1 X5 F100", "G1 X9"]);
    assert.deepEqual(p.lines, ["G90", "G1 X5 F100", "G1 X9"]);
    assert.deepEqual(p.segments.map((s) => s.seq), [2, 3]);       // seq tính theo dòng đã làm sạch (1-based)
    assert.deepEqual(p.segments.map((s) => s.line), [5, 6]);      // line = số dòng trong tệp gốc
});

test("G1 Z có dưới nửa hành trình bút là bút xuống; G1 XY khi bút lên là travel", () => {
    const p = parse(["G90", "G1 Z5 F3000", "G1 X10 Y0", "G1 Z0", "G1 X20 Y0", "G1 Z5", "G1 X30 Y0"]);
    const kinds = p.segments.map((s) => s.kind);
    assert.deepEqual(kinds, ["travel", "z", "draw", "z", "travel"]);
    near(p.drawLength, 10); near(p.travelLength, 20);
});

test("tệp không có Z: mọi G1 là nét vẽ", () => {
    const p = parse(["G90", "G0 X0 Y0", "G1 X10 F600", "G1 Y10"]);
    assert.equal(p.features.hasZ, false);
    near(p.drawLength, 20);
});

test("G91 cộng dồn tương đối; G20 đổi inch sang mm", () => {
    const rel = parse(["G91", "G1 X5 F100", "G1 X5", "G1 Y-3"]);
    assert.equal(rel.bbox.maxX, 10); assert.equal(rel.bbox.minY, -3);
    const inch = parse(["G20", "G1 X1 F10"]);
    near(inch.drawLength, 25.4);
    near(inch.seconds, 25.4 / (10 * 25.4) * 60);            // F tính theo inch/phút -> 254 mm/phút
});

test("M30 kết thúc chương trình: dòng sau không được gửi, không được vẽ", () => {
    const p = parse(["G1 X5 F100", "M30", "G1 X50"]);
    assert.equal(p.lineCount, 2);
    near(p.drawLength, 5);
});

test("cung tròn G2 nửa vòng: chiều dài ≈ πR và không có cảnh báo", () => {
    const p = parse(["G90", "G0 X10 Y0", "G2 X-10 Y0 I-10 J0 F600"]);
    assert.equal(p.features.arcs, 1);
    near(p.drawLength, Math.PI * 10, 0.15);                 // đa giác nội tiếp ngắn hơn cung một chút
    assert.equal(p.warnings.length, 0);
    assert.ok(p.bbox.minY < -9.9);                          // G2 = chiều kim đồng hồ, đi qua (0, -10)
});

test("G3 ngược chiều đi qua phía đối diện", () => {
    const p = parse(["G90", "G0 X10 Y0", "G3 X-10 Y0 I-10 J0 F600"]);
    assert.ok(p.bbox.maxY > 9.9);
});

test("cảnh báo: lệnh G/M không hỗ trợ, thiếu F, tạm dừng chương trình", () => {
    const p = parse(["G1 X5", "G38.2 X5 F100", "M0", "M99"]);
    const keys = p.warnings.map((w) => w.key);
    assert.ok(keys.includes("unsupported_g")); assert.ok(keys.includes("program_pause"));
    assert.ok(keys.includes("unsupported_m")); assert.ok(keys.includes("missing_feed"));
    near(p.drawLength, 5);                                   // G38.2 không bị đoán là chuyển động
});

test("G4 P tính bằng giây và nằm trong tổng thời gian", () => {
    const p = parse(["G4 P2", "G1 X6 F360"]);
    assert.equal(p.segments[0].kind, "dwell");
    near(p.seconds, 2 + 1);
});

test("outOfRange cộng độ lệch gốc làm việc và có dung sai", () => {
    const box = { minX: 0, minY: 0, maxX: 285, maxY: 318 };
    assert.equal(outOfRange(box, 285, 318), false);
    assert.equal(outOfRange({ ...box, maxX: 285.5 }, 285, 318), true);
    assert.equal(outOfRange(box, 285, 318, [1, 0, 0]), true);          // WCO đẩy khung ra ngoài
    assert.equal(outOfRange({ ...box, minX: -0.0005 }, 285, 318), false);
    assert.equal(outOfRange(null, 285, 318), false);
});

test("positionAt nội suy trong đoạn và dừng ở cuối", () => {
    const p = parse(["G90", "G1 X10 F600", "G1 Y10"]);          // mỗi đoạn 10 mm @600 = 1 s
    assert.deepEqual(positionAt([], 0), null);
    const mid = positionAt(p.segments, 0.5);
    near(mid.x, 5); near(mid.y, 0); assert.equal(mid.penDown, true);
    const second = positionAt(p.segments, 1.5);
    near(second.x, 10); near(second.y, 5);
    const end = positionAt(p.segments, 99);
    near(end.x, 10); near(end.y, 10);
});

test("formatDuration", () => {
    assert.equal(formatDuration(59.6), "1:00");
    assert.equal(formatDuration(3725), "1:02:05");
    assert.equal(formatDuration(0), "0:00");
    assert.equal(formatDuration(NaN), "—");
});
