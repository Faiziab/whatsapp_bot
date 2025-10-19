"""
LLM Adapter for Google Gemini
Provides a thin wrapper with guardrails for generating natural replies
"""

import logging
from typing import List, Dict, Optional

from config import Config

logger = logging.getLogger(__name__)


class GeminiAdapter:
    """Adapter to interact with Google Generative AI (Gemini)"""

    def __init__(self):
        self.enabled = Config.USE_GEMINI and bool(Config.GEMINI_API_KEY)
        self._model = None
        if self.enabled:
            try:
                import google.generativeai as genai
                genai.configure(api_key=Config.GEMINI_API_KEY)
                # Use a lightweight, general model for short replies
                self._model = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("✅ Gemini adapter initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini: {e}")
                self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled and self._model is not None

    def generate_clarification(self, product_hook: str, state_id: str, user_message: str,
                                next_expected: str, history: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Generate a natural clarification response that guides the user back to the flow.

        Args:
            product_hook: Short product blurb to keep context rooted
            state_id: Current dialogue state id
            user_message: The user's raw message
            next_expected: Instruction on expected reply format (e.g., Yes/No)
            history: Optional brief history for tone continuity
        """
        if not self.is_enabled():
            return None

        system_rules = (
            "You are a concise, helpful mortgage assistant. "
            "Respond politely in <= 2 sentences. "
            "Do not invent policy or eligibility outcomes. "
            "Gently guide the user to answer the expected input. "
            "Avoid links unless provided."
        )

        prompt = (
            f"Context: {product_hook}\n"
            f"State: {state_id}\n"
            f"User said: {user_message}\n"
            f"Expected reply: {next_expected}\n\n"
            "Write a friendly clarification that restates the question and gives 1 short example of a valid reply."
        )

        try:
            result = self._model.generate_content([
                {"role": "user", "parts": [system_rules]},
                {"role": "user", "parts": [prompt]},
            ])
            text = getattr(result, "text", None) or (result.candidates[0].content.parts[0].text if getattr(result, "candidates", None) else None)
            if not text:
                return None
            # Ensure brevity
            return text.strip()[:500]
        except Exception as e:
            logger.error(f"❌ Gemini generation error: {e}")
            return None


