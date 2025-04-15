document.addEventListener("DOMContentLoaded", function () {
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendButton = document.getElementById("send-button");
    const clearButton = document.getElementById("clear-chat-button");
    const loadingIndicator = document.getElementById("loading-indicator");
    const sessionId = document.getElementById("session-id").value;
    const suggestionChips = document.querySelectorAll(".suggestion-chip");
    const uploadInput = document.getElementById("upload-input");
    const uploadButton = document.getElementById("upload-button");
    const incidentContainer = document.getElementById("incident-container");
    const paginationControls = document.getElementById("incident-pagination");
    const referencedChunksPanel = document.getElementById("referenced-chunks-panel");

    let allIncidents = [];
    let allReferencedChunks = [];
    let currentPage = 1;
    const incidentsPerPage = 5;

    sendButton.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") sendMessage();
    });
    clearButton.addEventListener("click", clearChatMemory);

    suggestionChips.forEach((chip) => {
        chip.addEventListener("click", function () {
            const query = this.getAttribute("data-query");
            chatInput.value = query;
            sendMessage();
        });
    });

    const docSelect = document.getElementById("document-select");
    if (docSelect) {
        [...docSelect.options].forEach(opt => {
            if (opt.value.toLowerCase().includes("incident_report")) {
                opt.remove();
            }
        });
    }

    if (uploadButton) {
        uploadButton.addEventListener("click", function () {
            const file = uploadInput.files[0];
            if (!file) return alert("Please select a file to upload.");

            const formData = new FormData();
            formData.append("file", file);
            formData.append("session_id", sessionId);

            fetch("/api/chat/upload", {
                method: "POST",
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        alert("File uploaded and embedded successfully!");
                    } else {
                        alert("Upload failed: " + (data.error || "Unknown error"));
                    }
                })
                .catch(err => {
                    console.error("Upload error:", err);
                    alert("Error uploading file.");
                });
        });
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addMessage(content, isUser = false, isHTML = false) {
        const messageElement = document.createElement("div");
        messageElement.className = `message ${isUser ? "user-message" : "system-message"}`;

        const messageContent = document.createElement("div");
        messageContent.className = "message-content";
        if (isHTML) {
            messageContent.innerHTML = content;
        } else {
            messageContent.textContent = content;
        }

        const messageTime = document.createElement("div");
        messageTime.className = "message-time";
        messageTime.textContent = formatTime(new Date());

        messageElement.appendChild(messageContent);
        messageElement.appendChild(messageTime);
        chatMessages.appendChild(messageElement);
        scrollToBottom();
    }

    function formatTime(date) {
        return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
    }

    function sendMessage() {
        const message = chatInput.value.trim();
        const selectedDocs = Array.from(document.getElementById("document-select").selectedOptions).map(opt => opt.value);
        if (!message) return;

        addMessage(message, true);
        chatInput.value = "";
        if (loadingIndicator) {
            loadingIndicator.style.display = "block";
        }
        scrollToBottom();

        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                session_id: sessionId,
                filter_files: selectedDocs
            })
        })
            .then(response => {
                if (!response.ok) throw new Error("Request failed.");
                return response.json();
            })
            .then(data => {
                if (loadingIndicator) {
                    loadingIndicator.style.display = "none";
                }
                console.log(data);
                const respData = data.response;
                // Use marked.parse to convert Markdown to HTML
                if (typeof respData === "string") {
                    const htmlAnswer = marked.parse(respData);
                    addMessage(htmlAnswer, false, true);
                } else {
                    const answer = respData.answer || "No answer found.";
                    const renderedHTML = marked.parse(answer);
                    addMessage(renderedHTML, false, true);
                }
        
                allIncidents = data.incidents || [];
                currentPage = 1;
                renderIncidents();
        
                // Process referenced chunks: assume data.referenced_chunks is an array of objects
                // with keys: chunk_id, text, doc, and page.
                allReferencedChunks = data.referenced_chunks || [];
                renderReferencedChunks();
        
                generateContextualSuggestions(
                    message,
                    typeof respData === "string" ? respData : respData.answer || ""
                );
            })
            .catch(error => {
                console.error("Chat error:", error);
                if (loadingIndicator) {
                    loadingIndicator.style.display = "none";
                }
                addMessage("Sorry, there was an error. Please try again.");
            });
    }

    function clearChatMemory() {
        fetch("/api/chat/clear", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        })
            .then(res => res.json())
            .then(() => {
                chatMessages.innerHTML = "";
                incidentContainer.innerHTML = "";
                paginationControls.innerHTML = "";
                referencedChunksPanel.innerHTML = "";
                addMessage("Chat memory cleared.");
            });
    }

    // Updated function: renderReferencedChunks now shows doc and page details
    function renderReferencedChunks() {
        if (!referencedChunksPanel) return;
        // Wrap all items in a single accordion container (for styling only)
        let items = allReferencedChunks.map((chunk, index) => {
          const docName = chunk.doc && chunk.doc.trim() ? chunk.doc : "Unknown Document";
          const pageStr = (chunk.page !== null && chunk.page !== undefined) ? chunk.page : "N/A";
          return `
            <div class="accordion-item bg-dark text-light">
              <h2 class="accordion-header" id="chunk-heading-${index}">
                <button class="accordion-button collapsed bg-secondary text-white" 
                        type="button" 
                        data-bs-toggle="collapse" 
                        data-bs-target="#chunk-collapse-${index}" 
                        aria-expanded="false" 
                        aria-controls="chunk-collapse-${index}">
                  Reference ${index + 1}: Doc : ${chunk.doc || ""}, Page : ${chunk.page || ""}
                </button>
              </h2>
              <div id="chunk-collapse-${index}" class="accordion-collapse collapse" 
                   aria-labelledby="chunk-heading-${index}">
                <div class="accordion-body">
                  ${chunk.text || "No text found."} <br/>
                  <small>Document: ${docName}, Page: ${pageStr}</small>
                </div>
              </div>
            </div>
          `;
        }).join("");
        
        referencedChunksPanel.innerHTML = `<div class="accordion" id="referencedChunksAccordion">
          ${items}
        </div>`;
      }
      
    function renderIncidents() {
        const startIdx = (currentPage - 1) * incidentsPerPage;
        const endIdx = startIdx + incidentsPerPage;
        const visibleIncidents = allIncidents.slice(startIdx, endIdx);

        incidentContainer.innerHTML = visibleIncidents.map((incident, index) => `
            <div class="accordion mb-2" id="accordion-${startIdx + index}">
                <div class="accordion-item bg-dark text-light">
                    <h2 class="accordion-header" id="heading-${startIdx + index}">
                        <button class="accordion-button collapsed bg-secondary text-white" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${startIdx + index}" aria-expanded="false" aria-controls="collapse-${startIdx + index}">
                            Incident ${startIdx + index + 1}
                        </button>
                    </h2>
                    <div id="collapse-${startIdx + index}" class="accordion-collapse collapse" aria-labelledby="heading-${startIdx + index}" data-bs-parent="#accordion-${startIdx + index}">
                        <div class="accordion-body">
                            <p><strong>Date:</strong> ${incident.Date || "N/A"}</p>
                            <p><strong>Location:</strong> ${incident.Location || "N/A"}</p>
                            <p><strong>Operator:</strong> ${incident["Pipeline Operator"] || "N/A"}</p>
                            <p><strong>Material:</strong> ${incident["Material Released"] || "N/A"}</p>
                            <p><strong>Description:</strong> ${incident["Incident Description"] || "N/A"}</p>
                            <p><strong>Response:</strong> ${incident["Response Actions"] || "N/A"}</p>
                            <p><strong>Injuries:</strong> ${incident["Casualties & Injuries"] || "N/A"}</p>
                        </div>
                    </div>
                </div>
            </div>
        `).join("");

        renderPagination();
    }

    function renderPagination() {
        const totalPages = Math.ceil(allIncidents.length / incidentsPerPage);
        if (totalPages <= 1) {
            paginationControls.innerHTML = "";
            return;
        }

        paginationControls.innerHTML = "";
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement("button");
            btn.className = `btn btn-sm ${i === currentPage ? "btn-info" : "btn-outline-light"} me-1`;
            btn.textContent = i;
            btn.addEventListener("click", () => {
                currentPage = i;
                renderIncidents();
            });
            paginationControls.appendChild(btn);
        }
    }

    function generateContextualSuggestions(userMessage, systemResponse) {
        const suggestions = [];
        const lowerUser = userMessage.toLowerCase();
        const lowerResp = systemResponse.toLowerCase();

        if (lowerUser.includes("chemical") || lowerUser.includes("spill") || lowerResp.includes("chemical")) {
            suggestions.push(
                { text: "How to clean up chemical spills?", query: "How do I properly clean up a chemical spill?" },
                { text: "Required PPE for chemicals", query: "What PPE is required when handling chemicals?" },
                { text: "Chemical exposure treatment", query: "How to treat chemical exposure to skin?" }
            );
        } else if (lowerUser.includes("fire") || lowerResp.includes("fire") || lowerUser.includes("burn")) {
            suggestions.push(
                { text: "Fire extinguisher types", query: "What type of fire extinguisher should I use?" },
                { text: "Evacuation procedures", query: "What are the evacuation procedures for a fire?" },
                { text: "Fire prevention", query: "How can we prevent fires in the workplace?" }
            );
        } else if (lowerUser.includes("gas") || lowerUser.includes("leak") || lowerResp.includes("gas leak")) {
            suggestions.push(
                { text: "Gas leak detection", query: "How can I detect a gas leak?" },
                { text: "Ventilation procedures", query: "What ventilation procedures should I follow for a gas leak?" },
                { text: "Similar gas incidents", query: "Have there been similar gas leak incidents in the past?" }
            );
        }

        updateSuggestionChips(suggestions);
    }

    function updateSuggestionChips(suggestions) {
        if (!suggestions.length || !suggestionChips.length) return;
        for (let i = 0; i < suggestionChips.length && i < suggestions.length; i++) {
            suggestionChips[i].textContent = suggestions[i].text;
            suggestionChips[i].setAttribute("data-query", suggestions[i].query);
        }
    }

    scrollToBottom();
});
