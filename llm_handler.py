import os
import logging
import time
import json
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMHandler:
    def __init__(self):
        self.token = os.getenv("LLMFOUNDRY_TOKEN", "").strip()
        self.project = "my-test-project"
        self.base_url = "https://llmfoundry.straive.com/openai/v1/"
        self.model = "gpt-4o-mini"
        self.cache = {}
        self.cache_ttl = 3600  # Cache expiry time in seconds

        if not self.token:
            logger.warning("LLMFOUNDRY_TOKEN is missing. LLM calls will not work.")
            self.client = None
        else:
            try:
                self.client = OpenAI(
                    api_key=f"{self.token}:{self.project}",
                    base_url=self.base_url
                )
                logger.info("LLM Foundry client initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing LLM Foundry client: {e}")
                self.client = None

    def _clean_cache(self):
        current_time = time.time()
        self.cache = {
            k: v for k, v in self.cache.items() if current_time - v["timestamp"] <= self.cache_ttl
        }

    def generate_response(self, prompt, context=None, max_length=250):
        self._clean_cache()
        context_str = str(context) if context else ""
        cache_key = f"{prompt}_{context_str}"

        if cache_key in self.cache:
            logger.info("Returning cached response.")
            return self.cache[cache_key]["response"]

        if not self.client:
            logger.error("LLM client not initialized.")
            return "Error: LLM client unavailable."

        try:
            messages = [{
                "role": "system",
                "content": (
                    "You are a safety information assistant. Answer the query based solely on the provided context. "
                    "Do not use any external sources. Ensure that your response aligns with the given context."
                )
            }]
            if context:
                messages.append({"role": "system", "content": context_str})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_length,
                temperature=0.5
            )

            generated_text = response.choices[0].message.content
            self.cache[cache_key] = {"response": generated_text, "timestamp": time.time()}
            return generated_text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Error generating response."

    def analyze_sentiment(self, text):
        if not self.client:
            logger.warning("Sentiment analysis fallback due to missing LLM client.")
            return {"rating": 3, "confidence": 0.5}

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Analyze sentiment and return JSON with keys 'rating' (1-5) and 'confidence' (0-1)."},
                    {"role": "user", "content": text}
                ]
            )

            result = json.loads(response.choices[0].message.content)
            return {
                "rating": result.get("rating", 3),
                "confidence": result.get("confidence", 0.5)
            }
        except json.JSONDecodeError:
            logger.error("Invalid JSON format received from LLM.")
            return {"rating": 3, "confidence": 0.5}
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {"rating": 3, "confidence": 0.5}

    def parse_filters(self, natural_query):
        """Converts a natural query to structured filter parameters using the LLM."""
        if not self.client:
            logger.error("LLM client not initialized.")
            return {}

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a filter extraction engine. Extract and return a JSON object "
                        "from the user's query with keys such as 'material', 'location_contains', "
                        "'from_year', 'to_year', 'has_injuries', and 'severity'. "
                        "Respond with JSON only. Do not include explanations or extra text.\n\n"
                        "Example:\n"
                        "Input: gas leaks in Texas with injuries after 2022\n"
                        "Output:\n"
                        "{\n"
                        "  \"material\": \"gas\",\n"
                        "  \"location_contains\": \"Texas\",\n"
                        "  \"has_injuries\": true,\n"
                        "  \"from_year\": 2022\n"
                        "}"
                    )
                },
                {
                    "role": "user",
                    "content": natural_query
                }
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.3
            )

            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            return parsed
        except Exception as e:
            logger.error(f"Filter parsing error: {e}")
            return {}
        
    def generate_summary_from_chunks(self, query, chunks, context_type="incident"):
        """
        Summarizes relevant info from provided chunks based on the query.

        :param query: User query.
        :param chunks: List of dictionaries with a "text" key and optional "page".
        :param context_type: "incident" (default) or "document"
        :return: The LLM-generated summary.
        """
        if not self.client:
            return "LLM client unavailable."

        # Format context with page numbers
        context = "\n\n".join([
        f"(Document: {chunk.get('doc', 'Unknown')}, Page: {chunk.get('page', 'Unknown')})\n{chunk['text']}" 
        for chunk in chunks if 'text' in chunk
    ])
        if context_type == "incident":
            prompt = (
                f"Based on the following safety incident context, provide a short and clear summary "
                f"in response to the user query: '{query}'"
            )
        else:
            prompt = (
                f"Based on the following document context, provide a concise, well-structured answer "
                f"to the user's query: '{query}'"
            )

        try:
            #print(context)
            messages = [
                {"role": "system", "content": (
                    "You are a chemical safety assistant. Use the provided context to answer questions in a numbered format.\n"
                    "For each point you mention, include the reference to its document source as: '... (Document: doc_name, Page: X)' if available.\n"
                    "You can assume some technical terms such as PPE, but do not fabricate any information."
                )},
                {"role": "system", "content": context},  # Full formatted context with page numbers
                {"role": "user", "content": prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"generate_summary_from_chunks failed: {e}")
            return "Failed to generate summary from provided context."

