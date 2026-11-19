/* ==========================================================
   StudyMate AI — quick search (command palette) + shortcuts
   Ctrl/Cmd+K or "/"  open quick search
   ?                  keyboard shortcuts
   Alt+1 … Alt+7      jump to a page (sidebar order)
   Items come from the sidebar links and a few app actions, so a
   new page in config/navigation.html appears here automatically.
   ========================================================== */

(function () {
    "use strict";

    var dialog, input, list, items = [], filtered = [], active = 0;

    function isTyping(target) {
        var tag = (target && target.tagName) || "";
        return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (target && target.isContentEditable);
    }

    function pageLinks() {
        return Array.prototype.slice.call(document.querySelectorAll("#sidebar .nav-link"));
    }

    function buildItems() {
        var result = pageLinks().map(function (link, index) {
            var icon = link.querySelector("i");
            return {
                group: "Go to",
                title: link.textContent.trim(),
                icon: icon ? icon.className.replace("bi ", "").replace("bi-", "") : "arrow-right",
                hint: index < 9 ? "Alt " + (index + 1) : "",
                run: function () { location.href = link.getAttribute("href"); }
            };
        });

        var focus = window.StudyMateFocus;
        if (focus) {
            var snap = focus.snapshot();
            result.push({
                group: "Actions",
                title: snap.running ? "Pause focus timer" : "Start a 25-minute focus session",
                icon: snap.running ? "pause-circle" : "hourglass-split",
                run: function () {
                    if (focus.snapshot().running) focus.pause();
                    else if (focus.snapshot().remaining < focus.snapshot().total) focus.start();
                    else focus.start(25);
                }
            });
        }

        var theme = window.StudyMateTheme;
        if (theme) {
            theme.themes.forEach(function (t) {
                if (t.id === theme.current()) return;
                result.push({ group: "Actions", title: "Switch to " + t.name + " theme", icon: "palette",
                              run: function () { theme.apply(t.id); } });
            });
        }

        if (window.StudyMateTour) {
            result.push({ group: "Help", title: "Take the dashboard tour", icon: "signpost-split",
                          run: function () { window.StudyMateTour.start(); } });
        }
        if (document.querySelector(".page-tips")) {
            result.push({ group: "Help", title: "Show tips for this page", icon: "lightbulb",
                          run: function () {
                              var tips = document.querySelector(".page-tips");
                              tips.open = true;
                              tips.scrollIntoView({ behavior: "smooth", block: "center" });
                          } });
        }
        result.push({ group: "Help", title: "Keyboard shortcuts", icon: "keyboard", hint: "?",
                      run: function () { openShortcuts(); } });
        return result;
    }

    function ensureDialog() {
        if (dialog) return;
        dialog = document.createElement("dialog");
        dialog.className = "palette";
        dialog.setAttribute("aria-label", "Search tools and actions");
        dialog.innerHTML =
            '<div class="palette-search">' +
            '  <i class="bi bi-search" aria-hidden="true"></i>' +
            '  <input type="text" class="palette-input" placeholder="Search tools and actions…" aria-label="Search" ' +
            '         role="combobox" aria-expanded="true" aria-controls="paletteList" autocomplete="off">' +
            '  <kbd>Esc</kbd>' +
            '</div>' +
            '<ul class="palette-list" id="paletteList" role="listbox"></ul>' +
            '<p class="palette-foot"><kbd>↑</kbd><kbd>↓</kbd> to move, <kbd>Enter</kbd> to open</p>';
        document.body.appendChild(dialog);
        input = dialog.querySelector(".palette-input");
        list = dialog.querySelector(".palette-list");

        input.addEventListener("input", function () { active = 0; render(); });
        input.addEventListener("keydown", function (event) {
            if (event.key === "ArrowDown") { event.preventDefault(); active = Math.min(active + 1, filtered.length - 1); render(); }
            if (event.key === "ArrowUp") { event.preventDefault(); active = Math.max(active - 1, 0); render(); }
            if (event.key === "Enter" && filtered[active]) { event.preventDefault(); choose(filtered[active]); }
        });
        dialog.addEventListener("click", function (event) {
            if (event.target === dialog) dialog.close();
        });
    }

    function render() {
        var query = input.value.trim().toLowerCase();
        filtered = items.filter(function (item) {
            return !query || (item.title + " " + item.group).toLowerCase().indexOf(query) !== -1;
        });
        list.replaceChildren();
        if (!filtered.length) {
            var empty = document.createElement("li");
            empty.className = "palette-empty";
            empty.textContent = "Nothing matches “" + input.value + "”. Try a tool name like QuickNotes.";
            list.appendChild(empty);
            return;
        }
        var lastGroup = "";
        filtered.forEach(function (item, index) {
            if (item.group !== lastGroup) {
                var heading = document.createElement("li");
                heading.className = "palette-group";
                heading.setAttribute("role", "presentation");
                heading.textContent = item.group;
                list.appendChild(heading);
                lastGroup = item.group;
            }
            var li = document.createElement("li");
            li.className = "palette-item" + (index === active ? " is-active" : "");
            li.setAttribute("role", "option");
            li.setAttribute("aria-selected", String(index === active));
            li.innerHTML = '<i class="bi bi-' + item.icon + '" aria-hidden="true"></i><span></span>' +
                (item.hint ? "<kbd>" + item.hint + "</kbd>" : "");
            li.querySelector("span").textContent = item.title;
            li.addEventListener("mousemove", function () { if (active !== index) { active = index; render(); } });
            li.addEventListener("click", function () { choose(item); });
            list.appendChild(li);
        });
        var current = list.querySelector(".is-active");
        if (current) current.scrollIntoView({ block: "nearest" });
    }

    function choose(item) {
        dialog.close();
        item.run();
    }

    function openPalette() {
        ensureDialog();
        if (dialog.open) return;
        items = buildItems();
        input.value = "";
        active = 0;
        render();
        dialog.showModal();
        input.focus();
    }

    // ---------------- Shortcuts dialog ----------------
    var shortcuts;
    function openShortcuts() {
        if (!shortcuts) {
            shortcuts = document.createElement("dialog");
            shortcuts.className = "palette shortcuts";
            shortcuts.setAttribute("aria-labelledby", "shortcutsTitle");
            var rows = [
                ["Ctrl K", "Quick search"], ["/", "Quick search"], ["?", "This list"],
                ["Alt 1–7", "Jump to a page in the menu"], ["Esc", "Close menus and dialogs"],
                ["Enter", "Send a message (Assistant)"], ["Shift Enter", "New line in a message"]
            ];
            shortcuts.innerHTML = '<div class="shortcuts-head"><h2 id="shortcutsTitle">Keyboard shortcuts</h2>' +
                '<button type="button" class="icon-button" aria-label="Close"><i class="bi bi-x-lg" aria-hidden="true"></i></button></div>' +
                '<dl class="shortcut-list">' + rows.map(function (r) {
                    return "<div><dt>" + r[0].split(" ").map(function (k) { return "<kbd>" + k + "</kbd>"; }).join(" ") +
                        "</dt><dd>" + r[1] + "</dd></div>";
                }).join("") + "</dl>";
            document.body.appendChild(shortcuts);
            shortcuts.querySelector("button").addEventListener("click", function () { shortcuts.close(); });
            shortcuts.addEventListener("click", function (event) { if (event.target === shortcuts) shortcuts.close(); });
        }
        if (!shortcuts.open) shortcuts.showModal();
    }

    // ---------------- Global keys ----------------
    document.addEventListener("keydown", function (event) {
        var key = event.key;
        if ((event.ctrlKey || event.metaKey) && key.toLowerCase() === "k") {
            event.preventDefault();
            openPalette();
            return;
        }
        if (isTyping(event.target) || event.ctrlKey || event.metaKey) return;
        if (document.querySelector("dialog[open]")) return;

        if (key === "/") { event.preventDefault(); openPalette(); }
        else if (key === "?") { event.preventDefault(); openShortcuts(); }
        else if (event.altKey && /^[1-9]$/.test(key)) {
            var link = pageLinks()[Number(key) - 1];
            if (link) { event.preventDefault(); location.href = link.getAttribute("href"); }
        }
    });

    function init() {
        var trigger = document.getElementById("paletteOpen");
        if (trigger) trigger.addEventListener("click", openPalette);
    }

    window.StudyMatePalette = { open: openPalette, shortcuts: openShortcuts };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
