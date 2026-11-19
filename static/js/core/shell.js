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

    // ---------------- Theme ----------------
    function currentTheme() {
        return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    }

    function renderThemeButton(button) {
        if (!button) return;
        var dark = currentTheme() === "dark";
        button.innerHTML = dark
            ? '<i class="bi bi-sun" aria-hidden="true"></i>'
            : '<i class="bi bi-moon-stars" aria-hidden="true"></i>';
        button.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    }

    function setupTheme() {
        var button = document.getElementById("themeToggle");
        renderThemeButton(button);
        if (!button) return;

        button.addEventListener("click", function () {
            var next = currentTheme() === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", next);
            try { localStorage.setItem(THEME_KEY, next); } catch (error) { /* ignore */ }
            renderThemeButton(button);
            document.dispatchEvent(new CustomEvent("studymate:themechange", { detail: { theme: next } }));
        });
    }

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

    onReady(function () {
        setupTheme();
        setupSidebar();
        setupHealth();
        setupDropzones();
    });
})();
