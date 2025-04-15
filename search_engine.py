import os
import numpy as np
import faiss
import logging
from sentence_transformers import SentenceTransformer
from llm_handler import LLMHandler
from incident_matcher import find_similar_incidents

logger = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self, embed_model="all-mpnet-base-v2", index_path="faiss_index.bin", mapping_path="doc_mapping.npy"):
        """
        Initializes the search engine by loading FAISS index, mappings, and embedding model.
        """
        self.embedder = SentenceTransformer(embed_model)
        self.llm_handler = LLMHandler()
        self.index = None
        self.doc_mapping = {}

        if os.path.exists(index_path) and os.path.exists(mapping_path):
            try:
                self.index = faiss.read_index(index_path)
                self.doc_mapping = np.load(mapping_path, allow_pickle=True).item()
                logger.info("FAISS index and doc mapping loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load FAISS index or mapping: {e}")
        else:
            logger.error("FAISS index or mapping file not found.")

    def search_documents(self, query, top_n=5, filter_files=None):
        """
        Searches the FAISS index for the top_n semantically relevant text chunks.

        :param query: User query
        :param top_n: Number of chunks to retrieve
        :param filter_files: Optional list of document names to filter results from
        :return: List of dictionaries with keys: "chunk_id", "score", "text", "doc", and "page"
        """
        if not self.index or not self.doc_mapping:
            logger.error("Search attempted without a loaded FAISS index or mapping.")
            return []

        try:
            # Compute the query embedding
            query_embedding = self.embedder.encode(
                [query],
                normalize_embeddings=True,
                convert_to_numpy=True
            ).astype(np.float32)
            # Search the FAISS index (search wider range for filtering)
            distances, indices = self.index.search(query_embedding, top_n * 3)

            results = []
            for i, idx in enumerate(indices[0]):
                if idx not in self.doc_mapping:
                    continue

                entry = self.doc_mapping[idx]
                # Retrieve the fields from the mapping; default to empty string if missing
                chunk_id = entry.get("chunk_id", f"chunk_{idx}")
                chunk_text = entry.get("text", "")
                doc_name = entry.get("doc", "")  # Document name if provided
                page = entry.get("page", None)

                # If a file filter is provided, skip chunks whose document name is not in the filter list
                if filter_files and doc_name not in filter_files:
                    continue

                results.append({
                    "chunk_id": chunk_id,
                    "score": float(distances[0][i]),
                    "text": chunk_text,
                    "doc": doc_name,
                    "page": page
                })

                if len(results) >= top_n:
                    break

            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def generate_llm_response(self, query, context):
        """
        Uses the LLM to generate a response using only the given context.
        This version always uses generate_summary_from_chunks.
        
        :param query: User question
        :param context: Raw context string or list of chunks (each chunk must have a "text" key)
        :return: LLM-generated response
        """
        try:
            if not isinstance(context, list):
                context = [context]

            # Ensure each item has 'text', 'page', and 'doc'
            normalized_context = []
            for c in context:
                if isinstance(c, str):
                    normalized_context.append({
                        "text": c,
                        "page": None,
                        "doc": None
                    })
                elif isinstance(c, dict):
                    normalized_context.append({
                        "text": c.get("text", ""),
                        "page": c.get("page") or c.get("page_number") or None,
                        "doc": c.get("doc") or c.get("document") or None
                    })
                else:
                    logger.warning(f"Unexpected context item type: {type(c)}")
                    normalized_context.append({
                        "text": str(c),
                        "page": None,
                        "doc": None
                    })

            return self.llm_handler.generate_summary_from_chunks(query, normalized_context)

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "Unable to generate response at this time."

            if not isinstance(context, list):
                context = [context]

            # Ensure each item is a dict with 'text' and 'page'
            #print(context)
            normalized_context = []
            for c in context:
                if isinstance(c, str):
                    normalized_context.append({"text": c, "page": None})
                elif isinstance(c, dict):
                    normalized_context.append({
                        "text": c.get("text", ""),
                        "page": c.get("page") or c.get("page_number") or None
                    })
                else:
                    logger.warning(f"Unexpected context item type: {type(c)}")
                    normalized_context.append({"text": str(c), "page": None})

            return self.llm_handler.generate_summary_from_chunks(query, normalized_context)

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "Unable to generate response at this time."



    def nlp_incident_query(self, query, top_n=5):
        """
        Performs NLP-based search over embedded documents and incident reports.

        :param query: User natural language query
        :return: Dictionary containing:
            - "summary": LLM-generated summary,
            - "sources": List of retrieved chunk metadata,
            - "incidents": List of matched incidents (from incident_matcher)
        """
        sources = self.search_documents(query, top_n=top_n)
        
        # Wrap each chunk with doc and page for generate_llm_response
        context = [
            {
                "text": s["text"],
                "page": s.get("page"),
                "doc": s.get("doc"),
                "chunk_id": s.get("chunk_id")  # optional, in case used later
            }
            for s in sources
        ]
        
        summary = self.generate_llm_response(query, context)
        incidents = find_similar_incidents(query)

        return {
            "summary": summary,
            "sources": sources,
            "incidents": incidents
        }

