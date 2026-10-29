const DEFAULT_LANGUAGE = "vi";

let currentLanguage = DEFAULT_LANGUAGE;
let messages = {};

const dictionaries = {
    vi: () => import("../../locales/vi.json", {
        with: { type: "json" }
    }),
    en: () => import("../../locales/en.json", {
        with: { type: "json" }
    })
};

export async function setLanguage(language) {
    const selectedLanguage = dictionaries[language]
        ? language
        : DEFAULT_LANGUAGE;

    const module = await dictionaries[selectedLanguage]();

    messages = module.default;
    currentLanguage = selectedLanguage;

    document.documentElement.lang = currentLanguage;

    return currentLanguage;
}

export function getLanguage() {
    return currentLanguage;
}

export function t(key) {
    return messages[key] ?? key;
}

export function applyTranslations(root = document) {
    root.querySelectorAll("[data-i18n]").forEach((element) => {
        // Cú pháp: "khóa" (đặt chữ) hoặc "[thuộc-tính]khóa" (đặt thuộc tính),
        // nhiều phần ngăn cách bằng dấu ";"
        element.dataset.i18n.split(";").forEach((part) => {
            const rule = part.trim();
            if (!rule) return;

            const match = rule.match(/^\[([^\]]+)\](.+)$/);
            if (match) {
                element.setAttribute(match[1], t(match[2].trim()));
            } else {
                element.textContent = t(rule);
            }
        });
    });
}