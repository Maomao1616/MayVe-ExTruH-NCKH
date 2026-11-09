// views/customer.js — ảnh khách gửi (backend: api/customer.py, services/customer.py).
//   Khách (không đăng nhập): chọn ảnh, cắt, khổ giấy, chỉnh tông, chọn preset / kiểu nét "mong muốn" rồi bấm "Gửi ảnh":
//     ảnh thu nhỏ ≤ 1600 px (JPEG) + thông số + tên / ghi chú đi lên máy chủ, tự xóa sau vài ngày. Khách chỉ xem ảnh xám.
//   Quản lý: hộp thư "Ảnh khách gửi" trong tab Tạo bản vẽ: Mở = nạp ảnh + điền lại đúng thông số khách chọn
//     (quản lý tự bấm "Tạo nét" khi sẵn sàng), Xóa = xóa khỏi máy chủ.
// drawing.js đưa vào hai hàm: snapshot() = { file, params } hiện tại; open(file, params) = nạp vào tab (xem drawing.js).
import { api, ApiError } from "../core/api.js";
import { isAdmin } from "../core/auth.js";
import { t } from "../core/i18n.js";
import { shrinkToJpeg } from "../lib/imageprep.js";
import { askConfirm } from "./confirm.js";

const $ = (id) => document.getElementById(id);
const REFRESH_MS = 30000;

const errorText = (error) => {
    const key = error instanceof ApiError ? `customer.error.${error.code}` : "";
    if (key && t(key) !== key) return t(key);
    return error instanceof ApiError && error.message ? error.message : String(error?.message ?? error);
};

export function initCustomer({ snapshot, open }) {
    if (isAdmin()) initInbox(open);
    else initSender(snapshot);
}

/* ---------- khách: gửi ảnh ---------- */
function initSender(snapshot) {
    const button = $("customer-send-btn");
    const status = $("customer-send-status");
    if (!button || !status) return;
    const say = (text, kind = "") => {
        status.textContent = text;
        status.classList.toggle("is-error", kind === "error");
        status.classList.toggle("is-success", kind === "success");
    };
    const ready = () => { const { file } = snapshot(); return Boolean(file) && !file.name.toLowerCase().endsWith(".svg"); };
    window.addEventListener("extruxy:draw-file", () => { button.disabled = !ready(); say(""); });
    button.disabled = true;

    button.addEventListener("click", async () => {
        const { file, params } = snapshot();
        if (!file) return;
        button.disabled = true;
        say(t("customer.send.sending"));
        try {
            const jpeg = await shrinkToJpeg(file);
            if (!jpeg) throw new ApiError("bad_image", t("customer.error.bad_image"), 0);
            const form = new FormData();
            form.append("file", jpeg);
            form.append("meta", JSON.stringify({ name: $("customer-name")?.value ?? "", note: $("customer-note")?.value ?? "", params }));
            const result = await api.customerSend(form);
            const until = result.item?.expires ? new Date(result.item.expires).toLocaleDateString() : "";
            say(t("customer.send.done").replace("{date}", until), "success");
            if ($("customer-note")) $("customer-note").value = "";
        } catch (error) {
            say(errorText(error), "error");
        } finally {
            button.disabled = !ready();
        }
    });
}

/* ---------- quản lý: hộp thư ---------- */
function initInbox(open) {
    const panel = $("customer-inbox-panel");
    const list = $("customer-inbox-list");
    if (!panel || !list) return;
    let items = [];
    let busy = false;

    const say = (text, isError = false) => {
        const el = $("customer-inbox-status");
        el.textContent = text;
        el.classList.toggle("is-error", isError);
    };

    function render() {
        const unseen = items.filter((i) => !i.seen).length;
        $("customer-inbox-badge").textContent = items.length ? `${items.length}${unseen ? ` · ${unseen} ${t("customer.inbox.new")}` : ""}` : "—";
        $("customer-inbox-empty").hidden = items.length > 0;
        list.replaceChildren(...items.map(row));
    }

    function row(item) {
        const li = document.createElement("li");
        li.className = `customer-item${item.seen ? "" : " is-new"}`;
        const img = document.createElement("img");
        img.alt = "";
        img.loading = "lazy";
        img.src = api.customerImageUrl(item.id);
        const text = document.createElement("div");
        text.className = "customer-item-text";
        const name = document.createElement("strong");
        name.textContent = item.name || t("customer.inbox.noName");
        const meta = document.createElement("small");
        const preset = item.params?.["draw-preset"];
        meta.textContent = [new Date(item.created).toLocaleString(), `${item.width}×${item.height}`,
            preset && preset !== "custom" ? t(`drawing.preset.${preset}`) : null].filter(Boolean).join(" · ");
        text.append(name, meta);
        if (item.note) {
            const note = document.createElement("p");
            note.textContent = item.note;
            text.append(note);
        }
        const expires = document.createElement("small");
        expires.textContent = `${t("customer.inbox.expires")} ${new Date(item.expires).toLocaleDateString()}`;
        text.append(expires);
        const actions = document.createElement("div");
        actions.className = "customer-item-actions";
        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "secondary-button";
        openBtn.textContent = t("customer.inbox.open");
        openBtn.addEventListener("click", () => openItem(item, openBtn));
        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "danger-button";
        delBtn.textContent = t("customer.inbox.delete");
        delBtn.addEventListener("click", () => deleteItem(item));
        actions.append(openBtn, delBtn);
        li.append(img, text, actions);
        return li;
    }

    async function refresh() {
        if (busy) return;
        busy = true;
        try {
            items = (await api.customers()).items;
            say("");
        } catch (error) {
            say(errorText(error), true);
        } finally {
            busy = false;
        }
        render();
    }

    async function openItem(item, button) {
        button.disabled = true;
        try {
            const blob = await api.customerImage(item.id);
            const file = new File([blob], item.filename || "anh-khach.jpg", { type: "image/jpeg" });
            await open(file, item.params ?? {});
            if (!item.seen) { await api.customerSeen(item.id).catch(() => {}); await refresh(); }
            say(t("customer.inbox.opened").replace("{name}", item.name || t("customer.inbox.noName")));     // sau refresh(): refresh xóa dòng trạng thái
        } catch (error) {
            say(errorText(error), true);
        } finally {
            button.disabled = false;
        }
    }

    async function deleteItem(item) {
        const ok = await askConfirm({
            title: t("customer.inbox.deleteTitle"), text: t("customer.inbox.deleteText"),
            facts: [[t("customer.inbox.from"), item.name || t("customer.inbox.noName")], [t("customer.inbox.sentAt"), new Date(item.created).toLocaleString()]],
            keep: t("confirm.keep"), confirm: t("customer.inbox.delete")
        });
        if (!ok) return;
        try {
            await api.customerDelete(item.id);
        } catch (error) {
            say(errorText(error), true);
        }
        await refresh();
    }

    $("customer-inbox-refresh-btn")?.addEventListener("click", refresh);
    window.addEventListener("extruxy:language-changed", render);
    // Làm mới khi đang xem tab Tạo bản vẽ (khách gửi lúc quản lý đang mở trang vẫn thấy sau tối đa REFRESH_MS giây).
    setInterval(() => { if (!document.hidden && panel.offsetParent !== null) refresh(); }, REFRESH_MS);
    refresh();
}
