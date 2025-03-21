document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-input");
    const searchButton = document.getElementById("search-button");
    const loadingSpinner = document.getElementById("loading-spinner");
    const searchResults = document.getElementById("search-results");
    const aiAnswer = document.getElementById("ai-answer");
    const resultDocuments = document.getElementById("result-documents");
    const exampleQueries = document.querySelectorAll(".example-query");

    // Set up event listeners
    searchButton.addEventListener("click", performSearch);
    searchInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
            performSearch();
        }
    });

    // Handle example queries
    exampleQueries.forEach(example => {
        example.addEventListener("click", function () {
            const query = this.getAttribute("data-query");
            searchInput.value = query;
            performSearch();
        });
    });

    function performSearch() {
        const query = searchInput.value.trim();

        if (!query) {
            showError("Please enter a search query.");
            return;
        }

        // Show loading spinner
        loadingSpinner.style.display = "block";
        searchResults.style.display = "none";
        aiAnswer.innerHTML = "";
        resultDocuments.innerHTML = "";

        // Make API request
        fetch("/api/search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query: query }),
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then(data => {
                loadingSpinner.style.display = "none";
                displayResults(data);
            })
            .catch(error => {
                console.error("Error during search:", error);
                loadingSpinner.style.display = "none";
                showError("An error occurred while searching. Please try again.");
            });
    }

    function displayResults(data) {
        // Clear previous results
        aiAnswer.innerHTML = "";
        resultDocuments.innerHTML = "";

        // Format and display AI-generated answer
        const formattedAnswer = formatAnswer(data.answers);
        aiAnswer.innerHTML = formattedAnswer;

        // Display ranked source documents
        if (data.results && data.results.length > 0) {
            // Sort results by highest similarity score
            let sortedResults = data.results.sort((a, b) => b.score - a.score);

            sortedResults.forEach(result => {
                const resultCard = createResultCard(result);
                resultDocuments.appendChild(resultCard);
            });
        } else {
            resultDocuments.innerHTML =
                '<div class="alert alert-info">No source documents found for this query.</div>';
        }

        // Show results section
        searchResults.style.display = "block";
    }

    function formatAnswer(answer) {
        if (!answer) return "<p class='text-muted'>No AI-generated response available.</p>";

        // Replace newlines with HTML line breaks
        let formattedAnswer = answer.replace(/\n/g, "<br>");

        // Highlight key safety terms
        const importantTerms = [
            "Emergency", "Protocol", "Hazard", "Risk", "Critical", "Warning",
            "Caution", "Danger", "Safety", "Procedure", "Guideline"
        ];

        importantTerms.forEach(term => {
            const regex = new RegExp(`\\b${term}\\b`, "gi");
            formattedAnswer = formattedAnswer.replace(regex, '<span class="text-info">$&</span>');
        });

        return formattedAnswer;
    }

    function createResultCard(result) {
        const card = document.createElement("div");
        card.className = "card result-card mb-3";

        let cardContent = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">${result.file || "Untitled Document"}</h6>
                <span class="badge bg-secondary source-badge">Relevance: ${Math.round(result.score * 100)}%</span>
            </div>
            <div class="card-body">
                <p>${result.snippet || "No content available"}</p>
            </div>
        `;

        card.innerHTML = cardContent;
        return card;
    }

    function showError(message) {
        let errorAlert = document.getElementById("search-error");

        if (!errorAlert) {
            errorAlert = document.createElement("div");
            errorAlert.id = "search-error";
            errorAlert.className = "alert alert-danger mt-3";
            searchInput.parentNode.parentNode.appendChild(errorAlert);
        }

        errorAlert.textContent = message;

        // Auto-hide after 4 seconds
        setTimeout(() => {
            if (errorAlert.parentNode) {
                errorAlert.parentNode.removeChild(errorAlert);
            }
        }, 4000);
    }
});
