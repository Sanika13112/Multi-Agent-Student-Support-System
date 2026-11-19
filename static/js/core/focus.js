/* ==========================================================
   StudyMate AI — focus timer (Pomodoro)
   The end time is saved, so the timer keeps running while you
   move between pages. A pill in the topbar shows the time left.
   A finished focus session is recorded by core/progress.js.
   Public API: window.StudyMateFocus
   ========================================================== */

(function () {
    "use strict";

    var KEY = "studymate-focus";
    var BREAK_MINUTES = 5;
    var listeners = [];

    function load() {
        try {
            return JSON.parse(localStorage.getItem(KEY) || "null") || idle(25);
        } catch (error) {
            return idle(25);
        }
    }

    function idle(minutes) {
        return { mode: "focus", minutes: minutes, running: false, endsAt: 0, remaining: minutes * 60 * 1000 };
    }

    function save(state) {
        try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (error) { /* ignore */ }
        listeners.forEach(function (fn) { fn(snapshot()); });
        renderPill();
    }

    function remaining(state) {
        return state.running ? Math.max(0, state.endsAt - Date.now()) : state.remaining;
    }

    function snapshot() {
        var state = load();
        return {
            mode: state.mode,
            minutes: state.minutes,
            running: state.running,
            remaining: remaining(state),
            total: state.minutes * 60 * 1000
        };
    }

    function format(ms) {
        var total = Math.ceil(ms / 1000);
        var m = Math.floor(total / 60);
        var s = total % 60;
        return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    }

    function start(minutes, mode) {
        var state = load();
        if (minutes) {
            state = idle(minutes);
            state.mode = mode || "focus";
        }
        state.running = true;
        state.endsAt = Date.now() + state.remaining;
        save(state);
    }

    function pause() {
        var state = load();
        if (!state.running) return;
        state.remaining = remaining(state);
        state.running = false;
        save(state);
    }

    function reset(minutes) {
        var state = load();
        save(idle(minutes || state.minutes));
    }

    function finish(state) {
        var wasFocus = state.mode === "focus";
        var next = wasFocus ? idle(BREAK_MINUTES) : idle(25);
        next.mode = wasFocus ? "break" : "focus";
        save(next);

        var progress = window.StudyMateProgress;
        if (wasFocus) {
            if (progress) progress.record("focus");
            if (progress) progress.toast({ kind: "goal", icon: "cup-hot", title: "Focus session complete",
                text: "Take a " + BREAK_MINUTES + "-minute break. You earned it.", duration: 6000 });
        } else if (progress) {
            progress.toast({ icon: "lightning-charge", title: "Break over", text: "Ready for another focus session?" });
        }
    }

    function tick() {
        var state = load();
        if (state.running && Date.now() >= state.endsAt) {
            finish(state);
            return;
        }
        if (state.running) {
            listeners.forEach(function (fn) { fn(snapshot()); });
            renderPill();
        }
    }

    function renderPill() {
        var pill = document.getElementById("focusPill");
        if (!pill) return;
        var snap = snapshot();
        var active = snap.running || snap.remaining < snap.total;
        pill.hidden = !active;
        if (!active) return;
        var label = pill.querySelector("[data-focus-time]");
        if (label) label.textContent = format(snap.remaining);
        pill.dataset.mode = snap.mode;
        pill.dataset.running = String(snap.running);
        pill.title = (snap.mode === "focus" ? "Focus" : "Break") + (snap.running ? " running" : " paused") + ". Open the dashboard to control it.";
    }

    window.StudyMateFocus = {
        start: start,
        pause: pause,
        reset: reset,
        snapshot: snapshot,
        format: format,
        onChange: function (fn) { listeners.push(fn); }
    };

    setInterval(tick, 1000);
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", renderPill);
    else renderPill();
})();
