/*
=========================================
STUDYMATE AI - NLP PIPELINE PAGE
=========================================

1. Collect the document (file or pasted text) and the options.
2. POST them to /api/nlp-pipeline/run.
3. Show the report: one panel per Course Outcome (CO1-CO4),
   one card per stage, with that stage's real output.

Safety: every value from the server is inserted with textContent
(never innerHTML), so text from a document cannot inject HTML.
*/

document.addEventListener("DOMContentLoaded", function () {

    const fileInput = document.getElementById("pipelineFile");
    const textInput = document.getElementById("pipelineText");
    const useLlm = document.getElementById("useLlm");
    const translateTo = document.getElementById("translateTo");
    const numTopics = document.getElementById("numTopics");
    const runButton = document.getElementById("runPipeline");
    const statusBox = document.getElementById("pipelineStatus");
    const output = document.getElementById("pipelineOutput");

    // Rubric rows, so each group shows what it is marked on.
    const CO_GROUPS = [
        { co: "CO1", marks: 7, title: "Text extraction, preprocessing, cleaning and vectorization" },
        { co: "CO2", marks: 8, title: "Sentiment analysis and information extraction, with evaluation" },
        { co: "CO3", marks: 7, title: "Topic modeling and multilingual NLP with a cloud AI service" },
        { co: "CO4", marks: 8, title: "Generative AI: prompt engineering, integration and working demo" }
    ];

    const STATUS_LABEL = { done: "Done", skipped: "Skipped", failed: "Failed" };


    // =====================================
    // SMALL DOM HELPERS
    // =====================================

    // Create an element with an optional class and text.
    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    // A row of small labelled pills, e.g. key terms.
    function chips(values) {
        const row = el("div", "np-chips");
        values.forEach(function (value) { row.appendChild(el("span", "badge", value)); });
        return row;
    }

    // A simple table from a header list and rows of cell values.
    function table(headers, rows) {
        const wrapper = el("div", "np-table-wrap");
        const tableNode = el("table", "np-table");
        const head = el("tr");
        headers.forEach(function (header) { head.appendChild(el("th", "", header)); });
        tableNode.appendChild(el("thead")).appendChild(head);
        const body = el("tbody");
        rows.forEach(function (row) {
            const tr = el("tr");
            row.forEach(function (cell) { tr.appendChild(el("td", "", cell)); });
            body.appendChild(tr);
        });
        tableNode.appendChild(body);
        wrapper.appendChild(tableNode);
        return wrapper;
    }

    // Label + value pairs in the app's meta grid.
    function metaGrid(pairs) {
        const grid = el("div", "meta-grid");
        pairs.forEach(function (pair) {
            const item = el("div", "meta-item");
            item.appendChild(el("span", "", pair[0]));
            item.appendChild(el("strong", "", pair[1]));
            grid.appendChild(item);
        });
        return grid;
    }

    function heading(text) {
        return el("h4", "np-subheading", text);
    }

    function quote(text) {
        return el("pre", "np-text", text);
    }

    function setStatus(message, type) {
        statusBox.textContent = message;
        statusBox.className = "status" + (type ? " " + type : "");
    }


    // =====================================
    // STAGE DETAIL RENDERERS (one per stage number)
    // =====================================

    const RENDERERS = {
        1: function (d) {
            return [
                metaGrid([["Source", d.source], ["Pages", d.pages], ["Words", d.words.toLocaleString()]]),
                heading("First 300 characters"),
                quote(d.preview)
            ];
        },
        2: function (d) {
            return [heading("Before"), quote(d.before_sample), heading("After"), quote(d.after_sample)];
        },
        3: function (d) {
            return [
                metaGrid([
                    ["Tokens", d.tokens.toLocaleString()],
                    ["Stop words removed", d.stopwords_removed.toLocaleString()],
                    ["1-letter tokens removed", d.single_characters_removed.toLocaleString()],
                    ["Content tokens", d.content_tokens.toLocaleString()],
                    ["Unique stems", d.unique_stems.toLocaleString()]
                ]),
                heading("Token → stem (Porter)"),
                table(["Token", "Stem"], d.sample_stems.map(function (s) { return [s.token, s.stem]; })),
                heading("Most frequent stems"),
                chips(d.most_frequent_stems.map(function (s) { return s.stem + " × " + s.count; }))
            ];
        },
        4: function (d) {
            return [
                metaGrid([
                    ["Matrix", d.matrix_shape[0] + " × " + d.matrix_shape[1].toLocaleString()],
                    ["Sparsity", d.sparsity_percent + "%"],
                    ["N-grams", d.ngram_range]
                ]),
                heading("Highest average TF-IDF"),
                table(["Term", "Mean TF-IDF"], d.top_terms.map(function (t) { return [t.term, t.mean_tfidf]; }))
            ];
        },
        5: function (d) {
            const parts = [metaGrid([
                ["Overall", d.overall_sentiment],
                ["Avg compound", d.average_compound],
                ["Sentences", d.total_sentences]
            ])];
            parts.push(chips([
                "Positive " + d.distribution_percentage.positive + "%",
                "Neutral " + d.distribution_percentage.neutral + "%",
                "Negative " + d.distribution_percentage.negative + "%"
            ]));
            if (d.most_positive) {
                parts.push(heading("Most positive sentence (" + d.most_positive.scores.compound + ")"), quote(d.most_positive.sentence));
            }
            if (d.most_negative) {
                parts.push(heading("Most negative sentence (" + d.most_negative.scores.compound + ")"), quote(d.most_negative.sentence));
            }
            parts.push(el("p", "field-hint", d.note));
            return parts;
        },
        6: function (d) {
            const parts = [heading("Definitions")];
            parts.push(d.definitions.length
                ? table(["Term", "Definition"], d.definitions.map(function (x) { return [x.term, x.definition]; }))
                : el("p", "muted", "No definition sentences found."));
            parts.push(heading("Acronyms"));
            parts.push(d.acronyms.length
                ? table(["Acronym", "Expansion"], d.acronyms.map(function (x) { return [x.acronym, x.expansion]; }))
                : el("p", "muted", "No acronyms found."));
            parts.push(heading("Key terms (TF-IDF)"), chips(d.key_terms.map(function (t) { return t.term; })));
            if (d.complexity_expressions.length) {
                parts.push(heading("Complexity expressions"), chips(d.complexity_expressions));
            }
            if (d.years.length || d.dates.length) {
                parts.push(heading("Dates and years"), chips(d.dates.concat(d.years)));
            }
            return parts;
        },
        7: function (d) {
            const s = d.sentiment;
            const x = d.extraction;
            const matrixRows = s.confusion_matrix.map(function (row, i) {
                return [s.confusion_matrix_labels[i]].concat(row);
            });
            return [
                heading("Metrics on hand-labelled test data"),
                table(["Model", "Samples", "Precision", "Recall", "F1", "Accuracy"], [
                    ["Sentiment (VADER)", s.test_samples, s.precision, s.recall, s.f1_score, s.accuracy],
                    ["Definition extraction", x.test_samples, x.definitions.precision, x.definitions.recall, x.definitions.f1_score, "–"],
                    ["Acronym extraction", x.test_samples, x.acronyms.precision, x.acronyms.recall, x.acronyms.f1_score, "–"]
                ]),
                heading("Sentiment confusion matrix (rows = true, columns = predicted)"),
                table([""].concat(s.confusion_matrix_labels), matrixRows)
            ];
        },
        8: function (d) {
            return [
                metaGrid([["Topics", d.num_topics], ["Perplexity", d.perplexity], ["Segments", d.segments]]),
                table(["Topic", "Top words", "Segments"], d.topics.map(function (t) {
                    return [t.topic, t.top_words.join(", "), d.segments_per_topic[String(t.topic)] || 0];
                }))
            ];
        },
        9: function (d) {
            const parts = [metaGrid([["Language", d.name], ["Confidence", d.confidence], ["Method", d.method]])];
            if (d.top_predictions.length) {
                parts.push(chips(d.top_predictions.map(function (p) { return p.code + " " + p.confidence; })));
            }
            return parts;
        },
        10: function (d) {
            const checks = d.checks;
            const parts = [
                metaGrid([
                    ["Model", d.model],
                    ["Format followed", checks.format_followed ? "Yes" : "No"],
                    ["Key terms used", checks.key_terms_used.length + " / " + checks.key_terms_checked]
                ]),
                heading("Generated summary"),
                quote(d.output),
                heading("Prompt engineering techniques"),
                el("ul", "np-list")
            ];
            d.prompt_techniques.forEach(function (t) { parts[parts.length - 1].appendChild(el("li", "", t)); });

            const promptBox = el("details", "np-prompt");
            promptBox.appendChild(el("summary", "", "Show the exact prompt sent to the model"));
            promptBox.appendChild(heading("System prompt"));
            promptBox.appendChild(quote(d.system_prompt));
            promptBox.appendChild(heading("User prompt"));
            promptBox.appendChild(quote(d.user_prompt));
            parts.push(promptBox);
            return parts;
        },
        11: function (d) {
            return [
                metaGrid([["Service", d.service], ["Language", d.target_language_name], ["Translated", d.translated_from]]),
                heading("Translation"),
                quote(d.translated_text)
            ];
        }
    };


    // =====================================
    // RENDER THE WHOLE REPORT
    // =====================================

    function stageCard(stage) {
        const card = el("article", "np-stage is-" + stage.status);

        const header = el("header", "np-stage-header");
        header.appendChild(el("span", "np-stage-number", stage.number));
        const titles = el("div", "np-stage-titles");
        titles.appendChild(el("h3", "np-stage-title", stage.title));
        titles.appendChild(el("span", "np-stage-method", stage.method));
        header.appendChild(titles);
        header.appendChild(el("span", "badge np-badge-" + stage.status, STATUS_LABEL[stage.status]));
        header.appendChild(el("span", "np-stage-time", stage.seconds + " s"));
        card.appendChild(header);

        card.appendChild(el("p", "np-stage-summary", stage.summary));

        const renderer = RENDERERS[stage.number];
        if (stage.status === "done" && renderer) {
            const body = el("div", "np-stage-body");
            try {
                renderer(stage.details).forEach(function (part) { body.appendChild(part); });
            } catch (error) {
                body.appendChild(el("p", "muted", "Details could not be displayed: " + error.message));
            }
            card.appendChild(body);
        }
        return card;
    }

    function downloadButton(label, icon, filename, content, type) {
        const button = el("button", "btn btn-secondary btn-sm");
        button.type = "button";
        const iconNode = el("i", "bi bi-" + icon);
        iconNode.setAttribute("aria-hidden", "true");
        button.appendChild(iconNode);
        button.appendChild(document.createTextNode(" " + label));
        button.addEventListener("click", function () {
            const url = URL.createObjectURL(new Blob([content], { type: type }));
            const link = el("a");
            link.href = url;
            link.download = filename;
            link.click();
            URL.revokeObjectURL(url);
        });
        return button;
    }

    function renderReport(report, markdown) {
        output.replaceChildren();
        const totals = report.totals;
        const baseName = report.title.replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_-]+/g, "_");

        // Summary panel.
        const summary = el("section", "panel np-summary");
        summary.appendChild(el("h2", "panel-title", report.title));
        summary.appendChild(metaGrid([
            ["Stages done", totals.done + " / " + totals.stages],
            ["Skipped / failed", totals.skipped + " / " + totals.failed],
            ["Total time", totals.seconds + " s"]
        ]));
        const actions = el("div", "np-actions");
        actions.appendChild(downloadButton("Markdown report", "file-earmark-text", baseName + "_pipeline.md", markdown, "text/markdown"));
        actions.appendChild(downloadButton("JSON report", "filetype-json", baseName + "_pipeline.json",
            JSON.stringify(report, null, 2), "application/json"));
        summary.appendChild(actions);
        output.appendChild(summary);

        // One panel per Course Outcome.
        CO_GROUPS.forEach(function (group) {
            const stages = report.stages.filter(function (stage) { return stage.co === group.co; });
            if (!stages.length) return;

            const panel = el("section", "panel np-co");
            const header = el("header", "np-co-header");
            header.appendChild(el("span", "badge badge-ink", group.co));
            header.appendChild(el("h2", "panel-title", group.title));
            header.appendChild(el("span", "np-co-marks", group.marks + " marks"));
            panel.appendChild(header);
            stages.forEach(function (stage) { panel.appendChild(stageCard(stage)); });
            output.appendChild(panel);
        });
    }


    // =====================================
    // RUN BUTTON
    // =====================================

    runButton.addEventListener("click", async function () {
        const file = fileInput.files && fileInput.files[0];
        const text = textInput.value.trim();

        if (!file && text.length < 200) {
            setStatus("Choose a PDF/TXT file, or paste at least 200 characters.", "error");
            return;
        }

        const formData = new FormData();
        if (file) formData.append("file", file);
        else formData.append("text", text);
        formData.append("use_llm", useLlm.checked ? "true" : "false");
        formData.append("translate_to", translateTo.value);
        formData.append("num_topics", numTopics.value || "5");

        runButton.disabled = true;
        setStatus(useLlm.checked
            ? "Running all stages… the LLM step can take up to a minute."
            : "Running all stages…");

        try {
            const response = await fetch("/api/nlp-pipeline/run", { method: "POST", body: formData });
            const data = await response.json().catch(function () { return {}; });

            if (!response.ok || !data.success) {
                throw new Error(data.message || "The pipeline could not run.");
            }

            renderReport(data.report, data.markdown);
            const t = data.report.totals;
            setStatus(t.done + " of " + t.stages + " stages finished" +
                (t.failed ? ", " + t.failed + " failed (see the red cards)." : "."), t.failed ? "error" : "success");
        } catch (error) {
            setStatus(error.message, "error");
        } finally {
            runButton.disabled = false;
        }
    });
});
