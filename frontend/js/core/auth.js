// auth.js — vai trò của trình duyệt này: khách hay quản lý (backend: app/auth.py).
// Backend mới là nơi chặn thật; ở đây chỉ để ẩn nút và không gọi những route khách không được gọi.
// Đăng nhập / đăng xuất / hết phiên đều TẢI LẠI TRANG: mọi view khởi động lại đúng vai trò, khỏi đồng bộ từng chỗ.

import { api } from "./api.js";

export const auth = { role: "admin", pinSet: false };

export const isAdmin = () => auth.role === "admin";

function applyRole() {
    document.body.classList.toggle("role-guest", !isAdmin());
}

// Hỏi backend mình là ai. Backend chưa lên thì thử lại vài lần; vẫn không được thì giữ mặc định "quản lý"
// (như trước khi có phân quyền) — backend vẫn tự chặn nên không mở thêm quyền nào.
export async function refreshAuth() {
    for (let attempt = 0; attempt < 3; attempt += 1) {
        try {
            const me = await api.me();
            auth.role = me.role === "guest" ? "guest" : "admin";
            auth.pinSet = Boolean(me.pin_set);
            break;
        } catch {
            await new Promise((resolve) => setTimeout(resolve, 700));
        }
    }
    applyRole();
}

export async function login(pin) {
    await api.login(pin);
    window.location.reload();
}

export async function logout() {
    try { await api.logout(); } finally { window.location.reload(); }
}

// Chỉ khi mình đang là quản lý có đặt PIN thì 401 mới nghĩa là hết phiên. Khách gặp 401 là bình thường
// (không tải lại, nếu không sẽ lặp vô hạn).
let reloading = false;
window.addEventListener("extruxy:auth-lost", () => {
    if (reloading || !isAdmin() || !auth.pinSet) return;
    reloading = true;
    window.location.reload();
});
