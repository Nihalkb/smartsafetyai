from flask import render_template, request, jsonify, session
import uuid
import logging
from app import app
from search_engine import SearchEngine
from llm_handler import LLMHandler
from chatbot import Chatbot
from risk_assessor import RiskAssessor  # Import Risk Assessor

logger = logging.getLogger(__name__)

# Initialize components
search_engine = SearchEngine()
llm_handler = LLMHandler()
chatbot = Chatbot()
risk_assessor = RiskAssessor()  # Initialize Risk Assessor

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search_page():
    return render_template('search.html')

@app.route('/chat')
def chat_page():
    """Renders the chatbot UI and assigns a session ID."""
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())
    return render_template('chat.html', session_id=session['chat_session_id'])

@app.route('/risk-assessment')
def risk_assessment():
    return render_template('risk_assessment.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    """Search for relevant documents and generate AI-powered responses."""
    data = request.json
    query = data.get("query", "")

    if not query:
        return jsonify({"error": "Query required"}), 400

    results = search_engine.search_documents(query, top_n=3)
    context = "\n".join([res[2] for res in results])  # Combine extracted snippets
    response_text = llm_handler.generate_response(query, context)

    return jsonify({
        "query": query,
        "results": [
            {
                "file": res[0],
                "score": float(res[1]),  # Convert float32 → float
                "snippet": res[2]
            }
            for res in results
        ],
        "answers": response_text
    })

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handles chatbot interaction and maintains session-based memory."""
    data = request.json
    message = data.get("message", "")
    session_id = session.get("chat_session_id")

    if not message or not session_id:
        return jsonify({"error": "Message and session_id required"}), 400

    # Process chatbot response
    response_text = chatbot.chat(session_id, message)

    return jsonify({"response": response_text, "session_id": session_id})

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat_memory():
    """Clears chatbot memory for the current session."""
    session_id = session.get("chat_session_id")
    if chatbot.clear_memory(session_id):
        return jsonify({"message": "Chat history cleared", "session_id": session_id})
    return jsonify({"error": "No active chat session"}), 400

@app.route('/api/risk-assessment', methods=['POST'])
def api_risk_assessment():
    """Handles risk severity assessment for an incident."""
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

# Commented-out routes (return None)
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
