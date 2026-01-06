from typing import List
import openai

from app.core.config import settings
from app.llm.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        openai.api_key = settings.openai_api_key
        openai.base_url = getattr(openai, "base_url", None) or None
        self.model = settings.openai_model

    def summarize(self, text: str) -> str:
        resp = openai.chat.completions.create(model=self.model, messages=[{"role": "user", "content": f"Summarize: {text}"}])
        return resp.choices[0].message.content

    def extract_keywords(self, text: str) -> List[str]:
        resp = openai.chat.completions.create(model=self.model, messages=[{"role": "user", "content": f"Keywords list: {text}"}])
        return [k.strip() for k in resp.choices[0].message.content.split(',') if k.strip()]

    def generate_tags(self, text: str) -> List[str]:
        resp = openai.chat.completions.create(model=self.model, messages=[{"role": "user", "content": f"Tags: {text}"}])
        return [k.strip() for k in resp.choices[0].message.content.split(',') if k.strip()]

    def embed(self, text: str) -> List[float]:
        resp = openai.embeddings.create(model="text-embedding-3-small", input=text)
        return resp.data[0].embedding
