import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from models import IncidentReport
from sqlalchemy import func
from llm_handler import LLMHandler

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.llm_handler = LLMHandler()
        except Exception as e:
            self.logger.error(f"LLMHandler initialization failed: {e}")
            self.llm_handler = None

    def assess_severity(self, incident_details):
        """
        Uses the LLM exclusively to assess the severity of an incident.
        Expects a JSON response with keys:
          - severity (integer 1-5)
          - severity_level (one of 'Minimal Risk', 'Low Risk', 'Moderate Risk', 'High Risk', 'Critical Risk')
          - rationale (a brief explanation)
        
        The prompt instructs the LLM that if the incident description indicates that the gas is non toxic 
        (e.g., contains phrases like "non toxic" or "not toxic"), then a low severity should be assigned.
        """
        if not self.llm_handler:
            return 3, "LLM not available; defaulting to moderate risk."
        prompt = (
            "You are a safety risk analyst. Analyze the following incident description and return a JSON object "
            "with keys 'severity' (an integer between 1 and 5), 'severity_level' (one of 'Minimal Risk', 'Low Risk', "
            "'Moderate Risk', 'High Risk', or 'Critical Risk'), and 'rationale' (a brief explanation). "
            "Note: If the incident mentions that the gas is non toxic or not toxic, assign a low severity (1 or 2).\n\n"
            "Incident description:\n" + incident_details
        )
        try:
            response = self.llm_handler.generate_response(prompt, max_length=150)
            data = json.loads(response)
            return data.get("severity", 3), data.get("rationale", "No rationale provided.")
        except Exception as e:
            self.logger.error(f"Error in assess_severity: {e}")
            return 3, "Error assessing severity; defaulting to moderate risk."

    def generate_predictive_insights(self, incident_details, severity):
        """
        Uses the LLM exclusively to generate predictive insights.
        Expects a plain text response that provides recommendations.
        """
        if not self.llm_handler:
            return "LLM not available; no predictive insights."
        prompt = (
            "You are a safety risk analyst. Given the incident details and a severity rating of "
            f"{severity}/5, provide concise predictive insights and recommendations to mitigate future risks.\n\n"
            "Incident details:\n" + incident_details
        )
        try:
            response = self.llm_handler.generate_response(prompt, max_length=150)
            return response.strip()
        except Exception as e:
            self.logger.error(f"Error in generate_predictive_insights: {e}")
            return "Error generating predictive insights."

    def generate_enhanced_risk_report(self, incident_details):
        """
        Uses the LLM exclusively to generate a full risk report for a single incident.
        Expects a JSON response with keys:
          - severity, severity_level, rationale, predictive_insights, and timestamp.
        """
        if not self.llm_handler:
            return {"error": "LLM handler not available."}
        prompt = (
            "You are a safety risk analyst. Analyze the following incident description and return a JSON object "
            "with keys: 'severity' (integer 1-5), 'severity_level' (one of 'Minimal Risk', 'Low Risk', 'Moderate Risk', "
            "'High Risk', or 'Critical Risk'), 'rationale' (a brief explanation), 'predictive_insights' (recommendations), "
            "and 'timestamp' (ISO 8601 format).\n\nIncident description:\n" + incident_details
        )
        try:
            response = self.llm_handler.generate_response(prompt, max_length=250)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error in generate_enhanced_risk_report: {e}")
            return {"error": str(e)}

    def categorize_risk(self, incidents):
        """
        Uses the LLM exclusively to categorize a list of incidents into risk levels.
        Each incident is summarized by its ID and the first 50 characters of its description or title.
        Expects a JSON output with keys: 'Low', 'Moderate', 'High', 'Critical', and 'total_count'.
        """
        if not self.llm_handler:
            return {"error": "LLM handler not available."}
        summary_lines = []
        for inc in incidents:
            desc = getattr(inc, "description", "") or getattr(inc, "title", "")
            summary_lines.append(f"ID:{inc.id}, Desc:{desc[:50].strip()}")
        summary_text = "\n".join(summary_lines)
        prompt = (
            "You are a safety risk analyst. Given the following incident summaries (one per line), group the incident IDs "
            "into four risk categories: 'Low', 'Moderate', 'High', 'Critical', and report the total count. "
            "Return a valid JSON with keys 'Low', 'Moderate', 'High', 'Critical', and 'total_count'.\n\n"
            "Incident summaries:\n" + summary_text
        )
        try:
            response = self.llm_handler.generate_response(prompt, max_length=300)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error in categorize_risk: {e}")
            return {"error": str(e)}

    def predict_risk(self):
        """
        Uses the LLM exclusively to predict risk trends from historical incident data.
        Retrieves incidents from the past year, summarizes location counts, and delegates analysis to the LLM.
        Expects a JSON output with keys 'high_risk_locations', 'prediction_date', and 'additional_insights'.
        """
        try:
            one_year_ago = datetime.now() - timedelta(days=365)
            recent_incidents = IncidentReport.query.filter(IncidentReport.date_occurred >= one_year_ago).all()
        except Exception as e:
            self.logger.error(f"Error retrieving historical incidents: {e}")
            return {"error": str(e)}
        if not recent_incidents:
            return {"message": "Not enough historical data", "predictions": []}
        loc_counts = defaultdict(int)
        for inc in recent_incidents:
            if inc.location:
                loc_counts[inc.location] += 1
        summary_lines = []
        for loc, count in loc_counts.items():
            if count > 1:
                risk_level = "High" if count >= 3 else "Moderate"
                summary_lines.append(f"Location: {loc}, Count: {count}, Risk Level: {risk_level}")
        summary_text = "\n".join(summary_lines) if summary_lines else "No locations with multiple incidents."
        prompt = (
            "You are a safety risk analyst. Based on the following high-risk location summary data from historical incidents, "
            "provide risk predictions. Return a valid JSON with keys: 'high_risk_locations' (list of objects with 'location', "
            "'incident_count', 'risk_level'), 'prediction_date' (YYYY-MM-DD), and 'additional_insights' (brief recommendations).\n\n"
            "Location summary:\n" + summary_text
        )
        try:
            response = self.llm_handler.generate_response(prompt, max_length=250)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error in predict_risk: {e}")
            return {"error": str(e)}
