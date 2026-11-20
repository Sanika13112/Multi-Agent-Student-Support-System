/*
=========================================
STUDYMATE AI - BRAINCHECK STUDENT FEEDBACK
=========================================

1. After a quiz is saved, the student rates it (1-5) and writes feedback.
2. POST /api/brain-check/feedback analyses it (VADER sentiment + aspects)
   and saves it next to the quiz score in MySQL.
3. A "Student Feedback & Sentiment" card in the Student Performance
   dashboard shows all feedback together with quiz performance
   (GET /api/brain-check/feedback-summary).

brain_check.js tells this file when an attempt is saved, using events:
    braincheck:saving, braincheck:attempt-saved, braincheck:attempt-save-failed

Safety: server text is always inserted with textContent, never innerHTML.
*/

document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const $ = id => document.getElementById(id);

    const form = {
        section: $("feedbackSection"),
        ratingInputs: document.querySelectorAll('input[name="feedbackRating"]'),
        ratingLabels: document.querySelectorAll("#feedbackRating label"),
        text: $("feedbackText"),
        submit: $("submitFeedbackButton"),
        status: $("feedbackStatus"),
        result: $("feedbackResult")
    };

    if (!form.section) return;

    let attemptId = null;       // the saved quiz attempt this feedback belongs to

    // Sentiment label -> existing badge colour classes in brain-check.css.
    const BADGE_CLASS = { Positive: "strong", Neutral: "average", Negative: "weak" };


    // =====================================
    // SMALL DOM HELPERS
    // =====================================

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    function badge(label) {
        return el("span", "bc-topic-badge " + (BADGE_CLASS[label] || "average"), label);
    }

    function signed(value) {
        const number = Number(value);
        return (number > 0 ? "+" : "") + number.toFixed(2);
    }

    function setStatus(message, type) {
        form.status.textContent = message;
        form.status.className = "bc-feedback-status" + (type ? " " + type : "");
    }


    // =====================================
    // STAR RATING
    // =====================================

    function selectedRating() {
        const checked = document.querySelector('input[name="feedbackRating"]:checked');
        return checked ? Number(checked.value) : null;
    }

    // Light up stars up to the chosen one.
    function paintStars() {
        const rating = selectedRating() || 0;
        form.ratingLabels.forEach(label => {
            label.classList.toggle("is-on", Number(label.dataset.value) <= rating);
        });
    }

    form.ratingInputs.forEach(input => input.addEventListener("change", paintStars));


    // =====================================
    // FORM STATE (driven by brain_check.js events)
    // =====================================

    function resetForm() {
        form.ratingInputs.forEach(input => { input.checked = false; });
        paintStars();
        form.text.value = "";
        form.result.hidden = true;
        form.result.replaceChildren();
        setStatus("");
    }

    document.addEventListener("braincheck:saving", () => {
        attemptId = null;
        resetForm();
        form.submit.disabled = true;
        setStatus("Saving your quiz result…");
    });

    document.addEventListener("braincheck:attempt-saved", event => {
        attemptId = event.detail.attemptId;
        form.submit.disabled = false;
        setStatus("");
    });

    document.addEventListener("braincheck:attempt-save-failed", () => {
        attemptId = null;
        form.submit.disabled = true;
        setStatus("Feedback needs the quiz result saved in MySQL first.", "error");
    });


    // =====================================
    // SUBMIT FEEDBACK
    // =====================================

    form.submit.addEventListener("click", async () => {
        const text = form.text.value.trim();

        if (!attemptId) {
            setStatus("Finish and save a quiz first.", "error");
            return;
        }
        if (text.length < 3) {
            setStatus("Please write a few words of feedback.", "error");
            form.text.focus();
            return;
        }

        form.submit.disabled = true;
        setStatus("Analysing your feedback…");

        try {
            const response = await fetch("/api/brain-check/feedback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ attempt_id: attemptId, feedback_text: text, rating: selectedRating() })
            });
            const data = await response.json().catch(() => ({}));

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Could not save your feedback.");
            }

            renderOwnResult(data.analysis);
            setStatus("Thanks! Feedback saved.", "success");
            loadSummary();
        } catch (error) {
            setStatus(error.message, "error");
        } finally {
            form.submit.disabled = !attemptId;
        }
    });

    // Show the student what the analysis found in their own feedback.
    function renderOwnResult(analysis) {
        const parts = [];

        const top = el("div", "bc-feedback-line");
        top.append(el("span", "", "Sentiment"), badge(analysis.sentiment),
            el("span", "muted", "compound " + signed(analysis.compound)));
        parts.push(top);

        if (analysis.aspects.length) {
            const aspects = el("div", "bc-feedback-line");
            aspects.append(el("span", "", "You talked about"));
            analysis.aspects.forEach(item => {
                const chip = el("span", "bc-aspect-chip " + (BADGE_CLASS[item.sentiment] || ""), item.aspect);
                chip.title = item.sentiment + " (" + signed(item.compound) + ")";
                aspects.append(chip);
            });
            parts.push(aspects);
        }

        if (analysis.rating_label) {
            const agree = analysis.agrees_with_rating;
            parts.push(el("p", "muted text-sm",
                "Your " + analysis.rating + "-star rating means " + analysis.rating_label + "; " +
                (agree ? "the sentiment model agrees." : "the sentiment model read it as " + analysis.sentiment + ".")));
        }

        form.result.replaceChildren(...parts);
        form.result.hidden = false;
    }


    // =====================================
    // DASHBOARD CARD: STUDENT FEEDBACK & SENTIMENT
    // =====================================

    // Put the card inside the Student Performance panel, before "Recent Quiz History".
    function ensureCard() {
        let card = $("bcFeedbackInsights");
        if (card) return card;

        const panel = $("bcHistoryPanel");
        if (!panel) return null;

        card = el("div", "bc-performance-card bc-feedback-insights");
        card.id = "bcFeedbackInsights";
        card.append(el("h3", "", "Student Feedback & Sentiment"), el("div", "", ""));

        const headings = panel.querySelectorAll(".bc-history-heading");
        const historyHeading = headings[headings.length - 1];
        if (headings.length > 1 && historyHeading) {
            panel.insertBefore(card, historyHeading);
        } else {
            panel.appendChild(card);
        }
        return card;
    }

    async function loadSummary() {
        const card = ensureCard();
        if (!card) return;
        const body = card.lastElementChild;

        try {
            const response = await fetch("/api/brain-check/feedback-summary");
            const data = await response.json().catch(() => ({}));

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Could not load feedback.");
            }
            renderSummary(body, data.summary, data.recent);
        } catch (error) {
            body.replaceChildren(el("p", "muted", error.message));
        }
    }

    function stat(value, label) {
        const box = el("div", "bc-feedback-stat");
        box.append(el("strong", "", value), el("span", "", label));
        return box;
    }

    // Labelled horizontal bar, reusing the dashboard's bar styles.
    function barRow(label, percent, valueText) {
        const row = el("div", "bc-subject-row");
        const track = el("div", "bc-bar-track");
        const fill = el("div", "bc-bar-fill");
        fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
        track.appendChild(fill);
        row.append(el("span", "bc-subject-name", label), track, el("span", "bc-subject-score", valueText));
        return row;
    }

    function smallTable(headers, rows) {
        const wrap = el("div", "bc-feedback-table-wrap");
        const table = el("table", "bc-feedback-table");
        const head = el("tr");
        headers.forEach(h => head.appendChild(el("th", "", h)));
        table.appendChild(el("thead")).appendChild(head);
        const body = el("tbody");
        rows.forEach(r => {
            const tr = el("tr");
            r.forEach(cell => tr.appendChild(el("td", "", cell)));
            body.appendChild(tr);
        });
        table.appendChild(body);
        wrap.appendChild(table);
        return wrap;
    }

    function describeCorrelation(r) {
        if (r === null || r === undefined) return "Needs at least 3 feedbacks with different scores.";
        const strength = Math.abs(r) >= 0.5 ? "strong" : Math.abs(r) >= 0.3 ? "moderate" : "weak";
        const direction = r > 0
            ? "higher scores come with more positive feedback"
            : "higher scores come with more negative feedback";
        return "r = " + r.toFixed(2) + " (" + strength + (Math.abs(r) >= 0.3 ? "; " + direction : " relationship") + ")";
    }

    function renderSummary(body, summary, recent) {
        if (!summary.total_feedback) {
            body.replaceChildren(el("p", "muted",
                "No feedback yet. Finish a quiz and tell us how it went; the sentiment analysis will appear here."));
            return;
        }

        const parts = [];

        // Headline numbers.
        const stats = el("div", "bc-feedback-stats");
        stats.append(
            stat(summary.total_feedback, "feedback received"),
            stat(summary.average_rating !== null ? summary.average_rating + " / 5" : "–", "average rating"),
            stat(signed(summary.average_compound), "average sentiment")
        );
        parts.push(stats);

        // Sentiment distribution and performance by sentiment.
        const grid = el("div", "bc-feedback-grid");

        const split = el("div");
        split.appendChild(el("h4", "bc-feedback-subheading", "How students feel"));
        ["Positive", "Neutral", "Negative"].forEach(label => {
            split.appendChild(barRow(label, summary.distribution_percentage[label],
                summary.distribution[label] + " (" + summary.distribution_percentage[label] + "%)"));
        });

        const performance = el("div");
        performance.appendChild(el("h4", "bc-feedback-subheading", "Average quiz score by sentiment"));
        ["Positive", "Neutral", "Negative"].forEach(label => {
            const average = summary.average_score_by_sentiment[label];
            performance.appendChild(barRow(label, average || 0, average === null ? "–" : average + "%"));
        });
        performance.appendChild(el("p", "muted text-sm",
            "Score vs sentiment: " + describeCorrelation(summary.score_sentiment_correlation)));

        grid.append(split, performance);
        parts.push(grid);

        // Aspects (what students talk about).
        if (summary.aspects.length) {
            parts.push(el("h4", "bc-feedback-subheading", "What students talk about"));
            parts.push(smallTable(["Aspect", "Mentions", "Positive", "Neutral", "Negative"],
                summary.aspects.map(a => [a.aspect, a.mentions, a.Positive, a.Neutral, a.Negative])));
        }

        // Evaluation of the sentiment model against star ratings.
        const evaluation = summary.evaluation;
        parts.push(el("h4", "bc-feedback-subheading", "Sentiment model vs students' star ratings"));
        if (evaluation) {
            parts.push(el("p", "muted text-sm",
                evaluation.samples + " rated feedback · accuracy " + evaluation.accuracy +
                " · precision " + evaluation.precision + " · recall " + evaluation.recall +
                " · F1 " + evaluation.f1_score + " (4–5★ = Positive, 3★ = Neutral, 1–2★ = Negative)"));
            parts.push(smallTable(["Stars say ↓ / model says →"].concat(evaluation.confusion_matrix_labels),
                evaluation.confusion_matrix.map((row, i) => [evaluation.confusion_matrix_labels[i]].concat(row))));
        } else {
            parts.push(el("p", "muted text-sm", "Appears once students give star ratings."));
        }

        // Latest feedback.
        parts.push(el("h4", "bc-feedback-subheading", "Latest feedback"));
        const list = el("div", "bc-feedback-list");
        recent.forEach(item => {
            const row = el("div", "bc-feedback-item");
            const head = el("div", "bc-feedback-line");
            head.append(badge(item.sentiment),
                el("span", "muted text-sm",
                    item.topic + " · score " + item.score_percentage + "%" +
                    (item.rating ? " · " + item.rating + "★" : "")));
            row.append(head, el("p", "bc-feedback-text", "“" + item.feedback_text + "”"));
            list.appendChild(row);
        });
        parts.push(list);

        body.replaceChildren(...parts);
    }

    loadSummary();
});
