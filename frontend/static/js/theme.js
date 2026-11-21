(() => {
    "use strict";

    const readAppearance = () => {
        try {
            const settings = JSON.parse(localStorage.getItem("ncdNepalSettings") || "{}");
            return settings.appearance || localStorage.getItem("ncd_provider_theme") || localStorage.getItem("ncd-theme") || "light";
        } catch (_) {
            return "light";
        }
    };

    const applyAppearance = () => {
        const appearance = readAppearance();
        const isDark = appearance === "dark" || (
            appearance === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches
        );
        document.documentElement.classList.toggle("dark-mode", isDark);
        if (document.body) document.body.classList.toggle("dark-mode", isDark);
    };

    applyAppearance();
    document.addEventListener("DOMContentLoaded", applyAppearance, { once: true });
    window.addEventListener("storage", event => {
        if (event.key === "ncdNepalSettings" || event.key === "ncd_provider_theme" || event.key === "ncd-theme") applyAppearance();
    });
    const colorScheme = window.matchMedia("(prefers-color-scheme: dark)");
    colorScheme.addEventListener?.("change", () => {
        if (readAppearance() === "system") applyAppearance();
    });
})();
