from flask import render_template, request, jsonify, session
import uuid
import logging
import os
from app import app
from search_engine import SearchEngine
from llm_handler import LLMHandler
from chatbot import Chatbot
from risk_assessor import RiskAssessor
import pandas as pd 
import json 

logger = logging.getLogger(__name__)

# Initialize components
search_engine = SearchEngine()
llm_handler = LLMHandler()
chatbot = Chatbot()
risk_assessor = RiskAssessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search_page():
    return render_template('search.html')

@app.route('/chat')
def chat_page():
    """Renders the chatbot UI and assigns a session ID with available documents."""
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())

    processed_folder = "processed_docs"
    available_docs = []
    if os.path.exists(processed_folder):
        available_docs = [
            f.replace(".txt", "") for f in os.listdir(processed_folder)
            if f.endswith(".txt") and "incident_reports" not in f.lower()
        ]

    return render_template(
        'chat.html',
        session_id=session['chat_session_id'],
        available_docs=available_docs
    )

@app.route('/risk-assessment')
def risk_assessment():
    return render_template('risk_assessment.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    query = data.get("query", "")

    if not query:
        return jsonify({"error": "Query required"}), 400

    try:
        results = search_engine.nlp_incident_query(query)
        # Format each source to include document name and page number.
        formatted_sources = []
        for src in results.get("sources", []):
            doc_name = src.get("doc", "").strip() or "Unknown Document"
            page = src.get("page")
            page_str = str(page) if page is not None else "N/A"
            formatted_sources.append(f"Document: {doc_name}, Page: {page_str}")
            
        return jsonify({
            "query": query,
            "answers": results.get("summary", "No summary available."),
            "sources": formatted_sources,
            "incidents": results.get("incidents", [])
        })
    except Exception as e:
        logger.error(f"NLP search failed: {e}")
        return jsonify({
            "error": "Search failed. Please try again.",
            "answers": "",
            "sources": [],
            "incidents": []
        }), 500

from incident_filters import load_incident_data, filter_incidents
from incident_graphs import (
    generate_material_bar_chart,
    generate_operator_pie_chart,
    generate_incidents_over_time,
    generate_severity_chart,
    generate_location_chart
)

@app.route('/api/incidents/filter', methods=['POST'])
def api_filter_incidents():
    data = request.json
    df = load_incident_data()

    if "query" in data:
        # Parse filters from natural language using LLM
        try:
            parsed = llm_handler.parse_filters(data["query"])
            logger.info("Parsed filters from query: %s", parsed)
            # Remove unsupported keys like 'operator'
            parsed.pop("operator", None)
        except Exception as e:
            logger.error(f"LLM filter parsing failed: {e}")
            return jsonify({"error": "Could not interpret query"}), 400
    else:
        # Use traditional form filters
        parsed = {
            "material": data.get("material"),
            "location_contains": data.get("location_contains"),
            "from_year": data.get("from_year"),
            "to_year": data.get("to_year"),
            "has_injuries": data.get("has_injuries"),
            "severity": data.get("severity")
        }

    filtered_df = filter_incidents(df, **parsed)
    # Replace NaN with None to ensure valid JSON
    incidents_list = filtered_df.where(pd.notnull(filtered_df), None).to_dict(orient="records")

    # Build context for AI summarization from incidents.
    incident_texts = []
    for record in incidents_list:
        text_parts = []
        if record.get("Material Released"):
            text_parts.append(f"Material: {record.get('Material Released')}")
        if record.get("Date"):
            text_parts.append(f"Date: {record.get('Date')}")
        if record.get("Location"):
            text_parts.append(f"Location: {record.get('Location')}")
        if record.get("Casualties & Injuries"):
            text_parts.append(f"Injuries: {record.get('Casualties & Injuries')}")
        if record.get("Severity"):
            text_parts.append(f"Severity: {record.get('Severity')}")
        if text_parts:
            incident_texts.append(", ".join(text_parts))

    if incident_texts:
        chunks = [{"text": text} for text in incident_texts]
        ai_summary = llm_handler.generate_summary_from_chunks(data.get("query", ""), chunks)
    else:
        ai_summary = "No incident details available for summarization."

    # Clean up filters (replace NaN with None)
    parsed = {k: (v if pd.notnull(v) else None) for k, v in parsed.items()}

    return jsonify({
        "results": incidents_list,
        "count": len(incidents_list),
        "filters": parsed,
        "ai_summary": ai_summary
    })

@app.route('/api/incidents/chart', methods=['POST'])
def api_incident_chart():
    data = request.json
    chart_type = data.get("chart_type", "bar")

    df = load_incident_data()
    filtered_df = filter_incidents(
        df,
        material=data.get("material"),
        location_contains=data.get("location_contains"),
        from_year=data.get("from_year"),
        to_year=data.get("to_year"),
        has_injuries=data.get("has_injuries"),
        severity=data.get("severity")
    )

    if chart_type == "pie":
        chart = generate_operator_pie_chart(filtered_df)
    elif chart_type == "line":
        chart = generate_incidents_over_time(filtered_df)
    elif chart_type == "severity":
        chart = generate_severity_chart(filtered_df)
    elif chart_type == "location":
        chart = generate_location_chart(filtered_df)
    else:
        chart = generate_material_bar_chart(filtered_df)

    return jsonify({"chart": chart})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handles chatbot interaction and returns structured result."""
    data = request.json
    message = data.get("message", "")
    filter_files = data.get("filter_files", None)
    session_id = session.get("chat_session_id")

    if not message or not session_id:
        return jsonify({"error": "Message and session_id required"}), 400

    result = chatbot.chat(session_id, message, filter_files=filter_files)

    # Format sources for display, if they exist
    formatted_sources = []
    for src in result.get("sources", []):
        if isinstance(src, str):
            formatted_sources.append(src)
        else:
            doc_name = src.get("doc", "").strip() or "Unknown Document"
            page = src.get("page")
            page_str = str(page) if page is not None else "N/A"
            formatted_sources.append(f"Document: {doc_name}, Page: {page_str}")

    return jsonify({
        "response": result.get("answer", "No response."),
        "sources": formatted_sources,
        "incidents": result.get("incidents", []),
        "referenced_chunks": result.get("referenced_chunks", []),
        "session_id": session_id
    })


@app.route('/api/chat/clear', methods=['POST'])
def clear_chat_memory():
    session_id = session.get("chat_session_id")
    if chatbot.clear_memory(session_id):
        return jsonify({"message": "Chat history cleared", "session_id": session_id})
    return jsonify({"error": "No active chat session"}), 400

@app.route('/api/chat/upload', methods=['POST'])
def upload_chat_document():
    session_id = session.get("chat_session_id")
    if not session_id:
        return jsonify({"error": "Session not initialized"}), 400

    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return jsonify({"error": "No file provided"}), 400

    filename = uploaded_file.filename
    os.makedirs("data/uploads", exist_ok=True)
    save_path = os.path.join("data/uploads", filename)
    uploaded_file.save(save_path)

    success = chatbot.process_uploaded_file(session_id, save_path)
    if success:
        return jsonify({"success": True, "message": f"{filename} processed and ready for chat."})
    else:
        return jsonify({"success": False, "error": f"Could not process {filename}"}), 500

@app.route('/api/risk-assessment', methods=['POST'])
def api_risk_assessment():
    data = request.json
    incident_description = data.get("details", "")

    if not incident_description:
        return jsonify({"error": "Incident details required"}), 400

    try:
        severity, rationale = risk_assessor.assess_severity(incident_description)
        return jsonify({"severity": severity, "rationale": rationale})
    except Exception as e:
        logger.error(f"Risk assessment error: {e}")
        return jsonify({"error": "Risk assessment failed. Please try again later."}), 500

@app.route('/api/similarity-search', methods=['POST'])
def similarity_search():
    return None

@app.route('/api/document-summary', methods=['POST'])
def document_summary():
    return None

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500
