import logging
import time
import os
from openai import OpenAI
from search_engine import SearchEngine
from embed_documents import EmbedDocuments
from doc_processor import DocProcessor
from langchain.text_splitter import RecursiveCharacterTextSplitter
from incident_matcher import find_similar_incidents  # ✅ new module for incident suggestions

logger = logging.getLogger(__name__)

UPLOADS_FOLDER = "data/uploads"

class Chatbot:
    def __init__(self):
        self.token = os.getenv("LLMFOUNDRY_TOKEN", "").strip()
        self.model = "gpt-4o-mini"
        self.base_url = "https://llmfoundry.straive.com/openai/v1/"
        self.client = self._initialize_llm_client()

        self.chat_memory = {}  # session_id → {timestamp, messages: []}
        self.memory_ttl = 3600
        self.max_memory_messages = 5  # ✅ keep only last 5 messages per session

        self.search_engine = SearchEngine()
        self.embedder = EmbedDocuments()
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

        self.uploaded_embeddings = {}  # session_id → list of (chunk_id, chunk_text)

    def _initialize_llm_client(self):
        if not self.token:
            logger.warning("LLMFOUNDRY_TOKEN is missing. LLM calls will not work.")
            return None
        try:
            client = OpenAI(api_key=f"{self.token}:my-test-project", base_url=self.base_url)
            logger.info("LLM Foundry client initialized.")
            return client
        except Exception as e:
            logger.error(f"Error initializing LLM Foundry client: {e}")
            return None

    def _clean_memory(self):
        current_time = time.time()
        expired_sessions = [s for s, d in self.chat_memory.items() if current_time - d["timestamp"] > self.memory_ttl]
        for s in expired_sessions:
            self.chat_memory.pop(s, None)
            self.uploaded_embeddings.pop(s, None)

    def clear_memory(self, session_id):
        self.chat_memory.pop(session_id, None)
        self.uploaded_embeddings.pop(session_id, None)
        return True

    def process_uploaded_file(self, session_id, file_path):
        logger.info(f"Processing uploaded file for session: {session_id} → {file_path}")
        ext = file_path.lower().split(".")[-1]
        if ext not in ["pdf", "docx", "txt"]:
            logger.warning(f"Unsupported file type: {file_path}")
            return False

        chunks = []
        try:
            processor = DocProcessor(UPLOADS_FOLDER)
            if ext == "pdf":
                chunks = processor._extract_pdf_chunks(file_path, os.path.basename(file_path))
            elif ext == "docx":
                chunks = processor._extract_docx_chunks(file_path, os.path.basename(file_path))
            elif ext == "txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read().strip().lower()
                    if text:
                        base_name = os.path.splitext(os.path.basename(file_path))[0]
                        chunks = [(f"{base_name}_chunk_0", text, base_name, None)]
        except Exception as e:
            logger.error(f"Error reading uploaded file: {e}")
            return False

        if not chunks:
            return False

        simplified_chunks = [(chunk_id, chunk, doc_name, page_num) for chunk_id, chunk, doc_name, page_num in chunks]

        if session_id not in self.uploaded_embeddings:
            self.uploaded_embeddings[session_id] = []

        self.uploaded_embeddings[session_id].extend(simplified_chunks)
        logger.info(f"Stored {len(simplified_chunks)} chunks in session memory for uploaded file.")
        return True

    def chat(self, session_id, user_message, filter_files=None):
        self._clean_memory()

        retrieved_docs = self.search_engine.search_documents(user_message, top_n=5, filter_files=filter_files)
        context_chunks = []
        source_refs = []
        referenced_chunks = []

        for item in retrieved_docs:
            chunk_id = item.get("chunk_id")
            chunk_text = item.get("text")
            doc_name = item.get("doc", "")
            page = item.get("page")

            context_chunks.append(chunk_text)
            source_refs.append(f"- from {doc_name}, page {page}")
            referenced_chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "doc": doc_name,
                "page": page
            })

        if session_id in self.uploaded_embeddings:
            uploaded_chunks = self.uploaded_embeddings[session_id]
            self.embedder.embed_texts([(c[0], c[1]) for c in uploaded_chunks])

            if self.embedder.index is not None:
                query_embedding = self.embedder.model.encode(
                    [user_message], normalize_embeddings=True, convert_to_numpy=True
                ).astype("float32")
                D, I = self.embedder.index.search(query_embedding, 3)

                for idx in I[0]:
                    match = self.embedder.doc_mapping.get(idx)
                    if match:
                        context_chunks.append(match["text"])
                        source_refs.append(f"- from uploaded file, chunk {idx}")
                        referenced_chunks.append({"chunk_id": match["chunk_id"], "text": match["text"]})

        context = "\n".join(context_chunks).strip()
        if not context:
            return "I'm sorry, I couldn't find relevant information for your question in the selected documents."

        if session_id not in self.chat_memory:
            self.chat_memory[session_id] = {"timestamp": time.time(), "messages": []}

        # ✅ In-memory message persistence
        memory = self.chat_memory[session_id]["messages"]
        system_prompt = {
            "role": "system",
            "content": (
                "You are a chemical safety assistant. Use the provided context to answer questions in a numbered format.\n"
                "For each point you mention, also include the reference to its document source like: '... (Document: doc_name, Chunk: X, Page: Y)'.\n"
                "If relevant incidents are identified, mention they are shown in the left sidebar.\n"
                "Do not fabricate information."
            )
        }

        context_message = {
            "role": "system",
            "content": f"Context extracted from documents:\n\n{referenced_chunks}"
        }

        user_msg = {"role": "user", "content": user_message}

        # Combine last memory + current context
        messages = [system_prompt, context_message] + memory[-self.max_memory_messages:] + [user_msg]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=600,
                temperature=0.5
            )
            final_response = response.choices[0].message.content.strip()

            # ✅ Store user + assistant messages in memory
            memory.append(user_msg)
            memory.append({"role": "assistant", "content": final_response})
            self.chat_memory[session_id]["timestamp"] = time.time()

            incidents = find_similar_incidents(user_message)

            return {
                "answer": final_response,
                "sources": source_refs,
                "incidents": incidents,
                "referenced_chunks": referenced_chunks
            }
        except Exception as e:
            logger.error(f"Chatbot LLM error: {e}")
            return {
                "answer": "Sorry, I encountered an error while processing your request.",
                "sources": [],
                "incidents": [],
                "referenced_chunks": []
            }
