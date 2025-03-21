import os
import numpy as np
import faiss
import logging
from sentence_transformers import SentenceTransformer
from llm_handler import LLMHandler

logger = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self, embed_model="all-mpnet-base-v2", index_path="faiss_index.bin", mapping_path="doc_mapping.npy"):
        """
        Initializes the search engine, loads FAISS index, and prepares the embedding model.
        
        :param embed_model: SentenceTransformer model for query embedding.
        :param index_path: Path to the FAISS index file.
        :param mapping_path: Path to the document mapping file.
        """
        self.embedder = SentenceTransformer(embed_model)
        self.index_path = index_path
        self.mapping_path = mapping_path
        self.llm_handler = LLMHandler()

        # Load or rebuild FAISS index
        self.index, self.doc_mapping = self._load_or_build_faiss_index()

    def _load_or_build_faiss_index(self):
        """Loads FAISS index and document mappings, or rebuilds if missing."""
        if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
            try:
                index = faiss.read_index(self.index_path)
                doc_mapping = np.load(self.mapping_path, allow_pickle=True).item()
                logger.info("FAISS index and document mapping loaded successfully.")
                return index, doc_mapping
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}. Rebuilding index...")
        
        return self._build_faiss_index()

    def _build_faiss_index(self):
        """Builds FAISS index from available documents."""
        processed_docs_dir = "processed_docs"
        if not os.path.exists(processed_docs_dir):
            logger.error("Processed documents directory not found. Cannot build FAISS index.")
            return None, {}

        doc_files = [f for f in os.listdir(processed_docs_dir) if f.endswith(".txt")]
        if not doc_files:
            logger.error("No processed documents found. FAISS index cannot be created.")
            return None, {}

        # Load document contents
        doc_texts = []
        doc_mapping = {}
        for i, file_name in enumerate(doc_files):
            file_path = os.path.join(processed_docs_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    doc_texts.append(content)
                    doc_mapping[i] = file_name.replace(".txt", "")
            except Exception as e:
                logger.error(f"Error reading file {file_name}: {e}")

        if not doc_texts:
            logger.error("No document text available for embedding.")
            return None, {}

        # Generate embeddings
        doc_embeddings = self.embedder.encode(doc_texts, normalize_embeddings=True, convert_to_numpy=True)
        dimension = doc_embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(doc_embeddings)

        # Save FAISS index and mappings
        faiss.write_index(index, self.index_path)
        np.save(self.mapping_path, doc_mapping)

        logger.info("FAISS index built successfully.")
        return index, doc_mapping

    def search_documents(self, query, top_n=3):
        """
        Searches for the most relevant documents in the FAISS index.
        
        :param query: User's search query.
        :param top_n: Number of top documents to retrieve.
        :return: List of relevant documents [(filename, score, snippet)].
        """
        if not self.index:
            logger.error("FAISS index not initialized.")
            return []

        # Generate embedding for the query
        query_embedding = self.embedder.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        query_embedding = np.array(query_embedding, dtype=np.float64)

        # Search FAISS index
        distances, indices = self.index.search(query_embedding, top_n)
        results = []

        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(self.doc_mapping):
                file_name = self.doc_mapping[idx]
                extracted_text = self._extract_text(file_name)
                snippet = self.extract_relevant_passage(extracted_text, query)
                results.append((file_name, distances[0][i], snippet))

        return results

    def _extract_text(self, file_name):
        """Extracts text from stored documents (this assumes processed documents are saved)."""
        file_path = f"processed_docs/{file_name}.txt"
        if not os.path.exists(file_path):
            logger.error(f"Processed document not found: {file_name}")
            return "Document content unavailable."

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_name}: {e}")
            return "Error retrieving document content."

    def extract_relevant_passage(self, text, query, window_size=300):
        """
        Extracts the most relevant passage from the document.
        
        :param text: Full document text.
        :param query: Search query.
        :param window_size: Maximum size of the extracted snippet.
        :return: Most relevant text snippet.
        """
        sentences = text.split(". ")  # Simple sentence split
        query_words = set(query.lower().split())

        best_snippet = ""
        best_score = 0

        for sentence in sentences:
            words = set(sentence.lower().split())
            score = len(query_words.intersection(words))
            
            if score > best_score:
                best_score = score
                best_snippet = sentence

        return best_snippet[:window_size] if best_snippet else "No relevant snippet found."

    def generate_llm_response(self, query, context):
        """
        Uses LLM to generate a detailed answer based on retrieved context.
        
        :param query: User's question.
        :param context: Extracted relevant text.
        :return: AI-generated response.
        """
        try:
            return self.llm_handler.generate_response(query, context)
        except Exception as e:
            logger.error(f"LLM response generation error: {e}")
            return "Unable to generate response at this time."
