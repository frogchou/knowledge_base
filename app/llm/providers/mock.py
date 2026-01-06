import hashlib
import random
from typing import List

from app.core.config import settings
from app.llm.providers.base import LLMProvider


class MockProvider(LLMProvider):
    def summarize(self, text: str) -> str:
        return text[:200] + ("..." if len(text) > 200 else "")

    def extract_keywords(self, text: str) -> List[str]:
        words = list({w.strip('.,') for w in text.split()[:10]})
        return words[:5]

    def generate_tags(self, text: str) -> List[str]:
        return ["mock", "auto"]

    def embed(self, text: str) -> List[float]:
        random.seed(hashlib.sha256(text.encode()).hexdigest())
        return [random.random() for _ in range(settings.embedding_dim)]
