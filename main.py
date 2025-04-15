import os
import logging
from flask import Flask
from embed_documents import EmbedDocuments
from search_engine import SearchEngine
from llm_handler import LLMHandler
from chatbot import Chatbot
from risk_assessor import RiskAssessor
from preprocess_incidents import extract_incident_data_from_txt, save_incident_data
import pandas as pd
import json

# Initialize Flask App
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your_secret_key")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths
DOCUMENTS_FOLDER = "data/pdfs"
PROCESSED_DOCS_FOLDER = "processed_docs"
FAISS_INDEX_PATH = "faiss_index.bin"
MAPPING_PATH = "doc_mapping.npy"

# Incident data preprocessing paths
INCIDENT_DOCX_PATH = "processed_docs/Incident_report_modified_without regulatory clause_200 cases.docx.txt"
INCIDENT_OUTPUT_FOLDER = "data/processed"
INCIDENT_CSV_PATH = os.path.join(INCIDENT_OUTPUT_FOLDER, "incident_reports.csv")
INCIDENT_JSON_PATH = os.path.join(INCIDENT_OUTPUT_FOLDER, "incident_reports.json")

# Ensure required folders exist
os.makedirs(PROCESSED_DOCS_FOLDER, exist_ok=True)
os.makedirs(INCIDENT_OUTPUT_FOLDER, exist_ok=True)

# Initialize components
# We no longer use doc_processor for PDF extraction since we want page numbers.
embedder = EmbedDocuments()  # This module now has process_file integrated.
search_engine = SearchEngine(index_path=FAISS_INDEX_PATH, mapping_path=MAPPING_PATH)
llm_handler = LLMHandler()
chatbot = Chatbot()
risk_assessor = RiskAssessor()

def process_and_embed_documents():
    """Processes documents from DOCUMENTS_FOLDER using the integrated extraction/chunking,
       then embeds and indexes them.
    """
    logger.info("Processing documents...")
    # List only supported files (PDF and DOCX)
    files = [f for f in os.listdir(DOCUMENTS_FOLDER) if f.lower().endswith((".pdf", ".docx"))]
    
    if not files:
        logger.warning("No documents found for processing.")
        return

    all_chunks = []
    for file_name in files:
        file_path = os.path.join(DOCUMENTS_FOLDER, file_name)
        # Use the process_file method from embed_documents which performs extraction and chunking.
        chunks = embedder.process_file(file_path)
        if chunks:
            all_chunks.extend(chunks)
            # Save the full extracted text to a file in the processed_docs folder for reference.
            with open(os.path.join(PROCESSED_DOCS_FOLDER, f"{file_name}.txt"), "w", encoding="utf-8") as f:
                # Concatenate all chunk texts (or you can use your own extraction function)
                f.write("\n\n".join([chunk["text"] for chunk in chunks]))
        else:
            logger.warning(f"No chunks produced for file: {file_name}")

    logger.info(f"Total chunks created: {len(all_chunks)}")
    embedder.embed_texts(all_chunks)
    embedder.save_index(index_path=FAISS_INDEX_PATH, mapping_path=MAPPING_PATH)
    logger.info("Documents processed, chunked, and indexed successfully.")

def preprocess_incident_data():
    """Extract structured incident data and save to disk."""   
    if os.path.exists(INCIDENT_CSV_PATH):
        logger.info("Incident report data already processed.")
        return

    if not os.path.exists(INCIDENT_DOCX_PATH):
        logger.warning("No incident DOCX file found.")
        return

    try:
        df = extract_incident_data_from_txt(INCIDENT_DOCX_PATH)
        save_incident_data(df, INCIDENT_OUTPUT_FOLDER)
        logger.info("Incident data extracted and saved.")
    except Exception as e:
        logger.error(f"Failed to preprocess incident data: {e}")

# Run preprocessors before app launch
if not os.path.exists(FAISS_INDEX_PATH):
    process_and_embed_documents()
else:
    logger.info("FAISS index already exists. Skipping document processing.")

preprocess_incident_data()

# Import routes after initialization
from routes import *

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT not set
    app.run(host="0.0.0.0", port=port)
