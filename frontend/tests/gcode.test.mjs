// Kiểm lib/gcode.js (bộ đọc G-code quyết định xem trước + cảnh báo). Chạy: node --test frontend/tests/gcode.test.mjs
// Số kỳ vọng tính tay từ hình học (không chép từ kết quả chạy).
import test from "node:test";
import assert from "node:assert/strict";
import { cleanLine, parseGcode, outOfRange, positionAt, formatDuration, trackProgress } from "../js/lib/gcode.js";

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
    const p = parse(["G1 X5", "G7 X5 F100", "M0", "M99"]);
    const keys = p.warnings.map((w) => w.key);
    assert.ok(keys.includes("unsupported_g")); assert.ok(keys.includes("program_pause"));
    assert.ok(keys.includes("unsupported_m")); assert.ok(keys.includes("missing_feed"));
    near(p.drawLength, 5);                                   // G7 không bị đoán là chuyển động
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

test("lệnh backend sẽ từ chối được đánh dấu chặn, kèm số dòng trong tệp gốc", () => {
    const p = parse(["G21", "; chú thích", "G92 X0 Y0", "G1 X5 F100", "$H", "G28.1", "G38.2 Z-1", "G1 X1 ?"]);
    assert.deepEqual(p.blocked.map((w) => [w.line, w.key]),
        [[3, "blocked_g"], [5, "blocked_dollar"], [6, "blocked_g"], [7, "blocked_g"], [8, "bad_char"]]);
    assert.deepEqual(p.lines, ["G21", "G92 X0 Y0", "G1 X5 F100", "G28.1", "G38.2 Z-1"]);   // $ / ký tự lạ không gửi
});

test("lệnh thường không bị chặn (G54, G91, M0 chỉ là lưu ý)", () => {
    const p = parse(["G54 G90 G21", "G91", "G1 X1 F100", "M0", "G0 X92", "G1 X1 ; G92 trong chú thích"]);
    assert.equal(p.blocked.length, 0);
    assert.ok(p.warnings.some((w) => w.key === "program_pause"));
});

test("trackProgress không mất dấu khi giữa hai lần hỏi máy đi qua hàng nghìn đoạn", () => {
    // 3000 nét 0,1 mm nối nhau theo trục X (dòng i đi tới X = i/10)
    const lines = ["G1 Z0 F1000", ...Array.from({ length: 3000 }, (_, i) => `G1 X${((i + 1) / 10).toFixed(1)}`)];
    const { segments } = parse(lines);
    // Máy đang ở X = 250 (dòng 2501 trong tệp, kể cả dòng Z đầu), đã nhận tới dòng 2520
    const hit = trackProgress(segments, 0, 2520, 250, 0);
    near(hit.x, 250, 0.5);                       // sai số thiết kế: đoạn đầu tiên cách dưới 0,5 mm
    assert.ok(Math.abs(segments[hit.index].seq - 2501) <= 5);
    // Không vượt quá dòng máy đã nhận, không lùi về trước lần trước
    assert.equal(trackProgress(segments, hit.index, 2520, 299, 0).x <= 252.0, true);
    assert.equal(trackProgress(segments, hit.index, 2520, 10, 0).index >= hit.index, true);
});

test("G-code nhấc thấp (Z2) vẫn là bút lên dù Z điều khiển là 5: ngưỡng theo Z xuống, không theo Z lên", () => {
    const p = parse(["G90 G21", "G1 Z2 F3000", "G0 X10 Y10", "G1 Z0", "G1 X20 Y10 F1500", "G1 Z2", "G0 X30 Y30"]);
    near(p.drawLength, 10);                        // chỉ nét Z0 tính là vẽ
    near(p.travelLength, Math.hypot(10, 10) + Math.hypot(10, 20));
});

// --- ước tính có gia tốc (opts.accel > 0; = backend drawing/gcode.py) ------------------------------------------
test("moveTime: hình thang và tam giác giống backend", async () => {
    const { moveTime } = await import("../js/lib/gcode.js");
    near(moveTime(100, 0, 0, 100, 1000), 1.1);
    near(moveTime(1, 0, 0, 100, 1000), 2 * Math.sqrt(1000) / 1000);
});

test("accel > 0: tính gia tốc + thời gian nâng bút; accel = 0 giữ cách tính cũ", () => {
    const text = ["G90 G21", "G1 Z3 F3000", "G4 P0.02", "G0 X10 Y10", "G1 Z0 F2000", "G4 P0.02",
                  "G1 X60 Y10 F8000", "G1 X60 Y11", "G1 X10 Y11", "G1 Z3 F3000", "G4 P0.02"].join("\n");
    const flat = parseGcode(text, { penUpZ: 3, rapidFeed: 8000 });
    const acc = parseGcode(text, { penUpZ: 3, rapidFeed: 8000, accel: 3000, junction: 0.05, liftOverheadS: 0.15 });
    assert.ok(acc.seconds > flat.seconds + 0.15);
    // t0 tăng dần và cộng lại đúng tổng
    const last = acc.segments.at(-1);
    near(last.t0 + last.dur, acc.seconds);
    assert.ok(acc.segments.every((s, i) => i === 0 || s.t0 >= acc.segments[i - 1].t0));
});

test("linesPerS: chuỗi dòng ngắn không nhanh hơn số dòng ÷ linesPerS; cung G2 tính là 1 dòng; dwellFlushS cộng mỗi G4", () => {
    // Tờ 7.6 (13/11/2026): đoạn 0,1 mm ở 8000 thật chỉ ~125 dòng/giây
    const pts = [];
    for (let i = 0; i <= 628; i++) pts.push(`G1 X${(10 * Math.cos(i / 100)).toFixed(3)} Y${(10 * Math.sin(i / 100)).toFixed(3)}`);
    const short = ["G90 G21", "G1 Z3 F3000", "G0 X10 Y0", "G1 Z0 F2000", "G1 X10 Y0 F8000", ...pts, "G1 Z3"].join("\n");
    const base = { penUpZ: 3, rapidFeed: 8000, accel: 3000, junction: 0.05 };
    const free = parseGcode(short, base);
    const capped = parseGcode(short, { ...base, linesPerS: 125 });
    assert.ok(free.seconds < 2);
    assert.ok(capped.seconds >= 629 / 125);
    const arc = ["G90 G21", "G1 Z3 F3000", "G0 X10 Y0", "G1 Z0 F2000", "G3 X-10 Y0 I-10 J0 F8000", "G1 Z3"].join("\n");
    near(parseGcode(arc, { ...base, linesPerS: 125 }).seconds, parseGcode(arc, base).seconds);
    const dwell = ["G90 G21", "G1 Z3 F3000", "G4 P0.02", "G4 P0.02"].join("\n");
    near(parseGcode(dwell, { ...base, dwellFlushS: 0.025 }).seconds - parseGcode(dwell, base).seconds, 0.05);
});

test("jobClientInfo.rapids đếm số lần nhấc bút theo Z, kể cả khi di chuyển bằng G1 (13/11/2026)", async () => {
    const { jobClientInfo } = await import("../js/lib/gcode.js");
    const text = ["G90 G21", "G1 Z3 F3000", "G1 X10 Y10 F8000", "G1 Z0 F2000", "G1 X20 Y10", "G1 Z3",
                  "G1 X30 Y30", "G1 Z0", "G1 X40 Y30", "G1 Z3"].join("\n");
    assert.equal(jobClientInfo(parseGcode(text, { penUpZ: 3, penDownZ: 0, rapidFeed: 8000 })).rapids, 2);
});
