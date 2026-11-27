
import {
    setLanguage,
    getLanguage,
    t,
    applyTranslations
} from "./core/i18n.js";

import { refreshAuth } from "./core/auth.js";
import { startPolling } from "./core/state.js";
import { initAuth } from "./views/auth.js";
import { initTerminal } from "./views/terminal.js";
import { initSettings} from "./views/settings.js";
import { initControl } from "./views/control.js";
import { initHeader } from "./views/header.js";
import { initShare } from "./views/share.js";
import { initDock } from "./views/dock.js";
import { initDrawing } from "./views/drawing.js";
import { initDrafts } from "./views/drafts.js";
import { initStorage } from "./views/storage.js";
import { initBeta } from "./views/beta/index.js";           // tab Beta (docs/10); gỡ: bỏ dòng này và initBeta() bên dưới
async function initApp() {
    try {
        initTabs();
        initDetailsMemory();
        initTerminalAlwaysOpen();
        initMoreToggles();
        initChevronOnlyToggle();
        await initLanguageSelector();
        initThemeSelector();
        await refreshAuth();             // biết mình là khách hay quản lý TRƯỚC khi các view khởi động
        initAuth();
        startPolling();
        initControl();
        initDrawing();
        initDrafts();
        initTerminal();
        initSettings();
        initStorage();
        initBeta();
        initHeader();
        initShare();
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

    const activate = (tab, targetPanel) => {
        tabs.forEach((item) => {
            item.classList.remove("is-active");
            item.setAttribute("aria-selected", "false");
        });
        panels.forEach((panel) => panel.classList.remove("is-active"));
        tab.classList.add("is-active");
        tab.setAttribute("aria-selected", "true");
        targetPanel.classList.add("is-active");
    };

    tabs.forEach((tab) => {
        tab.addEventListener("click", (event) => {
            const targetSelector = tab.getAttribute("href");

            if (!targetSelector?.startsWith("#")) return;

            const targetPanel = document.querySelector(targetSelector);
            if (!targetPanel) return;

            event.preventDefault();
            activate(tab, targetPanel);
            history.replaceState(null, "", targetSelector);
        });
    });

    // Lúc mới vào: tab theo #địa-chỉ nếu có (tab Beta ẩn thì bỏ qua), không thì tab Điều khiển. Trước đây không tab nào sáng cho tới khi bấm.
    const wanted = location.hash ? [...tabs].find((tab) => tab.getAttribute("href") === location.hash && !tab.hidden) : null;
    const first = wanted ?? tabs[0];
    const firstPanel = first ? document.querySelector(first.getAttribute("href")) : null;
    if (first && firstPanel) activate(first, firstPanel);
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
    const toggle = document.getElementById("theme-toggle");   // công tắc ngày / đêm: aria-checked = đang ở chế độ tối
    if (!toggle) return;

    const applyTheme = (theme) => {
        document.documentElement.dataset.theme = theme;
        toggle.setAttribute("aria-checked", String(theme === "dark"));
    };

    applyTheme(localStorage.getItem("extruxy-theme") === "light" ? "light" : "dark");

    toggle.addEventListener("click", () => {
        const theme = toggle.getAttribute("aria-checked") === "true" ? "light" : "dark";

        applyTheme(theme);
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

/* ==================== NÚT "CHI TIẾT" (hiện / ẩn các dòng phụ) ==================== */
// Nút có data-more-toggle bật / tắt lớp show-more trên khối .has-more (hoặc .has-more-mobile) gần nhất; CSS lo hiệu ứng.
function initMoreToggles() {
    document.addEventListener("click", (event) => {
        const button = event.target instanceof Element ? event.target.closest("[data-more-toggle]") : null;
        const box = button?.closest(".has-more, .has-more-mobile");
        if (!button || !box) return;
        const on = box.classList.toggle("show-more");
        button.setAttribute("aria-expanded", String(on));
    });
}

/* ==================== CHỈ BẤM MŨI TÊN MỚI THU GỌN / MỞ ==================== */
// Bấm chỗ khác trên hàng tiêu đề thì không đóng / mở (trước đây bấm nút "Đọc từ máy" nằm trong tiêu đề cũng tô xám cả khối).
// Giữ nguyên: bàn phím (Enter / Space trên tiêu đề: event.detail = 0), nút / ô nhập nằm trong tiêu đề, tiêu đề không có mũi tên.
function initChevronOnlyToggle() {
    const CHEVRON = ".drawing-section-chevron, .terminal-toggle";
    document.addEventListener("click", (event) => {
        if (event.detail === 0 || !(event.target instanceof Element)) return;
        const summary = event.target.closest("details.drawing-section > summary");
        if (!summary || !summary.querySelector(CHEVRON)) return;
        if (event.target.closest(`${CHEVRON}, button, input, select, textarea, a, label`)) return;
        event.preventDefault();
    }, true);
}

/* ==================== TERMINAL LUÔN MỞ TRÊN MÁY TÍNH ==================== */
// Màn rộng (>= 761 px): khối Terminal luôn mở, không thu gọn được (chủ dự án chọn 26/11/2026); điện thoại vẫn thu gọn như các khối khác.
// Dùng function (không dùng const ở ngoài hàm): initApp() chạy trước khi tệp đọc tới cuối, const sẽ chưa có giá trị.
function isTerminalPinned(details) {
    return details?.id === "terminal-panel" && window.matchMedia("(min-width: 761px)").matches;
}

function initTerminalAlwaysOpen() {
    const terminal = document.getElementById("terminal-panel");
    if (!terminal) return;
    const wide = window.matchMedia("(min-width: 761px)");
    const apply = () => { if (wide.matches) terminal.open = true; };
    apply();
    wide.addEventListener("change", apply);                // xoay máy / đổi cỡ cửa sổ qua ngưỡng 761 px
    terminal.querySelector(":scope > summary")?.addEventListener("click", (event) => {
        if (wide.matches) event.preventDefault();          // cả chuột lẫn bàn phím (Enter / Space) đều không đóng được
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

    // Điện thoại (< 761 px): khối đánh dấu data-mobile-closed đóng sẵn khi chưa có lựa chọn đã lưu, cho trang đỡ dài.
    // Lần đóng sẵn này KHÔNG được ghi nhớ như lựa chọn của người dùng (xem `programmatic`), kẻo mở lại ở màn rộng vẫn đóng.
    const narrow = window.matchMedia("(max-width: 760px)").matches;
    const programmatic = new WeakSet();
    document.querySelectorAll("details").forEach((details) => {
        const value = saved[keyOf(details)];
        if (typeof value === "boolean") {
            details.open = value;
        } else if (narrow && details.hasAttribute("data-mobile-closed") && details.open) {
            programmatic.add(details);
            details.open = false;
        }
    });

    // `toggle` không nổi bọt: nghe ở pha capture trên document.
    document.addEventListener("toggle", (event) => {
        const details = event.target;
        if (!(details instanceof HTMLDetailsElement)) return;
        if (programmatic.delete(details)) return;
        if (isTerminalPinned(details)) return;             // Terminal máy tính luôn mở: không ghi nhớ như lựa chọn của người dùng
        saved[keyOf(details)] = details.open;
        try { localStorage.setItem(DETAILS_KEY, JSON.stringify(saved)); } catch { /* bị chặn */ }
    }, true);
}
