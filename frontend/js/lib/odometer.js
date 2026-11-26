// Số lăn kiểu công-tơ-mét cho bảng tọa độ (26/11/2026): chữ số nào đổi thì trượt nhẹ lên / xuống, các chữ số khác đứng yên.
// Chữ vẫn là chữ thường trong từng <span> (textContent đọc ra đúng "12.345"), không dải 0–9 xếp chồng.
// Chỉ lăn phần nguyên (các chữ số TRƯỚC dấu chấm); phần thập phân đổi 10 lần/giây, lăn hết sẽ nhấp nháy (chủ dự án chốt 26/11/2026).
// Chỉ cột Workspace dùng; cột Machine ghi chữ thường.

const ROLL_MS = 150;
const ROLL_FROM = "70%";            // quãng trượt ban đầu, tính theo chiều cao chữ

/** Chỉ số các chữ số đổi giá trị (cùng độ dài chuỗi) và chiều lăn: +1 = số tăng, -1 = số giảm. Pure: có test. */
export function changedDigits(prev, next) {
    if (typeof prev !== "string" || prev.length !== next.length) return [];
    const out = [];
    const dot = next.indexOf(".");
    const last = dot < 0 ? next.length : dot;                // từ dấu chấm trở đi không lăn
    for (let i = 0; i < last; i += 1) {
        const a = prev[i];
        const b = next[i];
        if (a === b || !/\d/.test(a) || !/\d/.test(b)) continue;
        out.push({ index: i, dir: Number(b) > Number(a) ? 1 : -1 });
    }
    return out;
}

const reduceMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const isNumberText = (text) => /^-?\d+(\.\d+)?$/.test(text);

/** Ghi số vào phần tử; đổi chữ số nào thì chữ số đó lăn. Chuỗi không phải số (vd "—") ghi thẳng. */
export function setOdometer(element, text) {
    if (!element) return;
    // Nơi khác có thể ghi thẳng textContent (vd đặt "—" khi mất kết nối): chỉ tin trạng thái đã nhớ nếu chữ trên màn còn khớp.
    const prev = element.textContent === element._odometerText ? element._odometerText : undefined;
    if (prev === text) return;
    if (!isNumberText(text)) {
        element._odometerText = undefined;
        element.textContent = text;
        return;
    }
    const spans = element._odometerSpans;
    if (typeof prev === "string" && spans && prev.length === text.length) {
        for (let i = 0; i < text.length; i += 1) {
            if (prev[i] !== text[i]) spans[i].textContent = text[i];
        }
        if (!reduceMotion()) {
            for (const { index, dir } of changedDigits(prev, text)) {
                spans[index].animate(
                    [{ transform: `translateY(${dir > 0 ? ROLL_FROM : `-${ROLL_FROM}`})`, opacity: 0.15 },
                     { transform: "translateY(0)", opacity: 1 }],
                    { duration: ROLL_MS, easing: "ease-out" });
            }
        }
    } else {
        element.replaceChildren(...[...text].map((ch) => {
            const span = document.createElement("span");
            span.className = "odo-d";
            span.textContent = ch;
            return span;
        }));
        element._odometerSpans = [...element.children];
    }
    element._odometerText = text;
}
