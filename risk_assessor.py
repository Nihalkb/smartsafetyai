import logging
import json
import re
from llm_handler import LLMHandler
from search_engine import SearchEngine

logger = logging.getLogger(__name__)

class RiskAssessor:
    def __init__(self):
        """Initializes the Risk Assessor with LLM API and Vector Search."""
        self.llm_handler = LLMHandler()
        self.search_engine = SearchEngine()  # Retrieve past similar incidents

    def assess_severity(self, incident_description):
        """
        Assesses risk severity based on past incidents and LLM analysis.

        :param incident_description: Description of the incident
        :return: Severity Level (Minimal, Low, Moderate, High, Critical) and rationale
        """
        # Retrieve similar past incidents from the vector search.
        similar_incidents = self.search_engine.search_documents(incident_description, top_n=3)
        # Build context from the retrieved chunks using the "text" key.
        context = "\n".join([incident.get("text", "") for incident in similar_incidents])

        # Construct a query for the LLM.
        llm_prompt = f"""
Given the following incident description:

{incident_description}

And past similar incidents:

{context}

Determine the severity level of this incident based on its potential harm.
Categorize it as: Minimal, Low, Moderate, High, or Critical.
Provide a short rationale explaining your classification.
Respond in JSON format with keys "severity" and "rationale".
"""

        try:
            response = self.llm_handler.generate_response(llm_prompt)
            if not response.strip():
                logger.error("LLM returned an empty response.")
                return self.rule_based_severity(incident_description)

            logger.info(f"LLM Raw Response: {response}")

            # Clean response: Remove triple backticks if present.
            cleaned_response = re.sub(r"```json\n(.*?)\n```", r"\1", response, flags=re.DOTALL).strip()
            try:
                result = json.loads(cleaned_response)
                severity = result.get("severity", "Unknown")
                rationale = result.get("rationale", "No explanation provided.")
                return severity, rationale
            except json.JSONDecodeError as e:
                logger.error(f"JSON Parsing Error: {e} | Cleaned Response: {cleaned_response}")
                return self.rule_based_severity(incident_description)
        except Exception as e:
            logger.error(f"LLM Risk Assessment Error: {e}")
            return self.rule_based_severity(incident_description)

    def rule_based_severity(self, incident_description):
        """
        Backup heuristic-based risk scoring when LLM is unavailable.

        :param incident_description: Incident text
        :return: Severity Level (Low, Medium, High, Critical) and rationale
        """
        keywords = {
            "explosion": "Critical",
            "fire": "High",
            "gas leak": "High",
            "chemical spill": "Medium",
            "equipment failure": "Medium",
            "minor injury": "Low",
            "property damage": "Medium",
        }

        # Default severity
        severity = "Low"
        rationale = "No major hazard detected."
        for word, level in keywords.items():
            if word in incident_description.lower():
                severity = level
                rationale = f"Keyword '{word}' detected, classified as {level} risk."
                break
        return severity, rationale
