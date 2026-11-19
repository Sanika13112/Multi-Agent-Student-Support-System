/* ==========================================================
   StudyMate AI — first-visit tour (dashboard)
   Starts once automatically; replay from quick search
   ("Take the dashboard tour"). Steps whose element is hidden
   (for example the sidebar on phones) are skipped.
   ========================================================== */

(function () {
    "use strict";

    var KEY = "studymate-tour-done";
    var STEPS = [
        { target: "#sidebar", title: "Everything in one place",
          text: "Every tool is in this menu. The glowing item is the page you're on." },
        { target: "#paletteOpen", title: "Find anything fast",
          text: "Press Ctrl+K (or /) to jump to a tool, start a focus session or change the theme." },
        { target: "#progress", title: "Your progress",
          text: "Each study action counts toward today's goal, keeps your streak alive and earns XP to level up." },
        { target: ".tool-grid", title: "Pick a tool",
          text: "Make notes from a PDF or lecture, ask questions about a document, or test yourself with a quiz." },
        { target: "#focus", title: "Focus timer",
          text: "Start a session and keep studying in any tool. The timer stays in the top bar." },
        { target: "#themeToggle", title: "Make it yours",
          text: "Choose Midnight, Lavender, Sunrise or Ocean. Your choice is remembered." }
    ];

    var index = 0, steps = [], spot, card;

    function visible(el) {
        if (!el) return false;
        var rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== "hidden";
    }

    function build() {
        spot = document.createElement("div");
        spot.className = "tour-spotlight";
        card = document.createElement("div");
        card.className = "tour-card";
        card.setAttribute("role", "dialog");
        card.setAttribute("aria-modal", "true");
        card.setAttribute("aria-labelledby", "tourTitle");
        card.innerHTML =
            '<p class="tour-count" id="tourCount"></p>' +
            '<h2 class="tour-title" id="tourTitle"></h2>' +
            '<p class="tour-text" id="tourText"></p>' +
            '<div class="tour-actions">' +
            '  <button type="button" class="btn btn-ghost btn-sm" data-tour="skip">Skip tour</button>' +
            '  <span class="tour-spacer"></span>' +
            '  <button type="button" class="btn btn-secondary btn-sm" data-tour="back">Back</button>' +
            '  <button type="button" class="btn btn-primary btn-sm" data-tour="next">Next</button>' +
            '</div>';
        document.body.append(spot, card);
        card.addEventListener("click", function (event) {
            var action = event.target.closest("[data-tour]");
            if (!action) return;
            if (action.dataset.tour === "skip") finish();
            if (action.dataset.tour === "back") show(index - 1);
            if (action.dataset.tour === "next") index === steps.length - 1 ? finish() : show(index + 1);
        });
        document.addEventListener("keydown", onKey);
        window.addEventListener("resize", position);
        window.addEventListener("scroll", position, { passive: true });
    }

    function onKey(event) {
        if (!card) return;
        if (event.key === "Escape") finish();
        if (event.key === "ArrowRight") index === steps.length - 1 ? finish() : show(index + 1);
        if (event.key === "ArrowLeft") show(index - 1);
    }

    function position() {
        if (!card || !steps[index]) return;
        var el = document.querySelector(steps[index].target);
        if (!el) return;
        var rect = el.getBoundingClientRect();
        var pad = 8;
        spot.style.top = rect.top - pad + "px";
        spot.style.left = rect.left - pad + "px";
        spot.style.width = rect.width + pad * 2 + "px";
        spot.style.height = rect.height + pad * 2 + "px";

        var cardRect = card.getBoundingClientRect();
        var below = rect.bottom + 16;
        var top = below + cardRect.height < innerHeight ? below : Math.max(16, rect.top - cardRect.height - 16);
        if (rect.height > innerHeight * 0.6) top = Math.min(innerHeight - cardRect.height - 16, Math.max(16, rect.top + 24));
        var left = Math.min(Math.max(16, rect.left), innerWidth - cardRect.width - 16);
        if (rect.width < innerWidth * 0.3 && rect.left < innerWidth / 3 && rect.height > innerHeight * 0.6) {
            left = Math.min(rect.right + 16, innerWidth - cardRect.width - 16); // beside a tall sidebar
        }
        card.style.top = top + "px";
        card.style.left = left + "px";
    }

    function show(next) {
        if (next < 0 || next >= steps.length) return;
        index = next;
        var step = steps[index];
        var el = document.querySelector(step.target);
        card.querySelector("#tourCount").textContent = "Step " + (index + 1) + " of " + steps.length;
        card.querySelector("#tourTitle").textContent = step.title;
        card.querySelector("#tourText").textContent = step.text;
        card.querySelector('[data-tour="back"]').disabled = index === 0;
        card.querySelector('[data-tour="next"]').textContent = index === steps.length - 1 ? "Finish" : "Next";
        el.scrollIntoView({ block: "center" });
        requestAnimationFrame(function () {
            position();
            card.querySelector('[data-tour="next"]').focus();
        });
    }

    function finish() {
        try { localStorage.setItem(KEY, "1"); } catch (error) { /* ignore */ }
        document.removeEventListener("keydown", onKey);
        window.removeEventListener("resize", position);
        window.removeEventListener("scroll", position);
        if (spot) spot.remove();
        if (card) card.remove();
        spot = card = null;
        window.scrollTo({ top: 0 });
    }

    function start() {
        if (card) return;
        if (location.pathname !== "/") {
            try { sessionStorage.setItem("studymate-start-tour", "1"); } catch (error) { /* ignore */ }
            location.href = "/";
            return;
        }
        steps = STEPS.filter(function (s) { return visible(document.querySelector(s.target)); });
        if (!steps.length) return;
        build();
        show(0);
    }

    window.StudyMateTour = { start: start };

    function init() {
        if (location.pathname !== "/") return;
        var requested = false, done = false;
        try {
            requested = sessionStorage.getItem("studymate-start-tour") === "1";
            sessionStorage.removeItem("studymate-start-tour");
            done = localStorage.getItem(KEY) === "1";
        } catch (error) { done = true; }
        if (requested || !done) setTimeout(start, 600);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
