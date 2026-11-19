/* ==========================================================
   StudyMate AI — diagram renderer
   Any element with the attribute data-render-diagrams will have
   ```mermaid code blocks (rendered by marked as
   <pre><code class="language-mermaid">) turned into diagrams.
   Needs vendor/js/mermaid.min.js on the page.
   ========================================================== */

(function () {
    "use strict";

    if (!window.mermaid) return;

    var counter = 0;

    function theme() {
        return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "neutral";
    }

    window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: theme(),
        fontFamily: "Schibsted Grotesk, Segoe UI, sans-serif"
    });

    function convert(root) {
        var blocks = root.querySelectorAll("pre > code.language-mermaid");
        var nodes = [];

        blocks.forEach(function (code) {
            var holder = document.createElement("div");
            holder.className = "mermaid";
            holder.id = "diagram-" + (++counter);
            holder.textContent = code.textContent;
            holder.dataset.source = code.textContent;
            code.parentElement.replaceWith(holder);
            nodes.push(holder);
        });

        if (!nodes.length) return;

        window.mermaid.run({ nodes: nodes, suppressErrors: true }).catch(function () {
            nodes.forEach(function (node) {
                if (!node.querySelector("svg")) {
                    node.classList.add("mermaid-failed");
                    node.textContent = "This diagram could not be drawn. Its source is shown below.\n\n" + node.dataset.source;
                }
            });
        });
    }

    function watch(root) {
        convert(root);
        new MutationObserver(function () { convert(root); })
            .observe(root, { childList: true, subtree: true });
    }

    // Redraw existing diagrams in the new colours when the theme changes.
    document.addEventListener("studymate:themechange", function () {
        window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: theme() });
        var nodes = Array.prototype.slice.call(document.querySelectorAll(".mermaid[data-source]"));
        nodes.forEach(function (node) {
            node.removeAttribute("data-processed");
            node.textContent = node.dataset.source;
        });
        if (nodes.length) window.mermaid.run({ nodes: nodes, suppressErrors: true }).catch(function () {});
    });

    function init() {
        document.querySelectorAll("[data-render-diagrams]").forEach(watch);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
