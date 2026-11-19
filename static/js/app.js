
/*
=========================================
STUDYMATE AI - DASHBOARD JAVASCRIPT
=========================================

Features:
1. Light and Dark Theme
2. Save Theme Preference
3. Mobile Sidebar Toggle
4. Close Sidebar on Navigation
5. Close Sidebar on Outside Click
6. Disable Coming Soon Navigation Links
*/

document.addEventListener("DOMContentLoaded", function () {

    // =====================================
    // 1. LIGHT AND DARK THEME
    // =====================================

    const themeToggle = document.getElementById("themeToggle");

    // Get saved theme
    const savedTheme = localStorage.getItem("studymate-theme");

    // Apply saved theme or default to light
    const initialTheme =
        savedTheme === "dark" ? "dark" : "light";

    document.documentElement.setAttribute(
        "data-theme",
        initialTheme
    );

    // Update theme icon
    function updateThemeIcon() {

        if (!themeToggle) return;

        const currentTheme =
            document.documentElement.getAttribute("data-theme");

        themeToggle.innerHTML =
            currentTheme === "dark"
                ? '<i class="bi bi-sun"></i>'
                : '<i class="bi bi-moon-stars"></i>';

        themeToggle.setAttribute(
            "aria-label",
            currentTheme === "dark"
                ? "Switch to light theme"
                : "Switch to dark theme"
        );
    }

    // Initialize theme icon
    updateThemeIcon();

    // Theme toggle event
    if (themeToggle) {

        themeToggle.addEventListener("click", function () {

            const currentTheme =
                document.documentElement.getAttribute("data-theme");

            const newTheme =
                currentTheme === "dark" ? "light" : "dark";

            // Apply new theme
            document.documentElement.setAttribute(
                "data-theme",
                newTheme
            );

            // Save preference
            localStorage.setItem(
                "studymate-theme",
                newTheme
            );

            // Update icon
            updateThemeIcon();

        });

    }


    // =====================================
    // 2. MOBILE SIDEBAR
    // =====================================

    const menuToggle = document.getElementById("menuToggle");

    const sidebar = document.getElementById("sidebar");

    // Open or close sidebar
    if (menuToggle && sidebar) {

        menuToggle.setAttribute("aria-expanded", "false");

        menuToggle.addEventListener("click", function () {

            const isOpen = sidebar.classList.toggle("show");

            menuToggle.setAttribute(
                "aria-expanded",
                String(isOpen)
            );

        });

    }


    // =====================================
    // 3. CLOSE SIDEBAR AFTER NAVIGATION
    // =====================================

    if (sidebar) {

        // Match the actual HTML structure
        const navigationLinks =
            sidebar.querySelectorAll(".nav-link");

        navigationLinks.forEach(function (link) {

            link.addEventListener("click", function (event) {

                // Prevent unfinished navigation links
                if (link.classList.contains("disabled")) {

                    event.preventDefault();
                    return;
                }

                // Close mobile sidebar
                sidebar.classList.remove("show");

                if (menuToggle) {
                    menuToggle.setAttribute(
                        "aria-expanded",
                        "false"
                    );
                }

            });

        });

    }


    // =====================================
    // 4. CLOSE SIDEBAR ON OUTSIDE CLICK
    // =====================================

    document.addEventListener("click", function (event) {

        if (!sidebar || !menuToggle) return;

        const clickedInsideSidebar =
            sidebar.contains(event.target);

        const clickedMenuButton =
            menuToggle.contains(event.target);

        if (
            !clickedInsideSidebar &&
            !clickedMenuButton
        ) {

            sidebar.classList.remove("show");

            menuToggle.setAttribute(
                "aria-expanded",
                "false"
            );

        }

    });


    // =====================================
    // 5. CLOSE SIDEBAR ON WINDOW RESIZE
    // =====================================

    window.addEventListener("resize", function () {

        if (window.innerWidth > 768 && sidebar) {

            sidebar.classList.remove("show");

            if (menuToggle) {
                menuToggle.setAttribute(
                    "aria-expanded",
                    "false"
                );
            }

        }

    });

});
