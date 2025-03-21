import logging
import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VECTOR_STORE_DIR = "data/vector_store"
FAISS_INDEX_FILE = os.path.join(VECTOR_STORE_DIR, "documents_faiss.bin")
METADATA_FILE = os.path.join(VECTOR_STORE_DIR, "document_metadata.json")

# Ensure necessary directories exist
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# Load embedding model
embedding_model = SentenceTransformer("all-mpnet-base-v2")

class VectorStore:
    def __init__(self):
        self.document_metadata = {}
        self.index = None
        self._load_or_create_vector_store()

    def _load_or_create_vector_store(self):
        """Load or initialize FAISS index and metadata."""
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, "r") as f:
                self.document_metadata = json.load(f)

        if os.path.exists(FAISS_INDEX_FILE):
            self.index = faiss.read_index(FAISS_INDEX_FILE)
        else:
            self.index = None

    def _save_metadata(self):
        """Save metadata."""
        with open(METADATA_FILE, "w") as f:
            json.dump(self.document_metadata, f)

    def add_document(self, doc_id, text, metadata):
        """Add document embeddings to FAISS index."""
        embedding = embedding_model.encode([text], normalize_embeddings=True, convert_to_numpy=True)[0].astype("float")
        
        if self.index is None:
            self.index = faiss.IndexFlatL2(embedding.shape[0])

        self.index.add(np.array([embedding], dtype="float"))
        self.document_metadata[doc_id] = metadata

        faiss.write_index(self.index, FAISS_INDEX_FILE)
        self._save_metadata()
        logger.info(f"Added document {doc_id} to vector store.")

    def search(self, query, top_k=5):
        """Find relevant documents using FAISS."""
        if self.index is None or self.index.ntotal == 0:
            logger.warning("No documents in vector store.")
            return []

        query_embedding = embedding_model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float")
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        doc_ids = list(self.document_metadata.keys())

        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(doc_ids):
                continue
            doc_id = doc_ids[idx]
            similarity = 1.0 / (1.0 + distances[0][i])  # Convert L2 distance to similarity
            result = self.document_metadata[doc_id]
            result["similarity"] = similarity
            results.append(result)

        return results

def get_vector_store():
    return VectorStore()
