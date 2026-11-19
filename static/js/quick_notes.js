document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("documentInput");
    const generateButton = document.getElementById("generateButton");
    const statusMessage = document.getElementById("statusMessage");
    const selectedFile = document.getElementById("selectedFile");
    const documentInfo = document.getElementById("documentInfo");
    const documentEmpty = document.querySelector(".qn-document-empty");
    const fileName = document.getElementById("fileName");
    const fileType = document.getElementById("fileType");
    const pageCount = document.getElementById("pageCount");
    const fileSize = document.getElementById("fileSize");
    const modelName = document.getElementById("modelName");
    const notesContainer = document.getElementById("notesContainer");
    const notesContent = document.getElementById("notesContent");
    const downloadButton = document.getElementById("downloadButton");

    let generatedMarkdown = "";
    let busy = false;

    function setStatus(message, type = "") {
        if (!statusMessage) return;
        statusMessage.textContent = message;
        statusMessage.className = `qn-status-message ${type}`;
    }

    function selectedMode() {
        return document.querySelector('input[name="notesMode"]:checked')?.value || "quick";
    }

    function formatBytes(bytes) {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    function setBusy(value) {
        busy = value;
        generateButton.disabled = value || !fileInput.files.length;
        generateButton.innerHTML = value
            ? '<i class="bi bi-hourglass-split"></i> Generating...'
            : '<i class="bi bi-stars"></i> Generate Study Notes <i class="bi bi-arrow-right"></i>';
        fileInput.disabled = value;
    }

    function renderNotes(markdown) {
        const empty = notesContainer.querySelector(".qn-notes-empty");
        if (empty) empty.hidden = true;
        if (window.marked && typeof window.marked.parse === "function") {
            const html = window.marked.parse(markdown);
            notesContent.innerHTML = window.DOMPurify
                ? window.DOMPurify.sanitize(html)
                : html;
        } else {
            notesContent.textContent = markdown;
        }
        notesContent.hidden = false;
    }

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        generatedMarkdown = "";
        downloadButton.disabled = true;
        notesContent.innerHTML = "";
        if (!file) {
            selectedFile.innerHTML = '<i class="bi bi-file-earmark-text"></i><span>No document selected</span>';
            generateButton.disabled = true;
            return;
        }

        const ext = file.name.split(".").pop().toLowerCase();
        if (!["pdf", "txt"].includes(ext)) {
            setStatus("Please choose a PDF or TXT file.", "error");
            fileInput.value = "";
            generateButton.disabled = true;
            return;
        }
        if (file.size === 0 || file.size > 20 * 1024 * 1024) {
            setStatus(file.size === 0 ? "The selected file is empty." : "File size must be 20 MB or less.", "error");
            fileInput.value = "";
            generateButton.disabled = true;
            return;
        }

        selectedFile.innerHTML = "";
        const icon = document.createElement("i");
        icon.className = "bi bi-file-earmark-check";
        const name = document.createElement("span");
        name.textContent = file.name;
        selectedFile.append(icon, name);
        selectedFile.classList.add("has-file");
        generateButton.disabled = false;
        setStatus("Document selected. Choose a note style and generate your notes.", "success");
    });

    generateButton.addEventListener("click", async () => {
        const file = fileInput.files[0];
        if (!file || busy) {
            setStatus("Please select a PDF or TXT document first.", "error");
            return;
        }

        const mode = selectedMode();
        const formData = new FormData();
        formData.append("file", file);
        formData.append("mode", mode);
        setBusy(true);
        setStatus(mode === "detailed" ? "Preparing your document and generating AI notes with Qwen..." : "Preparing your document and generating quick notes...", "loading");

        try {
            const response = await fetch("/api/quick-notes/upload", {
                method: "POST",
                body: formData
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.message || "Notes generation failed.");
            }

            generatedMarkdown = result.notes || "";
            if (!generatedMarkdown.trim()) throw new Error("The server returned empty notes.");
            renderNotes(generatedMarkdown);

            fileName.textContent = result.filename || file.name;
            fileType.textContent = `${(result.file_type || "document").toUpperCase()} document`;
            pageCount.textContent = result.page_count ?? "—";
            fileSize.textContent = formatBytes(result.file_size || file.size);
            modelName.textContent = result.model || (mode === "quick" ? "Python" : "Qwen");
            documentInfo.hidden = false;
            if (documentEmpty) documentEmpty.hidden = true;
            downloadButton.disabled = false;
            setStatus("Study notes generated successfully.", "success");
        } catch (error) {
            setStatus(error.message || "Unable to generate notes. Please try again.", "error");
        } finally {
            setBusy(false);
        }
    });

    downloadButton.addEventListener("click", () => {
        if (!generatedMarkdown) return;
        const blob = new Blob([generatedMarkdown], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "StudyMate_Study_Notes.md";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
    });

    document.querySelectorAll('input[name="notesMode"]').forEach((radio) => {
        radio.addEventListener("change", () => {
            document.querySelectorAll(".qn-mode-option").forEach((option) => {
                option.classList.toggle("selected", option.querySelector("input").checked);
            });
        });
    });

    generateButton.disabled = !fileInput.files.length;
    downloadButton.disabled = true;
});
