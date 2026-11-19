// ==========================================
// NCD NEPAL - DASHBOARD JAVASCRIPT
// ==========================================


// ==========================================
// MOBILE SIDEBAR TOGGLE
// ==========================================

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");

    if (sidebar) {
        sidebar.classList.toggle("show");
    }
}


// ==========================================
// MARK MEDICATION AS TAKEN / NOT TAKEN
// ==========================================

function markTaken(button) {

    if (!button) {
        return;
    }

    if (button.textContent.trim() === "Mark Taken") {

        button.textContent = "✓ Taken";
        button.style.background = "#087f69";
        button.style.color = "#ffffff";

    } else {

        button.textContent = "Mark Taken";
        button.style.background = "#e8f5f1";
        button.style.color = "#087f69";

    }
}


// ==========================================
// THEME / APPEARANCE
// Light / Dark / System Default
// ==========================================

// Get saved settings
function getNCDSettings() {

    const savedSettings = localStorage.getItem("ncdNepalSettings");

    if (savedSettings) {
        try {
            return JSON.parse(savedSettings);
        } catch (error) {
            return {};
        }
    }

    return {};
}


// Apply the selected appearance
function applyNCDTheme() {

    const settings = getNCDSettings();

    const appearance = settings.appearance || "light";

    const html = document.documentElement;

    // Remove previous theme
    html.classList.remove("dark-mode");

    // DARK MODE
    if (appearance === "dark") {
        html.classList.add("dark-mode");
    }

    // SYSTEM DEFAULT
    else if (appearance === "system") {

        const systemDarkMode = window.matchMedia(
            "(prefers-color-scheme: dark)"
        ).matches;

        if (systemDarkMode) {
            html.classList.add("dark-mode");
        }
    }

    // LIGHT MODE
    else {
        html.classList.remove("dark-mode");
    }
}


// ==========================================
// SAVE APPEARANCE SETTING
// ==========================================

function saveNCDTheme(appearance) {

    const settings = getNCDSettings();

    settings.appearance = appearance;

    localStorage.setItem(
        "ncdNepalSettings",
        JSON.stringify(settings)
    );

    applyNCDTheme();
}


// ==========================================
// APPLY THEME WHEN PAGE LOADS
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    applyNCDTheme();

});


// ==========================================
// UPDATE SYSTEM DEFAULT AUTOMATICALLY
// ==========================================

const systemThemeMedia = window.matchMedia(
    "(prefers-color-scheme: dark)"
);

if (systemThemeMedia.addEventListener) {

    systemThemeMedia.addEventListener("change", function () {

        const settings = getNCDSettings();

        if (settings.appearance === "system") {
            applyNCDTheme();
        }

    });

}