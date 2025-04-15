import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

# Load incident data
INCIDENTS_PATH = "data/processed/incident_reports.json"
MODEL_NAME = "all-mpnet-base-v2"

# Load and embed incidents on import
incident_embeddings = None
incident_texts = []
incident_data = []
model = SentenceTransformer(MODEL_NAME)

def load_and_embed_incidents():
    global incident_embeddings, incident_texts, incident_data

    if not os.path.exists(INCIDENTS_PATH):
        logger.warning("Incident report file not found: %s", INCIDENTS_PATH)
        return

    with open(INCIDENTS_PATH, "r", encoding="utf-8") as f:
        incident_data = json.load(f)

    incident_texts = [
        f"Incident {item.get('Incident Number', '')}: {item.get('Incident Description', '')} {item.get('Response Actions', '')}"
        for item in incident_data
    ]

    logger.info("Embedding %d incidents...", len(incident_texts))
    incident_embeddings = model.encode(incident_texts, convert_to_tensor=True, normalize_embeddings=True)

# Call once at import
load_and_embed_incidents()

def find_similar_incidents(query, top_k=5, score_threshold=0.4, include_scores=False):
    """
    Returns top-k semantically similar incidents based on the query.
    """
    if incident_embeddings is None or not incident_texts:
        logger.warning("Incident embeddings not initialized.")
        return []

    query_embedding = model.encode([query], convert_to_tensor=True, normalize_embeddings=True)
    scores = cosine_similarity(query_embedding.cpu().numpy(), incident_embeddings.cpu().numpy())[0]

    top_indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for idx in top_indices:
        if scores[idx] >= score_threshold:
            incident = incident_data[idx].copy()
            if include_scores:
                incident["similarity"] = round(float(scores[idx]), 4)
            results.append(incident)

    return results
