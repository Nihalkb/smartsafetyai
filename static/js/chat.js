document.addEventListener("DOMContentLoaded", function () {
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendButton = document.getElementById("send-button");
    const clearButton = document.getElementById("clear-chat-button"); // New Clear Chat Button
    const loadingIndicator = document.getElementById("loading-indicator");
    const sessionId = document.getElementById("session-id").value;
    const suggestionChips = document.querySelectorAll(".suggestion-chip");

    // Set up event listeners
    sendButton.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

    clearButton.addEventListener("click", clearChatMemory); // Event listener for clearing chat

    // Set up suggestion chips
    suggestionChips.forEach((chip) => {
        chip.addEventListener("click", function () {
            const query = this.getAttribute("data-query");
            chatInput.value = query;
            sendMessage();
        });
    });

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addMessage(content, isUser = false) {
        const messageElement = document.createElement("div");
        messageElement.className = `message ${isUser ? "user-message" : "system-message"}`;

        const messageContent = document.createElement("div");
        messageContent.className = "message-content";
        messageContent.innerHTML = content;

        const messageTime = document.createElement("div");
        messageTime.className = "message-time";
        messageTime.textContent = formatTime(new Date());

        messageElement.appendChild(messageContent);
        messageElement.appendChild(messageTime);

        chatMessages.appendChild(messageElement);
        scrollToBottom();
    }

    function formatTime(date) {
        const hours = date.getHours();
        const minutes = date.getMinutes();
        return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
    }

    function sendMessage() {
        const message = chatInput.value.trim();

        if (!message) {
            return;
        }

        addMessage(message, true);
        chatInput.value = "";

        loadingIndicator.style.display = "block";
        scrollToBottom();

        fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
            }),
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then((data) => {
                loadingIndicator.style.display = "none";
                addMessage(data.response);
                generateContextualSuggestions(message, data.response);
            })
            .catch((error) => {
                console.error("Error during chat:", error);
                loadingIndicator.style.display = "none";
                addMessage("Sorry, there was an error processing your request. Please try again.");
            });
    }

    function clearChatMemory() {
        fetch("/api/chat/clear", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        })
            .then((response) => response.json())
            .then((data) => {
                chatMessages.innerHTML = ""; // Clear chat UI
                addMessage("Chat memory cleared. You can start a new conversation.", false);
            })
            .catch((error) => {
                console.error("Error clearing chat:", error);
                addMessage("Error clearing chat memory. Please try again.", false);
            });
    }

    function generateContextualSuggestions(userMessage, systemResponse) {
        if (
            userMessage.toLowerCase().includes("chemical") ||
            userMessage.toLowerCase().includes("spill") ||
            systemResponse.toLowerCase().includes("chemical")
        ) {
            updateSuggestionChips([
                { text: "How to clean up chemical spills?", query: "How do I properly clean up a chemical spill?" },
                { text: "Required PPE for chemicals", query: "What PPE is required when handling chemicals?" },
                { text: "Chemical exposure treatment", query: "How to treat chemical exposure to skin?" },
            ]);
        } else if (
            userMessage.toLowerCase().includes("fire") ||
            systemResponse.toLowerCase().includes("fire") ||
            userMessage.toLowerCase().includes("burn")
        ) {
            updateSuggestionChips([
                { text: "Fire extinguisher types", query: "What type of fire extinguisher should I use?" },
                { text: "Evacuation procedures", query: "What are the evacuation procedures for a fire?" },
                { text: "Fire prevention", query: "How can we prevent fires in the workplace?" },
            ]);
        } else if (
            userMessage.toLowerCase().includes("gas") ||
            userMessage.toLowerCase().includes("leak") ||
            systemResponse.toLowerCase().includes("gas leak")
        ) {
            updateSuggestionChips([
                { text: "Gas leak detection", query: "How can I detect a gas leak?" },
                { text: "Ventilation procedures", query: "What ventilation procedures should I follow for a gas leak?" },
                { text: "Similar gas incidents", query: "Have there been similar gas leak incidents in the past?" },
            ]);
        }
    }

    function updateSuggestionChips(suggestions) {
        if (!suggestions || !suggestionChips || suggestionChips.length === 0) {
            return;
        }

        if (suggestions.length >= suggestionChips.length) {
            for (let i = 0; i < suggestionChips.length; i++) {
                suggestionChips[i].textContent = suggestions[i].text;
                suggestionChips[i].setAttribute("data-query", suggestions[i].query);
            }
        }
    }

    scrollToBottom();
});
