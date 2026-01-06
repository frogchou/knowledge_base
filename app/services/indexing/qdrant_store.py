import asyncio
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.llm.providers.base import get_provider


class QdrantStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        self.collection = "knowledge_items"
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
            )

    async def upsert_item(self, item_id: str, embedding: list[float], payload: dict) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.upsert(
                collection_name=self.collection,
                points=[PointStruct(id=item_id, vector=embedding, payload=payload)],
            ),
        )

    async def delete_item(self, item_id: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: self.client.delete(collection_name=self.collection, points_selector=[item_id])
        )

    async def search(self, text: str, top_k: int = 10) -> list[dict]:
        provider = get_provider()
        query = provider.embed(text)
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.client.search(collection_name=self.collection, query_vector=query, limit=top_k),
            )
            return [
                {"id": r.id, "score": r.score, "payload": r.payload}
                for r in result
            ]
        except Exception:
            return []
