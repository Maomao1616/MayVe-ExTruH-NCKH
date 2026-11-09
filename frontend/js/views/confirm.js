// views/confirm.js — hộp xác nhận chung của app (cùng kiểu "Bỏ điểm dừng"), thay cho window.confirm của trình duyệt.
// Dựng DOM khi cần (không phụ thuộc index.html), mặc định chọn nút "Giữ lại" để bấm Enter nhầm cũng an toàn.
//   const ok = await askConfirm({ title, text, facts: [[nhãn, giá trị], ...], keep, confirm, icon });
import { t } from "../core/i18n.js";

let open = null;

export function askConfirm({ title, text = "", facts = [], keep = t("confirm.keep"), confirm = t("confirm.ok"), icon = "🗑️" }) {
    if (open) return open;                                   // đang hỏi: không chồng hộp thứ hai
    const make = (tag, className, content) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (content !== undefined) node.textContent = content;
        return node;
    };
    const overlay = make("div", "glass-modal-overlay");
    const box = make("div", "glass-modal-box resume-modal-box discard-modal-box");
    box.setAttribute("role", "alertdialog");
    box.setAttribute("aria-modal", "true");
    const heading = make("h3", "", title);
    box.append(make("div", "glass-modal-icon", icon), heading);
    if (facts.length) {
        const list = make("dl", "resume-facts");
        for (const [label, value] of facts) {
            const row = make("div", "resume-fact-wide");
            row.append(make("dt", "", label), make("dd", "", String(value)));
            list.append(row);
        }
        box.append(list);
    }
    if (text) box.append(make("p", "", text));
    const actions = make("div", "glass-modal-actions");
    const keepBtn = make("button", "secondary-button", keep);
    const okBtn = make("button", "primary-button danger-button", confirm);
    keepBtn.type = okBtn.type = "button";
    actions.append(keepBtn, okBtn);
    box.append(actions);
    overlay.append(box);
    document.body.append(overlay);

    open = new Promise((resolve) => {
        const done = (answer) => {
            window.removeEventListener("keydown", onKey, true);
            overlay.remove();
            open = null;
            resolve(answer);
        };
        const onKey = (event) => { if (event.key === "Escape") { event.stopPropagation(); done(false); } };
        window.addEventListener("keydown", onKey, true);
        keepBtn.addEventListener("click", () => done(false));
        okBtn.addEventListener("click", () => done(true));
        overlay.addEventListener("click", (event) => { if (event.target === overlay) done(false); });
        keepBtn.focus();
    });
    return open;
}
