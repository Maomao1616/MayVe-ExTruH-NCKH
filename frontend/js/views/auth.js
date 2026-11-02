// views/auth.js — khung "Khách / Quản lý" ở đầu trang: chủ ghi #auth-box và các phần tử con.
// Đăng nhập đúng thì tải lại trang (core/auth.js). Vai trò chỉ để ẩn nút; backend chặn thật.

import { auth, isAdmin, login, logout } from "../core/auth.js";
import { t } from "../core/i18n.js";

const $ = (id) => document.getElementById(id);

export function initAuth() {
    const badge = $("role-badge");
    const loginBtn = $("login-btn");
    const logoutBtn = $("logout-btn");
    const form = $("login-form");
    const pin = $("login-pin");
    const error = $("login-error");
    if (!badge || !loginBtn || !logoutBtn || !form || !pin || !error) return;

    function showError(key) {
        error.textContent = key ? t(key) : "";
        error.hidden = !key;
    }

    function render() {
        const guest = !isAdmin();
        badge.textContent = guest ? t("auth.role.guest") : auth.pinSet ? t("auth.role.admin") : t("auth.role.noPin");
        badge.title = guest ? t("auth.role.guestHint") : auth.pinSet ? "" : t("auth.role.noPinHint");
        badge.classList.toggle("is-guest", guest);
        badge.classList.toggle("is-warning", !guest && !auth.pinSet);
        loginBtn.hidden = !guest || form.hidden === false;
        logoutBtn.hidden = guest || !auth.pinSet;
        if (!guest) form.hidden = true;
    }

    loginBtn.addEventListener("click", () => {
        form.hidden = false;
        render();
        pin.focus();
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!pin.value) return;
        showError(null);
        try {
            await login(pin.value);              // thành công thì trang tải lại
        } catch (err) {
            pin.value = "";
            const key = `auth.error.${err?.code}`;
            showError(t(key) === key ? "auth.error.unknown" : key);
            pin.focus();
        }
    });

    pin.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        form.hidden = true;
        showError(null);
        render();
    });

    logoutBtn.addEventListener("click", () => { logout(); });

    window.addEventListener("extruxy:language-changed", render);
    render();
}
