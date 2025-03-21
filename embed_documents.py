import numpy as np
import faiss
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbedDocuments:
    def __init__(self, model_name="all-mpnet-base-v2"):
        """
        Initializes the embedding model and FAISS index.
        
        :param model_name: SentenceTransformer model to use for embeddings.
        """
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise e

        self.index = None
        self.doc_mapping = {}  # Stores document IDs mapped to filenames

    def embed_texts(self, documents):
        """
        Generates embeddings for extracted text and stores them in FAISS.
        
        :param documents: List of tuples (file_name, extracted_text).
        """
        if not documents:
            logger.warning("No documents provided for embedding.")
            return
        
        texts = [doc[1] for doc in documents]  # Extract text only
        filenames = [doc[0] for doc in documents]  # Extract filenames

        logger.info(f"Generating embeddings for {len(documents)} documents...")
        embeddings = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

        # Convert embeddings to float64 for FAISS compatibility
        embeddings = np.array(embeddings, dtype=np.float64)
        dimension = embeddings.shape[1]

        # Initialize FAISS index if it does not exist
        if self.index is None:
            self.index = faiss.IndexHNSWFlat(dimension, 32)
            self.index.hnsw.efConstruction = 64

        # Store document mappings
        for i, filename in enumerate(filenames):
            self.doc_mapping[i] = filename  # Maps FAISS index to filename

        # Add embeddings to FAISS index
        self.index.add(embeddings)
        logger.info("Embeddings stored in FAISS index.")

    def save_index(self, index_path="faiss_index.bin", mapping_path="doc_mapping.npy"):
        """
        Saves the FAISS index and document mappings to disk.
        
        :param index_path: Path to save FAISS index.
        :param mapping_path: Path to save document mapping.
        """
        if self.index is None:
            logger.error("No FAISS index found. Ensure documents are embedded first.")
            return
        
        faiss.write_index(self.index, index_path)
        np.save(mapping_path, self.doc_mapping)
        logger.info(f"FAISS index saved to {index_path} and mapping saved to {mapping_path}.")

    def load_index(self, index_path="faiss_index.bin", mapping_path="doc_mapping.npy"):
        """
        Loads a previously saved FAISS index and document mapping.
        
        :param index_path: Path to load FAISS index from.
        :param mapping_path: Path to load document mapping from.
        """
        try:
            self.index = faiss.read_index(index_path)
            self.doc_mapping = np.load(mapping_path, allow_pickle=True).item()
            logger.info("FAISS index and document mapping loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
