document.addEventListener("DOMContentLoaded", function () {
    const riskForm = document.getElementById("risk-assessment-form");
    const incidentTitle = document.getElementById("incident-title");
    const incidentDetails = document.getElementById("incident-details");
    const loadingAssessment = document.getElementById("loading-assessment");
    const resultsContainer = document.getElementById("results-container");
    const severityIndicator = document.getElementById("severity-indicator");
    const severityScore = document.getElementById("severity-score");
    const severityClassification = document.getElementById("severity-classification");
    const severityRationale = document.getElementById("severity-rationale");
    const predictiveInsights = document.getElementById("predictive-insights");

    // Severity mapping from text → numeric scale
    const severityMapping = {
        "Minimal": 1,
        "Low": 2,
        "Moderate": 3,
        "High": 4,
        "Critical": 5
    };

    // Initialize severity chart with sample data
    initSeverityChart();

    // Set up event listeners
    riskForm.addEventListener("submit", function (e) {
        e.preventDefault();
        performRiskAssessment();
    });

    function performRiskAssessment() {
        const title = incidentTitle.value.trim();
        const details = incidentDetails.value.trim();

        if (!title || !details) {
            showError("Please provide both a title and details for the incident.");
            return;
        }

        // Show loading indicator
        loadingAssessment.style.display = "block";
        resultsContainer.style.display = "none";

        // Make API request
        fetch("/api/risk-assessment", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: title,
                details: details
            })
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then((data) => {
                // Hide loading indicator
                loadingAssessment.style.display = "none";

                // Display results
                displayResults(data);
            })
            .catch((error) => {
                console.error("Error during risk assessment:", error);
                loadingAssessment.style.display = "none";
                showError("An error occurred during risk assessment. Please try again.");
            });
    }

    function displayResults(data) {
        const severityText = data.severity;
        const severityNum = severityMapping[severityText] || 1; // Default to Minimal if not found

        // Update severity indicator position
        const position = ((severityNum - 1) / 4) * 100; // Scale 1-5 to 0-100%
        severityIndicator.style.left = `${position}%`;

        // Update severity score and classification
        severityScore.textContent = severityNum;
        severityClassification.textContent = severityText;

        // Update color based on severity
        severityClassification.className = "";
        if (severityNum >= 4) {
            severityClassification.classList.add("text-danger", "fw-bold");
        } else if (severityNum === 3) {
            severityClassification.classList.add("text-warning", "fw-bold");
        } else {
            severityClassification.classList.add("text-success");
        }

        // Update rationale and insights
        severityRationale.textContent = data.rationale || "No explanation provided.";
        predictiveInsights.textContent = data.insights || "No insights available.";

        // Show results container
        resultsContainer.style.display = "block";

        // Update chart with new data point
        updateChartWithNewAssessment(severityNum);
    }

    function initSeverityChart() {
        const ctx = document.getElementById("severity-chart").getContext("2d");

        // Sample historical data
        const sampleData = {
            labels: ["Minimal", "Low", "Moderate", "High", "Critical"],
            datasets: [
                {
                    label: "Historical Incidents by Severity",
                    data: [5, 12, 18, 8, 3],
                    backgroundColor: ["#28a745", "#a3c739", "#ffc107", "#fd7e14", "#dc3545"],
                    borderWidth: 1
                }
            ]
        };

        window.severityChart = new Chart(ctx, {
            type: "bar",
            data: sampleData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Number of Incidents"
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: "Severity Level"
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `Incidents: ${context.raw}`;
                            }
                        }
                    }
                }
            }
        });
    }

    function updateChartWithNewAssessment(severityNum) {
        if (window.severityChart) {
            // Severity is 1-5, array index is 0-4
            const dataIndex = severityNum - 1;
            window.severityChart.data.datasets[0].data[dataIndex]++;
            window.severityChart.update();
        }
    }

    function showError(message) {
        let errorAlert = document.getElementById("assessment-error");

        if (!errorAlert) {
            errorAlert = document.createElement("div");
            errorAlert.id = "assessment-error";
            errorAlert.className = "alert alert-danger mt-3";
            riskForm.appendChild(errorAlert);
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
