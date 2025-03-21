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
        :return: Severity Level (Low, Medium, High, Critical) and rationale
        """
        # Retrieve similar past incidents
        similar_incidents = self.search_engine.search_documents(incident_description, top_n=3)
        context = "\n".join([incident[2] for incident in similar_incidents])

        # Construct query for LLM
        llm_prompt = f"""
        Given the following incident description:

        {incident_description}

        And past similar incidents:

        {context}

        Determine the severity level of this incident based on its potential harm. 
        Categorize it as: Low, Medium, High, or Critical.
        Provide a short rationale explaining why you chose this severity.
        Respond in JSON format with keys 'severity' and 'rationale'.
        """

        # Use LLM Handler
        try:
            response = self.llm_handler.generate_response(llm_prompt)

            if not response.strip():  # Check if response is empty
                logger.error("LLM returned an empty response.")
                return self.rule_based_severity(incident_description)

            logger.info(f"LLM Raw Response: {response}")  # Log response for debugging

            # Clean response: Remove triple backticks and language labels
            cleaned_response = re.sub(r"```json\n(.*?)\n```", r"\1", response, flags=re.DOTALL).strip()

            try:
                result = json.loads(cleaned_response)  # Parse cleaned JSON
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

        # Check for keywords
        for word, level in keywords.items():
            if word in incident_description.lower():
                severity = level
                rationale = f"Keyword '{word}' detected, classified as {level} risk."
                break  # Stop at first match

        return severity, rationale
