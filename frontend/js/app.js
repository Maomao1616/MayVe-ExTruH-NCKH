import {
    setLanguage,
    getLanguage,
    t,
    applyTranslations
} from "./i18n.js";


async function initApp() {
    try {
        await setLanguage("vi");
        initTabs();
        initLanguageSelector();
        console.log("ExtruXY đã khởi động.");
        console.log("Ngôn ngữ hiện tại:", getLanguage());
        console.log("Kiểm tra i18n:", t("nav.control"));
    } catch (error) {
        console.error("Không thể khởi tạo ExtruXY:", error);
    }
}

function initLanguageSelector() {
    const selector = document.getElementById("language-select");

    if (!selector) return;

    selector.value = getLanguage();
    applyTranslations();

    selector.addEventListener("change", async () => {
        try {
            await setLanguage(selector.value);
            applyTranslations();
        } catch (error) {
            console.error("Không thể đổi ngôn ngữ:", error);
        }
    });
}


initApp();


/* CHUYEN DOI TAB QUA JAVASCRIPT */
function initTabs() {
    const tabs = document.querySelectorAll(".nav-tab");
    const panels = document.querySelectorAll(".tab-panel");

    tabs.forEach((tab) => {
        tab.addEventListener("click", (event) => {
            const targetSelector = tab.getAttribute("href");

            if (!targetSelector || !targetSelector.startsWith("#")) {
                return;
            }

            const targetPanel = document.querySelector(targetSelector);

            if (!targetPanel) {
                return;
            }

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
