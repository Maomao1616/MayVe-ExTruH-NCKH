
import {
    setLanguage,
    getLanguage,
    t,
    applyTranslations
} from "./core/i18n.js";

import { startPolling } from "./core/state.js";
import { initTerminal } from "./views/terminal.js";
import { initSettings} from "./views/settings.js";
import { initControl } from "./views/control.js";
import { initHeader } from "./views/header.js";
import { initDock } from "./views/dock.js";
import { initDrawing } from "./views/drawing.js";
import { initDrafts } from "./views/drafts.js";
async function initApp() {
    try {
        initTabs();
        initDetailsMemory();
        await initLanguageSelector();
        initThemeSelector();
        startPolling();
        initControl();
        initDrawing();
        initDrafts();
        initTerminal();
        initSettings();
        initHeader();
        initDock();
        keepScrollSpace()
        console.log("ExtruXY đã khởi động.");
        console.log("Ngôn ngữ hiện tại:", getLanguage());
        console.log("Kiểm tra i18n:", t("nav.control"));

       
        
    } catch (error) {
        console.error("Không thể khởi tạo ExtruXY:", error);
    }
}

initApp();

/* ==================== TAB ==================== */
function initTabs() {
    const tabs = document.querySelectorAll(".nav-tab");
    const panels = document.querySelectorAll(".tab-panel");

    tabs.forEach((tab) => {
        tab.addEventListener("click", (event) => {
            const targetSelector = tab.getAttribute("href");

            if (!targetSelector?.startsWith("#")) return;

            const targetPanel = document.querySelector(targetSelector);
            if (!targetPanel) return;

            event.preventDefault();

            tabs.forEach((item) => {
                item.classList.remove("is-active");
                item.setAttribute("aria-selected", "false");
            });

            panels.forEach((panel) => {
                panel.classList.remove("is-active");
            });

            tab.classList.add("is-active");
            tab.setAttribute("aria-selected", "true");
            targetPanel.classList.add("is-active");

            history.replaceState(null, "", targetSelector);
        });
    });
}

/* ==================== NGÔN NGỮ ==================== */
async function initLanguageSelector() {
    const selector = document.getElementById("language-select");
    if (!selector) return;

    const savedLanguage = localStorage.getItem("extruxy-language");
    const language = savedLanguage === "en" ? "en" : "vi";

    try {
        await setLanguage(language);
        selector.value = language;
        applyTranslations();

        selector.addEventListener("change", async () => {
            try {
                const selectedLanguage =
                    selector.value === "en" ? "en" : "vi";

                await setLanguage(selectedLanguage);
                localStorage.setItem(
                    "extruxy-language",
                    selectedLanguage
                );
                applyTranslations();
                window.dispatchEvent(new Event("extruxy:language-changed"));   // chữ tạo bằng JS tự dịch lại
            } catch (error) {
                console.error("Không thể đổi ngôn ngữ:", error);
            }
        });
    } catch (error) {
        console.error("Không thể khởi tạo ngôn ngữ:", error);
    }
}

/* ==================== THEME ==================== */
function initThemeSelector() {
    const selector = document.getElementById("theme-select");
    if (!selector) return;

    const savedTheme = localStorage.getItem("extruxy-theme") || "dark";

    document.documentElement.dataset.theme = savedTheme;
    selector.value = savedTheme;

    selector.addEventListener("change", () => {
        const theme = selector.value === "light" ? "light" : "dark";

        document.documentElement.dataset.theme = theme;
        localStorage.setItem("extruxy-theme", theme);
    });
}



/* ==================== CHỐNG GIẬT KHUNG HÌNH (SCROLL MEMORY) ==================== */
function keepScrollSpace() {
    // Khung bao bọc toàn bộ nội dung của bạn
    const appShell = document.querySelector('.app-shell');
    if (!appShell) return;

    // Tìm tất cả các khối có thể đóng mở (Terminal, Tiền xử lý, Nguồn hình ảnh...)
    document.querySelectorAll('details').forEach(detail => {
        detail.addEventListener('click', function(e) {
            // Chỉ kích hoạt nếu người dùng bấm vào thanh tiêu đề (summary) và khối đó ĐANG MỞ
            if (e.target.closest('summary') && this.open) {
                // Ép vùng chứa giữ nguyên chiều cao lớn nhất hiện tại
                appShell.style.minHeight = `${appShell.scrollHeight}px`;
            }
        });
    });

    // Tùy chọn: Reset lại bộ nhớ chiều cao nếu người dùng thay đổi kích thước cửa sổ trình duyệt
    window.addEventListener('resize', () => {
        appShell.style.minHeight = '100vh'; // Trả về mặc định để tính toán lại
    });
}

/* ==================== NHỚ KHỐI ĐÃ THU GỌN / MỞ ==================== */
// Mỗi khối <details> nhớ trạng thái đóng/mở ở trình duyệt này; mở lại trang giữ nguyên như lần trước.
// Khóa = tab + khóa dịch của tiêu đề khối (ổn định, không phụ thuộc ngôn ngữ hay thứ tự).
function initDetailsMemory() {
    const DETAILS_KEY = "extruxy-details-v1";      // trong hàm: initApp() chạy trước khi file này đọc tới cuối
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem(DETAILS_KEY) ?? "{}") || {}; } catch { /* hỏng: bỏ qua */ }

    const keyOf = (details) => {
        const title = details.querySelector(":scope > summary [data-i18n]")?.dataset.i18n
            ?? details.id ?? details.className;
        return `${details.closest(".tab-panel")?.id ?? "app"}:${title}`;
    };

    document.querySelectorAll("details").forEach((details) => {
        const value = saved[keyOf(details)];
        if (typeof value === "boolean") details.open = value;
    });

    // `toggle` không nổi bọt: nghe ở pha capture trên document.
    document.addEventListener("toggle", (event) => {
        const details = event.target;
        if (!(details instanceof HTMLDetailsElement)) return;
        saved[keyOf(details)] = details.open;
        try { localStorage.setItem(DETAILS_KEY, JSON.stringify(saved)); } catch { /* bị chặn */ }
    }, true);
}
