// drafts.js — định dạng thông tin bản thảo (meta.json do backend trả). THUẦN (không DOM, không mạng).
import { formatDuration } from "./gcode.js";

// Cộng số liệu của mọi lớp (mỗi lớp một tệp G-code).
export function draftTotals(draft) {
    const total = { strokes: 0, drawMm: 0, travelMm: 0, lifts: 0, seconds: 0, lines: 0 };
    for (const file of draft?.files ?? []) {
        const s = file.stats ?? {};
        total.strokes += s.strokes ?? 0;
        total.drawMm += s.draw_mm ?? 0;
        total.travelMm += s.travel_mm ?? 0;
        total.lifts += s.pen_lifts ?? 0;
        total.seconds += s.est_seconds ?? 0;
        total.lines += s.lines ?? 0;
    }
    return total;
}

// "2026-10-30T10:39:21" -> "30/10/2026 10:39"
export function formatWhen(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso ?? "");
    return m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : "—";
}

// Một dòng số liệu ngắn: "320 nét · 320 lần nhấc · ~12 phút" — `labels` do view truyền vào (đã dịch).
export function summaryLine(draft, labels) {
    const total = draftTotals(draft);
    const parts = [`${total.strokes} ${labels.strokes}`, `${total.lifts} ${labels.lifts}`,
        `~${formatDuration(total.seconds)}`];
    if ((draft?.files?.length ?? 0) > 1) parts.push(`${draft.files.length} ${labels.layers}`);
    return parts.join(" · ");
}
