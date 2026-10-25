
import {
    setLanguage,
    getLanguage,
    t,
    applyTranslations
} from "./i18n.js";

import { startPolling, subscribe, state } from "./state.js";
import { api, ApiError } from "./api.js";
import { initTerminal } from "./views/terminal.js";
import { initSettings} from "./views/settings.js";
import { initControl } from "./views/control.js";
import { initJobs } from "./views/jobs.js";

async function initApp() {
    try {
        initTabs();
        await initLanguageSelector();
        initThemeSelector();
        initSettings();
        startPolling();
        initControl();
        initJobs();
        initTerminal();
        

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


