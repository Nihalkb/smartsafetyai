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
        """Removes expired cached responses."""
        current_time = time.time()
        self.cache = {k: v for k, v in self.cache.items() if current_time - v["timestamp"] <= self.cache_ttl}

    def generate_response(self, prompt, context=None, max_length=250):
        """Generates an AI response based on the prompt and optional context."""
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
            messages = [{"role": "system", "content": "You are a safety information assistant."}]
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
        """Analyzes sentiment using the LLM and returns a rating (1-5) with confidence."""
        if not self.client:
            logger.warning("Sentiment analysis fallback due to missing LLM client.")
            return {"rating": 3, "confidence": 0.5}  # Neutral fallback

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
                "rating": result.get("rating", 3),  # Default: Neutral sentiment
                "confidence": result.get("confidence", 0.5)  # Default: 50% confidence
            }
        except json.JSONDecodeError:
            logger.error("Invalid JSON format received from LLM.")
            return {"rating": 3, "confidence": 0.5}
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {"rating": 3, "confidence": 0.5}
