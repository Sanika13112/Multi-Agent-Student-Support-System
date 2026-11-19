document.addEventListener("DOMContentLoaded", () => {

    const imageInput = document.getElementById("noticeImage");
    const fileInfo = document.getElementById("fileInfo");
    const fileName = document.getElementById("fileName");
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

        const allowedTypes = ["image/jpeg", "image/png"];

        if (!allowedTypes.includes(file.type)) {
            showStatus("Please select a JPG, JPEG or PNG image.", true);
            resetFile();
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            showStatus("Image size must not exceed 10 MB.", true);
            resetFile();
            return;
        }

        selectedFile = file;

        fileName.textContent = file.name;
        fileInfo.hidden = false;

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
        }

        previewURL = URL.createObjectURL(file);
        previewImage.src = previewURL;
        preview.hidden = false;

        processButton.disabled = false;

        extractedText.value = "";
        downloadButton.disabled = true;
        languageDetails.hidden = true;

        resetTranslation();

        languageResult.textContent = "Ready for language detection";

        showStatus("Image selected. Ready to process.");
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
            showStatus("Please select a notice image first.", true);
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

            showStatus(data.message || "Notice processed successfully.");

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