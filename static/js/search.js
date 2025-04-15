// Enhances the incident filter UI with AI-powered search integration

document.addEventListener("DOMContentLoaded", function () {
    const applyButton = document.getElementById("apply-filters");
    const searchResults = document.getElementById("search-results");
    const resultDocuments = document.getElementById("result-documents");
    let chartContainer = document.getElementById("chart-container");
    const nlpInput = document.getElementById("nlp-query");
    const nlpSearchBtn = document.getElementById("submit-nlp-search");
    const toggle = document.getElementById("toggle-advanced-search");
    const aiCard = document.getElementById("ai-insight");
    const aiText = document.getElementById("ai-answer-text");
    const filterPanel = document.querySelector(".filter-section#filter-panel");
    const filterSummaryBox = document.getElementById("parsed-filter-summary");
    const chartTypeSelect = document.getElementById("chart-type-select");

    let currentFilters = null;

    toggle.checked = false;
    filterPanel.style.display = "none";
    nlpInput.closest(".filter-section").style.display = "block";

    toggle.addEventListener("change", function () {
        const advancedMode = toggle.checked;
        filterPanel.style.display = advancedMode ? "block" : "none";
        nlpInput.closest(".filter-section").style.display = advancedMode ? "none" : "block";
        aiCard.style.display = "none";
        filterSummaryBox.style.display = "none";
        chartContainer.innerHTML = "";
    });

    function isIncidentQuery(query) {
        const incidentKeywords = ["incident", "leak", "spill", "injur", "explosion", "pipeline"];
        return incidentKeywords.some(keyword => query.toLowerCase().includes(keyword));
    }

    async function loadChart(filters) {
        if (!filters) return;

        // Remove and recreate chart container to fully reset DOM and memory
        const oldContainer = chartContainer;
        const parent = oldContainer.parentElement;
        const newContainer = document.createElement("div");
        newContainer.id = "chart-container";
        newContainer.className = "chart-container";
        parent.replaceChild(newContainer, oldContainer);
        chartContainer = newContainer;

        try {
            const res = await fetch("/api/incidents/chart", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...filters, chart_type: chartTypeSelect.value })
            });

            const data = await res.json();

            if (data.chart) {
                const img = document.createElement("img");
                img.src = data.chart;
                img.alt = "Incident chart";
                img.classList.add("img-fluid", "rounded", "mt-2");
                chartContainer.appendChild(img);
            } else {
                chartContainer.innerHTML = `
                    <div class="text-muted small border rounded p-2 mt-2" style="background-color: var(--bs-light); color: #555;">
                        No chart available for this query.
                    </div>`;
            }
        } catch (err) {
            console.error("Chart fetch error:", err);
            chartContainer.innerHTML = `
                <div class="alert alert-warning mt-2">
                    Failed to load chart. Please try again.
                </div>`;
        }
    }

    chartTypeSelect.addEventListener("change", async function () {
        await loadChart(currentFilters);
    });

    nlpSearchBtn.addEventListener("click", async function () {
        const query = nlpInput.value.trim();
        if (!query) return;

        resultDocuments.innerHTML = "";
        chartContainer.innerHTML = "";
        aiCard.style.display = "none";
        filterSummaryBox.style.display = "none";
        searchResults.style.display = "none";

        aiText.innerText = "Loading answer...";
        aiCard.style.display = "block";

        try {
            let data;
            if (isIncidentQuery(query)) {
                const res = await fetch("/api/incidents/filter", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query })
                });
                data = await res.json();

                aiText.innerText = (data.ai_summary && !data.ai_summary.includes("Unable to generate response"))
                    ? data.ai_summary : "No insight found.";

                if (data.results && data.results.length > 0) {
                    data.results.forEach((incident) => {
                        resultDocuments.appendChild(createResultCard(incident));
                    });
                } else {
                    resultDocuments.innerHTML = '<div class="alert alert-info">No matching incidents found.</div>';
                }

                currentFilters = data.filters || { query };
                await loadChart(currentFilters);
            } else {
                const res = await fetch("/api/search", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query })
                });
                data = await res.json();

                aiText.innerText = (data.answers && !data.answers.includes("Unable to generate response"))
                    ? data.answers : "No answer found.";

                let foundResults = false;

                if (data.incidents && data.incidents.length > 0) {
                    data.incidents.forEach((incident) => {
                        resultDocuments.appendChild(createResultCard(incident));
                    });
                    foundResults = true;
                }

                if (!foundResults) {
                    resultDocuments.innerHTML = '<div class="alert alert-info">No matching incidents or documents found.</div>';
                }

                currentFilters = { query };
                await loadChart(currentFilters);
            }

            if (data.filters) {
                filterSummaryBox.innerText = "Parsed Filters: " + Object.entries(data.filters)
                    .filter(([_, val]) => val !== null && val !== "")
                    .map(([key, val]) => `${key}: ${val}`)
                    .join(", ");
                filterSummaryBox.style.display = "block";
            }
            searchResults.style.display = "block";
        } catch (err) {
            console.error("NLP Search error:", err);
            aiText.innerText = "Error loading answer.";
        }
    });

    applyButton.addEventListener("click", async function () {
        const filters = gatherFilters();
        currentFilters = filters;

        resultDocuments.innerHTML = "";
        chartContainer.innerHTML = "";
        searchResults.style.display = "none";
        aiCard.style.display = "none";
        filterSummaryBox.style.display = "none";

        try {
            const res = await fetch("/api/incidents/filter", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(filters)
            });
            const data = await res.json();

            if (data.results && data.results.length > 0) {
                data.results.forEach((incident) => {
                    resultDocuments.appendChild(createResultCard(incident));
                });
            } else {
                resultDocuments.innerHTML = '<div class="alert alert-info">No incidents matched your filters.</div>';
            }

            if (data.ai_summary && !data.ai_summary.includes("Unable to generate response")) {
                aiText.innerText = data.ai_summary;
                aiCard.style.display = "block";
            }

            if (data.filters) {
                filterSummaryBox.innerText = "Parsed Filters: " + Object.entries(data.filters)
                    .filter(([_, val]) => val !== null && val !== "")
                    .map(([key, val]) => `${key}: ${val}`)
                    .join(", ");
                filterSummaryBox.style.display = "block";
            }

            searchResults.style.display = "block";
            await loadChart(currentFilters);
        } catch (err) {
            console.error("Filter search error:", err);
        }

        try {
            if (!aiText.innerText || aiText.innerText.trim().length === 0 ||
                aiText.innerText.includes("Unable to generate response")) {
                const prompt = buildQueryFromFilters(filters);
                const res = await fetch("/api/search", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query: prompt })
                });
                const data = await res.json();

                if (data.answers && !data.answers.includes("Unable to generate response")) {
                    aiText.innerText = data.answers;
                    aiCard.style.display = "block";
                }
            }
        } catch (err) {
            console.error("AI augmentation error:", err);
        }
    });

    function gatherFilters() {
        const injuriesVal = document.getElementById("filter-injuries").value;
        const injuryFlag = injuriesVal === "yes" ? true : injuriesVal === "no" ? false : null;

        return {
            material: document.getElementById("filter-material").value.trim(),
            location_contains: document.getElementById("filter-location").value.trim(),
            from_year: parseInt(document.getElementById("filter-from-year").value) || null,
            to_year: parseInt(document.getElementById("filter-to-year").value) || null,
            has_injuries: injuryFlag,
            severity: document.getElementById("filter-severity")?.value.trim() || null
        };
    }

    function buildQueryFromFilters(filters) {
        let query = "Show incidents";
        if (filters.material) query += ` involving ${filters.material}`;
        if (filters.location_contains) query += ` in locations including ${filters.location_contains}`;
        if (filters.from_year || filters.to_year)
            query += ` from ${filters.from_year || "any year"} to ${filters.to_year || "present"}`;
        if (filters.has_injuries !== null)
            query += filters.has_injuries ? ", with injuries" : ", without injuries";
        if (filters.severity) query += ` with ${filters.severity} severity`;
        return query;
    }

    function createResultCard(data) {
        const card = document.createElement("div");
        card.className = "card result-card mb-3";

        const title = data["Date"] ? `${data["Date"]} – ${data["Location"] || ""}` : "Document/Incident";

        card.innerHTML = `
        <div class="card dynamic-result mb-3">
          <div class="card-header">
            <h6 class="mb-0">${title}</h6>
          </div>
          <div class="card-body">
            <p><strong>Operator/Source:</strong> ${data["Pipeline Operator"] || data["doc"] || "N/A"}</p>
            <p><strong>Material:</strong> ${data["Material Released"] || "N/A"}</p>
            <p><strong>Description:</strong> ${data["Incident Description"] || data["text"] || "No description available"}</p>
            <p><strong>Response/Notes:</strong> ${data["Response Actions"] || "N/A"}</p>
            <p><strong>Casualties/Injuries:</strong> ${data["Casualties & Injuries"] || "N/A"}</p>
          </div>
        </div>
      `;

        return card;
    }
});
