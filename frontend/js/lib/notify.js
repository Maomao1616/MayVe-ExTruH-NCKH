// lib/notify.js — báo "vẽ xong / lỗi" cho người đứng xa máy: âm báo + tiêu đề tab nhấp nháy.
// Không cần Internet và không cần tệp âm thanh (tạo tiếng bằng WebAudio). Chỉ các hàm thuần (tonePlan) được test;
// phần chạm trình duyệt (âm thanh, tiêu đề) bọc try/catch để chặn / thiếu API thì im lặng.

// Kế hoạch tiếng cho một trạng thái: [{ hz, ms }...] (nghỉ 60 ms giữa hai tiếng). Xong: ba nốt đi lên; lỗi: hai nốt trầm lặp.
// Hủy do người bấm: không kêu (người đó đang đứng trước máy).
export function tonePlan(kind) {
    if (kind === "done") return [{ hz: 660, ms: 140 }, { hz: 880, ms: 140 }, { hz: 1175, ms: 280 }];
    if (kind === "failed") return [{ hz: 440, ms: 320 }, { hz: 294, ms: 320 }, { hz: 440, ms: 320 }, { hz: 294, ms: 520 }];
    return [];
}

const GAP_S = 0.06;

export function playTones(plan) {
    if (!plan.length) return;
    try {
        const Ctx = window.AudioContext ?? window.webkitAudioContext;
        if (!Ctx) return;
        const ctx = new Ctx();
        let at = ctx.currentTime + 0.02;
        for (const { hz, ms } of plan) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.value = hz;
            gain.gain.setValueAtTime(0.0001, at);
            gain.gain.exponentialRampToValueAtTime(0.25, at + 0.02);       // vào êm, tránh tiếng "tách"
            gain.gain.exponentialRampToValueAtTime(0.0001, at + ms / 1000);
            osc.connect(gain).connect(ctx.destination);
            osc.start(at);
            osc.stop(at + ms / 1000 + 0.02);
            at += ms / 1000 + GAP_S;
        }
        setTimeout(() => ctx.close?.(), (at - ctx.currentTime) * 1000 + 300);
    } catch { /* trình duyệt chặn âm thanh: bỏ qua */ }
}

let flashTimer = null;
let savedTitle = null;

// Tab đang ẩn thì tiêu đề nhấp nháy giữa `text` và tiêu đề cũ tới khi người dùng quay lại tab. Tab đang hiện: không làm gì.
export function flashTitle(text) {
    try {
        if (!document.hidden || flashTimer) return;
        savedTitle = document.title;
        let on = false;
        const tick = () => { on = !on; document.title = on ? text : savedTitle; };
        tick();
        flashTimer = setInterval(tick, 1000);
        const stop = () => {
            if (document.hidden) return;
            clearInterval(flashTimer);
            flashTimer = null;
            document.title = savedTitle;
            document.removeEventListener("visibilitychange", stop);
        };
        document.addEventListener("visibilitychange", stop);
    } catch { /* bỏ qua */ }
}

// kind: "done" | "failed" (trạng thái khác thì không báo). title: chữ đã dịch, vd "✔ Vẽ xong · tên bản vẽ".
export function notifyJob(kind, title, { sound = true } = {}) {
    if (kind !== "done" && kind !== "failed") return;
    if (sound) playTones(tonePlan(kind));
    flashTitle(title);
}
