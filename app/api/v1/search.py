from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.db.models import KnowledgeItem
from app.services.indexing.qdrant_store import QdrantStore

router = APIRouter()


@router.get('/text')
async def text_search(q: str, db: AsyncSession = Depends(get_db)):
    stmt = select(KnowledgeItem).where(
        KnowledgeItem.is_deleted == False,
        (KnowledgeItem.title.ilike(f"%{q}%")) | (KnowledgeItem.summary.ilike(f"%{q}%")) | (KnowledgeItem.content_text.ilike(f"%{q}%"))
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return {"success": True, "data": [
        {"id": item.id, "title": item.title, "summary": item.summary, "score": None}
        for item in items
    ]}


@router.get('/semantic')
async def semantic_search(q: str, top_k: int = 10):
    store = QdrantStore()
    results = await store.search(q, top_k=top_k)
    return {"success": True, "data": results}
