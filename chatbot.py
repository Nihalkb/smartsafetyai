import logging
import time
import json
import os
from openai import OpenAI
from search_engine import SearchEngine

logger = logging.getLogger(__name__)

class Chatbot:
    def __init__(self):
        """Initializes the Chatbot with LLM API and Vector Search."""
        self.token = os.getenv("LLMFOUNDRY_TOKEN", "").strip()
        self.model = "gpt-4o-mini"
        self.base_url = "https://llmfoundry.straive.com/openai/v1/"
        self.client = self._initialize_llm_client()

        # Memory cache for chat history (stores last 5 exchanges per session)
        self.chat_memory = {}
        self.memory_ttl = 3600  # 1-hour memory timeout

        # Vector search engine for retrieving relevant documents
        self.search_engine = SearchEngine()

    def _initialize_llm_client(self):
        """Initializes LLM Foundry API client."""
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
        """Removes expired chat sessions from memory."""
        current_time = time.time()
        expired_sessions = [session for session, data in self.chat_memory.items()
                            if current_time - data["timestamp"] > self.memory_ttl]
        for session in expired_sessions:
            del self.chat_memory[session]

    def clear_memory(self, session_id):
        """Clears memory for a specific chat session."""
        if session_id in self.chat_memory:
            del self.chat_memory[session_id]
            return True
        return False

    def chat(self, session_id, user_message):
        """
        Handles user chat interactions:
        - Retrieves relevant context from vector embeddings
        - Generates a response using LLM
        - Maintains internal conversation memory

        :param session_id: Unique chat session ID
        :param user_message: User input message
        :return: AI-generated response
        """
        self._clean_memory()  # Cleanup expired sessions

        # Retrieve relevant documents from FAISS
        retrieved_docs = self.search_engine.search_documents(user_message, top_n=3)
        context = "\n".join([doc[2] for doc in retrieved_docs])  # Extract relevant snippets

        # Initialize session memory if not exists
        if session_id not in self.chat_memory:
            self.chat_memory[session_id] = {"history": [], "timestamp": time.time()}

        # Retrieve and update memory (keep last 5 exchanges)
        chat_history = self.chat_memory[session_id]["history"]
        chat_history.append({"role": "user", "content": user_message})

        # Trim chat history to last 5 messages
        chat_history = chat_history[-5:]

        # Construct message payload with memory and context
        messages = [{"role": "system", "content": "You are a knowledgeable safety assistant."}]
        messages.extend(chat_history)  # Add last 5 exchanges for memory
        if context:
            messages.append({"role": "system", "content": f"Relevant safety information:\n{context}"})
        messages.append({"role": "user", "content": user_message})

        # Generate response using LLM Foundry
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.5
            )
            ai_response = response.choices[0].message.content

            # Store assistant response in memory
            chat_history.append({"role": "assistant", "content": ai_response})
            self.chat_memory[session_id]["history"] = chat_history  # Save updated history

            return ai_response
        except Exception as e:
            logger.error(f"Chatbot LLM error: {e}")
            return "Sorry, I encountered an error while processing your request."
