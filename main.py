import os
import logging
from flask import Flask
from doc_processor import DocProcessor
from embed_documents import EmbedDocuments
from search_engine import SearchEngine
from llm_handler import LLMHandler

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

# Ensure required folders exist
os.makedirs(PROCESSED_DOCS_FOLDER, exist_ok=True)

# Initialize components
doc_processor = DocProcessor(DOCUMENTS_FOLDER)
embedder = EmbedDocuments()
search_engine = SearchEngine(index_path=FAISS_INDEX_PATH, mapping_path=MAPPING_PATH)
llm_handler = LLMHandler()

def process_and_embed_documents():
    """
    Extracts text from all documents, saves processed text, 
    generates embeddings, and stores them in FAISS.
    """
    logger.info("Processing documents...")
    documents = doc_processor.process_documents()
    
    if not documents:
        logger.warning("No documents found for processing.")
        return
    
    # Save processed text
    for file_name, text in documents:
        with open(os.path.join(PROCESSED_DOCS_FOLDER, f"{file_name}.txt"), "w", encoding="utf-8") as f:
            f.write(text)

    # Embed and store in FAISS
    embedder.embed_texts(documents)
    embedder.save_index(index_path=FAISS_INDEX_PATH, mapping_path=MAPPING_PATH)
    logger.info("Documents processed and indexed successfully.")

# Only process documents if FAISS index is missing
if not os.path.exists(FAISS_INDEX_PATH):
    process_and_embed_documents()
else:
    logger.info("FAISS index already exists. Skipping document processing.")

# Import routes after initializing components
from routes import *

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
