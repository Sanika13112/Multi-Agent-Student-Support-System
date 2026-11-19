/* ==========================================================
   StudyMate AI — study progress (XP, levels, streak, daily goal,
   achievements, toasts and confetti). Loaded on every page.

   It listens to the app's own API calls, so page scripts and the
   backend need no changes:
     POST /api/quick-notes/upload      → notes created
     POST /api/voice-snap/notes        → notes created
     POST /api/ask-away/ask, /api/chat → question asked
     POST /api/brain-check/save-result → quiz completed (+score)
     POST /api/career-guidance/generate→ roadmap made
   Focus sessions are recorded by core/focus.js.

   Everything is stored in this browser only (localStorage).
   Public API: window.StudyMateProgress
   ========================================================== */

(function () {
    "use strict";

    var KEY = "studymate-progress";
    var DEFAULT_GOAL = 3;

    var ACTIONS = {
        notes:    { xp: 30, label: "creating study notes" },
        question: { xp: 10, label: "asking a question" },
        quiz:     { xp: 40, label: "finishing a quiz" },
        roadmap:  { xp: 25, label: "planning your career" },
        focus:    { xp: 20, label: "a focus session" }
    };

    var LEVELS = [
        { xp: 0, name: "Fresh Starter" },
        { xp: 100, name: "Curious Learner" },
        { xp: 250, name: "Note Taker" },
        { xp: 450, name: "Question Asker" },
        { xp: 750, name: "Concept Builder" },
        { xp: 1150, name: "Focused Scholar" },
        { xp: 1700, name: "Topic Master" },
        { xp: 2400, name: "Exam Ready" },
        { xp: 3300, name: "Study Champion" },
        { xp: 4500, name: "StudyMate Legend" }
    ];

    var ACHIEVEMENTS = [
        { id: "first-notes", icon: "journal-check", title: "First notes", text: "Create study notes once.",
          test: function (s) { return s.counts.notes >= 1; } },
        { id: "first-quiz", icon: "patch-check", title: "First quiz", text: "Finish a BrainCheck quiz.",
          test: function (s) { return s.counts.quiz >= 1; } },
        { id: "quiz-ace", icon: "trophy", title: "Quiz ace", text: "Score 80% or more in a quiz.",
          test: function (s) { return s.bestScore >= 80; } },
        { id: "perfect", icon: "stars", title: "Perfect score", text: "Score 100% in a quiz.",
          test: function (s) { return s.bestScore >= 100; } },
        { id: "curious", icon: "chat-heart", title: "Curious mind", text: "Ask 10 questions.",
          test: function (s) { return s.counts.question >= 10; } },
        { id: "focused", icon: "hourglass-split", title: "Deep focus", text: "Complete 3 focus sessions.",
          test: function (s) { return s.counts.focus >= 3; } },
        { id: "goal-day", icon: "bullseye", title: "Goal getter", text: "Reach your daily goal.",
          test: function (s) { return s.goalsMet >= 1; } },
        { id: "streak-3", icon: "fire", title: "On a roll", text: "Study 3 days in a row.",
          test: function (s) { return s.bestStreak >= 3; } },
        { id: "streak-7", icon: "lightning-charge", title: "Week warrior", text: "Study 7 days in a row.",
          test: function (s) { return s.bestStreak >= 7; } },
        { id: "planner", icon: "compass", title: "Future planner", text: "Make a career roadmap.",
          test: function (s) { return s.counts.roadmap >= 1; } },
        { id: "night-owl", icon: "moon-stars", title: "Night owl", text: "Study after 11 pm.",
          test: function (s) { return s.nightOwl; } },
        { id: "all-rounder", icon: "grid", title: "All-rounder", text: "Use notes, questions and quizzes.",
          test: function (s) { return s.counts.notes > 0 && s.counts.question > 0 && s.counts.quiz > 0; } }
    ];

    // ---------------- Storage ----------------
    function emptyState() {
        return {
            xp: 0,
            days: {},                 // "YYYY-MM-DD": number of actions
            counts: { notes: 0, question: 0, quiz: 0, roadmap: 0, focus: 0 },
            bestScore: 0,
            bestStreak: 0,
            goal: DEFAULT_GOAL,
            goalsMet: 0,
            goalDays: {},             // days on which the goal was reached
            nightOwl: false,
            achievements: {},         // id: timestamp
            recent: []                // last 8 actions {type, xp, time}
        };
    }

    function load() {
        try {
            var data = JSON.parse(localStorage.getItem(KEY) || "null");
            if (!data) return emptyState();
            var base = emptyState();
            for (var k in base) if (!(k in data)) data[k] = base[k];
            for (var c in base.counts) if (!(c in data.counts)) data.counts[c] = 0;
            return data;
        } catch (error) {
            return emptyState();
        }
    }

    function save(state) {
        try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (error) { /* storage full or blocked */ }
    }

    // ---------------- Dates and streak ----------------
    function dayKey(date) {
        var d = date || new Date();
        var m = String(d.getMonth() + 1).padStart(2, "0");
        var day = String(d.getDate()).padStart(2, "0");
        return d.getFullYear() + "-" + m + "-" + day;
    }

    function streak(state) {
        var count = 0;
        var date = new Date();
        // Today not studied yet doesn't break the streak; start from yesterday.
        if (!state.days[dayKey(date)]) date.setDate(date.getDate() - 1);
        while (state.days[dayKey(date)]) {
            count += 1;
            date.setDate(date.getDate() - 1);
        }
        return count;
    }

    function levelFor(xp) {
        var index = 0;
        for (var i = 0; i < LEVELS.length; i++) if (xp >= LEVELS[i].xp) index = i;
        var current = LEVELS[index];
        var next = LEVELS[index + 1] || null;
        var progress = next ? (xp - current.xp) / (next.xp - current.xp) : 1;
        return { number: index + 1, name: current.name, next: next, progress: progress, xp: xp };
    }

    function summary(state) {
        state = state || load();
        var today = state.days[dayKey()] || 0;
        return {
            state: state,
            today: today,
            goal: state.goal,
            streak: streak(state),
            level: levelFor(state.xp),
            achievements: ACHIEVEMENTS.map(function (a) {
                return { id: a.id, icon: a.icon, title: a.title, text: a.text, earned: Boolean(state.achievements[a.id]) };
            })
        };
    }

    // ---------------- Recording ----------------
    var listeners = [];

    function notify(detail) {
        listeners.forEach(function (fn) { try { fn(detail); } catch (error) { /* ignore */ } });
        document.dispatchEvent(new CustomEvent("studymate:progress", { detail: detail }));
    }

    function record(type, data) {
        var action = ACTIONS[type];
        if (!action) return null;
        data = data || {};

        var state = load();
        var before = levelFor(state.xp);
        var todayKey = dayKey();
        var xp = action.xp;

        if (type === "quiz" && typeof data.score === "number") {
            if (data.score >= 80) xp += 20;
            if (data.score >= 100) xp += 20;
            state.bestScore = Math.max(state.bestScore, Math.round(data.score));
        }

        state.xp += xp;
        state.counts[type] += 1;
        state.days[todayKey] = (state.days[todayKey] || 0) + 1;
        if (new Date().getHours() >= 23 || new Date().getHours() < 4) state.nightOwl = true;

        var goalJustMet = false;
        if (state.days[todayKey] >= state.goal && !state.goalDays[todayKey]) {
            state.goalDays[todayKey] = true;
            state.goalsMet += 1;
            goalJustMet = true;
        }

        state.bestStreak = Math.max(state.bestStreak, streak(state));
        state.recent.unshift({ type: type, xp: xp, time: Date.now() });
        state.recent = state.recent.slice(0, 8);

        var unlocked = [];
        ACHIEVEMENTS.forEach(function (a) {
            if (!state.achievements[a.id] && a.test(state)) {
                state.achievements[a.id] = Date.now();
                unlocked.push(a);
            }
        });

        save(state);
        var after = levelFor(state.xp);
        var detail = { type: type, xp: xp, levelUp: after.number > before.number, level: after,
                       goalJustMet: goalJustMet, unlocked: unlocked, summary: summary(state), data: data };

        celebrate(detail, action);
        notify(detail);
        return detail;
    }

    function setGoal(goal) {
        var state = load();
        state.goal = Math.max(1, Math.min(12, Math.round(goal)));
        save(state);
        notify({ type: "goal", summary: summary(state) });
    }

    function reset() {
        save(emptyState());
        notify({ type: "reset", summary: summary() });
    }

    // ---------------- Toasts ----------------
    function toastRegion() {
        var region = document.getElementById("toastRegion");
        if (!region) {
            region = document.createElement("div");
            region.id = "toastRegion";
            region.className = "toast-region";
            region.setAttribute("role", "status");
            region.setAttribute("aria-live", "polite");
            document.body.appendChild(region);
        }
        return region;
    }

    function toast(options) {
        var item = document.createElement("div");
        item.className = "toast" + (options.kind ? " toast-" + options.kind : "");

        var icon = document.createElement("span");
        icon.className = "toast-icon";
        icon.innerHTML = '<i class="bi bi-' + (options.icon || "stars") + '" aria-hidden="true"></i>';

        var body = document.createElement("div");
        body.className = "toast-body";
        var title = document.createElement("strong");
        title.textContent = options.title;
        body.appendChild(title);
        if (options.text) {
            var text = document.createElement("span");
            text.textContent = options.text;
            body.appendChild(text);
        }

        item.append(icon, body);
        toastRegion().appendChild(item);
        requestAnimationFrame(function () { item.classList.add("is-visible"); });

        setTimeout(function () {
            item.classList.remove("is-visible");
            setTimeout(function () { item.remove(); }, 400);
        }, options.duration || 3800);
    }

    // ---------------- Confetti (no library, respects reduced motion) ----------------
    function confetti() {
        if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        var canvas = document.createElement("canvas");
        canvas.className = "confetti-canvas";
        canvas.setAttribute("aria-hidden", "true");
        document.body.appendChild(canvas);
        var ctx = canvas.getContext("2d");
        var dpr = window.devicePixelRatio || 1;
        canvas.width = innerWidth * dpr;
        canvas.height = innerHeight * dpr;
        ctx.scale(dpr, dpr);

        var colours = ["#8b5cf6", "#6366f1", "#22d3ee", "#f472b6", "#fbbf24", "#34d399"];
        var pieces = [];
        for (var i = 0; i < 140; i++) {
            pieces.push({
                x: innerWidth / 2 + (Math.random() - 0.5) * 160,
                y: innerHeight * 0.35,
                vx: (Math.random() - 0.5) * 13,
                vy: Math.random() * -13 - 4,
                size: Math.random() * 7 + 4,
                rotation: Math.random() * Math.PI,
                spin: (Math.random() - 0.5) * 0.3,
                colour: colours[i % colours.length]
            });
        }

        var start = performance.now();
        function frame(now) {
            var elapsed = now - start;
            ctx.clearRect(0, 0, innerWidth, innerHeight);
            pieces.forEach(function (p) {
                p.vy += 0.32;
                p.vx *= 0.99;
                p.x += p.vx;
                p.y += p.vy;
                p.rotation += p.spin;
                ctx.save();
                ctx.globalAlpha = Math.max(0, 1 - elapsed / 2600);
                ctx.translate(p.x, p.y);
                ctx.rotate(p.rotation);
                ctx.fillStyle = p.colour;
                ctx.fillRect(-p.size / 2, -p.size / 3, p.size, p.size * 0.66);
                ctx.restore();
            });
            if (elapsed < 2600) requestAnimationFrame(frame);
            else canvas.remove();
        }
        requestAnimationFrame(frame);
    }

    function celebrate(detail, action) {
        var bigMoment = false;

        if (detail.levelUp) {
            bigMoment = true;
            toast({ kind: "level", icon: "rocket-takeoff", title: "Level " + detail.level.number + ": " + detail.level.name,
                    text: "You levelled up. Keep going!", duration: 5200 });
        }

        detail.unlocked.forEach(function (a) {
            bigMoment = true;
            toast({ kind: "badge", icon: a.icon, title: "Achievement unlocked: " + a.title, text: a.text, duration: 5200 });
        });

        if (detail.goalJustMet) {
            bigMoment = true;
            toast({ kind: "goal", icon: "bullseye", title: "Daily goal reached", text: "That's your study goal for today. Nice work!" });
        }

        if (detail.type === "quiz" && detail.data.score >= 80) bigMoment = true;

        toast({ icon: "plus-circle", title: "+" + detail.xp + " XP", text: "for " + action.label });
        if (bigMoment) confetti();
    }

    // ---------------- Listen to the app's API calls ----------------
    var TRACKED = [
        { method: "POST", path: "/api/quick-notes/upload", type: "notes" },
        { method: "POST", path: "/api/voice-snap/notes", type: "notes" },
        { method: "POST", path: "/api/ask-away/ask", type: "question" },
        { method: "POST", path: "/api/chat", type: "question" },
        { method: "POST", path: "/api/brain-check/save-result", type: "quiz" },
        { method: "POST", path: "/api/career-guidance/generate", type: "roadmap" }
    ];

    function match(url, method) {
        try {
            var path = new URL(url, location.origin).pathname;
            for (var i = 0; i < TRACKED.length; i++) {
                if (TRACKED[i].path === path && TRACKED[i].method === method) return TRACKED[i];
            }
        } catch (error) { /* ignore */ }
        return null;
    }

    if (window.fetch) {
        var originalFetch = window.fetch;
        window.fetch = function (input, init) {
            var url = typeof input === "string" ? input : (input && input.url) || "";
            var method = ((init && init.method) || (input && input.method) || "GET").toUpperCase();
            var rule = match(url, method);
            var promise = originalFetch.apply(this, arguments);
            if (!rule) return promise;

            return promise.then(function (response) {
                if (response.ok) {
                    response.clone().json().then(function (data) {
                        if (!data || data.success === false) return;
                        var extra = {};
                        if (rule.type === "quiz") {
                            try {
                                var body = JSON.parse((init && init.body) || "{}");
                                extra.score = Number(body.score_percentage);
                            } catch (error) { /* no score */ }
                        }
                        record(rule.type, extra);
                    }).catch(function () { /* not JSON */ });
                }
                return response;
            });
        };
    }

    // ---------------- Topbar streak pill ----------------
    function renderStreakPill() {
        var pill = document.getElementById("streakPill");
        if (!pill) return;
        var info = summary();
        var count = pill.querySelector("[data-streak-count]");
        if (count) count.textContent = info.streak;
        pill.dataset.active = info.today > 0 ? "true" : "false";
        pill.title = info.streak
            ? info.streak + "-day study streak. " + (info.today ? "You've studied today." : "Study today to keep it going.")
            : "Start a study streak today.";
        pill.setAttribute("aria-label", pill.title);
    }

    listeners.push(renderStreakPill);

    window.StudyMateProgress = {
        record: record,
        summary: summary,
        setGoal: setGoal,
        reset: reset,
        toast: toast,
        confetti: confetti,
        levels: LEVELS,
        dayKey: dayKey,
        onChange: function (fn) { listeners.push(fn); }
    };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", renderStreakPill);
    else renderStreakPill();
})();
