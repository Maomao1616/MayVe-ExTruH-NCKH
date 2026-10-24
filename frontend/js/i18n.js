
const DEFAULT_LANGUAGE = "vi";

let currentLanguage = DEFAULT_LANGUAGE;
let messages = {};

const dictionaries = {
    vi: () => import("../locales/vi.json", {
        with: { type: "json" }
    }),
    en: () => import("../locales/en.json", {
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
        const key = element.dataset.i18n;
        element.textContent = t(key);
    });
}

