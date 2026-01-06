import os
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import List

from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    def summarize(self, text: str) -> str: ...

    @abstractmethod
    def extract_keywords(self, text: str) -> List[str]: ...

    @abstractmethod
    def generate_tags(self, text: str) -> List[str]: ...

    @abstractmethod
    def embed(self, text: str) -> List[float]: ...


@lru_cache()
def get_provider() -> LLMProvider:
    if settings.openai_api_key:
        from app.llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    from app.llm.providers.mock import MockProvider
    return MockProvider()
