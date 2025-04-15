import os
import re
import logging
import faiss
import numpy as np
import fitz  # PyMuPDF for PDF extraction
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
        # Document mapping: vector ID -> dictionary with keys "chunk_id", "text", "page", and "doc"
        self.doc_mapping = {}

    #############################
    # Extraction Functions
    #############################
    def extract_text_from_pdf(self, pdf_path):
        """
        Extracts text from a PDF file.
        Returns a list of tuples: (page_number, page_text)
        """
        try:
            doc = fitz.open(pdf_path)
            pages = []
            for page_no, page in enumerate(doc):
                page_text = page.get_text("text")
                pages.append((page_no + 1, page_text))
            return pages
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return []

    def extract_text_from_docx(self, docx_path):
        """
        Extracts text from a DOCX file.
        """
        try:
            import docx
            document = docx.Document(docx_path)
            text = "\n".join([para.text for para in document.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX {docx_path}: {e}")
            return ""

    #############################
    # Chunking Functions
    #############################
    def split_paragraph_into_chunks(self, text, max_length=500, overlap=100):
        """
        Splits a long text (paragraph) into smaller chunks using a sliding window.
        
        :param text: The text to split.
        :param max_length: Maximum characters in a chunk.
        :param overlap: Overlap in characters between chunks.
        :return: List of text chunks.
        """
        chunks = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = start + max_length
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= text_length:
                break
            start = end - overlap
        return chunks

    def split_page_into_chunks(self, page_number, page_text, max_para_length=500, overlap=100):
        """
        Splits the page text into smaller chunks.
        First splits by paragraphs (double newlines). For paragraphs exceeding max_para_length,
        further splits using a sliding window.
        
        Returns a list of dictionaries with keys:
            - 'chunk_id': Unique identifier (combining page number and chunk index).
            - 'text': The chunk's text.
            - 'page': The page number.
        """
        paragraphs = re.split(r'\n\s*\n', page_text.strip())
        chunks = []
        chunk_counter = 1
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(para) <= max_para_length:
                chunks.append({
                    "chunk_id": f"page_{page_number}_chunk_{chunk_counter}",
                    "text": para,
                    "page": page_number
                })
                chunk_counter += 1
            else:
                sub_chunks = self.split_paragraph_into_chunks(para, max_length=max_para_length, overlap=overlap)
                for sub in sub_chunks:
                    chunks.append({
                        "chunk_id": f"page_{page_number}_chunk_{chunk_counter}",
                        "text": sub,
                        "page": page_number
                    })
                    chunk_counter += 1
        return chunks

    def process_file(self, file_path):
        """
        Processes a file (PDF or DOCX) to produce a list of chunk dictionaries.
        
        For PDFs, extracts text page-by-page, then uses hybrid chunking.
        For DOCX files, uses a simple text splitter.
        
        Each chunk dictionary contains:
            "chunk_id", "text", "page" (or None), and "doc" (document filename).
        """
        file_name = os.path.basename(file_path)
        if file_path.lower().endswith(".pdf"):
            pages = self.extract_text_from_pdf(file_path)
            chunks = []
            for page_number, page_text in pages:
                page_chunks = self.split_page_into_chunks(page_number, page_text, max_para_length=500, overlap=100)
                for chunk in page_chunks:
                    # Add document name to each chunk
                    chunk["doc"] = file_name
                    chunks.append(chunk)
            return chunks
        elif file_path.lower().endswith(".docx"):
            text = self.extract_text_from_docx(file_path)
            # Use a simple splitting method; for example, split on double newlines.
            paragraphs = re.split(r'\n\s*\n', text.strip())
            chunks = []
            for i, para in enumerate(paragraphs):
                para = para.strip()
                if para:
                    chunks.append({
                        "chunk_id": f"{file_name}_chunk{i+1}",
                        "text": para,
                        "doc": file_name,
                        "page": None
                    })
            return chunks
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return []

    #############################
    # Embedding Functions
    #############################
    def embed_texts(self, documents):
        """
        Generates embeddings for text chunks and stores them in a FAISS index.
        
        :param documents: List of dictionaries with keys: "chunk_id", "text", "page", and "doc".
        """
        if not documents:
            logger.warning("No documents provided for embedding.")
            return

        texts = [doc.get("text", "") for doc in documents]
        ids = [doc.get("chunk_id", f"chunk_{i}") for i, doc in enumerate(documents)]

        logger.info(f"Generating embeddings for {len(documents)} chunks...")
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True
        ).astype(np.float32)

        dimension = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexHNSWFlat(dimension, 32)
            self.index.hnsw.efConstruction = 64

        self.index.add(embeddings)

        start_id = len(self.doc_mapping)
        for i, chunk_id in enumerate(ids):
            mapping = {
                "chunk_id": chunk_id,
                "text": texts[i],
                "page": documents[i].get("page", None),
                "doc": documents[i].get("doc", "").strip() if documents[i].get("doc") else "Unknown Document"
            }
            self.doc_mapping[start_id + i] = mapping

        logger.info("Chunk embeddings stored in FAISS index.")

    def save_index(self, index_path="faiss_index.bin", mapping_path="doc_mapping.npy"):
        """
        Saves the FAISS index and document mapping to disk.
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
        """
        try:
            self.index = faiss.read_index(index_path)
            self.doc_mapping = np.load(mapping_path, allow_pickle=True).item()
            logger.info("FAISS index and document mapping loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
