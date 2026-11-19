
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const $ = id => document.getElementById(id);

    const el = {
        setupForm: $("quizSetupForm"),
        setupWrapper: $("quizSetupFormWrapper"),
        subject: $("quizSubject"),
        topic: $("quizTopic"),
        difficulty: $("quizDifficulty"),
        count: $("questionCount"),
        timerEnabled: $("enableTimer"),
        explanationsEnabled: $("showExplanations"),
        generate: $("generateQuizButton"),
        status: $("quizStatus"),
        quizArea: $("quizArea"),
        resultsArea: $("resultsArea"),
        title: $("quizTitle"),
        subtitle: $("quizSubtitle"),
        timer: $("quizTimer"),
        timerDisplay: $("timerDisplay"),
        questionProgress: $("questionProgress"),
        progressPercent: $("progressPercent"),
        progressFill: $("progressFill"),
        questionArea: $("questionArea"),
        previous: $("previousQuestionButton"),
        next: $("nextQuestionButton"),
        submit: $("submitQuizButton"),
        resultMessage: $("resultMessage"),
        percentage: $("resultPercentage"),
        correct: $("correctCount"),
        incorrect: $("incorrectCount"),
        unanswered: $("unansweredCount"),
        review: $("answerReview"),
        restart: $("restartQuizButton")
    };

    let questions = [];
    let answers = [];
    let quizHistory = [];

    let currentIndex = 0;
    let timerInterval = null;
    let remainingSeconds = 0;
    let quizSubmitted = false;
    let currentQuizMeta = null;

    // ==========================================
    // STATUS MESSAGES
    // ==========================================

    function showStatus(message, type = "info") {
        if (!el.status) return;

        el.status.textContent = message;
        el.status.className = `bc-status ${type}`;
        el.status.style.display = "block";
    }

    function hideStatus() {
        if (!el.status) return;

        el.status.textContent = "";
        el.status.className = "bc-status";
        el.status.style.display = "none";
    }

    // ==========================================
    // QUESTION VALIDATION
    // ==========================================

    function normalizeKey(value) {
        return String(value ?? "")
            .trim()
            .replace(/^(option|answer)\s+/i, "")
            .replace(/[.):]$/, "")
            .toUpperCase();
    }

    function getOptionEntries(options) {
        if (Array.isArray(options)) {
            return options.map((option, index) => {
                const fallback = String.fromCharCode(65 + index);

                if (option && typeof option === "object") {
                    return [
                        normalizeKey(option.key || option.label || fallback),
                        String(option.text ?? option.value ?? "")
                    ];
                }

                return [fallback, String(option)];
            });
        }

        if (options && typeof options === "object") {
            return Object.entries(options).map(([key, value]) => [
                normalizeKey(key),
                String(value)
            ]);
        }

        return [];
    }

    function normalizeQuestion(question, index) {
        return {
            question: String(question.question || `Question ${index + 1}`),
            options: getOptionEntries(question.options).map(
                ([key, text]) => ({ key, text })
            ),
            correct_answer: normalizeKey(
                question.correct_answer || question.answer
            ),
            explanation: String(question.explanation || "")
        };
    }

    function validateQuestions(data, expectedCount) {
        if (!data || !Array.isArray(data.questions)) {
            throw new Error("The AI response does not contain valid questions.");
        }

        const normalized = data.questions.map(normalizeQuestion);

        if (normalized.length !== expectedCount) {
            throw new Error(
                `Expected ${expectedCount} questions, but received ${normalized.length}.`
            );
        }

        normalized.forEach((question, index) => {
            const keys = question.options.map(option => option.key);

            if (!question.question.trim()) {
                throw new Error(`Question ${index + 1} is empty.`);
            }

            if (question.options.length !== 4 || new Set(keys).size !== 4) {
                throw new Error(
                    `Question ${index + 1} must have four unique options.`
                );
            }

            if (!keys.includes(question.correct_answer)) {
                throw new Error(
                    `Question ${index + 1} has an invalid correct answer.`
                );
            }
        });

        return normalized;
    }

    // ==========================================
    // TIMER
    // ==========================================

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function formatTime(seconds) {
        const safe = Math.max(0, seconds);
        const minutes = Math.floor(safe / 60);
        const remainder = safe % 60;

        return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
    }

    function updateTimerDisplay() {
        if (!el.timerDisplay) return;

        el.timerDisplay.textContent = formatTime(remainingSeconds);
        el.timerDisplay.classList.toggle(
            "timer-warning",
            remainingSeconds <= 60
        );
    }

    function startTimer() {
        stopTimer();

        if (!el.timerEnabled?.checked) {
            if (el.timer) el.timer.style.display = "none";
            return;
        }

        remainingSeconds = questions.length * 60;

        if (el.timer) el.timer.style.display = "flex";

        updateTimerDisplay();

        timerInterval = setInterval(() => {
            remainingSeconds--;
            updateTimerDisplay();

            if (remainingSeconds <= 0) {
                stopTimer();
                window.alert("Time is up! Your quiz will be submitted.");
                submitQuiz(true);
            }
        }, 1000);
    }

    // ==========================================
    // GENERATE QUIZ
    // ==========================================

    async function generateQuiz(event) {
        event?.preventDefault();
        hideStatus();

        const subject = el.subject?.value.trim() || "";
        const topic = el.topic?.value.trim() || "";
        const difficulty = el.difficulty?.value || "Medium";
        const count = Number(el.count?.value || 5);

        if (!subject) {
            showStatus("Please select a subject.", "error");
            return;
        }

        if (!topic) {
            showStatus("Please enter a quiz topic.", "error");
            el.topic?.focus();
            return;
        }

        if (![5, 10, 15, 20].includes(count)) {
            showStatus("Please select a valid question count.", "error");
            return;
        }

        if (el.generate) {
            el.generate.disabled = true;
            el.generate.textContent = "Generating quiz...";
        }

        showStatus("Your AI tutor is preparing your questions...", "loading");
        stopTimer();

        try {
            const response = await fetch("/api/brain-check/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    subject,
                    topic,
                    difficulty,
                    question_count: count
                })
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok || data.success === false) {
                throw new Error(
                    data.error || data.message || "Quiz generation failed."
                );
            }

            questions = validateQuestions(data, count);
            answers = new Array(questions.length).fill(null);

            currentIndex = 0;
            quizSubmitted = false;

            currentQuizMeta = {
                subject,
                topic,
                difficulty,
                title: data.title || `${topic} Quiz`
            };

            if (el.title) el.title.textContent = currentQuizMeta.title;

            if (el.subtitle) {
                el.subtitle.textContent =
                    `${subject} • ${difficulty} • ${questions.length} Questions`;
            }

            if (el.setupWrapper) el.setupWrapper.style.display = "none";
            if (el.resultsArea) el.resultsArea.style.display = "none";
            if (el.quizArea) el.quizArea.style.display = "block";

            hideStatus();
            renderQuestion();
            startTimer();

            window.scrollTo({ top: 0, behavior: "smooth" });

        } catch (error) {
            console.error("Quiz generation error:", error);
            showStatus(error.message, "error");

        } finally {
            if (el.generate) {
                el.generate.disabled = false;
                el.generate.innerHTML =
                    '<i class="bi bi-stars"></i> Generate Quiz <i class="bi bi-arrow-right"></i>';
            }
        }
    }

    // ==========================================
    // DISPLAY QUESTION
    // ==========================================

    function renderQuestion() {
        if (!el.questionArea || !questions.length) return;

        const question = questions[currentIndex];
        const selected = answers[currentIndex];

        el.questionArea.replaceChildren();

        const card = document.createElement("div");
        card.className = "bc-question-card";

        const number = document.createElement("div");
        number.className = "bc-question-number";
        number.textContent =
            `QUESTION ${currentIndex + 1} OF ${questions.length}`;

        const heading = document.createElement("h3");
        heading.className = "bc-question-text";
        heading.textContent = question.question;

        const options = document.createElement("div");
        options.className = "bc-options-list";

        question.options.forEach(option => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "bc-option";
            button.setAttribute(
                "aria-pressed",
                String(selected === option.key)
            );

            if (selected === option.key) {
                button.classList.add("selected");
            }

            const letter = document.createElement("span");
            letter.className = "bc-option-letter";
            letter.textContent = option.key;

            const text = document.createElement("span");
            text.className = "bc-option-text";
            text.textContent = option.text;

            button.append(letter, text);

            button.addEventListener("click", () => {
                if (quizSubmitted) return;
                answers[currentIndex] = option.key;
                renderQuestion();
            });

            options.appendChild(button);
        });

        card.append(number, heading, options);
        el.questionArea.appendChild(card);

        updateProgress();
        updateNavigation();
    }

    // ==========================================
    // PROGRESS AND NAVIGATION
    // ==========================================

    function updateProgress() {
        const total = questions.length;
        const current = currentIndex + 1;
        const percentage = total
            ? Math.round((current / total) * 100)
            : 0;

        if (el.questionProgress) {
            el.questionProgress.textContent =
                `Question ${current} of ${total}`;
        }

        if (el.progressPercent) {
            el.progressPercent.textContent = `${percentage}%`;
        }

        if (el.progressFill) {
            el.progressFill.style.width = `${percentage}%`;
        }
    }

    function updateNavigation() {
        if (el.previous) {
            el.previous.disabled = currentIndex === 0;
        }

        if (el.next) {
            el.next.style.display =
                currentIndex === questions.length - 1
                    ? "none"
                    : "inline-flex";
        }

        if (el.submit) {
            el.submit.style.display =
                currentIndex === questions.length - 1
                    ? "inline-flex"
                    : "none";
        }
    }

    function goPrevious() {
        if (currentIndex > 0) {
            currentIndex--;
            renderQuestion();
        }
    }

    function goNext() {
        if (currentIndex < questions.length - 1) {
            currentIndex++;
            renderQuestion();
        }
    }

    // ==========================================
    // SCORE CALCULATION
    // ==========================================

    function getOptionText(question, key) {
        const option = question.options.find(item => item.key === key);

        return option
            ? `${key}. ${option.text}`
            : (key || "Not answered");
    }

    function calculateResult() {
        let correct = 0;
        let incorrect = 0;
        let unanswered = 0;

        questions.forEach((question, index) => {
            if (answers[index] === null) {
                unanswered++;
            } else if (answers[index] === question.correct_answer) {
                correct++;
            } else {
                incorrect++;
            }
        });

        const total = questions.length;

        return {
            correct,
            incorrect,
            unanswered,
            total,
            percentage: total
                ? Math.round((correct / total) * 100)
                : 0
        };
    }

    // ==========================================
    // LOAD QUIZ HISTORY FROM MYSQL
    // ==========================================

    async function loadHistory() {
        try {
            const response = await fetch("/api/brain-check/history");
            const data = await response.json().catch(() => ({}));

            if (!response.ok || data.success === false) {
                throw new Error(
                    data.message || data.error || "Could not load quiz history."
                );
            }

            quizHistory = Array.isArray(data.history) ? data.history : [];
            renderHistory();

        } catch (error) {
            console.error("History loading error:", error);
            quizHistory = [];
            renderHistory("Unable to load quiz history. Check Flask and MySQL.");
        }
    }

    // ==========================================
    // SAVE QUIZ RESULT TO MYSQL
    // ==========================================

    async function saveAttempt(result) {
        const payload = {
            subject: currentQuizMeta?.subject || "Unknown subject",
            topic: currentQuizMeta?.topic || "Untitled topic",
            difficulty: currentQuizMeta?.difficulty || "Medium",
            total_questions: result.total,
            correct_answers: result.correct,
            incorrect_answers: result.incorrect,
            unanswered: result.unanswered,
            score_percentage: result.percentage
        };

        try {
            const response = await fetch(
                "/api/brain-check/save-result",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                }
            );

            const data = await response.json().catch(() => ({}));

            if (!response.ok || data.success === false) {
                throw new Error(
                    data.message || data.error || "Could not save quiz result."
                );
            }

            showStatus("Your quiz result has been saved to MySQL.", "success");
            await loadHistory();

        } catch (error) {
            console.error("Quiz save error:", error);
            showStatus(
                "Quiz completed, but saving failed: " + error.message,
                "error"
            );
        }
    }

    // ==========================================
    // DASHBOARD STYLES
    // ==========================================

    function addDashboardStyles() {
        // Styles for the performance dashboard now live in
        // static/css/pages/brain-check.css (shared design system).
    }

    // ==========================================
    // CREATE DASHBOARD
    // ==========================================

    function ensureHistoryPanel() {
        if (!el.setupWrapper || $("bcHistoryPanel")) return;

        addDashboardStyles();

        const panel = document.createElement("section");
        panel.id = "bcHistoryPanel";
        panel.className = "bc-history-panel";

        panel.innerHTML = `
            <div class="bc-history-heading">
                <div>
                    <span class="bc-section-label">YOUR LEARNING JOURNEY</span>
                    <h2>Student Performance</h2>
                    <p>Track your quiz results and learning progress.</p>
                </div>
            </div>

            <div class="bc-history-summary" id="bcHistorySummary"></div>

            <div class="bc-performance-grid">
                <div class="bc-performance-card">
                    <h3>Subject-wise Performance</h3>
                    <div id="bcSubjectAnalytics"></div>
                </div>

                <div class="bc-performance-card">
                    <h3>Recent Score Trend</h3>
                    <div id="bcScoreTrend"></div>
                </div>
            </div>

            <div class="bc-performance-card bc-topic-insights">
                <h3>Topic Performance Analysis</h3>
                <div id="bcTopicInsights"></div>
            </div>

            <div class="bc-performance-card bc-study-recommendations">
                <h3>Personalized Study Recommendations</h3>
                <div id="bcStudyRecommendations"></div>
            </div>

            <div class="bc-history-heading">
                <div>
                    <h2>Recent Quiz History</h2>
                    <p>Your saved quiz attempts</p>
                </div>
            </div>

            <div class="bc-history-list" id="bcHistoryList"></div>
        `;

        el.setupWrapper.insertAdjacentElement("afterend", panel);
    }

    // ==========================================
    // WEAK TOPIC DETECTION
    // ==========================================

    function renderTopicInsights(history) {
        const container = $("bcTopicInsights");
        const recommendations = $("bcStudyRecommendations");

        if (!container || !recommendations) return;

        container.replaceChildren();
        recommendations.replaceChildren();

        if (!history.length) {
            container.textContent =
                "Complete quizzes to identify your strong and weak topics.";

            recommendations.textContent =
                "Personalized study recommendations will appear here.";

            return;
        }

        const topicMap = new Map();

        history.forEach(attempt => {
            const topic = attempt.topic || "Other";

            if (!topicMap.has(topic)) {
                topicMap.set(topic, []);
            }

            topicMap.get(topic).push(
                Number(attempt.score_percentage || 0)
            );
        });

        const topics = [...topicMap.entries()].map(([topic, scores]) => {
            const average = Math.round(
                scores.reduce((sum, score) => sum + score, 0) / scores.length
            );

            let status = "Average";

            if (average < 50) {
                status = "Weak";
            } else if (average >= 80) {
                status = "Strong";
            }

            return {
                topic,
                average,
                status,
                attempts: scores.length
            };
        });

        // Display topic scores and status.
        topics.forEach(item => {
            const row = document.createElement("div");
            row.className = "bc-topic-row";

            const details = document.createElement("div");
            details.className = "bc-topic-details";

            const name = document.createElement("strong");
            name.textContent = item.topic;

            const score = document.createElement("span");
            score.textContent =
                `${item.average}% • ${item.attempts} attempt(s)`;

            details.append(name, score);

            const badge = document.createElement("span");
            badge.className =
                `bc-topic-badge ${item.status.toLowerCase()}`;
            badge.textContent = item.status;

            row.append(details, badge);
            container.appendChild(row);
        });

        // Build personalized recommendations.
        const messages = [];

        topics.forEach(item => {
            if (item.status === "Weak") {
                messages.push({
                    title: `Revise ${item.topic}`,
                    message:
                        `Your average score is ${item.average}%. ` +
                        "Review the fundamentals and practise more questions."
                });
            } else if (item.status === "Average") {
                messages.push({
                    title: `Improve ${item.topic}`,
                    message:
                        `Your average score is ${item.average}%. ` +
                        "Revise important concepts and attempt another quiz."
                });
            } else {
                messages.push({
                    title: `Keep improving ${item.topic}`,
                    message:
                        `Great work! You scored ${item.average}%. ` +
                        "Try advanced questions to strengthen your knowledge."
                });
            }
        });

        messages.forEach(item => {
            const card = document.createElement("div");
            card.className = "bc-recommendation-item";

            const title = document.createElement("strong");
            title.textContent = item.title;

            const description = document.createElement("p");
            description.textContent = item.message;

            card.append(title, description);
            recommendations.appendChild(card);
        });
    }

    // ==========================================
    // RENDER PERFORMANCE DASHBOARD
    // ==========================================

    function renderHistory(errorMessage = "") {
        ensureHistoryPanel();

        const summary = $("bcHistorySummary");
        const list = $("bcHistoryList");
        const subjectAnalytics = $("bcSubjectAnalytics");
        const scoreTrend = $("bcScoreTrend");

        if (!summary || !list || !subjectAnalytics || !scoreTrend) {
            return;
        }

        const history = quizHistory;

        // Render topic analysis.
        renderTopicInsights(history);

        const total = history.length;
        const scores = history.map(
            item => Number(item.score_percentage || 0)
        );

        const average = total
            ? Math.round(scores.reduce((sum, value) => sum + value, 0) / total)
            : 0;

        const best = total ? Math.max(...scores) : 0;

        // Summary cards.
        summary.replaceChildren();

        [
            ["Total quizzes", total, "bi-journal-check"],
            ["Average score", `${average}%`, "bi-graph-up"],
            ["Best score", `${best}%`, "bi-trophy"]
        ].forEach(([label, value, icon]) => {
            const card = document.createElement("div");
            card.className = "bc-history-stat";

            const symbol = document.createElement("i");
            symbol.className = `bi ${icon}`;

            const strong = document.createElement("strong");
            strong.textContent = value;

            const caption = document.createElement("span");
            caption.textContent = label;

            card.append(symbol, strong, caption);
            summary.appendChild(card);
        });

        list.replaceChildren();
        subjectAnalytics.replaceChildren();
        scoreTrend.replaceChildren();

        if (errorMessage) {
            const error = document.createElement("div");
            error.className = "bc-history-empty";
            error.textContent = errorMessage;
            list.appendChild(error);

            subjectAnalytics.textContent =
                "Analytics will appear when history is available.";

            scoreTrend.textContent =
                "Score trend will appear when history is available.";

            return;
        }

        if (!history.length) {
            const empty = document.createElement("div");
            empty.className = "bc-history-empty";
            empty.textContent =
                "No quiz attempts yet. Generate your first quiz to start tracking progress.";

            list.appendChild(empty);

            subjectAnalytics.textContent =
                "Complete quizzes in different subjects to compare performance.";

            scoreTrend.textContent =
                "Complete at least one quiz to see your score trend.";

            return;
        }

        // Subject-wise performance.
        const subjectMap = new Map();

        history.forEach(attempt => {
            const subject = attempt.subject || "Other";

            if (!subjectMap.has(subject)) {
                subjectMap.set(subject, []);
            }

            subjectMap.get(subject).push(
                Number(attempt.score_percentage || 0)
            );
        });

        [...subjectMap.entries()]
            .map(([subject, values]) => ({
                subject,
                average: Math.round(
                    values.reduce((sum, value) => sum + value, 0) /
                    values.length
                )
            }))
            .sort((a, b) => b.average - a.average)
            .forEach(item => {
                const row = document.createElement("div");
                row.className = "bc-subject-row";

                const name = document.createElement("span");
                name.className = "bc-subject-name";
                name.textContent = item.subject;

                const track = document.createElement("div");
                track.className = "bc-bar-track";
                track.setAttribute("role", "progressbar");
                track.setAttribute("aria-valuenow", String(item.average));
                track.setAttribute("aria-valuemin", "0");
                track.setAttribute("aria-valuemax", "100");

                const fill = document.createElement("div");
                fill.className = "bc-bar-fill";
                fill.style.width =
                    `${Math.max(0, Math.min(100, item.average))}%`;

                track.appendChild(fill);

                const score = document.createElement("span");
                score.className = "bc-subject-score";
                score.textContent = `${item.average}%`;

                row.append(name, track, score);
                subjectAnalytics.appendChild(row);
            });

        // Recent score trend.
        const recent = history.slice(0, 5).reverse();
        const chart = document.createElement("div");
        chart.className = "bc-trend-chart";

        recent.forEach((attempt, index) => {
            const value = Math.max(
                0,
                Math.min(100, Number(attempt.score_percentage || 0))
            );

            const column = document.createElement("div");
            column.className = "bc-trend-column";

            const label = document.createElement("span");
            label.className = "bc-trend-value";
            label.textContent = `${value}%`;

            const bar = document.createElement("div");
            bar.className = "bc-trend-bar";
            bar.style.height = `${Math.max(value, 3)}%`;

            const dateLabel = document.createElement("span");
            dateLabel.className = "bc-trend-label";
            dateLabel.textContent = `#${index + 1}`;

            column.append(label, bar, dateLabel);
            chart.appendChild(column);
        });

        scoreTrend.appendChild(chart);

        // Recent quiz attempts.
        history.forEach(attempt => {
            const row = document.createElement("article");
            row.className = "bc-history-item";

            const details = document.createElement("div");
            details.className = "bc-history-details";

            const title = document.createElement("strong");
            title.textContent = attempt.topic
                ? `${attempt.topic} Quiz`
                : "BrainCheck Quiz";

            const meta = document.createElement("span");
            const dateValue = attempt.created_at || attempt.date;
            const date = dateValue ? new Date(dateValue) : null;

            const dateText =
                date && !Number.isNaN(date.getTime())
                    ? date.toLocaleString()
                    : "";

            meta.textContent =
                `${attempt.subject || "Subject"} • ` +
                `${attempt.topic || "Topic"} • ` +
                `${attempt.difficulty || "Medium"} • ${dateText}`;

            details.append(title, meta);

            const scoreWrap = document.createElement("div");
            scoreWrap.className = "bc-history-score-wrap";

            const score = document.createElement("strong");
            score.className = "bc-history-score";
            score.textContent =
                `${Number(attempt.score_percentage || 0)}%`;

            const count = document.createElement("small");
            count.textContent =
                `${Number(attempt.correct_answers || 0)}/` +
                `${Number(attempt.total_questions || 0)} correct`;

            scoreWrap.append(score, count);
            row.append(details, scoreWrap);
            list.appendChild(row);
        });
    }

    // ==========================================
    // ANSWER REVIEW
    // ==========================================

    function renderAnswerReview() {
        if (!el.review) return;

        el.review.replaceChildren();

        questions.forEach((question, index) => {
            const selected = answers[index];

            const isCorrect =
                selected === question.correct_answer;

            const card = document.createElement("article");
            card.className = "bc-review-card";

            const heading = document.createElement("h4");
            heading.textContent =
                `Q${index + 1}. ${question.question}`;

            const status = document.createElement("span");

            status.className =
                selected === null
                    ? "bc-review-status unanswered"
                    : isCorrect
                        ? "bc-review-status correct"
                        : "bc-review-status incorrect";

            status.textContent =
                selected === null
                    ? "Not answered"
                    : isCorrect
                        ? "Correct"
                        : "Incorrect";

            const yourAnswer = document.createElement("p");
            yourAnswer.textContent =
                `Your answer: ${getOptionText(question, selected)}`;

            const correctAnswer = document.createElement("p");
            correctAnswer.textContent =
                `Correct answer: ${getOptionText(question, question.correct_answer)}`;

            card.append(
                heading,
                status,
                yourAnswer,
                correctAnswer
            );

            if (
                el.explanationsEnabled?.checked &&
                question.explanation
            ) {
                const explanation = document.createElement("p");
                explanation.className = "bc-explanation";
                explanation.textContent =
                    `Explanation: ${question.explanation}`;

                card.appendChild(explanation);
            }

            el.review.appendChild(card);
        });
    }

    // ==========================================
    // DISPLAY RESULTS
    // ==========================================

    function displayResults(result) {
        if (el.quizArea) {
            el.quizArea.style.display = "none";
        }

        if (el.resultsArea) {
            el.resultsArea.style.display = "block";
        }

        if (el.correct) {
            el.correct.textContent = result.correct;
        }

        if (el.incorrect) {
            el.incorrect.textContent = result.incorrect;
        }

        if (el.unanswered) {
            el.unanswered.textContent = result.unanswered;
        }

        if (el.percentage) {
            el.percentage.textContent = `${result.percentage}%`;
        }

        if (el.resultMessage) {
            if (result.percentage >= 80) {
                el.resultMessage.textContent =
                    "Excellent work! You have mastered this topic.";
            } else if (result.percentage >= 60) {
                el.resultMessage.textContent =
                    "Good job! Keep practising to improve.";
            } else if (result.percentage >= 40) {
                el.resultMessage.textContent =
                    "You're making progress. Revise and try again.";
            } else {
                el.resultMessage.textContent =
                    "Keep learning! Review the explanations and try again.";
            }
        }

        renderAnswerReview();

        // Save result in MySQL.
        saveAttempt(result);

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    // ==========================================
    // SUBMIT QUIZ
    // ==========================================

    function submitQuiz(autoSubmit = false) {
        if (quizSubmitted || !questions.length) return;

        const unanswered = answers.filter(
            answer => answer === null
        ).length;

        if (unanswered > 0 && !autoSubmit) {
            const confirmed = window.confirm(
                `You have ${unanswered} unanswered question(s). Do you want to submit the quiz?`
            );

            if (!confirmed) return;
        }

        quizSubmitted = true;
        stopTimer();

        const result = calculateResult();
        displayResults(result);
    }

    // ==========================================
    // RESTART QUIZ
    // ==========================================

    function restartQuiz() {
        stopTimer();

        questions = [];
        answers = [];

        currentIndex = 0;
        remainingSeconds = 0;

        quizSubmitted = false;
        currentQuizMeta = null;

        if (el.quizArea) {
            el.quizArea.style.display = "none";
        }

        if (el.resultsArea) {
            el.resultsArea.style.display = "none";
        }

        if (el.setupWrapper) {
            el.setupWrapper.style.display = "block";
        }

        if (el.review) {
            el.review.replaceChildren();
        }

        hideStatus();

        // Refresh history and dashboard from MySQL.
        loadHistory();

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    // ==========================================
    // AI PERSONALIZED STUDY PLAN PANEL
    // ==========================================

    function createStudyPlanPanel() {
        if (document.getElementById("bcStudyPlanPanel")) return;

        const panel = document.createElement("section");

        panel.id = "bcStudyPlanPanel";
        panel.className = "bc-study-plan-panel";

        panel.innerHTML = `
            <div class="bc-study-plan-header">
                <div>
                    <span class="bc-section-label">AI POWERED LEARNING</span>
                    <h2>Your Personalized Study Plan</h2>
                    <p>Get revision guidance based on your quiz performance.</p>
                </div>

                <button
                    type="button"
                    id="generateStudyPlanButton"
                    class="bc-study-plan-button"
                >
                    <i class="bi bi-stars"></i>
                    Generate My Study Plan
                </button>
            </div>

            <div
                id="studyPlanStatus"
                class="bc-study-plan-status"
                style="display:none;"
            ></div>

            <div
                id="studyPlanAnalysis"
                class="bc-study-plan-analysis"
            ></div>

            <div
                id="studyPlanContent"
                class="bc-study-plan-content"
            ></div>
        `;

        if (el.setupWrapper) {
            el.setupWrapper.insertAdjacentElement("afterend", panel);
        }

        document
            .getElementById("generateStudyPlanButton")
            ?.addEventListener("click", generateStudyPlan);
    }

    // ==========================================
    // GENERATE AI STUDY PLAN
    // ==========================================

    async function generateStudyPlan() {
        const button = $("generateStudyPlanButton");
        const status = $("studyPlanStatus");
        const analysis = $("studyPlanAnalysis");
        const content = $("studyPlanContent");

        if (!button || !status || !content) return;

        button.disabled = true;
        button.innerHTML =
            '<i class="bi bi-arrow-repeat"></i> Generating...';

        status.style.display = "block";
        status.className = "bc-study-plan-status";
        status.textContent =
            "Qwen AI is analyzing your quiz performance. Please wait...";

        content.replaceChildren();
        analysis.replaceChildren();

        try {
            const response = await fetch(
                "/api/brain-check/study-plan",
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            const data = await response.json().catch(() => ({}));

            if (!response.ok || data.success === false) {
                throw new Error(
                    data.message ||
                    data.error ||
                    "Unable to generate your study plan."
                );
            }

            // Display topic-wise performance.
            if (Array.isArray(data.topic_analysis)) {
                data.topic_analysis.forEach(item => {
                    const card = document.createElement("div");

                    card.className =
                        `bc-topic-analysis ${String(item.status).toLowerCase()}`;

                    const title = document.createElement("strong");
                    title.textContent = item.topic;

                    const score = document.createElement("span");
                    score.textContent =
                        `${item.average_score}% • ${item.status}`;

                    card.append(title, score);
                    analysis.appendChild(card);
                });
            }

            // Display AI-generated study plan safely.
            const heading = document.createElement("h3");
            heading.textContent = "Your AI Study Recommendations";

            const plan = document.createElement("pre");
            plan.className = "bc-study-plan-text";
            plan.textContent = data.study_plan || "";

            content.append(heading, plan);

            status.textContent =
                "Your personalized study plan is ready!";

            status.className =
                "bc-study-plan-status success";

        } catch (error) {
            console.error("AI Study Plan Error:", error);

            status.textContent =
                error.message || "Something went wrong.";

            status.className =
                "bc-study-plan-status error";

        } finally {
            button.disabled = false;
            button.innerHTML =
                '<i class="bi bi-stars"></i> Generate My Study Plan';
        }
    }

    // ==========================================
    // EVENT LISTENERS
    // ==========================================

    el.setupForm?.addEventListener(
        "submit",
        generateQuiz
    );

    el.previous?.addEventListener(
        "click",
        goPrevious
    );

    el.next?.addEventListener(
        "click",
        goNext
    );

    el.submit?.addEventListener(
        "click",
        () => submitQuiz(false)
    );

    el.restart?.addEventListener(
        "click",
        restartQuiz
    );

    // ==========================================
    // INITIAL PAGE SETUP
    // ==========================================

    if (el.quizArea) {
        el.quizArea.style.display = "none";
    }

    if (el.resultsArea) {
        el.resultsArea.style.display = "none";
    }

    if (el.timer) {
        el.timer.style.display = "none";
    }

    // Create dashboard and AI study plan panel.
    ensureHistoryPanel();
    createStudyPlanPanel();
    loadHistory();

});
