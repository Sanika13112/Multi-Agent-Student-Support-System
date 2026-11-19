
/*
StudyMate AI - AskAway Frontend

Features:
1. PDF/TXT upload
2. Document status
3. Ask questions
4. Display AI responses
5. Show retrieved source chunks
6. Display original PDF page numbers
7. Display relevance scores
8. Reset document
*/

document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // ELEMENT REFERENCES
    // ==========================================

    const documentInput = document.getElementById("documentInput");
    const documentStatus = document.getElementById("documentStatus");
    const documentInfo = document.getElementById("documentInfo");
    const documentName = document.getElementById("documentName");
    const documentDetails = document.getElementById("documentDetails");

    const resetDocumentButton = document.getElementById(
        "resetDocumentButton"
    );

    const chatMessages = document.getElementById("chatMessages");
    const welcomeMessage = document.getElementById("welcomeMessage");
    const askAwayForm = document.getElementById("askAwayForm");
    const questionInput = document.getElementById("questionInput");

    const sendQuestionButton = document.getElementById(
        "sendQuestionButton"
    );

    const chatStatus = document.getElementById("chatStatus");


    // ==========================================
    // APPLICATION STATE
    // ==========================================

    let documentUploaded = false;
    let busy = false;


    // ==========================================
    // STATUS HELPERS
    // ==========================================

    function showDocumentStatus(message, type = "") {

        documentStatus.textContent = message;
        documentStatus.className = "document-status";

        if (type === "success") {
            documentStatus.classList.add("status-success");
        }

        if (type === "error") {
            documentStatus.classList.add("status-error");
        }
    }


    function setBusy(value) {

        busy = value;

        sendQuestionButton.disabled = value || !documentUploaded;
        resetDocumentButton.disabled = value;
        documentInput.disabled = value;
        questionInput.disabled = value || !documentUploaded;

    }


    function updateChatStatus(message) {
        chatStatus.textContent = message;
    }


    // ==========================================
    // MESSAGE DISPLAY
    // ==========================================

    function addMessage(content, sender, sources = []) {

        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        const messageWrapper = document.createElement("div");

        messageWrapper.className =
            sender === "user"
                ? "message user-message"
                : "message ai-message";


        const label = document.createElement("div");

        label.className = "message-label";

        label.textContent =
            sender === "user" ? "YOU" : "ASKAWAY";


        const messageText = document.createElement("div");

        // Prevent document content from being interpreted as HTML.
        messageText.textContent = content;


        messageWrapper.appendChild(label);
        messageWrapper.appendChild(messageText);


        // ==========================================
        // DISPLAY RETRIEVED DOCUMENT SOURCES
        // ==========================================

        if (sender === "ai" && sources.length > 0) {

            const details = document.createElement("details");

            details.className = "source-panel";

            const summary = document.createElement("summary");

            summary.textContent =
                `Sources used (${sources.length})`;

            details.appendChild(summary);


            sources.forEach(source => {

                const sourceText = document.createElement("p");

                sourceText.className = "mt-2 mb-0";

                // Get retrieved chunk number.
                const chunkNumber = source.chunk_index || "?";

                // Get original PDF page number.
                const pageNumber = source.page_number;

                const pageText = pageNumber !== null &&
                    pageNumber !== undefined
                    ? `Page ${pageNumber}`
                    : "Page not available";

                // Get semantic relevance score.
                const score = Number(source.relevance_score);

                const scoreText = Number.isFinite(score)
                    ? score.toFixed(3)
                    : "N/A";

                // Display page, chunk, score and source text.
                sourceText.textContent =
                    `${pageText} | Chunk ${chunkNumber} | Relevance: ${scoreText}\n` +
                    (source.text || "");

                details.appendChild(sourceText);

            });

            messageWrapper.appendChild(details);

        }


        chatMessages.appendChild(messageWrapper);

        chatMessages.scrollTop = chatMessages.scrollHeight;

    }


    // ==========================================
    // DOCUMENT UPLOAD
    // ==========================================

    documentInput.addEventListener("change", async () => {

        const file = documentInput.files[0];

        if (!file) {
            return;
        }

        const extension = file.name.split(".").pop().toLowerCase();

        // Validate file extension.
        if (!["pdf", "txt"].includes(extension)) {

            showDocumentStatus(
                "Please select a PDF or TXT file.",
                "error"
            );

            documentInput.value = "";

            return;
        }


        // Validate file size.
        if (file.size === 0 || file.size > 20 * 1024 * 1024) {

            showDocumentStatus(
                file.size === 0
                    ? "The selected file is empty."
                    : "File size must be less than or equal to 20 MB.",
                "error"
            );

            documentInput.value = "";

            return;
        }


        const formData = new FormData();

        formData.append("file", file);

        setBusy(true);

        showDocumentStatus(
            "Uploading document and generating embeddings..."
        );


        try {

            const response = await fetch(
                "/api/ask-away/upload",
                {
                    method: "POST",
                    body: formData
                }
            );


            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Document upload failed."
                );
            }


            documentUploaded = true;

            documentInfo.hidden = false;

            documentName.textContent = result.filename;

            documentDetails.textContent =
                `${result.file_type.toUpperCase()} | ` +
                `${result.page_count} pages | ` +
                `${result.chunk_count} chunks`;


            questionInput.disabled = false;

            questionInput.placeholder =
                "Ask something about your document...";


            showDocumentStatus(
                "Document uploaded and processed successfully.",
                "success"
            );


            // Clear previous conversation for a newly uploaded file.
            chatMessages.innerHTML = "";

            addMessage(
                `Your document "${result.filename}" is ready. ` +
                "Ask me anything about its content!",
                "ai"
            );


            questionInput.focus();

        } catch (error) {

            documentUploaded = false;

            showDocumentStatus(
                error.message,
                "error"
            );

            questionInput.disabled = true;

        } finally {

            setBusy(false);

            documentInput.value = "";

        }

    });


    // ==========================================
    // ASK QUESTION
    // ==========================================

    askAwayForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        if (!documentUploaded || busy) {
            return;
        }

        const question = questionInput.value.trim();

        if (!question) {
            return;
        }


        addMessage(question, "user");

        questionInput.value = "";

        setBusy(true);

        updateChatStatus(
            "AskAway is finding relevant information..."
        );


        try {

            const response = await fetch(
                "/api/ask-away/ask",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        question: question
                    })
                }
            );


            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Unable to generate an answer."
                );
            }


            // Display AI answer and retrieved sources.
            addMessage(
                result.answer,
                "ai",
                result.sources || []
            );

            updateChatStatus("Answer generated successfully.");

        } catch (error) {

            addMessage(
                `Sorry, something went wrong: ${error.message}`,
                "ai"
            );

            updateChatStatus("Please try again.");

        } finally {

            setBusy(false);

            questionInput.focus();

        }

    });


    // ==========================================
    // RESET DOCUMENT
    // ==========================================

    resetDocumentButton.addEventListener("click", async () => {

        if (busy) {
            return;
        }

        const confirmed = window.confirm(
            "Are you sure you want to remove the uploaded document?"
        );

        if (!confirmed) {
            return;
        }


        setBusy(true);

        try {

            const response = await fetch(
                "/api/ask-away/reset",
                {
                    method: "POST"
                }
            );


            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Unable to reset the document."
                );
            }


            documentUploaded = false;

            documentInfo.hidden = true;

            documentInput.value = "";

            questionInput.value = "";

            questionInput.disabled = true;

            questionInput.placeholder =
                "Upload a document to start asking...";


            chatMessages.innerHTML = "";

            chatMessages.appendChild(welcomeMessage);

            welcomeMessage.hidden = false;


            showDocumentStatus(
                "Document removed successfully.",
                "success"
            );

            updateChatStatus("");

        } catch (error) {

            showDocumentStatus(
                error.message,
                "error"
            );

        } finally {

            setBusy(false);

        }

    });


    // ==========================================
    // CHECK EXISTING DOCUMENT SESSION
    // ==========================================

    async function checkExistingDocument() {

        try {

            const response = await fetch(
                "/api/ask-away/document"
            );

            const result = await response.json();

            if (!response.ok || !result.success) {
                return;
            }


            documentUploaded = true;

            documentInfo.hidden = false;

            documentName.textContent = result.filename;

            documentDetails.textContent =
                `${result.file_type.toUpperCase()} | ` +
                `${result.page_count} pages | ` +
                `${result.chunk_count} chunks`;


            questionInput.disabled = false;

            questionInput.placeholder =
                "Ask something about your document...";


            showDocumentStatus(
                "Your previous document session is available.",
                "success"
            );

            setBusy(false);

        } catch (error) {

            console.error(
                "Could not restore AskAway document:",
                error
            );

        }

    }


    // ==========================================
    // INITIALIZATION
    // ==========================================

    checkExistingDocument();

});
