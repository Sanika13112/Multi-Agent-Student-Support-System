document.addEventListener("DOMContentLoaded", () => {

    const imageInput = document.getElementById("noticeImage");
    const fileInfo = document.getElementById("fileInfo");
    const fileName = document.getElementById("fileName");
    const fileIcon = document.getElementById("fileIcon");
    const removeFile = document.getElementById("removeFile");

    const preview = document.getElementById("imagePreview");
    const previewImage = document.getElementById("previewImage");

    const processButton = document.getElementById("processButton");
    const statusMessage = document.getElementById("statusMessage");

    const extractedText = document.getElementById("extractedText");
    const downloadButton = document.getElementById("downloadText");

    const languageResult = document.getElementById("languageResult");
    const languageDetails = document.getElementById("languageDetails");

    const sourceLanguage = document.getElementById("sourceLanguage");
    const targetLanguage = document.getElementById("targetLanguage");

    const translateButton = document.getElementById("translateButton");
    const translationStatus = document.getElementById("translationStatus");
    const translationOutput = document.getElementById("translationOutput");

    const copyTranslation = document.getElementById("copyTranslation");
    const downloadTranslation = document.getElementById("downloadTranslation");

    let selectedFile = null;
    let previewURL = null;
    let translatedText = "";

    function showStatus(message, isError = false) {
        statusMessage.textContent = message;
        statusMessage.style.color = isError ? "#dc5555" : "inherit";
    }

    function showTranslationStatus(message, isError = false) {
        translationStatus.textContent = message;
        translationStatus.style.color = isError ? "#dc5555" : "inherit";
    }

    function resetTranslation() {
        translatedText = "";
        translationOutput.textContent =
            "Your translated notice will appear here.";

        copyTranslation.disabled = true;
        downloadTranslation.disabled = true;
        translateButton.disabled = !extractedText.value.trim();

        showTranslationStatus("");
    }

    // Icon shown next to the chosen file name.
    const FILE_ICONS = {
        jpg: "bi-file-earmark-image",
        jpeg: "bi-file-earmark-image",
        png: "bi-file-earmark-image",
        pdf: "bi-file-earmark-pdf",
        docx: "bi-file-earmark-word"
    };

    // How the text was obtained, shown after processing.
    function describeSource(data) {
        const pages = data.pages
            ? ` (${data.pages_read && data.pages_read < data.pages
                ? `first ${data.pages_read} of ${data.pages} pages`
                : `${data.pages} page${data.pages > 1 ? "s" : ""}`})`
            : "";
        const descriptions = {
            image: "Text read from the image with OCR.",
            pdf_text: `Text read directly from the PDF${pages}.`,
            pdf_scanned: `Scanned PDF: text read from the page images with OCR${pages}.`,
            pdf_mixed: `PDF text read directly, scanned pages read with OCR${pages}.`,
            docx: "Text read from the Word file."
        };
        return descriptions[data.source_type] || "";
    }

    // Warn when OCR was unsure, so wrong text is not trusted blindly.
    function describeQuality(quality) {
        if (!quality || !quality.ocr_used) return "";

        const percent = Math.round((quality.average_confidence || 0) * 100);
        const removed = quality.removed_lines
            ? ` ${quality.removed_lines} unclear line(s) were left out.`
            : "";

        if (!quality.low) {
            return `OCR confidence ${percent}%.${removed}`;
        }

        return `Warning: the text was hard to read (OCR confidence ${percent}%).${removed} ` +
            "The extracted text and its translation may be wrong. Try a sharper, straight, " +
            "well-lit photo, or upload the original PDF.";
    }

    function getLanguageCode(languageName) {
        const name = (languageName || "").toLowerCase();

        if (name.includes("english")) return "en";
        if (name.includes("hindi")) return "hi";
        if (name.includes("marathi")) return "mr";

        return "";
    }

    imageInput.addEventListener("change", () => {
        const file = imageInput.files[0];

        if (!file) return;

        // Check by file extension: browsers report Word/PDF types inconsistently.
        const extension = file.name.split(".").pop().toLowerCase();
        const isImage = ["jpg", "jpeg", "png"].includes(extension);

        if (extension === "doc") {
            resetFile();   // clears the status, so show the message after it
            showStatus("Old .doc files are not supported. Save it as .docx or PDF.", true);
            return;
        }

        if (!isImage && !["pdf", "docx"].includes(extension)) {
            resetFile();
            showStatus("Please select a JPG, PNG, PDF or DOCX file.", true);
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            resetFile();
            showStatus("File size must not exceed 10 MB.", true);
            return;
        }

        selectedFile = file;

        fileName.textContent = file.name;
        fileInfo.hidden = false;
        fileIcon.className = "bi " + FILE_ICONS[extension];

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
            previewURL = null;
        }

        // Only images get a picture preview.
        if (isImage) {
            previewURL = URL.createObjectURL(file);
            previewImage.src = previewURL;
            preview.hidden = false;
        } else {
            previewImage.removeAttribute("src");
            preview.hidden = true;
        }

        processButton.disabled = false;

        extractedText.value = "";
        downloadButton.disabled = true;
        languageDetails.hidden = true;

        resetTranslation();

        languageResult.textContent = "Ready for language detection";

        showStatus(isImage ? "Image selected. Ready to process." : "File selected. Ready to process.");
    });

    removeFile.addEventListener("click", resetFile);

    function resetFile() {
        selectedFile = null;
        imageInput.value = "";

        fileInfo.hidden = true;
        preview.hidden = true;

        processButton.disabled = true;

        extractedText.value = "";
        downloadButton.disabled = true;

        languageDetails.hidden = true;
        resetTranslation();

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
            previewURL = null;
        }

        previewImage.removeAttribute("src");
        showStatus("");
    }

    processButton.addEventListener("click", async () => {

        if (!selectedFile) {
            showStatus("Please select a notice file first.", true);
            return;
        }

        const formData = new FormData();
        formData.append("notice_image", selectedFile);

        processButton.disabled = true;
        processButton.textContent = "Processing...";

        showStatus("Extracting text and detecting language...");

        try {
            const response = await fetch(
                "/api/notice-translator/process",
                {
                    method: "POST",
                    body: formData
                }
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Notice processing failed.");
            }

            extractedText.value = data.extracted_text || "";

            downloadButton.disabled = !extractedText.value.trim();

            const language = data.language || {};

            languageResult.textContent = "Language detection completed";

            languageDetails.hidden = false;

            document.getElementById("primaryLanguage").textContent =
                language.primary_language_name || "Unknown";

            document.getElementById("languageConfidence").textContent =
                `${((language.confidence || 0) * 100).toFixed(2)}%`;

            document.getElementById("mixedLanguage").textContent =
                language.is_mixed ? "Mixed language" : "Single language";

            const detectedCode = getLanguageCode(
                language.primary_language_name
            );

            if (detectedCode) {
                sourceLanguage.value = detectedCode;
            }

            translateButton.disabled =
                !extractedText.value.trim() || !detectedCode;

            showStatus(
                [data.message || "Notice processed successfully.", describeSource(data), describeQuality(data.quality)]
                    .filter(Boolean).join(" "),
                Boolean(data.quality && data.quality.low)
            );

            resetTranslation();

            translateButton.disabled =
                !extractedText.value.trim() || !detectedCode;

            if (language.is_mixed) {
                showTranslationStatus(
                    "This notice contains mixed languages. " +
                    "Please select the main source language manually."
                );
                translateButton.disabled = !extractedText.value.trim();
            }

        } catch (error) {
            showStatus(error.message, true);

        } finally {
            processButton.disabled = !selectedFile;
            processButton.innerHTML =
                '<i class="bi bi-scan"></i> Extract Text and Detect Language';
        }
    });

    extractedText.addEventListener("input", () => {
        downloadButton.disabled = !extractedText.value.trim();
        translateButton.disabled = !extractedText.value.trim();
        resetTranslation();
    });

    sourceLanguage.addEventListener("change", resetTranslation);
    targetLanguage.addEventListener("change", resetTranslation);

    translateButton.addEventListener("click", async () => {

        const text = extractedText.value.trim();
        const source = sourceLanguage.value;
        const target = targetLanguage.value;

        if (!text) {
            showTranslationStatus("Please extract or enter notice text.", true);
            return;
        }

        if (source === target) {
            translatedText = text;
            translationOutput.textContent = translatedText;

            copyTranslation.disabled = false;
            downloadTranslation.disabled = false;

            showTranslationStatus(
                "Source and target languages are the same. Original text displayed."
            );
            return;
        }

        translateButton.disabled = true;
        translateButton.textContent = "Translating...";

        translationOutput.textContent = "Translation in progress...";

        showTranslationStatus(
            "Connecting to MyMemory translation service..."
        );

        try {
            const response = await fetch(
                "/api/notice-translator/translate",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        text: text,
                        source_language: source,
                        target_language: target
                    })
                }
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Translation failed.");
            }

            translatedText = data.translated_text;

            translationOutput.textContent = translatedText;

            copyTranslation.disabled = false;
            downloadTranslation.disabled = false;

            showTranslationStatus(
                "Translation completed successfully."
            );

        } catch (error) {
            translationOutput.textContent =
                "Unable to translate this notice.";

            showTranslationStatus(error.message, true);

        } finally {
            translateButton.disabled = !extractedText.value.trim();
            translateButton.innerHTML =
                '<i class="bi bi-translate"></i> Translate Notice';
        }
    });

    copyTranslation.addEventListener("click", async () => {
        if (!translatedText) return;

        try {
            await navigator.clipboard.writeText(translatedText);
            showTranslationStatus("Translation copied successfully.");
        } catch (error) {
            showTranslationStatus(
                "Unable to copy. Please select and copy the text manually.",
                true
            );
        }
    });

    downloadTranslation.addEventListener("click", () => {
        if (!translatedText) return;

        const blob = new Blob(
            [translatedText],
            { type: "text/plain;charset=utf-8" }
        );

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "translated_notice.txt";
        link.click();

        URL.revokeObjectURL(url);
    });

    downloadButton.addEventListener("click", () => {
        const text = extractedText.value.trim();

        if (!text) return;

        const blob = new Blob(
            [text],
            { type: "text/plain;charset=utf-8" }
        );

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "extracted_notice.txt";
        link.click();

        URL.revokeObjectURL(url);
    });

});