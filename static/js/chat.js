
// Get chat interface elements
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatMessages = document.getElementById("chatMessages");
const sendButton = document.getElementById("sendButton");

// Convert agent IDs into readable names
function getAgentName(agent) {
    const agentNames = {
        study_explanation: "Study Explanation Agent",
        career_guidance: "Career Guidance Agent",
        interview_preparation: "Interview Preparation Agent",
        greeting: "General Help Agent",
        voice_snap: "VoiceSnap Agent",
        quick_notes: "QuickNotes Agent",
        ask_away: "AskAway Agent",
        brain_check: "BrainCheck Agent"
    };

    return agentNames[agent] || "General Student Support";
}

// Display a chat message
function addMessage(text, sender, metadata = null) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", `${sender}-message`);

    const messageText = document.createElement("p");
    messageText.textContent = text;
    messageDiv.appendChild(messageText);

    // Display routing information for AI responses
    if (sender === "bot" && metadata) {
        const infoDiv = document.createElement("div");
        infoDiv.classList.add("routing-info");

        const agentName = getAgentName(metadata.agent);
        const method = metadata.routing_method || "unknown";

        infoDiv.textContent =
            `Agent: ${agentName} | Routed by: ${method}`;

        messageDiv.appendChild(infoDiv);
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Display a temporary loading message
function showLoading() {
    const loadingDiv = document.createElement("div");
    loadingDiv.classList.add("message", "bot-message");
    loadingDiv.id = "loadingMessage";
    loadingDiv.textContent = "StudyMate AI is thinking...";
    chatMessages.appendChild(loadingDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove loading message
function removeLoading() {
    const loadingMessage = document.getElementById("loadingMessage");

    if (loadingMessage) {
        loadingMessage.remove();
    }
}

// Handle chat form submission
chatForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = messageInput.value.trim();

    if (!message) {
        return;
    }

    // Display student's message
    addMessage(message, "user");

    messageInput.value = "";
    sendButton.disabled = true;

    showLoading();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        removeLoading();

        if (!response.ok || !data.success) {
            addMessage(
                data.message || "Unable to process your question.",
                "bot"
            );
            return;
        }

        // Display AI answer and routing metadata
        addMessage(data.message, "bot", {
            agent: data.agent,
            intent: data.intent,
            routing_method: data.routing_method,
            confidence: data.confidence
        });

    } catch (error) {
        removeLoading();

        console.error("Chat error:", error);

        addMessage(
            "Unable to connect to the server. Please try again.",
            "bot"
        );
    } finally {
        sendButton.disabled = false;
        messageInput.focus();
    }
});
