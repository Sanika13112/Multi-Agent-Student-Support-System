/* ==========================================================
   StudyMate AI — app shell (loaded on every page)
   - Light/dark theme (saved as "studymate-theme")
   - Mobile sidebar (menu button, backdrop, Escape key)
   - Local AI status pill from /api/health
   Replaces the old static/js/app.js.
   ========================================================== */

(function () {
    "use strict";

    var THEME_KEY = "studymate-theme";
    var HEALTH_CACHE_KEY = "studymate-health";
    var HEALTH_CACHE_MS = 60 * 1000;

    function onReady(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
        } else {
            callback();
        }
    }

    // ---------------- Themes ----------------
    // Keep the id → scheme map in sync with layouts/base.html.
    var THEMES = [
        { id: "dark", name: "Midnight", text: "Dark with violet glow", scheme: "dark",
          swatch: "linear-gradient(135deg, #080a14 40%, #8b5cf6 70%, #22d3ee)" },
        { id: "light", name: "Lavender", text: "Soft light glass", scheme: "light",
          swatch: "linear-gradient(135deg, #f3f1fb 40%, #7c3aed 70%, #0891b2)" },
        { id: "sunrise", name: "Sunrise", text: "Bright and playful", scheme: "light",
          swatch: "linear-gradient(135deg, #fff6ef 40%, #f43f5e 68%, #f59e0b)" },
        { id: "ocean", name: "Ocean", text: "Deep teal, calm", scheme: "dark",
          swatch: "linear-gradient(135deg, #03121a 40%, #06b6d4 70%, #10b981)" }
    ];

    function currentTheme() {
        var id = document.documentElement.getAttribute("data-theme");
        return THEMES.some(function (t) { return t.id === id; }) ? id : "dark";
    }

    function applyTheme(id) {
        var theme = THEMES.filter(function (t) { return t.id === id; })[0] || THEMES[0];
        document.documentElement.setAttribute("data-theme", theme.id);
        document.documentElement.setAttribute("data-scheme", theme.scheme);
        try { localStorage.setItem(THEME_KEY, theme.id); } catch (error) { /* ignore */ }
        renderThemeMenu();
        document.dispatchEvent(new CustomEvent("studymate:themechange", { detail: { theme: theme.id, scheme: theme.scheme } }));
    }

    function renderThemeMenu() {
        var menu = document.getElementById("themeMenu");
        if (!menu) return;
        var current = currentTheme();
        menu.replaceChildren();
        var title = document.createElement("p");
        title.className = "theme-menu-title";
        title.textContent = "Theme";
        menu.appendChild(title);
        THEMES.forEach(function (theme) {
            var option = document.createElement("button");
            option.type = "button";
            option.className = "theme-option" + (theme.id === current ? " is-current" : "");
            option.dataset.theme = theme.id;
            option.setAttribute("aria-pressed", String(theme.id === current));
            option.innerHTML = '<span class="theme-swatch" aria-hidden="true"></span>' +
                '<span class="theme-option-text"><strong></strong><small></small></span>' +
                '<i class="bi bi-check2 theme-check" aria-hidden="true"></i>';
            option.querySelector(".theme-swatch").style.background = theme.swatch;
            option.querySelector("strong").textContent = theme.name;
            option.querySelector("small").textContent = theme.text;
            option.addEventListener("click", function () { applyTheme(theme.id); });
            menu.appendChild(option);
        });
    }

    function setupTheme() {
        var button = document.getElementById("themeToggle");
        var menu = document.getElementById("themeMenu");
        renderThemeMenu();
        if (!button || !menu) return;

        function setOpen(open) {
            menu.hidden = !open;
            button.setAttribute("aria-expanded", String(open));
            if (open) {
                var current = menu.querySelector(".is-current");
                if (current) current.focus();
            }
        }

        button.addEventListener("click", function (event) {
            event.stopPropagation();
            setOpen(menu.hidden);
        });
        document.addEventListener("click", function (event) {
            if (!menu.hidden && !menu.contains(event.target)) setOpen(false);
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && !menu.hidden) {
                setOpen(false);
                button.focus();
            }
        });
    }

    window.StudyMateTheme = { themes: THEMES, apply: applyTheme, current: currentTheme };

    // ---------------- Sidebar ----------------
    function setupSidebar() {
        var sidebar = document.getElementById("sidebar");
        var toggle = document.getElementById("menuToggle");
        var backdrop = document.getElementById("sidebarOverlay");
        if (!sidebar || !toggle) return;

        function setOpen(open) {
            sidebar.classList.toggle("show", open);
            toggle.setAttribute("aria-expanded", String(open));
            toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
            if (backdrop) backdrop.hidden = !open;
        }

        toggle.addEventListener("click", function () {
            setOpen(!sidebar.classList.contains("show"));
        });

        if (backdrop) backdrop.addEventListener("click", function () { setOpen(false); });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && sidebar.classList.contains("show")) {
                setOpen(false);
                toggle.focus();
            }
        });

        sidebar.querySelectorAll(".nav-link").forEach(function (link) {
            link.addEventListener("click", function () { setOpen(false); });
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > 860) setOpen(false);
        });
    }

    // ---------------- Local AI status ----------------
    function renderHealth(state, label, title) {
        var pill = document.getElementById("aiStatus");
        var text = document.getElementById("aiStatusLabel");
        if (!pill || !text) return;
        pill.dataset.state = state;
        text.textContent = label;
        if (title) pill.title = title;
        document.dispatchEvent(new CustomEvent("studymate:health", { detail: { state: state, label: label } }));
    }

    function applyHealth(data) {
        if (data && data.ollama) {
            renderHealth("ready", "Local AI ready", "Ollama is running" + (data.model ? " (" + data.model + ")" : ""));
        } else {
            renderHealth("offline", "Local AI offline",
                "Ollama is not reachable. Start the Ollama app or run: ollama serve");
        }
    }

    function setupHealth() {
        if (!document.getElementById("aiStatus")) return;

        try {
            var cached = JSON.parse(sessionStorage.getItem(HEALTH_CACHE_KEY) || "null");
            if (cached && Date.now() - cached.time < HEALTH_CACHE_MS) {
                applyHealth(cached.data);
                return;
            }
        } catch (error) { /* ignore */ }

        fetch("/api/health", { cache: "no-store" })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                applyHealth(data);
                try {
                    sessionStorage.setItem(HEALTH_CACHE_KEY, JSON.stringify({ time: Date.now(), data: data }));
                } catch (error) { /* ignore */ }
            })
            .catch(function () {
                renderHealth("offline", "Server unreachable", "The StudyMate server did not respond.");
            });
    }

    // ---------------- Drop zones ----------------
    // Any <label class="dropzone" for="fileInputId"> gets drag-and-drop.
    // With data-show-filename it also shows the chosen file's name.
    // Page scripts still handle the upload itself.
    function setupDropzones() {
        document.querySelectorAll(".dropzone[for]").forEach(function (zone) {
            var input = document.getElementById(zone.getAttribute("for"));
            if (!input || input.type !== "file") return;
            var hint = zone.querySelector(".dropzone-hint");
            var defaultHint = hint ? hint.textContent : "";

            input.addEventListener("change", function () {
                if (!zone.hasAttribute("data-show-filename")) return;
                var file = input.files && input.files[0];
                zone.classList.toggle("has-file", Boolean(file));
                if (hint) hint.textContent = file ? "Selected: " + file.name : defaultHint;
            });

            ["dragenter", "dragover"].forEach(function (name) {
                zone.addEventListener(name, function (event) {
                    event.preventDefault();
                    if (!input.disabled) zone.classList.add("is-dragging");
                });
            });

            ["dragleave", "drop"].forEach(function (name) {
                zone.addEventListener(name, function (event) {
                    event.preventDefault();
                    zone.classList.remove("is-dragging");
                });
            });

            zone.addEventListener("drop", function (event) {
                if (input.disabled || !event.dataTransfer || !event.dataTransfer.files.length) return;
                try {
                    input.files = event.dataTransfer.files;
                    input.dispatchEvent(new Event("change", { bubbles: true }));
                } catch (error) { /* very old browsers: click to browse still works */ }
            });
        });
    }

    // ---------------- Page tips: remember if the student closed them ----------------
    function setupTips() {
        var KEY = "studymate-tips-closed";
        var closed = {};
        try { closed = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (error) { closed = {}; }
        document.querySelectorAll(".page-tips[data-tips-id]").forEach(function (tips) {
            var id = tips.dataset.tipsId;
            if (closed[id]) tips.open = false;
            function remember(isOpen) {
                closed[id] = !isOpen;
                try { localStorage.setItem(KEY, JSON.stringify(closed)); } catch (error) { /* ignore */ }
            }
            // Save on click right away (the toggle event fires slightly later).
            var summary = tips.querySelector("summary");
            if (summary) summary.addEventListener("click", function () { remember(!tips.open); });
            tips.addEventListener("toggle", function () { remember(tips.open); });
        });
    }

    onReady(function () {
        setupTips();
        setupTheme();
        setupSidebar();
        setupHealth();
        setupDropzones();
    });
})();
