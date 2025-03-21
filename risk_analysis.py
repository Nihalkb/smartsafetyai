import logging
import numpy as np
from datetime import datetime, timedelta
from models import IncidentReport
from sqlalchemy import func
from collections import Counter
from llm_handler import LLMHandler

logger = logging.getLogger(__name__)

def categorize_risk(incidents):
    categorized = {'Low': [], 'Medium': [], 'High': [], 'Critical': []}
    for incident in incidents:
        severity = incident.severity if incident.severity else 1
        if severity <= 2:
            categorized['Low'].append(incident)
        elif severity == 3:
            categorized['Medium'].append(incident)
        elif severity == 4:
            categorized['High'].append(incident)
        else:
            categorized['Critical'].append(incident)
    result = {"categories": {}, "total_count": len(incidents)}
    for level, items in categorized.items():
        result["categories"][level] = {"count": len(items), "incidents": items[:5]}
    return result

def predict_risk():
    try:
        one_year_ago = datetime.now() - timedelta(days=365)
        recent_incidents = IncidentReport.query.filter(IncidentReport.date_occurred >= one_year_ago).all()
        if not recent_incidents:
            return {"message": "Not enough historical data", "predictions": []}
        
        # Analyze incidents by location
        locations = [inc.location for inc in recent_incidents if inc.location]
        location_counts = Counter(locations)
        high_risk_locations = [{"location": loc, "incident_count": count, "risk_level": "High" if count >= 3 else "Medium"}
                               for loc, count in location_counts.items() if count > 1]
        
        # Use the LLM to generate additional predictive insights
        try:
            llm_handler = LLMHandler()
            prompt = (
                f"Based on historical incident data from the past year and the following high-risk locations: "
                f"{high_risk_locations}, please provide additional predictive insights on potential risk trends, "
                "and recommend actions to improve safety measures."
            )
            llm_response = llm_handler.generate_response(prompt, max_length=250)
            additional_insights = llm_response.strip() if llm_response else ""
        except Exception as e:
            logger.error(f"LLM integration error in predict_risk: {e}")
            additional_insights = "LLM predictive insights not available."
        
        return {
            "high_risk_locations": high_risk_locations,
            "prediction_date": datetime.now().strftime('%Y-%m-%d'),
            "llm_insights": additional_insights
        }
    except Exception as e:
        logger.error(f"Error in risk prediction: {e}")
        return {"message": str(e), "predictions": []}
