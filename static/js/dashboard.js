/* ==========================================================
   StudyMate AI — dashboard: daily goal, streak, level,
   focus timer and achievements (data from core/progress.js
   and core/focus.js, stored in this browser).
   ========================================================== */

(function () {
    "use strict";

    var progress = window.StudyMateProgress;
    var focus = window.StudyMateFocus;
    if (!progress || !focus) return;

    var $ = function (id) { return document.getElementById(id); };
    var DAY_NAMES = ["S", "M", "T", "W", "T", "F", "S"];

    function renderProgress() {
        var info = progress.summary();
        var state = info.state;

        // Daily goal ring
        var ratio = Math.min(1, info.today / info.goal);
        $("goalRing").style.setProperty("--value", String(Math.round(ratio * 100)));
        $("goalRing").classList.toggle("is-complete", info.today >= info.goal);
        $("goalCount").textContent = Math.min(info.today, 99) + "/" + info.goal;
        $("goalValue").textContent = info.goal + " a day";
        $("goalText").textContent = info.today >= info.goal
            ? "Goal reached for today. Anything more is a bonus!"
            : (info.goal - info.today) + " more study action" + (info.goal - info.today === 1 ? "" : "s") +
              " to reach today's goal: notes, questions, quizzes or focus sessions.";

        // Streak + this week
        $("streakDays").textContent = info.streak;
        $("streakText").textContent = info.streak === 0
            ? "Study today to start a streak."
            : info.today ? "You've studied today. Come back tomorrow to keep it going."
                         : "Study today to keep your streak alive.";
        var week = $("weekDots");
        week.replaceChildren();
        var today = new Date();
        var monday = new Date(today);
        monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
        for (var i = 0; i < 7; i++) {
            var d = new Date(monday);
            d.setDate(monday.getDate() + i);
            var key = progress.dayKey(d);
            var li = document.createElement("li");
            var done = Boolean(state.days[key]);
            li.className = "week-dot" + (done ? " is-done" : "") + (key === progress.dayKey(today) ? " is-today" : "");
            li.innerHTML = '<span class="week-dot-mark">' + (done ? '<i class="bi bi-check-lg" aria-hidden="true"></i>' : "") +
                '</span><span class="week-dot-day">' + DAY_NAMES[d.getDay()] + "</span>";
            li.setAttribute("aria-label", d.toLocaleDateString(undefined, { weekday: "long" }) + (done ? ": studied" : ": not yet"));
            week.appendChild(li);
        }

        // Level
        var level = info.level;
        $("levelNumber").textContent = level.number;
        $("levelName").textContent = level.name;
        $("levelXp").textContent = level.xp.toLocaleString();
        $("levelBarFill").style.width = Math.round(level.progress * 100) + "%";
        $("levelBar").setAttribute("aria-valuenow", String(Math.round(level.progress * 100)));
        $("levelText").textContent = level.next
            ? (level.next.xp - level.xp) + " XP to " + level.next.name
            : "Top level reached. You're a StudyMate Legend!";

        // Achievements
        var list = $("achievementList");
        list.replaceChildren();
        var earned = 0;
        info.achievements.forEach(function (a) {
            if (a.earned) earned += 1;
            var item = document.createElement("li");
            item.className = "achievement" + (a.earned ? " is-earned" : "");
            item.title = a.text;
            item.innerHTML = '<span class="achievement-icon"><i class="bi bi-' + a.icon + '" aria-hidden="true"></i></span>' +
                '<span class="achievement-text"><strong></strong><small></small></span>';
            item.querySelector("strong").textContent = a.title;
            item.querySelector("small").textContent = a.earned ? "Unlocked" : a.text;
            list.appendChild(item);
        });
        $("achievementCount").textContent = earned;
        $("achievementTotal").textContent = info.achievements.length;
    }

    $("goalMinus").addEventListener("click", function () { progress.setGoal(progress.summary().goal - 1); });
    $("goalPlus").addEventListener("click", function () { progress.setGoal(progress.summary().goal + 1); });

    // ---------------- Focus timer ----------------
    var selectedMinutes = focus.snapshot().minutes || 25;

    function renderFocus(snap) {
        snap = snap || focus.snapshot();
        $("focusTime").textContent = focus.format(snap.remaining);
        $("focusMode").textContent = snap.mode === "focus" ? "Focus" : "Break";
        $("focus").dataset.mode = snap.mode;
        $("focus").dataset.running = String(snap.running);
        var startButton = $("focusStart");
        startButton.innerHTML = snap.running
            ? '<i class="bi bi-pause-fill" aria-hidden="true"></i> Pause'
            : snap.remaining < snap.total
                ? '<i class="bi bi-play-fill" aria-hidden="true"></i> Resume'
                : '<i class="bi bi-play-fill" aria-hidden="true"></i> ' + (snap.mode === "focus" ? "Start focus" : "Start break");
        document.querySelectorAll(".preset").forEach(function (button) {
            button.classList.toggle("is-selected", Number(button.dataset.minutes) === snap.minutes && snap.mode === "focus");
            button.disabled = snap.running;
        });
    }

    $("focusStart").addEventListener("click", function () {
        var snap = focus.snapshot();
        if (snap.running) focus.pause();
        else focus.start();
        renderFocus();
    });

    $("focusReset").addEventListener("click", function () {
        focus.reset(selectedMinutes);
        renderFocus();
    });

    document.querySelectorAll(".preset").forEach(function (button) {
        button.addEventListener("click", function () {
            selectedMinutes = Number(button.dataset.minutes);
            focus.reset(selectedMinutes);
            renderFocus();
        });
    });

    focus.onChange(renderFocus);
    progress.onChange(renderProgress);
    renderProgress();
    renderFocus();
})();
